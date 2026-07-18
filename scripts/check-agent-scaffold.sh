#!/usr/bin/env bash
# check-agent-scaffold.sh — static quality gate for the agent-scaffold skill.
#
# Usage: bash scripts/check-agent-scaffold.sh [-h|--help]
# Checks syntax, LF/executable contracts, managed-asset reconciliation, current
# public surface, hook install depth, and this repository's dogfood copies.
# Exit 0 clean, 1 on any failed invariant. Requires bash, git, and Python.
set -uo pipefail

usage() { sed -n '2,7p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "$#" in
  0) ;;
  1) case "$1" in -h|--help) usage 0 ;; *) usage 2 ;; esac ;;
  *) usage 2 ;;
esac

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill="$repo/skills/agent-scaffold"
core="$skill/scripts/harness-core.py"
manifest="$skill/scripts/managed-assets.json"
fails=0
fail() { printf 'FAIL: %s\n' "$*"; fails=$((fails + 1)); }

[ -d "$skill" ] || { echo "agent-scaffold skill not present — nothing to check"; exit 0; }
command -v python >/dev/null 2>&1 || fail "python unavailable (required by agent-scaffold)"

for entrypoint in \
  "$repo/scripts/e2e-agent-scaffold.sh" \
  "$repo/scripts/tests/e2e-agent-scaffold-preflight.sh"; do
  bash "$entrypoint" --not-a-real-option >/dev/null 2>&1
  [ "$?" = 2 ] || fail "unknown option does not exit 2: ${entrypoint#"$repo"/}"
  bash "$entrypoint" --help --not-a-real-option >/dev/null 2>&1
  [ "$?" = 2 ] || fail "help masks an unknown option: ${entrypoint#"$repo"/}"
done

if ! python "$core" --manifest "$manifest" assets validate >/dev/null 2>&1; then
  fail "managed-assets manifest is invalid or references a missing source"
fi

# Syntax and LF are checked across every shipped executable source, including
# internal helpers. Runtime assets remain executable in Git because consumers
# may invoke the installed copies directly.
while IFS= read -r file; do
  bash -n "$file" 2>/dev/null || fail "bash syntax error: ${file#"$repo"/}"
  [ -n "$(tr -dc '\015' < "$file")" ] \
    && fail "CRLF line endings — must be LF: ${file#"$repo"/}"
done < <(find "$skill" -type f -name '*.sh' -print)

