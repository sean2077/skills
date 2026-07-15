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
# Exit 0 = all runnable assertions passed, 1 = a failure. Needs git + python.
# CI (or AGENT_SCAFFOLD_E2E_REQUIRE_SYMLINKS=1) requires the positive real-link
# suite; an unprivileged local Windows host runs the zero-residue negative suite.
set -uo pipefail

usage() { sed -n '2,11p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "${1:-}" in -h | --help) usage 0 ;; esac

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
H="$repo/skills/agent-scaffold/harness-init.sh"
SM="$repo/skills/agent-scaffold/templates/symlink-manager.py"
[ -f "$H" ] || { echo "installer not found: $H" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git required" >&2; exit 1; }
command -v python >/dev/null 2>&1 || { echo "python required" >&2; exit 1; }

fails=0
ok()  { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; fails=$((fails + 1)); }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
# JSON assertions via python (portable; avoids a jq dependency in CI).
# shellcheck disable=SC2317,SC2329  # run indirectly through check() "$@"; code varies by ShellCheck version
jmatch() { python -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d["hooks"][sys.argv[2]][0]["matcher"]==sys.argv[3] else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329
jcount() { python -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if len(d["hooks"][sys.argv[2]][0]["hooks"])==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329
jcommand_count() { python -c 'import json,re,sys; d=json.load(open(sys.argv[1])); p=re.compile(r"(?:^|[/\s\"\x27;&|()<>])tools/agent/hooks/"+re.escape(sys.argv[2])+r"\.sh(?=$|[\s\"\x27;&|()<>])"); n=sum(bool(p.search(str(h.get("command", "")).replace("\\", "/"))) for groups in d.get("hooks", {}).values() for g in groups for h in g.get("hooks", [])); sys.exit(0 if n==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329
fixed_text_in_both() { grep -qF "$1" "$2" && grep -qF "$1" "$3"; }
# shellcheck disable=SC2317,SC2329
fixed_text_absent_in_both() { ! grep -qF "$1" "$2" && ! grep -qF "$1" "$3"; }
# shellcheck disable=SC2317,SC2329
logical_line_count() { python -c 'import pathlib,sys; lines=pathlib.Path(sys.argv[1]).read_bytes().splitlines(); sys.exit(0 if lines.count(sys.argv[2].encode())==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329  # run indirectly through check() "$@"
is_real_dir() { [ -d "$1" ] && [ ! -L "$1" ]; }
# shellcheck disable=SC2317,SC2329
no_fixed_text() { ! grep -qF "$2" "$1"; }
# shellcheck disable=SC2317,SC2329
no_exact_line() { ! grep -qxF "$2" "$1"; }
# shellcheck disable=SC2317,SC2329
no_partial_harness() {
  local root="$1" path
  for path in AGENTS.md CLAUDE.md .agents .claude .codex tools; do
    [ ! -e "$root/$path" ] && [ ! -L "$root/$path" ] || return 1
  done
}
# shellcheck disable=SC2317,SC2329
no_generated_harness() {
  local root="$1" path
  for path in CLAUDE.md .agents .claude .codex tools; do
    [ ! -e "$root/$path" ] && [ ! -L "$root/$path" ] || return 1
  done
}

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
S="$work/scratch space-雪"; mkdir -p "$S"
git -C "$S" init -q -b main
git -C "$S" config user.email t@t.t; git -C "$S" config user.name tester
git -C "$S" config core.symlinks true
git -C "$S" config core.autocrlf true
git -C "$S" config core.filemode false
git -C "$S" commit -q --allow-empty -m init

echo "== unsupported host: fail before mutation, never copy =="
N="$work/no-links"; mkdir -p "$N"
git -C "$N" init -q -b main
git -C "$N" config user.email t@t.t; git -C "$N" config user.name tester
git -C "$N" config core.symlinks true
git -C "$N" commit -q --allow-empty -m init
( cd "$N" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" init --no-husky ) >/dev/null 2>&1; rc=$?
check "unsupported init exits 2"                    test "$rc" = 2
check "unsupported init leaves no partial harness" no_partial_harness "$N"
( cd "$N" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" init --no-worktree --no-husky ) >/dev/null 2>&1; rc=$?
check "unsupported light init exits 2"              test "$rc" = 2
check "unsupported light init leaves no residue"   no_partial_harness "$N"
before="$( { find "$N" -type f; find "$N" -type l; } | sort )"
( cd "$N" && bash "$H" plan --no-worktree ) >"$work/no-worktree-plan.out" 2>&1; rc=$?
after="$( { find "$N" -type f; find "$N" -type l; } | sort )"
check "no-worktree plan exits 0"                   test "$rc" = 0
check "no-worktree plan makes no change"           test "$before" = "$after"
check "no-worktree plan reports disabled flow"     grep -qF "disabled by --no-worktree" "$work/no-worktree-plan.out"
check "no-worktree plan keeps flag in apply command" grep -qF "retrofit --no-worktree" "$work/no-worktree-plan.out"

echo "== malformed AGENTS markers: fail before mutation =="
B="$work/bad-agents-markers"; mkdir -p "$B"
git -C "$B" init -q -b main
git -C "$B" config user.email t@t.t; git -C "$B" config user.name tester
git -C "$B" config core.symlinks true
printf '# Project contract\n\n<!-- agent-scaffold:start -->\nKEEP-THIS-USER-TAIL\n' > "$B/AGENTS.md"
git -C "$B" add AGENTS.md && git -C "$B" commit -q -m "malformed contract fixture"
agents_before="$(git hash-object "$B/AGENTS.md")"
( cd "$B" && bash "$H" plan ) >"$work/bad-markers-plan.out" 2>&1; rc=$?
check "plan rejects malformed managed markers"       test "$rc" = 2
check "plan explains the malformed marker conflict"  grep -qF "malformed agent-scaffold markers" "$work/bad-markers-plan.out"
check "plan leaves malformed AGENTS.md byte-identical" test "$(git hash-object "$B/AGENTS.md")" = "$agents_before"
( cd "$B" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" upgrade ) >"$work/bad-markers-upgrade.out" 2>&1; rc=$?
check "upgrade rejects malformed markers before doctor" grep -qF "malformed agent-scaffold markers" "$work/bad-markers-upgrade.out"
check "failed upgrade leaves AGENTS.md byte-identical" test "$(git hash-object "$B/AGENTS.md")" = "$agents_before"
check "failed upgrade leaves no partial harness"      no_generated_harness "$B"

python "$SM" doctor --repo "$S" >/dev/null 2>&1; symlink_rc=$?
if [ "$symlink_rc" != 0 ]; then
  if [ "${AGENT_SCAFFOLD_E2E_REQUIRE_SYMLINKS:-${CI:+1}}" = 1 ]; then
    bad "real file/directory symlink capability is required for this run"
  else
    echo "  SKIP positive suite: this host lacks real symlink privilege (run harness-init.sh doctor for remediation)"
  fi
  echo
  if [ "$fails" -eq 0 ]; then echo "OK: agent-scaffold negative e2e passed (positive suite skipped)"; exit 0; fi
  echo "FAIL: $fails agent-scaffold e2e assertion(s) failed"; exit 1
fi

echo "== init (greenfield) =="
# Existing text files need not end with a newline. Every managed append must
# preserve the old record and add the new record on its own line.
printf 'dist' > "$S/.gitignore"
printf '*.txt text' > "$S/.gitattributes"
printf '{"name":"fixture"}\n' > "$S/package.json"
mkdir -p "$S/.husky"
printf '#!/usr/bin/env bash' > "$S/.husky/pre-commit"
( cd "$S" && bash "$H" init ) >/dev/null 2>&1 || bad "init exited nonzero"
check "no bogus '*' symlink in .claude/skills" test -z "$(ls -A "$S/.claude/skills" 2>/dev/null)"
check "worktree.sh installed"                test -f "$S/tools/agent/worktree.sh"
check "trunk_edit_guard.sh installed"        test -f "$S/tools/agent/hooks/trunk_edit_guard.sh"
check "shared hook parser installed"         test -f "$S/tools/agent/hooks/hook-paths.py"
check "CLAUDE.md -> AGENTS.md symlink"        test "$(readlink "$S/CLAUDE.md")" = AGENTS.md
check "CC PreToolUse matcher"                jmatch "$S/.claude/settings.json" PreToolUse "Edit|MultiEdit|Write|NotebookEdit"
check "Codex PreToolUse matcher"             jmatch "$S/.codex/hooks.json"     PreToolUse "Edit|Write|apply_patch"
check "original gitignore line stays separate" grep -qxF "dist" "$S/.gitignore"
check "first gitignore append is separate"     grep -qxF ".claude/settings.local.json" "$S/.gitignore"
check ".gitignore ignores .worktrees/"       grep -qx ".worktrees/" "$S/.gitignore"
check "original attributes line stays separate" grep -qxF "*.txt text" "$S/.gitattributes"
check ".gitattributes pins LF on scripts"    grep -qxF "tools/agent/*.sh text eol=lf" "$S/.gitattributes"
check ".gitattributes pins Husky LF"         grep -qxF ".husky/pre-commit text eol=lf" "$S/.gitattributes"
check "original Husky line stays separate"   grep -qxF "#!/usr/bin/env bash" "$S/.husky/pre-commit"
check "Husky guard append is separate"       grep -qxF "python tools/agent/generate-subagents.py --check" "$S/.husky/pre-commit"
git -C "$S" add -A
# shellcheck disable=SC2016  # sh -c expands its own positional parameters
check "tracked CLAUDE.md mode is 120000"     sh -c '[ "$(git -C "$1" ls-files -s -- CLAUDE.md | awk '\''{print $1}'\'')" = 120000 ]' _ "$S"

echo "== idempotent re-run =="
python - "$S/.gitignore" "$S/.gitattributes" "$S/.husky/pre-commit" <<'PY'
from pathlib import Path
import sys

fixtures = (
    (sys.argv[1], b".claude/settings.local.json\n", b".claude/settings.local.json\r\n"),
    (sys.argv[2], b"tools/agent/*.sh text eol=lf\n", b"tools/agent/*.sh text eol=lf\r\n"),
    (sys.argv[3], b"python tools/agent/generate-subagents.py --check\n", b"python tools/agent/generate-subagents.py --check\r"),
)
for name, old, new in fixtures:
    path = Path(name)
    data = path.read_bytes()
    assert data.count(old) == 1
    path.write_bytes(data.replace(old, new, 1))
PY
( cd "$S" && bash "$H" retrofit ) >/dev/null 2>&1; rc=$?
check "retrofit re-run exits 0"              test "$rc" = 0
check "PostToolUse stays 2 hooks (no dup)"   jcount "$S/.claude/settings.json" PostToolUse 2
check "CRLF gitignore target stays singular" logical_line_count "$S/.gitignore" ".claude/settings.local.json" 1
check "CRLF attributes target stays singular" logical_line_count "$S/.gitattributes" "tools/agent/*.sh text eol=lf" 1
check "CR-only Husky target stays singular" logical_line_count "$S/.husky/pre-commit" "python tools/agent/generate-subagents.py --check" 1

echo "== retrofit-merge preserves a pre-existing user hook =="
python - "$S/.claude/settings.json" <<'PY'
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
merge_subject="$(git -C "$S" log -1 --format=%s)"
check "merge commit landed on main"          test "$merge_subject" = "Merge branch 'chore/demo'"

echo "== trunk guard: block on main + escape hatch =="
g="$S/tools/agent/hooks/trunk_edit_guard.sh"
printf '{"tool_input":{"file_path":"%s/AGENTS.md"}}' "$S" | CLAUDE_PROJECT_DIR="$S" bash "$g" >/dev/null 2>&1; rc=$?
check "blocks a tracked main edit (exit 2)"  test "$rc" = 2
printf '{"tool_input":{"file_path":"%s/AGENTS.md"}}' "$S" | WORKTREE_ALLOW_TRUNK_EDIT=1 CLAUDE_PROJECT_DIR="$S" bash "$g" >/dev/null 2>&1; rc=$?
check "escape hatch allows (exit 0)"         test "$rc" = 0
python -c 'import json,sys; print(json.dumps({"cwd": sys.argv[1], "tool_input": {"file_path": "AGENTS.md"}}))' "$S" \
  | CLAUDE_PROJECT_DIR="$S" bash "$g" >/dev/null 2>&1; rc=$?
check "relative hook path uses payload cwd" test "$rc" = 2
case "$(uname -s)" in
  MINGW* | MSYS*)
    native_root="$(cygpath -w "$S")"
    native_file="$(cygpath -w "$S/AGENTS.md")"
    python -c 'import json,sys; print(json.dumps({"cwd": sys.argv[1], "tool_input": {"file_path": sys.argv[2]}}))' "$native_root" "$native_file" \
      | CLAUDE_PROJECT_DIR="$native_root" bash "$g" >/dev/null 2>&1; rc=$?
    check "native Windows paths remain guarded" test "$rc" = 2
    # Conversion-only coverage for drive, backslash, UNC, and Git Bash forms.
    # shellcheck disable=SC2016  # bash -c expands its own positional parameters
    check "hook runtime converts drive paths" bash -c 'source "$1"; [[ "$(hook_posix_path "C:\\Temp\\x")" == /c/Temp/x ]]' _ "$S/tools/agent/hooks/hook-common.sh"
    # shellcheck disable=SC2016
    check "hook runtime preserves UNC shape" bash -c 'source "$1"; [[ "$(hook_posix_path "\\\\server\\share\\x")" == //server/share/x ]]' _ "$S/tools/agent/hooks/hook-common.sh"
    # shellcheck disable=SC2016
    check "hook runtime accepts Git Bash paths" bash -c 'source "$1"; [[ "$(hook_posix_path "/c/Temp/x")" == /c/Temp/x ]]' _ "$S/tools/agent/hooks/hook-common.sh"
    ;;
esac

echo "== relink coexistence with an npx-installed skill =="
mkdir -p "$S/.agents/skills/proj-skill"; printf -- '---\nname: proj-skill\n---\n' > "$S/.agents/skills/proj-skill/SKILL.md"
mkdir -p "$S/.claude/skills/vendor-skill"; echo x > "$S/.claude/skills/vendor-skill/SKILL.md"
( cd "$S" && bash .agents/relink-skills.sh ) >/dev/null 2>&1
check "project skill symlinked into .claude/skills" test -L "$S/.claude/skills/proj-skill"
{ test -d "$S/.claude/skills/vendor-skill" && ! test -L "$S/.claude/skills/vendor-skill"; }; rc=$?
check "npx-installed real dir left untouched" test "$rc" = 0

echo "== relink: capability loss fails without a copy or vendor mutation =="
rm -rf "$S/.claude/skills/proj-skill"
( cd "$S" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash .agents/relink-skills.sh ) >/dev/null 2>&1; rc=$?
check "capability loss exits 2"                       test "$rc" = 2
check "capability loss leaves no project-skill copy" test ! -e "$S/.claude/skills/proj-skill"
check "capability loss leaves vendor-native dir"     is_real_dir "$S/.claude/skills/vendor-skill"
( cd "$S" && bash .agents/relink-skills.sh ) >/dev/null 2>&1; rc=$?   # idempotent real-link reconciliation
check "recovered: relink exits 0"                         test "$rc" = 0
check "recovered: project skill back to a symlink"   test -L "$S/.claude/skills/proj-skill"
check "recovered: project skill link is not dangling" test -e "$S/.claude/skills/proj-skill"
check "recovered: vendor-native dir still untouched" is_real_dir "$S/.claude/skills/vendor-skill"
git -C "$S" add .claude/skills/proj-skill .agents/skills/proj-skill
# shellcheck disable=SC2016
check "tracked project skill mode is 120000" sh -c '[ "$(git -C "$1" ls-files -s -- .claude/skills/proj-skill | awk '\''{print $1}'\'')" = 120000 ]' _ "$S"
# shellcheck disable=SC2016
check "tracked project skill target stays portable" sh -c '[ "$(git -C "$1" show :.claude/skills/proj-skill)" = ../../.agents/skills/proj-skill ]' _ "$S"

echo "== verify mode (read-only) =="
( cd "$S" && bash "$H" doctor ) >/dev/null 2>&1; rc=$?
check "doctor reports real link capability (exit 0)" test "$rc" = 0
( cd "$S" && bash "$H" verify ) >"$work/verify.out" 2>&1; rc=$?
if [ "$rc" != 0 ]; then
  sed 's/^/  verify> /' "$work/verify.out" >&2
fi
check "verify reports harness OK (exit 0)"   test "$rc" = 0

echo "== verify rejects active-profile drift and hook mismatches =="
( cd "$S" && bash "$H" verify --no-format-hook ) >/dev/null 2>&1; rc=$?
check "verify rejects unexpected format hook" test "$rc" != 0
cp "$S/.claude/settings.json" "$work/claude-settings.clean.json"
cp "$S/.codex/hooks.json" "$work/codex-hooks.clean.json"
python - "$S/.claude/settings.json" "$S/.codex/hooks.json" <<'PY'
import json, sys
for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as source:
        data = json.load(source)
    for event, groups in list(data.get("hooks", {}).items()):
        for group in groups or []:
            group["hooks"] = [
                hook for hook in group.get("hooks", [])
                if "format_on_edit" not in str(hook.get("command", ""))
            ]
    data["hooks"]["PostToolUse"][0]["hooks"].append({
        "type": "command",
        "command": "python scripts/check_format_on_edit_custom.py",
    })
    with open(path, "w", encoding="utf-8") as target:
        json.dump(data, target, indent=2, ensure_ascii=False)
        target.write("\n")
PY
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "verify rejects missing format hook despite lookalike" test "$rc" != 0
( cd "$S" && bash "$H" verify --no-format-hook ) >/dev/null 2>&1; rc=$?
check "disabled format profile ignores user lookalike" test "$rc" = 0
mv "$work/claude-settings.clean.json" "$S/.claude/settings.json"
mv "$work/codex-hooks.clean.json" "$S/.codex/hooks.json"
cp "$S/tools/agent/hooks/format_on_edit.sh" "$work/format-on-edit.clean.sh"
printf '\n# drift fixture\n' >> "$S/tools/agent/hooks/format_on_edit.sh"
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "verify rejects active script drift" test "$rc" != 0
mv "$work/format-on-edit.clean.sh" "$S/tools/agent/hooks/format_on_edit.sh"
cp "$S/tools/agent/generate-subagents.py" "$work/generate-subagents.clean.py"
printf '\n# generator drift fixture\n' >> "$S/tools/agent/generate-subagents.py"
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "verify rejects generator byte drift" test "$rc" != 0
mv "$work/generate-subagents.clean.py" "$S/tools/agent/generate-subagents.py"
mv "$S/tools/agent/generate-subagents.py" "$work/generate-subagents.missing.py"
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "verify rejects missing generator" test "$rc" != 0
mv "$work/generate-subagents.missing.py" "$S/tools/agent/generate-subagents.py"

echo "== lightweight profile: --no-worktree omits the complete worktree policy =="
L="$work/lightweight"; mkdir -p "$L"
git -C "$L" init -q -b main
git -C "$L" config user.email t@t.t; git -C "$L" config user.name tester
git -C "$L" config core.symlinks true
git -C "$L" commit -q --allow-empty -m init
( cd "$L" && bash "$H" init --no-worktree --no-husky --no-example-subagent ) >/dev/null 2>&1; rc=$?
check "no-worktree init exits 0"                 test "$rc" = 0
check "no-worktree omits worktree.sh"            test ! -e "$L/tools/agent/worktree.sh"
check "no-worktree omits trunk guard script"     test ! -e "$L/tools/agent/hooks/trunk_edit_guard.sh"
check "Claude config omits trunk guard"          jcommand_count "$L/.claude/settings.json" trunk_edit_guard 0
check "Codex config omits trunk guard"           jcommand_count "$L/.codex/hooks.json" trunk_edit_guard 0
check "authority hook remains wired"             jcommand_count "$L/.claude/settings.json" authority_doc_budget 1
check "managed AGENTS block omits hard rule"     no_fixed_text "$L/AGENTS.md" "Worktree-per-change (hard rule)"
check "no-worktree omits .worktrees ignore"      no_exact_line "$L/.gitignore" ".worktrees/"
check "no-worktree omits escape-hatch ignore"    no_exact_line "$L/.gitignore" ".claude/allow-trunk-edit"
check "no-worktree keeps the real-link contract" test "$(readlink "$L/CLAUDE.md")" = AGENTS.md
( cd "$L" && bash "$H" verify --no-worktree ) >/dev/null 2>&1; rc=$?
check "no-worktree verify accepts light profile" test "$rc" = 0
( cd "$L" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "default verify detects omitted workflow"  test "$rc" != 0
git -C "$L" add -A && git -C "$L" commit -q -m "light harness"
( cd "$L" && bash "$H" retrofit --no-worktree --no-husky --no-example-subagent ) >/dev/null 2>&1; rc=$?
check "no-worktree retrofit re-run exits 0"       test "$rc" = 0
check "no-worktree retrofit is idempotent"        test -z "$(git -C "$L" status --porcelain)"
( cd "$L" && bash "$H" upgrade --no-husky --no-example-subagent ) >/dev/null 2>&1; rc=$?
check "default upgrade re-enables worktree flow" test "$rc" = 0
check "re-enabled worktree.sh is installed"      test -f "$L/tools/agent/worktree.sh"
check "re-enabled Claude guard is wired once"    jcommand_count "$L/.claude/settings.json" trunk_edit_guard 1
check "re-enabled AGENTS block has hard rule"    grep -qF "Worktree-per-change (hard rule)" "$L/AGENTS.md"

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

echo "== retrofit adopts hand-authored subagents into the SSOT (python, no package.json) =="
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
( cd "$A" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "subagent projections in sync after adopt"  test "$rc" = 0
printf -- '---\nname: ghost\ndescription: no source\n---\n\nbody\n' > "$A/.claude/agents/ghost.md"
( cd "$A" && python tools/agent/generate-subagents.py ) >/dev/null 2>&1
check "sourceless hand-authored projection not pruned" test -f "$A/.claude/agents/ghost.md"

echo "== upgrade reconciles only managed hooks (no jq, no format hook) =="
U="$work/upgrade"; mkdir -p "$U/.claude" "$U/.codex"
git -C "$U" init -q -b main
git -C "$U" config user.email t@t.t; git -C "$U" config user.name tester
git -C "$U" config core.symlinks true
git -C "$U" commit -q --allow-empty -m init
python - "$U/.claude/settings.json" "$U/.codex/hooks.json" <<'PY'
import json, sys
for path, matcher, user in ((sys.argv[1], "Edit", "user-extra.sh"), (sys.argv[2], "apply_patch", "user-cx.sh")):
    value = {"model": "keep-me", "hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [
        {"type": "command", "command": user},
        {"type": "command", "command": "python scripts/check_authority_doc_budget_custom.py"},
        {"type": "command", "command": "bash tools/custom/trunk_edit_guard_backup.sh"},
        {"type": "command", "command": "bash tools/agent/hooks/format_on_edit.sh.backup"},
        {"type": "command", "command": "bash tools/agent/hooks/format_on_edit.sh~"},
        {"type": "command", "command": "bash tools/agent/hooks/format_on_edit.sh+backup"},
        {"type": "command", "command": "bash vendor/@tools/agent/hooks/format_on_edit.sh"},
        {"type": "command", "command": "bash pkg:tools/agent/hooks/format_on_edit.sh"},
        {"type": "command", "command": "bash tools/agent/hooks/format_on_edit.sh"},
        {"type": "command", "command": "bash \\\"tools/agent/hooks/authority_doc_budget.sh\\\""},
        {"type": "command", "command": "(tools/agent/hooks/trunk_edit_guard.sh)"},
        {"type": "command", "command": "bash Tools/Agent/Hooks/format_on_edit.sh"},
        {"type": "command", "command": "old/tools/agent/hooks/trunk_edit_guard.sh"},
    ]}], "PostToolUse": [{"matcher": matcher, "hooks": [
        {"type": "command", "command": "old/tools/agent/hooks/format_on_edit.sh"},
        {"type": "command", "command": "old/tools/agent/hooks/authority_doc_budget.sh"},
    ]}]}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f)
PY
( cd "$U" && HARNESS_NO_JQ=1 bash "$H" upgrade --no-format-hook --no-husky --no-example-subagent ) >/dev/null 2>&1; rc=$?
check "upgrade without jq exits 0"             test "$rc" = 0
check "upgrade preserves Claude user hook"     grep -q user-extra "$U/.claude/settings.json"
check "upgrade preserves Codex user hook"      grep -q user-cx "$U/.codex/hooks.json"
check "upgrade preserves authority lookalikes" fixed_text_in_both check_authority_doc_budget_custom.py "$U/.claude/settings.json" "$U/.codex/hooks.json"
check "upgrade preserves guard lookalikes"     fixed_text_in_both trunk_edit_guard_backup.sh "$U/.claude/settings.json" "$U/.codex/hooks.json"
check "upgrade preserves dotted suffix"        fixed_text_in_both format_on_edit.sh.backup "$U/.claude/settings.json" "$U/.codex/hooks.json"
check "upgrade preserves tilde suffix"         fixed_text_in_both format_on_edit.sh~ "$U/.claude/settings.json" "$U/.codex/hooks.json"
check "upgrade preserves plus suffix"          fixed_text_in_both format_on_edit.sh+backup "$U/.claude/settings.json" "$U/.codex/hooks.json"
check "upgrade preserves at-prefixed segment"  fixed_text_in_both vendor/@tools/agent/hooks/format_on_edit.sh "$U/.claude/settings.json" "$U/.codex/hooks.json"
check "upgrade preserves colon-prefixed path"  fixed_text_in_both pkg:tools/agent/hooks/format_on_edit.sh "$U/.claude/settings.json" "$U/.codex/hooks.json"
if [ -e "$U/Tools/Agent/Hooks/format_on_edit.sh" ]; then
  check "case-equivalent managed path is removed" fixed_text_absent_in_both Tools/Agent/Hooks/format_on_edit.sh "$U/.claude/settings.json" "$U/.codex/hooks.json"
else
  check "case-distinct user path is preserved" fixed_text_in_both Tools/Agent/Hooks/format_on_edit.sh "$U/.claude/settings.json" "$U/.codex/hooks.json"
fi
check "upgrade preserves unrelated config"     grep -q keep-me "$U/.claude/settings.json"
check "--no-format-hook removes Claude managed format" jcommand_count "$U/.claude/settings.json" format_on_edit 0
check "--no-format-hook removes Codex managed format"  jcommand_count "$U/.codex/hooks.json" format_on_edit 0
check "Claude trunk guard appears once"        jcommand_count "$U/.claude/settings.json" trunk_edit_guard 1
check "Codex authority hook appears once"       jcommand_count "$U/.codex/hooks.json" authority_doc_budget 1
( cd "$U" && HARNESS_NO_JQ=1 bash "$H" upgrade --no-worktree --no-format-hook --no-husky --no-example-subagent ) >/dev/null 2>&1; rc=$?
check "default-to-light upgrade exits 0"         test "$rc" = 0
check "light upgrade preserves Claude user hook" grep -q user-extra "$U/.claude/settings.json"
check "light upgrade preserves Codex user hook"  grep -q user-cx "$U/.codex/hooks.json"
check "light upgrade removes Claude guard"       jcommand_count "$U/.claude/settings.json" trunk_edit_guard 0
check "light upgrade removes Codex guard"        jcommand_count "$U/.codex/hooks.json" trunk_edit_guard 0
check "light upgrade keeps authority hook"       jcommand_count "$U/.codex/hooks.json" authority_doc_budget 1
check "light upgrade removes managed hard rule"  no_fixed_text "$U/AGENTS.md" "Worktree-per-change (hard rule)"
check "light upgrade preserves dormant script"   test -f "$U/tools/agent/worktree.sh"
check "light upgrade preserves existing worktree ignore" grep -qxF ".worktrees/" "$U/.gitignore"
check "light upgrade preserves existing escape ignore"   grep -qxF ".claude/allow-trunk-edit" "$U/.gitignore"
( cd "$U" && bash "$H" verify --no-worktree --no-format-hook ) >/dev/null 2>&1; rc=$?
check "light upgrade verifies with matching flags" test "$rc" = 0
printf '\n# dormant drift fixture\n' >> "$U/tools/agent/worktree.sh"
( cd "$U" && bash "$H" verify --no-worktree --no-format-hook ) >/dev/null 2>&1; rc=$?
check "light verify ignores dormant worktree script drift" test "$rc" = 0

echo "== hardening: deep-review regression fixes =="
# PY_MERGE: retrofit over an existing config whose "hooks" is null must not crash on
# the python path (jq coped via // {}) and must preserve the user's other keys.
HN="$work/hooksnull"; mkdir -p "$HN/.claude"
git -C "$HN" init -q -b main
git -C "$HN" config user.email t@t.t; git -C "$HN" config user.name tester
git -C "$HN" commit -q --allow-empty -m init
printf '{"hooks": null, "model": "opus"}' > "$HN/.claude/settings.json"
( cd "$HN" && HARNESS_NO_JQ=1 bash "$H" retrofit --no-husky ) >/dev/null 2>&1; rc=$?
check "retrofit over hooks:null (python path) exits 0"   test "$rc" = 0
check "hooks:null retrofit preserves user's other keys"  grep -q '"model"' "$HN/.claude/settings.json"
check "hooks:null retrofit wires the trunk guard"        grep -q trunk_edit_guard "$HN/.claude/settings.json"

# M3: a hand-authored agent whose PROSE contains the phrase "do not edit by hand"
# must still be adopted by --import (the banner test keys on "Generated from
# .agents/subagents/", not the loose phrase). Reuses the adopt repo $A.
printf -- '---\nname: phrase-rev\ndescription: mentions the banner phrase\n---\n\nRule: do not edit by hand-written config.\n' > "$A/.claude/agents/phrase-rev.md"
( cd "$A" && python tools/agent/generate-subagents.py --import ) >/dev/null 2>&1
check "hand-authored agent w/ banner phrase in prose still adopted (M3)" test -f "$A/.agents/subagents/phrase-rev/metadata.json"

# M1: metadata.json without a non-empty description must fail fast, not emit "None".
DN="$work/nodesc"; mkdir -p "$DN/.agents/subagents/x" "$DN/tools/agent"
cp "$repo/tools/agent/generate-subagents.py" "$DN/tools/agent/generate-subagents.py"
printf '{"name":"x"}' > "$DN/.agents/subagents/x/metadata.json"
printf 'body\n' > "$DN/.agents/subagents/x/instructions.md"
( cd "$DN" && python tools/agent/generate-subagents.py ) >/dev/null 2>&1; rc=$?
check "metadata without description fails fast (M1)"     test "$rc" != 0

# m1: malformed metadata.json gives a friendly, named error — no raw python traceback.
MJ="$work/badjson"; mkdir -p "$MJ/.agents/subagents/y" "$MJ/tools/agent"
cp "$repo/tools/agent/generate-subagents.py" "$MJ/tools/agent/generate-subagents.py"
printf '{not json' > "$MJ/.agents/subagents/y/metadata.json"
printf 'body\n' > "$MJ/.agents/subagents/y/instructions.md"
( cd "$MJ" && python tools/agent/generate-subagents.py ) >"$work/badjson.out" 2>&1; rc=$?
check "malformed metadata.json exits nonzero (m1)"       test "$rc" != 0
check "malformed metadata.json names subagent + reason (m1)" grep -qF "subagent 'y': metadata.json is not valid JSON" "$work/badjson.out"
# shellcheck disable=SC2016  # $1 is sh -c's own positional; the outer shell must NOT expand it
check "malformed metadata.json prints no python traceback (m1)" sh -c '! grep -q Traceback "$1"' _ "$work/badjson.out"

echo
if [ "$fails" -eq 0 ]; then echo "OK: agent-scaffold e2e passed"; exit 0; fi
echo "FAIL: $fails agent-scaffold e2e assertion(s) failed"; exit 1
