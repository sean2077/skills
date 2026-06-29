#!/usr/bin/env bash
# Regenerate the per-skill symlinks that map .agents/skills/ (the authoritative
# source) into .claude/skills/, so Claude Code discovers them. Codex reads
# .agents/skills/ directly, so it needs no symlinks. Idempotent — safe to re-run.
#
# Add a skill:  create .agents/skills/<name>/SKILL.md, then run this script.
# See .agents/skills/README.md for the full authoring contract.
#
# Coexistence with `npx skills` (or any externally-installed skill): an entry in
# .claude/skills/ that is a REAL directory (not a symlink) is treated as
# vendor-native and left untouched. Only symlinks this script created are
# (re)pointed or pruned. Keep project skill names distinct from installed ones.
set -euo pipefail

usage() { sed -n '2,12p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "${1:-}" in -h | --help) usage 0 ;; esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

src=".agents/skills"
vendor=".claude/skills"
[ -d "$src" ] || { echo "relink: no $src here" >&2; exit 1; }
mkdir -p "$vendor"

made=0 pruned=0 copied=0
# Make one skill symlink, detecting the Git-Bash-on-Windows case where `ln -s`
# silently COPIES instead of linking (the copy then drifts from the source).
link_one() {  # <name> <target>
  ln -sfn "$2" "$vendor/$1" 2>/dev/null || true
  if [ -L "$vendor/$1" ]; then
    made=$((made + 1))
  else
    copied=$((copied + 1))
    echo "relink: WARN $vendor/$1 is a COPY, not a symlink — it will drift from $src/$1. Windows/Git Bash: git config core.symlinks true; export MSYS=winsymlinks:nativestrict; + Developer Mode, then re-run." >&2
  fi
}
# prune symlinks whose source skill no longer exists (and any _* leftovers)
for link in "$vendor"/*; do
  [ -L "$link" ] || continue
  name="$(basename "$link")"
  case "$name" in
    _*) rm -f "$link"; pruned=$((pruned + 1)); continue ;;
  esac
  [ -d "$src/$name" ] || { rm -f "$link"; pruned=$((pruned + 1)); }
done
# (re)create one symlink per authoritative skill (skip _* support dirs)
for d in "$src"/*/; do
  [ -d "$d" ] || continue   # no skill dirs yet → unmatched glob stays literal; skip it
  name="$(basename "$d")"
  case "$name" in
    _*) continue ;;
  esac
  target="../../.agents/skills/$name"
  if [ -L "$vendor/$name" ]; then
    [ "$(readlink "$vendor/$name")" = "$target" ] || link_one "$name" "$target"
  elif [ -d "$vendor/$name" ] && diff -rq "$vendor/$name" "$src/$name" >/dev/null 2>&1; then
    # a prior Git-Bash degradation copy (byte-identical to the source) — converge it
    # back to a real symlink now that linking works. A genuine vendor-native dir has
    # different contents and falls through to the skip branch below, untouched.
    rm -rf "${vendor:?}/$name"; link_one "$name" "$target"
  elif [ -e "$vendor/$name" ]; then
    echo "relink: skip $vendor/$name — exists and is not a symlink (vendor-native skill?)" >&2
  else
    link_one "$name" "$target"
  fi
done

skill_count="$(find "$src" -mindepth 1 -maxdepth 1 -type d ! -name '_*' | wc -l | tr -d ' ')"
summary="relink: ${skill_count} skills · ${made} link(s) (re)created · ${pruned} stale pruned"
[ "$copied" -gt 0 ] && summary="$summary · ${copied} copied (no symlink support — see warnings)"
echo "$summary"
