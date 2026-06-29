#!/usr/bin/env bash
# e2e-agent-scaffold.sh — behavioral end-to-end test of the agent-scaffold installer.
#
# Installs the harness into a throwaway git repo and asserts the invariants the
# static gate (check-agent-scaffold.sh) cannot: dual-host wiring, idempotent re-run,
# retrofit-merge of a pre-existing hook, the worktree round-trip, the trunk guard's
# block + escape hatch, and relink coexistence with an npx-installed skill.
# Mirrors skills/agent-scaffold/reference.md section 12. All writes stay in a mktemp dir.
#
# Usage: bash scripts/e2e-agent-scaffold.sh [-h|--help]
# Exit 0 = all assertions passed, 1 = a failure. Needs git + python3.
set -uo pipefail

usage() { sed -n '2,11p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "${1:-}" in -h | --help) usage 0 ;; esac

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
H="$repo/skills/agent-scaffold/harness-init.sh"
[ -f "$H" ] || { echo "installer not found: $H" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 required" >&2; exit 1; }

fails=0
ok()  { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; fails=$((fails + 1)); }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
# JSON assertions via python3 (portable; avoids a jq dependency in CI).
# shellcheck disable=SC2317  # jmatch/jcount run indirectly through check() "$@"
jmatch() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d["hooks"][sys.argv[2]][0]["matcher"]==sys.argv[3] else 1)' "$@"; }
# shellcheck disable=SC2317
jcount() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if len(d["hooks"][sys.argv[2]][0]["hooks"])==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317  # run indirectly through check() "$@"
is_real_dir() { [ -d "$1" ] && [ ! -L "$1" ]; }

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
S="$work/scratch"; mkdir -p "$S"
git -C "$S" init -q -b main
git -C "$S" config user.email t@t.t; git -C "$S" config user.name tester
git -C "$S" commit -q --allow-empty -m init

echo "== init (greenfield) =="
( cd "$S" && bash "$H" init ) >/dev/null 2>&1 || bad "init exited nonzero"
check "no bogus '*' symlink in .claude/skills" test -z "$(ls -A "$S/.claude/skills" 2>/dev/null)"
check "worktree.sh executable"               test -x "$S/tools/agent/worktree.sh"
check "trunk_edit_guard.sh executable"       test -x "$S/tools/agent/hooks/trunk_edit_guard.sh"
check "CLAUDE.md -> AGENTS.md symlink"        test "$(readlink "$S/CLAUDE.md")" = AGENTS.md
check "CC PreToolUse matcher"                jmatch "$S/.claude/settings.json" PreToolUse "Edit|MultiEdit|Write|NotebookEdit"
check "Codex PreToolUse matcher"             jmatch "$S/.codex/hooks.json"     PreToolUse "Edit|Write|apply_patch"
check ".gitignore ignores .worktrees/"       grep -qx ".worktrees/" "$S/.gitignore"
check ".gitattributes pins LF on scripts"    grep -qF "tools/agent/*.sh text eol=lf" "$S/.gitattributes"

echo "== idempotent re-run =="
( cd "$S" && bash "$H" retrofit ) >/dev/null 2>&1; rc=$?
check "retrofit re-run exits 0"              test "$rc" = 0
check "PostToolUse stays 2 hooks (no dup)"   jcount "$S/.claude/settings.json" PostToolUse 2

echo "== retrofit-merge preserves a pre-existing user hook =="
python3 - "$S/.claude/settings.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["hooks"]["PreToolUse"][0]["hooks"].append({"type": "command", "command": "user-custom.sh"})
json.dump(d, open(p, "w"))
PY
( cd "$S" && bash "$H" retrofit ) >/dev/null 2>&1; rc=$?
check "retrofit-merge exits 0"               test "$rc" = 0
check "trunk_edit_guard still wired"         grep -q trunk_edit_guard "$S/.claude/settings.json"
check "pre-existing user hook preserved"     grep -q user-custom "$S/.claude/settings.json"

echo "== worktree round-trip =="
git -C "$S" add -A && git -C "$S" commit -q -m harness
( cd "$S" && bash tools/agent/worktree.sh new demo --type chore ) >/dev/null 2>&1
check "worktree .worktrees/demo created"     test -d "$S/.worktrees/demo"
( cd "$S/.worktrees/demo" && echo hi > note.txt && git add -A && git commit -q -m "feat: note" \
  && bash tools/agent/worktree.sh "done" --no-push ) >/dev/null 2>&1
check "worktree removed after done"          test ! -d "$S/.worktrees/demo"
git -C "$S" log --oneline | grep -q "Merge branch 'chore/demo'"; rc=$?
check "merge commit landed on main"          test "$rc" = 0

echo "== trunk guard: block on main + escape hatch =="
g="$S/tools/agent/hooks/trunk_edit_guard.sh"
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$S" | CLAUDE_PROJECT_DIR="$S" bash "$g" >/dev/null 2>&1; rc=$?
check "blocks a tracked main edit (exit 2)"  test "$rc" = 2
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$S" | WORKTREE_ALLOW_TRUNK_EDIT=1 CLAUDE_PROJECT_DIR="$S" bash "$g" >/dev/null 2>&1; rc=$?
check "escape hatch allows (exit 0)"         test "$rc" = 0

echo "== relink coexistence with an npx-installed skill =="
mkdir -p "$S/.agents/skills/proj-skill"; printf -- '---\nname: proj-skill\n---\n' > "$S/.agents/skills/proj-skill/SKILL.md"
mkdir -p "$S/.claude/skills/vendor-skill"; echo x > "$S/.claude/skills/vendor-skill/SKILL.md"
( cd "$S" && bash .agents/relink-skills.sh ) >/dev/null 2>&1
check "project skill symlinked into .claude/skills" test -L "$S/.claude/skills/proj-skill"
{ test -d "$S/.claude/skills/vendor-skill" && ! test -L "$S/.claude/skills/vendor-skill"; }; rc=$?
check "npx-installed real dir left untouched" test "$rc" = 0

echo "== relink: Git Bash symlink degradation → convergence =="
# fake ln: -s* COPIES the link-relative target instead of linking (Git Bash w/o winsymlinks)
LNSHIM="$work/lnshim"; mkdir -p "$LNSHIM"
cat > "$LNSHIM/ln" <<'SH'
#!/bin/sh
case "$1" in -s*) shift; t="$1"; l="$2"; rm -rf "$l"; exec cp -RL "$(dirname "$l")/$t" "$l";; esac
exec /usr/bin/ln "$@"
SH
chmod +x "$LNSHIM/ln"
rm -rf "$S/.claude/skills/proj-skill"
( cd "$S" && PATH="$LNSHIM:$PATH" bash .agents/relink-skills.sh ) >/dev/null 2>&1
check "degraded: project skill is a real-dir copy"   is_real_dir "$S/.claude/skills/proj-skill"
check "degraded: vendor-native dir untouched"        is_real_dir "$S/.claude/skills/vendor-skill"
( cd "$S" && bash .agents/relink-skills.sh ) >/dev/null 2>&1   # re-run with real ln
check "converged: project skill back to a symlink"   test -L "$S/.claude/skills/proj-skill"
check "converged: vendor-native dir still untouched" is_real_dir "$S/.claude/skills/vendor-skill"

