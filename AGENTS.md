# Skills — Agent Contract

`skills/` is the published catalog. `.agents/skills/` is this repository's private harness; its `skill-eval` route is not a public install target.

## Editing and verification

Edit canonical sources using the [ownership map](docs/architecture.md). Generate runtime payloads from `scripts/workflow_runtime/` and `scripts/p0_runtime/`; update scaffold-owned copies through `agent-scaffold upgrade`.

Run affected checks from [development](docs/development.md); `.github/workflows/validate.yml` defines CI. Add an Unreleased entry for user- or maintainer-visible changes. Use Conventional Commits without `Co-Authored-By`.

Keep frontmatter strict-YAML compatible; quote scalars containing `: `. Published descriptions use one physical line within the 320-character routing budget. Installer examples use quoted globs and `./` for local skill directories. Project-scope `skills remove` from the catalog root can remove catalog files.

Skills target Linux, macOS, and Windows through Git Bash, with LF source and real symlinks where required. Distinguish format, installation, wiring, and behavior evidence in support claims.

## References

| Topic | Source |
|---|---|
| Product surfaces and source/generated ownership | [Architecture](docs/architecture.md) |
| Commands, checks, and releases | [Development](docs/development.md) |
| Dated host and installer verification | [Compatibility](docs/compatibility.md) |
| Documentation ownership and freshness | [Documentation maintenance](docs/documentation-maintenance.md) |
| Skill and control design | [Harness principles](docs/harness-constraint-policy.md) |
| Canonical project terminology | [CONTEXT.md](CONTEXT.md) |
| Pending and historical release changes | [CHANGELOG.md](CHANGELOG.md) |

<!-- agent-scaffold:start (managed; edit outside) -->
<!-- agent-scaffold:profile=default -->
<!-- agent-scaffold:domains=docs,tools,testing,specs,terminology,git,release,environment -->
## Agent Harness

`.agents/` is the harness source; `.claude/` and `.codex/` hold generated projections. `CLAUDE.md` links to this contract.

### Session and task context

Honor the user's session entry; prefer task-local implementation/review. Resolve the task checkout and revision; use its `AGENTS.md` chain, terminology, skills, and tool working directories. Pass peers its absolute path and review revision. A shell `cd` does not reload host instructions or permissions; resolve access or guidance conflicts explicitly.

### Worktree-per-change (hard rule)

Never edit the primary worktree, including docs. Reuse an assigned linked worktree; otherwise, if the scaffold owns creation, run `bash .agents/tools/worktree.sh new <name>`.

Keep one lifecycle owner. `done --dir <absolute-wt>` merges, ff-only pushes, and removes the worktree; it requires explicit authorization and scaffold ownership, runs outside that worktree, and is not a PR/MR handoff. Leave externally managed worktrees to their owner instead of merging or cleaning them up. Bypass the trunk guard only with explicit user approval.

### Authority documents (hard rules)

`AGENTS.md` is the canonical repository-level Agent contract; read the applicable nested chain before acting. Keep it lean and current; route detail to project docs and nest only for real local differences. Repair durable guidance drift in the same change; follow higher-priority instructions and surface material disagreement instead of guessing. Interpret document status and freshness alongside repository evidence and user intent.

### Project terminology (hard rule)

Every Agent, project skill, and subagent uses the declared glossary, else root `CONTEXT-MAP.md`, then `CONTEXT.md`; read only relevant contexts before using project terms. A term and each language equivalent are equally valid names for one concept — use whichever is clearest and do not force one language. Reserve avoided names for history or compatibility. Resolve durable term changes with evidence and owner intent; update the glossary in the same change. Adopt an existing glossary; add definitions as durable concepts are resolved.

### Convention guides

Before the matching work, read its generic guide; project documentation and nested contracts win where they are more specific.

- Documentation: `.agents/conventions/docs.md`
- Commands and tools: `.agents/conventions/tools.md`
- Tests: `.agents/conventions/testing.md`
- Specifications and design records: `.agents/conventions/specs.md`
- Glossary changes: `.agents/conventions/terminology.md`
- Commits and delivery: `.agents/conventions/git.md`
- Version bumps, tags, and publication: `.agents/tools/release/README.md`
- Setup and shared environments: `.agents/conventions/environment.md`

### Sources and projections

- Edit skills in `.agents/skills/`, then run `bash .agents/relink-skills.sh`; commit source and symlinks.
- Edit subagents in `.agents/subagents/`, then run `python .agents/tools/generate-subagents.py`; commit source and projections.
- Do not hand-edit host projections or scaffold runtime (`.agents/tools/**`, `.agents/conventions/**`, `.agents/relink-skills.sh`, `.agents/symlink-manager.py`); use `agent-scaffold upgrade`, then `agent-scaffold verify`.
- **Third-party skills** follow project-owned placement and installation policy; preserve unrelated entries.

For Codex, confirm project trust, agent discovery, and `/hooks` approval; re-review changed definitions. Restore symlink/hardlink targets with Git, not Claude checkpoints.
<!-- agent-scaffold:end -->