while IFS= read -r file; do
  python -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$file" 2>/dev/null \
    || fail "python syntax error: ${file#"$repo"/}"
  [ -n "$(tr -dc '\015' < "$file")" ] \
    && fail "CRLF line endings — must be LF: ${file#"$repo"/}"
done < <(find "$skill" -type f -name '*.py' -print)

if grep -En '(^|[^[:alnum:]_])(declare|local)[[:space:]]+-A|(^|[^[:alnum:]_])(mapfile|readarray)([^[:alnum:]_]|$)' \
    "$skill/agent-scaffold.sh" "$skill"/assets/runtime/*.sh "$skill"/assets/runtime/hooks/*.sh \
    >/dev/null 2>&1; then
  fail "Bash 4-only construct found in agent-scaffold shell scripts"
fi

file="$skill/agent-scaffold.sh"
relative="${file#"$repo"/}"
mode="$(git -C "$repo" ls-files -s -- "$relative" | awk 'NR==1{print $1}')"
[ "$mode" = 100755 ] || fail "git mode is ${mode:-untracked}, expected 100755: $relative"
[ ! -e "$skill/harness-init.sh" ] || fail "retired public entry remains: skills/agent-scaffold/harness-init.sh"

while IFS=$'\t' read -r id source target strategy executable; do
  executable="${executable%$'\r'}"
  [ "$strategy" = copy ] || continue
  [ "$executable" = 1 ] || continue
  relative="skills/agent-scaffold/$source"
  mode="$(git -C "$repo" ls-files -s -- "$relative" | awk 'NR==1{print $1}')"
  [ "$mode" = 100755 ] || fail "git mode is ${mode:-untracked}, expected 100755: $relative ($id)"
done < <(python "$core" --manifest "$manifest" assets list --profile default --strategy copy)

# Hook runtime depth is a cross-host invariant.
for hook in trunk_edit_guard authority_doc_budget; do
  file="$skill/assets/runtime/hooks/$hook.sh"
  [ -f "$file" ] || { fail "missing runtime hook: $hook.sh"; continue; }
  grep -qF 'hook-common.sh' "$file" || fail "$hook.sh does not source hook-common.sh"
done
common="$skill/assets/runtime/hooks/hook-common.sh"
grep -qF '/../../..' "$common" || fail "hook-common.sh lost the 3-level install fallback"
grep -qF 'rev-parse --show-toplevel' "$common" || fail "hook-common.sh lost the git-root fallback"
grep -qF 'cygpath -u' "$common" || fail "hook-common.sh lost Windows/MSYS path conversion"

for config in claude.settings.json codex.hooks.json; do
  file="$skill/assets/host/$config"
  grep -q '"command": "bash ' "$file" || fail "$config does not invoke hooks through bash"
done
grep -qF '<!-- agent-scaffold:worktree:start -->' "$skill/assets/scaffold/AGENTS.harness.md" \
  || fail "AGENTS.harness.md lost the profile boundary"
grep -qF 'Third-party skills** follow project-owned placement and installation policy' \
  "$skill/assets/scaffold/AGENTS.harness.md" \
  || fail "AGENTS.harness.md lost project-owned third-party policy wording"
# shellcheck disable=SC2016  # backticks are literal Markdown in the rejected wording
if grep -qF 'they land as real dirs in `.claude/skills/`' \
  "$skill/assets/scaffold/AGENTS.harness.md" >/dev/null 2>&1; then
  fail "AGENTS.harness.md publishes an unconditional third-party placement policy"
fi

worktree_helper="$skill/assets/runtime/worktree.sh"
grep -qF 'removed clean detached release worktree' "$worktree_helper" \
  || fail "worktree.sh lost guarded detached-release cleanup"
if grep -qF 'git worktree remove --force' "$worktree_helper" >/dev/null 2>&1; then
  fail "worktree.sh tells users to force-remove release worktrees"
fi
grep -qF 'files atomic-replace' "$skill/agent-scaffold.sh" \
  || fail "agent-scaffold.sh lost same-directory atomic state replacement"
grep -qF 'agent-scaffold-link-' "$skill/assets/runtime/symlink-manager.py" \
  || fail "symlink-manager.py lost unique temporary link names"
if grep -qF 'shutil.rmtree(path)' "$skill/assets/runtime/symlink-manager.py" >/dev/null 2>&1; then
  fail "symlink-manager.py recursively removes an untrusted projection path"
fi

# The public surface has one ordinary mutating mode.
if grep -Eq '<init\|retrofit|\b(init|retrofit)\b.*Mode|Modes:.*(init|retrofit)' \
    "$skill/SKILL.md" "$skill/agent-scaffold.sh"; then
  fail "retired init/retrofit command surface remains"
fi

# Dogfood copies in this repository must match every active default-profile
# runtime asset. The same manifest drives install, verify, and this drift gate.
if [ -d "$repo/.agents/tools" ]; then
  while IFS=$'\t' read -r id source target strategy executable; do
    executable="${executable%$'\r'}"
    [ "$strategy" = copy ] || continue
    installed="$repo/$target"
    bundled="$skill/$source"
    if [ ! -f "$installed" ]; then
      fail "dogfood harness file missing: $target (run agent-scaffold upgrade)"
    elif ! cmp -s "$bundled" "$installed"; then
      fail "dogfood drift: $target differs from $source"
    fi
  done < <(python "$core" --manifest "$manifest" assets list --profile default --strategy copy)
fi

if [ -f "$repo/.agents/tools/generate-subagents.py" ]; then
  (cd "$repo" && python .agents/tools/generate-subagents.py --check >/dev/null 2>&1) \
    || fail "subagent projection drift"
fi

if [ "$fails" -eq 0 ]; then
  echo "OK: agent-scaffold checks passed"
  exit 0
fi
echo "FAIL: $fails agent-scaffold check(s) failed"
exit 1
