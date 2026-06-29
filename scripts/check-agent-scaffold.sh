#!/usr/bin/env bash
# check-agent-scaffold.sh — quality gate for the agent-scaffold skill.
#
# Asserts the bundled scripts are syntactically valid and that the three hook
# scripts keep the `tools/agent/hooks/` install-depth resolver — `proj` three
# levels up plus a `git rev-parse --show-toplevel` fallback. That resolver is what
# makes them dual-host-correct: Codex has no $CLAUDE_PROJECT_DIR, so a shallower
# CC-only resolver would silently break the Codex side. Do not flatten it.
#
# Exit 0 clean, 1 on failure. No third-party deps (bash; node only if present).
set -uo pipefail

usage() { sed -n '2,10p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "${1:-}" in -h | --help) usage 0 ;; esac

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sk="$repo/skills/agent-scaffold"
fails=0
fail() { printf 'FAIL: %s\n' "$*"; fails=$((fails + 1)); }

[ -d "$sk" ] || { echo "agent-scaffold skill not present — nothing to check"; exit 0; }

# 1. bash syntax on every shipped shell script
for f in "$sk/harness-init.sh" "$sk"/templates/*.sh; do
  [ -f "$f" ] || continue
  bash -n "$f" 2>/dev/null || fail "bash syntax error: ${f#"$repo"/}"
done

# 2. node syntax on the generator (when node is available)
if command -v node >/dev/null 2>&1 && [ -f "$sk/templates/generate-subagents.mjs" ]; then
  node --check "$sk/templates/generate-subagents.mjs" 2>/dev/null || fail "node syntax error: generate-subagents.mjs"
fi

# 3. install-depth invariant on the three hooks (3 levels up + git fallback)
for h in trunk_edit_guard authority_doc_budget format_on_edit; do
  f="$sk/templates/$h.sh"
  [ -f "$f" ] || { fail "missing hook template: $h.sh"; continue; }
  if ! grep -qF '/../../..' "$f" || ! grep -qF 'rev-parse --show-toplevel' "$f"; then
    fail "$h.sh lost the tools/agent/hooks/ install-depth resolver (3 levels up + git fallback)"
  fi
done

# 4. shipped scripts are executable
for f in "$sk/harness-init.sh" "$sk"/templates/*.sh "$sk"/templates/*.mjs; do
  [ -f "$f" ] || continue
  [ -x "$f" ] || fail "not executable (commit the +x bit): ${f#"$repo"/}"
done

if [ "$fails" -eq 0 ]; then
  echo "OK: agent-scaffold checks passed"
  exit 0
fi
echo "FAIL: $fails agent-scaffold check(s) failed"
exit 1
