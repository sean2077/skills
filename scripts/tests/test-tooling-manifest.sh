#!/usr/bin/env bash
# Focused behavioral suite for tooling-conventions/scripts/manifest-check.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
CHECKER="$REPO_ROOT/skills/tooling-conventions/scripts/manifest-check.sh"

fixture_parent="$(cd "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P)" \
    || { echo "temporary-directory parent is unavailable: ${TMPDIR:-/tmp}" >&2; exit 1; }
fixture_prefix="${fixture_parent%/}/tooling-manifest-test."
fixture="$(mktemp -d "${fixture_prefix}XXXXXX")" \
    || { echo "failed to create temporary directory under $fixture_parent" >&2; exit 1; }
fixture_suffix="${fixture#"$fixture_prefix"}"
[[ "$fixture" == "$fixture_prefix"* && -n "$fixture_suffix" && -d "$fixture" ]] \
    || { echo "mktemp returned an unsafe temporary directory: ${fixture:-<empty>}" >&2; exit 1; }
# shellcheck disable=SC2329  # invoked by the EXIT trap
cleanup() {
    local suffix="${fixture#"$fixture_prefix"}"
    if [[ "$fixture" == "$fixture_prefix"* && -n "$suffix" && -d "$fixture" ]]; then
        rm -rf -- "$fixture"
    fi
}
trap cleanup EXIT
mkdir -p "$fixture/tools/package-dir" "$fixture/tools/vendor"
{
    printf 'path\tsurface\n'
    printf 'tool.sh\tpublic\n'
    printf 'package-dir/\tpackage\n'
    printf 'vendor/tool\tvendor\n'
    printf 'valid path-雪.py\thelper\n'
} > "$fixture/tools/tools-manifest.tsv"
# Literal fixture must retain ${1:-} for the generated script.
# shellcheck disable=SC2016
printf '%s\n' '#!/usr/bin/env bash' 'case "${1:-}" in -h|--help) exit 0;; esac' > "$fixture/tools/tool.sh"
printf 'vendor fixture\n' > "$fixture/tools/vendor/tool"
printf '# -*- coding: latin-1 -*-\nmessage = "caf\351"\n' > "$fixture/tools/valid path-雪.py"
bash "$CHECKER" "$fixture/tools/tools-manifest.tsv"

mkdir -p "$fixture/dash-path"
printf 'path\tsurface\n%b\n' '-dash.sh\thelper' > "$fixture/dash-path/manifest.tsv"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/dash-path/-dash.sh"
bash "$CHECKER" "$fixture/dash-path/manifest.tsv"

mkdir -p "$fixture/semantic"
printf '%s\n' '#!/usr/bin/env bash' '# --help appears only in this comment' 'exit 0' > "$fixture/semantic/comment-only.sh"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/semantic/helper.sh"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/semantic/installed.sh"
{
    printf 'path\tsurface\tentry_for\tverify\taudit_level\n'
    printf 'comment-only.sh\tpublic\trun the comment fixture\tbash -n only\tenforce\n'
    printf 'helper.sh\thelper\tindependent operator job\t-\tenforce\n'
    printf 'installed.sh\tinstalled\t\tcli-contract test\tenforce\n'
} > "$fixture/semantic/manifest.tsv"
if semantic_output="$(bash "$CHECKER" "$fixture/semantic/manifest.tsv" 2>&1)"; then
    echo "expected semantic manifest contradictions to fail" >&2
    exit 1
fi
for diagnostic in \
    'public entry verify must declare --help=0 and unknown-arg=2 evidence (or a cli-contract test): comment-only.sh' \
    'helper entry_for must be blank (not an independent entry): helper.sh' \
    'installed entry must declare entry_for: installed.sh'; do
    if ! grep -qF "$diagnostic" <<<"$semantic_output"; then
        echo "missing semantic manifest diagnostic: $diagnostic" >&2
        exit 1
    fi
done
if find "$fixture/tools" -type f -name '*.pyc' -print -quit | grep -q .; then
    echo "manifest check left Python bytecode residue" >&2
    exit 1
fi

negative_fails=0
cp "$fixture/tools/tools-manifest.tsv" "$fixture/base-manifest.tsv"

for args in \
    "--not-a-real-option" \
    "--help --not-a-real-option" \
    "$fixture/tools/tools-manifest.tsv unexpected"; do
    # shellcheck disable=SC2086  # deliberate argument-vector fixtures
    if bash "$CHECKER" $args >/dev/null 2>&1; then
        echo "expected invalid CLI arguments to fail: $args" >&2
        negative_fails=$((negative_fails + 1))
    elif [[ "$?" != 2 ]]; then
        echo "expected invalid CLI arguments to exit 2: $args" >&2
        negative_fails=$((negative_fails + 1))
    fi
done

