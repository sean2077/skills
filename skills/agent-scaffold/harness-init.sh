#!/usr/bin/env bash
# harness-init.sh — install or retrofit the dual-host (Claude Code + Codex) agent
# harness into a project. Idempotent and merge-aware: it never clobbers existing
# config, and re-running it changes nothing.
#
# Usage:
#   bash harness-init.sh <init|retrofit|plan|doctor|verify|upgrade> [flags]
#
# Modes:
#   init       greenfield — lay down the full harness (seeds an example subagent)
#   retrofit   merge into a project that already has some .claude/.codex/AGENTS.md
#   plan       read-only — preview what init/retrofit would create/merge/migrate
#   doctor     read-only — verify git + real file/directory symlink capability
#   verify     read-only — report harness presence / drift / parity
#   upgrade    retrofit + re-copy the vendored scripts over the installed ones
#
# Flags:
#   --no-worktree          omit the worktree lifecycle, trunk-edit guard, and managed worktree policy
#   --no-format-hook        deprecated no-op; formatter hooks are project-owned
#   --no-husky              do not set up the .husky/pre-commit drift guard
#   --no-example-subagent   do not seed the example code-reviewer subagent (init)
#   --example-subagent      seed it even on retrofit/upgrade
#   --force-scripts         overwrite already-installed vendored scripts (implied by upgrade)
#   -h, --help              this help
# Optional-profile flags are per invocation; repeat them on later upgrade/verify runs.
#
# Run it from anywhere inside the TARGET project; it resolves the repo via git.
# ---8<--- help ends here
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$SKILL_DIR/templates"

c_blue=$'\033[1;34m'; c_red=$'\033[1;31m'; c_yellow=$'\033[1;33m'; c_green=$'\033[1;32m'; c_off=$'\033[0m'
log()  { printf '%s[harness]%s %s\n' "$c_blue"   "$c_off" "$*"; }
ok()   { printf '%s[harness]%s %s\n' "$c_green"  "$c_off" "$*"; }
warn() { printf '%s[harness]%s %s\n' "$c_yellow" "$c_off" "$*" >&2; }
die()  { printf '%s[harness] ABORT:%s %s\n' "$c_red" "$c_off" "$*" >&2; exit 2; }
usage() { sed -n '2,/^# ---8<---/p' "$0" | sed '/^# ---8<---/d; s/^# \?//'; exit "${1:-0}"; }

# ---- args ------------------------------------------------------------------
[[ $# -ge 1 ]] || usage 1
MODE="$1"; shift
case "$MODE" in init|retrofit|plan|doctor|verify|upgrade) ;; -h|--help) usage 0 ;; *) die "unknown mode: $MODE (init|retrofit|plan|doctor|verify|upgrade)";; esac

WORKTREE_FLOW=1; HUSKY=1; FORCE_SCRIPTS=0; LEGACY_NO_FORMAT_HOOK=0
EXAMPLE_SUBAGENT="auto"   # auto → on for init, off otherwise
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-worktree) WORKTREE_FLOW=0 ;;
    --no-format-hook) LEGACY_NO_FORMAT_HOOK=1 ;;
    --no-husky) HUSKY=0 ;;
    --no-example-subagent) EXAMPLE_SUBAGENT=0 ;;
    --example-subagent) EXAMPLE_SUBAGENT=1 ;;
    --force-scripts) FORCE_SCRIPTS=1 ;;
    -h|--help) usage 0 ;;
    *) die "unknown flag: $1" ;;
  esac
  shift
done
[[ "$MODE" == upgrade ]] && FORCE_SCRIPTS=1
[[ "$LEGACY_NO_FORMAT_HOOK" == 1 ]] && \
  warn "--no-format-hook is deprecated and ignored; formatter hooks are now project-owned"
if [[ "$EXAMPLE_SUBAGENT" == auto ]]; then
  [[ "$MODE" == init ]] && EXAMPLE_SUBAGENT=1 || EXAMPLE_SUBAGENT=0
fi

# ---- resolve target repo ---------------------------------------------------
TARGET="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository — run from within the target project"
log "target repo: $TARGET   mode: $MODE"

RUNTIME_ROOT=".agents/tools"
LEGACY_RUNTIME_ROOT="tools/agent"

TMPDIR_H="$(mktemp -d)"; trap 'rm -rf "$TMPDIR_H"' EXIT

# ---- python runtime --------------------------------------------------------
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

# ---- owned-hook reconciliation (python; no jq dependency) -----------------
# Upgrade removes only agent-scaffold-owned commands before merging the current
# canonical additions. User hooks and unrelated config keys remain untouched.

PY_MERGE='
import json, os, re
ex = os.environ.get("HARNESS_EXISTING") or ""
existing = json.load(open(ex)) if ex and os.path.exists(ex) else {}
add = json.load(open(os.environ["HARNESS_ADD"]))
if not isinstance(existing.get("hooks"), dict):
    existing["hooks"] = {}
root = os.environ.get("HARNESS_TARGET", "")
trimmed_root = root.rstrip("/\\")
basename_start = max(trimmed_root.rfind("/"), trimmed_root.rfind("\\")) + 1
case_probe = None
for index in range(basename_start, len(trimmed_root)):
    character = trimmed_root[index]
    if character.isascii() and character.isalpha():
        replacement = character.upper() if character.islower() else character.lower()
        case_probe = trimmed_root[:index] + replacement + trimmed_root[index + 1:]
        break
try:
    case_insensitive_paths = case_probe is not None and os.path.samefile(root, case_probe)
except OSError:
    case_insensitive_paths = False
managed_path = re.compile(
    r"(?:^|[/\s\"\x27;&|()<>])(?:\.agents/tools|tools/agent)/hooks/"
    r"(?:trunk_edit_guard|authority_doc_budget|format_on_edit)\.sh"
    r"(?=$|[\s\"\x27;&|()<>])",
    re.IGNORECASE if case_insensitive_paths else 0,
)
def is_managed(command):
    return bool(managed_path.search(str(command or "").replace("\\", "/")))
def union(a, b):
    out = list(a or [])
    seen = {h.get("command") for h in out}
    for h in b or []:
        if h.get("command") not in seen:
            out.append(h)
            seen.add(h.get("command"))
    return out
def merge_event(cur, add_arr):
    cleaned = []
    for group in cur or []:
        if not isinstance(group, dict):
            cleaned.append(group)
            continue
        group = dict(group)
        hooks = group.get("hooks") or []
        group["hooks"] = [h for h in hooks if not is_managed(h.get("command", ""))]
        if group["hooks"] or any(k not in {"matcher", "hooks"} for k in group):
            cleaned.append(group)
    cur = cleaned
    for g in add_arr:
        i = next((k for k, x in enumerate(cur) if isinstance(x, dict) and x.get("matcher") == g.get("matcher")), -1)
        if i < 0:
            cur.append(g)
        else:
            cur[i]["hooks"] = union(cur[i].get("hooks"), g.get("hooks"))
    return cur
for ev in ("PreToolUse", "PostToolUse"):
    if ev in add.get("hooks", {}):
        merged = merge_event(existing["hooks"].get(ev), add["hooks"].get(ev) or [])
        if merged:
            existing["hooks"][ev] = merged
        else:
            existing["hooks"].pop(ev, None)
