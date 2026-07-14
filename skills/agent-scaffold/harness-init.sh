#!/usr/bin/env bash
# harness-init.sh — install or retrofit the dual-host (Claude Code + Codex) agent
# harness into a project. Idempotent and merge-aware: it never clobbers existing
# config, and re-running it changes nothing.
#
# Usage:
#   bash harness-init.sh <init|retrofit|plan|verify|upgrade> [flags]
#
# Modes:
#   init       greenfield — lay down the full harness (seeds an example subagent)
#   retrofit   merge into a project that already has some .claude/.codex/AGENTS.md
#   plan       read-only — preview what init/retrofit would create/merge/migrate
#   verify     read-only — report harness presence / drift / parity
#   upgrade    retrofit + re-copy the vendored scripts over the installed ones
#
# Flags:
#   --no-format-hook        do not wire format_on_edit.sh (still copied; does not unwire an existing one)
#   --no-husky              do not set up the .husky/pre-commit drift guard
#   --no-example-subagent   do not seed the example code-reviewer subagent (init)
#   --example-subagent      seed it even on retrofit/upgrade
#   --force-scripts         overwrite already-installed vendored scripts (implied by upgrade)
#   -h, --help              this help
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
case "$MODE" in init|retrofit|plan|verify|upgrade) ;; -h|--help) usage 0 ;; *) die "unknown mode: $MODE (init|retrofit|plan|verify|upgrade)";; esac

FORMAT_HOOK=1; HUSKY=1; FORCE_SCRIPTS=0
EXAMPLE_SUBAGENT="auto"   # auto → on for init, off otherwise
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-format-hook) FORMAT_HOOK=0 ;;
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
if [[ "$EXAMPLE_SUBAGENT" == auto ]]; then
  [[ "$MODE" == init ]] && EXAMPLE_SUBAGENT=1 || EXAMPLE_SUBAGENT=0
fi

# ---- resolve target repo ---------------------------------------------------
TARGET="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository — run from within the target project"
log "target repo: $TARGET   mode: $MODE"

TMPDIR_H="$(mktemp -d)"; trap 'rm -rf "$TMPDIR_H"' EXIT

# ---- json merge (jq → python → paste-block) -------------------------------
# shellcheck disable=SC2016  # $a/$b/$g/$h below are jq variables, not shell expansions
JQ_PROG='
def unionByCommand($a; $b):
  reduce $b[] as $h ($a; if (map(.command) | index($h.command)) then . else . + [$h] end);
