#!/usr/bin/env bash
# check-agent-scaffold.sh — quality gate for the agent-scaffold skill.
#
# Asserts the bundled scripts are syntactically valid and that the three hook
# scripts share the `.agents/tools/hooks/` install-depth resolver — `proj` three
# levels up plus a `git rev-parse --show-toplevel` fallback — and keep the
# Bash-3.2/real-symlink cross-platform contract.
#
# Exit 0 clean, 1 on failure. No third-party deps (bash; python only if present).
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

# 2. python syntax on every shipped helper (python is a harness prerequisite)
if command -v python >/dev/null 2>&1; then
  for f in "$sk"/templates/*.py; do
    [ -f "$f" ] || continue
    python -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$f" 2>/dev/null \
      || fail "python syntax error: ${f#"$sk/templates/"}"
  done
else
  fail "python unavailable (required by agent-scaffold)"
fi

# 3. hooks must source the shared runtime; it owns the 3-level + git fallback
for h in trunk_edit_guard authority_doc_budget format_on_edit; do
  f="$sk/templates/$h.sh"
  [ -f "$f" ] || { fail "missing hook template: $h.sh"; continue; }
  grep -qF 'hook-common.sh' "$f" || fail "$h.sh does not source hook-common.sh"
done
common="$sk/templates/hook-common.sh"
grep -qF '/../../..' "$common" || fail "hook-common.sh lost the 3-level install fallback"
grep -qF 'rev-parse --show-toplevel' "$common" || fail "hook-common.sh lost the git-root fallback"
grep -qF 'cygpath -u' "$common" || fail "hook-common.sh lost native Windows/MSYS path conversion"

# 4. shipped command/helper scripts must be committed executable. Inspect the
# index rather than `[ -x ]`, which is unreliable with Windows core.filemode=false.
for f in "$sk/harness-init.sh" "$sk"/templates/*.sh "$sk"/templates/*.py; do
  [ -f "$f" ] || continue
  rel="${f#"$repo"/}"
  mode="$(git -C "$repo" ls-files -s -- "$rel" | awk 'NR==1{print $1}')"
  [ "$mode" = 100755 ] || fail "git mode is ${mode:-untracked}, expected 100755: $rel"
done

# 4b. shipped scripts must be LF-only — CRLF breaks bash under Windows/Git Bash, and
#     these are copied verbatim into consumer projects (cross-platform design goal).
for f in "$sk/harness-init.sh" "$sk"/templates/*.sh "$sk"/templates/*.py "$sk/templates/husky.pre-commit"; do
  [ -f "$f" ] || continue
  [ -n "$(tr -dc '\015' < "$f")" ] && fail "CRLF line endings — must be LF (Windows/Git Bash): ${f#"$repo"/}"
done

# 4c. macOS ships Bash 3.2: ban the known Bash-4-only constructs from shipped
# scripts. (Indexed arrays and process substitution remain valid in 3.2.)
if grep -En '(^|[^[:alnum:]_])(declare|local)[[:space:]]+-A|(^|[^[:alnum:]_])(mapfile|readarray)([^[:alnum:]_]|$)' \
    "$sk/harness-init.sh" "$sk"/templates/*.sh >/dev/null 2>&1; then
  fail "Bash 4-only construct found in agent-scaffold shell scripts"
fi

# Hook configs must invoke shell helpers through bash, never via executable-bit
# dispatch (Windows commonly checks files out with core.filemode=false).
for cfg in claude.settings.json codex.hooks.json; do
  grep -q '"command": "bash ' "$sk/templates/$cfg" || fail "$cfg does not invoke hooks via bash"
done
grep -q -- '--no-worktree' "$sk/harness-init.sh" || fail "harness-init.sh lost the lightweight profile flag"
grep -qF '<!-- agent-scaffold:worktree:start -->' "$sk/templates/AGENTS.root.md" \
  || fail "AGENTS.root.md lost the optional worktree policy boundary"
grep -qF 'HARNESS_ENABLE_WORKTREE' "$sk/harness-init.sh" \
  || fail "hook reconciliation no longer filters the optional trunk guard"

# Legacy runtime text is allowed only where upgrade recognizes, explains, or tests
# the hard-cut migration. Active contracts and current command examples must not drift back.
legacy_runtime="tools""/agent"
while IFS= read -r legacy_file; do
  case "$legacy_file" in
    .agents/tools/generate-subagents.py | \
    .oma/* | \
    CHANGELOG.md | \
    scripts/e2e-agent-scaffold.sh | \
    skills/agent-scaffold/SKILL.md | \
    skills/agent-scaffold/harness-init.sh | \
    skills/agent-scaffold/references/harness-migration.md | \
    skills/agent-scaffold/templates/generate-subagents.py) ;;
    *) fail "stale active legacy runtime reference: $legacy_file" ;;
  esac
done < <(git -C "$repo" grep -lF "$legacy_runtime" -- . 2>/dev/null || true)

# 5. dogfood drift: if this repo installed the harness (.agents/tools/ exists), the
#    installed copies must stay byte-identical to the skill templates they came from.
if [ -d "$repo/.agents/tools" ]; then
  for pair in \
    "worktree.sh:.agents/tools/worktree.sh" \
    "trunk_edit_guard.sh:.agents/tools/hooks/trunk_edit_guard.sh" \
    "authority_doc_budget.sh:.agents/tools/hooks/authority_doc_budget.sh" \
    "format_on_edit.sh:.agents/tools/hooks/format_on_edit.sh" \
    "hook-common.sh:.agents/tools/hooks/hook-common.sh" \
    "hook-paths.py:.agents/tools/hooks/hook-paths.py" \
    "relink-skills.sh:.agents/relink-skills.sh" \
    "symlink-manager.py:.agents/symlink-manager.py" \
    "generate-subagents.py:.agents/tools/generate-subagents.py"; do
    inst="$repo/${pair##*:}"
    if [ ! -f "$inst" ]; then
      fail "dogfood harness file missing: ${pair##*:} (run: agent-scaffold upgrade)"
    elif ! cmp -s "$sk/templates/${pair%%:*}" "$inst"; then
      fail "dogfood drift: ${pair##*:} differs from its skill template (run: agent-scaffold upgrade)"
    fi
    case "$inst" in
      *.sh | *.py)
        rel="${inst#"$repo"/}"
        mode="$(git -C "$repo" ls-files -s -- "$rel" | awk 'NR==1{print $1}')"
        [ "$mode" = 100755 ] || fail "dogfood git mode is ${mode:-untracked}, expected 100755: $rel"
        ;;
    esac
  done
fi

# 6. subagent projection drift: this repo dogfoods the generator, so CI stands in for the
#    pre-commit --check guard (no package.json/husky here). No sources -> clean exit 0.
if [ -f "$repo/.agents/tools/generate-subagents.py" ] && command -v python >/dev/null 2>&1; then
  ( cd "$repo" && python .agents/tools/generate-subagents.py --check >/dev/null 2>&1 ) \
    || fail "subagent projection drift (run: python .agents/tools/generate-subagents.py)"
fi

if [ "$fails" -eq 0 ]; then
  echo "OK: agent-scaffold checks passed"
  exit 0
fi
echo "FAIL: $fails agent-scaffold check(s) failed"
exit 1
