#!/usr/bin/env bash
# e2e-agent-scaffold.sh — behavioral end-to-end test of the agent-scaffold installer.
#
# Runs the deterministic preflight suite, then installs the harness into a
# throwaway repo and covers dual-host wiring, idempotent apply, worktree flow,
# hooks, profiles, and real-symlink projection behavior.
# All writes stay inside a generated temporary directory.
#
# Usage: bash scripts/e2e-agent-scaffold.sh [-h|--help]
# Exit 0 = all runnable assertions passed, 1 = a failure. Needs git + python.
# CI (or AGENT_SCAFFOLD_E2E_REQUIRE_SYMLINKS=1) requires the positive real-link
# suite; an unprivileged local Windows host runs the zero-residue negative suite.
set -uo pipefail

usage() { sed -n '2,11p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "$#" in
  0) ;;
  1) case "$1" in -h | --help) usage 0 ;; *) usage 2 ;; esac ;;
  *) usage 2 ;;
esac

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
H="$repo/skills/agent-scaffold/agent-scaffold.sh"
SM="$repo/skills/agent-scaffold/assets/runtime/symlink-manager.py"
[ -f "$H" ] || { echo "installer not found: $H" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git required" >&2; exit 1; }
command -v python >/dev/null 2>&1 || { echo "python required" >&2; exit 1; }

bash "$repo/scripts/tests/e2e-agent-scaffold-preflight.sh" || exit 1

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
jcommand_count() { python -c 'import json,re,sys; d=json.load(open(sys.argv[1])); p=re.compile(r"(?:^|[/\s\"\x27;&|()<>]).agents/tools/hooks/"+re.escape(sys.argv[2])+r"\.sh(?=$|[\s\"\x27;&|()<>])"); n=sum(bool(p.search(str(h.get("command", "")).replace("\\", "/"))) for groups in d.get("hooks", {}).values() for g in groups for h in g.get("hooks", [])); sys.exit(0 if n==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329
fixed_text_in_both() { grep -qF "$1" "$2" && grep -qF "$1" "$3"; }
# shellcheck disable=SC2317,SC2329
fixed_text_absent_in_both() { ! grep -qF "$1" "$2" && ! grep -qF "$1" "$3"; }
# shellcheck disable=SC2317,SC2329
logical_line_count() { python -c 'import pathlib,sys; lines=pathlib.Path(sys.argv[1]).read_bytes().splitlines(); sys.exit(0 if lines.count(sys.argv[2].encode())==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329  # run indirectly through check() "$@"
is_real_dir() { [ -d "$1" ] && [ ! -L "$1" ]; }
# shellcheck disable=SC2317,SC2329
no_fixed_text() { ! grep -qF -- "$2" "$1"; }
# shellcheck disable=SC2317,SC2329
no_exact_line() { ! grep -qxF "$2" "$1"; }
# shellcheck disable=SC2317,SC2329
both_absent() { [ ! -e "$1" ] && [ ! -e "$2" ]; }
# shellcheck disable=SC2317,SC2329
authority_laws_present() {
  local file="$1"
  grep -qF 'canonical repository-level contract for Agent work' "$file" \
    && grep -qF '**Keep it current.**' "$file" \
    && grep -qF '**Keep it lean.**' "$file" \
    && grep -qF '**Keep scopes honest.**' "$file" \
    && grep -qF 'directory structure alone never justifies one.' "$file" \
    && grep -qF '**Resolve conflicts explicitly.**' "$file" \
    && grep -qF 'budget hook remains advisory; projects may override its default line and character limits' "$file"
}
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

temp_parent="$(cd "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P)" \
  || { echo "temporary-directory parent is unavailable: ${TMPDIR:-/tmp}" >&2; exit 1; }
temp_prefix="${temp_parent%/}/agent-scaffold-e2e."
work="$(mktemp -d "${temp_prefix}XXXXXX")" \
  || { echo "failed to create temporary directory under $temp_parent" >&2; exit 1; }
temp_suffix="${work#"$temp_prefix"}"
if [ "$work" = "$temp_suffix" ] || [ -z "$temp_suffix" ] || [ ! -d "$work" ]; then
  echo "mktemp returned an unsafe temporary directory: ${work:-<empty>}" >&2
  exit 1
fi
# shellcheck disable=SC2317,SC2329  # invoked by the EXIT trap; code differs by ShellCheck version
cleanup() {
  local suffix="${work#"$temp_prefix"}"
  if [ "$work" != "$suffix" ] && [ -n "$suffix" ] && [ -d "$work" ]; then
    rm -rf -- "$work"
  fi
}
trap cleanup EXIT
S="$work/scratch space-雪"; mkdir -p "$S"
git -C "$S" init -q -b main
git -C "$S" config user.email t@t.t; git -C "$S" config user.name tester
git -C "$S" config core.symlinks true
git -C "$S" config core.autocrlf true
git -C "$S" config core.filemode false
git -C "$S" commit -q --allow-empty -m init

echo "== temporary-directory failures stop before target mutation =="
MKTEMP_BIN="$work/mktemp-bin"; mkdir -p "$MKTEMP_BIN"
cat > "$MKTEMP_BIN/mktemp" <<'EOF'
#!/usr/bin/env bash
case "${FAKE_MKTEMP_MODE:-fail}" in
  fail) exit 37 ;;
  unsafe) printf '%s\n' "$FAKE_MKTEMP_UNSAFE" ;;
  *) exit 38 ;;
esac
EOF
chmod +x "$MKTEMP_BIN/mktemp"
temp_before="$(git -C "$S" status --porcelain=v1 --untracked-files=all)"
( cd "$S" && PATH="$MKTEMP_BIN:$PATH" FAKE_MKTEMP_MODE=fail bash "$H" apply ) \
  >"$work/mktemp-fail.out" 2>&1; rc=$?
check "mktemp failure exits 2" test "$rc" = 2
check "mktemp failure is explained" grep -qF "failed to create a temporary directory" "$work/mktemp-fail.out"
check "mktemp failure leaves target unchanged" test "$(git -C "$S" status --porcelain=v1 --untracked-files=all)" = "$temp_before"
( cd "$S" && PATH="$MKTEMP_BIN:$PATH" FAKE_MKTEMP_MODE=unsafe FAKE_MKTEMP_UNSAFE="$work" bash "$H" apply ) \
  >"$work/mktemp-unsafe.out" 2>&1; rc=$?
check "unsafe mktemp path exits 2" test "$rc" = 2
check "unsafe mktemp path is explained" grep -qF "mktemp returned an unsafe temporary directory" "$work/mktemp-unsafe.out"
check "unsafe mktemp path preserves E2E root" test -d "$S"
check "unsafe mktemp path leaves target unchanged" test "$(git -C "$S" status --porcelain=v1 --untracked-files=all)" = "$temp_before"

echo "== unsupported host: fail before mutation, never copy =="
N="$work/no-links"; mkdir -p "$N"
git -C "$N" init -q -b main
git -C "$N" config user.email t@t.t; git -C "$N" config user.name tester
git -C "$N" config core.symlinks true
git -C "$N" commit -q --allow-empty -m init
( cd "$N" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" apply ) >/dev/null 2>&1; rc=$?
check "unsupported apply exits 2"                    test "$rc" = 2
check "unsupported apply leaves no partial harness" no_partial_harness "$N"
( cd "$N" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" apply --profile light ) >/dev/null 2>&1; rc=$?
check "unsupported light apply exits 2"              test "$rc" = 2
check "unsupported light apply leaves no residue"   no_partial_harness "$N"
before="$( { find "$N" -type f; find "$N" -type l; } | sort )"
( cd "$N" && bash "$H" plan --profile light ) >"$work/light-profile-plan.out" 2>&1; rc=$?
after="$( { find "$N" -type f; find "$N" -type l; } | sort )"
check "light-profile plan exits 0"                   test "$rc" = 0
check "light-profile plan makes no change"           test "$before" = "$after"
check "light plan reports omitted governance"      grep -qF "worktree governance omitted" "$work/light-profile-plan.out"
check "light plan keeps profile in apply command"  grep -qF "apply --profile light" "$work/light-profile-plan.out"

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
    bash "$H" verify --profile light
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
    bash "$H" verify --profile light
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
    bash "$H" verify --profile light
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
    bash "$H" verify --profile light
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
    bash "$H" plan --profile light
) >"$work/harness-no-python.out" 2>&1; rc=$?
check "harness rejects an entirely incompatible candidate set" test "$rc" = 2
check "harness names its Python version prerequisite" grep -qF "python 3.8+ is required" "$work/harness-no-python.out"

R="$work/relink-python-fallback"; mkdir -p "$R/.agents"
cp "$repo/skills/agent-scaffold/assets/runtime/relink-skills.sh" "$R/.agents/relink-skills.sh"
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
      _ "$repo/skills/agent-scaffold/assets/runtime/hooks/hook-common.sh"
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
      "$repo/skills/agent-scaffold/assets/runtime/hooks/hook-common.sh" \
      '{"tool_input":{"file_path":"ignored"}}'
} 2>/dev/null)"; rc=$?
check "hook path extraction remains fail-open" test "$rc" = 0
check "hook uses jq when every Python candidate is incompatible" grep -qxF jq "$resolver_log"
check "jq fallback returns the extracted path" test "$hook_paths" = /fixture/AGENTS.md

