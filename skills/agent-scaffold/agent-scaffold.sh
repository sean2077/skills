#!/usr/bin/env bash
# agent-scaffold.sh — converge a dual-host Claude Code + Codex harness in a repo.
#
# Usage:
#   bash agent-scaffold.sh <apply|plan|doctor|verify|upgrade> [flags]
#
# Modes:
#   apply      add or reconcile the contract; refuse managed runtime drift
#   plan       read-only preview with a copyable apply/upgrade decision
#   doctor     read-only prerequisite and real-symlink capability check
#   verify     read-only current-contract, drift, and projection check
#   upgrade    refresh current managed runtime files, then reconcile the contract
#
# Flags:
#   --profile <default|light>  default includes worktree governance; light omits it
#   --json                     structured output for plan, doctor, or verify
#   -h, --help                 show this help
#
# Run from anywhere inside the target project. Requires git, Python 3.8+, and
# Bash 3.2+. Windows support is Git Bash with native symlink privilege.
# ---8<--- help ends here
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE="$SKILL_DIR/scripts/harness-core.py"
MANIFEST="$SKILL_DIR/scripts/managed-assets.json"

c_blue=$'\033[1;34m'; c_red=$'\033[1;31m'; c_yellow=$'\033[1;33m'; c_green=$'\033[1;32m'; c_off=$'\033[0m'
log()  { printf '%s[harness]%s %s\n' "$c_blue" "$c_off" "$*"; }
ok()   { printf '%s[harness]%s %s\n' "$c_green" "$c_off" "$*"; }
warn() { printf '%s[harness]%s %s\n' "$c_yellow" "$c_off" "$*" >&2; }
die()  { printf '%s[harness] ABORT:%s %s\n' "$c_red" "$c_off" "$*" >&2; exit 2; }
usage() { sed -n '2,/^# ---8<---/p' "$0" | sed '/^# ---8<---/d; s/^# \?//'; exit "${1:-0}"; }

[[ $# -ge 1 ]] || usage 2
if [[ "$1" == -h || "$1" == --help ]]; then
  [[ $# -eq 1 ]] || usage 2
  usage 0
fi
MODE="$1"
shift
case "$MODE" in
  apply|plan|doctor|verify|upgrade) ;;
  *) die "unknown mode: $MODE (apply|plan|doctor|verify|upgrade)" ;;
esac

PROFILE=default
JSON_OUTPUT=0
HELP_OUTPUT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || die "--profile requires default or light"
      PROFILE="$2"
      shift
      ;;
    --profile=*) PROFILE="${1#*=}" ;;
    --json) JSON_OUTPUT=1 ;;
    -h|--help) HELP_OUTPUT=1 ;;
    *) die "unknown flag: $1" ;;
  esac
  shift
done
case "$PROFILE" in default|light) ;; *) die "unknown profile: $PROFILE (default|light)" ;; esac
if [[ "$JSON_OUTPUT" == 1 ]]; then
  case "$MODE" in plan|doctor|verify) ;; *) die "--json is available only for plan, doctor, and verify" ;; esac
fi
[[ "$HELP_OUTPUT" == 0 ]] || usage 0

WORKTREE_FLOW=1
[[ "$PROFILE" == light ]] && WORKTREE_FLOW=0
FORCE_SCRIPTS=0
[[ "$MODE" == upgrade ]] && FORCE_SCRIPTS=1

TARGET="$(git rev-parse --show-toplevel 2>/dev/null)" \
  || die "not inside a git repository — run from within the target project"

TEMP_PARENT="$(cd "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P)" \
  || die "temporary-directory parent is unavailable: ${TMPDIR:-/tmp}"
TEMP_PREFIX="${TEMP_PARENT%/}/agent-scaffold."
TMPDIR_H="$(mktemp -d "${TEMP_PREFIX}XXXXXX")" \
  || die "failed to create a temporary directory under $TEMP_PARENT"
TEMP_SUFFIX="${TMPDIR_H#"$TEMP_PREFIX"}"
[[ "$TMPDIR_H" == "$TEMP_PREFIX"* && -n "$TEMP_SUFFIX" && -d "$TMPDIR_H" ]] \
  || die "mktemp returned an unsafe temporary directory: ${TMPDIR_H:-<empty>}"
# shellcheck disable=SC2329  # invoked by the EXIT trap
cleanup_temp_dir() {
  local suffix="${TMPDIR_H#"$TEMP_PREFIX"}"
  if [[ "$TMPDIR_H" == "$TEMP_PREFIX"* && -n "$suffix" && -d "$TMPDIR_H" ]]; then
    rm -rf -- "$TMPDIR_H"
  fi
}
trap cleanup_temp_dir EXIT

