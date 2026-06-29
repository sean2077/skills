---
name: agent-scaffold
description: 'Install or retrofit the complete dual-host (Claude Code + Codex) agent harness into a project — the .agents/ single-source-of-truth layout, the worktree-per-change flow with a trunk-edit guard, the AGENTS.md line-budget + format-on-edit PostToolUse hooks, the CLAUDE.md→AGENTS.md contract, idempotent skill symlinks, and (Node projects) a subagent generator with a pre-commit drift guard. One turnkey, idempotent, merge-aware installer. Use when setting up agent tooling for a repo, standardizing Claude Code + Codex in one project, adding worktree/hook governance, or asked to "init/retrofit the agent harness". Modes: init (greenfield), retrofit (merge into existing config), verify (parity/drift check), upgrade (refresh vendored scripts). Not for writing one commit message (use conventional-commit) or installing third-party skills (use npx skills).'
allowed-tools: Read, Edit, Write, Grep, Glob, Bash(git:*), Bash(bash:*)
---

# Agent Scaffold

Install or retrofit a **vendored, dual-host agent harness** into a project so Claude
Code and Codex work from the **same** rules and tooling. `.agents/` is the single
source of truth (SSOT); `.claude/` and `.codex/` are wired to the same implementations
under `tools/agent/`. After running this skill once, the harness is fully set up for
both runtimes — there is no resident skill to keep loaded for day-to-day use; the
installed scripts and the project's `AGENTS.md` carry the workflow.

A ready-to-run installer ships beside this skill as **`harness-init.sh`**; it does the
mechanical work (idempotent, merge-aware). The deep tables, hook semantics, dual-host
wiring snippets, the JSON-merge algorithm, and troubleshooting live in **`reference.md`** —
read it on demand, not up front.

## When To Use

- set up agent tooling / standardize Claude Code + Codex for a repo ("init the agent harness")
- retrofit the worktree flow, the trunk-edit guard, or the AGENTS.md budget hook into an existing project
- check an existing harness for drift or parity across the two hosts (`verify`)
- refresh the vendored harness scripts after this skill is updated (`upgrade`)

Do **not** use this skill for:

- writing a single commit message → `conventional-commit`
- installing third-party skills → `npx skills add <repo> -a claude-code -a codex` (coexists; see below)
- authoring one standalone `CLAUDE.md` with no harness → just write the file

## Invariants

- **Never edit a trunk worktree directly.** Every change starts in its own `.worktrees/<name>` branch; `trunk_edit_guard.sh` (PreToolUse) enforces it mechanically.
- **`.agents/` is the SSOT; `.claude/`/`.codex/` are projections.** Skills project as symlinks (`relink-skills.sh`); subagents project via the Node generator. **Never hand-edit** generated `.claude/agents/*.md` or `.codex/agents/*.toml`.
- **Hook configs are merged, never clobbered.** The installer adds our entries beside any existing ones and is a no-op on re-run.
- **`CLAUDE.md` is a symlink to `AGENTS.md`.** `AGENTS.md` is an entry point, not a detail dump (the budget hook advises when it grows too large).
- **The installer is idempotent.** Re-running any mode changes nothing that is already in place.

## Modes

| Mode | When | Command (run from the target repo root) |
|---|---|---|
| `init` | greenfield — no `.claude/`, `.codex/`, or `AGENTS.md` | `bash <skill-dir>/harness-init.sh init` |
| `retrofit` | project already has some `.claude`/`.codex`/`AGENTS.md` | `bash <skill-dir>/harness-init.sh retrofit` |
| `verify` | check presence / drift / dual-host parity (read-only) | `bash <skill-dir>/harness-init.sh verify` |
| `upgrade` | re-copy the vendored scripts + add any new hook | `bash <skill-dir>/harness-init.sh upgrade` |

`<skill-dir>` is this skill's installed directory (where `harness-init.sh` sits). `init` and
`retrofit` share one idempotent code path — when unsure which applies, run `retrofit`; it
creates what is missing and merges into what exists.

## Workflow

1. **Detect intent + state.** From the user's words pick the mode; confirm the target repo with `git rev-parse --show-toplevel` and note whether `.claude/`, `.codex/`, `AGENTS.md`, and `package.json` already exist. If ambiguous between init and retrofit, run `retrofit`.
2. **Run the installer** for that mode (table above). Useful flags: `--no-format-hook`, `--no-husky`, `--no-example-subagent`, `--force-scripts` (implied by `upgrade`). See `harness-init.sh --help`. The worktree flow's trunk is chosen per-call (`WORKTREE_TRUNK=… ` or `worktree.sh … --trunk <branch>`), not at install time.
3. **Finish the contract.** For `init`, fill the `AGENTS.md` TODO sections (project overview / commands / architecture) — keep it an entry point; link depth into `docs/`. For nested directories that deserve their own contract, drop in `templates/AGENTS.nested.md` and fill it (keep `<!-- Parent: ../AGENTS.md -->`). For a multi-directory codebase, generate a full parent-linked tree — see `reference.md` → *Generating the nested AGENTS.md tree*.
4. **Report** what was installed, what was merged vs created, what was skipped (e.g. subagents on a non-Node project), and the **Codex trust** reminder the installer prints.
5. **Verify** with `verify` mode (or the recipe in `reference.md`) before handing back.

## The installer at a glance

`harness-init.sh` copies the vendored scripts into `tools/agent/` + `.agents/`, **merges**
the dual-host hook wiring into `.claude/settings.json` and `.codex/hooks.json` (jq → node →
"paste this block" fallback), creates the `CLAUDE.md → AGENTS.md` symlink, seeds `.agents/{skills,subagents}/`
and the root `AGENTS.md`, appends the `.gitignore` lines, runs `relink-skills.sh`, and — on a
Node project — installs the subagent generator + the pre-commit drift guard. Every step is
"create if missing, merge if present, skip if already done."

## Dual-host wiring (at a glance)

Both hosts call the **same** hook scripts under `tools/agent/hooks/`; only the invocation differs:

| | Claude Code (`.claude/settings.json`) | Codex (`.codex/hooks.json`) |
|---|---|---|
| Path resolution | `"$CLAUDE_PROJECT_DIR"/tools/agent/hooks/X.sh` | `bash -lc 'root="$(git rev-parse --show-toplevel)"; "$root/.../X.sh"'` |
| Matcher | `Edit\|MultiEdit\|Write\|NotebookEdit` (Pre) / `Edit\|MultiEdit\|Write` (Post) | `Edit\|Write\|apply_patch` |

The hook scripts resolve their own project root either way, so nothing host-specific leaks into them. **Codex only loads project-level `.codex/` for a TRUSTED project** — the installer prints how to trust it. Full snippets + rationale: `reference.md`.

## Node vs non-Node

The pure-bash core (worktree flow, the 3 hooks, `relink-skills.sh`, both host configs, the
`AGENTS.md` contract) installs **everywhere**. The subagent generator (`generate-subagents.mjs`)
and its pre-commit `--check` drift guard need **Node** (a `package.json` at the root) — without
it they are cleanly skipped, and the installer says how to enable them later.

## Coexistence with `npx skills`

`.agents/skills/` holds this **project's own** skills (SSOT). **Third-party** skills install
separately via `npx skills` and land as **real directories** in `.claude/skills/`; the relinker
only manages **symlinks**, so it never touches them. Keep project skill names distinct from
installed ones.

→ Deep reference (manifest, hook semantics, merge algorithm, AGENTS.md budget rationale,
Codex trust, troubleshooting, end-to-end test recipe): **`reference.md`**.