echo "== worktree push rejection: retain a retryable feature worktree =="
R="$work/worktree-push-origin.git"
P="$work/worktree-push-primary"
Q="$work/worktree-push-peer"
D="$P/.worktrees/develop-trunk"
W="$P/.worktrees/push-retry"
git init --bare -q "$R"
git init -q -b main "$P"
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
WT_HELPER="$P/.agents/tools/worktree.sh"
mkdir -p "$(dirname "$WT_HELPER")"
cp "$repo/skills/agent-scaffold/assets/runtime/worktree.sh" "$WT_HELPER"
chmod +x "$WT_HELPER"
printf 'base\n' > "$P/base.txt"
git -C "$P" add base.txt .agents/tools/worktree.sh && git -C "$P" commit -q -m "base"
git -C "$P" remote add origin "$R"
git -C "$P" push -q -u origin main
main_oid="$(git -C "$P" rev-parse main)"
git -C "$P" branch develop
git -C "$P" push -q -u origin develop
git -C "$P" worktree add -q "$D" develop
git clone -q -b develop "$R" "$Q"
git -C "$Q" config user.email t@t.t; git -C "$Q" config user.name tester
(
  cd "$P" || exit 1
  bash "$WT_HELPER" new push-retry --type fix --trunk develop
) >"$work/worktree-push-new.out" 2>&1
printf 'feature\n' > "$W/feature.txt"
git -C "$W" add feature.txt && git -C "$W" commit -q -m "feature change"
feature_oid="$(git -C "$W" rev-parse HEAD)"
printf 'peer\n' > "$Q/peer.txt"
git -C "$Q" add peer.txt && git -C "$Q" commit -q -m "peer change"
git -C "$Q" push -q origin develop
(
  cd "$W" || exit 1
  bash "$WT_HELPER" "done" --trunk develop --keep-branch
) >"$work/worktree-push-first.out" 2>&1; first_rc=$?
check "concurrent remote advance rejects the first push" test "$first_rc" = 2
check "feature commit remains on local develop" git -C "$P" merge-base --is-ancestor "$feature_oid" develop
check "failed target push leaves main untouched" test "$(git -C "$P" rev-parse main)" = "$main_oid"
check "failed push keeps feature worktree" test -d "$W"
check "failed push keeps feature branch" git -C "$P" show-ref --verify -q refs/heads/fix/push-retry
check "failed push explains retained retry state" \
  grep -qF "worktree and branch kept" "$work/worktree-push-first.out"
check "retry command preserves trunk and cleanup policy" \
  grep -qF -- '--trunk "develop" --keep-branch' "$work/worktree-push-first.out"
git -C "$D" fetch -q origin
git -C "$D" merge --no-edit origin/develop >"$work/worktree-push-recover.out" 2>&1; recover_rc=$?
check "trunk can merge the concurrent remote advance" test "$recover_rc" = 0
(
  cd "$W" || exit 1
  bash "$WT_HELPER" "done" --trunk develop --keep-branch
) >"$work/worktree-push-retry.out" 2>&1; retry_rc=$?
check "retained worktree can retry done" test "$retry_rc" = 0
check "successful retry removes feature worktree" test ! -d "$W"
check "successful retry preserves requested feature branch" \
  git -C "$P" show-ref --verify -q refs/heads/fix/push-retry
git -C "$P" fetch -q origin
check "successful retry pushes the resolved develop" \
  test "$(git -C "$P" rev-parse develop)" = "$(git -C "$P" rev-parse origin/develop)"
check "successful retry still leaves origin main untouched" \
  test "$(git -C "$P" rev-parse origin/main)" = "$main_oid"

echo "== deterministic conflicts stop before the first target write =="
K="$work/preflight-contract-conflict"; mkdir -p "$K"
git -C "$K" init -q -b main
git -C "$K" config user.email t@t.t; git -C "$K" config user.name tester
git -C "$K" config core.symlinks true
printf '# Canonical contract\n' > "$K/AGENTS.md"
printf '# Divergent Claude contract\n' > "$K/CLAUDE.md"
git -C "$K" add -A && git -C "$K" commit -q -m "contract conflict fixture"
agents_before="$(git hash-object "$K/AGENTS.md")"
claude_before="$(git hash-object "$K/CLAUDE.md")"
(
  cd "$K" || exit 1
  bash "$H" apply
) >"$work/preflight-contract-conflict.out" 2>&1; rc=$?
check "contract conflict exits 2" test "$rc" = 2
check "contract conflict is explicit" grep -qF "projection conflict" "$work/preflight-contract-conflict.out"
check "contract conflict preserves AGENTS.md" test "$(git hash-object "$K/AGENTS.md")" = "$agents_before"
check "contract conflict preserves CLAUDE.md" test "$(git hash-object "$K/CLAUDE.md")" = "$claude_before"
check "contract conflict leaves repo unchanged" test -z "$(git -C "$K" status --porcelain --untracked-files=all)"

fixture=target-text
  K="$work/preflight-contract-$fixture"; mkdir -p "$K"
  git -C "$K" init -q -b main
  git -C "$K" config user.email t@t.t; git -C "$K" config user.name tester
  git -C "$K" config core.symlinks true
  printf '# Canonical contract\n' > "$K/AGENTS.md"
  printf 'AGENTS.md\n' > "$K/CLAUDE.md"
  git -C "$K" add -A && git -C "$K" commit -q -m "$fixture materialization fixture"
  (
    cd "$K" || exit 1
    AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 \
      bash "$H" apply
  ) >"$work/preflight-contract-$fixture.out" 2>&1; rc=$?
  check "$fixture materialization reaches the capability probe" \
    grep -qF "symlink capability denied by the test fixture" "$work/preflight-contract-$fixture.out"
  check "$fixture capability failure exits 2" test "$rc" = 2
  check "$fixture capability failure leaves repo unchanged" \
    test -z "$(git -C "$K" status --porcelain --untracked-files=all)"

K="$work/preflight-subagent-conflict"; mkdir -p "$K/.claude/agents" "$K/.codex/agents"
git -C "$K" init -q -b main
git -C "$K" config user.email t@t.t; git -C "$K" config user.name tester
git -C "$K" config core.symlinks true
printf -- '---\nname: dual\ndescription: shared description\n---\n\nCLAUDE_ONLY_INSTRUCTIONS\n' > "$K/.claude/agents/dual.md"
printf '%s\n' \
  'name = "dual"' \
  'description = "shared description"' \
  "developer_instructions = 'CODEX_ONLY_INSTRUCTIONS'" > "$K/.codex/agents/dual.toml"
git -C "$K" add -A && git -C "$K" commit -q -m "subagent conflict fixture"
(
  cd "$K" || exit 1
  bash "$H" apply
) >"$work/preflight-subagent-conflict.out" 2>&1; rc=$?
check "subagent conflict exits nonzero" test "$rc" != 0
check "subagent conflict is explicit" \
  grep -qF "have different instructions; resolve the conflict before --import" "$work/preflight-subagent-conflict.out"
