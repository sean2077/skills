# PROJECT — Agent Contract

> `AGENTS.md` is the canonical repository-level contract; `CLAUDE.md` is a symlink to it. Keep this file an actionable entry point and put durable detail in `docs/`.

## Project

`sean2077/skills` publishes 16 independently installable Agent Skills under `skills/`. The repository-private `.agents/skills/skill-eval` workflow belongs to the dogfooded project harness and is not a catalog target. Consumers need no build step; maintainers must regenerate checked-in runtime payloads from their source modules before committing.

## Required workflow

1. Read this contract and any applicable nested `AGENTS.md` before changing files.
2. Follow the scaffold-managed worktree rule below; documentation-only work is not an exception.
3. Edit the canonical source, not a generated projection or scaffold-owned managed copy. Use the ownership map in [repository architecture](docs/architecture.md).
4. Run the changed-surface checks and the appropriate full gates from the [development guide](docs/development.md). `.github/workflows/validate.yml` is the normative CI definition.
5. Add an Unreleased changelog entry for user- or maintainer-visible behavior. Use Conventional Commits, omit `Co-Authored-By`, and keep all required gates green before merging to `main`.

## Repository boundaries

- `skills/` is the published product; `.agents/skills/` is the private project harness. Never infer one catalog from the other.
- `scripts/workflow_runtime/` and `scripts/p0_runtime/` are maintainer source. Run their generators instead of editing generated skill runtime payloads.
- Format validation, installer discovery, host wiring, and runtime behavior are different evidence layers. Keep support claims in [compatibility.md](docs/compatibility.md).
- Prefer model-native reasoning for reversible single-session work. Add deterministic controls only for the costly machine-checkable boundaries described in the [harness constraint policy](docs/harness-constraint-policy.md).
- Skills and bundled scripts target Linux, macOS, and Windows through Git Bash, with LF line endings and real symlinks where the scaffold requires them.

## High-cost maintenance traps

- Keep frontmatter strict-YAML compatible. Quote a scalar containing `: `.
- Keep every published `description` on one physical line and within the 320-character routing budget; preserve decisive triggers and exclusions.
- Treat copy-paste commands as interfaces: verify working directory, scope, quoting, identity, side effects, and expected result. Quote shell globs such as `'*'`.
- Prefix local skill directories with `./`; otherwise the installer may interpret the value as a GitHub repository.
- Do not describe the CI-audited `skills@1.5.17` pin as upstream latest. Do not run project-scope `skills remove` from the catalog root.

## Canonical references

| Topic | Source |
|---|---|
| Product surfaces, generated ownership, and validation boundaries | [docs/architecture.md](docs/architecture.md) |
| Local workflow, commands, platform checks, and releases | [docs/development.md](docs/development.md) |
| Host, installer, trust, and certification claims | [docs/compatibility.md](docs/compatibility.md) |
| Documentation ownership, evidence, and freshness | [docs/documentation-maintenance.md](docs/documentation-maintenance.md) |
| Mechanical-control selection | [docs/harness-constraint-policy.md](docs/harness-constraint-policy.md) |
| Pending and historical release changes | [CHANGELOG.md](CHANGELOG.md) |

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
| `.agents/tools/hooks/` | scaffold-owned hook runtime (doc budget + optional trunk guard) — **managed copies, do NOT hand-edit** | ✅ |
| `.agents/tools/worktree.sh` | worktree lifecycle — **managed copy, do NOT hand-edit** | ✅ |
| `.claude/allow-trunk-edit` | worktree escape hatch | ❌ ignored |
| `.claude/settings.local.json` | personal overrides | ❌ ignored |

- **Change managed runtime**: everything under `.agents/tools/` is a copy the skill owns. Edit the skill's bundled source and run `agent-scaffold upgrade` to refresh — a hand-edit here is drift, and `agent-scaffold verify` reports it.
- **Add a skill**: edit `.agents/skills/` → run `bash .agents/relink-skills.sh` → commit source + symlink.
- **Add a subagent** (needs python): edit `.agents/subagents/` → run `python .agents/tools/generate-subagents.py` → commit source + generated. Wire `--check` into the project's own CI or hook manager when desired.
- **Third-party skills** follow project-owned placement and installation policy. The relinker manages only names sourced from `.agents/skills/`, preserves unrelated entries, and fails on same-name ownership conflicts.

**Codex trust has two independent gates**: trust the project so project-local `.codex/` config, hooks, and rules can load, then verify generated project agents are discoverable. Separately, open `/hooks` and review each exact scaffold-owned, non-managed command-hook definition. Codex records hook trust by definition hash, so an unreviewed or changed hook is skipped even when the project layer itself is trusted.

**Claude checkpoint boundary**: Claude Code checkpoint restore does not rewind symlinked or hard-linked files. For edits reached through `CLAUDE.md` or `.claude/skills/*`, verify the real target with Git and reverse or restore that target explicitly.
<!-- agent-scaffold:end -->
