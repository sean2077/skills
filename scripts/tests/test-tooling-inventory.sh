#!/usr/bin/env bash
# Focused behavioral suite for tooling-conventions/scripts/inventory-check.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKER="$REPO_ROOT/skills/tooling-conventions/scripts/inventory-check.sh"
[[ -f "$CHECKER" ]] || { echo "missing structural inventory checker: $CHECKER" >&2; exit 1; }

fixture_parent="${TMPDIR:-/tmp}"
fixture_prefix="${fixture_parent%/}/tooling-inventory-test."
fixture="$(mktemp -d "${fixture_prefix}XXXXXX")"
fixture_suffix="${fixture#"$fixture_prefix"}"
[[ "$fixture" == "$fixture_prefix"* && -n "$fixture_suffix" && -d "$fixture" ]] \
    || { echo "unsafe fixture directory: $fixture" >&2; exit 1; }
REAL_PYTHON="$(command -v python || command -v python3 || true)"
[[ -n "$REAL_PYTHON" ]] || { echo "test requires a Python interpreter" >&2; exit 1; }
cleanup() {
    local suffix="${fixture#"$fixture_prefix"}"
    if [[ "$fixture" == "$fixture_prefix"* && -n "$suffix" && -d "$fixture" ]]; then
        rm -rf -- "$fixture"
    fi
}
trap cleanup EXIT

negative_fails=0

run_with_python_candidate() { # <python|python3|py|none> <inventory>
    local selected="$1" inventory="$2"
    (
        # shellcheck disable=SC2317,SC2329 # exported to model launcher availability in child Bash
        python() {
            [[ "$PYTHON_FIXTURE_CANDIDATE" == "python" ]] || return 127
            "$REAL_PYTHON" "$@"
        }
        # shellcheck disable=SC2317,SC2329 # exported to model launcher availability in child Bash
        python3() {
            [[ "$PYTHON_FIXTURE_CANDIDATE" == "python3" ]] || return 127
            "$REAL_PYTHON" "$@"
        }
        # shellcheck disable=SC2317,SC2329 # exported to model launcher availability in child Bash
        py() {
            [[ "$PYTHON_FIXTURE_CANDIDATE" == "py" && "${1:-}" == "-3" ]] || return 127
            shift
            "$REAL_PYTHON" "$@"
        }
        export -f python python3 py
        PYTHON_FIXTURE_CANDIDATE="$selected" REAL_PYTHON="$REAL_PYTHON" \
            bash "$CHECKER" "$inventory" 2>&1
    )
}

# No-argument behavior is only a convenience default; target projects can use any root.
mkdir -p "$fixture/default/tools/package-dir"
# shellcheck disable=SC2016 # literal fixture script must retain its runtime parameter expansion
printf '%s\n' '#!/usr/bin/env bash' 'case "${1:-}" in -h|--help) exit 0;; *) exit 0;; esac' \
    > "$fixture/default/tools/tool.sh"
printf '%s\n' '#!/usr/bin/env python3' 'print("ok")' \
    > "$fixture/default/tools/valid path-雪.py"
chmod +x "$fixture/default/tools/valid path-雪.py"
{
    printf 'path\tproject_role\taudit_level\n'
    printf 'tool.sh\tproject-owned-entry\tenforce\n'
    printf 'valid path-雪.py\tcustom-python-role\tenforce\n'
    printf 'package-dir/\tproject-package\tenforce\n'
} > "$fixture/default/tools/tools-inventory.tsv"
(
    cd "$fixture/default"
    bash "$CHECKER"
)
if find "$fixture/default" -type d -name __pycache__ -print -quit | grep -q . \
    || find "$fixture/default" -type f -name '*.pyc' -print -quit | grep -q .; then
    echo "inventory check left Python bytecode residue" >&2
    exit 1
fi