echo "== verify mode (read-only) =="
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "verify reports harness OK (exit 0)"   test "$rc" = 0

echo "== plan + retrofit migrate a real CLAUDE.md into AGENTS.md =="
M="$work/migrate"; mkdir -p "$M"
git -C "$M" init -q -b main
git -C "$M" config user.email t@t.t; git -C "$M" config user.name tester
git -C "$M" commit -q --allow-empty -m init
printf '# Legacy Contract\n\nHand-written agent rules to keep.\n' > "$M/CLAUDE.md"
git -C "$M" add -A && git -C "$M" commit -q -m "pre-existing CLAUDE.md"
before="$( { find "$M" -type f; find "$M" -type l; } | sort )"
( cd "$M" && bash "$H" plan ) >"$work/plan.out" 2>&1; rc=$?
after="$( { find "$M" -type f; find "$M" -type l; } | sort )"
check "plan exits 0"                          test "$rc" = 0
check "plan makes no filesystem change"       test "$before" = "$after"
check "plan flags the CLAUDE.md migration"    grep -q migrate "$work/plan.out"
( cd "$M" && bash "$H" retrofit ) >/dev/null 2>&1; rc=$?
check "retrofit exits 0"                      test "$rc" = 0
check "AGENTS.md keeps the original prose"    grep -q "Hand-written agent rules to keep" "$M/AGENTS.md"
check "AGENTS.md gains the harness block"     grep -qF "<!-- agent-scaffold:start" "$M/AGENTS.md"
check "CLAUDE.md is now a symlink to AGENTS.md" test "$(readlink "$M/CLAUDE.md")" = AGENTS.md

echo "== retrofit adopts hand-authored subagents into the SSOT (python3, no package.json) =="
A="$work/adopt"; mkdir -p "$A/.claude/agents"
git -C "$A" init -q -b main
git -C "$A" config user.email t@t.t; git -C "$A" config user.name tester
git -C "$A" commit -q --allow-empty -m init
printf -- '---\nname: custom-rev\ndescription: hand-authored reviewer\ntools: Read, Grep\n---\n\nReview the diff and report.\n' > "$A/.claude/agents/custom-rev.md"
git -C "$A" add -A && git -C "$A" commit -q -m "hand-authored subagent"
( cd "$A" && bash "$H" retrofit --no-husky ) >/dev/null 2>&1; rc=$?
check "retrofit exits 0"                          test "$rc" = 0
check "adopted without creating a package.json"   test ! -f "$A/package.json"
check "hand-authored agent adopted into SSOT"     test -f "$A/.agents/subagents/custom-rev/metadata.json"
check "adopted metadata keeps the tools"          grep -q Read "$A/.agents/subagents/custom-rev/metadata.json"
check "CC projection regenerated with banner"     grep -q "do not edit by hand" "$A/.claude/agents/custom-rev.md"
check "Codex projection generated"                test -f "$A/.codex/agents/custom-rev.toml"
( cd "$A" && python3 tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "subagent projections in sync after adopt"  test "$rc" = 0
printf -- '---\nname: ghost\ndescription: no source\n---\n\nbody\n' > "$A/.claude/agents/ghost.md"
( cd "$A" && python3 tools/agent/generate-subagents.py ) >/dev/null 2>&1
check "sourceless hand-authored projection not pruned" test -f "$A/.claude/agents/ghost.md"

echo
if [ "$fails" -eq 0 ]; then echo "OK: agent-scaffold e2e passed"; exit 0; fi
echo "FAIL: $fails agent-scaffold e2e assertion(s) failed"; exit 1
