---
name: agent-scaffold
description: 'Use when setting up, standardizing, retrofitting, planning, diagnosing, verifying, or upgrading a vendored dual-host Claude Code + Codex agent harness. Covers .agents/ SSOT, real-symlink projections, AGENTS.md/CLAUDE.md migration, hooks, subagent import/generation, and optional worktree/trunk-guard governance, including --no-worktree. Modes: init, retrofit, plan, doctor, verify, upgrade. Not for one commit message (use conventional-commit), authoring a standalone CLAUDE.md when no harness is wanted, or third-party skill installation (use npx skills).'
compatibility: Requires git, Python 3.8 or newer, and Bash 3.2 or newer. Windows requires Git Bash plus native file and directory symlink privilege.
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
- retrofit the default worktree flow, or install the lighter `--no-worktree` profile while retaining the rest of the harness
- check an existing harness for drift or parity across the two hosts (`verify`)
- refresh the vendored harness scripts after this skill is updated (`upgrade`)

Do **not** use this skill for:

- writing a single commit message → `conventional-commit`
- installing third-party skills → `npx skills add <repo> -a claude-code -a codex` (coexists; see below)
- authoring one standalone `CLAUDE.md` with no harness → just write the file

## Invariants

- **Worktree governance is default-on but optional.** The default profile starts every change in `.worktrees/<name>` and enforces that with `trunk_edit_guard.sh`. `--no-worktree` omits that policy, lifecycle script, guard wiring, and new worktree ignore entries while preserving the SSOT, documentation, formatting, and subagent layers.
- **`.agents/` is the SSOT; `.claude/`/`.codex/` are projections.** Skills project as symlinks (`relink-skills.sh`); subagents project via the python generator. **Never hand-edit** generated `.claude/agents/*.md` or `.codex/agents/*.toml`.
- **Real symlinks are a hard prerequisite.** `doctor`, every mutating mode, and `relink-skills.sh` probe file + directory links first. Unsupported hosts exit 2 before target mutation; there is no copy fallback.
- **Hook configs are reconciled, never clobbered.** The installer refreshes only enabled managed entries beside existing user hooks and removes only disabled managed identities. Invalid, structurally incompatible, or symlinked existing hook configs stop before target mutation with a named error.
- **`CLAUDE.md` is a symlink to `AGENTS.md`.** `AGENTS.md` is an entry point, not a detail dump (the budget hook advises when it grows too large).
- **The installer is idempotent for the same profile flags.** Re-running a mode with the same options changes nothing already in place; changing profile flags intentionally reconciles to that profile.

## Modes

| Mode | When | Command (run from the target repo root) |
|---|---|---|
| `init` | greenfield — no `.claude/`, `.codex/`, or `AGENTS.md` | `bash <skill-dir>/harness-init.sh init` |
| `retrofit` | project already has some `.claude`/`.codex`/`AGENTS.md`, or is mid-development (a real `CLAUDE.md`, hand-written subagents) | `bash <skill-dir>/harness-init.sh retrofit` |
| `plan` | preview what init/retrofit would create / merge / migrate (read-only) | `bash <skill-dir>/harness-init.sh plan` |
| `doctor` | check Python, effective git symlink config, and real file/directory link capability (read-only) | `bash <skill-dir>/harness-init.sh doctor` |
| `verify` | check presence / drift / dual-host parity (read-only) | `bash <skill-dir>/harness-init.sh verify` |
| `upgrade` | re-copy the vendored scripts + add any new hook | `bash <skill-dir>/harness-init.sh upgrade` |

`<skill-dir>` is this skill's installed directory (where `harness-init.sh` sits). `init` and
`retrofit` share one idempotent code path — when unsure which applies, run `retrofit`; it
creates what is missing and merges into what exists.

Append `--no-worktree` to `plan`, `init`/`retrofit`, `upgrade`, and `verify` for the lightweight
profile. Flags are intentionally per-invocation: repeat it on later `upgrade`/`verify` runs;
omitting it selects the default worktree profile again. A clean lightweight install omits the
scripts; a default→light upgrade leaves existing copies dormant and removes only managed
policy/hook wiring.

## Retrofitting a project mid-development

`retrofit` is not only for near-empty repos — it folds an in-flight project's existing agent
assets into the SSOT instead of stranding them. **Run `plan` first** to preview every
create / merge / migrate decision without writing anything.

- **A real `CLAUDE.md` and no `AGENTS.md`** → its prose is adopted as the `AGENTS.md` SSOT and
  `CLAUDE.md` is replaced with the symlink. A real `CLAUDE.md` *beside* a real `AGENTS.md` is left
  for you to merge by hand (the installer says which).