check "subagent conflict leaves repo unchanged" test -z "$(git -C "$K" status --porcelain --untracked-files=all)"

K="$work/preflight-skill-conflict"; mkdir -p "$K/.agents/skills/dual" "$K/.claude/skills/dual"
git -C "$K" init -q -b main
git -C "$K" config user.email t@t.t; git -C "$K" config user.name tester
git -C "$K" config core.symlinks true
printf -- '---\nname: dual\n---\n\nAUTHORITATIVE\n' > "$K/.agents/skills/dual/SKILL.md"
printf -- '---\nname: dual\n---\n\nCONFLICTING\n' > "$K/.claude/skills/dual/SKILL.md"
git -C "$K" add -A && git -C "$K" commit -q -m "skill conflict fixture"
(
  cd "$K" || exit 1
  bash "$H" apply
) >"$work/preflight-skill-conflict.out" 2>&1; rc=$?
check "skill projection conflict exits 2" test "$rc" = 2
check "skill projection conflict is explicit" grep -qF "projection conflict" "$work/preflight-skill-conflict.out"
check "skill projection conflict leaves repo unchanged" test -z "$(git -C "$K" status --porcelain --untracked-files=all)"

python "$SM" doctor --repo "$S" >/dev/null 2>&1; symlink_rc=$?
if [ "$symlink_rc" != 0 ]; then
  if [ "${AGENT_SCAFFOLD_E2E_REQUIRE_SYMLINKS:-${CI:+1}}" = 1 ]; then
    bad "real file/directory symlink capability is required for this run"
  else
    echo "  SKIP positive suite: this host lacks real symlink privilege (run agent-scaffold.sh doctor for remediation)"
  fi
  echo
  if [ "$fails" -eq 0 ]; then echo "OK: agent-scaffold negative e2e passed (positive suite skipped)"; exit 0; fi
  echo "FAIL: $fails agent-scaffold e2e assertion(s) failed"; exit 1
fi

echo "== managed directory symlinks cannot redirect writes outside the repo =="
K="$work/managed-root-symlink"; OUTSIDE="$work/managed-root-outside"
mkdir -p "$K/.claude" "$OUTSIDE"
git -C "$K" init -q -b main
git -C "$K" config user.email t@t.t; git -C "$K" config user.name tester
git -C "$K" config core.symlinks true
printf 'outside sentinel\n' > "$OUTSIDE/sentinel.txt"
python - "$K" "$OUTSIDE" <<'PY'
import os
from pathlib import Path
import sys

