# .agents/skills/ — authoritative skill source (CC + Codex)

This directory is the **single source of truth** for this project's own skills.
Both runtimes consume the same `SKILL.md` files, by different discovery paths:

| | Claude Code | Codex |
|---|---|---|
| Source | `.agents/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` |
| Discovery | `.claude/skills/<name>` (symlink) | reads `.agents/skills/` directly |
| After a change | run `./.agents/relink-skills.sh` | nothing extra |

## Add / rename / remove a skill

1. Create or edit `.agents/skills/<name>/SKILL.md` (+ optional `references/`, `scripts/`).
2. Run `./.agents/relink-skills.sh` (idempotent — (re)creates `.claude/skills/<name>`, prunes stale links).
3. `git add .agents/skills/<name> .claude/skills/<name>`.

Directories named `_*` (e.g. `_shared/`) are support material — they are **not** skills
and are skipped by the relinker.

## SKILL.md shape

```markdown
---
name: <kebab-case>            # must match the directory name
description: "<one line: what it does + when to use it>"
# optional:
# argument-hint: "<args summary>"
# metadata: { requires: { bins: ["bash", "node"] } }
---

# <name>

## Router            # intent → sub-step map (if multi-mode)
## <workflow steps>  # concise; deep material goes in references/, read on demand
```

Keep `SKILL.md` lean: routing + invariants + step skeleton. Push long checklists,
templates, and worked examples into `references/` so they load only when needed.

## Coexistence with `npx skills` (third-party skills)

This directory is for **project-authored** skills. Third-party skills install
separately via `npx skills add <repo> -a claude-code -a codex`; they land as
**real directories** in `.claude/skills/` (and Codex's own path). The relinker
only manages **symlinks**, so it leaves those installed directories untouched.
Keep your project skill names distinct from installed ones to avoid a clash.

## Conventions

- Skills describe **repeatable agent workflows for this project**, not one-off tasks.
- `.claude/skills/` holds **only symlinks** for project skills — never real skill files there.
- Don't hand-edit symlinks; let `relink-skills.sh` own them.
