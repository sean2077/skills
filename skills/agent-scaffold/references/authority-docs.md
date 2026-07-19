# Agent Scaffold Authority Documents

Read this only when changing AGENTS.md or CLAUDE.md governance, budgets, or nested contracts.

## AGENTS.md authority and lifecycle

`AGENTS.md` (root plus any applicable on-demand nested contracts; root `CLAUDE.md` is a symlink to
it) is the canonical repository-level **Agent work contract**. It governs Agent behavior, commands,
constraints, and navigation. It is not the factual source of truth for every product behavior,
configuration value, schema, API, or architecture decision; those remain owned by the relevant
source, configuration, specification, or topic documentation. Higher-priority instructions still
govern.

The managed contract publishes four common laws:

- **Keep it current.** Close contract or linked-document drift in the same durable change.
- **Keep it lean.** Keep only concise, actionable, high-value guidance resident.
- **Keep scopes honest.** Put global rules at the root and create nested contracts only for real
  local differences.
- **Resolve conflicts explicitly.** Never silently guess, ignore a contract, or follow known-stale
  guidance when applicable instructions or verified repository facts materially disagree.

### Maintenance trigger and ownership

A **durable Agent-relevant change** is a lasting change to something future Agent work must know:

- a build, test, lint, generation, run, release, or recovery command;
- an invariant, convention, registration point, or architectural boundary;
- an ownership, security, data-handling, review, or other risk boundary; or
- a path or navigation entry that the contract tells Agents to use.

The change author owns the documentation closure, and the reviewer checks semantic freshness. If
the change makes resident guidance false, incomplete, or misleading, update or remove that guidance
in the same change. If the affected detail belongs in linked project docs, update it there and keep
the contract's concise summary and link accurate. Ordinary implementation changes that do not alter
durable Agent guidance require neither an `AGENTS.md` edit nor a boilerplate review declaration.

### Resident rules and routed detail

Keep a **resident rule** only when it directly changes Agent behavior and is frequently needed or
costly to miss. Keep it concise and actionable. Route depth to the target project's established
documentation location (conventionally `docs/`) and link it from the contract when the link helps an
Agent act correctly.

| Keep resident in `AGENTS.md` | Route to project docs |
|---|---|
| Commands Agents repeatedly need | Long procedures and troubleshooting trees |
| Non-obvious invariants and ownership boundaries | Rationale, history, and design narrative |
| High-cost safety, security, or data rules | Extended examples and tutorials |
| Short navigation to an authoritative source | Low-frequency background and reference detail |

The `authority_doc_budget.sh` hook remains advisory. Its defaults are 320 lines / 25,600 characters
for the root and 120 lines / 9,600 characters for nested contracts. Override them with
`AUTHORITY_DOC_MAX_ROOT`, `AUTHORITY_DOC_MAX_NESTED`, `AUTHORITY_DOC_MAX_ROOT_CHARS`, or
`AUTHORITY_DOC_MAX_NESTED_CHARS`. These measurements are signals, not substitutes for the semantic
admission rule. The character defaults retain the former line budgets' approximate 80-column
capacity without requiring source hard-wrap. Do not hard-fail solely on size or compress prose
mechanically to satisfy a number.

### Conflict handling

Use the root contract plus its most specific applicable nested-contract chain. When applicable
instructions conflict, obey the higher-priority instruction. When contract guidance disagrees with
verified repository facts, treat that as possible contract drift rather than silently using the
facts as permission to violate the contract. Surface the material conflict, request user or project
owner direction when authority is unclear, and repair stale lower-level guidance in the same change
when authorized.

This policy does not add a universal pull-request checkbox, periodic audit workflow, hard line gate,
new documentation tree, or automated semantic conflict resolver.

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

The managed template uses semantic source lines: one paragraph, list item, table row, or command per
physical line. It does not hard-wrap prose to a fixed display width. The installer applies this
convention only inside the managed markers and does not reflow project-owned prose outside them.

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
