#!/usr/bin/env bash
# format_on_edit.sh — shared PostToolUse hook for Claude Code and Codex.
#
# Runs a formatter on the files an edit just touched, reusing the project's OWN
# formatter config (it does NOT introduce a second one). It defaults to the
# project's Prettier on TS/JS/JSON; point it at any formatter via env. It never
# blocks: failures are loud no-ops, because the commit-time gate (pre-commit /
# CI) remains the hard enforcement point.
#
# Env overrides (set in .claude/settings.local.json env, or the shell):
#   FORMAT_ON_EDIT_CMD   formatter command; the file path is appended as the
#                        last arg (default: "npx --no-install prettier --write")
#   FORMAT_ON_EDIT_EXTS  space-separated extensions to format, no dots
#                        (default: "ts tsx js mjs cjs json")
# Examples:
#   FORMAT_ON_EDIT_CMD="gofmt -w"        FORMAT_ON_EDIT_EXTS="go"
#   FORMAT_ON_EDIT_CMD="ruff format"     FORMAT_ON_EDIT_EXTS="py pyi"
#
# Wired for BOTH runtimes at the same shared impl:
#   - Claude Code: .claude/settings.json PostToolUse → this script ($CLAUDE_PROJECT_DIR set)
#   - Codex:       .codex/hooks.json     PostToolUse → this script (proj resolved via git)
set -uo pipefail

fmt_cmd="${FORMAT_ON_EDIT_CMD:-npx --no-install prettier --write}"
fmt_exts="${FORMAT_ON_EDIT_EXTS:-ts tsx js mjs cjs json}"

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="${CLAUDE_PROJECT_DIR:-$(git -C "$hook_dir" rev-parse --show-toplevel 2>/dev/null || (cd "$hook_dir/../../.." && pwd))}"
input="$(cat || true)"

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
for key in ("file_path", "path"):
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
        jq -r '.tool_input.file_path // .tool_input.path // empty' <<<"$input" 2>/dev/null
    fi
}

# Bail (loud no-op) if the formatter's launcher isn't on PATH (e.g. no npx).
fmt_bin="${fmt_cmd%% *}"
command -v "$fmt_bin" >/dev/null 2>&1 || exit 0

formatted=()
while IFS= read -r file_path; do
    [[ -n "${file_path:-}" && "$file_path" == /* && -f "$file_path" ]] || continue
    # Extension allow-list (from FORMAT_ON_EDIT_EXTS).
    matched=0
    for e in $fmt_exts; do [[ "$file_path" == *."$e" ]] && { matched=1; break; }; done
    [[ $matched -eq 1 ]] || continue
    case "$file_path" in
        */node_modules/* | */dist/* | */dev-dist/* | */build/* | */.wrangler/* | */.git/*) continue ;;
    esac

    dir="$(dirname -- "$file_path")"
    file_common="$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || continue
    proj_common="$(git -C "$proj" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || continue
    [[ "$file_common" == "$proj_common" ]] || continue
    # Skip files the formatter is configured to ignore (reuses e.g. .prettierignore).
    git -C "$dir" check-ignore -q -- "$file_path" 2>/dev/null && continue

    before="$(cksum <"$file_path")"
    # shellcheck disable=SC2086  # fmt_cmd is intentionally word-split into argv
    if ! out="$(cd "$proj" && $fmt_cmd "$file_path" 2>&1)"; then
        echo "format_on_edit: skipped — ${out##*$'\n'} (commit-time gate still applies)" >&2
        continue
    fi
    after="$(cksum <"$file_path")"
    [[ "$before" != "$after" ]] && formatted+=("$file_path")
done < <(extract_paths)

if [[ ${#formatted[@]} -gt 0 ]] && command -v jq >/dev/null 2>&1; then
    joined="$(printf '%s\n' "${formatted[@]}")"
    jq -cn --arg files "$joined" \
        '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:("The formatter rewrote these files after your edit — re-read them before further exact-string edits:\n" + $files)}}'
fi
exit 0
