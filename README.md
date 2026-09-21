# skills

A curated catalog of 13 reusable [Agent Skills](https://agentskills.io/specification) for software delivery, analysis, repository operations, and productivity.

Each installed skill contributes discovery metadata; its instructions and bundled resources are loaded when needed. Format validation, installer discovery, host wiring, and runtime behavior are separate claims—see the [compatibility matrix](docs/compatibility.md).

## Install

```bash
# One skill for the Claude Code and Codex targets
npx skills add sean2077/skills --skill tdd -a claude-code -a codex

# Complete catalog
npx skills add sean2077/skills --skill '*' -a claude-code -a codex

# One skill from a local catalog checkout; keep the catalog root as the source
npx skills add . --skill agent-scaffold -a codex
```

Repeat `--skill` and `-a` for selective installs. Use an explicit local prefix when installing a skill directory directly, for example `./skills/agent-scaffold`. The [installer section of the compatibility matrix](docs/compatibility.md#installer-semantics) owns option scope, catalog-root behavior, and the audited CLI pin.

Check the dated [native overlap notes](docs/compatibility.md#native-overlap-and-visibility-2026-09-20) for host-specific naming and discovery behavior before choosing routes.

## Catalog

Repository analysis, disposable experiments, general cleanup, code review, and ordinary delivery use the host or project's workflow rather than separate catalog skills. See [installation cleanup](docs/skill-composition.md#installation-and-evidence) for previously installed entries.

Use the [selection and composition guide](docs/skill-composition.md) to distinguish adjacent routes without loading a whole workflow chain.

| Skill | Description | Stack |
|-------|-------------|-------|
| [agent-scaffold](skills/agent-scaffold/) | Apply or refresh a dual-host (Claude Code + Codex) harness: `.agents/` SSOT, mandatory real-symlink projections, reconciled host hooks, subagent projection, lean authority and terminology contracts, repository LF/CRLF defaults, `default`/`light` governance profiles, and structured plan/doctor/verify output. | Shell, Python, Governance |
| [best-practice-research](skills/best-practice-research/) | Compare current primary sources and viable trade-offs to produce a repository-specific technical recommendation. | Research, Engineering |
| [conventional-commit](skills/conventional-commit/) | Create one scoped local Conventional Commit or return one history-aware message-only subject while preserving unrelated index state. | Git |
| [deep-interview](skills/deep-interview/) | Turn unresolved requirements into an approved specification through an adaptive interview, with optional revision-bound, exact-file approval records. | Python, Requirements |
| [domain-modeling](skills/domain-modeling/) | Actively define, challenge, group, split, and migrate project terminology with user-selectable up-front or incremental modeling, evidence-backed context boundaries, multilingual canonical equivalents, and atomic `CONTEXT.md`/`CONTEXT-MAP.md` evolution. | Domain Modeling, Documentation |
| [lark-cli](skills/lark-cli/) | Handle selected 飞书/Feishu/Lark CLI operations through one lean `lark-cli` entry point with on-demand domain references, explicit identity continuity, command discovery, and side-effect safety. | Lark, CLI, Productivity |
| [project-docs-organizer](skills/project-docs-organizer/) | Derive project-owned documentation structure from reader, task, domain, ownership, lifecycle, and retrieval evidence; use optional sibling-local numbering only when stable order materially improves reader navigation. | Documentation |
| [ralph](skills/ralph/) | Use a deterministic bounded verifier loop only when fixed attempts and mechanical pass, stall, plateau, exhaustion, or resume state are part of the task boundary. | Python, Iteration |
| [semver-release](skills/semver-release/) | Plan and publish a semver release with deterministic reachable-tag/bump analysis, a preferred changelog-backed tag workflow, project-owned version synchronization, and policy-derived publication verification. | Git, Python, Release |
| [spec-writing](skills/spec-writing/) | Write or revise human-facing requirements and design documents, compare unresolved material options, preserve settled meaning, clarify authority and acceptance, and separate working history from the reader narrative. | Documentation, Requirements |
| [tdd](skills/tdd/) | Apply user- or project-required test-first implementation across stacks by deriving seams, oracles, test levels, and commands from the target project, with validated RED-GREEN-REFACTOR evidence and guidance for effects, legacy code, and hard cases. | Engineering, Testing |
| [tooling-conventions](skills/tooling-conventions/) | Derive project-owned command boundaries, placement, and evidence-gated safety contracts, with optional structural inventory reconciliation. | Shell, Governance |
| [work-protocol](skills/work-protocol/) | Provide durable owner leases, CAS state, compact evidence receipts, and isolated writers/review snapshots without prescribing caller phases or roles. | Python, Git, Coordination |

Each selected catalog skill is independently installable from `skills/<name>/`. The project-private `.agents/skills/skill-eval` workflow is used by this repository's harness and is not a public install target.

## Repository map

| Path | Purpose |
|---|---|
| `skills/` | Published catalog source consumed by installers. |
| `.agents/` | This repository's private, dogfooded Claude Code + Codex harness. |
| `scripts/` | Validators, generators, contracts, tests, and scaffold tooling. |
| `evals/` | Offline examples and live-host routing-suite manifests. |
| `docs/` | Architecture, contributor workflow, compatibility, and policy. |
| `.github/workflows/` | Cross-platform validation and release automation. |

The catalog is read directly from `skills/`; there are no generated `.claude/skills` or `.codex/skills` mirrors for published skills. See [repository architecture](docs/architecture.md) for source/generated ownership and the private-harness boundary.

## Documentation

| Need | Canonical page |
|---|---|
| Understand product surfaces, source ownership, generators, and validation layers | [Repository architecture](docs/architecture.md) |
| Develop, validate, regenerate, and release | [Development guide](docs/development.md) |
| Check host, installer, trust, and support claims | [Compatibility and verification matrix](docs/compatibility.md) |
| Maintain documentation and evidence freshness | [Documentation maintenance](docs/documentation-maintenance.md) |
| Decide when mechanical controls justify their cost | [Harness design principles](docs/harness-constraint-policy.md) |
| Use the repository's canonical terminology, context grouping, language equivalents, and avoided names | [Project language](CONTEXT.md) |
| Follow repository-level Agent rules | [Agent contract](AGENTS.md) |
| Review historical native-first findings and evidence | [2026-09-20 audit](docs/audits/2026-09-20-native-first.md) |
| Review release history and pending changes | [Changelog](CHANGELOG.md) |

## License

MIT
