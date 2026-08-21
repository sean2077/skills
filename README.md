# skills

Reusable agent skills for development, ops, and productivity — battle-tested patterns with working examples.

Uses the universal [Agent Skills specification](https://agentskills.io/specification). Compatible with Claude Code, Codex, OpenCode, Cursor, GitHub Copilot, Windsurf, and other Agent Skills hosts.

The minimal [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) is installer compatibility metadata: `npx skills` uses it to group the installed skills under **Sean2077 Skills** for every target agent.

## Install

Install only the workflows you expect an agent to discover. Every installed skill contributes routing metadata even though its full body, references, and scripts remain on demand.

```bash
# Recommended: install one skill for both Claude Code and Codex
npx skills add sean2077/skills --skill analyze -a claude-code -a codex

# Add a deterministic delivery workflow only where it is needed
npx skills add sean2077/skills --skill ralph -a claude-code -a codex

# Single-host examples
npx skills add sean2077/skills --skill code-review -a codex
npx skills add sean2077/skills --skill deep-interview -a claude-code

# Optional convenience: install the complete catalog
npx skills add sean2077/skills -a claude-code -a codex

# From a local checkout, keep the leading ./ so it is parsed as a path
npx skills add ./skills/agent-scaffold -a codex
```

Repeat the selective command for each additional skill. If skills were installed before the compatibility manifest existed, rerun a catalog-root `add` command once in the same project/global scope so `npx skills` records the group in its lockfile. For a local checkout, use `npx skills add . --skill agent-scaffold -a codex`; installing `./skills/agent-scaffold` directly bypasses the root manifest and therefore remains ungrouped.

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [agent-scaffold](skills/agent-scaffold/) | Apply or refresh a dual-host (Claude Code + Codex) harness: `.agents/` SSOT, mandatory real-symlink projections, merge-owned hooks, subagent projection, `default`/`light` governance profiles, and structured plan/doctor/verify output. | Shell, Python, Governance |
| [ai-slop-cleaner](skills/ai-slop-cleaner/) | Perform behavior-preserving, bounded cleanup of duplication, dead code, needless abstraction, boundary leaks, and weak coverage with explicit verification. | Engineering, Refactoring |
| [analyze](skills/analyze/) | Answer repository-local questions through read-only cross-file evidence, ranked synthesis, and explicit fact/inference/unknown boundaries. | Engineering, Analysis |
| [autopilot](skills/autopilot/) | Run explicit autonomous delivery through persistent phases, a required plan artifact, one bounded retry, compact receipts, and recoverable workspace-bound state. | Python, Delivery |
| [best-practice-research](skills/best-practice-research/) | Compare current primary sources and viable trade-offs to produce a repository-specific technical recommendation. | Research, Engineering |
| [code-review](skills/code-review/) | Perform an evidence-based defect review of a concrete change set, including regressions, security, maintainability, and verification gaps. | Engineering, Review |
| [conventional-commit](skills/conventional-commit/) | Create one scoped local Conventional Commit or return one history-aware message-only subject while preserving unrelated index state. | Git |
| [deep-interview](skills/deep-interview/) | Turn vague ideas into an approved specification with a Socratic interview, component×dimension scoring, deterministic gates, and explicit approval before completion. | Python, Requirements |
| [lark-cli](skills/lark-cli/) | Route all 飞书/Feishu/Lark operations through one lean `lark-cli` entry point with on-demand domain references, explicit identity continuity, command discovery, and side-effect safety. | Lark, CLI, Productivity |
| [project-docs-organizer](skills/project-docs-organizer/) | Derive project-owned documentation structure from reader, task, domain, ownership, lifecycle, and retrieval evidence; use optional sibling-local numbering only when stable order materially improves reader navigation. | Documentation |
| [prototype](skills/prototype/) | Reduce one uncertainty through a disposable, bounded experiment with explicit oracle, safety, conclusion, and cleanup boundaries. | Engineering, Experimentation |
| [ralph](skills/ralph/) | Run a bounded verifier loop until it passes, stalls, plateaus, or exhausts its round budget, with deterministic state and compact receipts. | Python, Iteration |
| [semver-release](skills/semver-release/) | Plan and publish a semver release with deterministic reachable-tag/bump analysis, a preferred changelog-backed tag workflow, project-owned version synchronization, and policy-derived publication verification. | Git, Python, Release |
| [tdd](skills/tdd/) | Apply explicitly requested test-first implementation across stacks by deriving seams, oracles, test levels, and commands from the target project, with validated RED-GREEN-REFACTOR evidence and guidance for effects, legacy code, and hard cases. | Engineering, Testing |
| [tooling-conventions](skills/tooling-conventions/) | Derive project-owned command boundaries, placement, and evidence-gated safety contracts, with optional structural inventory reconciliation. | Shell, Governance |
| [trace](skills/trace/) | Investigate failures through read-only causal evidence, competing hypotheses, falsification, and one discriminating probe. | Engineering, Debugging |

## Structure

```
skills/
└── <name>/
    ├── SKILL.md            # Single source of truth for every installer
    ├── references/         # Optional: category-named, on-demand detail (no catch-all document)
    │   └── <category>.md
    └── scripts/ / assets/  # Optional: deterministic helpers and output resources
scripts/
├── validate_skills.py       # Catalog-wide frontmatter, name↔dir, README, reference, and placeholder checks
├── catalog_core.py          # Shared error/warning collection and repository path constants
├── contracts/               # One semantic contract module per skill, discovered by filename
│   └── <skill>.py
├── workflow_runtime/        # Maintainer SSOT for common + workflow-specific deterministic runtime code
│   ├── common.py
│   ├── autopilot.py
│   ├── deep_interview.py
│   └── ralph.py
├── generate_workflow_runtimes.py # Generates/checks each independently installable single-file runtime
├── test_validate_skills.py  # Focused catalog-contract regression fixtures
├── tests/                    # Behavioral and adversarial skill-specific regressions
├── check-agent-scaffold.sh  # agent-scaffold static gate: syntax + install-depth invariant + dogfood drift
└── e2e-agent-scaffold.sh    # agent-scaffold behavioral gate: install into a throwaway repo, assert it works
requirements-validation.txt  # Pinned official skills-ref + StrictYAML validation dependency
.claude-plugin/
└── plugin.json              # npx skills grouping metadata, kept in sync by the validator
.github/workflows/
└── validate.yml             # Cross-platform catalog, runtime, install, shell, and behavioral gates
```

`autopilot`, `deep-interview`, and `ralph` each ship one generated, Python 3.8+ standard-library script. Installing a single skill therefore creates no sibling-skill, repository-runtime, or OMA CLI dependency. Maintainers edit `scripts/workflow_runtime/`, run `python scripts/generate_workflow_runtimes.py`, and let CI reject generated drift.

The runtime scripts emit compact versioned receipts by default. Full state is opt-in through `--full`; history is bounded through `history --tail`; discovery is bounded through `list --limit`. Git repositories share discovery across worktrees while preserving explicit mutation ownership. Non-Git workspaces use a stable `--root`.

Reference filenames are descriptive lowercase kebab-case. Link every category directly under the resident `SKILL.md` `On-demand references` router, and state its conditional load boundary near the top. Do not add root-level `reference.md` files or catch-alls such as `misc.md`, `all.md`, or `references/README.md`.

`npx skills` reads directly from `skills/`, so this repository does not maintain separate `.codex/skills` or `.claude/skills` mirrors.

## Development and releases

Run the catalog's pinned validation, official spec, discovery, deterministic runtime, shell, and behavioral gates from the [development commands](AGENTS.md#development-commands). Release-facing changes accumulate in the [changelog](CHANGELOG.md). After the release snapshot is merged and validated on `main`, an annotated stable or numbered-prerelease `v` tag triggers the repository-owned release workflow. It reruns the complete validation workflow, extracts the exact matching changelog section from the tagged commit, and creates a GitHub Release only after both steps succeed.

## License

MIT
