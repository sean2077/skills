# PROJECT — Agent Contract

> `AGENTS.md` is the canonical agent contract; `CLAUDE.md` is a symlink to it. It is
> shared by Claude Code and Codex. Keep it an **entry point**, not a detail dump —
> put detail in `docs/` and link back; inline only important, frequently-needed points.

## Project Overview

`sean2077/skills` is a universal [SKILL.md](https://github.com/anthropics/skills) **catalog** —
reusable agent skills installed into any project via `npx skills` (Claude Code + Codex and other
Agent-Skills hosts). It ships 5 skills: `conventional-commit`, `semver-release`,
`project-docs-organizer`, `tooling-conventions`, and `agent-scaffold`. No build step — the skills
*are* the product.

## Development Commands

The CI gates must stay green — `.github/workflows/validate.yml` runs them on push/PR:

```bash
python -m pip install -r requirements-validation.txt  # pinned StrictYAML + official skills-ref
python scripts/validate_skills.py      # frontmatter, name↔dir, README + reference links, allowed-tools, placeholders
python scripts/test_validate_skills.py # category-reference validation fixtures
for d in skills/*; do python -m skills_ref.cli validate "$d"; done  # official Agent Skills spec validator
npx --yes skills@1.5.17 add . -l    # real catalog discovery smoke test
bash scripts/check-agent-scaffold.sh    # agent-scaffold static gate: syntax + install-depth invariant + dogfood drift
bash scripts/e2e-agent-scaffold.sh      # agent-scaffold behavioral gate: install into a throwaway repo, assert it works
find scripts skills -type f -name '*.sh' -print0 | xargs -0 shellcheck
shellcheck skills/agent-scaffold/templates/husky.pre-commit
```

## Architecture

- `skills/<name>/SKILL.md` — the **distributable** catalog (what `npx skills` consumers install);
  optional `references/<category>.md` files hold on-demand depth, plus any scripts/templates a skill
  ships. Keep the resident file lean (router + invariants + skeleton); use descriptive lowercase
  kebab-case category names and link each file directly from `SKILL.md`. Do not use root-level
  `reference.md` or catch-alls such as `misc.md`, `all.md`, or `references/README.md`.
- `scripts/` — the CI quality gates above; `.github/workflows/validate.yml` runs them in CI.
- **Two skill layouts coexist — do not conflate:** `skills/` is the published catalog (the product);
  `.agents/skills/` (harness SSOT, below) is for *this repo's own* internal skills — currently empty.
- Conventions: Conventional Commits, **no `Co-Authored-By`**; worktree-per-change (below); all gates
  green before any merge back to `main`.
- **Cross-platform (design goal)** — skills + bundled scripts target macOS / Linux / Windows
  (**Git Bash only**): keep them POSIX-bash + GNU-coreutils compatible, **LF** line endings
  (enforced by `.gitattributes` + a CI CRLF check), and **real-symlink-required** (preflight
  fails before mutation when the OS lacks symlink support; copying is forbidden). Harness
  symlink management, subagents, and hook JSON parsing use `python`.

## Catalog Maintenance Gotchas

- Treat the real `npx skills` CLI as the source of truth for install behavior. After changing
  `SKILL.md` frontmatter, skill names, or catalog layout, smoke-test discovery with
  `npx skills add . -l`; after pushing a discovery fix, smoke-test the remote path too.
- Keep frontmatter valid for a strict YAML parser. Plain scalars containing `: `, such as
  `Modes: init`, must be quoted or `npx skills` silently drops that skill during discovery.
- Local subdirectory installs need an explicit path prefix: use
  `npx skills add ./skills/agent-scaffold`, not `npx skills add skills/agent-scaffold`, because
  the latter is parsed as the GitHub repository `skills/agent-scaffold`.

<!-- agent-scaffold:start — managed by the agent-scaffold skill. Edit project prose OUTSIDE these markers; `agent-scaffold upgrade` refreshes this block. -->
## Agent Harness (Claude Code + Codex)

This repo carries a vendored, dual-host agent harness. `.agents/` is the single
source of truth (SSOT); `.claude/` and `.codex/` are wired to the **same**
implementations under `.agents/tools/`.

### Worktree-per-change (hard rule)

**Never edit trunk (`main`) directly** — every change, however small ("just docs"
is NOT an exception), starts in its own worktree cut from the trunk tip:

```bash
bash .agents/tools/worktree.sh new <name>   # edit inside .worktrees/<name>/  (branch feat|fix|docs|chore/<name>)
bash .agents/tools/worktree.sh done         # merge back to local trunk (--no-ff) + clean up + ff-only push
```

`.agents/tools/hooks/trunk_edit_guard.sh` (PreToolUse) mechanically blocks edits to
tracked files while on trunk. Escape hatch — only when the user explicitly
authorizes a trunk edit: `touch .claude/allow-trunk-edit` (auto-expires in 2 h)
or `WORKTREE_ALLOW_TRUNK_EDIT=1`.

### Authority docs

`AGENTS.md` (root plus nested contracts created only for local differences;
root `CLAUDE.md` is a symlink to it) is an **entry
point**, not a detail dump. `.agents/tools/hooks/authority_doc_budget.sh`
(PostToolUse) advises when a contract exceeds its line budget (root 320 / nested
120; override with `AUTHORITY_DOC_MAX_ROOT|NESTED`). Nested contracts carry a
`<!-- Parent: ... -->` link to the nearest existing ancestor contract.

### SSOT layout

| Path | Role | Commit? |
|---|---|---|
| `.agents/skills/<name>/SKILL.md` | project skill source | ✅ |
| `.agents/subagents/<name>/{metadata.json,instructions.md}` | subagent source | ✅ |
| `.claude/skills/<name>` | symlink → `.agents/skills/<name>` (CC discovery; Codex reads `.agents/` directly) | ✅ |
| `.claude/agents/*.md`, `.codex/agents/*.toml` | **generated** subagent projections — do NOT hand-edit | ✅ |
| `.agents/tools/hooks/` | scaffold-managed hook runtime (doc budget + optional trunk guard) | ✅ |
| `.agents/tools/worktree.sh` | worktree lifecycle | ✅ |
| `.claude/allow-trunk-edit` | worktree escape hatch | ❌ ignored |
| `.claude/settings.local.json` | personal overrides | ❌ ignored |

- **Add a skill**: edit `.agents/skills/` → run `bash .agents/relink-skills.sh` → commit source + symlink.
- **Add a subagent** (needs python): edit `.agents/subagents/` → run `python .agents/tools/generate-subagents.py` → commit source + generated. A pre-commit `--check` guards the two sides from drifting.
- **Third-party skills** install separately via `npx skills`; they land as real dirs in `.claude/skills/` and the relinker leaves them untouched.

**Codex trust**: project-level `.codex/` (config + hooks + agents) only loads for a
**trusted** project; until trusted it is silently skipped. Trust once: run `codex`
here and accept, or add `[projects."<repo abs path>"] trust_level = "trusted"` to
`~/.codex/config.toml`.
<!-- agent-scaffold:end -->
