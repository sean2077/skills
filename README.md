# skills

A curated catalog of 12 reusable [Agent Skills](https://agentskills.io/specification) for requirements, documentation, repository operations, release, and productivity.

Install the skills that add something to your host or project. Ordinary investigation, experiments, cleanup, review, and delivery use the host/project workflow (including native goals where available); there is no mandatory skill chain. The [selection guide](docs/skill-composition.md) explains adjacent routes and retired installations.

## Install

Run installation from the **consumer project**, not this catalog checkout. These examples use the repository's audited installer pin; they do not claim it is the latest version.

```bash
# One skill for Claude Code and Codex
npx --yes skills@1.5.17 add sean2077/skills --skill tdd -a claude-code -a codex

# Complete catalog for just these two targets
npx --yes skills@1.5.17 add sean2077/skills --skill '*' -a claude-code -a codex

# A local catalog source, still installing into the consumer project
npx --yes skills@1.5.17 add /absolute/path/to/skills --skill agent-scaffold -a codex
```

Replace the absolute path with the catalog checkout. Repeat `--skill` and `-a` for selective installs; quote `'*'`. A relative local source needs `./` or `../`, not a repository-like shorthand. See [installer semantics](docs/compatibility.md#installer-semantics) for scope, discovery-only checks, global installation, and safe removal.

Installing `agent-scaffold` makes the skill available; it does **not** apply a harness to the consumer project. Its [entry point](skills/agent-scaffold/SKILL.md) starts with a read-only plan. Host trust and hook approval remain separate from installation; see [compatibility](docs/compatibility.md).

## Catalog

Each catalog skill is independently installable from `skills/<name>/`. The linked entry point owns its full workflow and on-demand references.

| Skill | Use |
|---|---|
| [agent-scaffold](skills/agent-scaffold/) | Install, diagnose, or refresh a project-owned Claude Code + Codex harness. |
| [best-practice-research](skills/best-practice-research/) | Compare primary sources and trade-offs for a repository-specific technical recommendation. |
| [conventional-commit](skills/conventional-commit/) | Create a scoped local commit or message while preserving unrelated index state. |
| [deep-interview](skills/deep-interview/) | Resolve requirements into an approved specification; exact-file approval records are optional. |
| [domain-modeling](skills/domain-modeling/) | Define and evolve project terminology, context boundaries, and multilingual equivalents. |
| [lark-cli](skills/lark-cli/) | Perform selected 飞书/Feishu/Lark CLI operations with identity and side-effect safeguards. |
| [project-docs-organizer](skills/project-docs-organizer/) | Organize documentation, consolidate ownership, and repair navigation. |
| [semver-release](skills/semver-release/) | Analyze a version and complete an authorized repository-owned release. |
| [spec-writing](skills/spec-writing/) | Write or revise requirements/design documents while preserving settled meaning. |
| [tdd](skills/tdd/) | Perform user- or project-required test-first implementation with RED/GREEN evidence. |
| [tooling-conventions](skills/tooling-conventions/) | Design project-owned command boundaries, placement, and optional inventory checks. |
| [work-protocol](skills/work-protocol/) | Coordinate durable ownership, leases, CAS state, evidence, and isolated workspaces. |

The project skill `.agents/skills/skill-eval` and project subagent `skill-verifier` support this repository's own evaluations. Neither is a catalog install target.

## Documentation

| Need | Start here |
|---|---|
| Choose skills, combine them, or clean up retired installations | [Selection and composition](docs/skill-composition.md) |
| Understand catalog, harness, and source/generated ownership | [Architecture](docs/architecture.md) |
| Contribute, verify changes, regenerate, or release | [Development](docs/development.md) |
| Check installer behavior, host trust, and dated support evidence | [Compatibility](docs/compatibility.md) |
| Maintain documentation or design a skill | [Documentation maintenance](docs/documentation-maintenance.md) · [Harness principles](docs/harness-constraint-policy.md) |
| Measure routing decisions or actual task outcomes | [Routing probes](evals/agent-skills/README.md) · [Task outcomes](evals/tasks/README.md) |
| Work as a repository Agent | [AGENTS.md](AGENTS.md) · [Canonical terminology](CONTEXT.md) |
| Review pending changes and releases | [CHANGELOG.md](CHANGELOG.md) |

Historical audits are linked from the [maintenance guide](docs/documentation-maintenance.md#historical-records); they are not current operating instructions.

## License

MIT. Preserve any skill-specific attribution notices when redistributing its payload.
