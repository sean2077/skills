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

# From a local checkout, keep the leading ./ so it is parsed as a path
npx skills add ./skills/agent-scaffold -a codex
```

If the skills were installed before the compatibility manifest existed, rerun the catalog-root `add` command once in the same project/global scope so `npx skills` records the group in its lockfile. For a local checkout, use `npx skills add . --skill agent-scaffold -a codex`; installing `./skills/agent-scaffold` directly bypasses the root manifest and therefore remains ungrouped.

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [conventional-commit](skills/conventional-commit/) | Create one scoped local Conventional Commit or return one history-aware message-only subject while preserving unrelated index state. | Git |
| [semver-release](skills/semver-release/) | Plan and publish a semver release with deterministic reachable-tag/bump analysis, project-owned version synchronization, and verified CI or direct forge publication. | Git, Python, Release |
| [project-docs-organizer](skills/project-docs-organizer/) | Derive project-owned documentation structure from reader, task, domain, ownership, lifecycle, and retrieval evidence; use optional default-on local numbering only when no coherent convention governs. | Documentation |
| [tooling-conventions](skills/tooling-conventions/) | Govern committed command surfaces with project-owned placement, failure-domain boundaries, safe script contracts, and optional manifest reconciliation. | Shell, Governance |
| [agent-scaffold](skills/agent-scaffold/) | Apply or refresh a dual-host (Claude Code + Codex) harness: `.agents/` SSOT, mandatory real-symlink projections, merge-owned hooks, subagent projection, `default`/`light` governance profiles, and structured plan/doctor/verify output. | Shell, Python, Governance |

## Structure

```
skills/
└── <name>/
    ├── SKILL.md            # Single source of truth for every installer
    ├── references/         # Optional: category-named, on-demand detail (no catch-all document)
    │   └── <category>.md
    └── scripts/ / assets/  # Optional: deterministic helpers and output resources
scripts/
├── validate_skills.py       # Catalog check: frontmatter, name↔dir, README + reference links, allowed-tools, placeholders
├── test_validate_skills.py  # Focused fixtures for category reference routing and naming
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
the [changelog](CHANGELOG.md); the repository's SemVer workflow owns the final version, tag, and
forge publication.

## License

MIT
