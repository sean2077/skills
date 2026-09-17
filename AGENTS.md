# PROJECT — Agent Contract

> `AGENTS.md` is the canonical repository-level contract; `CLAUDE.md` is a symlink to it. Keep this file an actionable entry point and put durable detail in `docs/`.

## Project

`sean2077/skills` publishes independently installable Agent Skills under `skills/`. The repository-private `.agents/skills/skill-eval` workflow belongs to the dogfooded project harness and is not a catalog target. Consumers need no build step; maintainers must regenerate checked-in runtime payloads from their source modules before committing.

## Required workflow

1. Read this contract and any applicable nested `AGENTS.md` before changing files.
2. Follow the scaffold-managed worktree rule below; documentation-only work is not an exception.
3. Edit the canonical source, not a generated projection or scaffold-owned managed copy. Use the ownership map in [repository architecture](docs/architecture.md).
4. Run the changed-surface checks and the appropriate full gates from the [development guide](docs/development.md). `.github/workflows/validate.yml` is the normative CI definition.
5. Add an Unreleased changelog entry for user- or maintainer-visible behavior. Use Conventional Commits, omit `Co-Authored-By`, and keep all required gates green before merging to `main`.

## Repository boundaries

- `skills/` is the published product; `.agents/skills/` is the private project harness. Never infer one catalog from the other.
- `scripts/workflow_runtime/` and `scripts/p0_runtime/` are maintainer source. Run their generators instead of editing generated skill runtime payloads.
- Format validation, installer discovery, host wiring, and runtime behavior are different evidence layers. Keep support claims in [compatibility.md](docs/compatibility.md).
- Prefer model-native reasoning for reversible single-session work. Add deterministic controls only for the costly machine-checkable boundaries described in the [harness constraint policy](docs/harness-constraint-policy.md).
- Skills and bundled scripts target Linux, macOS, and Windows through Git Bash, with LF line endings and real symlinks where the scaffold requires them.

## High-cost maintenance traps

- Keep frontmatter strict-YAML compatible. Quote a scalar containing `: `.
- Keep every published `description` on one physical line and within the 320-character routing budget; preserve decisive triggers and exclusions.
- Treat copy-paste commands as interfaces: verify working directory, scope, quoting, identity, side effects, and expected result. Quote shell globs such as `'*'`.
- Prefix local skill directories with `./`; otherwise the installer may interpret the value as a GitHub repository.
- Do not describe the CI-audited `skills@1.5.17` pin as upstream latest. Do not run project-scope `skills remove` from the catalog root.

## Canonical references

| Topic | Source |
|---|---|
| Product surfaces, generated ownership, and validation boundaries | [docs/architecture.md](docs/architecture.md) |
| Local workflow, commands, platform checks, and releases | [docs/development.md](docs/development.md) |
| Host, installer, trust, and certification claims | [docs/compatibility.md](docs/compatibility.md) |
| Documentation ownership, evidence, and freshness | [docs/documentation-maintenance.md](docs/documentation-maintenance.md) |
| Mechanical-control selection | [docs/harness-constraint-policy.md](docs/harness-constraint-policy.md) |
| Canonical project terminology, context grouping, language equivalents, and avoided names | [CONTEXT.md](CONTEXT.md) |
| Pending and historical release changes | [CHANGELOG.md](CHANGELOG.md) |

<!-- agent-scaffold:start — managed; keep project prose outside; upgrade refreshes this block. -->
## Agent Harness

`.agents/` is the harness source; `.claude/` and `.codex/` hold generated projections. `CLAUDE.md` links to this contract.

### Session and task context

Honor the user's session entry; prefer task-local implementation/review. Resolve the task checkout and revision; use its `AGENTS.md` chain, terminology, skills, and tool working directories. Pass peers its absolute path and review revision. A shell `cd` does not reload host instructions or permissions; resolve access or guidance conflicts explicitly.

### Worktree-per-change (hard rule)

Never edit the primary worktree, including docs. Reuse an assigned linked worktree; otherwise, if the scaffold owns creation, run `bash .agents/tools/worktree.sh new <name>`.

Keep one lifecycle owner. `done --dir <absolute-wt>` merges, ff-only pushes, and removes the worktree; it requires explicit authorization and scaffold ownership, runs outside that worktree, and is not a PR/MR handoff. Leave externally managed worktrees to their owner instead of merging or cleaning them up. Bypass the trunk guard only with explicit user approval.

### Authority documents (hard rules)

`AGENTS.md` is the canonical repository-level Agent contract; read the applicable nested chain before acting. Keep it lean and current; route detail to project docs and nest only for real local differences. Repair durable guidance drift in the same change; follow higher-priority instructions and surface material disagreement instead of guessing. Judge document metadata against evidence and user intent: drafts/superseded notes are not settled guidance; missing metadata is not a blocker.

### Project terminology (hard rule)

Every Agent, project skill, and subagent uses the declared glossary, else root `CONTEXT-MAP.md`, then `CONTEXT.md`; read only relevant contexts before using project terms. A term and each language equivalent are equally valid names for one concept — use whichever is clearest and do not force one language. Reserve avoided names for history or compatibility. Resolve durable term changes with evidence and owner intent; update the glossary in the same change. Adopt an existing glossary. Never seed an empty glossary.

### Sources and projections

- Edit skills in `.agents/skills/`, then run `bash .agents/relink-skills.sh`; commit source and symlinks.
- Edit subagents in `.agents/subagents/`, then run `python .agents/tools/generate-subagents.py`; commit source and projections.
- Do not hand-edit host projections or scaffold runtime (`.agents/tools/**`, `.agents/relink-skills.sh`, `.agents/symlink-manager.py`); use `agent-scaffold upgrade`, then `agent-scaffold verify`.
- **Third-party skills** follow project-owned placement and installation policy; preserve unrelated entries.

For Codex, confirm project trust, agent discovery, and `/hooks` approval; re-review changed definitions. Restore symlink/hardlink targets with Git, not Claude checkpoints.
<!-- agent-scaffold:end -->
