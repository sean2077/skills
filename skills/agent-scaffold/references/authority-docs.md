# Agent Scaffold Authority Documents

Read this only when changing AGENTS.md or CLAUDE.md governance, budgets, or nested contracts.

## AGENTS.md governance and budget

`AGENTS.md` (root plus any on-demand nested contracts; root `CLAUDE.md` is a symlink to it) is an **entry
point, not a detail dump** — put depth in `docs/` and link back; inline only important,
frequently-needed points. The `authority_doc_budget.sh` hook advises when a contract crosses its
line budget (root 320 / nested 120). Nested contracts carry `<!-- Parent: ... -->` pointing to the
nearest existing ancestor contract and stay subordinate to the root.

**Apply never overwrites a hand-authored `AGENTS.md`.** The installer manages only the marked
block:

- No `AGENTS.md` → create it with only the managed harness block.
- `AGENTS.md` with the markers → replace **only** the block, preserving surrounding prose.
- `AGENTS.md` without the markers → append the block (review placement).
- Unbalanced, duplicated, or reversed markers → abort before target mutation; repair the marker
  pair manually, then rerun `plan` or the requested install/upgrade command.

Keep project prose **outside** the `<!-- agent-scaffold:start … end -->` markers; `upgrade`
refreshes everything between them. The template's inner worktree boundary is installer-owned:
`--profile light` removes that complete policy and its worktree-only layout rows.

### Project-owned root prose

Add only the sections the project can keep accurate. A useful starting shape is a reference, not
scaffold-owned content:

```markdown
# PROJECT — Agent Contract

## Project Overview

<!-- What the project is, who it serves, and its headline technology. -->

## Development Commands

<!-- The small set of build, test, lint, and run commands agents actually use. -->

## Architecture

<!-- Load-bearing modules and links to deeper docs; keep this an index. -->
```

Place that prose before or after the managed block. The scaffold never fills, refreshes, or judges
those project sections.

When the contract lives in a **real `CLAUDE.md`** with no `AGENTS.md` yet, apply adopts that
prose as the `AGENTS.md` SSOT and replaces `CLAUDE.md` with the symlink — see
[`retrofit.md`](retrofit.md#adopt-an-existing-claudemd).

### Creating nested AGENTS.md on demand

The root contract is sufficient by default. A multi-directory layout, source / config / asset
files, or a useful directory description does **not** by itself justify another instruction file.
Create a nested `AGENTS.md` only when the directory has at least one **local difference** from the
nearest ancestor contract:

- a different build, test, lint, generation, or release command;
- a local invariant, convention, ownership boundary, or registration point; or
- a stronger risk, security, data-handling, or review boundary.

When a local difference exists:

- **Start from the local delta.** State the differing guidance first. Purpose, key-file, or
  dependency notes are optional and belong only when they help apply that guidance; never create
  the file merely to hold a directory map.
- **Link to the nearest contract.** Set `<!-- Parent: ... -->` to the nearest ancestor directory
  that actually has an `AGENTS.md`. Sparse trees may need `../../AGENTS.md` (or deeper); do not
  create empty intermediary contracts just to keep every parent path at `../AGENTS.md`.
- **Validate the sparse chain.** Every nested parent path resolves and chains to the single root
  without orphans or cycles, and each nested file contains a concrete local difference while
  staying under the 120-line budget.

Reference skeleton:

```markdown
<!-- Parent: ../AGENTS.md -->
<!-- Subordinate to the parent-linked AGENTS.md chain. -->

# <directory>/

## Local Differences

<!-- Required: the command, invariant, ownership boundary, or risk boundary that differs. -->

## Purpose

<!-- Optional: include only when it helps apply the local differences. -->

## Key Files

<!-- Optional: list only files needed to apply the local differences. -->
```

This creation policy does not scan, rewrite, or delete existing nested contracts.
