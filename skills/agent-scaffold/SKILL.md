---
name: agent-scaffold
description: 'Install or retrofit the complete dual-host (Claude Code + Codex) agent harness into a project: the .agents/ single-source-of-truth layout, worktree-per-change flow with a trunk-edit guard, AGENTS.md budget + format-on-edit hooks, the CLAUDE.md→AGENTS.md contract, skill symlinks, and (python3) a subagent generator with a drift guard. One idempotent, merge-aware installer that also retrofits a project already mid-development — it adopts an existing real CLAUDE.md as the AGENTS.md SSOT and reverse-generates hand-authored .claude/agents or .codex/agents into .agents/subagents sources. Use when setting up or standardizing agent tooling, adding worktree/hook governance, migrating an existing CLAUDE.md or hand-written subagents into the harness, or asked to "init/retrofit the agent harness". Modes: init, retrofit (merge/migrate an existing project), plan (read-only preview), verify (drift check), upgrade (refresh scripts). Not for one commit message (use conventional-commit) or third-party skills (use npx skills).'
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
- **`.agents/` is the SSOT; `.claude/`/`.codex/` are projections.** Skills project as symlinks (`relink-skills.sh`); subagents project via the python3 generator. **Never hand-edit** generated `.claude/agents/*.md` or `.codex/agents/*.toml`.
- **Hook configs are merged, never clobbered.** The installer adds our entries beside any existing ones and is a no-op on re-run.
- **`CLAUDE.md` is a symlink to `AGENTS.md`.** `AGENTS.md` is an entry point, not a detail dump (the budget hook advises when it grows too large).
- **The installer is idempotent.** Re-running any mode changes nothing that is already in place.

## Modes

| Mode | When | Command (run from the target repo root) |
|---|---|---|
| `init` | greenfield — no `.claude/`, `.codex/`, or `AGENTS.md` | `bash <skill-dir>/harness-init.sh init` |
| `retrofit` | project already has some `.claude`/`.codex`/`AGENTS.md`, or is mid-development (a real `CLAUDE.md`, hand-written subagents) | `bash <skill-dir>/harness-init.sh retrofit` |
| `plan` | preview what init/retrofit would create / merge / migrate (read-only) | `bash <skill-dir>/harness-init.sh plan` |
| `verify` | check presence / drift / dual-host parity (read-only) | `bash <skill-dir>/harness-init.sh verify` |
| `upgrade` | re-copy the vendored scripts + add any new hook | `bash <skill-dir>/harness-init.sh upgrade` |

`<skill-dir>` is this skill's installed directory (where `harness-init.sh` sits). `init` and
`retrofit` share one idempotent code path — when unsure which applies, run `retrofit`; it
creates what is missing and merges into what exists.

## Retrofitting a project mid-development

`retrofit` is not only for near-empty repos — it folds an in-flight project's existing agent
assets into the SSOT instead of stranding them. **Run `plan` first** to preview every
create / merge / migrate decision without writing anything.

- **A real `CLAUDE.md` and no `AGENTS.md`** → its prose is adopted as the `AGENTS.md` SSOT and
  `CLAUDE.md` is replaced with the symlink. A real `CLAUDE.md` *beside* a real `AGENTS.md` is left
  for you to merge by hand (the installer says which).
- **Hand-authored `.claude/agents/*.md` / `.codex/agents/*.toml`** (python3) → reverse-generated into
  `.agents/subagents/<name>/` sources (`generate-subagents.py --import`), then re-projected with
  the do-not-edit banner. A sourceless hand-authored projection is never silently pruned; without
  python3 the installer flags them instead (install python3, then `upgrade`).
- **Everything else** (hook configs, `.gitignore`, `package.json` scripts) is merged, never clobbered.

## Workflow

1. **Detect intent + state.** From the user's words pick the mode; confirm the target repo with `git rev-parse --show-toplevel` and note whether `.claude/`, `.codex/`, and `AGENTS.md` already exist. If ambiguous between init and retrofit, run `retrofit`.
2. **Run the installer** for that mode (table above). Useful flags: `--no-format-hook`, `--no-husky`, `--no-example-subagent`, `--force-scripts` (implied by `upgrade`). See `harness-init.sh --help`. The worktree flow's trunk is chosen per-call (`WORKTREE_TRUNK=… ` or `worktree.sh … --trunk <branch>`), not at install time.
3. **Finish the contract.** For `init`, fill the `AGENTS.md` TODO sections (project overview / commands / architecture) — keep it an entry point; link depth into `docs/`. For nested directories that deserve their own contract, drop in `templates/AGENTS.nested.md` and fill it (keep `<!-- Parent: ../AGENTS.md -->`). For a multi-directory codebase, generate a full parent-linked tree — see `reference.md` → *Generating the nested AGENTS.md tree*.
4. **Report** what was installed, what was merged vs created, what was skipped (e.g. subagents when python3 is unavailable), and the **Codex trust** reminder the installer prints.
5. **Verify** with `verify` mode (or the recipe in `reference.md`) before handing back.

## The installer at a glance

`harness-init.sh` copies the vendored scripts into `tools/agent/` + `.agents/`, **merges**
the dual-host hook wiring into `.claude/settings.json` and `.codex/hooks.json` (jq → python3 →
"paste this block" fallback), creates the `CLAUDE.md → AGENTS.md` symlink, seeds `.agents/{skills,subagents}/`
and the root `AGENTS.md`, appends the `.gitignore` lines, runs `relink-skills.sh`, and — when
python3 is available — installs the subagent generator + the pre-commit drift guard. Every step is
"create if missing, merge if present, skip if already done."

## Dual-host wiring (at a glance)

Both hosts call the **same** hook scripts under `tools/agent/hooks/`; only the invocation differs:

| | Claude Code (`.claude/settings.json`) | Codex (`.codex/hooks.json`) |
|---|---|---|
| Path resolution | `"$CLAUDE_PROJECT_DIR"/tools/agent/hooks/X.sh` | `bash -lc 'root="$(git rev-parse --show-toplevel)"; "$root/.../X.sh"'` |
| Matcher | `Edit\|MultiEdit\|Write\|NotebookEdit` (Pre) / `Edit\|MultiEdit\|Write` (Post) | `Edit\|Write\|apply_patch` |

The hook scripts resolve their own project root either way, so nothing host-specific leaks into them. **Codex only loads project-level `.codex/` for a TRUSTED project** — the installer prints how to trust it. Full snippets + rationale: `reference.md`.

## When subagents are available

The bash core (worktree flow, the 3 hooks, `relink-skills.sh`, both host configs, the `AGENTS.md`
contract) installs **everywhere**. The subagent generator (`generate-subagents.py`) and its
pre-commit `--check` drift guard need **python3** — no Node or `package.json`. Since the rest of the
harness already prefers python3 for hook JSON, subagents now install wherever the core does; without
python3 they are cleanly skipped, and the installer says how to enable them later.

## Coexistence with `npx skills`

`.agents/skills/` holds this **project's own** skills (SSOT). **Third-party** skills install
separately via `npx skills` and land as **real directories** in `.claude/skills/`; the relinker
only manages **symlinks**, so it never touches them. Keep project skill names distinct from
installed ones.

→ Deep reference (manifest, hook semantics, merge algorithm, AGENTS.md budget rationale,
Codex trust, troubleshooting, end-to-end test recipe): **`reference.md`**.