with open(os.environ["HARNESS_OUT"], "w") as f:
    f.write(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")
'

PY_FILTER_HOOKS='
import json, os
with open(os.environ["HARNESS_ADD"]) as f:
    data = json.load(f)
disabled = []
if os.environ.get("HARNESS_ENABLE_WORKTREE") != "1":
    disabled.append("trunk_edit_guard")
for event, groups in list(data.get("hooks", {}).items()):
    kept = []
    for group in groups or []:
        group = dict(group)
        group["hooks"] = [
            hook for hook in group.get("hooks", [])
            if not any(name in str(hook.get("command", "")) for name in disabled)
        ]
        if group["hooks"] or any(key not in {"matcher", "hooks"} for key in group):
            kept.append(group)
    data["hooks"][event] = kept
with open(os.environ["HARNESS_OUT"], "w") as f:
    f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
'

PY_VALIDATE_HOOK_CONFIG='
import json, math, os, sys
path = os.environ["HARNESS_EXISTING"]
name = os.environ["HARNESS_CONFIG_NAME"]
def reject_constant(value):
    raise ValueError(f"non-standard constant {value}")
def validate_json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number")
    if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("unpaired Unicode surrogate")
    if isinstance(value, list):
        for item in value:
            validate_json_value(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            validate_json_value(key)
            validate_json_value(item)
try:
    with open(path, encoding="utf-8") as source:
        data = json.load(source, parse_constant=reject_constant)
    validate_json_value(data)
except json.JSONDecodeError as exc:
    print(
        f"[harness] ABORT: {name}: invalid JSON "
        f"({exc.msg}, line {exc.lineno}, column {exc.colno})",
        file=sys.stderr,
    )
    raise SystemExit(2)
except (OSError, UnicodeError) as exc:
    print(f"[harness] ABORT: {name}: cannot read UTF-8 JSON ({exc})", file=sys.stderr)
    raise SystemExit(2)
except (ValueError, RecursionError) as exc:
    print(f"[harness] ABORT: {name}: invalid JSON ({exc})", file=sys.stderr)
    raise SystemExit(2)
if not isinstance(data, dict):
    print(f"[harness] ABORT: {name}: top level must be a JSON object", file=sys.stderr)
    raise SystemExit(2)
hooks = data.get("hooks")
if hooks is not None and not isinstance(hooks, dict):
    print(f"[harness] ABORT: {name}: hooks must be a JSON object or null", file=sys.stderr)
    raise SystemExit(2)
for event in ("PreToolUse", "PostToolUse"):
    groups = (hooks or {}).get(event)
    if groups is None:
        continue
    if not isinstance(groups, list):
        print(f"[harness] ABORT: {name}: hooks.{event} must be an array or null", file=sys.stderr)
        raise SystemExit(2)
    for group_index, group in enumerate(groups):
        field = f"hooks.{event}[{group_index}]"
        if not isinstance(group, dict):
            print(f"[harness] ABORT: {name}: {field} must be a JSON object", file=sys.stderr)
            raise SystemExit(2)
        entries = group.get("hooks")
        if entries is None:
            continue
        if not isinstance(entries, list):
            print(f"[harness] ABORT: {name}: {field}.hooks must be an array or null", file=sys.stderr)
            raise SystemExit(2)
        for hook_index, hook in enumerate(entries):
            if not isinstance(hook, dict):
                print(
                    f"[harness] ABORT: {name}: {field}.hooks[{hook_index}] "
                    "must be a JSON object",
                    file=sys.stderr,
                )
                raise SystemExit(2)
            if "command" in hook and not isinstance(hook["command"], str):
                print(
                    f"[harness] ABORT: {name}: {field}.hooks[{hook_index}].command "
                    "must be a string",
                    file=sys.stderr,
                )
                raise SystemExit(2)
'

PY_VERIFY_HOOKS='
import json, os, re, sys
def load(name):
    with open(os.environ[name], encoding="utf-8") as source:
        return json.load(source)
def hook_tuples(data):
    found = set()
    for event, groups in data.get("hooks", {}).items():
        for group in groups or []:
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher")
            for hook in group.get("hooks") or []:
                if isinstance(hook, dict) and "command" in hook:
                    found.add((event, matcher, str(hook["command"])))
    return found
try:
    actual = hook_tuples(load("HARNESS_EXISTING"))
    expected = hook_tuples(load("HARNESS_EXPECTED"))
except (OSError, ValueError, TypeError):
    raise SystemExit(1)
root = os.environ.get("HARNESS_TARGET", "")
trimmed_root = root.rstrip("/\\")
basename_start = max(trimmed_root.rfind("/"), trimmed_root.rfind("\\")) + 1
case_probe = None
for index in range(basename_start, len(trimmed_root)):
    character = trimmed_root[index]
    if character.isascii() and character.isalpha():
        replacement = character.upper() if character.islower() else character.lower()
        case_probe = trimmed_root[:index] + replacement + trimmed_root[index + 1:]
        break
try:
    case_insensitive_paths = case_probe is not None and os.path.samefile(root, case_probe)
except OSError:
    case_insensitive_paths = False
managed_path = re.compile(
    r"(?:^|[/\s\"\x27;&|()<>])(?:\.agents/tools|tools/agent)/hooks/"
    r"(?:trunk_edit_guard|authority_doc_budget|format_on_edit)\.sh"
    r"(?=$|[\s\"\x27;&|()<>])",
    re.IGNORECASE if case_insensitive_paths else 0,
)
managed_actual = {item for item in actual if managed_path.search(item[2].replace("\\", "/"))}
raise SystemExit(0 if expected <= actual and managed_actual <= expected else 1)
'

# merge_hooks <existing-or-empty> <addition-file> <out>
merge_hooks() {
  local existing="$1" add="$2" out="$3"
  HARNESS_EXISTING="$existing" HARNESS_ADD="$add" HARNESS_OUT="$out" HARNESS_TARGET="$TARGET" \
    run_python -c "$PY_MERGE"
}

# Prepare a canonical hook addition for the selected optional features. The
# merge step then removes stale managed commands before adding this filtered set.
prepare_hook_addition() {
  local src="$1" out="$2"
  HARNESS_ADD="$src" HARNESS_OUT="$out" \
    HARNESS_ENABLE_WORKTREE="$WORKTREE_FLOW" \
    run_python -c "$PY_FILTER_HOOKS"
}

validate_existing_hook_config() {  # <existing-file> <repo-relative-name>
  local existing="$1" name="$2"
  [[ -L "$existing" ]] && \
    die "$name: symlinked hook configs are unsupported; replace it with a regular file before installing"
  [[ -e "$existing" ]] || return 0
  HARNESS_EXISTING="$existing" HARNESS_CONFIG_NAME="$name" \
    run_python -c "$PY_VALIDATE_HOOK_CONFIG"
}

validate_existing_hook_configs() {
  validate_existing_hook_config "$TARGET/.claude/settings.json" ".claude/settings.json"
  validate_existing_hook_config "$TARGET/.codex/hooks.json" ".codex/hooks.json"
}

verify_hook_config() {  # <existing> <expected-profile-addition>
  HARNESS_EXISTING="$1" HARNESS_EXPECTED="$2" HARNESS_TARGET="$TARGET" \
    run_python -c "$PY_VERIFY_HOOKS"
}

write_hook_config() {  # <host-label> <existing-file> <addition-file>
  local label="$1" existing="$2" add="$3" out="$TMPDIR_H/merged.json"
  merge_hooks "$existing" "$add" "$out"
  if [[ -f "$existing" ]] && cmp -s "$existing" "$out"; then
    log "$label hooks already wired (no change)"
  else
    mkdir -p "$(dirname "$existing")"; mv "$out" "$existing"; ok "$label hooks wired → ${existing#"$TARGET"/}"
  fi
}

# ---- small idempotent helpers ----------------------------------------------
copy_script() {  # <src> <dst>
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [[ -e "$dst" && "$FORCE_SCRIPTS" != 1 ]]; then :; else cp "$src" "$dst"; fi
  chmod +x "$dst" 2>/dev/null || true
}
copy_if_missing() {  # <src> <dst>
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  [[ -e "$dst" ]] || cp "$src" "$dst"
}
ensure_line() {  # <file> <line>
  local file="$1" line="$2" matches
  mkdir -p "$(dirname "$file")"; touch "$file"
  matches="$(tr '\r' '\n' < "$file" | grep -cxF "$line" || true)"
  [[ "$matches" -gt 0 ]] && return
  if [[ -s "$file" && -n "$(tail -c 1 "$file")" ]]; then
    printf '\n' >> "$file"
  fi
  printf '%s\n' "$line" >> "$file"
}
remove_line() {  # <file> <logical-line>; preserve every non-matching byte
  local file="$1" line="$2"
  [[ -f "$file" ]] || return 0
  HARNESS_LINE_FILE="$file" HARNESS_LINE_VALUE="$line" run_python -c '
import os
path = os.environ["HARNESS_LINE_FILE"]
target = os.environ["HARNESS_LINE_VALUE"].encode("utf-8")
with open(path, "rb") as source:
    before = source.read()
parts = before.splitlines(keepends=True)
after = b"".join(part for part in parts if part.rstrip(b"\r\n") != target)
if after != before:
    with open(path, "wb") as destination:
        destination.write(after)
'
}
replace_managed_text() {  # <file> <owned-old-text> <owned-new-text>; upgrade only
  local file="$1" before="$2" after="$3"
  [[ "$MODE" == upgrade && -f "$file" ]] || return 0
  HARNESS_TEXT_FILE="$file" HARNESS_TEXT_BEFORE="$before" HARNESS_TEXT_AFTER="$after" run_python -c '
import os
path = os.environ["HARNESS_TEXT_FILE"]
before = os.environ["HARNESS_TEXT_BEFORE"].encode("utf-8")
after = os.environ["HARNESS_TEXT_AFTER"].encode("utf-8")
with open(path, "rb") as source:
    content = source.read()
updated = content.replace(before, after)
if updated != content:
    with open(path, "wb") as destination:
        destination.write(updated)
'
}

runtime_pairs() {
  # format_on_edit.sh is retired. Keep its old path in the migration inventory
  # for one compatibility cycle so upgrade can remove legacy installed copies.
  printf '%s\n' \
    "worktree.sh:worktree.sh" \
    "trunk_edit_guard.sh:hooks/trunk_edit_guard.sh" \
    "authority_doc_budget.sh:hooks/authority_doc_budget.sh" \
    "format_on_edit.sh:hooks/format_on_edit.sh" \
    "hook-common.sh:hooks/hook-common.sh" \
    "hook-paths.py:hooks/hook-paths.py" \
    "generate-subagents.py:generate-subagents.py"
}

has_legacy_runtime() {
  local pair rel legacy
  while IFS= read -r pair; do
    rel="${pair##*:}"
    legacy="$TARGET/$LEGACY_RUNTIME_ROOT/$rel"
    [[ -e "$legacy" || -L "$legacy" ]] && return 0
  done < <(runtime_pairs)
  return 1
}

stale_managed_hook_wiring_present() {
  local config
  for config in "$TARGET/.claude/settings.json" "$TARGET/.codex/hooks.json"; do
    [[ -f "$config" ]] || continue
    if HARNESS_LEGACY_CONFIG="$config" HARNESS_TARGET="$TARGET" run_python -c '
import json, os, re
try:
    with open(os.environ["HARNESS_LEGACY_CONFIG"], encoding="utf-8") as source:
        data = json.load(source)
except (OSError, ValueError, TypeError):
    raise SystemExit(1)
root = os.environ.get("HARNESS_TARGET", "")
trimmed_root = root.rstrip("/\\")
basename_start = max(trimmed_root.rfind("/"), trimmed_root.rfind("\\")) + 1
case_probe = None
for index in range(basename_start, len(trimmed_root)):
    character = trimmed_root[index]
    if character.isascii() and character.isalpha():
        replacement = character.upper() if character.islower() else character.lower()
        case_probe = trimmed_root[:index] + replacement + trimmed_root[index + 1:]
        break
try:
    insensitive = case_probe is not None and os.path.samefile(root, case_probe)
except OSError:
    insensitive = False
owned = re.compile(
    r"(?:^|[/\s\"\x27;&|()<>])(?:"
    r"tools/agent/hooks/(?:trunk_edit_guard|authority_doc_budget|format_on_edit)\.sh"
    r"|\.agents/tools/hooks/format_on_edit\.sh)"
    r"(?=$|[\s\"\x27;&|()<>])",
    re.IGNORECASE if insensitive else 0,
)
def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
raise SystemExit(0 if any(owned.search(value.replace("\\", "/")) for value in strings(data)) else 1)
' 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

legacy_package_scripts_present() {
  [[ -f "$TARGET/package.json" ]] || return 1
  HARNESS_LEGACY_PACKAGE="$TARGET/package.json" run_python -c '
import json, os
try:
    with open(os.environ["HARNESS_LEGACY_PACKAGE"], encoding="utf-8") as source:
        scripts = (json.load(source).get("scripts") or {})
except (AttributeError, OSError, ValueError, TypeError):
    raise SystemExit(1)
legacy = {
    "gen:subagents": "python tools/agent/generate-subagents.py",
    "check:agents": "python tools/agent/generate-subagents.py --check",
}
raise SystemExit(0 if any(scripts.get(key) == value for key, value in legacy.items()) else 1)
' 2>/dev/null
}

legacy_managed_docs_present() {
  if [[ -f "$TARGET/.agents/subagents/README.md" ]] \
    && grep -Fq "python tools/agent/generate-subagents.py" "$TARGET/.agents/subagents/README.md"; then
    return 0
  fi
  [[ -f "$TARGET/AGENTS.md" ]] || return 1
  HARNESS_LEGACY_AGENTS="$TARGET/AGENTS.md" run_python -c '
import os
try:
    with open(os.environ["HARNESS_LEGACY_AGENTS"], encoding="utf-8") as source:
        text = source.read()
except (OSError, UnicodeError):
    raise SystemExit(1)
start = text.find("<!-- agent-scaffold:start")
end = text.find("<!-- agent-scaffold:end -->", start + 1)
managed = text[start:end] if start >= 0 and end >= 0 else ""
raise SystemExit(0 if "tools/agent/" in managed else 1)
' 2>/dev/null
}

has_legacy_managed_installation() {
  has_legacy_runtime && return 0
  stale_managed_hook_wiring_present && return 0
  [[ -e "$TARGET/$RUNTIME_ROOT/hooks/format_on_edit.sh" \
    || -L "$TARGET/$RUNTIME_ROOT/hooks/format_on_edit.sh" ]] && return 0
  legacy_package_scripts_present && return 0
  legacy_managed_docs_present && return 0
  if [[ -f "$TARGET/.husky/pre-commit" ]] \
    && tr '\r' '\n' < "$TARGET/.husky/pre-commit" | grep -qxF "python tools/agent/generate-subagents.py --check"; then
    return 0
  fi
  local attribute
  for attribute in \
    "tools/agent/*.sh text eol=lf" \
    "tools/agent/hooks/*.sh text eol=lf" \
    "tools/agent/*.py text eol=lf" \
    "tools/agent/hooks/*.py text eol=lf"; do
    if [[ -f "$TARGET/.gitattributes" ]] \
      && tr '\r' '\n' < "$TARGET/.gitattributes" | grep -qxF "$attribute"; then
      return 0
    fi
  done
  local projection_root
  for projection_root in "$TARGET/.claude/agents" "$TARGET/.codex/agents"; do
    [[ -d "$projection_root" ]] || continue
    grep -r -Fq -- "Run: python tools/agent/generate-subagents.py" "$projection_root" 2>/dev/null \
      && return 0
  done
  return 1
}

validate_runtime_layout() {
  local pair rel legacy current
  if has_legacy_managed_installation && [[ "$MODE" != upgrade ]]; then
    die "legacy $LEGACY_RUNTIME_ROOT layout or managed integration detected; run agent-scaffold upgrade (see references/harness-migration.md)"
  fi
  while IFS= read -r pair; do
    rel="${pair##*:}"
    legacy="$TARGET/$LEGACY_RUNTIME_ROOT/$rel"
    current="$TARGET/$RUNTIME_ROOT/$rel"
    if [[ -e "$legacy" || -L "$legacy" ]] && [[ ! -f "$legacy" || -L "$legacy" ]]; then
      die "runtime migration conflict: expected a regular managed file at $LEGACY_RUNTIME_ROOT/$rel"
    fi
    if [[ -e "$current" || -L "$current" ]] && [[ ! -f "$current" || -L "$current" ]]; then
      die "runtime layout conflict: expected a regular managed file at $RUNTIME_ROOT/$rel"
    fi
    if [[ ( -e "$legacy" || -L "$legacy" ) && ( -e "$current" || -L "$current" ) ]] \
      && ! cmp -s "$legacy" "$current"; then
      die "runtime migration conflict: both $LEGACY_RUNTIME_ROOT/$rel and $RUNTIME_ROOT/$rel exist with different content"
    fi
  done < <(runtime_pairs)
}

migrate_legacy_runtime() {
  [[ "$MODE" == upgrade ]] || return 0
  local pair rel legacy current migrated=0
  while IFS= read -r pair; do
    rel="${pair##*:}"
    legacy="$TARGET/$LEGACY_RUNTIME_ROOT/$rel"
    current="$TARGET/$RUNTIME_ROOT/$rel"
    [[ -e "$legacy" || -L "$legacy" ]] || continue
    mkdir -p "$(dirname "$current")"
    if [[ -e "$current" || -L "$current" ]]; then
      rm -f -- "$legacy"
    else
      mv -- "$legacy" "$current"
    fi
    migrated=1
  done < <(runtime_pairs)
  if [[ "$migrated" == 1 ]]; then
    rmdir "$TARGET/$LEGACY_RUNTIME_ROOT/hooks" 2>/dev/null || true
    rmdir "$TARGET/$LEGACY_RUNTIME_ROOT" 2>/dev/null || true
    rmdir "$TARGET/tools" 2>/dev/null || true
    ok "legacy $LEGACY_RUNTIME_ROOT runtime migrated to $RUNTIME_ROOT (no compatibility wrappers)"
  fi
}

remove_retired_format_hook() {
  [[ "$MODE" == upgrade ]] || return 0
  local retired="$TARGET/$RUNTIME_ROOT/hooks/format_on_edit.sh"
  [[ -e "$retired" || -L "$retired" ]] || return 0
  rm -f -- "$retired"
  ok "retired managed format hook removed; project-owned hooks belong outside $RUNTIME_ROOT"
}
render_agents_template() {
  awk -v include_worktree="$WORKTREE_FLOW" '
    /<!-- agent-scaffold:worktree:start -->/ { if (!include_worktree) skip=1; next }
    /<!-- agent-scaffold:worktree:end -->/   { skip=0; next }
    !include_worktree && /<!-- agent-scaffold:worktree-only -->/ { next }
    !skip {
      gsub(/[[:space:]]*<!-- agent-scaffold:worktree-only -->[[:space:]]*/, "")
      print
    }
  ' "$TPL/AGENTS.root.md"
}

validate_agents_markers() {
  local agents="$TARGET/AGENTS.md"
  [[ -f "$agents" ]] || return 0
  if awk '
    {
      starts_here = gsub(/<!-- agent-scaffold:start/, "&")
      ends_here = gsub(/<!-- agent-scaffold:end/, "&")
      if (starts_here) {
        starts += starts_here
        if (active || ended || starts_here != 1 || ends_here) invalid=1
        active=1
      }
      if (ends_here) {
        ends += ends_here
        if (!active || ends_here != 1 || starts_here) invalid=1
        active=0
        ended=1
      }
    }
    END {
      if (starts == 0 && ends == 0) exit 0
      exit !(starts == 1 && ends == 1 && ended && !active && !invalid)
    }
  ' "$agents"; then
    return 0
  fi
  die "AGENTS.md has malformed agent-scaffold markers (expected exactly one ordered start/end pair); repair them manually before $MODE"
}

# ---- AGENTS.md (init writes template; retrofit injects the marked block) ----
ensure_agents_md() {
  local agents="$TARGET/AGENTS.md" block="$TMPDIR_H/block.md" rendered="$TMPDIR_H/AGENTS.root.md"
  validate_agents_markers
  render_agents_template > "$rendered"
  awk '/<!-- agent-scaffold:start/{f=1} f{print} /<!-- agent-scaffold:end/{f=0}' "$rendered" > "$block"
  if [[ ! -e "$agents" ]]; then
    cp "$rendered" "$agents"; ok "AGENTS.md created from template (fill the TODO sections)"
  elif grep -qF '<!-- agent-scaffold:start' "$agents"; then
    awk -v bf="$block" '
      BEGIN { while ((getline l < bf) > 0) blk = blk l "\n" }
      /<!-- agent-scaffold:start/ { printf "%s", blk; skip=1; next }
      skip && /<!-- agent-scaffold:end/ { skip=0; next }
      !skip { print }
    ' "$agents" > "$agents.tmp" && mv "$agents.tmp" "$agents"
    log "AGENTS.md harness block refreshed (project prose preserved)"
  else
    printf '\n' >> "$agents"; cat "$block" >> "$agents"
    ok "AGENTS.md exists — appended the harness block (review placement)"
  fi
}

ensure_claude_md_symlink() {
  run_python "$TPL/symlink-manager.py" ensure-contract --repo "$TARGET"
}

# ---- subagent wiring: pre-commit drift guard + (Node projects) package.json scripts ----
# The generator itself is python (needs no package.json). package.json scripts are a
# convenience added only when the project already has one; husky is npm-based, so its
# path is likewise gated on package.json. Everything else just advises the one line to wire.
GEN_CHECK='python .agents/tools/generate-subagents.py --check'
LEGACY_GEN_CHECK='python tools/agent/generate-subagents.py --check'
PKG_MERGE_PY='
import json, os, sys
p = os.environ["HARNESS_PKG"]
with open(p) as f:
    j = json.load(f)
j.setdefault("scripts", {})
changed = False
want = {
    "gen:subagents": "python .agents/tools/generate-subagents.py",
    "check:agents": "python .agents/tools/generate-subagents.py --check",
}
legacy = {
    "gen:subagents": "python tools/agent/generate-subagents.py",
    "check:agents": "python tools/agent/generate-subagents.py --check",
}
for k, v in want.items():
    if k not in j["scripts"] or j["scripts"].get(k) == legacy[k]:
        j["scripts"][k] = v
        changed = True
if os.environ.get("HARNESS_PREPARE") == "1" and "prepare" not in j["scripts"]:
    j["scripts"]["prepare"] = "husky"
    changed = True
if changed:
    with open(p, "w") as f:
        f.write(json.dumps(j, indent=2, ensure_ascii=False) + "\n")
sys.stdout.write("updated" if changed else "unchanged")
'

is_generated_agent_projection() {  # <path> <name>
  local path="$1" name="$2" marker legacy_marker first
  marker="Generated from .agents/subagents/$name; do not edit by hand. Run: python .agents/tools/generate-subagents.py"
  legacy_marker="Generated from .agents/subagents/$name; do not edit by hand. Run: python tools/agent/generate-subagents.py"
  case "$path" in
    *.toml)
      IFS= read -r first < "$path" || return 1
      first="${first%$'\r'}"
      [[ "$first" == "# $marker" || "$first" == "# $legacy_marker" ]]
      ;;
    *.md)
      awk -v marker="<!-- $marker -->" -v legacy_marker="<!-- $legacy_marker -->" '
        { sub(/\r$/, "", $0) }
        NR == 1 { if ($0 != "---") exit 1; next }
        $0 == "---" {
          if ((getline blank) <= 0) exit 1
          sub(/\r$/, "", blank)
          if (blank != "") exit 1
          if ((getline owner) <= 0) exit 1
          sub(/\r$/, "", owner)
          if (owner != marker && owner != legacy_marker) exit 1
          found=1
          exit
        }
        END { if (!found) exit 1 }
      ' "$path"
      ;;
    *) return 1 ;;
  esac
}