- **Hand-authored `.claude/agents/*.md` / `.codex/agents/*.toml`** → reverse-generated into
  `.agents/subagents/<name>/` sources (`generate-subagents.py --import`), then re-projected with
  the do-not-edit banner. A sourceless hand-authored projection is never silently pruned; import
  conflicts stop before projection writes.
- **Everything else** (hook configs, `.gitignore`, `package.json` scripts) is merged, never clobbered.

## Workflow

1. **Detect intent + state.** From the user's words pick the mode; confirm the target repo with `git rev-parse --show-toplevel` and note whether `.claude/`, `.codex/`, and `AGENTS.md` already exist. If ambiguous between init and retrofit, run `retrofit`.
2. **Run the installer** for that mode (table above). Useful flags: `--no-worktree`, `--no-format-hook`, `--no-husky`, `--no-example-subagent`, `--force-scripts` (implied by `upgrade`). See `harness-init.sh --help`. When enabled, the worktree flow's trunk is chosen per-call (`WORKTREE_TRUNK=… ` or `worktree.sh … --trunk <branch>`), not at install time.
3. **Finish the contract.** For `init`, fill the `AGENTS.md` TODO sections (project overview / commands / architecture) — keep it an entry point; link depth into `docs/`. For nested directories that deserve their own contract, drop in `templates/AGENTS.nested.md` and fill it (keep `<!-- Parent: ../AGENTS.md -->`). For a multi-directory codebase, generate a full parent-linked tree — see `reference.md` → *Generating the nested AGENTS.md tree*.
4. **Report** what was installed, what was merged vs created, any preflight stop, and the **Codex trust** reminder the installer prints.
5. **Verify** with `verify` mode (or the recipe in `reference.md`) before handing back.

## The installer at a glance

`harness-init.sh` resolves Python 3.8+ before every mode. In mutating modes it rejects deterministic
contract, skill-projection, and subagent-import conflicts before the real-link doctor or any target write.
It then copies the selected vendored scripts into `tools/agent/` + `.agents/`, **reconciles only owned hook
entries** in `.claude/settings.json` and `.codex/hooks.json` (Python; user hooks remain), creates the
`CLAUDE.md → AGENTS.md` symlink, seeds `.agents/{skills,subagents}/`
and the root `AGENTS.md`, appends the selected `.gitignore` lines, runs `relink-skills.sh`, installs
and runs the subagent generator. When drift-hook wiring is enabled, eligible Husky projects are
updated automatically; alternate managers or no-package projects receive manual guidance. Every step is
"create if missing, merge if present, skip if already done."

## Dual-host wiring (at a glance)

Both hosts call the **same** hook scripts under `tools/agent/hooks/`; only the invocation differs:

| | Claude Code (`.claude/settings.json`) | Codex (`.codex/hooks.json`) |
|---|---|---|
| Path resolution | `bash -lc` + `$CLAUDE_PROJECT_DIR`, normalized with `cygpath` on Windows | `bash -lc` + `git rev-parse --show-toplevel` |
| Matcher | `Edit\|MultiEdit\|Write\|NotebookEdit` (Pre) / `Edit\|MultiEdit\|Write` (Post) | `Edit\|Write\|apply_patch` |

The hook scripts resolve their own project root either way, so nothing host-specific leaks into them. **Codex only loads project-level `.codex/` for a TRUSTED project** — the installer prints how to trust it. Full snippets + rationale: `reference.md`.

## Platform support

macOS, Linux, and **Windows (Git Bash only)**. Bash 3.2 is the shell baseline. Bundled scripts are
**LF-only** (the installer writes `.gitattributes` rules; CRLF breaks bash), and every internal
shell dispatch explicitly uses `bash` rather than relying on executable-bit checkout behavior.
Real file and directory symlinks are mandatory: unsupported hosts stop before mutation with
remediation, never a copy. Windows setup and degraded-checkout recovery: `reference.md` §11.

## Runtime prerequisites

The harness requires **git, Python 3.8+, and Bash 3.2+**. Each Python candidate is executed with a
3.8+ probe before selection, in order: `PYTHON_BIN`, `python`, `python3`, then `py -3`; an unusable
or older candidate falls through. Python owns real-link creation, hook JSON parsing, and subagent
projection, so an install never quietly loses SSOT or guard behavior because Python is absent.
Node and `package.json` remain optional; they only enable npm/Husky conveniences.

## Coexistence with `npx skills`

`.agents/skills/` holds this **project's own** skills (SSOT). **Third-party** skills install
separately via `npx skills` and land as **real directories** in `.claude/skills/`; the relinker
only manages **symlinks**, so it never touches them. Keep project skill names distinct from
installed ones.

→ Deep reference (manifest, hook semantics, merge algorithm, AGENTS.md budget rationale,
Codex trust, troubleshooting, end-to-end test recipe): **`reference.md`**.