PYTHON_CMD=()
python_compatible() {
  PYTHONUTF8=1 "$@" -c \
    'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 8) else 1)' \
    >/dev/null 2>&1
}
resolve_python() {
  PYTHON_CMD=()
  if [[ -n "${PYTHON_BIN:-}" ]] && python_compatible "$PYTHON_BIN"; then
    PYTHON_CMD=("$PYTHON_BIN")
  elif python_compatible python; then
    PYTHON_CMD=(python)
  elif python_compatible python3; then
    PYTHON_CMD=(python3)
  elif python_compatible py -3; then
    PYTHON_CMD=(py -3)
  else
    return 1
  fi
}
run_python() { PYTHONUTF8=1 "${PYTHON_CMD[@]}" "$@"; }
resolve_python || die "python 3.8+ is required (set PYTHON_BIN, or install python/python3/py -3)"
run_core() { run_python "$CORE" --manifest "$MANIFEST" "$@"; }
atomic_replace_file() { run_core files atomic-replace --source "$1" --target "$2"; }

asset_field() {  # <asset-id> <field>
  run_core assets get --id "$1" --field "$2"
}
asset_source() { asset_field "$1" source; }

copy_script() {  # <source> <destination> <executable:0|1>
  local source="$1" destination="$2" executable="$3"
  mkdir -p "$(dirname "$destination")"
  if [[ -e "$destination" && "$FORCE_SCRIPTS" != 1 ]]; then
    cmp -s "$source" "$destination" \
      || die "${destination#"$TARGET"/}: managed runtime drift requires upgrade"
  else
    atomic_replace_file "$source" "$destination"
  fi
  if [[ "$executable" == 1 ]]; then
    chmod +x "$destination" 2>/dev/null || true
  fi
}

copy_if_missing() {  # <source> <destination>
  local source="$1" destination="$2"
  mkdir -p "$(dirname "$destination")"
  [[ -e "$destination" ]] || atomic_replace_file "$source" "$destination"
}

ensure_line() {  # <file> <logical-line>
  local file="$1" line="$2" matches=0 candidate
  mkdir -p "$(dirname "$file")"
  if [[ -f "$file" ]]; then
    matches="$(tr '\r' '\n' < "$file" | grep -cxF "$line" || true)"
  fi
  [[ "$matches" -gt 0 ]] && return
  candidate="$(mktemp "$TMPDIR_H/ensure-line.XXXXXX")" \
    || die "could not allocate a line-update candidate"
  if [[ -f "$file" ]]; then
    cp "$file" "$candidate"
  else
    : > "$candidate"
  fi
  if [[ -s "$candidate" && -n "$(tail -c 1 "$candidate")" ]]; then
    printf '\n' >> "$candidate"
  fi
  printf '%s\n' "$line" >> "$candidate"
  atomic_replace_file "$candidate" "$file"
}

prepare_hook_addition() {  # <source> <output>
  run_core hooks prepare --source "$1" --output "$2" --profile "$PROFILE"
}

write_hook_config() {  # <host-label> <existing-file> <addition-file> <host>
  local label="$1" existing="$2" addition="$3" output="$TMPDIR_H/merged-$4.json"
  local args=(hooks merge --addition "$addition" --output "$output" --target "$TARGET")
  [[ -e "$existing" ]] && args+=(--existing "$existing")
  run_core "${args[@]}"
  if [[ -f "$existing" ]] && cmp -s "$existing" "$output"; then
    log "$label hooks already wired (no change)"
  else
    mkdir -p "$(dirname "$existing")"
    atomic_replace_file "$output" "$existing"
    ok "$label hooks wired → ${existing#"$TARGET"/}"
  fi
}

validate_agents_markers() {
  [[ -f "$TARGET/AGENTS.md" ]] || return 0
  run_core agents validate-markers --file "$TARGET/AGENTS.md"
}

render_agents_template() {
  local source
  source="$SKILL_DIR/$(asset_source contract.agents)"
  run_core agents render --source "$source" --profile "$PROFILE"
}

ensure_agents_md() {
  local agents block="$TMPDIR_H/block.md" rendered="$TMPDIR_H/AGENTS.harness.md"
  local candidate="$TMPDIR_H/AGENTS.updated.md"
  agents="$TARGET/$(asset_field contract.agents target)"
  validate_agents_markers
  render_agents_template > "$rendered"
  awk '/<!-- agent-scaffold:start/{f=1} f{print} /<!-- agent-scaffold:end/{f=0}' "$rendered" > "$block"
  if [[ ! -e "$agents" ]]; then
    atomic_replace_file "$rendered" "$agents"
    ok "AGENTS.md created with the managed harness block; project prose stays author-owned"
  elif grep -qF '<!-- agent-scaffold:start' "$agents"; then
    awk -v block_file="$block" '
      BEGIN { while ((getline line < block_file) > 0) block = block line "\n" }
      /<!-- agent-scaffold:start/ { printf "%s", block; skip=1; next }
      skip && /<!-- agent-scaffold:end/ { skip=0; next }
      !skip { print }
    ' "$agents" > "$candidate"
    if cmp -s "$agents" "$candidate"; then
      log "AGENTS.md harness block already current (no change)"
    else
      atomic_replace_file "$candidate" "$agents"
      log "AGENTS.md harness block refreshed (project prose preserved)"
    fi
  else
    cp "$agents" "$candidate"
    printf '\n' >> "$candidate"
    cat "$block" >> "$candidate"
    atomic_replace_file "$candidate" "$agents"
    ok "AGENTS.md exists — appended the harness block (review placement)"
  fi
}