# Explicit inventory paths support roots named scripts, bin, or anything project-owned.
mkdir -p "$fixture/explicit/scripts"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/explicit/scripts/run.sh"
{
    printf 'owner\tpath\tcustom_policy\r\n'
    printf 'developer\trun.sh\tanything-the-project-defines\r\n'
} > "$fixture/explicit/scripts/inventory.tsv"
bash "$CHECKER" "$fixture/explicit/scripts/inventory.tsv"
bash "$CHECKER" -- "$fixture/explicit/scripts/inventory.tsv"

# A separated inventory uses TOOLS_DIR as the authoritative scan-root override.
mkdir -p "$fixture/override/config" "$fixture/override/bin"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/override/bin/run.sh"
printf 'path\nrun.sh\n' > "$fixture/override/config/inventory.tsv"
override_scan="$(cd "$fixture/override/bin" && pwd -P)"
if ! override_output="$(
    TOOLS_DIR="$fixture/override/bin" bash "$CHECKER" "$fixture/override/config/inventory.tsv"
)"; then
    echo "TOOLS_DIR did not override the inventory directory" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF "scan: $override_scan" <<<"$override_output"; then
    echo "TOOLS_DIR override was not reported as the scan root" >&2
    negative_fails=$((negative_fails + 1))
fi

# A directory row records the directory itself; it never hides nested command drift.
mkdir -p "$fixture/directory-cover/tools/package"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/directory-cover/tools/package/nested.sh"
printf 'path\npackage/\n' > "$fixture/directory-cover/tools/inventory.tsv"
set +e
directory_output="$(bash "$CHECKER" "$fixture/directory-cover/tools/inventory.tsv" 2>&1)"
directory_rc=$?
set -e
if [[ "$directory_rc" != 1 ]]; then
    echo "directory inventory row does not cover nested commands with exit 1 (got $directory_rc)" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: unregistered command (no inventory row): package/nested.sh' \
    <<<"$directory_output"; then
    echo "directory inventory row hid a nested command without the expected diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi

# Leading dashes and project-owned skip rules remain safe and explicit.
mkdir -p "$fixture/dash/tools/generated"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/dash/tools/-dash.sh"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/dash/tools/generated/ignored.sh"
printf 'path\n-dash.sh\n' > "$fixture/dash/tools/inventory.tsv"
INVENTORY_CHECK_SKIP='(^|/)generated/' bash "$CHECKER" "$fixture/dash/tools/inventory.tsv"

# The unset skip policy is neutral: semantic-looking project directories remain audited.
mkdir -p "$fixture/neutral-skip/tools/legacy"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/neutral-skip/tools/listed.sh"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/neutral-skip/tools/legacy/unlisted.sh"
printf 'path\nlisted.sh\n' > "$fixture/neutral-skip/tools/inventory.tsv"
set +e
neutral_skip_output="$(
    env -u INVENTORY_CHECK_SKIP bash "$CHECKER" "$fixture/neutral-skip/tools/inventory.tsv" 2>&1
)"
neutral_skip_rc=$?
set -e
if [[ "$neutral_skip_rc" != 1 ]]; then
    echo "default skip policy hid a project-owned command (got $neutral_skip_rc)" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: unregistered command (no inventory row): legacy/unlisted.sh' \
    <<<"$neutral_skip_output"; then
    echo "neutral default did not report a semantic-looking project path" >&2
    negative_fails=$((negative_fails + 1))
fi

# Invalid rows and malformed contracts remain blocking structural findings.
mkdir -p "$fixture/invalid/tools/package-dir"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/invalid/tools/tool.sh"
{
    printf 'path\taudit_level\n'
    printf '\tenforce\n'
    # Exact parent segments remain blocking even when the row asks to warn.
    printf '..\twarn\n'
    printf '../outside.sh\tenforce\n'
    printf './tool.sh\tenforce\n'
    printf 'tool.sh\tenforce\n'
    printf 'tool.sh\tenforce\n'
    printf 'package-dir\tenforce\n'
} > "$fixture/invalid/tools/invalid.tsv"
set +e
invalid_output="$(bash "$CHECKER" "$fixture/invalid/tools/invalid.tsv" 2>&1)"
invalid_rc=$?
set -e
if [[ "$invalid_rc" != 1 ]]; then
    echo "expected invalid inventory rows to exit 1 (got $invalid_rc)" >&2
    negative_fails=$((negative_fails + 1))
