---
name: tooling-conventions
description: 'Use when adding, moving, renaming, splitting, or removing committed commands under tools/, scripts/, or bin/; auditing tooling sprawl; or establishing tool-surface governance. Covers public, installed, helper, break-glass, and packaged surfaces, failure-domain boundaries, safe command contracts, path migrations, and optional manifest reconciliation. Not for application source layout, documentation systems (use project-docs-organizer), or uncommitted throwaway scripts.'
---

# Tooling Conventions

Keep committed command surfaces discoverable and safe without imposing one universal
directory tree. The target repository owns names and roots; this skill supplies a routing
model, contract checks, and an optional reconciliation tool.

## Invariants

- Classify a command by who invokes it, the state or artifact it owns, its hazard model,
  and how success is verified—not merely by its filename or noun domain.
- Give each independent failure domain one authoritative public entry. Keep helpers private;
  do not hide distinct recovery, batch, or low-level jobs inside a mega-CLI.
- Preserve installed paths and service-bound commands unless every active consumer moves in
  the same coordinated change.
- Route dangerous actions through the project's authoritative deploy, install, upgrade, or
  release path; a generic skill must not invent that path.
- Add governance machinery only when current scale or drift justifies it.

## Workflow

1. Identify the job: add, move/rename/delete, or audit. Inventory the repository's actual
   command roots, callers, documentation, services, build/package surfaces, and existing gates.
2. Read [`surface-taxonomy.md`](references/surface-taxonomy.md) to classify each affected
   surface and test whether related commands share one failure domain.
3. For an addition, prefer an existing authoritative entry or subcommand when the failure
   domain matches. Otherwise place a new project-owned public entry, helper, package, installed,
   or break-glass surface deliberately.
4. When implementing or auditing executable behavior, apply
   [`script-contract.md`](references/script-contract.md). Keep project-specific CLI shape,
   formatters, languages, and deployment mechanics project-owned.
5. For a move, rename, or deletion, follow
   [`path-migrations.md`](references/path-migrations.md) and update all active consumers in the
   same change. Do not add a generic compatibility shim; unresolved external consumers are a
   coordination blocker, not permanent skill-owned machinery.
6. When the repository has enough commands or contributors for drift to recur, adapt
   [`manifest-schema.md`](references/manifest-schema.md) and run:

   ```bash
   bash <skill-dir>/scripts/manifest-check.sh <path/to/tools-manifest.tsv>
   ```

7. Run the smallest complete verification set from
   [`verification.md`](references/verification.md), plus existing domain tests and any required
   real-target smoke.

## Output contract

Report the affected command surfaces, classification and placement decisions, active callers
updated, checks run, and any external coordination still required. In audit-only work, present
ranked candidates and evidence; do not mass-move commands without change authorization.

## On-demand references

| Need | Reference |
|---|---|
| Classify surfaces, choose placement, or decide aggregate versus toolkit | [`surface-taxonomy.md`](references/surface-taxonomy.md) |
| Implement help, exit, resolver, hazard, secret, atomicity, and logging behavior | [`script-contract.md`](references/script-contract.md) |
| Move, rename, or delete a command and reconcile callers | [`path-migrations.md`](references/path-migrations.md) |
| Adopt the optional TSV surface inventory | [`manifest-schema.md`](references/manifest-schema.md) |
| Select syntax, help, dry-run, manifest, stale-reference, and real-target checks | [`verification.md`](references/verification.md) |