is_portable_subagent_name() {
  [[ "$1" =~ ^[a-z]+(-[a-z]+)*$ ]] || return 1
  case "$1" in con | prn | aux | nul) return 1 ;; esac
  return 0
}

wire_subagents() {
  local pkg="$TARGET/package.json"
  local hook="$TARGET/.husky/pre-commit" manager="" prepare=0
  remove_line "$hook" "$LEGACY_GEN_CHECK"
  # detect a pre-existing non-husky hook manager so we never bolt husky on beside it
  if [[ -f "$TARGET/lefthook.yml" || -f "$TARGET/lefthook.yaml" || -f "$TARGET/.lefthook.yml" ]]; then manager=lefthook
  elif [[ -f "$TARGET/.pre-commit-config.yaml" ]]; then manager=pre-commit
  elif [[ -f "$pkg" ]] && grep -qE '"(simple-git-hooks|yorkie)"' "$pkg" 2>/dev/null; then
    manager="$(grep -oE 'simple-git-hooks|yorkie' "$pkg" | head -1)"
  else
    local nat; nat="$(git -C "$TARGET" rev-parse --git-path hooks/pre-commit 2>/dev/null || true)"
    if [[ -n "$nat" && -f "$nat" ]]; then manager="existing git pre-commit hook"; fi
  fi

  if [[ -n "$manager" ]]; then
    warn "detected $manager — add '$GEN_CHECK' to your $manager config to guard subagent drift"
  elif [[ "$HUSKY" == 1 && -f "$pkg" ]]; then
    # husky path (npm-based, so it needs a package.json): create/extend .husky/pre-commit
    if [[ ! -f "$hook" ]]; then
      mkdir -p "$TARGET/.husky"
      cp "$TPL/husky.pre-commit" "$hook"
    else
      ensure_line "$hook" "$GEN_CHECK"
    fi
    chmod +x "$hook" 2>/dev/null || true
    prepare=1
    ok ".husky/pre-commit drift guard wired"
    [[ -d "$TARGET/node_modules/husky" ]] || warn "husky not installed yet — activate the hook with: npm install -D husky && npm run prepare"
  elif [[ "$HUSKY" == 1 ]]; then
    warn "no package.json → husky unavailable; add '$GEN_CHECK' to your pre-commit / CI to guard subagent drift"
  fi

  # package.json convenience scripts — only when the project actually has a package.json
  if [[ -f "$pkg" ]]; then
    if HARNESS_PKG="$pkg" HARNESS_PREPARE="$prepare" run_python -c "$PKG_MERGE_PY" >/dev/null; then
      log "package.json: ensured gen:subagents / check:agents scripts"
    else
      warn "could not update package.json scripts"
    fi
  fi
}

