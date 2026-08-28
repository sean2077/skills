<!-- agent-scaffold:start — managed; keep project prose outside; upgrade refreshes this block. -->
## Agent Harness (Claude Code + Codex)

`.agents/` is the SSOT for harness-owned skills, subagents, and runtime; `.claude/` and `.codex/` contain host projections.

<!-- agent-scaffold:worktree:start -->
### Worktree-per-change (hard rule)

The primary worktree's checked-out branch is the active trunk (`--trunk` overrides); `new` records it and `done` merges back. Never edit the primary worktree directly, including docs:

```bash
bash .agents/tools/worktree.sh new <name>  # work in .worktrees/<name>/
bash .agents/tools/worktree.sh done        # merge, clean up, and ff-only push
```

On Windows, leave the target worktree and run `done --dir <absolute-wt>` from the primary worktree; `new` prints the exact command.

The trunk guard blocks non-ignored project-file edits in the primary worktree, regardless of branch name. Bypass it only with explicit user approval: `WORKTREE_ALLOW_TRUNK_EDIT=1`, or `touch .claude/allow-trunk-edit` for a 2 h flag.

<!-- agent-scaffold:worktree:end -->
### Authority documents (hard rules)

`AGENTS.md` is the canonical repository-level contract for Agent work. Read the root contract and applicable nested chain before acting.

- **Keep it current.** When a durable Agent-relevant change makes guidance stale, update it in the same change.
- **Keep it lean.** Keep only frequent or costly-to-miss behavior; route depth to project docs.
- **Keep scopes honest.** Add nested `AGENTS.md` only for a concrete local difference; directory structure alone never justifies one.
- **Resolve conflicts explicitly.** Surface conflicts, follow higher-priority instructions, ask the owner when authority is unclear, and repair stale guidance when authorized.

The authority-document budget hook remains advisory; projects may override its default line and character limits.

### Project terminology (hard rule)

Every Agent, project skill, and subagent uses the canonical terminology source declared in project-owned `AGENTS.md` prose. If none is declared, use root `CONTEXT.md`; root `CONTEXT-MAP.md` may route multi-context repositories to context-local `CONTEXT.md` files.

- **Load only what applies.** Before naming or interpreting project concepts, read the declared glossary or map and only the relevant context file.
- **Use canonical terms.** Use them in project-controlled code, APIs, tests, docs, plans, and commits. Treat `_Avoid_` names as migration/search aliases; preserve externally fixed names only at compatibility boundaries.
- **Close vocabulary drift.** When a durable concept, ambiguity, or synonym appears, resolve it against repository evidence and project-owner intent, then update the applicable glossary in the same change. Do not silently introduce a second name.
- **Keep glossaries focused.** Define project-specific concepts briefly and without behavior, architecture, or decision detail.

If no source is declared, adopt an existing project glossary rather than duplicating it; if none exists, create root `CONTEXT.md` only when the first durable project term is resolved. Never seed an empty glossary.

### Sources and projections

- Edit project skills in `.agents/skills/<name>/`, then run `bash .agents/relink-skills.sh`; commit source and symlink.
- Edit project subagents in `.agents/subagents/<name>/`, then run `python .agents/tools/generate-subagents.py`; commit source and projections.
- Do not hand-edit harness projections: `CLAUDE.md`, `.claude/skills/<name>` entries owned by `.agents/skills/`, `.claude/agents/*.md`, or `.codex/agents/*.toml`.
- Do not hand-edit scaffold runtime: `.agents/tools/**`, `.agents/relink-skills.sh`, or `.agents/symlink-manager.py`. Refresh it with `agent-scaffold upgrade`, then run `agent-scaffold verify`.
- **Third-party skills** follow project-owned placement and installation policy. The relinker preserves unrelated names and rejects same-name conflicts.

For Codex, trust the project, confirm generated agents are discoverable, and review each exact hook definition in `/hooks`; re-review changed definitions. Claude checkpoints do not rewind symlinked or hard-linked targets (`CLAUDE.md`, `.claude/skills/*`); inspect and restore the real target with Git.
<!-- agent-scaffold:end -->
