#!/usr/bin/env bash
# authority_doc_budget.sh — shared PostToolUse hook for Claude Code and Codex.
#
# Watches the size of the AUTHORITATIVE agent contracts — root /AGENTS.md and
# every nested subdirectory AGENTS.md (plus the CLAUDE.md symlink) — so they
# stay lean ENTRY POINTS, not detail dumps. When an edit pushes a contract past
# its line budget, it surfaces an advisory nudge: move the detail into docs/ and
# keep only important, frequently-needed points inline in the contract.
#
# Never blocks (growth is a judgment call; the commit-time gates remain the hard
# enforcement). It only informs the agent so it can choose to trim or relocate.
#
# Budgets — override via env (e.g. in .claude/settings.local.json env, or shell):
#   AUTHORITY_DOC_MAX_ROOT    root /AGENTS.md       (default 320 lines)
#   AUTHORITY_DOC_MAX_NESTED  any subdir AGENTS.md  (default 120 lines)
#
# Wired for BOTH runtimes at the same shared impl:
#   - Claude Code: .claude/settings.json PostToolUse → this script ($CLAUDE_PROJECT_DIR set)
#   - Codex:       .codex/hooks.json     PostToolUse → this script (proj resolved via git)
# Reads the tool-call JSON on stdin; always exits 0 (advisory). When jq is
# available it emits the nudge as PostToolUse additionalContext (fed to the
# agent); otherwise it falls back to stderr (shown to the user).
set -uo pipefail

max_root="${AUTHORITY_DOC_MAX_ROOT:-320}"
max_nested="${AUTHORITY_DOC_MAX_NESTED:-120}"

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Location-independent project root: $CLAUDE_PROJECT_DIR (Claude Code) if set,
# else the git toplevel of the hook's own dir (works for Codex and any layout).
proj="${CLAUDE_PROJECT_DIR:-$(git -C "$hook_dir" rev-parse --show-toplevel 2>/dev/null || (cd "$hook_dir/../../.." && pwd))}"
input="$(cat || true)"

# Pull every file path the tool call touched out of the hook JSON on stdin.
# Handles Edit/Write (file_path/path) and apply_patch payloads. python
# preferred, jq fallback; with neither, stay silent (advisory hook, fail open).
extract_paths() {
    if command -v python >/dev/null 2>&1; then
        HOOK_INPUT="$input" python - <<'PY'
import json, os, re, sys
raw = os.environ.get("HOOK_INPUT", "")
try:
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    sys.exit(0)
tool_input = data.get("tool_input") or {}
if not isinstance(tool_input, dict):
    tool_input = {"input": str(tool_input)}
cwd = data.get("cwd") or os.environ.get("PWD") or os.getcwd()
paths = []
for key in ("file_path", "notebook_path", "path"):
    value = tool_input.get(key)
    if isinstance(value, str) and value:
        paths.append(value)
patch = tool_input.get("patch") or tool_input.get("input") or data.get("input")
if isinstance(patch, str):
    for line in patch.splitlines():
        m = re.match(r"^\*\*\* (?:Add|Update) File: (.+)$", line)
        if m:
            paths.append(m.group(1).strip())
seen = set()
for path in paths:
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(cwd, path))
    if path not in seen:
        seen.add(path)
        print(path)
PY
    elif command -v jq >/dev/null 2>&1; then
        jq -r '.tool_input.file_path // .tool_input.notebook_path // .tool_input.path // empty' <<<"$input" 2>/dev/null
    fi
}

warnings=()
while IFS= read -r file_path; do
    [[ -n "${file_path:-}" && "$file_path" == /* && -e "$file_path" ]] || continue
    case "$(basename -- "$file_path")" in
        AGENTS.md | CLAUDE.md) ;;
        *) continue ;;
    esac

    # Only the project repo's contracts (not nested/sibling repos).
    dir="$(dirname -- "$file_path")"
    file_common="$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || continue
    proj_common="$(git -C "$proj" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || continue
    [[ "$file_common" == "$proj_common" ]] || continue
    toplevel="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || continue

    # Resolve the CLAUDE.md → AGENTS.md symlink so each contract is measured once.
    real="$file_path"
    [[ -L "$file_path" ]] && real="$(readlink -f "$file_path" 2>/dev/null || echo "$file_path")"
    [[ -f "$real" ]] || continue
    lines="$(wc -l <"$real" 2>/dev/null | tr -d ' ')" || continue
    [[ "$lines" =~ ^[0-9]+$ ]] || continue

    rel="${real#"$toplevel"/}"
    if [[ "$rel" == "AGENTS.md" ]]; then
        budget="$max_root"
    else
        budget="$max_nested"
    fi
    if ((lines > budget)); then
        warnings+=("$rel — $lines lines (budget $budget, +$((lines - budget)) over)")
    fi
done < <(extract_paths)

((${#warnings[@]} > 0)) || exit 0

msg="Authoritative-doc budget exceeded — AGENTS.md is an ENTRY POINT, not a detail dump:
$(printf '  - %s\n' "${warnings[@]}")
Keep the contract lean: move detail into docs/ and link to it; leave inline only important, frequently-needed points. Trim back under budget, or raise AUTHORITY_DOC_MAX_ROOT / AUTHORITY_DOC_MAX_NESTED if the budget is genuinely too low."

if command -v jq >/dev/null 2>&1; then
    jq -cn --arg m "$msg" \
        '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$m}}'
else
    echo "authority_doc_budget: $msg" >&2
fi
exit 0