# ---- the install path (shared by init / retrofit / upgrade) ----------------
do_install() {
  # 1. contract convergence
  # A real CLAUDE.md must become a symlink while it is still byte-identical to
  # AGENTS.md. Only then may the managed block or any other target file change.
  local contract_linked=0
  if [[ ! -e "$TARGET/AGENTS.md" && -f "$TARGET/CLAUDE.md" && ! -L "$TARGET/CLAUDE.md" ]]; then
    cp "$TARGET/CLAUDE.md" "$TARGET/AGENTS.md"
    ok "CLAUDE.md prose adopted as AGENTS.md (SSOT); CLAUDE.md will become a symlink"
  fi
  if [[ -e "$TARGET/AGENTS.md" ]]; then
    ensure_claude_md_symlink
    contract_linked=1
  fi
  ensure_agents_md
  [[ "$contract_linked" == 1 ]] || ensure_claude_md_symlink

  # 2. vendored scripts
  migrate_legacy_runtime
  remove_retired_format_hook
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    copy_script "$TPL/worktree.sh"            "$TARGET/.agents/tools/worktree.sh"
    copy_script "$TPL/trunk_edit_guard.sh"    "$TARGET/.agents/tools/hooks/trunk_edit_guard.sh"
  else
    log "worktree flow disabled — lifecycle script and trunk guard are not installed or refreshed"
  fi
  copy_script "$TPL/authority_doc_budget.sh" "$TARGET/.agents/tools/hooks/authority_doc_budget.sh"
  copy_script "$TPL/hook-common.sh"         "$TARGET/.agents/tools/hooks/hook-common.sh"
  copy_script "$TPL/hook-paths.py"          "$TARGET/.agents/tools/hooks/hook-paths.py"
  copy_script "$TPL/relink-skills.sh"       "$TARGET/.agents/relink-skills.sh"
  copy_script "$TPL/symlink-manager.py"     "$TARGET/.agents/symlink-manager.py"
  log "selected vendored scripts in place under .agents/tools/ + .agents/"

  # 3. .agents/ SSOT scaffolding
  copy_if_missing "$TPL/agents-skills.README.md"    "$TARGET/.agents/skills/README.md"
  copy_if_missing "$TPL/agents-subagents.README.md" "$TARGET/.agents/subagents/README.md"
  replace_managed_text "$TARGET/.agents/subagents/README.md" \
    "python tools/agent/generate-subagents.py" "python .agents/tools/generate-subagents.py"
  touch "$TARGET/.agents/skills/.gitkeep"

  # 4. dual-host hook wiring (merge, never clobber)
  local cc_add="$TMPDIR_H/cc_add.json" cx_add="$TMPDIR_H/cx_add.json"
  prepare_hook_addition "$TPL/claude.settings.json" "$cc_add"
  prepare_hook_addition "$TPL/codex.hooks.json"     "$cx_add"
  write_hook_config "Claude Code" "$TARGET/.claude/settings.json" "$cc_add"
  write_hook_config "Codex"       "$TARGET/.codex/hooks.json"     "$cx_add"
  copy_if_missing "$TPL/codex.config.toml" "$TARGET/.codex/config.toml"

  # 5. ignore + attributes
  local gi="$TARGET/.gitignore"
  ensure_line "$gi" ".claude/settings.local.json"
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    ensure_line "$gi" ".worktrees/"
    ensure_line "$gi" ".claude/allow-trunk-edit"
  else
    log "worktree flow disabled — existing ignore entries, if any, are preserved as user-owned content"
  fi
  # keep the vendored scripts LF so they run under Windows/Git Bash (CRLF breaks bash)
  local ga="$TARGET/.gitattributes"
  remove_line "$ga" "tools/agent/*.sh text eol=lf"
  remove_line "$ga" "tools/agent/hooks/*.sh text eol=lf"
  remove_line "$ga" "tools/agent/*.py text eol=lf"
  remove_line "$ga" "tools/agent/hooks/*.py text eol=lf"
  ensure_line "$ga" ".agents/tools/*.sh text eol=lf"
  ensure_line "$ga" ".agents/tools/hooks/*.sh text eol=lf"
  ensure_line "$ga" ".agents/tools/*.py text eol=lf"
  ensure_line "$ga" ".agents/tools/hooks/*.py text eol=lf"
  ensure_line "$ga" ".agents/relink-skills.sh text eol=lf"
  ensure_line "$ga" ".agents/*.py text eol=lf"
  ensure_line "$ga" ".husky/pre-commit text eol=lf"

  # 6. example subagent (so the source → projection round-trip is demonstrable)
  if [[ "$EXAMPLE_SUBAGENT" == 1 ]]; then
    if find "$TARGET/.agents/subagents" -mindepth 1 -maxdepth 1 -type d ! -name '_*' 2>/dev/null | grep -q .; then
      log "subagents already exist — skipping example seed"
    else
      mkdir -p "$TARGET/.agents/subagents/code-reviewer"
      cp "$TPL/subagent.metadata.json"   "$TARGET/.agents/subagents/code-reviewer/metadata.json"
      cp "$TPL/subagent.instructions.md" "$TARGET/.agents/subagents/code-reviewer/instructions.md"
      ok "seeded example subagent .agents/subagents/code-reviewer (delete it once you add your own)"
    fi
  fi
  [[ "$EXAMPLE_SUBAGENT" == 1 ]] || touch "$TARGET/.agents/subagents/.gitkeep"

  # 7. relink skills (idempotent)
  bash "$TARGET/.agents/relink-skills.sh"

  # 8. subagent generator + drift guard (python is a harness prerequisite)
  copy_script "$TPL/generate-subagents.py" "$TARGET/.agents/tools/generate-subagents.py"
  wire_subagents
  # --import first: adopt any hand-authored .claude/agents/*.md or .codex/agents/*.toml
  # into the .agents/ SSOT (no-op when there are none), then project everything back.
  # Importing first also stops the projection step from pruning a hand-authored agent as a
  # sourceless "orphan"; any ownership or parse conflict propagates and aborts the install.
  run_python "$TARGET/.agents/tools/generate-subagents.py" --import

  # 9. closing notes
  echo
  ok "harness $MODE complete."
  log "Codex trust: project-level .codex/ only loads for a TRUSTED project. Trust once:"
  log "  run 'codex' in $TARGET and accept, or add to ~/.codex/config.toml:"
  log "    [projects.\"$TARGET\"]"
  log "    trust_level = \"trusted\""
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    log "next: fill the AGENTS.md TODO sections; start changes with bash .agents/tools/worktree.sh new <name>."
  else
    log "next: fill the AGENTS.md TODO sections; use the project's existing branch/change workflow."
  fi
}

