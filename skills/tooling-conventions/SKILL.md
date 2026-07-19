---
name: tooling-conventions
description: 'Use when adding, moving, renaming, splitting, or removing committed commands under a project-owned tool root; auditing tooling sprawl; or establishing contextual command governance. Derives job boundaries, contract profiles, placement decisions, safe command contracts, path migrations, and optional structural inventory checks without imposing one directory tree or semantic schema. Not for application source layout, documentation systems (use project-docs-organizer), or uncommitted throwaway scripts.'
---

# Tooling Conventions

Keep committed command surfaces discoverable and safe without imposing a universal directory
tree or classification schema. The target repository owns names and roots; this skill supplies
evidence-led boundary methods, contract checks, and an optional structural inventory tool.

## Invariants

- Derive command boundaries from the job, invoker, owned state or artifact, failure/rollback
  model, and verification—not from filenames, noun domains, or the current directory tree.
- Give each independent Job Boundary one authoritative entry. Keep helpers private; do not hide
  distinct recovery, batch, audit, or low-level jobs inside a happy-path mega-CLI.
- Build a Contract Profile before choosing placement. Installed paths and service-bound commands
  remain external contracts until every active consumer moves in one coordinated change.
- Keep project-specific roots, names, semantic metadata, CLI shape, languages, and deployment
  mechanics project-owned. Require safe outcomes without inventing flags, exit numbers, resolver
  languages, logging formats, or write mechanisms.
- There is no required `tools/`, `scripts/`, or `bin/` root and no mandatory semantic inventory
  schema; only the structural `path` contract is universal when an inventory is adopted.
- Route dangerous actions through the project's authoritative deploy, install, upgrade, or
  release path; a generic skill must not invent that path.
- Add inventories or other governance machinery only when current scale or recurring drift
  justifies them.

## Workflow

1. Identify the job: add, move/rename/delete, or audit. Inventory actual command roots, callers,
   docs, services, build/package consumers, project vocabulary, ownership, and existing gates.
2. Read [`classification-methods.md`](references/classification-methods.md). Select only lenses
   supported by project evidence; method cards are not required categories or directory names.
3. Establish Job Boundaries independently of layout. Aggregate duplicate entries only when they
   own the same job with compatible state/artifact, failure/rollback, and verification semantics.
4. Build each affected command's Contract Profile, then derive roots, grouping, paths, and names
   from the target project's coherent conventions. A physical directory never defines a job.
5. Before recommending or applying a Placement Decision, output the **Tool Governance Decision
   Record** defined in `classification-methods.md`.
6. When implementing or auditing executable behavior, derive only the applicable command-contract
   cards from the Contract Profile in [`script-contract.md`](references/script-contract.md).
7. For a move, rename, or deletion, follow [`path-migrations.md`](references/path-migrations.md)
   and update all active consumers in the same coordinated change.
8. When recurring drift justifies a machine inventory, adapt
   [`inventory-contract.md`](references/inventory-contract.md) and run:

   ```bash
   bash <skill-dir>/scripts/inventory-check.sh [--] [path/to/inventory.tsv]
   ```

9. Existing users of the retired flat surface manifest follow
   [`migration-from-surface-manifest.md`](references/migration-from-surface-manifest.md); there is
   no compatibility wrapper or silent semantic downgrade.
10. Run the smallest complete verification set from
    [`verification.md`](references/verification.md), plus existing domain tests and any required
    real-target smoke.

## Output contract

Report the Tool Governance Decision Record, affected authoritative entries and helpers, active
callers updated, checks run, and external coordination still required. In audit-only work,
present ranked candidates and evidence; do not mass-move commands without change authorization.

## On-demand references

| Need | Reference |
|---|---|
| Derive Job Boundaries, Contract Profiles, and project-owned placement | [`classification-methods.md`](references/classification-methods.md) |
| Derive fail-closed input, resolver, state, secret, output, and preview behavior from command evidence | [`script-contract.md`](references/script-contract.md) |
| Move, rename, or delete a command and reconcile callers | [`path-migrations.md`](references/path-migrations.md) |
| Adopt the optional path-only structural inventory | [`inventory-contract.md`](references/inventory-contract.md) |
| Migrate the retired flat surface manifest and checker | [`migration-from-surface-manifest.md`](references/migration-from-surface-manifest.md) |
| Select syntax, help, dry-run, inventory, stale-reference, and real-target checks | [`verification.md`](references/verification.md) |