{
    printf 'path\tsurface\taudit_level\n'
    printf '\tpublic\tenforce\n'
    printf '../outside.sh\tpublic\tenforce\n'
    printf './tool.sh\tpublic\tenforce\n'
    printf 'tool.sh\tpublic\tmaybe\n'
    printf 'package-dir\tpackage\tenforce\n'
} > "$fixture/tools/invalid-contract-manifest.tsv"
if invalid_contract_output="$(bash "$CHECKER" "$fixture/tools/invalid-contract-manifest.tsv" 2>&1)"; then
    echo "expected invalid manifest row contracts to fail" >&2
    negative_fails=$((negative_fails + 1))
else
    for diagnostic in \
        'has an empty path' \
        'invalid manifest path (must be normalized and relative): ../outside.sh' \
        'invalid manifest path (must be normalized and relative): ./tool.sh' \
        'invalid audit_level for tool.sh: maybe' \
        'package directory path must end in / and name a directory: package-dir'; do
        if ! grep -qF "$diagnostic" <<<"$invalid_contract_output"; then
            echo "missing invalid-contract diagnostic: $diagnostic" >&2
            negative_fails=$((negative_fails + 1))
        fi
    done
fi

{
    printf 'path\tsurface\n'
    printf 'tool.sh\tpublic\n'
    printf 'tool.sh\thelper\n'
} > "$fixture/tools/duplicate-path-manifest.tsv"
if duplicate_output="$(bash "$CHECKER" "$fixture/tools/duplicate-path-manifest.tsv" 2>&1)"; then
    echo "expected a duplicate manifest path to fail" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: duplicate manifest path: tool.sh' <<<"$duplicate_output"; then
    echo "missing duplicate manifest path diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi

{
    printf 'path\tsurface\n'
    printf 'tool.sh\tpublci\n'
} > "$fixture/tools/invalid-surface-manifest.tsv"
if invalid_surface_output="$(bash "$CHECKER" "$fixture/tools/invalid-surface-manifest.tsv" 2>&1)"; then
    echo "expected an invalid manifest surface to fail" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: invalid manifest surface for tool.sh: publci' <<<"$invalid_surface_output"; then
    echo "missing invalid manifest surface diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi

{
    printf 'vendor/missing-tool\tvendor\n'
    printf 'missing-package/\tpackage\n'
} >> "$fixture/tools/tools-manifest.tsv"
if forward_output="$(bash "$CHECKER" "$fixture/tools/tools-manifest.tsv" 2>&1)"; then
    echo "expected every missing manifest row to fail" >&2
    negative_fails=$((negative_fails + 1))
else
    for missing in vendor/missing-tool missing-package/; do
        if ! grep -qF "manifest row → missing file: $missing" <<<"$forward_output"; then
            echo "missing forward-drift diagnostic for: $missing" >&2
            negative_fails=$((negative_fails + 1))
        fi
    done
fi

{
    printf 'audit_level\tpath\tsurface\n'
    printf 'enforce\ttool.sh\tpublic\n'
    printf 'enforce\tvendor/missing-enforce-tool\tvendor\n'
} > "$fixture/tools/enforce-manifest.tsv"
if enforce_output="$(bash "$CHECKER" "$fixture/tools/enforce-manifest.tsv" 2>&1)"; then
    echo "expected explicit audit_level=enforce to remain blocking" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: manifest row → missing file: vendor/missing-enforce-tool' <<<"$enforce_output"; then
    echo "missing explicit enforce-level diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi

{
    printf 'path\tsurface\taudit_level\tnotes\n'
    printf 'tool.sh\tpublic\tenforce\tfixture\n'
    printf 'vendor/missing-blank-audit-tool\tvendor\t\twarn\n'
} > "$fixture/tools/blank-audit-manifest.tsv"
if blank_audit_output="$(bash "$CHECKER" "$fixture/tools/blank-audit-manifest.tsv" 2>&1)"; then
    echo "expected a blank audit_level to default to enforce" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: manifest row → missing file: vendor/missing-blank-audit-tool' <<<"$blank_audit_output"; then
    echo "later TSV fields shifted into a blank audit_level" >&2
    negative_fails=$((negative_fails + 1))
fi

{
    printf 'path\taudit_level\tsurface\r\n'
    printf 'tool.sh\tenforce\tpublic\r\n'
    printf 'vendor/missing-crlf-tool\twarn\tvendor\r\n'
} > "$fixture/tools/crlf-manifest.tsv"
if ! crlf_output="$(bash "$CHECKER" "$fixture/tools/crlf-manifest.tsv" 2>&1)"; then
    echo "expected CRLF manifest rows to preserve named columns and warn levels" >&2
    printf '%s\n' "$crlf_output" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'warn: manifest row → missing file: vendor/missing-crlf-tool' <<<"$crlf_output"; then
    echo "missing CRLF warn-level diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi

