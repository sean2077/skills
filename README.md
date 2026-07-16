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
| [conventional-commit](skills/conventional-commit/) | Generate a Conventional Commits message using the repository's historical language convention, defaulting to English when unclear, and create one local commit when requested. | Git |
| [semver-release](skills/semver-release/) | Cut a semver release from conventional commits: infer the bump, update CHANGELOG + version file, tag, then hand off to tag-triggered release CI (or publish a GitHub/GitLab release directly). | Git, Release |
| [project-docs-organizer](skills/project-docs-organizer/) | Build or reorganize project documentation systems: README-only for simple projects, major/subcategory numbered docs zones for complex projects. | Documentation |
| [tooling-conventions](skills/tooling-conventions/) | Govern a project's `tools/`/`scripts/` directory at scale: surface taxonomy, failure-domain aggregation, placement tree, script contract, and a reconciliation-checked surface manifest. Ships `manifest-check.sh`. | Shell, Governance |
| [agent-scaffold](skills/agent-scaffold/) | Install or retrofit a dual-host (Claude Code + Codex) agent harness: `.agents/` SSOT with mandatory real symlink projections, AGENTS.md/format/subagent governance, and a default-on worktree + trunk-guard workflow that lighter projects can omit with `--no-worktree`. Includes a preflight `doctor`; unsupported symlink hosts fail before mutation and never receive copy fallbacks. | Shell, Python, Governance |

## Structure

```
skills/
└── <name>/
    ├── SKILL.md            # Single source of truth for every installer
    ├── references/         # Optional: category-named, on-demand detail (no catch-all document)
    │   └── <category>.md
    └── *.sh / templates/   # Optional: scripts/templates a skill ships (agent-scaffold, tooling-conventions)
scripts/
├── validate_skills.py       # Catalog check: frontmatter, name↔dir, README + reference links, allowed-tools, placeholders
├── test_validate_skills.py  # Focused fixtures for category reference routing and naming
├── check-agent-scaffold.sh  # agent-scaffold static gate: syntax + install-depth invariant + dogfood drift
└── e2e-agent-scaffold.sh    # agent-scaffold behavioral gate: install into a throwaway repo, assert it works
requirements-validation.txt  # pinned official skills-ref + StrictYAML validation dependency
.claude-plugin/
└── plugin.json             # npx skills grouping metadata, kept in sync by the validator
.github/workflows/
└── validate.yml            # Runs the checks on push / PR
```

Reference filenames are descriptive lowercase kebab-case. Link every category directly from its
resident `SKILL.md`; do not add root-level `reference.md` files or catch-alls such as `misc.md`,
`all.md`, or `references/README.md`.

`npx skills` reads directly from `skills/`, so this repository does not maintain separate `.codex/skills` or `.claude/skills` mirrors.

## License

MIT