root, outside = map(Path, sys.argv[1:])
os.symlink(
    os.path.relpath(outside, root / ".claude"),
    root / ".claude/skills",
    target_is_directory=True,
)
PY
git -C "$K" add -A && git -C "$K" commit -q -m "managed root symlink fixture"
outside_before="$(git hash-object "$OUTSIDE/sentinel.txt")"
( cd "$K" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" apply ) \
  >"$work/managed-root-symlink.out" 2>&1; rc=$?
check "managed root symlink exits 2" test "$rc" = 2
check "managed root symlink is explicit" grep -qF "managed directory must not be a symlink" "$work/managed-root-symlink.out"
check "managed root rejection precedes capability probe" \
  no_fixed_text "$work/managed-root-symlink.out" "symlink capability denied by the test fixture"
check "external sentinel survives managed root rejection" \
  test "$(git hash-object "$OUTSIDE/sentinel.txt")" = "$outside_before"
check "managed root rejection leaves repo unchanged" test -z "$(git -C "$K" status --porcelain --untracked-files=all)"

echo "== subagent generator rejects symlinked projection roots =="
K="$work/generator-root-symlink"; OUTSIDE="$work/generator-root-outside"
mkdir -p "$K/.agents/tools" "$K/.agents/subagents/alpha" "$K/.claude" "$K/.codex" "$OUTSIDE"
cp "$repo/skills/agent-scaffold/assets/runtime/generate-subagents.py" "$K/.agents/tools/generate-subagents.py"
printf '%s\n' '{"name":"alpha","description":"root containment fixture"}' > "$K/.agents/subagents/alpha/metadata.json"
printf 'CONTAINED_SOURCE\n' > "$K/.agents/subagents/alpha/instructions.md"
printf 'outside sentinel\n' > "$OUTSIDE/sentinel.txt"
python - "$K" "$OUTSIDE" <<'PY'
import os
from pathlib import Path
import sys

root, outside = map(Path, sys.argv[1:])
os.symlink(
    os.path.relpath(outside, root / ".codex"),
    root / ".codex/agents",
    target_is_directory=True,
)
PY
outside_before="$(git hash-object "$OUTSIDE/sentinel.txt")"
( cd "$K" && python .agents/tools/generate-subagents.py ) \
  >"$work/generator-root-symlink.out" 2>&1; rc=$?
check "generator symlinked root exits nonzero" test "$rc" != 0
check "generator symlinked root is explicit" \
  grep -qF ".codex/agents: managed directory must not be a symlink" "$work/generator-root-symlink.out"
check "generator leaves external sentinel byte-identical" \
  test "$(git hash-object "$OUTSIDE/sentinel.txt")" = "$outside_before"
check "generator writes no sibling projection" test ! -e "$K/.claude/agents/alpha.md"

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
    bash "$H" apply --profile light
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

echo "== tracked target-text placeholders materialize as real links =="
fixture=target-text
  K="$work/positive-contract-$fixture"; mkdir -p "$K"
  git -C "$K" init -q -b main
  git -C "$K" config user.email t@t.t; git -C "$K" config user.name tester
  git -C "$K" config core.symlinks true
  printf '# Canonical contract\n' > "$K/AGENTS.md"
  printf 'AGENTS.md\n' > "$K/CLAUDE.md"
  git -C "$K" add -A && git -C "$K" commit -q -m "$fixture contract fixture"
  (
    cd "$K" || exit 1
    bash "$H" apply --profile light
  ) >"$work/positive-contract-$fixture.out" 2>&1; rc=$?
  check "$fixture contract apply exits 0" test "$rc" = 0
  check "$fixture contract becomes a real link" test -L "$K/CLAUDE.md"
  check "$fixture contract targets AGENTS.md" test "$(readlink "$K/CLAUDE.md")" = AGENTS.md
  check "$fixture contract keeps original prose" grep -qxF '# Canonical contract' "$K/AGENTS.md"
  check "$fixture contract has one managed block" \
    test "$(grep -cF '<!-- agent-scaffold:start' "$K/AGENTS.md")" = 1
  git -C "$K" add -A
  (cd "$K" && bash "$H" verify --profile light) \
    >"$work/positive-contract-$fixture-verify.out" 2>&1; rc=$?
  check "$fixture contract verifies" test "$rc" = 0
  mode="$(git -C "$K" ls-files -s -- CLAUDE.md | awk '{print $1}')"
  check "$fixture contract stages as a symlink" test "$mode" = 120000
  git -C "$K" commit -q -m "$fixture contract installed"
  (cd "$K" && bash "$H" apply --profile light) \
    >"$work/positive-contract-$fixture-rerun.out" 2>&1; rc=$?
  check "$fixture contract rerun exits 0" test "$rc" = 0
  check "$fixture contract rerun is idempotent" test -z "$(git -C "$K" status --porcelain)"

echo "== apply (greenfield) =="
# Existing text files need not end with a newline. Every managed append must
# preserve the old record and add the new record on its own line.
printf 'dist' > "$S/.gitignore"
printf '*.txt text' > "$S/.gitattributes"
printf '{"name":"fixture","scripts":{"test":"keep"}}\n' > "$S/package.json"
mkdir -p "$S/.husky"
printf '#!/usr/bin/env bash' > "$S/.husky/pre-commit"
package_before="$(git hash-object "$S/package.json")"
husky_before="$(git hash-object "$S/.husky/pre-commit")"
( cd "$S" && bash "$H" apply ) >/dev/null 2>&1 || bad "apply exited nonzero"
check "no bogus '*' symlink in .claude/skills" test -z "$(ls -A "$S/.claude/skills" 2>/dev/null)"
check "worktree.sh installed"                test -f "$S/.agents/tools/worktree.sh"
check "trunk_edit_guard.sh installed"        test -f "$S/.agents/tools/hooks/trunk_edit_guard.sh"
check "shared hook parser installed"         test -f "$S/.agents/tools/hooks/hook-paths.py"
check "greenfield install adds no tools root" test ! -e "$S/tools"
check "CLAUDE.md -> AGENTS.md symlink"        test "$(readlink "$S/CLAUDE.md")" = AGENTS.md
check "CC PreToolUse matcher"                jmatch "$S/.claude/settings.json" PreToolUse "Edit|MultiEdit|Write|NotebookEdit"
check "Codex PreToolUse matcher"             jmatch "$S/.codex/hooks.json"     PreToolUse "Edit|Write|apply_patch"
check "original gitignore line stays separate" grep -qxF "dist" "$S/.gitignore"
check "first gitignore append is separate"     grep -qxF ".claude/settings.local.json" "$S/.gitignore"
check ".gitignore ignores .worktrees/"       grep -qx ".worktrees/" "$S/.gitignore"
check "original attributes line stays separate" grep -qxF "*.txt text" "$S/.gitattributes"
check ".gitattributes pins LF on scripts"    grep -qxF ".agents/tools/*.sh text eol=lf" "$S/.gitattributes"
check ".gitattributes leaves Husky project-owned" no_exact_line "$S/.gitattributes" ".husky/pre-commit text eol=lf"
check "project-owned Husky hook is byte-identical" test "$(git hash-object "$S/.husky/pre-commit")" = "$husky_before"
check "project-owned package.json is byte-identical" test "$(git hash-object "$S/package.json")" = "$package_before"
check "package scripts are not scaffolded" no_fixed_text "$S/package.json" "generate-subagents.py"
check "greenfield creates no Codex config" test ! -e "$S/.codex/config.toml"
check "greenfield creates no example source" test ! -e "$S/.agents/subagents/code-reviewer"
check "greenfield creates no example projection" both_absent "$S/.claude/agents/code-reviewer.md" "$S/.codex/agents/code-reviewer.toml"
check "AGENTS.md contains no project overview" no_fixed_text "$S/AGENTS.md" "## Project Overview"
check "AGENTS.md starts at the managed boundary" grep -qF '<!-- agent-scaffold:start' "$S/AGENTS.md"
check "AGENTS.md carries the common authority laws" authority_laws_present "$S/AGENTS.md"
check "AGENTS.md keeps third-party policy project-owned" grep -qF "Third-party skills** follow project-owned placement and installation policy" "$S/AGENTS.md"
# shellcheck disable=SC2016  # backticks are literal Markdown in the rejected wording
check "AGENTS.md omits unconditional third-party placement" no_fixed_text "$S/AGENTS.md" 'they land as real dirs in `.claude/skills/`'
# shellcheck disable=SC2016  # backticks are literal Markdown in the expected table row
check "managed table keeps its closing cell spacing" grep -qF '| `.agents/tools/worktree.sh` | worktree lifecycle | ✅ |' "$S/AGENTS.md"
check "resident skill README stays thin" test "$(wc -l < "$S/.agents/skills/README.md" | tr -d ' ')" -le 24
check "resident skill README routes to depth" grep -qF 'references/harness-layout.md' "$S/.agents/skills/README.md"
check "resident subagent README stays thin" test "$(wc -l < "$S/.agents/subagents/README.md" | tr -d ' ')" -le 26
check "resident subagent README routes to example" grep -qF 'references/subagents.md' "$S/.agents/subagents/README.md"

echo "== installed command entry points fail closed =="
( cd "$S" && bash "$H" --help --not-a-real-option ) >"$work/harness-help-unknown.out" 2>&1; rc=$?
check "harness help does not mask unknown arguments" test "$rc" = 2
( cd "$S" && bash "$H" apply --help --not-a-real-option ) >"$work/harness-mode-help-unknown.out" 2>&1; rc=$?
check "mode help does not mask unknown arguments" test "$rc" = 2
( cd "$S" && bash "$H" apply --help ) >/dev/null 2>&1; rc=$?
check "pure mode help exits 0" test "$rc" = 0
WT_CLI="$S/.agents/tools/worktree.sh"
for args in \
  "--help --not-a-real-option" \
  "list unexpected" \
  "release HEAD unexpected" \
  "new --type" \
  "done --dir"; do
  # shellcheck disable=SC2086  # deliberate argument-vector fixtures
  ( cd "$S" && bash "$WT_CLI" $args ) >"$work/worktree-invalid.out" 2>&1; rc=$?
  check "worktree rejects invalid arguments: $args" test "$rc" = 2
done
( cd "$S" && bash "$WT_CLI" list --help ) >/dev/null 2>&1; rc=$?
check "pure worktree subcommand help exits 0" test "$rc" = 0
( cd "$S" && bash .agents/relink-skills.sh --help --not-a-real-option ) \
  >"$work/relink-help-unknown.out" 2>&1; rc=$?
check "relink help does not mask unknown arguments" test "$rc" = 2
( cd "$S" && bash .agents/relink-skills.sh --help ) >/dev/null 2>&1; rc=$?
check "pure relink help exits 0" test "$rc" = 0

( cd "$S" && bash "$H" plan --json ) >"$work/plan.json" 2>&1; rc=$?
check "plan JSON exits 0" test "$rc" = 0
check "plan JSON has stable schema and check fields" python - "$work/plan.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
required = {"id", "status", "path", "fix"}
raise SystemExit(
    data.get("schema_version") != 1
    or data.get("mode") != "plan"
    or data.get("apply_mode") not in {"apply", "upgrade"}
    or any(not required <= set(item) for item in data.get("checks", []))
)
PY

git -C "$S" add -A
# shellcheck disable=SC2016  # sh -c expands its own positional parameters
check "tracked CLAUDE.md mode is 120000"     sh -c '[ "$(git -C "$1" ls-files -s -- CLAUDE.md | awk '\''{print $1}'\'')" = 120000 ]' _ "$S"

echo "== idempotent re-run =="
python - "$S/.gitignore" "$S/.gitattributes" <<'PY'
from pathlib import Path
import sys

fixtures = (
    (sys.argv[1], b".claude/settings.local.json\n", b".claude/settings.local.json\r\n"),
    (sys.argv[2], b".agents/tools/*.sh text eol=lf\n", b".agents/tools/*.sh text eol=lf\r\n"),
)
for name, old, new in fixtures:
    path = Path(name)
    data = path.read_bytes()
    assert data.count(old) == 1
    path.write_bytes(data.replace(old, new, 1))
PY
( cd "$S" && bash "$H" apply ) >/dev/null 2>&1; rc=$?
check "apply re-run exits 0"              test "$rc" = 0
check "PostToolUse stays 1 hook (no dup)"    jcount "$S/.claude/settings.json" PostToolUse 1
check "CRLF gitignore target stays singular" logical_line_count "$S/.gitignore" ".claude/settings.local.json" 1
check "CRLF attributes target stays singular" logical_line_count "$S/.gitattributes" ".agents/tools/*.sh text eol=lf" 1
check "rerun preserves project-owned Husky hook" test "$(git hash-object "$S/.husky/pre-commit")" = "$husky_before"
check "rerun preserves project-owned package.json" test "$(git hash-object "$S/package.json")" = "$package_before"

echo "== apply propagates subagent import rejection =="
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
import_out="$work/import-propagation-apply.out"
( cd "$S" && bash "$H" apply ) >"$import_out" 2>&1; rc=$?
check "apply propagates import rejection"         test "$rc" != 0
check "apply surfaces divergent instructions"     grep -qF "have different instructions; resolve the conflict before --import" "$import_out"
check "apply does not downgrade import rejection" no_fixed_text "$import_out" "generate-subagents.py --import returned nonzero"
check "failed apply omits completion banner"      no_fixed_text "$import_out" "harness apply complete."
check "failed apply preserves Claude input"       test "$(git hash-object "$S/.claude/agents/import-propagation.md")" = "$import_cc_before"
check "failed apply preserves Codex input"        test "$(git hash-object "$S/.codex/agents/import-propagation.toml")" = "$import_cx_before"
check "failed apply writes no partial SSOT"       test ! -e "$S/.agents/subagents/import-propagation"
rm -f "$S/.claude/agents/import-propagation.md" "$S/.codex/agents/import-propagation.toml"

