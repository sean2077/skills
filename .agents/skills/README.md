# .agents/skills/ — project skill SSOT

Project-authored skills live here. Claude Code discovers matching real symlinks
under `.claude/skills/`; Codex reads `.agents/skills/` directly.

## Change a project skill

1. Edit `.agents/skills/<name>/SKILL.md` and any local resources.
2. Run `bash .agents/relink-skills.sh`.
3. Commit the source and `.claude/skills/<name>` symlink together.

Rules:

- Do not hand-edit `.claude/skills/` projections.
- Keep third-party skills separate; install them with `npx skills`.
- Prefix support-only directories with `_`; the relinker skips them.
- Same-name project and third-party skills are an ownership conflict.

For full authoring conventions, naming, and coexistence details, load the
`agent-scaffold` skill's `references/harness-layout.md` on demand.
