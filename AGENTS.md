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
python scripts/test_validate_skills.py # focused catalog-contract regression fixtures
python scripts/tests/test_agent_scaffold_core.py # deterministic manifest, hook, and JSON-report core
python scripts/tests/test_semver_release_plan.py # read-only SemVer/base/bump planner fixtures
for d in skills/*; do python -m skills_ref.cli validate "$d"; done  # official Agent Skills spec validator
npx --yes skills@1.5.17 add . -l    # real catalog discovery smoke test
bash scripts/tests/test-tooling-inventory.sh # tooling structural-inventory reconciliation fixtures
bash scripts/check-agent-scaffold.sh    # agent-scaffold static gate: syntax + install-depth invariant + dogfood drift
bash scripts/e2e-agent-scaffold.sh      # agent-scaffold behavioral gate: install into a throwaway repo, assert it works
find scripts skills -type f -name '*.sh' -print0 | xargs -0 shellcheck
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
- With the pinned CLI, `npx skills add <source> --help` performs an install; inspect options with
  top-level `npx skills --help` instead. Never run project-scope `skills remove` from this catalog
  root because it can delete product `skills/*`. Refresh globals from outside the repo with
  `npx skills@1.5.17 update <names...> -g -y`, then compare installed files with the tagged source.

<!-- agent-scaffold:start — managed by the agent-scaffold skill. Edit project prose OUTSIDE these markers; `agent-scaffold upgrade` refreshes this block. -->
## Agent Harness (Claude Code + Codex)

This repo carries a vendored, dual-host agent harness. `.agents/` is the single source of truth (SSOT); `.claude/` and `.codex/` are wired to the **same** implementations under `.agents/tools/`.

### Worktree-per-change (hard rule)

**Never edit trunk (`main`) directly** — every change, however small ("just docs" is NOT an exception), starts in its own worktree cut from the trunk tip:

```bash
bash .agents/tools/worktree.sh new <name>   # edit inside .worktrees/<name>/  (branch feat|fix|docs|chore/<name>)
bash .agents/tools/worktree.sh done         # merge back to local trunk (--no-ff) + clean up + ff-only push
```

`.agents/tools/hooks/trunk_edit_guard.sh` (PreToolUse) mechanically blocks edits to tracked files while on trunk. Escape hatch — only when the user explicitly authorizes a trunk edit: `touch .claude/allow-trunk-edit` (auto-expires in 2 h) or `WORKTREE_ALLOW_TRUNK_EDIT=1`.

### Authority documents (hard rules)

`AGENTS.md` is the canonical repository-level contract for Agent work. Read and follow the root contract and its applicable nested contract chain before acting; higher-priority instructions still govern.

- **Keep it current.** When a durable change affects an Agent-relevant command, invariant, ownership boundary, risk boundary, or navigation path, update or remove the affected contract guidance in the same change. If the detail lives in linked project docs, update it there and keep the contract summary and link accurate.
- **Keep it lean.** Keep only concise, actionable guidance that changes Agent behavior and is frequently needed or costly to miss. Move explanations, rationale, history, long procedures, examples, and low-frequency detail to project docs and link to it.
- **Keep scopes honest.** Root rules are project-wide. Create a nested `AGENTS.md` only for a concrete local difference from the nearest ancestor; directory structure alone never justifies one.
- **Resolve conflicts explicitly.** If applicable instructions conflict, or contract guidance disagrees with verified repository facts, do not guess or silently ignore either. Surface the conflict, follow higher-priority instructions, request owner direction when authority is unclear, and repair stale guidance in the same change when authorized.

The authority-document budget hook remains advisory; projects may override its default line and character limits when justified.

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
- **Add a subagent** (needs python): edit `.agents/subagents/` → run `python .agents/tools/generate-subagents.py` → commit source + generated. Wire `--check` into the project's own CI or hook manager when desired.
- **Third-party skills** follow project-owned placement and installation policy. The relinker manages only names sourced from `.agents/skills/`, preserves unrelated entries, and fails on same-name ownership conflicts.

**Codex trust**: project-level `.codex/` (config + hooks + agents) only loads for a **trusted** project; until trusted it is silently skipped. Trust once: run `codex` here and accept, or add `[projects."<repo abs path>"] trust_level = "trusted"` to `~/.codex/config.toml`.
<!-- agent-scaffold:end -->
