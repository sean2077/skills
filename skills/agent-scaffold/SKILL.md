---
name: agent-scaffold
description: 'Use when setting up, standardizing, retrofitting, planning, diagnosing, verifying, or upgrading a vendored dual-host Claude Code + Codex agent harness. Covers .agents/ SSOT, real-symlink projections, AGENTS.md/CLAUDE.md migration, hooks, subagent import/generation, and optional worktree/trunk-guard governance, including --no-worktree. Modes: init, retrofit, plan, doctor, verify, upgrade. Not for one commit message (use conventional-commit), authoring a standalone CLAUDE.md when no harness is wanted, or third-party skill installation (use npx skills).'
compatibility: Requires git, Python 3.8 or newer, and Bash 3.2 or newer. Windows requires Git Bash plus native file and directory symlink privilege.
---

# Agent Scaffold

Install or retrofit a vendored dual-host harness so Claude Code and Codex share
one contract, one project-authored asset source, and one runtime. `.agents/` is
the harness home: skills and subagents are authoritative sources, runtime tools
live under `.agents/tools/`, and `.claude/` / `.codex/` are host projections.

`harness-init.sh` beside this file is the idempotent, merge-aware installer.
After installation, the target repo's `AGENTS.md` and `.agents/tools/` carry the
day-to-day workflow; no resident copy of this skill is required.

## When to use

- initialize or retrofit the dual-host harness
- preview a retrofit without writes (`plan`)
- diagnose prerequisites (`doctor`) or installed drift (`verify`)
- refresh vendored runtime files and migrate an older installed layout (`upgrade`)

Do not use it for a single commit message, a standalone `CLAUDE.md`, or
third-party skill installation.

## Invariants

- **`.agents/` is the harness home and SSOT.** Project-authored skills live in
  `.agents/skills/`; subagents live in `.agents/subagents/`; shared runtime tools
  live in `.agents/tools/`.
- **`.claude/` and `.codex/` are projections.** Never hand-edit generated
  `.claude/agents/*.md` or `.codex/agents/*.toml`.
- **Real symlinks are mandatory.** Every mutating mode and `relink-skills.sh`
  probes file and directory link capability before target mutation; there is no
  copy fallback.
- **Hook configs are reconciled, never clobbered.** Only exact managed hook
  identities are refreshed or removed; user hooks and unrelated config survive.
- **`CLAUDE.md` is a symlink to `AGENTS.md`.** Keep `AGENTS.md` as a lean entry
  point and put project detail in `docs/`.
- **Worktree governance defaults on.** `--no-worktree` omits the lifecycle,
  trunk guard, and managed policy while retaining the rest of the harness.
- **Profile-equivalent reruns are idempotent.** Changing profile flags
  intentionally reconciles the installation to that profile.

## Modes

Run from inside the target repository:

| Mode | Purpose |
|---|---|
| `init` | Greenfield install of the managed harness contract and runtime |
| `retrofit` | Merge into an existing `.claude` / `.codex` / AGENTS setup |
| `plan` | Read-only preview of create, merge, adopt, and migration decisions |
| `doctor` | Read-only prerequisite and real-symlink capability check |
| `verify` | Read-only presence, drift, projection, and host-parity check |
| `upgrade` | Refresh vendored files and migrate an installed legacy layout |

```bash
bash <skill-dir>/harness-init.sh <mode> [flags]
```

Useful flags: `--no-worktree` and `--force-scripts` (implied by `upgrade`).
Repeat profile flags on later `upgrade` and `verify` runs. Formatter,
hook-manager/package, and example-subagent choices are project-owned recipes.

## Workflow

1. Confirm the target with `git rev-parse --show-toplevel` and inspect whether
   `.claude/`, `.codex/`, `AGENTS.md`, or legacy harness artifacts already exist.
2. Run `plan` before a non-trivial retrofit. If it reports the legacy
   `tools/agent` layout or stale managed path identities, read only
   [`references/harness-migration.md`](references/harness-migration.md), then
   run `upgrade` rather than `retrofit`.
3. Run the selected mode. Mutating modes preflight deterministic contract,
   projection, import, hook-config, runtime-layout, and symlink conflicts before
   the first target write.
4. For `init`, add project overview or command prose outside the managed block
   only when useful. Add nested authority documents only for real local differences; use
   [`references/authority-docs.md`](references/authority-docs.md).
5. Run `verify` and report created versus merged assets, any stopped preflight,
   and the Codex trust reminder. The installer installs and runs the subagent
   generator unconditionally.

## On-demand references

Read only the category required by the current task:

| Task | Reference |
|---|---|
| Installed layout, profiles, SSOT, third-party coexistence | [`harness-layout.md`](references/harness-layout.md) |
| Hooks, dual-host wiring, merge ownership, Codex trust | [`host-integration.md`](references/host-integration.md) |
| AGENTS/CLAUDE budgets and nested contracts | [`authority-docs.md`](references/authority-docs.md) |
| Subagent import, generation, projection, drift | [`subagents.md`](references/subagents.md) |
| Retrofit or legacy installed layout migration | [`harness-migration.md`](references/harness-migration.md) |
| Runtime prerequisites, Windows/Git Bash, symlink repair | [`platform-support.md`](references/platform-support.md) |
| Deep verify and E2E recipes | [`verification.md`](references/verification.md) |

## Platform contract

The harness requires **git, Python 3.8+, and Bash 3.2+**. Windows support is Git
Bash only and requires native file and directory symlink privilege. Bundled shell
and Python files stay LF-only. Python owns link materialization, hook JSON
handling, and subagent projection. Node and package-manager integration are not
required or selected by the scaffold.
