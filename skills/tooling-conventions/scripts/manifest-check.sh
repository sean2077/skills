#!/usr/bin/env bash
# manifest-check.sh — reconcile a command-surface manifest against scripts on disk.
#
# Generic companion to the tooling-conventions skill. Requires Bash plus standard GNU
# command-line tools available on the supported Git Bash/macOS/Linux hosts.
# The manifest is a TSV with (at least) a `path` and a `surface` column, identified by
# header name — so it works with any superset schema (see references/manifest-schema.md).
#
# Checks (row FAIL findings honor `audit_level=warn`; global failures stay blocking):
#   FAIL  duplicate paths, invalid labels, or contradictory `entry_for` semantics
#   FAIL  a manifest row points at a missing file
#   FAIL  a command file on disk (.sh, or executable .py) has no manifest row
#   FAIL  shell syntax error (bash -n) / python compile error (in-memory compile)
#   FAIL  when `verify` exists, public/installed rows lack declared CLI-contract evidence
#
# Usage:
#   bash manifest-check.sh [--] [path/to/manifest.tsv] # default: tools/tools-manifest.tsv
# Env:
#   TOOLS_DIR            scan root for the reverse drift check (default: dir of the manifest)
#   MANIFEST_CHECK_SKIP  extended regex of scan-root-relative paths to ignore in the reverse scan
#                        (default: internal/ vendor/ tests/ legacy/ + dotfiles + _underscore dirs)
set -euo pipefail

usage() { sed -n '2,21p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "$#" in
    0) MANIFEST="tools/tools-manifest.tsv" ;;
    1) case "$1" in -h | --help) usage 0 ;; -*) usage 2 ;; *) MANIFEST="$1" ;; esac ;;
    2) [[ "$1" == "--" ]] || usage 2; MANIFEST="$2" ;;
    *) usage 2 ;;
esac

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
ie="$(col_any entry_for || true)"
iv="$(col_any verify || true)"
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

TEMP_PARENT="$(cd "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P)" \
    || { echo "temporary-directory parent is unavailable: ${TMPDIR:-/tmp}" >&2; exit 2; }
TEMP_PREFIX="${TEMP_PARENT%/}/tooling-manifest."
TEMP_DIR="$(mktemp -d "${TEMP_PREFIX}XXXXXX")" \
    || { echo "failed to create temporary directory under $TEMP_PARENT" >&2; exit 2; }
TEMP_SUFFIX="${TEMP_DIR#"$TEMP_PREFIX"}"
[[ "$TEMP_DIR" == "$TEMP_PREFIX"* && -n "$TEMP_SUFFIX" && -d "$TEMP_DIR" ]] \
    || { echo "mktemp returned an unsafe temporary directory: ${TEMP_DIR:-<empty>}" >&2; exit 2; }
SEEN_FILE="$TEMP_DIR/seen"
INVENTORY_FILE="$TEMP_DIR/inventory"
: > "$SEEN_FILE"
# shellcheck disable=SC2329  # invoked by the EXIT trap
cleanup() {
    local suffix="${TEMP_DIR#"$TEMP_PREFIX"}"
    if [[ "$TEMP_DIR" == "$TEMP_PREFIX"* && -n "$suffix" && -d "$TEMP_DIR" ]]; then
        rm -rf -- "$TEMP_DIR"
    fi
}
trap cleanup EXIT
seen_count=0
row_number=0

declares_help_contract() { # <verify-field>
    local evidence="$1"
    case "$evidence" in
        *cli-contract* | *help-contract*) return 0 ;;
    esac
    printf '%s\n' "$evidence" | grep -qF -- '--help' \
        && printf '%s\n' "$evidence" | grep -qiE -- 'unknown|invalid[ -]+arg|exit[ =:()-]*2'
}

# Forward drift + per-file contract/syntax. Build the SEEN set of registered paths.
while IFS= read -r line || [[ -n "$line" ]]; do
    row_number=$((row_number + 1))
    line="${line%$'\r'}"
    ((row_number == 1)) && continue
    [[ -z "$line" ]] && continue
    tsv_field "$line" "$ip"; p="$REPLY"
    tsv_field "$line" "$is"; s="$REPLY"
    a="enforce"
    if [[ -n "$ia" ]]; then tsv_field "$line" "$ia"; a="${REPLY:-enforce}"; fi
    e=""
    if [[ -n "$ie" ]]; then tsv_field "$line" "$ie"; e="$REPLY"; fi
    v=""
    if [[ -n "$iv" ]]; then tsv_field "$line" "$iv"; v="$REPLY"; fi
    if [[ -z "$p" ]]; then
        fail "manifest row $row_number has an empty path"
        continue
    fi
    case "$p" in
        /* | [A-Za-z]:* | . | ./* | ../* | */. | */./* | */.. | */../* | *//* | *\\*)
            fail "invalid manifest path (must be normalized and relative): $p"
            continue
            ;;
    esac
    case "$a" in
        enforce | warn) : ;;
        *) fail "invalid audit_level for $p: $a"; continue ;;
    esac
    duplicate=0
    if grep -qxF -- "$p" "$SEEN_FILE" 2>/dev/null; then
        fail "duplicate manifest path: $p"
        duplicate=1
    else
        printf '%s\n' "$p" >> "$SEEN_FILE"
        seen_count=$((seen_count + 1))
    fi
    case "$s" in
        public | installed | helper | break-glass | paused | legacy | package | native | template | vendor) : ;;
        *) fail "invalid manifest surface for $p: ${s:-<empty>}"; continue ;;
    esac
    if [[ -n "$ie" ]]; then
        case "$s" in
            public | installed | break-glass | paused | legacy)
                [[ -n "$e" ]] || row_issue "$a" "$s entry must declare entry_for: $p"
                ;;
            helper)
                [[ -z "$e" ]] || row_issue "$a" "helper entry_for must be blank (not an independent entry): $p"
                ;;
        esac
    fi
    if ((duplicate)); then continue; fi
    f="$SCAN_DIR/$p"
    if [[ ! -e "$f" ]]; then row_issue "$a" "manifest row → missing file: $p"; continue; fi
    case "$s" in
        package | native)
            [[ "$p" == */ && -d "$f" ]] \
                || row_issue "$a" "$s directory path must end in / and name a directory: $p"
            continue
            ;;
        *)
            if [[ "$p" == */ ]]; then
                row_issue "$a" "$s path must not use directory-row syntax: $p"
                continue
            fi
            ;;
    esac
    case "$p" in *.sh | *.py) : ;; *) continue ;; esac # syntax/help apply only to command files
    case "$p" in
        *.sh) bash -n "$f" 2>/dev/null || row_issue "$a" "shell syntax error: $p" ;;
        *.py) command -v python >/dev/null 2>&1 &&
            { python -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], "exec")' "$f" 2>/dev/null || row_issue "$a" "python compile error: $p"; } ;;
    esac
    case "$s" in
        public | installed)
            if [[ -n "$iv" ]] && ! declares_help_contract "$v"; then
                row_issue "$a" "$s entry verify must declare --help=0 and unknown-arg=2 evidence (or a cli-contract test): $p"
            fi
            ;;
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
    grep -qxF -- "$rel" "$SEEN_FILE" 2>/dev/null || fail "unregistered command surface (no manifest row): $rel"
done < "$INVENTORY_FILE"

echo "---"
echo "manifest: $MANIFEST   scan: $SCAN_DIR   registered rows: $seen_count"
if ((fails)); then
    echo "RESULT: $fails fail / $warns warn"
    exit 1
fi
echo "RESULT: OK ($warns warn)"