echo "== apply-merge preserves a pre-existing user hook =="
python - "$S/.claude/settings.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["hooks"]["PreToolUse"][0]["hooks"].append({"type": "command", "command": "user-custom.sh"})
json.dump(d, open(p, "w"))
PY
( cd "$S" && bash "$H" apply ) >/dev/null 2>&1; rc=$?
check "apply-merge exits 0"               test "$rc" = 0
check "trunk_edit_guard still wired"         grep -q trunk_edit_guard "$S/.claude/settings.json"
check "pre-existing user hook preserved"     grep -q user-custom "$S/.claude/settings.json"

echo "== worktree round-trip =="
git -C "$S" add -A && git -C "$S" commit -q -m harness
( cd "$S" && bash .agents/tools/worktree.sh new demo --type chore ) >/dev/null 2>&1
check "worktree .worktrees/demo created"     test -d "$S/.worktrees/demo"
( cd "$S/.worktrees/demo" && echo hi > note.txt && git add -A && git commit -q -m "feat: note" \
  && bash .agents/tools/worktree.sh "done" --no-push ) >/dev/null 2>&1
check "worktree removed after done"          test ! -d "$S/.worktrees/demo"
merge_subject="$(git -C "$S" log -1 --format=%s)"
check "merge commit landed on main"          test "$merge_subject" = "Merge branch 'chore/demo'"

echo "== detached release worktree uses guarded done cleanup =="
release_out="$work/worktree-release-create.out"
( cd "$S" && bash .agents/tools/worktree.sh release ':/harness' ) >"$release_out" 2>&1; rc=$?
RELEASE_WT="$(sed -n 's/^.*ready: \(.*\)  (detached.*/\1/p' "$release_out" | tail -1)"
check "release worktree creation exits 0" test "$rc" = 0
check "release worktree is created" test -d "$RELEASE_WT"
check "release worktree is detached" test -z "$(git -C "$RELEASE_WT" symbolic-ref -q HEAD 2>/dev/null)"
case "$(basename "$RELEASE_WT")" in
  *[!A-Za-z0-9._-]*) portable_release_path=0 ;;
  *) portable_release_path=1 ;;
esac
check "release revision expression gets a portable basename" test "$portable_release_path" = 1
release_cleanup_command="$(sed -n 's/^.*done: //p' "$release_out" | tail -1)"
release_cleanup_command="${release_cleanup_command%$'\r'}"
CANONICAL_S="$(git -C "$S" rev-parse --show-toplevel)"
check "release cleanup command quotes helper path" \
  grep -qF "bash \"$CANONICAL_S/.agents/tools/worktree.sh\"" "$release_out"
check "release cleanup command quotes worktree path" \
  grep -qF -- "--dir \"$RELEASE_WT\"" "$release_out"
printf 'package output\n' > "$RELEASE_WT/package-output.txt"
release_dirty_out="$work/worktree-release-dirty.out"
bash -c "$release_cleanup_command" >"$release_dirty_out" 2>&1; rc=$?
check "dirty release cleanup exits 2" test "$rc" = 2
check "dirty release worktree remains" test -d "$RELEASE_WT"
check "dirty release cleanup explains refusal" grep -qF "worktree is dirty" "$release_dirty_out"
rm -f -- "$RELEASE_WT/package-output.txt"
release_done_out="$work/worktree-release-done.out"
bash -c "$release_cleanup_command" >"$release_done_out" 2>&1; rc=$?
check "clean release cleanup exits 0" test "$rc" = 0
check "clean release worktree is removed" test ! -d "$RELEASE_WT"
check "release cleanup uses guarded path" grep -qF "removed clean detached release worktree" "$release_done_out"
check "release workflow never recommends force removal" no_fixed_text "$release_out" "--force"

echo "== worktree cleanup never force-deletes post-preflight data =="
WS="$work/worktree-cleanup-safety"; mkdir -p "$WS"
git -C "$WS" init -q -b main
git -C "$WS" config user.email t@t.t; git -C "$WS" config user.name tester
WS_WT_HELPER="$WS/.agents/tools/worktree.sh"
mkdir -p "$(dirname "$WS_WT_HELPER")"
cp "$repo/skills/agent-scaffold/assets/runtime/worktree.sh" "$WS_WT_HELPER"
chmod +x "$WS_WT_HELPER"
printf 'base\n' > "$WS/base.txt"
git -C "$WS" add base.txt .agents/tools/worktree.sh && git -C "$WS" commit -q -m base
printf '.worktrees/\ntest-bin/\n' > "$WS/.git/info/exclude"
mkdir -p "$WS/test-bin"
cat > "$WS/test-bin/git" <<'SH'
#!/usr/bin/env bash
if [[ "${1:-}" == worktree && "${2:-}" == remove ]]; then
  printf '%s\n' "$*" >> "${WORKTREE_REMOVE_LOG:?}"
fi
if [[ "${SIMULATE_PARTIAL_REMOVE:-0}" == 1 && "${1:-}" == worktree && "${2:-}" == remove && "${3:-}" != --force ]]; then
  "$REAL_GIT" "$@"
  status=$?
  [[ $status -eq 0 ]] || exit "$status"
  mkdir -p "$3"
  printf 'must remain\n' > "$3/locked-residue.txt"
  exit 1
fi
if [[ "${SIMULATE_POST_PREFLIGHT_WRITE:-0}" == 1 && "${1:-}" == worktree && "${2:-}" == remove && "${3:-}" != --force ]]; then
  printf 'must survive\n' > "$3/precious-untracked.txt"
  "$REAL_GIT" "$@"
  exit $?
fi
exec "$REAL_GIT" "$@"
SH
chmod +x "$WS/test-bin/git"
WT_REMOVE_LOG="$WS/.git/worktree-remove.log"; : > "$WT_REMOVE_LOG"
( cd "$WS" && bash "$WS_WT_HELPER" new partial-remove --type fix ) >/dev/null 2>&1
PARTIAL_WT="$WS/.worktrees/partial-remove"
printf 'partial\n' > "$PARTIAL_WT/change.txt"
git -C "$PARTIAL_WT" add change.txt && git -C "$PARTIAL_WT" commit -q -m "partial removal"
(
  cd "$WS" || exit 1
  REAL_GIT="$(command -v git)" WORKTREE_REMOVE_LOG="$WT_REMOVE_LOG" \
    PATH="$WS/test-bin:$PATH" SIMULATE_PARTIAL_REMOVE=1 \
    bash "$WS_WT_HELPER" "done" --dir "$PARTIAL_WT" --no-push
) >"$work/worktree-partial-remove.out" 2>&1; rc=$?
check "unregistered partial removal still completes cleanup" test "$rc" = 0
check "partial removal explains the unregistered state" grep -qF "already unregistered" "$work/worktree-partial-remove.out"
check "partial removal keeps non-empty residue" test -f "$PARTIAL_WT/locked-residue.txt"
check "partial removal drops the merged branch" test -z "$(git -C "$WS" branch --list fix/partial-remove)"
check "partial removal is absent from the registry" no_fixed_text <(git -C "$WS" worktree list --porcelain) "partial-remove"

( cd "$WS" && bash "$WS_WT_HELPER" new post-preflight --type fix ) >/dev/null 2>&1
POST_WT="$WS/.worktrees/post-preflight"
printf 'post\n' > "$POST_WT/change.txt"
git -C "$POST_WT" add change.txt && git -C "$POST_WT" commit -q -m "post-preflight write"
(
  cd "$WS" || exit 1
  REAL_GIT="$(command -v git)" WORKTREE_REMOVE_LOG="$WT_REMOVE_LOG" \
    PATH="$WS/test-bin:$PATH" SIMULATE_POST_PREFLIGHT_WRITE=1 \
    bash "$WS_WT_HELPER" "done" --dir "$POST_WT" --no-push
) >"$work/worktree-post-preflight.out" 2>&1; rc=$?
check "post-preflight data aborts worktree cleanup" test "$rc" = 2
check "post-preflight data survives" test -f "$POST_WT/precious-untracked.txt"
check "registered failure keeps the feature branch" test -n "$(git -C "$WS" branch --list fix/post-preflight)"
check "registered failure remains in the registry" grep -qF "post-preflight" <(git -C "$WS" worktree list --porcelain)
check "registered failure explains force-removal refusal" grep -qF "refusing force removal" "$work/worktree-post-preflight.out"
check "cleanup never invokes worktree remove --force" no_fixed_text "$WT_REMOVE_LOG" "--force"

