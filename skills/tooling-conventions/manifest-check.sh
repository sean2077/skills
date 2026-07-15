#!/usr/bin/env bash
# manifest-check.sh — reconcile a tools/ surface manifest against the scripts on disk.
#
# Generic companion to the tooling-conventions skill. No deps beyond bash/awk/grep/find.
# The manifest is a TSV with (at least) a `path` and a `surface` column, identified by
# header name — so it works with any superset schema (see manifest.schema.md).
#
# Checks (row FAIL findings honor `audit_level=warn`; global failures stay blocking):
#   FAIL  a manifest row points at a missing file
#   FAIL  a command file on disk (.sh, or executable .py) has no manifest row
#   FAIL  shell syntax error (bash -n) / python compile error (in-memory compile)
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
[[ -d "$SCAN_DIR" ]] || { echo "scan directory not found: $SCAN_DIR" >&2; exit 2; }
SKIP_RE="${MANIFEST_CHECK_SKIP:-(^|/)(internal|vendor|tests?|legacy)/|(^|/)[._]}"

fails=0 warns=0
fail() { printf 'FAIL: %s\n' "$*"; fails=$((fails + 1)); }
warn() { printf 'warn: %s\n' "$*"; warns=$((warns + 1)); }
row_issue() { # <audit-level> <message...>
    local audit_level="$1"
    shift
    if [[ "$audit_level" == "warn" ]]; then warn "$@"; else fail "$@"; fi
}

# Locate columns by header name so any superset schema works. col_any takes
# aliases and returns the first that matches (e.g. `surface_current` for a manifest
# that tracks current-vs-target placement during a migration).
col_any() {
    local want idx
    for want in "$@"; do
        idx="$(awk -F'\t' -v w="$want" 'NR==1{sub(/\r$/, "", $NF); for(i=1;i<=NF;i++) if($i==w){print i; exit}}' "$MANIFEST")"
        [[ -n "$idx" ]] && { echo "$idx"; return; }
    done
}
ip="$(col_any path)"; is="$(col_any surface surface_current)"
ia="$(col_any audit_level || true)"
[[ -n "$ip" && -n "$is" ]] || { echo "manifest must have a 'path' and a 'surface' (or 'surface_current') column" >&2; exit 2; }

# Bash treats tab as IFS whitespace, so `read -a` collapses empty TSV fields.
# Extract by index without splitting to preserve optional blank columns.
tsv_field() { # <line> <1-based-index>; result in REPLY
    local value="$1" index="$2"
    while ((index > 1)); do
        if [[ "$value" == *$'\t'* ]]; then value="${value#*$'\t'}"; else value=""; break; fi
        index=$((index - 1))
    done
    REPLY="${value%%$'\t'*}"
}

SEEN_FILE="$(mktemp)"
INVENTORY_FILE="$(mktemp)"
trap 'rm -f "$SEEN_FILE" "$INVENTORY_FILE"' EXIT
seen_count=0

# Forward drift + per-file contract/syntax. Build the SEEN set of registered paths.
while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    tsv_field "$line" "$ip"; p="$REPLY"
    tsv_field "$line" "$is"; s="$REPLY"
    a="enforce"
    if [[ -n "$ia" ]]; then tsv_field "$line" "$ia"; a="${REPLY:-enforce}"; fi
    [[ -z "$p" || "$p" == "path" ]] && continue
    if ! grep -qxF "$p" "$SEEN_FILE" 2>/dev/null; then
        printf '%s\n' "$p" >> "$SEEN_FILE"
        seen_count=$((seen_count + 1))
    fi
    f="$SCAN_DIR/$p"
    if [[ ! -e "$f" ]]; then row_issue "$a" "manifest row → missing file: $p"; continue; fi
    [[ "$p" == */ ]] && continue                       # package/native directory row
    case "$p" in *.sh | *.py) : ;; *) continue ;; esac # syntax/help apply only to command files
    case "$p" in
        *.sh) bash -n "$f" 2>/dev/null || row_issue "$a" "shell syntax error: $p" ;;
        *.py) command -v python >/dev/null 2>&1 &&
            { python -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], "exec")' "$f" 2>/dev/null || row_issue "$a" "python compile error: $p"; } ;;
    esac
    case "$s" in
        public | installed)
            grep -qE -- '(^|[^a-zA-Z])-h([^a-zA-Z]|$)|--help' "$f" ||
                warn "$s entry has no detectable -h/--help handler: $p" ;;
    esac
done < "$MANIFEST"

# Reverse drift: command files on disk with no manifest row.
is_python_cli() { # <path>
    local file="$1" mode pathspec="${1#"$SCAN_DIR"/}"
    if command -v git >/dev/null 2>&1 && git -C "$SCAN_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        mode="$(git -C "$SCAN_DIR" ls-files -s -- "$pathspec" 2>/dev/null | awk 'NR==1{print $1}')"
        [[ -n "$mode" ]] && { [[ "$mode" == 100755 ]]; return; }
    fi
    [[ -x "$file" ]]
}

if ! find "$SCAN_DIR" -type f \( -name '*.sh' -o -name '*.py' \) | sort > "$INVENTORY_FILE"; then
    echo "reverse scan failed: $SCAN_DIR" >&2
    exit 2
fi
while IFS= read -r f; do
    rel="${f#"$SCAN_DIR"/}"
    [[ "$rel" =~ $SKIP_RE ]] && continue
    [[ "$f" == *.py ]] && ! is_python_cli "$f" && continue # index-aware on core.filemode=false
    grep -qxF "$rel" "$SEEN_FILE" 2>/dev/null || fail "unregistered command surface (no manifest row): $rel"
done < "$INVENTORY_FILE"

echo "---"
echo "manifest: $MANIFEST   scan: $SCAN_DIR   registered rows: $seen_count"
if ((fails)); then
    echo "RESULT: $fails fail / $warns warn"
    exit 1
fi
echo "RESULT: OK ($warns warn)"
