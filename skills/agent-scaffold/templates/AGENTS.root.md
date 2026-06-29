# PROJECT — Agent Contract

> `AGENTS.md` is the canonical agent contract; `CLAUDE.md` is a symlink to it. It is
> shared by Claude Code and Codex. Keep it an **entry point**, not a detail dump —
> put detail in `docs/` and link back; inline only important, frequently-needed points.

## Project Overview

<!-- TODO: one paragraph — what this project is, who it's for, the headline tech. -->

## Development Commands

<!-- TODO: the handful of commands an agent runs most (build / test / lint / run). -->

## Architecture

<!-- TODO: the load-bearing modules and how they relate. Keep it an INDEX that links
     into docs/ for depth, not a full tour. -->

<!-- agent-scaffold:start — managed by the agent-scaffold skill. Edit project prose OUTSIDE these markers; `agent-scaffold upgrade` refreshes this block. -->
## Agent Harness (Claude Code + Codex)

This repo carries a vendored, dual-host agent harness. `.agents/` is the single
source of truth (SSOT); `.claude/` and `.codex/` are wired to the **same**
implementations under `tools/agent/`.

### Worktree-per-change (hard rule)

**Never edit trunk (`main`) directly** — every change, however small ("just docs"
is NOT an exception), starts in its own worktree cut from the trunk tip:

```bash
tools/agent/worktree.sh new <name>   # edit inside .worktrees/<name>/  (branch feat|fix|docs|chore/<name>)
tools/agent/worktree.sh done         # merge back to local trunk (--no-ff) + clean up + ff-only push
```

`tools/agent/hooks/trunk_edit_guard.sh` (PreToolUse) mechanically blocks edits to
tracked files while on trunk. Escape hatch — only when the user explicitly
authorizes a trunk edit: `touch .claude/allow-trunk-edit` (auto-expires in 2 h)
or `WORKTREE_ALLOW_TRUNK_EDIT=1`.

### Authority docs

`AGENTS.md` (root + every subdirectory; `CLAUDE.md` is a symlink) is an **entry
point**, not a detail dump. `tools/agent/hooks/authority_doc_budget.sh`
(PostToolUse) advises when a contract exceeds its line budget (root 320 / nested
120; override with `AUTHORITY_DOC_MAX_ROOT|NESTED`). Subdirectory `AGENTS.md`
files carry `<!-- Parent: ../AGENTS.md -->` and stay subordinate to the root.

### SSOT layout

| Path | Role | Commit? |
|---|---|---|
| `.agents/skills/<name>/SKILL.md` | project skill source | ✅ |
| `.agents/subagents/<name>/{metadata.json,instructions.md}` | subagent source | ✅ |
| `.claude/skills/<name>` | symlink → `.agents/skills/<name>` (CC discovery; Codex reads `.agents/` directly) | ✅ |
| `.claude/agents/*.md`, `.codex/agents/*.toml` | **generated** subagent projections — do NOT hand-edit | ✅ |
| `tools/agent/hooks/` | shared hook impls (trunk guard / doc budget / format) | ✅ |
| `tools/agent/worktree.sh` | worktree lifecycle | ✅ |
| `.claude/allow-trunk-edit`, `.claude/settings.local.json` | escape hatch / personal overrides | ❌ ignored |

- **Add a skill**: edit `.agents/skills/` → run `./.agents/relink-skills.sh` → commit source + symlink.
- **Add a subagent** (needs python3): edit `.agents/subagents/` → run `python3 tools/agent/generate-subagents.py` → commit source + generated. A pre-commit `--check` guards the two sides from drifting.
- **Third-party skills** install separately via `npx skills`; they land as real dirs in `.claude/skills/` and the relinker leaves them untouched.

**Codex trust**: project-level `.codex/` (config + hooks + agents) only loads for a
**trusted** project; until trusted it is silently skipped. Trust once: run `codex`
here and accept, or add `[projects."<repo abs path>"] trust_level = "trusted"` to
`~/.codex/config.toml`.
<!-- agent-scaffold:end -->