{
    printf 'path\tsurface\taudit_level\r\n'
    printf 'tool.sh\tpublic\tenforce\r\n'
    printf 'vendor/missing-crlf-audit-tool\tvendor\twarn\r\n'
} > "$fixture/tools/crlf-audit-manifest.tsv"
if ! crlf_audit_output="$(bash "$CHECKER" "$fixture/tools/crlf-audit-manifest.tsv" 2>&1)"; then
    echo "expected a CRLF audit_level value to remain advisory" >&2
    printf '%s\n' "$crlf_audit_output" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'warn: manifest row → missing file: vendor/missing-crlf-audit-tool' <<<"$crlf_audit_output"; then
    echo "CRLF changed the warn audit level" >&2
    negative_fails=$((negative_fails + 1))
fi

printf '%s\n' '#!/usr/bin/env bash' 'if then' > "$fixture/tools/bad.sh"
printf '%s\n' 'return 1' > "$fixture/tools/bad.py"
{
    printf 'path\tsurface\tdomain\tentry_for\taudit_level\n'
    printf 'tool.sh\tpublic\tfixture\texercise the fixture\tenforce\n'
    printf 'vendor/missing-warn-tool\tvendor\tfixture\t\twarn\n'
    printf 'missing-warn-package/\tpackage\tfixture\t\twarn\n'
    printf 'bad.sh\thelper\tfixture\t\twarn\n'
    printf 'bad.py\thelper\tfixture\t\twarn\n'
} > "$fixture/tools/warn-manifest.tsv"
if ! warn_output="$(bash "$CHECKER" "$fixture/tools/warn-manifest.tsv" 2>&1)"; then
    echo "expected audit_level=warn rows to remain advisory" >&2
    printf '%s\n' "$warn_output" >&2
    negative_fails=$((negative_fails + 1))
else
    for missing in vendor/missing-warn-tool missing-warn-package/; do
        if ! grep -qF "warn: manifest row → missing file: $missing" <<<"$warn_output"; then
            echo "missing warn-level forward-drift diagnostic for: $missing" >&2
            negative_fails=$((negative_fails + 1))
        fi
    done
    for syntax in 'shell syntax error: bad.sh' 'python compile error: bad.py'; do
        if ! grep -qF "warn: $syntax" <<<"$warn_output"; then
            echo "missing warn-level syntax diagnostic for: $syntax" >&2
            negative_fails=$((negative_fails + 1))
        fi
    done
    if ! grep -qF 'RESULT: OK (4 warn)' <<<"$warn_output"; then
        echo "warn-level forward drift did not remain non-blocking" >&2
        negative_fails=$((negative_fails + 1))
    fi
fi

printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fixture/tools/rogue.sh"
if rogue_output="$(bash "$CHECKER" "$fixture/tools/warn-manifest.tsv" 2>&1)"; then
    echo "expected reverse drift to remain blocking after warn-level rows" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'FAIL: unregistered command surface (no manifest row): rogue.sh' <<<"$rogue_output"; then
    echo "warn-level row state leaked into reverse drift" >&2
    negative_fails=$((negative_fails + 1))
fi

mv "$fixture/base-manifest.tsv" "$fixture/tools/tools-manifest.tsv"
if TOOLS_DIR="$fixture/missing" bash "$CHECKER" "$fixture/tools/tools-manifest.tsv"; then
    echo "expected a missing scan root to fail" >&2
    negative_fails=$((negative_fails + 1))
fi

mkdir -p "$fixture/bin"
printf '%s\n' '#!/usr/bin/env bash' 'echo "injected find failure" >&2' 'exit 37' > "$fixture/bin/find"
chmod +x "$fixture/bin/find"
if PATH="$fixture/bin:$PATH" bash "$CHECKER" "$fixture/tools/tools-manifest.tsv"; then
    echo "expected a reverse-scan failure to propagate" >&2
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
if mktemp_output="$(PATH="$fixture/mktemp-bin:$PATH" FAKE_MKTEMP_MODE=fail bash "$CHECKER" "$fixture/tools/tools-manifest.tsv" 2>&1)"; then
    echo "expected temporary-directory creation failure to stop the checker" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'failed to create temporary directory' <<<"$mktemp_output"; then
    echo "missing temporary-directory failure diagnostic" >&2
    negative_fails=$((negative_fails + 1))
fi
if unsafe_mktemp_output="$(PATH="$fixture/mktemp-bin:$PATH" FAKE_MKTEMP_MODE=unsafe FAKE_MKTEMP_UNSAFE="$fixture" bash "$CHECKER" "$fixture/tools/tools-manifest.tsv" 2>&1)"; then
    echo "expected an unsafe temporary-directory result to stop the checker" >&2
    negative_fails=$((negative_fails + 1))
elif ! grep -qF 'mktemp returned an unsafe temporary directory' <<<"$unsafe_mktemp_output"; then
    echo "missing unsafe temporary-directory diagnostic" >&2
    negative_fails=$((negative_fails + 1))
elif [[ ! -d "$fixture/tools" ]]; then
    echo "unsafe temporary-directory result removed the test fixture" >&2
    negative_fails=$((negative_fails + 1))
fi

test "$negative_fails" = 0
echo "OK: tooling manifest suite passed"