# ---- plan (read-only preview of what init/retrofit would do) ---------------
do_plan() {
  local NEW="${c_green}+ create${c_off}" MRG="${c_yellow}~ merge${c_off}" \
        MIG="${c_blue}» migrate${c_off}" SKP="· present" MAN="${c_red}! needs you${c_off}"
  local legacy_runtime=0 legacy_installation=0
  has_legacy_runtime && legacy_runtime=1
  has_legacy_managed_installation && legacy_installation=1
  log "plan for $TARGET  (read-only — nothing is written)"
  printf '  legend: %s  %s  %s  %s  %s\n\n' "$NEW" "$MRG" "$MIG" "$MAN" "$SKP"

  local agents="$TARGET/AGENTS.md" cm="$TARGET/CLAUDE.md"
  echo "Contracts (AGENTS.md is the SSOT; CLAUDE.md a symlink to it):"
  if [[ ! -e "$agents" && -f "$cm" && ! -L "$cm" ]]; then
    printf '  %s AGENTS.md   adopt prose from your real CLAUDE.md, then append the harness block\n' "$MIG"
    printf '  %s CLAUDE.md   real file retired → symlink to AGENTS.md (prose preserved in AGENTS.md)\n' "$MIG"
  else
    if [[ ! -e "$agents" ]]; then
      printf '  %s AGENTS.md   from template (fill the TODO sections)\n' "$NEW"
    elif grep -qF '<!-- agent-scaffold:start' "$agents" 2>/dev/null; then
      printf '  %s AGENTS.md   refresh only the agent-scaffold block; your prose untouched\n' "$MRG"
    else
      printf '  %s AGENTS.md   append the harness block (review placement)\n' "$MRG"
    fi
    if [[ -L "$cm" ]]; then
      if [[ "$(readlink "$cm")" == "AGENTS.md" ]]; then printf '  %s CLAUDE.md   already a symlink to AGENTS.md\n' "$SKP"
      else printf '  %s CLAUDE.md   symlink points at %s, not AGENTS.md\n' "$MAN" "$(readlink "$cm")"; fi
    elif [[ -e "$cm" ]]; then
      printf '  %s CLAUDE.md   real file beside a real AGENTS.md — merge by hand, then symlink\n' "$MAN"
    else
      printf '  %s CLAUDE.md   symlink → AGENTS.md\n' "$NEW"
    fi
  fi
  echo

  echo "Harness runtime:"
  if [[ "$legacy_runtime" == 1 ]]; then
    printf '  %s %s → %s; remove only known managed files and prune empty legacy directories\n' \
      "$MIG" "$LEGACY_RUNTIME_ROOT" "$RUNTIME_ROOT"
    printf '  %s details are loaded on demand from references/harness-migration.md\n' "$SKP"
  elif [[ "$legacy_installation" == 1 ]]; then
    printf '  %s stale managed commands or documentation → %s identities\n' "$MIG" "$RUNTIME_ROOT"
    printf '  %s details are loaded on demand from references/harness-migration.md\n' "$SKP"
  elif [[ -d "$TARGET/$RUNTIME_ROOT" ]]; then
    printf '  %s %s\n' "$SKP" "$RUNTIME_ROOT"
  else
    printf '  %s %s\n' "$NEW" "$RUNTIME_ROOT"
  fi
  echo

  echo "Worktree workflow:"
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    printf '  %s install/refresh worktree.sh, wire the trunk guard, and publish the managed hard rule\n' "$MRG"
  else
    printf '  %s disabled by --no-worktree; do not add lifecycle/guard/ignore config or the managed policy\n' "$SKP"
  fi
  echo

  echo "Hook wiring (merged into existing config, never clobbered):"
  local cfg label
  for pair in ".claude/settings.json:Claude Code" ".codex/hooks.json:Codex"; do
    cfg="${pair%%:*}"; label="${pair##*:}"
    if [[ -f "$TARGET/$cfg" ]]; then printf '  %s %s   merge our hooks into existing %s\n' "$MRG" "$label" "$cfg"
    else printf '  %s %s   %s\n' "$NEW" "$label" "$cfg"; fi
  done
  echo

  echo "Subagents:"
  local any=0 af base filename lower expected_ext agent_dir seen_file="$TMPDIR_H/seen-subagents"
  : > "$seen_file"
  for agent_dir in "$TARGET/.claude/agents" "$TARGET/.codex/agents"; do
    if [[ ! -d "$agent_dir" ]] && [[ -e "$agent_dir" || -L "$agent_dir" ]]; then
      printf '  %s %s: expected a directory\n' "$MAN" "${agent_dir#"$TARGET"/}"
      any=1
    fi
  done
  for af in \
    "$TARGET/.claude/agents"/* \
    "$TARGET/.claude/agents"/.[!.]* \
    "$TARGET/.claude/agents"/..?* \
    "$TARGET/.codex/agents"/* \
    "$TARGET/.codex/agents"/.[!.]* \
    "$TARGET/.codex/agents"/..?*; do
    [[ -e "$af" || -L "$af" ]] || continue
    filename="$(basename "$af")"
    case "$af" in
      "$TARGET/.claude/agents/"*) expected_ext=.md ;;
      *) expected_ext=.toml ;;
    esac
    lower="$(printf '%s' "$filename" | tr '[:upper:]' '[:lower:]')"
    case "$filename" in
      *"$expected_ext") ;;
      *)
        case "$lower" in
          *"$expected_ext")
            base="${filename%.*}"
            printf '%s\n' "$base" >> "$seen_file"; any=1
            printf '  %s %s: host agent extension must be lowercase %s\n' "$MAN" "${af#"$TARGET"/}" "$expected_ext"
            ;;
        esac
        continue
        ;;
    esac
    if [[ ! -f "$af" ]]; then
      printf '  %s %s: expected a regular file\n' "$MAN" "${af#"$TARGET"/}"
      any=1
      continue
    fi
    base="${filename%.*}"
    if grep -qxF "$base" "$seen_file" 2>/dev/null; then continue; fi
    if ! is_portable_subagent_name "$base"; then
      printf '%s\n' "$base" >> "$seen_file"; any=1
      printf '  %s subagent non-portable host filename %s — use lowercase letter groups separated by hyphens\n' "$MAN" "$filename"
      continue
    fi
    if is_generated_agent_projection "$af" "$base"; then continue; fi
    printf '%s\n' "$base" >> "$seen_file"; any=1
    if [[ -d "$TARGET/.agents/subagents/$base" ]]; then
      printf '  %s subagent %s hand-authored projection conflicts with existing .agents/subagents/%s — resolve it before retrofit\n' "$MAN" "$base" "$base"
    else
      printf '  %s subagent %s → adopt hand-authored agent into .agents/subagents/%s\n' "$MIG" "$base" "$base"
    fi
  done
  if [[ "$any" == 0 ]]; then
    printf '  %s no hand-authored subagents to adopt; generator projects .agents/subagents/\n' "$SKP"
  fi
  echo

  echo "Skills:"
  local nss=0
  if [[ -d "$TARGET/.agents/skills" ]]; then
    nss="$(find "$TARGET/.agents/skills" -mindepth 1 -maxdepth 1 -type d ! -name '_*' | wc -l | tr -d ' ')"
  fi
  printf '  %s %s project skill(s) under .agents/skills → (re)symlinked into .claude/skills\n' "$MRG" "$nss"
  if [[ -d "$TARGET/.claude/skills" ]]; then
    local d name
    for d in "$TARGET/.claude/skills"/*/; do
      [[ -d "$d" ]] || continue
      name="$(basename "$d")"
      if [[ -L "${d%/}" ]]; then continue; fi
      printf '  %s .claude/skills/%s is a real dir (npx/vendor) — left as-is; if project-owned, move it to .agents/skills/%s\n' "$SKP" "$name" "$name"
    done
  fi
  echo

  local apply_mode=retrofit
  [[ "$legacy_installation" == 1 ]] && apply_mode=upgrade
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    log "to apply: bash <skill-dir>/harness-init.sh $apply_mode"
  else
    log "to apply: bash <skill-dir>/harness-init.sh $apply_mode --no-worktree"
  fi
  log "Codex trust: project-level .codex/ loads only for a TRUSTED project (references/host-integration.md)."
}