def mergeEvent($cur; $add):
  reduce $add[] as $g ($cur;
    (map(.matcher == $g.matcher) | index(true)) as $i
    | if $i == null then . + [$g]
      else .[$i].hooks = unionByCommand((.[$i].hooks // []); ($g.hooks // []))
      end);
($add[0]) as $a
| (. // {})
| .hooks = (.hooks // {})
| .hooks.PreToolUse  = mergeEvent((.hooks.PreToolUse  // []); ($a.hooks.PreToolUse  // []))
| .hooks.PostToolUse = mergeEvent((.hooks.PostToolUse // []); ($a.hooks.PostToolUse // []))
'

PY_MERGE='
import json, os
ex = os.environ.get("HARNESS_EXISTING") or ""
existing = json.load(open(ex)) if ex and os.path.exists(ex) else {}
add = json.load(open(os.environ["HARNESS_ADD"]))
# Coerce a null/non-object "hooks" to {} — mirrors the jq path .hooks = (.hooks // {}).
# Without this, an existing {"hooks": null} crashes the merge (None.get) while jq copes.
if not isinstance(existing.get("hooks"), dict):
    existing["hooks"] = {}
def union(a, b):
    out = list(a or [])
    seen = {h.get("command") for h in out}
    for h in b or []:
        if h.get("command") not in seen:
            out.append(h)
            seen.add(h.get("command"))
    return out
def merge_event(cur, add_arr):
    cur = cur or []
    for g in add_arr:
        i = next((k for k, x in enumerate(cur) if x.get("matcher") == g.get("matcher")), -1)
        if i < 0:
            cur.append(g)
        else:
            cur[i]["hooks"] = union(cur[i].get("hooks"), g.get("hooks"))
    return cur
for ev in ("PreToolUse", "PostToolUse"):
    if add["hooks"].get(ev):
        existing["hooks"][ev] = merge_event(existing["hooks"].get(ev), add["hooks"][ev])
with open(os.environ["HARNESS_OUT"], "w") as f:
    f.write(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")
'

# merge_hooks <existing-or-empty> <addition-file> <out>  → 0 merged, 1 needs paste
merge_hooks() {
  local existing="$1" add="$2" out="$3"
  if [[ ! -f "$existing" ]]; then cp "$add" "$out"; return 0; fi
  # HARNESS_NO_JQ forces the python path (lets the e2e test prove both paths agree).
  if [[ -z "${HARNESS_NO_JQ:-}" ]] && command -v jq >/dev/null 2>&1; then
    jq --slurpfile add "$add" "$JQ_PROG" "$existing" > "$out" && return 0
  fi
  if command -v python >/dev/null 2>&1; then
    HARNESS_EXISTING="$existing" HARNESS_ADD="$add" HARNESS_OUT="$out" python -c "$PY_MERGE" && return 0
  fi
  return 1
}

# strip the format_on_edit hook from a settings/hooks addition file (when --no-format-hook)
strip_format_hook() {
  local src="$1" out="$2"
  if command -v jq >/dev/null 2>&1; then
    jq '(.hooks.PostToolUse[]?.hooks) |= map(select((.command // "") | test("format_on_edit") | not))' "$src" > "$out" && return 0
  fi
  # no jq: cannot filter; wire it anyway (the hook self-skips at runtime without a formatter)
  cp "$src" "$out"; warn "no jq to filter format_on_edit out — wiring it anyway (it self-skips when no formatter is configured)"
}

write_hook_config() {  # <host-label> <existing-file> <addition-file>
  local label="$1" existing="$2" add="$3" out="$TMPDIR_H/merged.json"
  if merge_hooks "$existing" "$add" "$out"; then
    if [[ -f "$existing" ]] && cmp -s "$existing" "$out"; then
      log "$label hooks already wired (no change)"
    else
      mkdir -p "$(dirname "$existing")"; mv "$out" "$existing"; ok "$label hooks wired → ${existing#"$TARGET"/}"
    fi
  else
    warn "$label: no jq or python to merge JSON safely. Add this block to ${existing#"$TARGET"/} by hand:"
    sed 's/^/    /' "$add" >&2
    HARNESS_MERGE_DEFERRED=1
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
  local file="$1" line="$2"
  mkdir -p "$(dirname "$file")"; touch "$file"
  grep -qxF "$line" "$file" 2>/dev/null || printf '%s\n' "$line" >> "$file"
}

# ---- AGENTS.md (init writes template; retrofit injects the marked block) ----
ensure_agents_md() {
  local migrated="${1:-0}"
  local agents="$TARGET/AGENTS.md" cm="$TARGET/CLAUDE.md" block="$TMPDIR_H/block.md"
  awk '/<!-- agent-scaffold:start/{f=1} f{print} /<!-- agent-scaffold:end/{f=0}' "$TPL/AGENTS.root.md" > "$block"
  # Retrofit a project whose contract already lives in a REAL CLAUDE.md (no AGENTS.md
  # yet): adopt that prose as the AGENTS.md SSOT; CLAUDE.md becomes a symlink below.
  if [[ "$migrated" == 1 && ! -e "$agents" ]]; then
    cp "$cm" "$agents"
    ok "CLAUDE.md prose adopted as AGENTS.md (SSOT); CLAUDE.md will become a symlink"
  fi
  if [[ ! -e "$agents" ]]; then
    cp "$TPL/AGENTS.root.md" "$agents"; ok "AGENTS.md created from template (fill the TODO sections)"
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

# Windows/Git Bash without symlink support makes `ln -s` SILENTLY COPY instead of
# link; this is the one-line fix we point users at.
SYMLINK_HELP='Windows/Git Bash copied instead of linking — enable real symlinks with: git config core.symlinks true; export MSYS=winsymlinks:nativestrict; + Developer Mode (or admin), then re-run.'

# make_symlink <target> <linkname> — create the link inside $TARGET. Returns 0 only
# when a REAL symlink results; on the Git-Bash copy case it removes the bogus copy
# and returns 1 so the caller can fall back + warn.
make_symlink() {
  ( cd "$TARGET" && ln -s "$1" "$2" ) 2>/dev/null || true
  [[ -L "$TARGET/$2" ]] && return 0
  [[ -e "$TARGET/$2" && ! -L "$TARGET/$2" ]] && rm -rf "${TARGET:?}/$2"
  return 1
}

ensure_claude_md_symlink() {
  local migrated="${1:-0}"
  local cm="$TARGET/CLAUDE.md" agents="$TARGET/AGENTS.md"
  if [[ -L "$cm" ]]; then
    [[ "$(readlink "$cm")" == "AGENTS.md" ]] || warn "CLAUDE.md symlink points at $(readlink "$cm"), not AGENTS.md"
    return 0
  fi
  # Decide whether an existing real CLAUDE.md is safe to retire for the symlink:
  #   - nothing there yet, or
  #   - just-migrated prose (already copied into AGENTS.md), or
  #   - a prior copy-fallback still byte-identical to AGENTS.md (idempotent re-run).
  local retire=0
  if [[ ! -e "$cm" ]]; then retire=1
  elif [[ -f "$cm" && "$migrated" == 1 ]]; then retire=1
  elif [[ -f "$cm" && -f "$agents" ]] && cmp -s "$cm" "$agents"; then retire=1
  fi
  if [[ "$retire" != 1 ]]; then
    warn "CLAUDE.md and AGENTS.md are both real files — merge CLAUDE.md into AGENTS.md, then: ln -sf AGENTS.md CLAUDE.md"
    return 0
  fi
  rm -f "$cm"
  if make_symlink AGENTS.md CLAUDE.md; then
    ok "CLAUDE.md → AGENTS.md symlink created"
  else
    cp "$agents" "$cm"
    warn "CLAUDE.md → AGENTS.md: $SYMLINK_HELP Left a drift-prone COPY for now."
  fi
}

# ---- subagent wiring: pre-commit drift guard + (Node projects) package.json scripts ----
# The generator itself is python (needs no package.json). package.json scripts are a
# convenience added only when the project already has one; husky is npm-based, so its
# path is likewise gated on package.json. Everything else just advises the one line to wire.
GEN_CHECK='python tools/agent/generate-subagents.py --check'
PKG_MERGE_PY='
import json, os, sys
p = os.environ["HARNESS_PKG"]
with open(p) as f:
    j = json.load(f)
j.setdefault("scripts", {})
changed = False
want = {
    "gen:subagents": "python tools/agent/generate-subagents.py",
    "check:agents": "python tools/agent/generate-subagents.py --check",
}
for k, v in want.items():
    if k not in j["scripts"]:
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

wire_subagents() {
  local pkg="$TARGET/package.json"
  local manager="" prepare=0
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
    local hook="$TARGET/.husky/pre-commit"
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
    if HARNESS_PKG="$pkg" HARNESS_PREPARE="$prepare" python -c "$PKG_MERGE_PY" >/dev/null; then
      log "package.json: ensured gen:subagents / check:agents scripts"
    else
      warn "could not update package.json scripts"
    fi
  fi
}

# ---- the install path (shared by init / retrofit / upgrade) ----------------
do_install() {
  # 1. vendored scripts
  copy_script "$TPL/worktree.sh"            "$TARGET/tools/agent/worktree.sh"
  copy_script "$TPL/trunk_edit_guard.sh"    "$TARGET/tools/agent/hooks/trunk_edit_guard.sh"
  copy_script "$TPL/authority_doc_budget.sh" "$TARGET/tools/agent/hooks/authority_doc_budget.sh"
  copy_script "$TPL/format_on_edit.sh"      "$TARGET/tools/agent/hooks/format_on_edit.sh"
  copy_script "$TPL/relink-skills.sh"       "$TARGET/.agents/relink-skills.sh"
  log "vendored scripts in place under tools/agent/ + .agents/"

  # 2. .agents/ SSOT scaffolding
  copy_if_missing "$TPL/agents-skills.README.md"    "$TARGET/.agents/skills/README.md"
  copy_if_missing "$TPL/agents-subagents.README.md" "$TARGET/.agents/subagents/README.md"
  touch "$TARGET/.agents/skills/.gitkeep"

  # 3. dual-host hook wiring (merge, never clobber)
  local cc_add="$TPL/claude.settings.json" cx_add="$TPL/codex.hooks.json"
  if [[ "$FORMAT_HOOK" != 1 ]]; then
    strip_format_hook "$TPL/claude.settings.json" "$TMPDIR_H/cc_add.json"; cc_add="$TMPDIR_H/cc_add.json"
    strip_format_hook "$TPL/codex.hooks.json"     "$TMPDIR_H/cx_add.json"; cx_add="$TMPDIR_H/cx_add.json"
  fi
  write_hook_config "Claude Code" "$TARGET/.claude/settings.json" "$cc_add"
  write_hook_config "Codex"       "$TARGET/.codex/hooks.json"     "$cx_add"
  copy_if_missing "$TPL/codex.config.toml" "$TARGET/.codex/config.toml"

  # 4. contracts + ignore
  # CLAUDE.md -> AGENTS.md adoption: decide once here, pass to both steps (no shared global).
  local migrated=0
  if [[ ! -e "$TARGET/AGENTS.md" && -f "$TARGET/CLAUDE.md" && ! -L "$TARGET/CLAUDE.md" ]]; then migrated=1; fi
  ensure_agents_md "$migrated"
  ensure_claude_md_symlink "$migrated"
  local gi="$TARGET/.gitignore"
  ensure_line "$gi" ".worktrees/"
  ensure_line "$gi" ".claude/settings.local.json"
  ensure_line "$gi" ".claude/allow-trunk-edit"
  # keep the vendored scripts LF so they run under Windows/Git Bash (CRLF breaks bash)
  local ga="$TARGET/.gitattributes"
  ensure_line "$ga" "tools/agent/*.sh text eol=lf"
  ensure_line "$ga" "tools/agent/hooks/*.sh text eol=lf"
  ensure_line "$ga" "tools/agent/*.py text eol=lf"
  ensure_line "$ga" ".agents/relink-skills.sh text eol=lf"

  # 5. example subagent (so the source → projection round-trip is demonstrable)
  if [[ "$EXAMPLE_SUBAGENT" == 1 ]]; then
    if find "$TARGET/.agents/subagents" -mindepth 1 -maxdepth 1 -type d ! -name '_*' 2>/dev/null | grep -q .; then
      log "subagents already exist — skipping example seed"
    else
      mkdir -p "$TARGET/.agents/subagents/code-reviewer"
      cp "$TPL/subagent.metadata.json"   "$TARGET/.agents/subagents/code-reviewer/metadata.json"
      cp "$TPL/subagent.instructions.md" "$TARGET/.agents/subagents/code-reviewer/instructions.md"
      ok "seeded example subagent .agents/subagents/code-reviewer (delete it once you add your own)"
      command -v python >/dev/null 2>&1 || log "  (install python, then run upgrade to project it into .claude/ + .codex/)"
    fi
  fi
  [[ "$EXAMPLE_SUBAGENT" == 1 ]] || touch "$TARGET/.agents/subagents/.gitkeep"

  # 6. relink skills (idempotent)
  bash "$TARGET/.agents/relink-skills.sh" || warn "relink-skills.sh returned nonzero"

  # 7. python-gated: subagent generator + drift guard
  if command -v python >/dev/null 2>&1; then
    copy_script "$TPL/generate-subagents.py" "$TARGET/tools/agent/generate-subagents.py"
    wire_subagents
    # --import first: adopt any hand-authored .claude/agents/*.md or .codex/agents/*.toml
    # into the .agents/ SSOT (no-op when there are none / a source already exists), then it
    # projects everything back. Importing first also stops the projection step from pruning a
    # hand-authored agent as a sourceless "orphan".
    python "$TARGET/tools/agent/generate-subagents.py" --import || warn "generate-subagents.py --import returned nonzero"
  else
    log "no python → skipping subagent generator + drift guard (rest of the bash harness is installed)."
    log "  to enable subagents later: install python, then re-run 'agent-scaffold upgrade'."
    if find "$TARGET/.claude/agents" "$TARGET/.codex/agents" -maxdepth 1 -type f 2>/dev/null | grep -q .; then
      warn "hand-authored .claude/agents or .codex/agents found but python is unavailable — cannot adopt them into .agents/ SSOT. Install python, then: agent-scaffold upgrade"
    fi
  fi

  # 8. closing notes
  echo
  ok "harness $MODE complete."
  log "Codex trust: project-level .codex/ only loads for a TRUSTED project. Trust once:"
  log "  run 'codex' in $TARGET and accept, or add to ~/.codex/config.toml:"
  log "    [projects.\"$TARGET\"]"
  log "    trust_level = \"trusted\""
  [[ "${HARNESS_MERGE_DEFERRED:-0}" == 1 ]] && warn "one or more hook configs need a manual merge (see above)."
  log "next: fill the AGENTS.md TODO sections; start changes with tools/agent/worktree.sh new <name>."
}

# ---- plan (read-only preview of what init/retrofit would do) ---------------
do_plan() {
  local NEW="${c_green}+ create${c_off}" MRG="${c_yellow}~ merge${c_off}" \
        MIG="${c_blue}» migrate${c_off}" SKP="· present" MAN="${c_red}! needs you${c_off}"
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

  echo "Hook wiring (merged into existing config, never clobbered):"
  local cfg label
  for pair in ".claude/settings.json:Claude Code" ".codex/hooks.json:Codex"; do
    cfg="${pair%%:*}"; label="${pair##*:}"
    if [[ -f "$TARGET/$cfg" ]]; then printf '  %s %s   merge our hooks into existing %s\n' "$MRG" "$label" "$cfg"
    else printf '  %s %s   %s\n' "$NEW" "$label" "$cfg"; fi
  done
  echo

  echo "Subagents:"
  if command -v python >/dev/null 2>&1; then
    local -A seen=(); local any=0 af base
    for af in "$TARGET/.claude/agents"/*.md "$TARGET/.codex/agents"/*.toml; do
      [[ -e "$af" ]] || continue
      base="$(basename "$af")"; base="${base%.*}"
      if [[ -n "${seen[$base]:-}" ]]; then continue; fi
      if [[ -d "$TARGET/.agents/subagents/$base" ]]; then continue; fi
      if grep -qF 'Generated from .agents/subagents/' "$af" 2>/dev/null; then continue; fi
      seen[$base]=1; any=1
      printf '  %s subagent %s → adopt hand-authored agent into .agents/subagents/%s\n' "$MIG" "$base" "$base"
    done
    if [[ "$any" == 0 ]]; then
      printf '  %s no hand-authored subagents to adopt; generator projects .agents/subagents/\n' "$SKP"
    fi
  elif find "$TARGET/.claude/agents" "$TARGET/.codex/agents" -maxdepth 1 -type f 2>/dev/null | grep -q .; then
    printf '  %s hand-authored subagents found, but python is unavailable — install python to adopt them\n' "$MAN"
  else
    printf '  %s python unavailable — subagent generator skipped\n' "$SKP"
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

  log "to apply: bash <skill-dir>/harness-init.sh retrofit"
  log "Codex trust: project-level .codex/ loads only for a TRUSTED project (reference.md §7)."
}

# ---- verify (read-only) ----------------------------------------------------
do_verify() {
  local fails=0 pass="  ${c_green}✓${c_off}" fail="  ${c_red}✗${c_off}" info="  ${c_yellow}•${c_off}"
  log "verifying harness in $TARGET"

  for f in tools/agent/worktree.sh tools/agent/hooks/trunk_edit_guard.sh \
           tools/agent/hooks/authority_doc_budget.sh tools/agent/hooks/format_on_edit.sh \
           .agents/relink-skills.sh; do
    if [[ -x "$TARGET/$f" ]]; then printf '%s %s\n' "$pass" "$f"; else printf '%s %s (missing or not executable)\n' "$fail" "$f"; fails=$((fails+1)); fi
  done

  for pair in ".claude/settings.json:Claude Code" ".codex/hooks.json:Codex"; do
    local cfg="${pair%%:*}" label="${pair##*:}"
    if [[ -f "$TARGET/$cfg" ]]; then
      local miss=0
      for h in trunk_edit_guard authority_doc_budget; do
        grep -q "$h" "$TARGET/$cfg" || miss=1
      done
      if [[ "$miss" == 0 ]]; then printf '%s %s wiring present\n' "$pass" "$label"; else printf '%s %s wiring incomplete (%s)\n' "$fail" "$label" "$cfg"; fails=$((fails+1)); fi
    else
      printf '%s %s config missing (%s)\n' "$fail" "$label" "$cfg"; fails=$((fails+1))
    fi
  done

  if [[ -L "$TARGET/CLAUDE.md" && "$(readlink "$TARGET/CLAUDE.md")" == "AGENTS.md" ]]; then
    printf '%s CLAUDE.md → AGENTS.md symlink\n' "$pass"
  else
    printf '%s CLAUDE.md is not a symlink to AGENTS.md\n' "$fail"; fails=$((fails+1))
  fi

  if [[ -f "$TARGET/AGENTS.md" ]] && grep -qF '<!-- agent-scaffold:start' "$TARGET/AGENTS.md"; then
    printf '%s AGENTS.md carries the harness block\n' "$pass"
  else
    printf '%s AGENTS.md missing the harness block\n' "$fail"; fails=$((fails+1))
  fi

  # script drift vs the skill's vendored templates
  local drift=0
  for pair in "worktree.sh:tools/agent/worktree.sh" \
              "trunk_edit_guard.sh:tools/agent/hooks/trunk_edit_guard.sh" \
              "authority_doc_budget.sh:tools/agent/hooks/authority_doc_budget.sh" \
              "format_on_edit.sh:tools/agent/hooks/format_on_edit.sh" \
              "relink-skills.sh:.agents/relink-skills.sh"; do
    local t="${pair%%:*}" inst="$TARGET/${pair##*:}"
    [[ -f "$inst" ]] && ! cmp -s "$TPL/$t" "$inst" && { printf '%s drift: %s differs from the skill template\n' "$info" "${pair##*:}"; drift=$((drift+1)); }
  done
  [[ "$drift" == 0 ]] && printf '%s installed scripts match the skill templates\n' "$pass" || printf '%s %d script(s) drifted — run: agent-scaffold upgrade\n' "$info" "$drift"

  if [[ -f "$TARGET/tools/agent/generate-subagents.py" ]] && command -v python >/dev/null 2>&1; then
    if python "$TARGET/tools/agent/generate-subagents.py" --check >/dev/null 2>&1; then
      printf '%s subagent projections in sync\n' "$pass"
    else
      printf '%s subagent projections drifted — run: python tools/agent/generate-subagents.py\n' "$fail"; fails=$((fails+1))
    fi
  else
    printf '%s no subagent generator (python unavailable or not installed)\n' "$info"
  fi

  echo
  if [[ "$fails" == 0 ]]; then ok "verify: harness OK"; else warn "verify: $fails check(s) failed"; exit 1; fi
}

case "$MODE" in
  init|retrofit|upgrade) do_install ;;
  plan) do_plan ;;
  verify) do_verify ;;
esac
