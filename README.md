# skills

Reusable agent skills for development, ops, and productivity — battle-tested patterns with working examples.

Publishes 16 reusable workflows in the open [Agent Skills format](https://agentskills.io/specification). Format conformance, installer discovery, and host runtime support are separate claims: CI runs the pinned official validator across the catalog, smoke-tests discovery with an audited `skills` CLI version, and exercises the repository's Claude Code + Codex scaffold installer and projections. An installer listing another target does not by itself mean this repository has certified that host.

The minimal [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) is catalog metadata used by the repository's tested installer-discovery flow. It declares the catalog name and 16 published skill paths to that flow; it is not a declaration of native runtime compatibility for every installer target. See the [compatibility and verification matrix](docs/compatibility.md).

## Install

Install only the workflows you expect an agent to discover. Every installed skill contributes routing metadata even though its full body, references, and scripts remain on demand.

```bash
# Recommended: install one skill for both Claude Code and Codex
npx skills add sean2077/skills --skill analyze -a claude-code -a codex

# Add a deterministic bounded verifier loop only when mechanical stop state is needed
npx skills add sean2077/skills --skill ralph -a claude-code -a codex

# Single-host examples
npx skills add sean2077/skills --skill code-review -a codex
npx skills add sean2077/skills --skill deep-interview -a claude-code

# Optional: install the complete catalog for these two targets
npx skills add sean2077/skills --skill '*' -a claude-code -a codex

# From a local checkout, keep the leading ./ so it is parsed as a path
npx skills add ./skills/agent-scaffold -a codex
```

Repeat the selective command for each additional skill. With the current `skills` CLI, omitting `--skill` opens selection; quote `'*'` to select every skill for only the explicitly named `-a` targets. `--all` has broader semantics: every discovered skill to every supported agent. Use the catalog root when catalog metadata matters: for a local checkout run `npx skills add . --skill agent-scaffold -a codex`; installing `./skills/agent-scaffold` directly selects that skill directory and bypasses root catalog metadata.

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [agent-scaffold](skills/agent-scaffold/) | Apply or refresh a dual-host (Claude Code + Codex) harness: `.agents/` SSOT, mandatory real-symlink projections, reconciled host hooks, subagent projection, `default`/`light` governance profiles, and structured plan/doctor/verify output. | Shell, Python, Governance |
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
| [tdd](skills/tdd/) | Apply explicitly requested test-first implementation across stacks by deriving seams, oracles, test levels, and commands from the target project, with validated RED-GREEN-REFACTOR evidence and guidance for effects, legacy code, and hard cases. | Engineering, Testing |
| [tooling-conventions](skills/tooling-conventions/) | Derive project-owned command boundaries, placement, and evidence-gated safety contracts, with optional structural inventory reconciliation. | Shell, Governance |
| [work-protocol](skills/work-protocol/) | Externalize coordination only when durable ownership, CAS state, evidence integrity, isolated writers, or commit-fixed review materially matter. | Python, Git, Coordination |

## Structure

```
skills/
└── <name>/
    ├── SKILL.md            # Single source of truth for every installer
    ├── references/         # Optional: category-named, on-demand detail (no catch-all document)
    │   └── <category>.md
    └── scripts/ / assets/  # Optional: deterministic helpers and output resources
.agents/skills/skill-eval/  # Project-private evaluation skill, reference, and generated runtime
scripts/
├── catalog_health.py        # Resident route budget, duplicate-route, and payload-entry-type gate
├── test_catalog_health.py   # Focused catalog-health regression fixtures
├── validate_skills.py       # Catalog-wide frontmatter, name↔dir, README, reference, and placeholder checks
├── catalog_core.py          # Shared error/warning collection and repository path constants
├── contracts/               # Optional targeted executable/high-risk contracts, discovered by filename
│   └── <skill>.py
├── workflow_runtime/        # Maintainer SSOT for common + workflow-specific deterministic runtime code
│   ├── common.py
│   ├── autopilot.py
│   ├── deep_interview.py
│   └── ralph.py
├── generate_workflow_runtimes.py # Generates/checks each independently installable single-file runtime
├── p0_runtime/              # Maintainer SSOT for private skill-eval and public work-protocol runtimes
├── generate_p0_runtimes.py  # Generates/checks the private/public P0 skill runtime payloads
├── test_validate_skills.py  # Focused catalog-contract regression fixtures
├── tests/                    # Behavioral and adversarial skill-specific regressions
├── check-agent-scaffold.sh  # agent-scaffold static gate: syntax + install-depth invariant + dogfood drift
└── e2e-agent-scaffold.sh    # agent-scaffold behavioral gate: install into a throwaway repo, assert it works
evals/examples/tdd/         # Offline positive/negative/confusable skill-eval example
evals/agent-skills/         # Live analyze/autopilot/deep-interview routing suites; CI validates manifests only
requirements-validation.txt  # Pinned official skills-ref + StrictYAML validation dependency
.claude-plugin/
└── plugin.json              # npx skills grouping metadata, kept in sync by the validator
.github/workflows/
└── validate.yml             # Cross-platform catalog, runtime, install, shell, and behavioral gates
```

`autopilot`, `deep-interview`, and `ralph` each ship one generated, Python 3.8+ standard-library script. The `autopilot` and `deep-interview` runtimes are opt-in persistence/control planes; ordinary single-session delivery and interviewing stay model-native. `ralph` uses its runtime as the normal bounded verifier loop. Installing a single skill creates no sibling-skill, repository-runtime, or OMA CLI dependency. Maintainers edit `scripts/workflow_runtime/`, run `python scripts/generate_workflow_runtimes.py`, and let CI reject generated drift.
`skill-eval` is a project-private harness skill under `.agents/skills/skill-eval`; it is available to this repository's trusted Codex and Claude Code project layers but is not published through the catalog. `work-protocol` remains an independently installable catalog skill. Both use generated Python 3.8+ standard-library packages: maintainers edit `scripts/p0_runtime/`, run `python scripts/generate_p0_runtimes.py`, and validate the offline TDD A/B fixture plus the P0 behavioral/adversarial suites before committing.

Use model-native reasoning for reversible single-session work. Select execution topology and durable state independently: one Agent is the default; ephemeral host subagents are for bounded independent work with compact returns; project-owned subagents require a repeated stable role; and a host durable goal should precede a persistence runtime unless explicit machine-state semantics add value. The primary Agent owns integration and final verification, and each mutable surface has one active writer at a time. Add deterministic scripts only around machine state or costly machine-checkable boundaries such as external side effects, Git/release integrity, concurrency/CAS, path and identity safety, generated drift, or comparable evaluation. Targeted per-skill contract modules are optional; the reviewed high-risk subset is registered so accidental deletion fails validation, while prompt-only semantics belong in `SKILL.md` and live evaluations rather than brittle phrase checks. See the [harness constraint policy](docs/harness-constraint-policy.md).

Catalog health treats each frontmatter description as always-resident routing context: it must fit a 320-character, one-line budget, and normalized duplicate routes fail validation. Published skill trees may contain only regular files and directories, so the real-installer inventory cannot silently omit a symlink or special entry.

The former `trace` route is now the causal-investigation mode of `analyze`. Existing installations should replace `trace` with `analyze` and remove any stale `trace` projection to avoid duplicate routing.

The runtime scripts emit compact versioned receipts by default. Full state is opt-in through `--full`; history is bounded through `history --tail`; discovery is bounded through `list --limit`. Git repositories share discovery across worktrees while preserving explicit mutation ownership. Non-Git workspaces use a stable `--root`.

Reference filenames are descriptive lowercase kebab-case. Link every category directly under the resident `SKILL.md` `On-demand references` router, and state its conditional load boundary near the top. Do not add root-level `reference.md` files or catch-alls such as `misc.md`, `all.md`, or `references/README.md`.

`npx skills` reads the published payload directly from `skills/`, so this repository does not maintain generated `.codex/skills` or `.claude/skills` catalog mirrors. The separate `.agents/skills/` tree belongs to this repository's own dogfooded project harness, currently contains the private `skill-eval` workflow, and is not part of the published catalog.

## Documentation map

- [Compatibility and verification matrix](docs/compatibility.md) — what is format-validated, installer-tested, host-wired, or explicitly not certified.
- [Documentation maintenance policy](docs/documentation-maintenance.md) — ownership, evidence, freshness, duplication, and command-example rules.
- [Harness constraint policy](docs/harness-constraint-policy.md) — when mechanical controls earn their complexity.
- [Agent contract](AGENTS.md) — maintainer commands, architecture, and release boundary.
- [Changelog](CHANGELOG.md) — release history; historical entries are not silently rewritten to match later behavior.

## Development and releases

Run the catalog's pinned validation, official spec, discovery, deterministic runtime, shell, and behavioral gates from the [development commands](AGENTS.md#development-commands). The repository intentionally distinguishes a CI-audited dependency pin from the upstream latest release; see the [compatibility matrix](docs/compatibility.md) before changing either wording or version. Release-facing changes accumulate in the [changelog](CHANGELOG.md). After the release snapshot is merged and validated on `main`, an annotated stable or numbered-prerelease `v` tag triggers the repository-owned release workflow. It reruns the complete validation workflow, extracts the exact matching changelog section from the tagged commit, and creates a GitHub Release only after both steps succeed.

## License

MIT
