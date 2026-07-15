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
both_absent() { [ ! -e "$1" ] && [ ! -e "$2" ]; }
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

echo "== Python 3.8+ runtime candidates are probed before selection =="
real_python="$(command -v python)"
resolver_bin="$work/python resolver bin"; mkdir -p "$resolver_bin"
cat > "$resolver_bin/python-shim" <<'SH'
#!/usr/bin/env bash
candidate="${0##*/}"
case "$candidate" in
  explicit-python|"explicit python") mode="${RESOLVER_EXPLICIT_MODE:-py38}" ;;
  python)                              mode="${RESOLVER_PYTHON_MODE:-py38}" ;;
  python3)                             mode="${RESOLVER_PYTHON3_MODE:-py38}" ;;
  py)                                  mode="${RESOLVER_PY_MODE:-py38}" ;;
  *)                                   exit 99 ;;
esac
if [[ "$candidate" == py ]]; then
  [[ "${1:-}" == -3 ]] || exit 71
  shift
fi
kind=exec
if [[ "${1:-}" == -c && "${2:-}" == *version_info* ]]; then
  kind=probe
fi
printf '%s:%s\n' "$candidate" "$kind" >> "${PYTHON_RESOLVER_LOG:?}"
case "$mode" in
  py37|py38)
    if [[ "${1:-}" == -c ]]; then
      code="${2:-}"; shift 2
      [[ "$mode" == py37 ]] && minor=7 || minor=8
      exec "${REAL_PYTHON:?}" -c '
import collections
import sys

major = int(sys.argv.pop(1))
minor = int(sys.argv.pop(1))
code = sys.argv.pop(1)
version_info = collections.namedtuple(
    "version_info", "major minor micro releaselevel serial"
)
sys.version_info = version_info(major, minor, 0, "final", 0)
exec(compile(code, "<resolver-shim>", "exec"))
' 3 "$minor" "$code" "$@"
    fi
    exec "${REAL_PYTHON:?}" "$@"
    ;;
  broken) exit 70 ;;
  *)      exit 98 ;;
esac
SH
for candidate in explicit-python "explicit python" python python3 py; do
  cp "$resolver_bin/python-shim" "$resolver_bin/$candidate"
  chmod +x "$resolver_bin/$candidate"
done
resolver_path="$resolver_bin:$PATH"

resolver_log="$work/python-version-fixture.log"; : > "$resolver_log"
PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
  RESOLVER_PYTHON_MODE=py37 python -c \
  'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 7) else 1)'; rc=$?
check "resolver fixture simulates Python 3.7" test "$rc" = 0
PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
  RESOLVER_PYTHON3_MODE=py38 python3 -c \
  'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 8) else 1)'; rc=$?
check "resolver fixture simulates the supported Python 3.8 boundary" test "$rc" = 0

resolver_log="$work/harness-python3-fallback.log"; : > "$resolver_log"
(
  cd "$N" || exit 1
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=broken \
    RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=py38 RESOLVER_PY_MODE=broken \
    bash "$H" verify --no-worktree
) >/dev/null 2>&1; rc=$?
check "harness falls through broken and old candidates" test "$rc" = 1
check "harness probes candidates in documented order" test \
  "$(sed -n '1,3p' "$resolver_log")" = \
  "$(printf '%s\n' explicit-python:probe python:probe python3:probe)"
check "harness executes the selected python3" grep -qxF python3:exec "$resolver_log"

resolver_log="$work/harness-swapped-python3-fallback.log"; : > "$resolver_log"
(
  cd "$N" || exit 1
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=py37 \
    RESOLVER_PYTHON_MODE=broken RESOLVER_PYTHON3_MODE=py38 RESOLVER_PY_MODE=broken \
    bash "$H" verify --no-worktree
) >/dev/null 2>&1; rc=$?
check "harness falls through old and broken candidates" test "$rc" = 1
check "harness probes swapped failures in documented order" test \
  "$(sed -n '1,3p' "$resolver_log")" = \
  "$(printf '%s\n' explicit-python:probe python:probe python3:probe)"
check "harness executes python3 after swapped failures" grep -qxF python3:exec "$resolver_log"

resolver_log="$work/harness-py-fallback.log"; : > "$resolver_log"
(
  cd "$N" || exit 1
  unset PYTHON_BIN
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=broken RESOLVER_PY_MODE=py38 \
    bash "$H" verify --no-worktree
) >/dev/null 2>&1; rc=$?
check "harness reaches the Windows launcher candidate" test "$rc" = 1
check "harness preserves the py -3 candidate order" test \
  "$(sed -n '1,3p' "$resolver_log")" = "$(printf '%s\n' python:probe python3:probe py:probe)"
check "harness executes the selected py -3 launcher" grep -qxF py:exec "$resolver_log"

resolver_log="$work/harness-explicit-precedence.log"; : > "$resolver_log"
(
  cd "$N" || exit 1
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit python" RESOLVER_EXPLICIT_MODE=py38 \
    RESOLVER_PYTHON_MODE=broken RESOLVER_PYTHON3_MODE=broken RESOLVER_PY_MODE=broken \
    bash "$H" verify --no-worktree
) >/dev/null 2>&1; rc=$?
check "compatible explicit interpreter keeps precedence" test "$rc" = 1
check "explicit interpreter path with spaces is probed" grep -qxF "explicit python:probe" "$resolver_log"
check "explicit interpreter path with spaces is executed" grep -qxF "explicit python:exec" "$resolver_log"
check "lower-priority candidates stay untouched" test -z "$(grep -v '^explicit python:' "$resolver_log" || true)"

resolver_log="$work/harness-no-python.log"; : > "$resolver_log"
(
  cd "$N" || exit 1
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=broken \
    RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=broken RESOLVER_PY_MODE=py37 \
    bash "$H" plan --no-worktree
) >"$work/harness-no-python.out" 2>&1; rc=$?
check "harness rejects an entirely incompatible candidate set" test "$rc" = 2
check "harness names its Python version prerequisite" grep -qF "python 3.8+ is required" "$work/harness-no-python.out"

R="$work/relink-python-fallback"; mkdir -p "$R/.agents"
cp "$repo/skills/agent-scaffold/templates/relink-skills.sh" "$R/.agents/relink-skills.sh"
printf '%s\n' \
  'from pathlib import Path' \
  'Path(__file__).with_name("manager-ran").write_text("ok", encoding="utf-8")' \
  > "$R/.agents/symlink-manager.py"
resolver_log="$work/relink-python3-fallback.log"; : > "$resolver_log"
(
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=broken \
    RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=py38 RESOLVER_PY_MODE=broken \
    bash "$R/.agents/relink-skills.sh"
) >"$work/relink-python3-fallback.out" 2>&1; rc=$?
check "relink falls through to a compatible python3" test "$rc" = 0
check "relink probes candidates in documented order" test \
  "$(sed -n '1,3p' "$resolver_log")" = \
  "$(printf '%s\n' explicit-python:probe python:probe python3:probe)"
check "relink runs its manager through python3" grep -qxF python3:exec "$resolver_log"
check "relink manager reaches its entry point" test -f "$R/.agents/manager-ran"

resolver_log="$work/relink-no-python.log"; : > "$resolver_log"
(
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=broken \
    RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=broken RESOLVER_PY_MODE=py37 \
    bash "$R/.agents/relink-skills.sh"
) >"$work/relink-no-python.out" 2>&1; rc=$?
check "relink rejects an entirely incompatible candidate set" test "$rc" = 2
check "relink names its Python version prerequisite" grep -qF "python 3.8+ is required" "$work/relink-no-python.out"

resolver_log="$work/hook-python3-fallback.log"; : > "$resolver_log"
# shellcheck disable=SC2016  # bash -c expands its own positional parameters
hook_python="$({
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=broken \
    RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=py38 RESOLVER_PY_MODE=broken \
    bash -c 'source "$1"; hook_resolve_python; printf "%s\n" "${HOOK_PYTHON[*]}"' \
      _ "$repo/skills/agent-scaffold/templates/hook-common.sh"
} 2>/dev/null)"; rc=$?
check "hook resolver falls through to python3" test "$rc" = 0
check "hook resolver selects python3" test "$hook_python" = python3
check "hook resolver probes candidates in documented order" test \
  "$(sed -n '1,3p' "$resolver_log")" = \
  "$(printf '%s\n' explicit-python:probe python:probe python3:probe)"