( cd "$WS" && bash "$WS_WT_HELPER" new unsafe-registry --type fix ) >/dev/null 2>&1
UNSAFE_REGISTRY_WT="$WS/.worktrees/unsafe-registry"
printf 'registry\n' > "$UNSAFE_REGISTRY_WT/change.txt"
git -C "$UNSAFE_REGISTRY_WT" add change.txt && git -C "$UNSAFE_REGISTRY_WT" commit -q -m "unsafe registry temp"
registry_sentinel="$WS/.git/registry-sentinel.txt"
printf 'must remain byte-identical\n' > "$registry_sentinel"
registry_before="$(git hash-object "$registry_sentinel")"
(
  cd "$WS" || exit 1
  REAL_GIT="$(command -v git)" WORKTREE_REMOVE_LOG="$WT_REMOVE_LOG" \
    PATH="$MKTEMP_BIN:$WS/test-bin:$PATH" SIMULATE_POST_PREFLIGHT_WRITE=1 \
    FAKE_MKTEMP_MODE=unsafe FAKE_MKTEMP_UNSAFE="$registry_sentinel" \
    bash "$WS_WT_HELPER" "done" --dir "$UNSAFE_REGISTRY_WT" --no-push
) >"$work/worktree-unsafe-registry.out" 2>&1; rc=$?
check "unsafe registry temp exits 2" test "$rc" = 2
check "unsafe registry temp is rejected" \
  grep -qF "mktemp returned an unsafe worktree registry path" "$work/worktree-unsafe-registry.out"
check "unsafe registry temp preserves sentinel" \
  test "$(git hash-object "$registry_sentinel")" = "$registry_before"
check "unsafe registry temp keeps post-preflight data" \
  test -f "$UNSAFE_REGISTRY_WT/precious-untracked.txt"
check "unsafe registry temp keeps registration" \
  grep -qF "unsafe-registry" <(git -C "$WS" worktree list --porcelain)

echo "== trunk guard: block on main + escape hatch =="
g="$S/.agents/tools/hooks/trunk_edit_guard.sh"
guard_block_out="$work/trunk-guard-block.out"
printf '{"tool_input":{"file_path":"%s/AGENTS.md"}}' "$S" | CLAUDE_PROJECT_DIR="$S" bash "$g" >"$guard_block_out" 2>&1; rc=$?
check "blocks a tracked main edit (exit 2)"  test "$rc" = 2
check "block message requires explicit trunk-edit authorization" \
  grep -qF "Only if the user explicitly authorized a trunk edit in this conversation:" "$guard_block_out"
check "block message never lowers authorization to mentioning trunk" \
  no_fixed_text "$guard_block_out" "explicitly named a trunk"
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
    check "hook runtime converts drive paths" bash -c 'source "$1"; [[ "$(hook_posix_path "C:\\Temp\\x")" == /c/Temp/x ]]' _ "$S/.agents/tools/hooks/hook-common.sh"
    # shellcheck disable=SC2016
    check "hook runtime preserves UNC shape" bash -c 'source "$1"; [[ "$(hook_posix_path "\\\\server\\share\\x")" == //server/share/x ]]' _ "$S/.agents/tools/hooks/hook-common.sh"
    # shellcheck disable=SC2016
    check "hook runtime accepts Git Bash paths" bash -c 'source "$1"; [[ "$(hook_posix_path "/c/Temp/x")" == /c/Temp/x ]]' _ "$S/.agents/tools/hooks/hook-common.sh"
    ;;
esac

echo "== authority budgets classify root and nested contracts across path namespaces =="
budget_hook="$S/.agents/tools/hooks/authority_doc_budget.sh"
mkdir -p "$S/docs/budget-fixture"
printf 'nested\nentry\n' > "$S/docs/budget-fixture/AGENTS.md"
budget_root="$S"
root_contract="$S/AGENTS.md"
nested_contract="$S/docs/budget-fixture/AGENTS.md"
case "$(uname -s)" in
  MINGW* | MSYS*)
    budget_root="$(cygpath -w "$budget_root")"
    root_contract="$(cygpath -w "$root_contract")"
    nested_contract="$(cygpath -w "$nested_contract")"
    ;;
esac
python -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_input":{"file_path":sys.argv[2]}}))' \
  "$budget_root" "$root_contract" \
  | CLAUDE_PROJECT_DIR="$budget_root" AUTHORITY_DOC_MAX_ROOT=9999 AUTHORITY_DOC_MAX_NESTED=1 \
      bash "$budget_hook" >"$work/root-budget.out" 2>&1; rc=$?
check "root budget hook exits 0" test "$rc" = 0
check "root contract uses the root budget" no_fixed_text "$work/root-budget.out" "budget exceeded"
python -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_input":{"file_path":sys.argv[2]}}))' \
  "$budget_root" "$nested_contract" \
  | CLAUDE_PROJECT_DIR="$budget_root" AUTHORITY_DOC_MAX_ROOT=9999 AUTHORITY_DOC_MAX_NESTED=1 \
      bash "$budget_hook" >"$work/nested-budget.out" 2>&1; rc=$?
check "nested budget hook exits 0" test "$rc" = 0
check "nested contract uses the nested budget" grep -qF "docs/budget-fixture/AGENTS.md" "$work/nested-budget.out"
check "nested contract reports budget 1" grep -qF "budget 1" "$work/nested-budget.out"
budget_resolver_bin="$work/budget-python-resolver"; mkdir -p "$budget_resolver_bin"
for candidate in explicit-python "explicit python" python python3 py; do
  cp "$resolver_bin/python-shim" "$budget_resolver_bin/$candidate"
  chmod +x "$budget_resolver_bin/$candidate"
done
resolver_log="$work/budget-python3-fallback.log"; : > "$resolver_log"
python -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_input":{"file_path":sys.argv[2]}}))' \
  "$budget_root" "$nested_contract" \
  | PATH="$budget_resolver_bin:$PATH" REAL_PYTHON="$real_python" PYTHON_RESOLVER_LOG="$resolver_log" \
      PYTHON_BIN="$budget_resolver_bin/explicit-python" RESOLVER_EXPLICIT_MODE=broken \
      RESOLVER_PYTHON_MODE=py37 RESOLVER_PYTHON3_MODE=py38 RESOLVER_PY_MODE=broken \
      CLAUDE_PROJECT_DIR="$budget_root" AUTHORITY_DOC_MAX_ROOT=9999 AUTHORITY_DOC_MAX_NESTED=9999 \
      AUTHORITY_DOC_MAX_ROOT_CHARS=999999 AUTHORITY_DOC_MAX_NESTED_CHARS=1 \
      bash "$budget_hook" >"$work/nested-character-budget.out" 2>&1; rc=$?
check "character budget hook exits 0" test "$rc" = 0
check "nested contract uses the character budget" grep -qF "13 characters (budget 1" "$work/nested-character-budget.out"
check "character budget uses compatible hook Python" test "$(grep -c '^python3:exec$' "$resolver_log")" -ge 2
rm -rf "$S/docs/budget-fixture"