else
    for diagnostic in \
        'inventory row 2 has an empty path' \
        'FAIL: invalid inventory path (must be normalized and relative): ..' \
        'invalid inventory path (must be normalized and relative): ../outside.sh' \
        'invalid inventory path (must be normalized and relative): ./tool.sh' \
        'duplicate inventory path: tool.sh' \
        'directory inventory path must end in /: package-dir'; do
        if ! grep -qF "$diagnostic" <<<"$invalid_output"; then
            echo "missing invalid inventory diagnostic: $diagnostic" >&2
            negative_fails=$((negative_fails + 1))
        fi
    done
fi

# Syntax findings block at enforce level for both supported command forms.
mkdir -p "$fixture/enforce/tools"
printf '%s\n' '#!/usr/bin/env bash' 'if then' > "$fixture/enforce/tools/bad.sh"
printf '%s\n' '#!/usr/bin/env python3' 'def broken(:' > "$fixture/enforce/tools/bad.py"
chmod +x "$fixture/enforce/tools/bad.py"
{
    printf 'path\taudit_level\n'
    printf 'bad.sh\tenforce\n'
    printf 'bad.py\tenforce\n'
} > "$fixture/enforce/tools/inventory.tsv"
set +e
enforce_output="$(bash "$CHECKER" "$fixture/enforce/tools/inventory.tsv" 2>&1)"
enforce_rc=$?
set -e
if [[ "$enforce_rc" != 1 ]]; then
    echo "expected enforce-level syntax findings to exit 1 (got $enforce_rc)" >&2
    negative_fails=$((negative_fails + 1))
else
    for diagnostic in 'FAIL: shell syntax error: bad.sh' 'FAIL: python compile error: bad.py'; do
        if ! grep -qF "$diagnostic" <<<"$enforce_output"; then
            echo "missing enforce-level syntax diagnostic: $diagnostic" >&2
            negative_fails=$((negative_fails + 1))
        fi
    done
fi

printf 'path\taudit_level\ntool.sh\tmaybe\n' > "$fixture/invalid/tools/invalid-audit.tsv"
if invalid_audit_output="$(bash "$CHECKER" "$fixture/invalid/tools/invalid-audit.tsv" 2>&1)"; then
    echo "expected an invalid audit level to fail" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'invalid audit_level for tool.sh: maybe' <<<"$invalid_audit_output"; then
    echo "missing invalid audit-level diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi

printf 'owner\tcustom_policy\ndeveloper\tanything\n' > "$fixture/invalid/tools/missing-path.tsv"
set +e
bash "$CHECKER" "$fixture/invalid/tools/missing-path.tsv" >/dev/null 2>&1
missing_path_header_rc=$?
set -e
if [[ "$missing_path_header_rc" != 2 ]]; then
    echo "expected a missing path header to exit 2 (got $missing_path_header_rc)" >&2
    negative_fails=$((negative_fails + 1))
fi

# Python syntax checks support python3-only and Windows py -3 launcher environments.
mkdir -p "$fixture/python-preflight/tools"
printf '%s\n' '#!/usr/bin/env python3' 'print("ok")' \
    > "$fixture/python-preflight/tools/run.py"
printf 'path\taudit_level\nrun.py\twarn\n' > "$fixture/python-preflight/tools/inventory.tsv"

set +e
python3_fallback_output="$(
    run_with_python_candidate python3 "$fixture/python-preflight/tools/inventory.tsv"
)"
python3_fallback_rc=$?
set -e
if [[ "$python3_fallback_rc" != 0 ]]; then
    echo "python3 fallback did not complete the inventory check (got $python3_fallback_rc)" >&2
    echo "$python3_fallback_output" >&2
    negative_fails=$((negative_fails + 1))
