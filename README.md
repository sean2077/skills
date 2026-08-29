# skills

A curated catalog of 17 reusable [Agent Skills](https://agentskills.io/specification) for software delivery, analysis, repository operations, and productivity.

Install only the routes you expect an agent to discover. Each installed skill contributes discovery metadata; its full instructions and bundled resources are loaded only when needed. Format validation, installer discovery, host wiring, and runtime behavior are separate claims—see the [compatibility matrix](docs/compatibility.md).

## Install

```bash
# One skill for the Claude Code and Codex targets
npx skills add sean2077/skills --skill analyze -a claude-code -a codex

# Complete catalog for only these two targets
npx skills add sean2077/skills --skill '*' -a claude-code -a codex

# One skill from a local catalog checkout; keep the catalog root as the source
npx skills add . --skill agent-scaffold -a codex
```

Repeat `--skill` and `-a` for selective installs. Use an explicit local prefix when installing a skill directory directly, for example `./skills/agent-scaffold`. The [installer section of the compatibility matrix](docs/compatibility.md#installer-semantics) owns option scope, catalog-root behavior, and the audited CLI pin.

## Catalog

| Skill | Description | Stack |
|-------|-------------|-------|
| [agent-scaffold](skills/agent-scaffold/) | Apply or refresh a dual-host (Claude Code + Codex) harness: `.agents/` SSOT, mandatory real-symlink projections, reconciled host hooks, subagent projection, lean authority and terminology contracts, `default`/`light` governance profiles, and structured plan/doctor/verify output. | Shell, Python, Governance |
| [ai-slop-cleaner](skills/ai-slop-cleaner/) | Perform behavior-preserving, bounded cleanup of duplication, dead code, needless abstraction, boundary leaks, and weak coverage with explicit verification. | Engineering, Refactoring |
| [analyze](skills/analyze/) | Explain repository behavior or investigate failures through one read-only evidence workflow with ranked synthesis, competing hypotheses, falsification, and discriminating probes. | Engineering, Analysis |
| [autopilot](skills/autopilot/) | Deliver authorized work end to end with a proportional native loop, selective bounded delegation, and persistent state only when explicit resume, handoff, revision, or audit semantics add value. | Python, Delivery |
| [best-practice-research](skills/best-practice-research/) | Compare current primary sources and viable trade-offs to produce a repository-specific technical recommendation. | Research, Engineering |
| [code-review](skills/code-review/) | Perform an evidence-based defect review of a concrete change set, including regressions, security, maintainability, and verification gaps. | Engineering, Review |
| [conventional-commit](skills/conventional-commit/) | Create one scoped local Conventional Commit or return one history-aware message-only subject while preserving unrelated index state. | Git |
| [deep-interview](skills/deep-interview/) | Turn vague ideas into an explicitly approved specification through an adaptive interview, with opt-in deterministic topology/scoring state for persistent or auditable sessions. | Python, Requirements |
| [lark-cli](skills/lark-cli/) | Route all 飞书/Feishu/Lark operations through one lean `lark-cli` entry point with on-demand domain references, explicit identity continuity, command discovery, and side-effect safety. | Lark, CLI, Productivity |
| [project-docs-organizer](skills/project-docs-organizer/) | Derive project-owned documentation structure from reader, task, domain, ownership, lifecycle, and retrieval evidence; use optional sibling-local numbering only when stable order materially improves reader navigation. | Documentation |
| [prototype](skills/prototype/) | Reduce one uncertainty through a disposable, bounded experiment with explicit oracle, safety, conclusion, and cleanup boundaries. | Engineering, Experimentation |
| [ralph](skills/ralph/) | Use a deterministic bounded verifier loop only when fixed attempts and mechanical pass, stall, plateau, exhaustion, or resume state are part of the task boundary. | Python, Iteration |
| [semver-release](skills/semver-release/) | Plan and publish a semver release with deterministic reachable-tag/bump analysis, a preferred changelog-backed tag workflow, project-owned version synchronization, and policy-derived publication verification. | Git, Python, Release |
| [spec-writing](skills/spec-writing/) | Write or revise human-facing requirements and design documents, compare material implementation options, preserve settled meaning, clarify authority and acceptance, and separate working history from the reader narrative. | Documentation, Requirements |
| [tdd](skills/tdd/) | Apply explicitly requested test-first implementation across stacks by deriving seams, oracles, test levels, and commands from the target project, with validated RED-GREEN-REFACTOR evidence and guidance for effects, legacy code, and hard cases. | Engineering, Testing |
| [tooling-conventions](skills/tooling-conventions/) | Derive project-owned command boundaries, placement, and evidence-gated safety contracts, with optional structural inventory reconciliation. | Shell, Governance |
| [work-protocol](skills/work-protocol/) | Externalize coordination only when durable ownership, CAS state, evidence integrity, isolated writers, or commit-fixed review materially matter. | Python, Git, Coordination |

Each selected catalog skill is independently installable from `skills/<name>/`. The project-private `.agents/skills/skill-eval` workflow is used by this repository's harness and is not a public install target. The former `trace` route has moved into `analyze`; remove stale `trace` projections after upgrading.

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
| Maintain documentation and evidence freshness | [Documentation maintenance policy](docs/documentation-maintenance.md) |
| Decide when mechanical controls justify their cost | [Harness constraint policy](docs/harness-constraint-policy.md) |
| Use the repository's canonical terminology, language equivalents, and avoided names | [Project language](CONTEXT.md) |
| Follow repository-level Agent rules | [Agent contract](AGENTS.md) |
| Review release history and pending changes | [Changelog](CHANGELOG.md) |

## License

MIT
