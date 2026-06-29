# skills

Reusable agent skills for development, ops, and productivity — battle-tested patterns with working examples.

Uses the universal [SKILL.md](https://github.com/anthropics/skills) format. Compatible with Claude Code, Codex, OpenCode, Cursor, GitHub Copilot, Windsurf, and other agents supporting the Agent Skills spec.

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

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [conventional-commit](skills/conventional-commit/) | Generate a Conventional Commits message using the repository's historical language convention, defaulting to English when unclear, and create one local commit when requested. | Git |
| [semver-release](skills/semver-release/) | Cut a semver release from conventional commits: infer the bump, update CHANGELOG + version file, tag, then hand off to tag-triggered release CI (or publish a GitHub/GitLab release directly). | Git, Release |
| [project-docs-organizer](skills/project-docs-organizer/) | Build or reorganize project documentation systems: README-only for simple projects, major/subcategory numbered docs zones for complex projects. | Documentation |
| [tooling-conventions](skills/tooling-conventions/) | Govern a project's `tools/`/`scripts/` directory at scale: surface taxonomy, failure-domain aggregation, placement tree, script contract, and a reconciliation-checked surface manifest. Ships `manifest-check.sh`. | Shell, Governance |
| [agent-scaffold](skills/agent-scaffold/) | Install or retrofit the full dual-host (Claude Code + Codex) agent harness into a project: `.agents/` single-source-of-truth layout, worktree-per-change flow + trunk-edit guard, AGENTS.md line-budget + format-on-edit hooks, `CLAUDE.md`→`AGENTS.md` contract + a parent-linked nested AGENTS.md tree, and (Node) a subagent generator + pre-commit drift guard. One idempotent, merge-aware installer (`harness-init.sh`); coexists with `npx skills` for third-party skills. | Shell, Node, Governance |

## Structure

```
skills/
└── <name>/
    ├── SKILL.md            # Single source of truth for every installer
    ├── reference.md        # Optional: on-demand detail kept out of the resident skill body
    └── *.sh / templates/   # Optional: scripts/templates a skill ships (agent-scaffold, tooling-conventions)
scripts/
├── validate_skills.py       # Catalog check: frontmatter, name↔dir, README + reference links, allowed-tools, placeholders
├── check-agent-scaffold.sh  # agent-scaffold static gate: syntax + install-depth invariant + dogfood drift
└── e2e-agent-scaffold.sh    # agent-scaffold behavioral gate: install into a throwaway repo, assert it works
.github/workflows/
└── validate.yml            # Runs the checks on push / PR
```

`npx skills` reads directly from `skills/`, so this repository does not maintain separate `.codex/skills` or `.claude/skills` mirrors.

## License

MIT
