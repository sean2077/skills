#!/usr/bin/env bash
# manifest-check.sh — reconcile a tools/ surface manifest against the scripts on disk.
#
# Generic companion to the tooling-conventions skill. No deps beyond bash/awk/grep/find.
# The manifest is a TSV with (at least) a `path` and a `surface` column, identified by
# header name — so it works with any superset schema (see manifest.schema.md).
#
# Checks (FAIL → exit 1; warn → advisory, exit stays 0):
#   FAIL  a manifest row points at a missing file
#   FAIL  a command file on disk (.sh, or executable .py) has no manifest row
#   FAIL  shell syntax error (bash -n) / python compile error (py_compile)
#   warn  a public/installed entry has no detectable -h/--help handler
#
# Usage:
#   bash manifest-check.sh [path/to/manifest.tsv]      # default: tools/tools-manifest.tsv
# Env:
#   TOOLS_DIR            scan root for the reverse drift check (default: dir of the manifest)
#   MANIFEST_CHECK_SKIP  extended regex of tools-relative paths to ignore in the reverse scan
#                        (default: internal/ vendor/ tests/ legacy/ + dotfiles + _underscore dirs)
set -euo pipefail

case "${1:-}" in -h | --help) sed -n '2,19p' "$0" | sed 's/^# \?//'; exit 0 ;; esac

MANIFEST="${1:-tools/tools-manifest.tsv}"
[[ -f "$MANIFEST" ]] || { echo "manifest not found: $MANIFEST" >&2; exit 2; }
SCAN_DIR="${TOOLS_DIR:-$(dirname "$MANIFEST")}"
SKIP_RE="${MANIFEST_CHECK_SKIP:-(^|/)(internal|vendor|tests?|legacy)/|(^|/)[._]}"

fails=0 warns=0
fail() { printf 'FAIL: %s\n' "$*"; fails=$((fails + 1)); }
warn() { printf 'warn: %s\n' "$*"; warns=$((warns + 1)); }

# Locate columns by header name so any superset schema works. col_any takes
# aliases and returns the first that matches (e.g. `surface_current` for a manifest
# that tracks current-vs-target placement during a migration).
col_any() {
    local want idx
    for want in "$@"; do
        idx="$(awk -F'\t' -v w="$want" 'NR==1{for(i=1;i<=NF;i++) if($i==w){print i; exit}}' "$MANIFEST")"
        [[ -n "$idx" ]] && { echo "$idx"; return; }
    done
}
ip="$(col_any path)"; is="$(col_any surface surface_current)"
[[ -n "$ip" && -n "$is" ]] || { echo "manifest must have a 'path' and a 'surface' (or 'surface_current') column" >&2; exit 2; }

declare -A SEEN

# Forward drift + per-file contract/syntax. Build the SEEN set of registered paths.
while IFS=$'\t' read -r -a F || ((${#F[@]})); do
    p="${F[$((ip - 1))]:-}"; s="${F[$((is - 1))]:-}"
    [[ -z "$p" || "$p" == "path" ]] && continue
    SEEN["$p"]=1
    [[ "$p" == */ ]] && continue                       # package/native directory row
    case "$p" in *.sh | *.py) : ;; *) continue ;; esac # only command files are existence-checked
    f="$SCAN_DIR/$p"
    if [[ ! -e "$f" ]]; then fail "manifest row → missing file: $p"; continue; fi
    case "$p" in
        *.sh) bash -n "$f" 2>/dev/null || fail "shell syntax error: $p" ;;
        *.py) command -v python3 >/dev/null 2>&1 &&
            { python3 -m py_compile "$f" 2>/dev/null || fail "python compile error: $p"; } ;;
    esac
    case "$s" in
        public | installed)
            grep -qE -- '(^|[^a-zA-Z])-h([^a-zA-Z]|$)|--help' "$f" ||
                warn "$s entry has no detectable -h/--help handler: $p" ;;
    esac
done < "$MANIFEST"

# Reverse drift: command files on disk with no manifest row.
while IFS= read -r f; do
    rel="${f#"$SCAN_DIR"/}"
    [[ "$rel" =~ $SKIP_RE ]] && continue
    [[ "$f" == *.py && ! -x "$f" ]] && continue # only executable .py count as command CLIs
    [[ -n "${SEEN[$rel]:-}" ]] || fail "unregistered command surface (no manifest row): $rel"
done < <(find "$SCAN_DIR" -type f \( -name '*.sh' -o -name '*.py' \) | sort)

echo "---"
echo "manifest: $MANIFEST   scan: $SCAN_DIR   registered rows: ${#SEEN[@]}"
if ((fails)); then
    echo "RESULT: $fails fail / $warns warn"
    exit 1
fi
echo "RESULT: OK ($warns warn)"