cat > "$resolver_bin/jq" <<'SH'
#!/usr/bin/env bash
printf '%s\n' jq >> "${PYTHON_RESOLVER_LOG:?}"
printf '/fixture/AGENTS.md\n'
SH
chmod +x "$resolver_bin/jq"
resolver_log="$work/hook-jq-fallback.log"; : > "$resolver_log"
# shellcheck disable=SC2016  # bash -c expands its own positional parameters
hook_paths="$({
  PATH="$resolver_path" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
    PYTHON_BIN="$resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=broken \
    RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=broken RESOLVER_PY_MODE=py37 \
    bash -c 'source "$1"; hook_extract_paths "$2"' _ \
      "$repo/skills/agent-scaffold/templates/hook-common.sh" \
      '{"tool_input":{"file_path":"ignored"}}'
} 2>/dev/null)"; rc=$?
check "hook path extraction remains fail-open" test "$rc" = 0
check "hook uses jq when every Python candidate is incompatible" grep -qxF jq "$resolver_log"
check "jq fallback returns the extracted path" test "$hook_paths" = /fixture/AGENTS.md

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

echo "== invalid hook configs: fail before capability probe or mutation =="
for fixture in claude-syntax codex-root codex-hooks claude-command codex-constant codex-overflow claude-surrogate; do
  J="$work/invalid-$fixture-hooks"; mkdir -p "$J"
  git -C "$J" init -q -b main
  git -C "$J" config user.email t@t.t; git -C "$J" config user.name tester
  git -C "$J" config core.symlinks true
  case "$fixture" in
    claude-syntax)
      rel=.claude/settings.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.claude"; printf '{"hooks":' > "$J/$rel"
      ;;
    codex-root)
      rel=.codex/hooks.json; expected="$rel: top level must be a JSON object"
      mkdir -p "$J/.codex"; printf '[]\n' > "$J/$rel"
      ;;
    codex-hooks)
      rel=.codex/hooks.json; expected="$rel: hooks must be a JSON object or null"
      mkdir -p "$J/.codex"; printf '{"hooks":[]}\n' > "$J/$rel"
      ;;
    claude-command)
      rel=.claude/settings.json
      expected="$rel: hooks.PreToolUse[0].hooks[0].command must be a string"
      mkdir -p "$J/.claude"
      printf '%s\n' '{"hooks":{"PreToolUse":[{"matcher":"Edit|MultiEdit|Write|NotebookEdit","hooks":[{"type":"command","command":[]}]}]}}' > "$J/$rel"
      ;;
    codex-constant)
      rel=.codex/hooks.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.codex"; printf '{"model":NaN}\n' > "$J/$rel"
      ;;
    codex-overflow)
      rel=.codex/hooks.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.codex"; printf '{"model":1e9999}\n' > "$J/$rel"
      ;;
    claude-surrogate)
      rel=.claude/settings.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.claude"; printf '%s\n' '{"label":"\ud800"}' > "$J/$rel"
      ;;
  esac
  git -C "$J" add "$rel" && git -C "$J" commit -q -m "invalid $fixture hook fixture"
  (
    cd "$J" || exit 1
    AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" retrofit --no-husky
  ) >"$work/invalid-$fixture-hooks.out" 2>&1; rc=$?
  check "$fixture invalid hook config exits 2"              test "$rc" = 2
  check "$fixture invalid hook config names the error"      grep -qF "$expected" "$work/invalid-$fixture-hooks.out"
  check "$fixture invalid hook config prints no traceback"  no_fixed_text "$work/invalid-$fixture-hooks.out" "Traceback"
  check "$fixture invalid hook config stops before doctor"  no_fixed_text "$work/invalid-$fixture-hooks.out" "symlink capability denied by the test fixture"
  check "$fixture invalid hook config leaves repo unchanged" test -z "$(git -C "$J" status --porcelain --untracked-files=all)"
done

J="$work/invalid-nested-hooks"; mkdir -p "$J/.claude"
git -C "$J" init -q -b main
git -C "$J" config user.email t@t.t; git -C "$J" config user.name tester
git -C "$J" config core.symlinks true
printf '%s\n' '{"hooks":{"PreToolUse":[{"matcher":"x","hooks":"bad"}]}}' > "$J/.claude/settings.json"
git -C "$J" add .claude/settings.json && git -C "$J" commit -q -m "invalid nested hook fixture"
(
  cd "$J" || exit 1
  AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" retrofit --no-husky
) >"$work/invalid-nested-hooks.out" 2>&1; rc=$?
check "nested invalid hook config exits 2"              test "$rc" = 2
check "nested invalid hook config names the field"      grep -qF ".claude/settings.json: hooks.PreToolUse[0].hooks must be an array" "$work/invalid-nested-hooks.out"
check "nested invalid hook config prints no traceback"  no_fixed_text "$work/invalid-nested-hooks.out" "Traceback"
check "nested invalid hook config stops before doctor"  no_fixed_text "$work/invalid-nested-hooks.out" "symlink capability denied by the test fixture"
check "nested invalid hook config leaves repo unchanged" test -z "$(git -C "$J" status --porcelain --untracked-files=all)"

J="$work/valid-unicode-hooks"; mkdir -p "$J/.claude"
git -C "$J" init -q -b main
git -C "$J" config user.email t@t.t; git -C "$J" config user.name tester
git -C "$J" config core.symlinks true
printf '%s\n' '{"label":"\ud83d\ude00","hooks":null}' > "$J/.claude/settings.json"
git -C "$J" add .claude/settings.json && git -C "$J" commit -q -m "valid Unicode hook fixture"
(
  cd "$J" || exit 1
  AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" retrofit --no-husky
) >"$work/valid-unicode-hooks.out" 2>&1; rc=$?
check "valid Unicode pair reaches capability probe" test "$rc" = 2
check "valid Unicode pair is not rejected as JSON" no_fixed_text "$work/valid-unicode-hooks.out" "invalid JSON"
check "valid Unicode pair preserves hooks:null compatibility" grep -qF "symlink capability denied by the test fixture" "$work/valid-unicode-hooks.out"
check "valid Unicode fixture leaves repo unchanged" test -z "$(git -C "$J" status --porcelain --untracked-files=all)"

echo "== generated ownership requires the canonical marker, not prose =="
P="$work/provenance-phrase"; mkdir -p "$P/.claude/agents" "$P/.codex/agents" "$P/tools/agent"
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
printf -- '---\nname: phrase-claude\ndescription: hand-authored Claude agent\n---\n\nThis prose discusses Generated from .agents/subagents/ without claiming ownership.\nCLAUDE_PROSE_SENTINEL\n' > "$P/.claude/agents/phrase-claude.md"
printf '%s\n' \
  'name = "phrase-codex"' \
  'description = "hand-authored Codex agent"' \
  "developer_instructions = '''" \
  'This prose discusses Generated from .agents/subagents/ without claiming ownership.' \
  'CODEX_PROSE_SENTINEL' \
  "'''" > "$P/.codex/agents/phrase-codex.toml"
