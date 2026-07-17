# Agent Scaffold Verification

Read this only when running or extending deep verification and end-to-end fixtures.

## End-to-end test recipe

Run on a throwaway repo (all writes are inside it). This is the recipe the skill is validated
against; every assertion below passes against a clean install.

```bash
SKILL=<this skill dir>            # the dir holding harness-init.sh
H="$SKILL/harness-init.sh"
rm -rf /tmp/scratch && mkdir -p /tmp/scratch && cd /tmp/scratch
git init -q -b main && git config user.email t@t.t && git config user.name tester
git commit --allow-empty -qm init

# init (greenfield)
bash "$H" doctor
bash "$H" init
[ -z "$(ls -A .claude/skills)" ]                                             # no bogus '*' symlink
test -f .agents/tools/worktree.sh && test -f .agents/tools/hooks/trunk_edit_guard.sh
test -L CLAUDE.md && [ "$(readlink CLAUDE.md)" = AGENTS.md ]
jq -e '.hooks.PreToolUse[0].matcher=="Edit|MultiEdit|Write|NotebookEdit"' .claude/settings.json
jq -e '.hooks.PreToolUse[0].matcher=="Edit|Write|apply_patch"'              .codex/hooks.json
grep -q '^\.worktrees/$' .gitignore

# idempotent re-run — the managed PostToolUse entry stays singular
bash "$H" retrofit
jq -e '[.hooks.PostToolUse[0].hooks[].command]|length==1' .claude/settings.json

# retrofit-merge preserves a pre-existing user hook
jq '.hooks.PreToolUse[0].hooks += [{"type":"command","command":"user-custom.sh"}]' .claude/settings.json > t && mv t .claude/settings.json
bash "$H" retrofit
jq -e '[.hooks.PreToolUse[].hooks[].command]|any(test("trunk_edit_guard"))' .claude/settings.json
jq -e '[.hooks.PreToolUse[].hooks[].command]|any(test("user-custom"))'      .claude/settings.json

# worktree round-trip (commit the harness first so the worktree has the scripts)
git add -A && git commit -qm harness
bash .agents/tools/worktree.sh new demo --type chore && test -d .worktrees/demo
( cd .worktrees/demo && echo hi > note.txt && git add -A && git commit -qm "feat: note" && bash .agents/tools/worktree.sh done --no-push )
test ! -d .worktrees/demo && git log --oneline | grep -q "Merge branch 'chore/demo'"

# trunk guard blocks on main; escape hatch allows
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$PWD" | CLAUDE_PROJECT_DIR="$PWD" bash .agents/tools/hooks/trunk_edit_guard.sh; echo "exit=$?"   # 2
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$PWD" | WORKTREE_ALLOW_TRUNK_EDIT=1 CLAUDE_PROJECT_DIR="$PWD" bash .agents/tools/hooks/trunk_edit_guard.sh; echo "exit=$?"  # 0

# subagents: generator + drift guard (python — no package.json needed)
bash "$H" upgrade
python .agents/tools/generate-subagents.py --check      # exit 0, in sync
# opt-in npm convenience + husky hook on a Node project:
echo '{"name":"scratch","version":"1.0.0"}' > package.json
bash "$H" upgrade
grep -q 'generate-subagents.py --check' .husky/pre-commit
jq -e '.scripts["check:agents"]' package.json

# authority budget advises over-budget
seq 1 400 | sed 's/^/line /' > AGENTS.md
printf '{"tool_input":{"file_path":"%s/AGENTS.md"}}' "$PWD" | AUTHORITY_DOC_MAX_ROOT=320 CLAUDE_PROJECT_DIR="$PWD" bash .agents/tools/hooks/authority_doc_budget.sh   # prints budget nudge, exit 0

# relink coexistence: project skill symlinked, npx-installed real dir untouched
mkdir -p .agents/skills/proj-skill && printf -- '---\nname: proj-skill\n---\n' > .agents/skills/proj-skill/SKILL.md
mkdir -p .claude/skills/vendor-skill && echo x > .claude/skills/vendor-skill/SKILL.md
bash .agents/relink-skills.sh
test -L .claude/skills/proj-skill && test -d .claude/skills/vendor-skill && ! test -L .claude/skills/vendor-skill

# verify mode (read-only) reports OK on a clean install
bash "$H" verify

# lightweight profile (separate throwaway repo)
rm -rf /tmp/scratch-light && mkdir -p /tmp/scratch-light && cd /tmp/scratch-light
git init -q -b main && git config user.email t@t.t && git config user.name tester
git commit --allow-empty -qm init
bash "$H" plan --no-worktree | grep -qF 'retrofit --no-worktree'   # copyable apply command keeps the flag
bash "$H" init --no-worktree --no-husky --no-example-subagent
test ! -e .agents/tools/worktree.sh && test ! -e .agents/tools/hooks/trunk_edit_guard.sh
! grep -q trunk_edit_guard .claude/settings.json && ! grep -q trunk_edit_guard .codex/hooks.json
! grep -qF 'Worktree-per-change (hard rule)' AGENTS.md
bash "$H" verify --no-worktree
# The profile flag is per-invocation; plain `upgrade` deliberately restores the default profile.

# plan is read-only; retrofit adopts a real CLAUDE.md as the AGENTS.md SSOT
rm -rf /tmp/scratch2 && mkdir -p /tmp/scratch2 && cd /tmp/scratch2
git init -q -b main && git config user.email t@t.t && git config user.name tester
git commit --allow-empty -qm init
printf '# Legacy\n\nrules\n' > CLAUDE.md && git add -A && git commit -qm legacy
bash "$H" plan | grep -q migrate                                             # plan flags the migration
bash "$H" retrofit
test -L CLAUDE.md && [ "$(readlink CLAUDE.md)" = AGENTS.md ] && grep -q rules AGENTS.md

# adopt a hand-authored subagent into the SSOT (python — no package.json needed)
mkdir -p .claude/agents
printf -- '---\nname: rev\ndescription: hand-authored\ntools: Read\n---\n\nReview.\n' > .claude/agents/rev.md
bash "$H" upgrade
test -f .agents/subagents/rev/metadata.json && python .agents/tools/generate-subagents.py --check
```