echo "== relink coexistence with an npx-installed skill =="
mkdir -p "$S/.agents/skills/proj-skill"; printf -- '---\nname: proj-skill\n---\n' > "$S/.agents/skills/proj-skill/SKILL.md"
mkdir -p "$S/.claude/skills/vendor-skill"; echo x > "$S/.claude/skills/vendor-skill/SKILL.md"
mkdir -p "$S/.claude/skills/.proj-skill.agent-scaffold-link"
printf 'unrelated project data\n' > "$S/.claude/skills/.proj-skill.agent-scaffold-link/sentinel.txt"
( cd "$S" && bash .agents/relink-skills.sh ) >/dev/null 2>&1
check "project skill symlinked into .claude/skills" test -L "$S/.claude/skills/proj-skill"
{ test -d "$S/.claude/skills/vendor-skill" && ! test -L "$S/.claude/skills/vendor-skill"; }; rc=$?
check "npx-installed real dir left untouched" test "$rc" = 0
check "legacy temp-name directory left untouched" \
  test -f "$S/.claude/skills/.proj-skill.agent-scaffold-link/sentinel.txt"

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
( cd "$S" && bash "$H" doctor --json ) >"$work/doctor.json" 2>&1; rc=$?
check "doctor JSON exits 0" test "$rc" = 0
check "doctor JSON carries stable real-link check" python - "$work/doctor.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
checks = {item["id"]: item for item in data["checks"]}
raise SystemExit(
    data.get("schema_version") != 1
    or data.get("mode") != "doctor"
    or checks.get("prerequisite.real-symlinks", {}).get("status") != "pass"
)
PY
( cd "$S" && bash "$H" verify ) >"$work/verify.out" 2>&1; rc=$?
if [ "$rc" != 0 ]; then
  sed 's/^/  verify> /' "$work/verify.out" >&2
fi
check "verify reports harness OK (exit 0)"   test "$rc" = 0
( cd "$S" && bash "$H" verify --json ) >"$work/verify.json" 2>&1; rc=$?
check "verify JSON exits 0" test "$rc" = 0
check "verify JSON carries stable current-contract checks" python - "$work/verify.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
required = {"id", "status", "path", "fix"}
raise SystemExit(
    data.get("mode") != "verify"
    or not data.get("ok")
    or any(not required <= set(item) for item in data.get("checks", []))
)
PY

cp "$S/AGENTS.md" "$work/agents.clean.md"
python - "$S/AGENTS.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
path.write_text(text.replace("canonical repository-level contract for Agent work", "BROKEN MANAGED AUTHORITY CONTRACT", 1), encoding="utf-8")
PY
( cd "$S" && bash "$H" verify --json ) >"$work/verify-agents-drift.json" 2>&1; rc=$?
check "verify rejects managed AGENTS block drift" test "$rc" != 0
check "managed block drift has a stable check" python - "$work/verify-agents-drift.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
item = next(check for check in data["checks"] if check["id"] == "contract.agents-content")
raise SystemExit(item["status"] != "fail" or "apply" not in (item["fix"] or ""))
PY
mv "$work/agents.clean.md" "$S/AGENTS.md"

cp "$S/.gitattributes" "$work/gitattributes.clean"
python - "$S/.gitattributes" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line != ".agents/*.py text eol=lf"]
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
( cd "$S" && bash "$H" verify --json ) >"$work/verify-attributes-drift.json" 2>&1; rc=$?
check "verify rejects missing gitattributes invariant" test "$rc" != 0
check "gitattributes drift has a stable check" python - "$work/verify-attributes-drift.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
item = next(check for check in data["checks"] if check["id"] == "contract.gitattributes")
raise SystemExit(item["status"] != "fail" or ".agents/*.py text eol=lf" not in item.get("detail", ""))
PY
mv "$work/gitattributes.clean" "$S/.gitattributes"

echo "== verify rejects active-profile drift and hook mismatches =="
cp "$S/.claude/settings.json" "$work/claude-settings.clean.json"
cp "$S/.codex/hooks.json" "$work/codex-hooks.clean.json"
python - "$S/.claude/settings.json" "$S/.codex/hooks.json" <<'PY'
import json, sys
for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as source:
        data = json.load(source)
    data["hooks"]["PostToolUse"][0]["hooks"].append({
        "type": "command",
        "command": "bash .agents/hooks/format-on-edit.sh",
    })
    with open(path, "w", encoding="utf-8") as target:
        json.dump(data, target, indent=2, ensure_ascii=False)
        target.write("\n")
PY
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "verify preserves a project-owned formatter hook" test "$rc" = 0
mv "$work/claude-settings.clean.json" "$S/.claude/settings.json"
mv "$work/codex-hooks.clean.json" "$S/.codex/hooks.json"
cp "$S/.agents/tools/generate-subagents.py" "$work/generate-subagents.clean.py"
printf '\n# generator drift fixture\n' >> "$S/.agents/tools/generate-subagents.py"
( cd "$S" && bash "$H" verify --json ) >"$work/verify-drift.json" 2>&1; rc=$?
check "verify rejects generator byte drift" test "$rc" != 0
check "verify drift JSON names the asset and fix" python - "$work/verify-drift.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
check = next(item for item in data["checks"] if item["id"] == "runtime.subagent-generator")
raise SystemExit(check["status"] != "fail" or "upgrade" not in (check["fix"] or ""))
PY
mv "$work/generate-subagents.clean.py" "$S/.agents/tools/generate-subagents.py"
mv "$S/.agents/tools/generate-subagents.py" "$work/generate-subagents.missing.py"
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "verify rejects missing generator" test "$rc" != 0
mv "$work/generate-subagents.missing.py" "$S/.agents/tools/generate-subagents.py"

echo "== upgrade refreshes only current managed runtime =="
printf '\n# runtime drift fixture\n' >> "$S/.agents/tools/worktree.sh"
( cd "$S" && bash "$H" apply ) >"$work/apply-runtime-drift.out" 2>&1; rc=$?
check "apply rejects managed runtime drift" test "$rc" = 2
check "apply directs runtime drift to upgrade" grep -qF "managed runtime drift requires upgrade" "$work/apply-runtime-drift.out"
check "failed apply preserves the drifted runtime" grep -qF "runtime drift fixture" "$S/.agents/tools/worktree.sh"
( cd "$S" && bash "$H" plan --json ) >"$work/upgrade-plan.json" 2>&1; rc=$?
check "drift plan exits 0" test "$rc" = 0
check "drift plan selects upgrade" python -c \
  'import json,sys; raise SystemExit(json.load(open(sys.argv[1]))["apply_mode"] != "upgrade")' \
  "$work/upgrade-plan.json"
( cd "$S" && bash "$H" upgrade ) >/dev/null 2>&1; rc=$?
check "current-layout upgrade exits 0" test "$rc" = 0
check "upgrade refreshes the drifted runtime" cmp -s \
  "$repo/skills/agent-scaffold/assets/runtime/worktree.sh" "$S/.agents/tools/worktree.sh"