( cd "$P" && bash "$H" plan ) >"$work/provenance-plan.out" 2>&1; rc=$?
check "provenance plan exits 0"                    test "$rc" = 0
check "plan lists Claude prose file for adoption" grep -qF "subagent phrase-claude" "$work/provenance-plan.out"
check "plan lists Codex prose file for adoption"  grep -qF "subagent phrase-codex" "$work/provenance-plan.out"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
( cd "$P" && python tools/agent/generate-subagents.py --import ) >"$work/provenance-import.out" 2>&1; rc=$?
check "provenance import exits 0"                 test "$rc" = 0
check "Claude prose file is adopted into SSOT"   test -f "$P/.agents/subagents/phrase-claude/metadata.json"
check "Codex prose file is adopted into SSOT"    test -f "$P/.agents/subagents/phrase-codex/metadata.json"
check "Claude SSOT preserves prose"               grep -qF CLAUDE_PROSE_SENTINEL "$P/.agents/subagents/phrase-claude/instructions.md"
check "Codex SSOT preserves prose"                grep -qF CODEX_PROSE_SENTINEL "$P/.agents/subagents/phrase-codex/instructions.md"
check "Claude projection keeps prose"             grep -qF CLAUDE_PROSE_SENTINEL "$P/.claude/agents/phrase-claude.md"
check "Codex projection keeps prose"              grep -qF CODEX_PROSE_SENTINEL "$P/.codex/agents/phrase-codex.toml"
( cd "$P" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "provenance projections are in sync"        test "$rc" = 0
rm -rf "$P/.agents"
python - "$P/.claude/agents/phrase-claude.md" "$P/.codex/agents/phrase-codex.toml" <<'PY'
from pathlib import Path
import sys

for name in sys.argv[1:]:
    path = Path(name)
    data = path.read_bytes()
    assert b"\r" not in data
    path.write_bytes(data.replace(b"\n", b"\r\n"))
PY
( cd "$P" && bash "$H" plan ) >"$work/provenance-crlf-plan.out" 2>&1; rc=$?
check "CRLF provenance plan exits 0"               test "$rc" = 0
check "plan recognizes canonical CRLF projections" no_fixed_text "$work/provenance-crlf-plan.out" "subagent phrase-"

echo "== divergent dual-host instructions fail before adoption =="
D="$work/divergent-hosts"; mkdir -p "$D/.claude/agents" "$D/.codex/agents" "$D/tools/agent"
printf -- '---\nname: alpha\ndescription: Claude-only control\n---\n\nALPHA_INSTRUCTIONS\n' > "$D/.claude/agents/alpha.md"
printf -- '---\nname: dual\ndescription: shared description\n---\n\nCLAUDE_ONLY_INSTRUCTIONS\n' > "$D/.claude/agents/dual.md"
printf '%s\n' \
  'name = "dual"' \
  'description = "shared description"' \
  "developer_instructions = '''" \
  'CODEX_ONLY_INSTRUCTIONS' \
  "'''" > "$D/.codex/agents/dual.toml"
cp "$repo/tools/agent/generate-subagents.py" "$D/tools/agent/generate-subagents.py"
alpha_before="$(git hash-object "$D/.claude/agents/alpha.md")"
claude_before="$(git hash-object "$D/.claude/agents/dual.md")"
codex_before="$(git hash-object "$D/.codex/agents/dual.toml")"
( cd "$D" && python tools/agent/generate-subagents.py --import ) >"$work/divergent-import.out" 2>&1; rc=$?
check "divergent import exits nonzero"             test "$rc" != 0
check "divergent import explains the conflict"     grep -qF "subagent 'dual': .claude/agents/dual.md and .codex/agents/dual.toml have different instructions" "$work/divergent-import.out"
check "conflict preserves earlier Claude input"    test "$(git hash-object "$D/.claude/agents/alpha.md")" = "$alpha_before"
check "conflict preserves dual Claude input"       test "$(git hash-object "$D/.claude/agents/dual.md")" = "$claude_before"
check "conflict preserves dual Codex input"        test "$(git hash-object "$D/.codex/agents/dual.toml")" = "$codex_before"
check "conflict writes no SSOT sources"            test ! -e "$D/.agents"

Q="$work/matching-hosts"; mkdir -p "$Q/.claude/agents" "$Q/.codex/agents" "$Q/tools/agent"
printf -- '---\nname: matching\ndescription: shared description\n---\n\nMATCHING_INSTRUCTIONS' > "$Q/.claude/agents/matching.md"
printf '%s\n' \
  'name = "matching"' \
  'description = "shared description"' \
  "developer_instructions = '''" \
  'MATCHING_INSTRUCTIONS' \
  "'''" > "$Q/.codex/agents/matching.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Q/tools/agent/generate-subagents.py"
( cd "$Q" && python tools/agent/generate-subagents.py --import ) >"$work/matching-import.out" 2>&1; rc=$?
check "matching dual-host import exits 0"           test "$rc" = 0
check "matching dual-host import creates SSOT"      grep -qF MATCHING_INSTRUCTIONS "$Q/.agents/subagents/matching/instructions.md"
( cd "$Q" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "matching dual-host projections are in sync" test "$rc" = 0

echo "== hand-authored import is lossless or fails before writing =="
U="$work/unparseable-host"; mkdir -p "$U/.claude/agents" "$U/.codex/agents" "$U/tools/agent"
printf -- '---\nname: alpha\ndescription: valid earlier candidate\n---\n\nALPHA_BEFORE_PARSE_FAILURE\n' > "$U/.claude/agents/alpha.md"
printf 'BROKEN_CLAUDE_SENTINEL\n' > "$U/.claude/agents/broken.md"
printf '%s\n' \
  'name = "broken"' \
  'description = "valid Codex counterpart"' \
  'developer_instructions = """' \
  'CODEX_COUNTERPART_SENTINEL' \
  '"""' > "$U/.codex/agents/broken.toml"
cp "$repo/tools/agent/generate-subagents.py" "$U/tools/agent/generate-subagents.py"
broken_claude_before="$(git hash-object "$U/.claude/agents/broken.md")"
broken_codex_before="$(git hash-object "$U/.codex/agents/broken.toml")"
( cd "$U" && python tools/agent/generate-subagents.py --import ) >"$work/unparseable-import.out" 2>&1; rc=$?
check "unparseable host import exits nonzero"       test "$rc" != 0
check "unparseable host names the rejected file"    grep -qF "cannot parse .claude/agents/broken.md as a Claude agent" "$work/unparseable-import.out"
check "unparseable Claude input stays byte-identical" test "$(git hash-object "$U/.claude/agents/broken.md")" = "$broken_claude_before"
check "unparseable Codex input stays byte-identical" test "$(git hash-object "$U/.codex/agents/broken.toml")" = "$broken_codex_before"
check "parse failure writes no SSOT sources"        test ! -e "$U/.agents"

M="$work/missing-import-metadata"; mkdir -p "$M/.claude/agents" "$M/.codex/agents" "$M/tools/agent"
printf -- '---\nname: alpha\ndescription: valid earlier candidate\n---\n\nALPHA_BEFORE_METADATA_FAILURE\n' > "$M/.claude/agents/alpha.md"
printf -- '---\nname: meta\ndescription:\n---\n\nMATCHING_METADATA_INSTRUCTIONS\n' > "$M/.claude/agents/meta.md"
printf '%s\n' \
  'name = "meta"' \
  'description = ""' \
  'developer_instructions = """' \
  'MATCHING_METADATA_INSTRUCTIONS' \
  '"""' > "$M/.codex/agents/meta.toml"
cp "$repo/tools/agent/generate-subagents.py" "$M/tools/agent/generate-subagents.py"
( cd "$M" && python tools/agent/generate-subagents.py --import ) >"$work/missing-import-metadata.out" 2>&1; rc=$?
check "missing import metadata exits nonzero"       test "$rc" != 0
check "missing import metadata explains the field" grep -qF "subagent 'meta': metadata.json needs a non-empty description" "$work/missing-import-metadata.out"
check "metadata failure writes no SSOT sources"     test ! -e "$M/.agents"

T="$work/codex-basic-multiline"; mkdir -p "$T/.codex/agents" "$T/tools/agent"
printf '%s\n' \
  'name = "basic-multiline"' \
  'description = "official basic multiline form"' \
  'developer_instructions = """' \
  'CODEX_BASIC_MULTILINE_SENTINEL' \
  '"""' > "$T/.codex/agents/basic-multiline.toml"
cp "$repo/tools/agent/generate-subagents.py" "$T/tools/agent/generate-subagents.py"
( cd "$T" && python tools/agent/generate-subagents.py --import ) >"$work/basic-multiline-import.out" 2>&1; rc=$?
check "Codex basic multiline import exits 0"        test "$rc" = 0
check "Codex basic multiline prompt is preserved"  grep -qF CODEX_BASIC_MULTILINE_SENTINEL "$T/.agents/subagents/basic-multiline/instructions.md"
( cd "$T" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "Codex basic multiline projection is in sync" test "$rc" = 0

F="$work/unsupported-host-fields"; mkdir -p "$F/.claude/agents" "$F/tools/agent"
printf -- '---\nname: rich-claude\ndescription: unsupported Claude metadata\nmemory: project\n---\n\nRICH_CLAUDE_SENTINEL\n' > "$F/.claude/agents/rich-claude.md"
cp "$repo/tools/agent/generate-subagents.py" "$F/tools/agent/generate-subagents.py"
( cd "$F" && python tools/agent/generate-subagents.py --import ) >"$work/unsupported-claude-import.out" 2>&1; rc=$?
check "unsupported Claude metadata exits nonzero"   test "$rc" != 0
check "unsupported Claude metadata names the field" grep -qF "unsupported Claude field 'memory'" "$work/unsupported-claude-import.out"
check "unsupported Claude metadata writes no SSOT" test ! -e "$F/.agents"

F="$work/unsupported-codex-fields"; mkdir -p "$F/.codex/agents" "$F/tools/agent"
printf '%s\n' \
  'name = "rich-codex"' \
  'description = "unsupported Codex metadata"' \
  'developer_instructions = """' \
  'RICH_CODEX_SENTINEL' \
  '"""' \
  '[mcp_servers.docs]' \
  'command = "docs-server"' > "$F/.codex/agents/rich-codex.toml"
cp "$repo/tools/agent/generate-subagents.py" "$F/tools/agent/generate-subagents.py"
( cd "$F" && python tools/agent/generate-subagents.py --import ) >"$work/unsupported-codex-import.out" 2>&1; rc=$?
check "unsupported Codex metadata exits nonzero"    test "$rc" != 0
check "unsupported Codex metadata names the field" grep -qF "unsupported Codex field 'mcp_servers.docs'" "$work/unsupported-codex-import.out"
check "unsupported Codex metadata writes no SSOT"  test ! -e "$F/.agents"

N="$work/host-identity-conflict"; mkdir -p "$N/.codex/agents" "$N/tools/agent"
printf '%s\n' \
  'name = "declared-name"' \
  'description = "name differs from the filename"' \
  "developer_instructions = '''" \
  'NAME_CONFLICT_SENTINEL' \
  "'''" > "$N/.codex/agents/filename-name.toml"
cp "$repo/tools/agent/generate-subagents.py" "$N/tools/agent/generate-subagents.py"
( cd "$N" && python tools/agent/generate-subagents.py --import ) >"$work/identity-conflict-import.out" 2>&1; rc=$?
check "host identity conflict exits nonzero"        test "$rc" != 0
check "host identity conflict explains the mismatch" grep -qF "declares name 'declared-name'; rename it to filename-name.toml before --import" "$work/identity-conflict-import.out"
check "host identity conflict writes no SSOT"       test ! -e "$N/.agents"

V="$work/description-conflict"; mkdir -p "$V/.claude/agents" "$V/.codex/agents" "$V/tools/agent"
printf -- '---\nname: description-conflict\ndescription: Claude description\n---\n\nSHARED_DESCRIPTION_INSTRUCTIONS\n' > "$V/.claude/agents/description-conflict.md"
printf '%s\n' \
  'name = "description-conflict"' \
  'description = "Codex description"' \
  "developer_instructions = '''" \
  'SHARED_DESCRIPTION_INSTRUCTIONS' \
  "'''" > "$V/.codex/agents/description-conflict.toml"
cp "$repo/tools/agent/generate-subagents.py" "$V/tools/agent/generate-subagents.py"
( cd "$V" && python tools/agent/generate-subagents.py --import ) >"$work/description-conflict-import.out" 2>&1; rc=$?
check "description conflict exits nonzero"          test "$rc" != 0
check "description conflict explains the mismatch" grep -qF "different descriptions; resolve the conflict before --import" "$work/description-conflict-import.out"
check "description conflict writes no SSOT"        test ! -e "$V/.agents"

I="$work/inline-multiline-strings"; mkdir -p "$I/.codex/agents" "$I/tools/agent"
printf '%s\n' \
  'name = "basic-inline"' \
  'description = "inline basic multiline"' \
  'developer_instructions = """INLINE_BASIC_SENTINEL"""' > "$I/.codex/agents/basic-inline.toml"
printf '%s\n' \
  'name = "literal-inline"' \
  'description = "inline literal multiline"' \
  "developer_instructions = '''INLINE_LITERAL_SENTINEL'''" > "$I/.codex/agents/literal-inline.toml"
cp "$repo/tools/agent/generate-subagents.py" "$I/tools/agent/generate-subagents.py"
( cd "$I" && python tools/agent/generate-subagents.py --import ) >"$work/inline-multiline-import.out" 2>&1; rc=$?
check "inline TOML multiline forms import"           test "$rc" = 0
check "inline basic prompt is exact"                 grep -qxF INLINE_BASIC_SENTINEL "$I/.agents/subagents/basic-inline/instructions.md"
check "inline literal prompt is exact"               grep -qxF INLINE_LITERAL_SENTINEL "$I/.agents/subagents/literal-inline/instructions.md"

Y="$work/claude-comment-boundary"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf '%s\n' \
  '---' \
  'name: quoted-hash' \
  'description: "  Review #123\nNext  "' \
  'model: "false"' \
  '---' \
  '' \
  'QUOTED_HASH_SENTINEL' > "$Y/.claude/agents/quoted-hash.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/quoted-hash-import.out" 2>&1; rc=$?
check "quoted hash Claude metadata imports"          test "$rc" = 0
check "quoted hash description stays exact"         grep -qxF 'description: "  Review #123\nNext  "' "$Y/.claude/agents/quoted-hash.md"
check "bool-looking model stays quoted"              grep -qxF 'model: "false"' "$Y/.claude/agents/quoted-hash.md"

Y="$work/claude-leading-body-space"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf '%s\n' \
  '---' \
  'name: leading-body-space' \
  'description: preserve intentional leading body space' \
  '---' \
  '' \
  '' \
  'LEADING_BODY_SENTINEL' > "$Y/.claude/agents/leading-body-space.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/leading-body-space-import.out" 2>&1; rc=$?
check "leading body whitespace imports"              test "$rc" = 0
check "one intentional leading body line remains"    python -c 'import pathlib,sys; raise SystemExit(pathlib.Path(sys.argv[1]).read_bytes() != b"\nLEADING_BODY_SENTINEL\n")' "$Y/.agents/subagents/leading-body-space/instructions.md"

Y="$work/claude-implicit-type"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf -- '---\nname: implicit-type\ndescription: reject implicit YAML types\nmodel: false\n---\n\nIMPLICIT_TYPE_SENTINEL\n' > "$Y/.claude/agents/implicit-type.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/implicit-type-import.out" 2>&1; rc=$?
check "implicit YAML type exits nonzero"              test "$rc" != 0
check "implicit YAML type explains string boundary"  grep -qF "implicit non-string YAML value for field 'model'" "$work/implicit-type-import.out"
check "implicit YAML type writes no SSOT"             test ! -e "$Y/.agents"

Y="$work/claude-empty-optional"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf -- '---\nname: empty-optional\ndescription: reject empty optional YAML values\nmodel:\n---\n\nEMPTY_OPTIONAL_SENTINEL\n' > "$Y/.claude/agents/empty-optional.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/empty-optional-import.out" 2>&1; rc=$?
check "empty optional YAML value exits nonzero"       test "$rc" != 0
check "empty optional YAML value is typed"            grep -qF "implicit non-string YAML value for field 'model'" "$work/empty-optional-import.out"
check "empty optional YAML value writes no SSOT"      test ! -e "$Y/.agents"

expect_empty_claude_field() {
  local slug="$1" field="$2" field_line="$3" root="$work/$1"
  mkdir -p "$root/.claude/agents" "$root/tools/agent"
  printf -- '---\nname: %s\ndescription: explicit empty Claude option\n%s\n---\n\nEMPTY_CLAUDE_OPTION_SENTINEL\n' \
    "$slug" "$field_line" > "$root/.claude/agents/$slug.md"
  cp "$repo/tools/agent/generate-subagents.py" "$root/tools/agent/generate-subagents.py"
  ( cd "$root" && python tools/agent/generate-subagents.py --import ) >"$work/$slug.out" 2>&1; rc=$?
  check "$slug exits nonzero"                         test "$rc" != 0
  check "$slug names the empty field"                grep -qF "Claude field '$field' must not be empty" "$work/$slug.out"
  check "$slug writes no SSOT"                       test ! -e "$root/.agents"
}

expect_empty_codex_field() {
  local slug="$1" field="$2" field_line root="$work/$1"
  field_line="${3:-$field = \"\"}"
  mkdir -p "$root/.codex/agents" "$root/tools/agent"
  printf '%s\n' \
    "name = \"$slug\"" \
    'description = "explicit empty Codex option"' \
    "$field_line" \
    "developer_instructions = 'EMPTY_CODEX_OPTION_SENTINEL'" > "$root/.codex/agents/$slug.toml"
  cp "$repo/tools/agent/generate-subagents.py" "$root/tools/agent/generate-subagents.py"
  ( cd "$root" && python tools/agent/generate-subagents.py --import ) >"$work/$slug.out" 2>&1; rc=$?
  check "$slug exits nonzero"                         test "$rc" != 0
  check "$slug names the empty field"                grep -qF "Codex field '$field' must not be empty" "$work/$slug.out"
  check "$slug writes no SSOT"                       test ! -e "$root/.agents"
}

expect_empty_claude_field empty-claude-tools tools 'tools: ""'
expect_empty_claude_field empty-claude-tools-commas tools 'tools: ", ,"'
expect_empty_claude_field empty-claude-tools-tail tools 'tools: "Read, "'
expect_empty_claude_field empty-claude-model model 'model: ""'
expect_empty_claude_field empty-claude-model-single model "model: ''"
expect_empty_codex_field empty-codex-model model
expect_empty_codex_field empty-codex-model-literal model "model = ''"
expect_empty_codex_field empty-codex-reasoning model_reasoning_effort
expect_empty_codex_field empty-codex-sandbox sandbox_mode

Y="$work/claude-value-comment"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf -- '---\nname: value-comment\ndescription: # KEEP_COMMENT\n---\n\nVALUE_COMMENT_SENTINEL\n' > "$Y/.claude/agents/value-comment.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/value-comment-import.out" 2>&1; rc=$?
check "Claude value comment exits nonzero"           test "$rc" != 0
check "Claude value comment writes no SSOT"          test ! -e "$Y/.agents"

Y="$work/codex-closing-comment"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf '%s\n' \
  'name = "closing-comment"' \
  'description = "closing delimiter comment"' \
  'developer_instructions = """' \
  'CLOSING_COMMENT_SENTINEL' \
  '""" # KEEP_COMMENT' > "$Y/.codex/agents/closing-comment.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/closing-comment-import.out" 2>&1; rc=$?
check "Codex closing comment exits nonzero"          test "$rc" != 0
check "Codex closing comment writes no SSOT"         test ! -e "$Y/.agents"

expect_internal_multiline_delimiter_rejected() {
  local slug="$1" instruction_line="$2" root="$work/$1"
  mkdir -p "$root/.codex/agents" "$root/tools/agent"
  printf '%s\n' \
    "name = \"$slug\"" \
    'description = "internal multiline delimiter"' \
    "$instruction_line" > "$root/.codex/agents/$slug.toml"
  cp "$repo/tools/agent/generate-subagents.py" "$root/tools/agent/generate-subagents.py"
  ( cd "$root" && python tools/agent/generate-subagents.py --import ) >"$work/$slug.out" 2>&1; rc=$?
  check "$slug exits nonzero"                        test "$rc" != 0
  check "$slug names the rejected field"            grep -qF "unsupported Codex value for field 'developer_instructions'" "$work/$slug.out"
  check "$slug writes no SSOT"                      test ! -e "$root/.agents"
}

expect_internal_multiline_delimiter_rejected codex-internal-basic-delimiter \
  'developer_instructions = """abc"""def"""'

Y="$work/codex-literal-quote"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf '%s\n' \
  "name = 'literal-quote'" \
  "description = 'can''t be one TOML literal'" \
  "developer_instructions = 'LITERAL_QUOTE_SENTINEL'" > "$Y/.codex/agents/literal-quote.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/literal-quote-import.out" 2>&1; rc=$?
check "invalid TOML literal exits nonzero"            test "$rc" != 0
check "invalid TOML literal names the field"         grep -qF "unsupported Codex value for field 'description'" "$work/literal-quote-import.out"
check "invalid TOML literal writes no SSOT"           test ! -e "$Y/.agents"

Y="$work/codex-invalid-basic-escape"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf '%s\n' \
  'name = "invalid-basic-escape"' \
  'description = "a\/b"' \
  "developer_instructions = 'INVALID_BASIC_ESCAPE_SENTINEL'" > "$Y/.codex/agents/invalid-basic-escape.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/invalid-basic-escape.out" 2>&1; rc=$?
check "invalid TOML basic escape exits nonzero"       test "$rc" != 0
check "invalid TOML basic escape names the field"    grep -qF "unsupported Codex value for field 'description'" "$work/invalid-basic-escape.out"
check "invalid TOML basic escape writes no SSOT"     test ! -e "$Y/.agents"

Y="$work/codex-invalid-unicode-scalar"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf '%s\n' \
  'name = "invalid-unicode-scalar"' \
  'description = "\uD800"' \
  "developer_instructions = 'INVALID_UNICODE_SENTINEL'" > "$Y/.codex/agents/invalid-unicode-scalar.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/invalid-unicode-scalar.out" 2>&1; rc=$?
check "invalid TOML Unicode scalar exits nonzero"    test "$rc" != 0
check "invalid TOML Unicode scalar names the field" grep -qF "unsupported Codex value for field 'description'" "$work/invalid-unicode-scalar.out"
check "invalid TOML Unicode scalar writes no SSOT"  test ! -e "$Y/.agents"

Y="$work/codex-raw-del"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf 'name = "raw-del"\ndescription = "a\177b"\ndeveloper_instructions = "RAW_DEL_SENTINEL"\n' > "$Y/.codex/agents/raw-del.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/codex-raw-del.out" 2>&1; rc=$?
check "raw TOML DEL exits nonzero"                   test "$rc" != 0
check "raw TOML DEL names the field"                grep -qF "unsupported Codex value for field 'description'" "$work/codex-raw-del.out"
check "raw TOML DEL writes no SSOT"                 test ! -e "$Y/.agents"

Y="$work/claude-raw-del"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf -- '---\nname: raw-del\ndescription: "a\177b"\n---\n\nRAW_DEL_SENTINEL\n' > "$Y/.claude/agents/raw-del.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/claude-raw-del.out" 2>&1; rc=$?
check "raw YAML DEL exits nonzero"                   test "$rc" != 0
check "raw YAML DEL names the field"                grep -qF "unsupported Claude value for field 'description'" "$work/claude-raw-del.out"
check "raw YAML DEL writes no SSOT"                 test ! -e "$Y/.agents"

Y="$work/claude-raw-noncharacter"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
python - "$Y/.claude/agents/raw-noncharacter.md" <<'PY'
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(
    '---\nname: raw-noncharacter\ndescription: "a%sb"\n---\n\nRAW_NONCHARACTER_SENTINEL\n'
    % chr(0xFFFE),
    encoding="utf-8",
)
PY
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/claude-raw-noncharacter.out" 2>&1; rc=$?
check "raw YAML noncharacter exits nonzero"          test "$rc" != 0
check "raw YAML noncharacter names the field"       grep -qF "unsupported Claude value for field 'description'" "$work/claude-raw-noncharacter.out"
check "raw YAML noncharacter writes no SSOT"        test ! -e "$Y/.agents"

Y="$work/codex-raw-tab"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf 'name = "raw-tab"\ndescription = "a\tb"\ndeveloper_instructions = "RAW_TAB_SENTINEL"\n' > "$Y/.codex/agents/raw-tab.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/codex-raw-tab.out" 2>&1; rc=$?
check "raw TOML TAB imports"                         test "$rc" = 0
check "raw TOML TAB stays semantic"                 python -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if d["description"] == "a\tb" else 1)' "$Y/.agents/subagents/raw-tab/metadata.json"
( cd "$Y" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "raw TOML TAB projection is in sync"           test "$rc" = 0

Y="$work/source-escaped-del"; mkdir -p "$Y/.agents/subagents/escaped-del" "$Y/tools/agent"
printf '%s\n' '{"name":"escaped-del","description":"a\u007fb"}' > "$Y/.agents/subagents/escaped-del/metadata.json"
printf 'ESCAPED_DEL_SOURCE\n' > "$Y/.agents/subagents/escaped-del/instructions.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py ) >"$work/source-escaped-del.out" 2>&1; rc=$?
check "escaped DEL source generates"                 test "$rc" = 0
check "escaped DEL projections stay escaped"        python -c 'import pathlib,sys; data=[pathlib.Path(p).read_bytes() for p in sys.argv[1:]]; sys.exit(0 if all(b"\x7f" not in d and b"\\u007f" in d for d in data) else 1)' "$Y/.claude/agents/escaped-del.md" "$Y/.codex/agents/escaped-del.toml"
( cd "$Y" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "escaped DEL projections are in sync"          test "$rc" = 0

Y="$work/source-yaml-boundary"; mkdir -p "$Y/.agents/subagents/yaml-boundary" "$Y/tools/agent"
printf '%s\n' '{"name":"yaml-boundary","description":"a\ufffeb\uffff"}' > "$Y/.agents/subagents/yaml-boundary/metadata.json"
printf 'YAML_BOUNDARY_SOURCE\n' > "$Y/.agents/subagents/yaml-boundary/instructions.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py ) >"$work/source-yaml-boundary.out" 2>&1; rc=$?
check "YAML boundary source generates"               test "$rc" = 0
check "YAML boundary projections stay escaped"      python -c 'import pathlib,sys; data=[pathlib.Path(p).read_bytes() for p in sys.argv[1:]]; raw=(chr(0xfffe).encode(),chr(0xffff).encode()); sys.exit(0 if all(not any(c in d for c in raw) and b"\\ufffe" in d and b"\\uffff" in d for d in data) else 1)' "$Y/.claude/agents/yaml-boundary.md" "$Y/.codex/agents/yaml-boundary.toml"
( cd "$Y" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "YAML boundary projections are in sync"        test "$rc" = 0

Y="$work/host-escaped-del"; mkdir -p "$Y/.claude/agents" "$Y/.codex/agents" "$Y/tools/agent"
printf -- '---\nname: escaped-del-import\ndescription: "a\\u007fb"\n---\n\nESCAPED_DEL_IMPORT_SENTINEL\n' > "$Y/.claude/agents/escaped-del-import.md"
printf '%s\n' \
  'name = "escaped-del-import"' \
  'description = "a\u007Fb"' \
  "developer_instructions = '''" \
  'ESCAPED_DEL_IMPORT_SENTINEL' \
  "'''" > "$Y/.codex/agents/escaped-del-import.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/host-escaped-del.out" 2>&1; rc=$?
check "escaped DEL host import succeeds"             test "$rc" = 0
check "escaped DEL host import stays semantic"       python -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if d["description"] == "a\x7fb" else 1)' "$Y/.agents/subagents/escaped-del-import/metadata.json"
check "escaped DEL host projections stay escaped"   python -c 'import pathlib,sys; data=[pathlib.Path(p).read_bytes() for p in sys.argv[1:]]; sys.exit(0 if all(b"\x7f" not in d and b"\\u007f" in d for d in data) else 1)' "$Y/.claude/agents/escaped-del-import.md" "$Y/.codex/agents/escaped-del-import.toml"
( cd "$Y" && python tools/agent/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "escaped DEL host projections are in sync"     test "$rc" = 0

Y="$work/claude-invalid-plain-colon"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf -- '---\nname: invalid-plain-colon\ndescription: value: changes YAML structure\n---\n\nINVALID_PLAIN_COLON_SENTINEL\n' > "$Y/.claude/agents/invalid-plain-colon.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/invalid-plain-colon.out" 2>&1; rc=$?
check "invalid YAML plain colon exits nonzero"        test "$rc" != 0
check "invalid YAML plain colon names the field"     grep -qF "unsupported Claude value for field 'description'" "$work/invalid-plain-colon.out"
check "invalid YAML plain colon writes no SSOT"      test ! -e "$Y/.agents"

Y="$work/claude-invalid-plain-dash"; mkdir -p "$Y/.claude/agents" "$Y/tools/agent"
printf -- '---\nname: invalid-plain-dash\ndescription: - changes YAML structure\n---\n\nINVALID_PLAIN_DASH_SENTINEL\n' > "$Y/.claude/agents/invalid-plain-dash.md"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/invalid-plain-dash.out" 2>&1; rc=$?
check "invalid YAML plain dash exits nonzero"         test "$rc" != 0
check "invalid YAML plain dash names the field"      grep -qF "unsupported Claude value for field 'description'" "$work/invalid-plain-dash.out"
check "invalid YAML plain dash writes no SSOT"       test ! -e "$Y/.agents"

Y="$work/codex-duplicate-nicknames"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf '%s\n' \
  'name = "duplicate-nicknames"' \
  'description = "duplicate nickname candidates"' \
  'nickname_candidates = ["Twin", "Twin"]' \
  "developer_instructions = 'DUPLICATE_NICKNAME_SENTINEL'" > "$Y/.codex/agents/duplicate-nicknames.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/duplicate-nicknames-import.out" 2>&1; rc=$?
check "duplicate nicknames exit nonzero"              test "$rc" != 0
check "duplicate nicknames explain uniqueness"       grep -qF "nickname_candidates must contain unique names" "$work/duplicate-nicknames-import.out"
check "duplicate nicknames write no SSOT"             test ! -e "$Y/.agents"

Y="$work/codex-invalid-nickname"; mkdir -p "$Y/.codex/agents" "$Y/tools/agent"
printf '%s\n' \
  'name = "invalid-nickname"' \
  'description = "invalid nickname characters"' \
  'nickname_candidates = ["bad@name"]' \
  "developer_instructions = 'INVALID_NICKNAME_SENTINEL'" > "$Y/.codex/agents/invalid-nickname.toml"
cp "$repo/tools/agent/generate-subagents.py" "$Y/tools/agent/generate-subagents.py"
( cd "$Y" && python tools/agent/generate-subagents.py --import ) >"$work/invalid-nickname-import.out" 2>&1; rc=$?
check "invalid nickname exits nonzero"                test "$rc" != 0
check "invalid nickname explains character set"      grep -qF "nickname_candidates use only ASCII letters, digits, spaces, hyphens, and underscores" "$work/invalid-nickname-import.out"
check "invalid nickname writes no SSOT"               test ! -e "$Y/.agents"

N="$work/dual-host-name-subset"; mkdir -p "$N/.codex/agents" "$N/tools/agent"
printf '%s\n' \
  'name = "pr_explorer"' \
  'description = "official Codex-only identity shape"' \
  "developer_instructions = '''NAME_SUBSET_SENTINEL'''" > "$N/.codex/agents/pr-explorer.toml"
cp "$repo/tools/agent/generate-subagents.py" "$N/tools/agent/generate-subagents.py"
( cd "$N" && python tools/agent/generate-subagents.py --import ) >"$work/name-subset-import.out" 2>&1; rc=$?
check "Codex-only name shape exits nonzero"           test "$rc" != 0
check "Codex-only name explains dual-host subset"    grep -qF "not dual-host compatible; use lowercase letters separated by hyphens" "$work/name-subset-import.out"
check "Codex-only name writes no SSOT"                test ! -e "$N/.agents"

N="$work/windows-reserved-name"; mkdir -p "$N/.claude/agents" "$N/tools/agent"
printf -- '---\nname: con\ndescription: Windows reserved filename\n---\n\nWINDOWS_RESERVED_SENTINEL\n' > "$N/.claude/agents/portable-name.md"
cp "$repo/tools/agent/generate-subagents.py" "$N/tools/agent/generate-subagents.py"
( cd "$N" && python tools/agent/generate-subagents.py --import ) >"$work/windows-reserved-name.out" 2>&1; rc=$?
check "Windows-reserved name exits nonzero"           test "$rc" != 0
check "Windows-reserved name explains portability"   grep -qF "agent name 'con' is reserved on Windows" "$work/windows-reserved-name.out"
check "Windows-reserved name writes no SSOT"          test ! -e "$N/.agents"

N="$work/case-colliding-names"; mkdir -p "$N/.claude/agents" "$N/.codex/agents" "$N/tools/agent"
printf -- '---\nname: Review\ndescription: uppercase Claude identity\n---\n\nCASE_COLLISION_SENTINEL\n' > "$N/.claude/agents/Review.md"
printf '%s\n' \
  'name = "review"' \
  'description = "lowercase Codex identity"' \
  "developer_instructions = '''CASE_COLLISION_SENTINEL'''" > "$N/.codex/agents/review.toml"
cp "$repo/tools/agent/generate-subagents.py" "$N/tools/agent/generate-subagents.py"
( cd "$N" && python tools/agent/generate-subagents.py --import ) >"$work/case-collision-import.out" 2>&1; rc=$?
check "case-colliding names exit nonzero"             test "$rc" != 0
check "case-colliding names write no SSOT"            test ! -e "$N/.agents"

C="$work/source-projection-collision"; mkdir -p "$C/.agents/subagents/sourced" "$C/.claude/agents" "$C/tools/agent"
printf '%s\n' '{"name":"sourced","description":"existing source"}' > "$C/.agents/subagents/sourced/metadata.json"
printf 'SOURCE_INSTRUCTIONS\n' > "$C/.agents/subagents/sourced/instructions.md"
printf -- '---\nname: sourced\ndescription: hand-authored projection\n---\n\nHAND_PROJECTION_SENTINEL\n' > "$C/.claude/agents/sourced.md"
cp "$repo/tools/agent/generate-subagents.py" "$C/tools/agent/generate-subagents.py"
git -C "$C" init -q -b main
git -C "$C" config user.email t@t.t; git -C "$C" config user.name tester
git -C "$C" commit -q --allow-empty -m init
collision_before="$(git hash-object "$C/.claude/agents/sourced.md")"
( cd "$C" && bash "$H" plan ) >"$work/source-collision-plan.out" 2>&1; rc=$?
check "source collision plan exits 0"                test "$rc" = 0
check "source collision plan requires resolution"    grep -qF "hand-authored projection conflicts with existing .agents/subagents/sourced" "$work/source-collision-plan.out"
( cd "$C" && python tools/agent/generate-subagents.py --import ) >"$work/source-collision-import.out" 2>&1; rc=$?
check "source collision import exits nonzero"        test "$rc" != 0
check "source collision import explains conflict"   grep -qF "hand-authored projection conflicts with existing .agents/subagents/sourced" "$work/source-collision-import.out"
check "source collision import preserves projection" test "$(git hash-object "$C/.claude/agents/sourced.md")" = "$collision_before"
printf -- '---\nname: sourced\ndescription: hand-authored projection\n---\n\nHAND_PROJECTION_SENTINEL\n' > "$C/.claude/agents/sourced.md"
( cd "$C" && python tools/agent/generate-subagents.py ) >"$work/source-collision-project.out" 2>&1; rc=$?
check "default projection collision exits nonzero"  test "$rc" != 0
check "default collision preserves projection"      test "$(git hash-object "$C/.claude/agents/sourced.md")" = "$collision_before"

C="$work/source-codex-collision"; mkdir -p "$C/.agents/subagents/sourced-codex" "$C/.codex/agents" "$C/tools/agent"
printf '%s\n' '{"name":"sourced-codex","description":"existing source"}' > "$C/.agents/subagents/sourced-codex/metadata.json"
printf 'SOURCE_INSTRUCTIONS\n' > "$C/.agents/subagents/sourced-codex/instructions.md"
printf '%s\n' \
  'name = "sourced-codex"' \
  'description = "hand-authored Codex projection"' \
  "developer_instructions = '''HAND_CODEX_PROJECTION_SENTINEL'''" > "$C/.codex/agents/sourced-codex.toml"
cp "$repo/tools/agent/generate-subagents.py" "$C/tools/agent/generate-subagents.py"
git -C "$C" init -q -b main
git -C "$C" config user.email t@t.t; git -C "$C" config user.name tester
git -C "$C" commit -q --allow-empty -m init
codex_collision_before="$(git hash-object "$C/.codex/agents/sourced-codex.toml")"
( cd "$C" && bash "$H" plan ) >"$work/source-codex-collision-plan.out" 2>&1; rc=$?
check "Codex source collision plan exits 0"          test "$rc" = 0
check "Codex source collision plan needs resolution" grep -qF "hand-authored projection conflicts with existing .agents/subagents/sourced-codex" "$work/source-codex-collision-plan.out"
( cd "$C" && python tools/agent/generate-subagents.py --import ) >"$work/source-codex-collision-import.out" 2>&1; rc=$?
check "Codex source collision import exits nonzero"  test "$rc" != 0
check "Codex collision import preserves projection" test "$(git hash-object "$C/.codex/agents/sourced-codex.toml")" = "$codex_collision_before"
check "Codex import conflict writes no Claude side"  test ! -e "$C/.claude/agents/sourced-codex.md"
( cd "$C" && python tools/agent/generate-subagents.py ) >"$work/source-codex-collision-project.out" 2>&1; rc=$?
check "Codex default collision exits nonzero"        test "$rc" != 0
check "Codex default preserves projection"           test "$(git hash-object "$C/.codex/agents/sourced-codex.toml")" = "$codex_collision_before"
check "Codex default conflict writes no Claude side" test ! -e "$C/.claude/agents/sourced-codex.md"

P="$work/projection-parent-conflict"; mkdir -p "$P/.claude/agents" "$P/tools/agent"
printf -- '---\nname: parent-conflict\ndescription: projection parent is not a directory\n---\n\nPARENT_CONFLICT_SENTINEL\n' > "$P/.claude/agents/parent-conflict.md"
printf 'not a directory\n' > "$P/.codex"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
parent_before="$(git hash-object "$P/.claude/agents/parent-conflict.md")"
( cd "$P" && python tools/agent/generate-subagents.py --import ) >"$work/projection-parent-conflict.out" 2>&1; rc=$?
check "projection parent conflict exits nonzero"      test "$rc" != 0
check "projection parent conflict names the path"    grep -qF ".codex: expected a directory" "$work/projection-parent-conflict.out"
check "projection parent conflict writes no SSOT"    test ! -e "$P/.agents"
check "projection parent preserves host input"       test "$(git hash-object "$P/.claude/agents/parent-conflict.md")" = "$parent_before"

P="$work/noncanonical-host-extension"; mkdir -p "$P/.claude/agents" "$P/.codex/agents" "$P/tools/agent"
printf -- '---\nname: alias\ndescription: hand-authored uppercase extension\n---\n\nUPPERCASE_EXTENSION_SENTINEL\n' > "$P/.claude/agents/alias.MD"
printf '%s\n' \
  'name = "alias"' \
  'description = "Codex alias candidate"' \
  "developer_instructions = 'UPPERCASE_EXTENSION_SENTINEL'" > "$P/.codex/agents/alias.toml"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
alias_before="$(git hash-object "$P/.claude/agents/alias.MD")"
( cd "$P" && bash "$H" plan ) >"$work/noncanonical-extension-plan.out" 2>&1; rc=$?
check "noncanonical extension plan exits 0"          test "$rc" = 0
check "noncanonical extension plan explains case"   grep -qF "host agent extension must be lowercase .md" "$work/noncanonical-extension-plan.out"
( cd "$P" && python tools/agent/generate-subagents.py --import ) >"$work/noncanonical-extension.out" 2>&1; rc=$?
check "noncanonical host extension exits nonzero"     test "$rc" != 0
check "noncanonical extension explains lowercase"    grep -qF "host agent extension must be lowercase .md" "$work/noncanonical-extension.out"
check "noncanonical extension writes no SSOT"         test ! -e "$P/.agents"
check "noncanonical extension preserves host input"  test "$(git hash-object "$P/.claude/agents/alias.MD")" = "$alias_before"

P="$work/projection-temp-conflict"; mkdir -p "$P/.claude/agents" "$P/.codex/agents/alpha.toml.tmp" "$P/tools/agent"
printf -- '---\nname: alpha\ndescription: temporary projection conflict\n---\n\nTEMP_CONFLICT_SENTINEL\n' > "$P/.claude/agents/alpha.md"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
temp_before="$(git hash-object "$P/.claude/agents/alpha.md")"
( cd "$P" && python tools/agent/generate-subagents.py --import ) >"$work/projection-temp-conflict.out" 2>&1; rc=$?
check "projection temp conflict exits nonzero"        test "$rc" != 0
check "projection temp conflict names the path"      grep -qF ".codex/agents/alpha.toml.tmp: temporary write path already exists" "$work/projection-temp-conflict.out"
check "projection temp conflict writes no SSOT"      test ! -e "$P/.agents"
check "projection temp preserves host input"         test "$(git hash-object "$P/.claude/agents/alpha.md")" = "$temp_before"

P="$work/stale-path-conflict"; mkdir -p "$P/.agents/subagents/alpha" "$P/.claude/agents/orphan.md" "$P/tools/agent"
printf '%s\n' '{"name":"alpha","description":"stale path preflight"}' > "$P/.agents/subagents/alpha/metadata.json"
printf 'STALE_PATH_SOURCE\n' > "$P/.agents/subagents/alpha/instructions.md"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
( cd "$P" && python tools/agent/generate-subagents.py ) >"$work/stale-path-conflict.out" 2>&1; rc=$?
check "stale path conflict exits nonzero"             test "$rc" != 0
check "stale path conflict names the path"           grep -qF ".claude/agents/orphan.md: expected a regular file" "$work/stale-path-conflict.out"
check "stale conflict writes no wanted projection"   test ! -e "$P/.claude/agents/alpha.md"
check "stale conflict writes no Codex projection"    test ! -e "$P/.codex/agents/alpha.toml"

P="$work/check-projection-root-file"; mkdir -p "$P/.claude" "$P/tools/agent"
printf 'NOT_A_DIRECTORY\n' > "$P/.claude/agents"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
( cd "$P" && python tools/agent/generate-subagents.py --check ) >"$work/check-projection-root-file.out" 2>&1; rc=$?
check "check rejects projection root file"           test "$rc" != 0
check "check names malformed projection root"       grep -qF ".claude/agents: expected a directory" "$work/check-projection-root-file.out"

P="$work/noncanonical-host-basename"; mkdir -p "$P/.agents/subagents/foo" "$P/tools/agent"
printf '%s\n' '{"name":"foo","description":"case-only host basename"}' > "$P/.agents/subagents/foo/metadata.json"
printf 'NONCANONICAL_BASENAME_SENTINEL\n' > "$P/.agents/subagents/foo/instructions.md"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
( cd "$P" && python tools/agent/generate-subagents.py ) >/dev/null 2>&1; rc=$?
check "basename fixture setup exits 0"               test "$rc" = 0
python - "$P/.claude/agents/foo.md" "$P/.claude/agents/Foo.md" <<'PY'
import os
import sys

source, target = sys.argv[1:]
hop = source + ".case-hop"
os.replace(source, hop)
os.replace(hop, target)
PY
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
( cd "$P" && bash "$H" plan ) >"$work/noncanonical-basename-plan.out" 2>&1; rc=$?
check "noncanonical basename plan exits 0"           test "$rc" = 0
check "noncanonical basename plan explains name"    grep -qF "non-portable host filename Foo.md" "$work/noncanonical-basename-plan.out"
( cd "$P" && python tools/agent/generate-subagents.py --check ) >"$work/noncanonical-basename-check.out" 2>&1; rc=$?
check "check rejects noncanonical basename"         test "$rc" != 0
check "check explains noncanonical basename"        grep -qF "agent name 'Foo' is not dual-host compatible" "$work/noncanonical-basename-check.out"
( cd "$P" && python tools/agent/generate-subagents.py ) >"$work/noncanonical-basename-write.out" 2>&1; rc=$?
check "write rejects noncanonical basename"         test "$rc" != 0
check "write creates no parallel lowercase file"    python -c 'import os,sys; names=os.listdir(sys.argv[1]); sys.exit(0 if "Foo.md" in names and "foo.md" not in names else 1)' "$P/.claude/agents"

P="$work/hidden-host-agent"; mkdir -p "$P/.claude/agents"
printf -- '---\nname: hidden\ndescription: hidden host filename\n---\n\nHIDDEN_HOST_SENTINEL\n' > "$P/.claude/agents/.hidden.md"
printf -- '---\nname: double-hidden\ndescription: double hidden host filename\n---\n\nDOUBLE_HIDDEN_HOST_SENTINEL\n' > "$P/.claude/agents/..double-hidden.md"
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
( cd "$P" && bash "$H" plan ) >"$work/hidden-host-plan.out" 2>&1; rc=$?
check "hidden host plan exits 0"                     test "$rc" = 0
check "hidden host plan explains filename"          grep -qF "non-portable host filename .hidden.md" "$work/hidden-host-plan.out"
check "double-hidden host plan explains filename"   grep -qF "non-portable host filename ..double-hidden.md" "$work/hidden-host-plan.out"

P="$work/source-entry-file"; mkdir -p "$P/.agents/subagents/source-file" "$P/tools/agent"
printf '%s\n' '{"name":"source-file","description":"source entry shape"}' > "$P/.agents/subagents/source-file/metadata.json"
printf 'SOURCE_ENTRY_PROJECTION_SENTINEL\n' > "$P/.agents/subagents/source-file/instructions.md"
cp "$repo/tools/agent/generate-subagents.py" "$P/tools/agent/generate-subagents.py"
( cd "$P" && python tools/agent/generate-subagents.py ) >/dev/null 2>&1; rc=$?
check "source entry fixture setup exits 0"          test "$rc" = 0
rm -rf "$P/.agents/subagents/source-file"
printf 'SOURCE_ENTRY_FILE_SENTINEL\n' > "$P/.agents/subagents/source-file"
( cd "$P" && python tools/agent/generate-subagents.py ) >"$work/source-entry-file.out" 2>&1; rc=$?
check "source entry file exits nonzero"             test "$rc" != 0
check "source entry file explains directory shape" grep -qF ".agents/subagents/source-file: expected a directory" "$work/source-entry-file.out"
check "source entry file stays byte-identical"      grep -qxF "SOURCE_ENTRY_FILE_SENTINEL" "$P/.agents/subagents/source-file"
check "source entry failure preserves projections" fixed_text_in_both "SOURCE_ENTRY_PROJECTION_SENTINEL" "$P/.claude/agents/source-file.md" "$P/.codex/agents/source-file.toml"

expect_invalid_metadata() {
  local slug="$1" json="$2" needle="$3" root="$work/source-metadata-$1"
  mkdir -p "$root/.agents/subagents/$slug" "$root/tools/agent"
  printf '%s\n' "$json" > "$root/.agents/subagents/$slug/metadata.json"
  printf 'INVALID_SOURCE_METADATA_SENTINEL\n' > "$root/.agents/subagents/$slug/instructions.md"
  cp "$repo/tools/agent/generate-subagents.py" "$root/tools/agent/generate-subagents.py"
  ( cd "$root" && python tools/agent/generate-subagents.py ) >"$work/source-metadata-$slug.out" 2>&1; rc=$?
  check "$slug metadata exits nonzero"              test "$rc" != 0
  check "$slug metadata explains type"             grep -qF "$needle" "$work/source-metadata-$slug.out"
  check "$slug metadata writes no projections"     both_absent "$root/.claude/agents/$slug.md" "$root/.codex/agents/$slug.toml"
}

expect_invalid_metadata description-type \
  '{"name":"description-type","description":["not","a","string"]}' \
  "metadata.description must be a non-empty string"
expect_invalid_metadata claude-tools-type \
  '{"name":"claude-tools-type","description":"bad tools","claude":{"tools":"Read"}}' \
  "metadata.claude.tools must be a non-empty list of strings"
expect_invalid_metadata claude-tool-comma \
  '{"name":"claude-tool-comma","description":"ambiguous tool","claude":{"tools":["Read,Write"]}}' \
  "metadata.claude.tools entries must not contain commas or surrounding whitespace"
expect_invalid_metadata claude-tool-padding \
  '{"name":"claude-tool-padding","description":"padded tool","claude":{"tools":[" Read "]}}' \
  "metadata.claude.tools entries must not contain commas or surrounding whitespace"
expect_invalid_metadata codex-model-type \
  '{"name":"codex-model-type","description":"bad model","codex":{"model":{"unexpected":true}}}' \
  "metadata.codex.model must be a non-empty string"
expect_invalid_metadata codex-sandbox-type \
  '{"name":"codex-sandbox-type","description":"bad sandbox","codex":{"sandbox_mode":false}}' \
  "metadata.codex.sandbox_mode must be a non-empty string"
expect_invalid_metadata source-unicode-scalar \
  '{"name":"source-unicode-scalar","description":"\ud800"}' \
  "metadata.description contains an invalid Unicode scalar value"

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

echo "== symlinked hook configs: reject before capability probe or mutation =="
K="$work/symlinked-hook-config"; mkdir -p "$K/.claude" "$K/shared"
git -C "$K" init -q -b main
git -C "$K" config user.email t@t.t; git -C "$K" config user.name tester
git -C "$K" config core.symlinks true
printf '%s\n' '{"env":{"KEEP":"yes"},"hooks":{}}' > "$K/shared/settings.json"
python - "$K" <<'PY'
import os
from pathlib import Path
import sys

root = Path(sys.argv[1])
os.symlink(
    "../shared/settings.json",
    root / ".claude/settings.json",
    target_is_directory=False,
)
PY
git -C "$K" add -A && git -C "$K" commit -q -m "symlinked hook config fixture"
before="$(git hash-object "$K/shared/settings.json")"
(
  cd "$K" || exit 1
  AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 \
    bash "$H" retrofit --no-worktree --no-husky --no-example-subagent
) >"$work/symlinked-hook-config.out" 2>&1; rc=$?
check "symlinked hook config exits 2" test "$rc" = 2
check "symlinked hook config names unsupported boundary" \
  grep -qF ".claude/settings.json: symlinked hook configs are unsupported" "$work/symlinked-hook-config.out"
check "symlinked hook config stops before doctor" \
  no_fixed_text "$work/symlinked-hook-config.out" "symlink capability denied by the test fixture"
check "hook config link survives" test -L "$K/.claude/settings.json"
check "hook config link target survives" test "$(readlink "$K/.claude/settings.json")" = "../shared/settings.json"
check "hook config referent is byte-identical" test "$(git hash-object "$K/shared/settings.json")" = "$before"
check "symlink rejection leaves repo unchanged" test -z "$(git -C "$K" status --porcelain --untracked-files=all)"

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
)
for name, old, new in fixtures:
    path = Path(name)
    data = path.read_bytes()
    assert data.count(old) == 1
    path.write_bytes(data.replace(old, new, 1))
hook = Path(sys.argv[3])
hook_data = hook.read_bytes()
assert b"python tools/agent/generate-subagents.py --check\n" in hook_data
hook.write_bytes(hook_data.replace(b"\n", b"\r"))
PY
( cd "$S" && bash "$H" retrofit ) >/dev/null 2>&1; rc=$?
check "retrofit re-run exits 0"              test "$rc" = 0
check "PostToolUse stays 2 hooks (no dup)"   jcount "$S/.claude/settings.json" PostToolUse 2
check "CRLF gitignore target stays singular" logical_line_count "$S/.gitignore" ".claude/settings.local.json" 1
check "CRLF attributes target stays singular" logical_line_count "$S/.gitattributes" "tools/agent/*.sh text eol=lf" 1
check "CR-only Husky target stays singular" logical_line_count "$S/.husky/pre-commit" "python tools/agent/generate-subagents.py --check" 1

echo "== retrofit propagates subagent import rejection =="
printf -- '---\nname: import-propagation\ndescription: propagation fixture\n---\n\nCLAUDE_IMPORT_BODY\n' \
  > "$S/.claude/agents/import-propagation.md"
printf '%s\n' \
  'name = "import-propagation"' \
  'description = "propagation fixture"' \
  "developer_instructions = '''" \
  'CODEX_IMPORT_BODY' \
  "'''" > "$S/.codex/agents/import-propagation.toml"
import_cc_before="$(git hash-object "$S/.claude/agents/import-propagation.md")"
import_cx_before="$(git hash-object "$S/.codex/agents/import-propagation.toml")"
import_out="$work/import-propagation-retrofit.out"
( cd "$S" && bash "$H" retrofit ) >"$import_out" 2>&1; rc=$?
check "retrofit propagates import rejection"         test "$rc" != 0
check "retrofit surfaces divergent instructions"     grep -qF "have different instructions; resolve the conflict before --import" "$import_out"
check "retrofit does not downgrade import rejection" no_fixed_text "$import_out" "generate-subagents.py --import returned nonzero"
check "failed retrofit omits completion banner"      no_fixed_text "$import_out" "harness retrofit complete."
check "failed retrofit preserves Claude input"       test "$(git hash-object "$S/.claude/agents/import-propagation.md")" = "$import_cc_before"
check "failed retrofit preserves Codex input"        test "$(git hash-object "$S/.codex/agents/import-propagation.toml")" = "$import_cx_before"
check "failed retrofit writes no partial SSOT"       test ! -e "$S/.agents/subagents/import-propagation"
rm -f "$S/.claude/agents/import-propagation.md" "$S/.codex/agents/import-propagation.toml"

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
