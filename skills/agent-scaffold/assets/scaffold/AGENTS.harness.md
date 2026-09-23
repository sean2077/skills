<!-- agent-scaffold:start — managed; keep project prose outside; upgrade refreshes this block. -->
<!-- agent-scaffold:profile=default -->
## Agent Harness

`.agents/` is the harness source; `.claude/` and `.codex/` hold generated projections. `CLAUDE.md` links to this contract.

### Session and task context

Honor the user's session entry; prefer task-local implementation/review. Resolve the task checkout and revision; use its `AGENTS.md` chain, terminology, skills, and tool working directories. Pass peers its absolute path and review revision. A shell `cd` does not reload host instructions or permissions; resolve access or guidance conflicts explicitly.

<!-- agent-scaffold:worktree:start -->
### Worktree-per-change (hard rule)

Never edit the primary worktree, including docs. Reuse an assigned linked worktree; otherwise, if the scaffold owns creation, run `bash .agents/tools/worktree.sh new <name>`.

Keep one lifecycle owner. `done --dir <absolute-wt>` merges, ff-only pushes, and removes the worktree; it requires explicit authorization and scaffold ownership, runs outside that worktree, and is not a PR/MR handoff. Leave externally managed worktrees to their owner instead of merging or cleaning them up. Bypass the trunk guard only with explicit user approval.

<!-- agent-scaffold:worktree:end -->
### Authority documents (hard rules)

`AGENTS.md` is the canonical repository-level Agent contract; read the applicable nested chain before acting. Keep it lean and current; route detail to project docs and nest only for real local differences. Repair durable guidance drift in the same change; follow higher-priority instructions and surface material disagreement instead of guessing. Interpret document status and freshness alongside repository evidence and user intent.

<!-- agent-scaffold:terminology:start -->
### Project terminology (hard rule)

Every Agent, project skill, and subagent uses the declared glossary, else root `CONTEXT-MAP.md`, then `CONTEXT.md`; read only relevant contexts before using project terms. A term and each language equivalent are equally valid names for one concept — use whichever is clearest and do not force one language. Reserve avoided names for history or compatibility. Resolve durable term changes with evidence and owner intent; update the glossary in the same change. Adopt an existing glossary; add definitions as durable concepts are resolved.

<!-- agent-scaffold:terminology:end -->
<!-- agent-scaffold:conventions:start -->
### Convention guides

Before the matching work, read its generic guide; project documentation and nested contracts win where they are more specific.

- Documentation: `.agents/conventions/docs.md` <!-- agent-scaffold:domain=docs -->
- Commands and tools: `.agents/conventions/tools.md` <!-- agent-scaffold:domain=tools -->
- Tests: `.agents/conventions/testing.md` <!-- agent-scaffold:domain=testing -->
- Specifications and design records: `.agents/conventions/specs.md` <!-- agent-scaffold:domain=specs -->
- Glossary changes: `.agents/conventions/terminology.md` <!-- agent-scaffold:domain=terminology -->
- Commits and delivery: `.agents/conventions/git.md` <!-- agent-scaffold:domain=git -->
- Version bumps, tags, and publication: `.agents/tools/release/README.md` <!-- agent-scaffold:domain=release -->
- Setup and shared environments: `.agents/conventions/environment.md` <!-- agent-scaffold:domain=environment -->

<!-- agent-scaffold:conventions:end -->
### Sources and projections

- Edit skills in `.agents/skills/`, then run `bash .agents/relink-skills.sh`; commit source and symlinks.
- Edit subagents in `.agents/subagents/`, then run `python .agents/tools/generate-subagents.py`; commit source and projections.
- Do not hand-edit host projections or scaffold runtime (`.agents/tools/**`, `.agents/conventions/**`, `.agents/relink-skills.sh`, `.agents/symlink-manager.py`); use `agent-scaffold upgrade`, then `agent-scaffold verify`.
- **Third-party skills** follow project-owned placement and installation policy; preserve unrelated entries.

For Codex, confirm project trust, agent discovery, and `/hooks` approval; re-review changed definitions. Restore symlink/hardlink targets with Git, not Claude checkpoints.
<!-- agent-scaffold:end -->