# ---- verify (read-only) ----------------------------------------------------
do_verify() {
  local fails=0 pass="  ${c_green}✓${c_off}" fail="  ${c_red}✗${c_off}"
  log "verifying harness in $TARGET"

  local required=".agents/tools/hooks/authority_doc_budget.sh \
           .agents/tools/hooks/hook-common.sh .agents/tools/hooks/hook-paths.py \
           .agents/relink-skills.sh .agents/symlink-manager.py"
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    required=".agents/tools/worktree.sh .agents/tools/hooks/trunk_edit_guard.sh $required"
  fi
  local f
  for f in $required; do
    if [[ -f "$TARGET/$f" ]]; then printf '%s %s\n' "$pass" "$f"; else printf '%s %s (missing)\n' "$fail" "$f"; fails=$((fails+1)); fi
  done

  local pair rel legacy
  while IFS= read -r pair; do
    rel="${pair##*:}"
    legacy="$TARGET/$LEGACY_RUNTIME_ROOT/$rel"
    if [[ -e "$legacy" || -L "$legacy" ]]; then
      printf '%s legacy managed runtime remains: %s/%s\n' "$fail" "$LEGACY_RUNTIME_ROOT" "$rel"
      fails=$((fails+1))
    fi
  done < <(runtime_pairs)

  local retired_format="$TARGET/$RUNTIME_ROOT/hooks/format_on_edit.sh"
  if [[ -e "$retired_format" || -L "$retired_format" ]]; then
    printf '%s retired managed runtime remains: %s/hooks/format_on_edit.sh\n' "$fail" "$RUNTIME_ROOT"
    fails=$((fails+1))
  else
    printf '%s retired managed format hook is absent\n' "$pass"
  fi

  local cc_expected="$TMPDIR_H/verify-cc-add.json" cx_expected="$TMPDIR_H/verify-cx-add.json"
  prepare_hook_addition "$TPL/claude.settings.json" "$cc_expected"
  prepare_hook_addition "$TPL/codex.hooks.json"     "$cx_expected"
  local host cfg label expected
  for host in claude codex; do
    if [[ "$host" == claude ]]; then
      cfg=".claude/settings.json"; label="Claude Code"
      expected="$cc_expected"
    else
      cfg=".codex/hooks.json"; label="Codex"
      expected="$cx_expected"
    fi
    if [[ -f "$TARGET/$cfg" ]]; then
      if verify_hook_config "$TARGET/$cfg" "$expected"; then
        printf '%s %s wiring matches the selected profile\n' "$pass" "$label"
      else
        printf '%s %s wiring does not match the selected profile (%s)\n' "$fail" "$label" "$cfg"
        fails=$((fails+1))
      fi
    else
      printf '%s %s config missing (%s)\n' "$fail" "$label" "$cfg"; fails=$((fails+1))
    fi
  done

  if [[ -L "$TARGET/CLAUDE.md" && "$(readlink "$TARGET/CLAUDE.md")" == "AGENTS.md" ]]; then
    printf '%s CLAUDE.md → AGENTS.md symlink\n' "$pass"
  else
    printf '%s CLAUDE.md is not a symlink to AGENTS.md\n' "$fail"; fails=$((fails+1))
  fi

  if run_python "$TPL/symlink-manager.py" verify --repo "$TARGET" >/dev/null; then
    printf '%s real symlink projections and tracked git modes are valid\n' "$pass"
  else
    printf '%s real symlink projection verification failed\n' "$fail"; fails=$((fails+1))
  fi

  if [[ -f "$TARGET/AGENTS.md" ]] && grep -qF '<!-- agent-scaffold:start' "$TARGET/AGENTS.md"; then
    printf '%s AGENTS.md carries the harness block\n' "$pass"
  else
    printf '%s AGENTS.md missing the harness block\n' "$fail"; fails=$((fails+1))
  fi
  local managed_block="$TMPDIR_H/verify-managed-block.md"
  awk '/<!-- agent-scaffold:start/{f=1} f{print} /<!-- agent-scaffold:end/{f=0}' "$TARGET/AGENTS.md" > "$managed_block" 2>/dev/null || true
  if [[ "$WORKTREE_FLOW" == 1 ]]; then
    if grep -qF '### Worktree-per-change (hard rule)' "$managed_block"; then
      printf '%s AGENTS.md publishes the worktree policy\n' "$pass"
    else
      printf '%s AGENTS.md worktree policy missing\n' "$fail"; fails=$((fails+1))
    fi
  elif grep -qF '### Worktree-per-change (hard rule)' "$managed_block"; then
    printf '%s AGENTS.md still publishes the worktree policy under --no-worktree\n' "$fail"; fails=$((fails+1))
  else
    printf '%s AGENTS.md omits the optional worktree policy\n' "$pass"
  fi

  # script drift vs the skill's vendored templates
  local drift=0
  for pair in "worktree.sh:.agents/tools/worktree.sh" \
              "trunk_edit_guard.sh:.agents/tools/hooks/trunk_edit_guard.sh" \
              "authority_doc_budget.sh:.agents/tools/hooks/authority_doc_budget.sh" \
              "hook-common.sh:.agents/tools/hooks/hook-common.sh" \
              "hook-paths.py:.agents/tools/hooks/hook-paths.py" \
              "relink-skills.sh:.agents/relink-skills.sh" \
              "symlink-manager.py:.agents/symlink-manager.py" \
              "generate-subagents.py:.agents/tools/generate-subagents.py"; do
    local t="${pair%%:*}" inst="$TARGET/${pair##*:}"
    case "$t" in
      worktree.sh|trunk_edit_guard.sh) [[ "$WORKTREE_FLOW" == 1 ]] || continue ;;
    esac
    [[ -f "$inst" ]] && ! cmp -s "$TPL/$t" "$inst" && { printf '%s drift: %s differs from the skill template\n' "$fail" "${pair##*:}"; drift=$((drift+1)); }
  done
  if [[ "$drift" == 0 ]]; then
    printf '%s active-profile scripts match the skill templates\n' "$pass"
  else
    printf '%s %d active-profile script(s) drifted — run: agent-scaffold upgrade\n' "$fail" "$drift"
    fails=$((fails + drift))
  fi

  if [[ -f "$TARGET/.agents/tools/generate-subagents.py" ]]; then
    if run_python "$TARGET/.agents/tools/generate-subagents.py" --check >/dev/null 2>&1; then
      printf '%s subagent projections in sync\n' "$pass"
    else
      printf '%s subagent projections drifted — run: python .agents/tools/generate-subagents.py\n' "$fail"; fails=$((fails+1))
    fi
  else
    printf '%s subagent generator missing\n' "$fail"; fails=$((fails+1))
  fi

  if [[ -f "$TARGET/.husky/pre-commit" ]] \
    && [[ "$(tr '\r' '\n' < "$TARGET/.husky/pre-commit" | grep -cxF "$LEGACY_GEN_CHECK" || true)" -gt 0 ]]; then
    printf '%s legacy Husky subagent check remains\n' "$fail"; fails=$((fails+1))
  fi
  if [[ -f "$TARGET/package.json" ]] && ! HARNESS_PKG="$TARGET/package.json" run_python -c '