fi

set +e
py_fallback_output="$(
    run_with_python_candidate py "$fixture/python-preflight/tools/inventory.tsv"
)"
py_fallback_rc=$?
set -e
if [[ "$py_fallback_rc" != 0 ]]; then
    echo "py -3 fallback did not complete the inventory check (got $py_fallback_rc)" >&2
    echo "$py_fallback_output" >&2
    negative_fails=$((negative_fails + 1))
fi

# Interpreter availability is a checker preflight and cannot be downgraded by row warning policy.
set +e
python_preflight_output="$(
    run_with_python_candidate none "$fixture/python-preflight/tools/inventory.tsv"
)"
python_preflight_rc=$?
set -e
if [[ "$python_preflight_rc" != 2 ]]; then
    echo "expected missing Python preflight to exit 2 (got $python_preflight_rc)" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'python 3.8+ interpreter unavailable for syntax check: run.py' \
    <<<"$python_preflight_output"; then
    echo "missing Python preflight diagnostic was not reported" >&2
    negative_fails=$((negative_fails + 1))
fi

# Row-level known debt may warn, but reverse inventory and contract failures still block.
mkdir -p "$fixture/warn/tools"
printf '%s\n' '#!/usr/bin/env bash' 'if then' > "$fixture/warn/tools/bad.sh"
printf '%s\n' '#!/usr/bin/env python3' 'def broken(:' > "$fixture/warn/tools/bad.py"
chmod +x "$fixture/warn/tools/bad.py"
{
    printf 'path\taudit_level\towner\n'
    printf 'missing.sh\twarn\tlegacy-owner\n'
    printf 'missing-dir/\twarn\tlegacy-owner\n'
    printf 'bad.sh\twarn\tlegacy-owner\n'
    printf 'bad.py\twarn\tlegacy-owner\n'
} > "$fixture/warn/tools/inventory.tsv"
if ! warn_output="$(bash "$CHECKER" "$fixture/warn/tools/inventory.tsv" 2>&1)"; then
    echo "expected warn-level row findings to remain non-blocking" >&2
    negative_fails=$((negative_fails + 1))
else
    for diagnostic in \
        'warn: inventory row -> missing path: missing.sh' \
        'warn: inventory row -> missing path: missing-dir/' \
        'warn: shell syntax error: bad.sh' \
        'warn: python compile error: bad.py'; do
        if ! grep -qF "$diagnostic" <<<"$warn_output"; then
            echo "missing warn-level diagnostic: $diagnostic" >&2
            negative_fails=$((negative_fails + 1))
        fi
    done
    if ! grep -qF 'RESULT: OK (4 warn)' <<<"$warn_output"; then
        echo "warn-level structural findings did not remain non-blocking" >&2
        negative_fails=$((negative_fails + 1))
    fi
fi
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/warn/tools/rogue.sh"
set +e
rogue_output="$(bash "$CHECKER" "$fixture/warn/tools/inventory.tsv" 2>&1)"
rogue_rc=$?
set -e
if [[ "$rogue_rc" != 1 ]]; then
    echo "expected reverse inventory drift to exit 1 (got $rogue_rc)" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: unregistered command (no inventory row): rogue.sh' <<<"$rogue_output"; then
    echo "warn-level row state leaked into reverse inventory drift" >&2
    negative_fails=$((negative_fails + 1))
fi

# CLI and preflight failures use exit 2; structural findings above use exit 1.
bash "$CHECKER" --help >/dev/null
for args in '--unknown' '-- extra.tsv unexpected'; do
    set +e
    # shellcheck disable=SC2086 # intentional word splitting exercises argument count
    bash "$CHECKER" $args >/dev/null 2>&1
    rc=$?
    set -e
    if [[ "$rc" != 2 ]]; then
        echo "expected invalid CLI arguments to exit 2: $args (got $rc)" >&2
        negative_fails=$((negative_fails + 1))
    fi
