#!/usr/bin/env bash
# inventory-check.sh — reconcile a structural command inventory against files on disk.
#
# Generic companion to the tooling-conventions skill. Requires Bash plus standard GNU
# command-line tools available on supported Git Bash/macOS/Linux hosts.
# Only `path` is required; optional `audit_level` controls row findings. All other
# project-owned columns are opaque to this checker.
#
# Checks (row FAIL findings honor `audit_level=warn`; contract/global failures block):
#   FAIL  invalid or duplicate inventory paths
#   FAIL  an inventory row points at a missing file or directory
#   FAIL  a command file on disk (.sh, or executable .py) has no file row
#   FAIL  shell syntax error (bash -n) / python compile error (in-memory compile)
#
# Usage:
#   bash inventory-check.sh [--] [path/to/inventory.tsv]
#   no argument defaults to tools/tools-inventory.tsv
# Env:
#   TOOLS_DIR             scan root (default: directory containing the inventory)
#   INVENTORY_CHECK_SKIP  full regex override for reverse-scan exclusions
#                         (default: match nothing; every command candidate is scanned)
set -euo pipefail

usage() {
    printf '%s\n' \
        'Usage: bash inventory-check.sh [--] [path/to/inventory.tsv]' \
        '       bash inventory-check.sh -h|--help'
    exit "${1:-0}"
}

case "$#" in
    0) INVENTORY="tools/tools-inventory.tsv" ;;
    1) case "$1" in -h | --help) usage 0 ;; -*) usage 2 ;; *) INVENTORY="$1" ;; esac ;;
    2) [[ "$1" == "--" ]] || usage 2; INVENTORY="$2" ;;
    *) usage 2 ;;
esac

[[ -f "$INVENTORY" ]] || { echo "inventory not found: $INVENTORY" >&2; exit 2; }
SCAN_DIR="${TOOLS_DIR:-$(dirname "$INVENTORY")}"
[[ -d "$SCAN_DIR" ]] || { echo "scan directory not found: $SCAN_DIR" >&2; exit 2; }
SCAN_DIR="$(cd "$SCAN_DIR" && pwd -P)" \
    || { echo "scan directory is unavailable: $SCAN_DIR" >&2; exit 2; }
SKIP_RE="${INVENTORY_CHECK_SKIP:-a^}"

fails=0 warns=0
fail() { printf 'FAIL: %s\n' "$*"; fails=$((fails + 1)); }
warn() { printf 'warn: %s\n' "$*"; warns=$((warns + 1)); }
row_issue() {
    local audit_level="$1"
    shift
    if [[ "$audit_level" == "warn" ]]; then warn "$@"; else fail "$@"; fi
}

column_index() {
    local wanted="$1"
    awk -F'\t' -v wanted="$wanted" '
        NR == 1 {
            sub(/\r$/, "", $NF)
            for (i = 1; i <= NF; i++) {
                if ($i == wanted) { print i; exit }
            }
        }
    ' "$INVENTORY"
}

path_column="$(column_index path)"
audit_column="$(column_index audit_level || true)"
[[ -n "$path_column" ]] \
    || { echo "inventory must have a 'path' column" >&2; exit 2; }

# Bash treats tab as IFS whitespace, so `read -a` collapses empty TSV fields.
tsv_field() {
    local value="$1" index="$2"
    while ((index > 1)); do
        if [[ "$value" == *$'\t'* ]]; then value="${value#*$'\t'}"; else value=""; break; fi
        index=$((index - 1))
    done
    REPLY="${value%%$'\t'*}"
}

TEMP_PARENT="$(cd "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P)" \
    || { echo "temporary-directory parent is unavailable: ${TMPDIR:-/tmp}" >&2; exit 2; }
TEMP_PREFIX="${TEMP_PARENT%/}/tooling-inventory."
TEMP_DIR="$(mktemp -d "${TEMP_PREFIX}XXXXXX")" \
    || { echo "failed to create temporary directory under $TEMP_PARENT" >&2; exit 2; }
