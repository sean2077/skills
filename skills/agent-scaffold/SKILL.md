---
name: agent-scaffold
description: 'Use when a repository needs planning, installation, retrofit, diagnosis, verification, or upgrade of a vendored Claude Code + Codex harness with .agents/ SSOT, real-symlink host projections, hooks, authority docs, or subagents. Not for one commit, a standalone authority file, or third-party skill installation.'
---

# Agent Scaffold

Converge a target repository on one vendored Claude Code + Codex harness.
`.agents/` owns project skills, subagents, and runtime tools; `.claude/` and
`.codex/` are host projections. Run the bundled installer from inside the
target repository:

```bash
bash <skill-dir>/agent-scaffold.sh <mode> [--profile default|light] [--json]
```

The harness requires **git, Python 3.8+, and Bash 3.2+**. The installer installs
and runs the subagent generator in every mutating mode.

## Invariants

- Treat `.agents/` as the SSOT; never hand-edit generated host-agent files.
- Require real file and directory symlinks; never fall back to copies.
- Keep `CLAUDE.md` as a symlink to the lean `AGENTS.md` entry point.
- Reconcile only exact scaffold-owned hook identities; preserve unrelated host config.
- Keep formatter, hook-manager, package, CI, nested-contract, and example-agent
  choices project-owned.
- Keep project terminology project-owned; route every Agent to its applicable
  glossary from the managed contract.

## Modes

| Mode | Use |
|---|---|
| `apply` | Add or reconcile the harness; refuse runtime drift that requires `upgrade` |
| `plan` | Preview create, merge, adopt, refresh, and attention states without writes |
| `doctor` | Check prerequisites and real-symlink capability |
| `verify` | Check the selected current contract, runtime drift, hooks, and projections |
| `upgrade` | Refresh current managed runtime files, then reconcile the contract |

Use `--profile default` for worktree/trunk-guard governance or `--profile light`
to omit it. Use `--json` with `plan`, `doctor`, or `verify` when another tool
needs stable check IDs and statuses.

## Workflow

1. Confirm the target with `git rev-parse --show-toplevel`.
2. Run `plan`; use its `apply_mode` (`apply` or `upgrade`) and selected profile.
3. Resolve any `attention` item before mutation. Mutating modes preflight marker,
   hook-config, runtime-shape, subagent-import, and symlink conflicts before the
   first target write.
4. Run the selected mutating mode, then `verify` with the same profile.
5. Report created or refreshed assets, preserved project-owned state, Codex project/hook trust steps, and any symlink-checkpoint caveat relevant to the changed files.

## On-demand references

Read only the category needed for the current task:

| Task | Reference |
|---|---|
| Installed assets, profiles, SSOT, third-party coexistence | [`harness-layout.md`](references/harness-layout.md) |
| Scaffold-owned host hooks, merge ownership, Codex project/hook trust | [`host-integration.md`](references/host-integration.md) |
| Project-owned format-on-edit integration | [`format-hooks.md`](references/format-hooks.md) |
| Root and nested authority-document policy | [`authority-docs.md`](references/authority-docs.md) |
| Project terminology SSOT, glossary format, multi-context routing, and legacy names | [`terminology.md`](references/terminology.md) |
| Subagent authoring, projection, and drift integration | [`subagents.md`](references/subagents.md) |
| Importing hand-authored Claude/Codex agents | [`subagent-import.md`](references/subagent-import.md) |
| Adopting an existing AGENTS/CLAUDE or host-agent setup | [`retrofit.md`](references/retrofit.md) |
| Runtime prerequisites, Windows/Git Bash, symlink repair, Claude checkpoint boundary | [`platform-support.md`](references/platform-support.md) |
| Structured plan/doctor/verify output and target troubleshooting | [`diagnostics.md`](references/diagnostics.md) |
