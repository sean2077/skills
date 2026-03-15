# skills

Reusable agent skills for development, ops, and productivity — battle-tested patterns with working examples.

Uses the universal [SKILL.md](https://github.com/anthropics/skills) format. Compatible with Claude Code, OpenCode, Cursor, GitHub Copilot, Windsurf, and other agents supporting the Agent Skills spec.

## Install

```bash
# Claude Code
/plugin install sean2077/skills

# npx skills (Vercel Labs cross-agent package manager)
npx skills add sean2077/skills
```

## Skills

| Skill | Description | Stack |
|-------|-------------|-------|
| [rich-tui-viewer](skills/rich-tui-viewer/) | Interactive TUI data viewer: table overview → click detail → ESC back. Dual-mode (TUI + CLI fallback). | Python, Rich, Textual |

## Structure

```
.claude-plugin/
└── marketplace.json       # Skill collection manifest
skills/
└── <name>/
    ├── SKILL.md           # Skill definition (universal agent format)
    └── example.py         # Minimal working example (PEP 723 inline deps, uv run ready)
```

## Try the Examples

```bash
cd skills/rich-tui-viewer
uv run example.py          # TUI interactive mode (mouse-clickable)
uv run example.py -s 1     # CLI direct output
```

## License

MIT