check "upgrade preserves project-owned Husky hook" test "$(git hash-object "$S/.husky/pre-commit")" = "$husky_before"
check "upgrade preserves project-owned package.json" test "$(git hash-object "$S/package.json")" = "$package_before"
( cd "$S" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "refreshed current layout verifies" test "$rc" = 0

echo "== lightweight profile: --profile light omits the complete worktree policy =="
L="$work/lightweight"; mkdir -p "$L"
git -C "$L" init -q -b main
git -C "$L" config user.email t@t.t; git -C "$L" config user.name tester
git -C "$L" config core.symlinks true
git -C "$L" commit -q --allow-empty -m init
( cd "$L" && bash "$H" apply --profile light ) >/dev/null 2>&1; rc=$?
check "light-profile apply exits 0"                test "$rc" = 0
check "light-profile omits worktree.sh"            test ! -e "$L/.agents/tools/worktree.sh"
check "light-profile omits trunk guard script"     test ! -e "$L/.agents/tools/hooks/trunk_edit_guard.sh"
check "Claude config omits trunk guard"          jcommand_count "$L/.claude/settings.json" trunk_edit_guard 0
check "Codex config omits trunk guard"           jcommand_count "$L/.codex/hooks.json" trunk_edit_guard 0
check "authority hook remains wired"             jcommand_count "$L/.claude/settings.json" authority_doc_budget 1
check "managed AGENTS block omits hard rule"     no_fixed_text "$L/AGENTS.md" "Worktree-per-change (hard rule)"
check "light-profile keeps common authority laws" authority_laws_present "$L/AGENTS.md"
check "light-profile omits .worktrees ignore"      no_exact_line "$L/.gitignore" ".worktrees/"
check "light-profile omits escape-hatch ignore"    no_exact_line "$L/.gitignore" ".claude/allow-trunk-edit"
check "light-profile keeps the real-link contract" test "$(readlink "$L/CLAUDE.md")" = AGENTS.md
( cd "$L" && bash "$H" verify --profile light ) >/dev/null 2>&1; rc=$?
check "light-profile verify accepts light profile" test "$rc" = 0
( cd "$L" && bash "$H" verify ) >/dev/null 2>&1; rc=$?
check "default verify detects omitted workflow"  test "$rc" != 0
git -C "$L" add -A && git -C "$L" commit -q -m "light harness"
( cd "$L" && bash "$H" apply --profile light ) >/dev/null 2>&1; rc=$?
check "light-profile apply re-run exits 0"       test "$rc" = 0
check "light-profile apply is idempotent"        test -z "$(git -C "$L" status --porcelain)"
( cd "$L" && bash "$H" upgrade ) >/dev/null 2>&1; rc=$?
check "default upgrade re-enables worktree flow" test "$rc" = 0
check "re-enabled worktree.sh is installed"      test -f "$L/.agents/tools/worktree.sh"
check "re-enabled Claude guard is wired once"    jcommand_count "$L/.claude/settings.json" trunk_edit_guard 1
check "re-enabled AGENTS block has hard rule"    grep -qF "Worktree-per-change (hard rule)" "$L/AGENTS.md"

echo "== plan + apply adopt a real CLAUDE.md into AGENTS.md =="
M="$work/adopt-contract"; mkdir -p "$M"
git -C "$M" init -q -b main
git -C "$M" config user.email t@t.t; git -C "$M" config user.name tester
git -C "$M" commit -q --allow-empty -m init
printf '# Existing Contract\n\nHand-written agent rules to keep.\n' > "$M/CLAUDE.md"
git -C "$M" add -A && git -C "$M" commit -q -m "pre-existing CLAUDE.md"
before="$( { find "$M" -type f; find "$M" -type l; } | sort )"
( cd "$M" && bash "$H" plan ) >"$work/plan.out" 2>&1; rc=$?
after="$( { find "$M" -type f; find "$M" -type l; } | sort )"
check "plan exits 0"                          test "$rc" = 0
check "plan makes no filesystem change"       test "$before" = "$after"
check "plan flags CLAUDE.md prose adoption"  grep -qF "adopt prose from CLAUDE.md" "$work/plan.out"
( cd "$M" && bash "$H" apply ) >/dev/null 2>&1; rc=$?
check "apply exits 0"                      test "$rc" = 0
check "AGENTS.md keeps the original prose"    grep -q "Hand-written agent rules to keep" "$M/AGENTS.md"
check "AGENTS.md gains the harness block"     grep -qF "<!-- agent-scaffold:start" "$M/AGENTS.md"
check "adopted AGENTS.md gains common authority laws" authority_laws_present "$M/AGENTS.md"
check "CLAUDE.md is now a symlink to AGENTS.md" test "$(readlink "$M/CLAUDE.md")" = AGENTS.md

echo "== apply adopts hand-authored subagents into the SSOT (python, no package.json) =="
A="$work/adopt"; mkdir -p "$A/.claude/agents"
git -C "$A" init -q -b main
git -C "$A" config user.email t@t.t; git -C "$A" config user.name tester
git -C "$A" commit -q --allow-empty -m init
printf -- '---\nname: custom-rev\ndescription: hand-authored reviewer\ntools: Read, Grep\n---\n\nReview the diff and report.\n' > "$A/.claude/agents/custom-rev.md"
git -C "$A" add -A && git -C "$A" commit -q -m "hand-authored subagent"
( cd "$A" && bash "$H" apply ) >/dev/null 2>&1; rc=$?
check "apply exits 0"                          test "$rc" = 0
check "adopted without creating a package.json"   test ! -f "$A/package.json"
check "hand-authored agent adopted into SSOT"     test -f "$A/.agents/subagents/custom-rev/metadata.json"
check "adopted metadata keeps the tools"          grep -q Read "$A/.agents/subagents/custom-rev/metadata.json"
check "CC projection regenerated with banner"     grep -q "do not edit by hand" "$A/.claude/agents/custom-rev.md"
check "Codex projection generated"                test -f "$A/.codex/agents/custom-rev.toml"
( cd "$A" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "subagent projections in sync after adopt"  test "$rc" = 0
printf -- '---\nname: ghost\ndescription: no source\n---\n\nbody\n' > "$A/.claude/agents/ghost.md"
( cd "$A" && python .agents/tools/generate-subagents.py ) >/dev/null 2>&1
check "sourceless hand-authored projection not pruned" test -f "$A/.claude/agents/ghost.md"

echo "== hardening: deep-review regression fixes =="
# PY_MERGE: apply over an existing config whose "hooks" is null must not crash on
# the python path (jq coped via // {}) and must preserve the user's other keys.
HN="$work/hooksnull"; mkdir -p "$HN/.claude"
git -C "$HN" init -q -b main
git -C "$HN" config user.email t@t.t; git -C "$HN" config user.name tester
git -C "$HN" commit -q --allow-empty -m init
printf '{"hooks": null, "model": "opus"}' > "$HN/.claude/settings.json"
( cd "$HN" && HARNESS_NO_JQ=1 bash "$H" apply ) >/dev/null 2>&1; rc=$?
check "apply over hooks:null (python path) exits 0"   test "$rc" = 0
check "hooks:null apply preserves user's other keys"  grep -q '"model"' "$HN/.claude/settings.json"
check "hooks:null apply wires the trunk guard"        grep -q trunk_edit_guard "$HN/.claude/settings.json"

# M3: a hand-authored agent whose PROSE contains the phrase "do not edit by hand"
# must still be adopted by --import (the banner test keys on "Generated from
# .agents/subagents/", not the loose phrase). Reuses the adopt repo $A.
printf -- '---\nname: phrase-rev\ndescription: mentions the banner phrase\n---\n\nRule: do not edit by hand-written config.\n' > "$A/.claude/agents/phrase-rev.md"
( cd "$A" && python .agents/tools/generate-subagents.py --import ) >/dev/null 2>&1
check "hand-authored agent w/ banner phrase in prose still adopted (M3)" test -f "$A/.agents/subagents/phrase-rev/metadata.json"

# M1: metadata.json without a non-empty description must fail fast, not emit "None".
DN="$work/nodesc"; mkdir -p "$DN/.agents/subagents/x" "$DN/.agents/tools"
cp "$repo/.agents/tools/generate-subagents.py" "$DN/.agents/tools/generate-subagents.py"
printf '{"name":"x"}' > "$DN/.agents/subagents/x/metadata.json"
printf 'body\n' > "$DN/.agents/subagents/x/instructions.md"
( cd "$DN" && python .agents/tools/generate-subagents.py ) >/dev/null 2>&1; rc=$?
check "metadata without description fails fast (M1)"     test "$rc" != 0

# m1: malformed metadata.json gives a friendly, named error — no raw python traceback.
MJ="$work/badjson"; mkdir -p "$MJ/.agents/subagents/y" "$MJ/.agents/tools"
cp "$repo/.agents/tools/generate-subagents.py" "$MJ/.agents/tools/generate-subagents.py"
printf '{not json' > "$MJ/.agents/subagents/y/metadata.json"
printf 'body\n' > "$MJ/.agents/subagents/y/instructions.md"
( cd "$MJ" && python .agents/tools/generate-subagents.py ) >"$work/badjson.out" 2>&1; rc=$?
check "malformed metadata.json exits nonzero (m1)"       test "$rc" != 0
check "malformed metadata.json names subagent + reason (m1)" grep -qF "subagent 'y': metadata.json is not valid JSON" "$work/badjson.out"
# shellcheck disable=SC2016  # $1 is sh -c's own positional; the outer shell must NOT expand it
check "malformed metadata.json prints no python traceback (m1)" sh -c '! grep -q Traceback "$1"' _ "$work/badjson.out"

echo
if [ "$fails" -eq 0 ]; then echo "OK: agent-scaffold e2e passed"; exit 0; fi
echo "FAIL: $fails agent-scaffold e2e assertion(s) failed"; exit 1