done
set +e
bash "$CHECKER" "$fixture/missing-inventory.tsv" >/dev/null 2>&1
missing_inventory_rc=$?
set -e
if [[ "$missing_inventory_rc" != 2 ]]; then
    echo "expected a missing inventory to exit 2 (got $missing_inventory_rc)" >&2
    negative_fails=$((negative_fails + 1))
fi
set +e
TOOLS_DIR="$fixture/missing-root" bash "$CHECKER" "$fixture/default/tools/tools-inventory.tsv" \
    >/dev/null 2>&1
missing_root_rc=$?
set -e
if [[ "$missing_root_rc" != 2 ]]; then
    echo "expected a missing scan root to exit 2 (got $missing_root_rc)" >&2
    negative_fails=$((negative_fails + 1))
fi

# Reverse-scan and temporary-directory preflight failures must propagate safely.
mkdir -p "$fixture/find-bin"
printf '%s\n' '#!/usr/bin/env bash' 'echo "injected find failure" >&2' 'exit 37' \
    > "$fixture/find-bin/find"
chmod +x "$fixture/find-bin/find"
set +e
PATH="$fixture/find-bin:$PATH" bash "$CHECKER" "$fixture/default/tools/tools-inventory.tsv" \
    >/dev/null 2>&1
find_rc=$?
set -e
if [[ "$find_rc" != 2 ]]; then
    echo "expected reverse-scan failure to exit 2 (got $find_rc)" >&2
    negative_fails=$((negative_fails + 1))
fi

mkdir -p "$fixture/mktemp-bin"
cat > "$fixture/mktemp-bin/mktemp" <<'EOF'
#!/usr/bin/env bash
case "${FAKE_MKTEMP_MODE:-fail}" in
    fail) exit 37 ;;
    unsafe) printf '%s\n' "$FAKE_MKTEMP_UNSAFE" ;;
    *) exit 38 ;;
esac
EOF
chmod +x "$fixture/mktemp-bin/mktemp"
set +e
mktemp_output="$(
    PATH="$fixture/mktemp-bin:$PATH" FAKE_MKTEMP_MODE=fail \
        bash "$CHECKER" "$fixture/default/tools/tools-inventory.tsv" 2>&1
)"
mktemp_rc=$?
set -e
if [[ "$mktemp_rc" != 2 ]]; then
    echo "expected temporary-directory creation failure to exit 2 (got $mktemp_rc)" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'failed to create temporary directory' <<<"$mktemp_output"; then
    echo "missing temporary-directory failure diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi
set +e
unsafe_mktemp_output="$(
    PATH="$fixture/mktemp-bin:$PATH" FAKE_MKTEMP_MODE=unsafe FAKE_MKTEMP_UNSAFE="$fixture" \
        bash "$CHECKER" "$fixture/default/tools/tools-inventory.tsv" 2>&1
)"
unsafe_mktemp_rc=$?
set -e
if [[ "$unsafe_mktemp_rc" != 2 ]]; then
    echo "expected an unsafe temporary-directory result to exit 2 (got $unsafe_mktemp_rc)" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'mktemp returned an unsafe temporary directory' <<<"$unsafe_mktemp_output"; then
    echo "missing unsafe temporary-directory diagnostic" >&2
    negative_fails=$((negative_fails + 1))
elif [[ ! -d "$fixture/default/tools" ]]; then
    echo "unsafe temporary-directory result removed the test fixture" >&2
    negative_fails=$((negative_fails + 1))
fi

if find "$fixture" -type d -name __pycache__ -print -quit | grep -q . \
    || find "$fixture" -type f -name '*.pyc' -print -quit | grep -q .; then
    echo "inventory check left Python bytecode residue" >&2
    exit 1
fi

test "$negative_fails" = 0
echo "OK: tooling inventory suite passed"
