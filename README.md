# skills

Reusable agent skills for development, ops, and productivity — battle-tested patterns with working examples.

Uses the universal [Agent Skills specification](https://agentskills.io/specification). Compatible with Claude Code, Codex, OpenCode, Cursor, GitHub Copilot, Windsurf, and other Agent Skills hosts.

The minimal [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) is installer compatibility metadata: `npx skills` uses it to group the installed skills under **Sean2077 Skills** for every target agent.

## Install

```bash
# Recommended: one install flow for both Claude Code and Codex
npx skills add sean2077/skills -a claude-code -a codex

# Codex only
npx skills add sean2077/skills -a codex

# Claude Code only
npx skills add sean2077/skills -a claude-code

# Install one skill from this catalog
npx skills add sean2077/skills --skill agent-scaffold -a codex

# Install an independently runnable workflow skill for both primary hosts
npx skills add sean2077/skills --skill ralph -a claude-code -a codex

# From a local checkout, keep the leading ./ so it is parsed as a path
npx skills add ./skills/agent-scaffold -a codex
```

If the skills were installed before the compatibility manifest existed, rerun the catalog-root `add` command once in the same project/global scope so `npx skills` records the group in its lockfile. For a local checkout, use `npx skills add . --skill agent-scaffold -a codex`; installing `./skills/agent-scaffold` directly bypasses the root manifest and therefore remains ungrouped.

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [agent-scaffold](skills/agent-scaffold/) | Apply or refresh a dual-host (Claude Code + Codex) harness: `.agents/` SSOT, mandatory real-symlink projections, merge-owned hooks, subagent projection, `default`/`light` governance profiles, and structured plan/doctor/verify output. | Shell, Python, Governance |
| [ai-slop-cleaner](skills/ai-slop-cleaner/) | Simplify behaviorally correct duplication, dead code, needless abstraction, boundary leaks, and weak coverage with a verifier-backed, deletion-first workflow. | Engineering, Refactoring |
| [analyze](skills/analyze/) | Answer repository-local questions through read-only cross-file evidence and a ranked fact/inference/unknown synthesis. | Engineering, Analysis |
| [autopilot](skills/autopilot/) | Drive an authorized task from clarification through verified delivery with a skill-local, interruption-safe phase runtime. | Engineering, Workflow, Python |
| [best-practice-research](skills/best-practice-research/) | Compare current primary-source practice and translate it into a repository-specific technical recommendation. | Research, Engineering |
| [code-review](skills/code-review/) | Review a concrete change set for actionable correctness, regression, security, maintainability, and verification defects. | Engineering, Review |
| [conventional-commit](skills/conventional-commit/) | Create one scoped local Conventional Commit or return one history-aware message-only subject while preserving unrelated index state. | Git |
| [deep-interview](skills/deep-interview/) | Turn a vague idea into an approval-ready specification with deterministic scoring, ambiguity, rotation, binding, and resume state. | Product, Workflow, Python |
| [lark-cli](skills/lark-cli/) | Route all 飞书/Feishu/Lark operations through one lean `lark-cli` entry point with on-demand domain references, explicit identity continuity, command discovery, and side-effect safety. | Lark, CLI, Productivity |
| [project-docs-organizer](skills/project-docs-organizer/) | Derive project-owned documentation structure from reader, task, domain, ownership, lifecycle, and retrieval evidence; use optional sibling-local numbering only when stable order materially improves reader navigation. | Documentation |
| [prototype](skills/prototype/) | Reduce one named uncertainty with a disposable, bounded experiment and an explicit evidence, promotion, and cleanup boundary. | Engineering, Experimentation |
| [ralph](skills/ralph/) | Iterate toward a verifier-backed goal with deterministic pass, stall, plateau, exhaustion, revision, and resume judgment. | Engineering, Workflow, Python |
| [semver-release](skills/semver-release/) | Plan and publish a semver release with deterministic reachable-tag/bump analysis, a preferred changelog-backed tag workflow, project-owned version synchronization, and policy-derived publication verification. | Git, Python, Release |
| [tdd](skills/tdd/) | Apply explicitly requested test-first implementation across stacks by deriving seams, oracles, test levels, and commands from the target project, with validated RED-GREEN-REFACTOR evidence and guidance for effects, legacy code, and hard cases. | Engineering, Testing |
| [tooling-conventions](skills/tooling-conventions/) | Derive project-owned command boundaries, placement, and evidence-gated safety contracts, with optional structural inventory reconciliation. | Shell, Governance |
| [trace](skills/trace/) | Investigate symptoms read-only through a confirmed observation loop, competing causal hypotheses, falsification, and one discriminating probe. | Engineering, Debugging |

## Structure

```
skills/
└── <name>/
    ├── SKILL.md            # Single source of truth for every installer
    ├── references/         # Optional: category-named, on-demand detail (no catch-all document)
    │   └── <category>.md
    └── scripts/ / assets/  # Optional: deterministic helpers and output resources
scripts/
├── validate_skills.py       # Catalog-wide check: frontmatter, name↔dir, README + reference links, allowed-tools, placeholders
├── catalog_core.py          # Shared error/warning collection and repository path constants
├── contracts/               # One module per skill: its semantic contract, discovered by filename
│   └── <skill>.py
├── test_validate_skills.py  # Focused catalog-contract regression fixtures
├── tests/                    # Focused regression suites and fixtures for skill-specific behavior
├── check-agent-scaffold.sh  # agent-scaffold static gate: syntax + install-depth invariant + dogfood drift
└── e2e-agent-scaffold.sh    # agent-scaffold behavioral gate: install into a throwaway repo, assert it works
requirements-validation.txt  # pinned official skills-ref + StrictYAML validation dependency
.claude-plugin/
└── plugin.json             # npx skills grouping metadata, kept in sync by the validator
.github/workflows/
└── validate.yml            # Runs the checks on push / PR
```

Reference filenames are descriptive lowercase kebab-case. Link every category directly under the
resident `SKILL.md` `On-demand references` router, and state its conditional load boundary near
the top. Do not add root-level `reference.md` files or catch-alls such as `misc.md`, `all.md`, or
`references/README.md`.

`npx skills` reads directly from `skills/`, so this repository does not maintain separate `.codex/skills` or `.claude/skills` mirrors.

## Development and releases

Run the catalog's pinned validation, official spec, discovery, shell, and behavioral gates from
the [development commands](AGENTS.md#development-commands). Release-facing changes accumulate in
the [changelog](CHANGELOG.md). After the release snapshot is merged and validated on `main`, an
annotated stable or numbered-prerelease `v` tag triggers the repository-owned release workflow.
It reruns the complete validation workflow, extracts the exact matching changelog section from
the tagged commit, and creates a GitHub Release only after both steps succeed.

## License

MIT
