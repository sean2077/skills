#!/usr/bin/env bash
# trunk_edit_guard.sh — PreToolUse guard for the worktree-per-change workflow.
#
# The mechanical other half of worktree.sh. It enforces this skill's hard
# invariant: never edit tracked files in a trunk worktree (main / master /
# release/* / maintenance/*). The guard blocks the wrong move and points at the
# right one (`worktree.sh new <name>`); worktree.sh provides that workflow.
#
# Wire it up as a Claude Code PreToolUse hook (see SKILL.md → "Mechanical
# enforcement"). It reads the tool-call JSON on stdin and exits:
#   0  allow
#   2  block — the message on stderr tells the agent what to run instead
# Any other exit is treated as a non-blocking error (fails open / allows).
#
# It only guards files that belong to the project repo (same git-common-dir),
# so edits to nested or sibling repos pass through, and it never blocks
# gitignored paths (build output, caches, …).
#
# Escape hatches — use ONLY when the user explicitly authorizes a trunk edit:
#   WORKTREE_ALLOW_TRUNK_EDIT=1              one-shot env bypass
#   touch <repo>/.claude/allow-trunk-edit   flag file, auto-expires in 2 h
#
# Env knobs:
#   WORKTREE_ALLOW_TRUNK_EDIT  set to 1 to disable the guard entirely
#   WORKTREE_GUARD_CMD         command shown in the block message
#                              (default: worktree.sh; set to e.g. tools/worktree.sh)
set -uo pipefail

[[ "${WORKTREE_ALLOW_TRUNK_EDIT:-0}" == "1" ]] && exit 0

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# CLAUDE_PROJECT_DIR is set by Claude Code; the fallback assumes the hook is
# installed at <repo>/.claude/hooks/trunk_edit_guard.sh.
proj="${CLAUDE_PROJECT_DIR:-$(cd "$hook_dir/../.." && pwd)}"
wt_cmd="${WORKTREE_GUARD_CMD:-worktree.sh}"
input="$(cat || true)"

# Pull every file path the tool call would touch out of the hook JSON on stdin.
# Handles Edit/Write/NotebookEdit (file_path/notebook_path/path) and apply_patch
# style payloads (*** Add|Update|Delete File: …). python3 preferred, jq fallback;
# with neither, fail open rather than block blindly.
extract_paths() {
    if command -v python3 >/dev/null 2>&1; then
        HOOK_INPUT="$input" python3 - "$proj" <<'PY'
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
        m = re.match(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", line)
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
    else
        echo "trunk_edit_guard: neither python3 nor jq available — cannot parse hook input, allowing" >&2
    fi
}

check_path() {
    local file_path="$1"
    [[ -n "${file_path:-}" && "$file_path" == /* ]] || return 0

    # Walk up to the nearest existing dir (the file itself may be a new file).
    local dir
    dir="$(dirname -- "$file_path")"
    while [[ ! -d "$dir" && "$dir" != "/" ]]; do
        dir="$(dirname -- "$dir")"
    done

    git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0

    # Only guard files belonging to the project repo, not nested/sibling repos.
    local proj_common file_common
    proj_common="$(git -C "$proj" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 0
    file_common="$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 0
    [[ "$file_common" == "$proj_common" ]] || return 0

    local branch
    branch="$(git -C "$dir" branch --show-current 2>/dev/null)"
    case "$branch" in
        main | master | release/* | maintenance/*) ;;
        *) return 0 ;;
    esac

    # Never block ignored files (build output, caches, vendored payloads, …).
    git -C "$dir" check-ignore -q -- "$file_path" 2>/dev/null && return 0

    local toplevel flag stale now mtime
    toplevel="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || return 0
    flag="$toplevel/.claude/allow-trunk-edit"
    stale=""
    if [[ -f "$flag" ]]; then
        now="$(date +%s)"
        mtime="$(stat -c %Y "$flag" 2>/dev/null || stat -f %m "$flag" 2>/dev/null || echo 0)"
        if ((now - mtime <= 7200)); then
            return 0
        fi
        stale=" (a STALE $flag exists — touch it again to renew)"
    fi

    cat >&2 <<EOF
trunk_edit_guard: BLOCKED — $file_path
This checkout ($toplevel) is on trunk branch '$branch'. Every change, however
small ("just docs" is NOT an exception), starts in its own .worktrees/ branch:
    $wt_cmd new <name>      # then edit inside .worktrees/<name>/
Only if the user explicitly named a trunk in this conversation:
    touch $toplevel/.claude/allow-trunk-edit    # auto-expires in 2 h${stale}
EOF
    return 2
}

blocked=0
while IFS= read -r path; do
    if ! check_path "$path"; then
        blocked=2
    fi
done < <(extract_paths)

exit "$blocked"