ensure_claude_md_symlink() {
  local manager
  manager="$SKILL_DIR/$(asset_source runtime.symlink-manager)"
  run_python "$manager" ensure-contract --repo "$TARGET"
}

preflight_install() {
  local manager
  run_core preflight --target "$TARGET" --profile "$PROFILE" --mode "$MODE"
  manager="$SKILL_DIR/$(asset_source runtime.symlink-manager)"
  run_python "$manager" doctor --repo "$TARGET" >/dev/null
}

install_assets() {
  local _id source target strategy executable
  while IFS=$'\t' read -r _id source target strategy executable; do
    executable="${executable%$'\r'}"
    case "$strategy" in
      copy) copy_script "$SKILL_DIR/$source" "$TARGET/$target" "$executable" ;;
      seed) copy_if_missing "$SKILL_DIR/$source" "$TARGET/$target" ;;
      *) die "internal manifest error: unsupported install strategy $strategy" ;;
    esac
  done < <(run_core assets list --profile "$PROFILE" --strategy copy --strategy seed)
}

do_install() {
  local contract_linked=0 adopted_claude=0
  log "target repo: $TARGET   mode: $MODE   profile: $PROFILE"

  if [[ ! -e "$TARGET/AGENTS.md" && -f "$TARGET/CLAUDE.md" && ! -L "$TARGET/CLAUDE.md" ]]; then
    atomic_replace_file "$TARGET/CLAUDE.md" "$TARGET/AGENTS.md"
    cmp -s "$TARGET/CLAUDE.md" "$TARGET/AGENTS.md" \
      || die "could not adopt CLAUDE.md prose into AGENTS.md byte-for-byte"
    adopted_claude=1
    ok "CLAUDE.md prose adopted as AGENTS.md (SSOT)"
  fi
  if [[ "$adopted_claude" == 1 ]]; then
    rm -f -- "$TARGET/CLAUDE.md"
  fi
  if [[ -e "$TARGET/AGENTS.md" ]]; then
    ensure_claude_md_symlink
    contract_linked=1
  fi
  ensure_agents_md
  [[ "$contract_linked" == 1 ]] || ensure_claude_md_symlink

  install_assets
  log "active-profile managed assets are in place"

  mkdir -p "$TARGET/.agents/skills" "$TARGET/.agents/subagents"
  touch "$TARGET/.agents/skills/.gitkeep" "$TARGET/.agents/subagents/.gitkeep"

  local cc_source cx_source cc_add="$TMPDIR_H/claude-add.json" cx_add="$TMPDIR_H/codex-add.json"
  cc_source="$SKILL_DIR/$(asset_source host.claude-hooks)"
  cx_source="$SKILL_DIR/$(asset_source host.codex-hooks)"
  prepare_hook_addition "$cc_source" "$cc_add"
  prepare_hook_addition "$cx_source" "$cx_add"
  write_hook_config "Claude Code" "$TARGET/.claude/settings.json" "$cc_add" claude
  write_hook_config "Codex" "$TARGET/.codex/hooks.json" "$cx_add" codex

  local _line_id line_target line
  while IFS=$'\t' read -r _line_id line_target line; do
    line="${line%$'\r'}"
    ensure_line "$TARGET/$line_target" "$line"
  done < <(run_core lines --profile "$PROFILE")
  if [[ "$WORKTREE_FLOW" != 1 ]]; then
    log "light profile selected — existing worktree-specific ignore entries remain project-owned"
  fi

  bash "$TARGET/.agents/relink-skills.sh"
  run_python "$TARGET/.agents/tools/generate-subagents.py" --import
  log "project-owned subagent drift guard: wire 'python .agents/tools/generate-subagents.py --check' only when useful"

  echo
  ok "harness $MODE complete."
  log "Codex trust: project-level .codex/ loads only for a trusted project."
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    log "next: start changes with bash .agents/tools/worktree.sh new <name>."
  else
    log "next: use the project's existing branch/change workflow."
  fi
}

do_report() {
  local args=(report "$MODE" --target "$TARGET" --profile "$PROFILE")
  [[ "$JSON_OUTPUT" == 1 ]] && args+=(--json)
  run_core "${args[@]}"
}

case "$MODE" in
  apply|upgrade)
    preflight_install
    do_install
    ;;
  plan|doctor|verify)
    do_report
    ;;
esac