TEMP_SUFFIX="${TEMP_DIR#"$TEMP_PREFIX"}"
[[ "$TEMP_DIR" == "$TEMP_PREFIX"* && -n "$TEMP_SUFFIX" && -d "$TEMP_DIR" ]] \
    || { echo "mktemp returned an unsafe temporary directory: ${TEMP_DIR:-<empty>}" >&2; exit 2; }
SEEN_FILE="$TEMP_DIR/seen"
COMMANDS_FILE="$TEMP_DIR/commands"
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
while IFS= read -r line || [[ -n "$line" ]]; do
    row_number=$((row_number + 1))
    line="${line%$'\r'}"
    ((row_number == 1)) && continue
    [[ -z "$line" ]] && continue

    tsv_field "$line" "$path_column"; path="$REPLY"
    audit_level="enforce"
    if [[ -n "$audit_column" ]]; then
        tsv_field "$line" "$audit_column"
        audit_level="${REPLY:-enforce}"
    fi

    if [[ -z "$path" ]]; then
        fail "inventory row $row_number has an empty path"
        continue
    fi
    case "$path" in
        /* | [A-Za-z]:* | . | ./* | ../* | */. | */./* | */.. | */../* | *//* | *\\*)
            fail "invalid inventory path (must be normalized and relative): $path"
            continue
            ;;
    esac
    case "$audit_level" in
        enforce | warn) : ;;
        *) fail "invalid audit_level for $path: $audit_level"; continue ;;
    esac
    if grep -qxF -- "$path" "$SEEN_FILE" 2>/dev/null; then
        fail "duplicate inventory path: $path"
        continue
    fi
    printf '%s\n' "$path" >> "$SEEN_FILE"
    seen_count=$((seen_count + 1))

    if [[ "$path" == */ ]]; then
        target="$SCAN_DIR/${path%/}"
        if [[ ! -e "$target" ]]; then
            row_issue "$audit_level" "inventory row -> missing path: $path"
        elif [[ ! -d "$target" ]]; then
            row_issue "$audit_level" "directory inventory path does not name a directory: $path"
        fi
        continue
    fi

    target="$SCAN_DIR/$path"
    if [[ ! -e "$target" ]]; then
        row_issue "$audit_level" "inventory row -> missing path: $path"
        continue
    fi
    if [[ -d "$target" ]]; then
        row_issue "$audit_level" "directory inventory path must end in /: $path"
        continue
    fi
    case "$path" in
        *.sh) bash -n "$target" 2>/dev/null || row_issue "$audit_level" "shell syntax error: $path" ;;
        *.py)
            if ! command -v python >/dev/null 2>&1; then
                echo "python interpreter unavailable for syntax check: $path" >&2
                exit 2
            elif ! python -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], "exec")' "$target" 2>/dev/null; then
                row_issue "$audit_level" "python compile error: $path"
            fi
            ;;
    esac
done < "$INVENTORY"

is_python_cli() {
    local file="$1" mode pathspec="${1#"$SCAN_DIR"/}"
    if command -v git >/dev/null 2>&1 && git -C "$SCAN_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        mode="$(git -C "$SCAN_DIR" ls-files -s -- "$pathspec" 2>/dev/null | awk 'NR==1{print $1}')"
        [[ -n "$mode" ]] && { [[ "$mode" == 100755 ]]; return; }
    fi
    [[ -x "$file" ]]
}

if ! find "$SCAN_DIR" -type f \( -name '*.sh' -o -name '*.py' \) | sort > "$COMMANDS_FILE"; then
    echo "reverse inventory scan failed: $SCAN_DIR" >&2
    exit 2
fi
while IFS= read -r file; do
    relative="${file#"$SCAN_DIR"/}"
    [[ "$relative" =~ $SKIP_RE ]] && continue
    [[ "$file" == *.py ]] && ! is_python_cli "$file" && continue
    grep -qxF -- "$relative" "$SEEN_FILE" 2>/dev/null \
        || fail "unregistered command (no inventory row): $relative"
done < "$COMMANDS_FILE"

echo "---"
echo "inventory: $INVENTORY   scan: $SCAN_DIR   registered rows: $seen_count"
if ((fails)); then
    echo "RESULT: $fails fail / $warns warn"
    exit 1
fi
echo "RESULT: OK ($warns warn)"