import json, os
with open(os.environ["HARNESS_PKG"], encoding="utf-8") as source:
    scripts = (json.load(source).get("scripts") or {})
legacy = {
    "gen:subagents": "python tools/agent/generate-subagents.py",
    "check:agents": "python tools/agent/generate-subagents.py --check",
}
raise SystemExit(1 if any(scripts.get(key) == value for key, value in legacy.items()) else 0)
'; then
    printf '%s legacy package.json subagent command remains\n' "$fail"; fails=$((fails+1))
  fi
  if legacy_managed_docs_present; then
    printf '%s legacy managed harness documentation remains\n' "$fail"; fails=$((fails+1))
  fi
  local legacy_attribute
  for legacy_attribute in \
    "tools/agent/*.sh text eol=lf" \
    "tools/agent/hooks/*.sh text eol=lf" \
    "tools/agent/*.py text eol=lf" \
    "tools/agent/hooks/*.py text eol=lf"; do
    if [[ -f "$TARGET/.gitattributes" ]] \
      && [[ "$(tr '\r' '\n' < "$TARGET/.gitattributes" | grep -cxF "$legacy_attribute" || true)" -gt 0 ]]; then
      printf '%s legacy .gitattributes rule remains: %s\n' "$fail" "$legacy_attribute"
      fails=$((fails+1))
    fi
  done

  echo
  if [[ "$fails" == 0 ]]; then ok "verify: harness OK"; else warn "verify: $fails check(s) failed"; exit 1; fi
}

case "$MODE" in
  init|retrofit|upgrade)
    # Contract and capability preflights are deliberately before the first target write.
    validate_runtime_layout
    validate_agents_markers
    validate_existing_hook_configs
    run_python "$TPL/symlink-manager.py" preflight-install --repo "$TARGET" >/dev/null
    env AGENT_SCAFFOLD_PREFLIGHT_REPO="$TARGET" PYTHONUTF8=1 "${PYTHON_CMD[@]}" \
      "$TPL/generate-subagents.py" --preflight-import >/dev/null
    run_python "$TPL/symlink-manager.py" doctor --repo "$TARGET" >/dev/null
    do_install
    ;;
  plan) validate_agents_markers; do_plan ;;
  doctor) run_python "$TPL/symlink-manager.py" doctor --repo "$TARGET" ;;
  verify) validate_agents_markers; do_verify ;;
esac
