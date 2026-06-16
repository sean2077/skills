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
```

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [conventional-commit](skills/conventional-commit/) | Generate a Conventional Commits message using the repository's historical language convention, defaulting to English when unclear, and create one local commit when requested. | Git |
| [git-worktree](skills/git-worktree/) | Worktree-per-change git workflow: an isolated `.worktrees/<name>` branch per change, one-command merge-back + cleanup, fast-forward-only push. Ships `worktree.sh`. | Git |
| [project-docs-organizer](skills/project-docs-organizer/) | Build or reorganize project documentation systems: README-only for simple projects, major/subcategory numbered docs zones for complex projects. | Documentation |
| [semver-release](skills/semver-release/) | Cut a semver release from conventional commits: infer the bump, update CHANGELOG + version file, tag, then hand off to tag-triggered release CI (or publish a GitHub/GitLab release directly). | Git, Release |
| [tooling-conventions](skills/tooling-conventions/) | Govern a project's `tools/`/`scripts/` directory at scale: surface taxonomy, failure-domain aggregation, placement tree, script contract, and a reconciliation-checked surface manifest. Ships `manifest-check.sh`. | Shell, Governance |

## Structure

```
skills/
└── <name>/
    ├── SKILL.md           # Single source of truth for every installer
    ├── reference.md       # Optional: on-demand detail kept out of the resident skill body
    └── example.py         # Optional: runnable example for code-building skills
scripts/
└── validate_skills.py     # Catalog check: frontmatter, name↔dir, README coverage, placeholders
.github/workflows/
└── validate.yml           # Runs the validator on push / PR
```

`npx skills` reads directly from `skills/`, so this repository does not maintain separate `.codex/skills` or `.claude/skills` mirrors.

## License

MIT
