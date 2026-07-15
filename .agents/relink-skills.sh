#!/usr/bin/env bash
# Regenerate the real per-skill symlinks that project .agents/skills/ (the
# authoritative source) into .claude/skills/ for Claude Code discovery.
#
# Add a skill: create .agents/skills/<name>/SKILL.md, then run this script.
# Real symlinks are a hard prerequisite. Unsupported hosts fail before mutation;
# this command never creates a copy fallback. Third-party real directories and
# unrelated symlinks under .claude/skills/ remain untouched.
#
# Usage: bash .agents/relink-skills.sh [-h|--help]
# Exit 2 means a missing prerequisite or a projection conflict.
set -euo pipefail

usage() { sed -n '2,10p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "${1:-}" in -h | --help) usage 0 ;; "") ;; *) usage 2 ;; esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manager="$repo_root/.agents/symlink-manager.py"
[[ -f "$manager" ]] || { echo "relink: missing helper .agents/symlink-manager.py; run agent-scaffold upgrade" >&2; exit 2; }

PYTHON_CMD=()
if [[ -n "${PYTHON_BIN:-}" ]] && command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_CMD=("$PYTHON_BIN")
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=(python)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=(python3)
elif command -v py >/dev/null 2>&1 && py -3 -c 'import sys' >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
else
  echo "relink: python is required (set PYTHON_BIN, or install python/python3/py -3)" >&2
  exit 2
fi

exec "${PYTHON_CMD[@]}" "$manager" sync-skills --repo "$repo_root"
