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

Optional Claude Code marketplace compatibility is still available:

```bash
/plugin install sean2077/skills
```

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [conventional-commit](skills/conventional-commit/) | Generate a Conventional Commits message using the repository's historical language convention, defaulting to English when unclear, and create one local commit when requested. | Git |
| [project-docs-organizer](skills/project-docs-organizer/) | Build or reorganize project documentation systems: README-only for simple projects, major/subcategory numbered docs zones for complex projects. | Documentation |
| [rich-tui-viewer](skills/rich-tui-viewer/) | Interactive TUI data viewer: table overview → click detail → ESC back. Dual-mode (TUI + CLI fallback). | Python, Rich, Textual |

## Structure

```
.claude-plugin/
└── marketplace.json       # Optional Claude Code marketplace manifest
skills/
└── <name>/
    ├── SKILL.md           # Single source of truth for every installer
    └── example.py         # Optional runnable example for code-building skills
```

`npx skills` reads directly from `skills/`, so this repository does not maintain separate `.codex/skills` or `.claude/skills` mirrors.

## Try the Examples

```bash
cd skills/rich-tui-viewer
uv run example.py          # TUI interactive mode (mouse-clickable)
uv run example.py -s 1     # CLI direct output
```

## License

MIT
