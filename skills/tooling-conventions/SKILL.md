---
name: tooling-conventions
description: 'Use when committed project commands need to be added, moved, renamed, split, removed, audited, or governed consistently. Not for application source layout, documentation systems, or uncommitted throwaway scripts.'
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
- Build a Contract Profile before choosing placement. Installed paths and service-bound commands remain external contracts until every active consumer moves in one coordinated change. README snippets, runbooks, skill references, templates, and generated examples count as consumers.
- Scale decision evidence to the contract change. Use a compact inline decision delta when a
  bounded maintenance change preserves the Job Boundary, Contract Profile, placement, and every
  active consumer contract; use a full Tool Governance Decision Record when any of them changes or project/user policy explicitly requires it.
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
5. Before recommending or applying a change, output the proportionate decision artifact defined
   in `classification-methods.md`: a compact inline delta for contract-preserving maintenance, or
   the full **Tool Governance Decision Record** for a material boundary, contract, or placement decision.
6. When implementing or auditing executable behavior, derive only the applicable command-contract
   cards from the Contract Profile in [`script-contract.md`](references/script-contract.md).
7. For a move, rename, or deletion, follow [`path-migrations.md`](references/path-migrations.md) and update all active consumers, including copy-paste documentation commands, in the same coordinated change.
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

Report the decision artifact, affected authoritative entries and helpers, active callers updated,
checks run, and external coordination still required. In audit-only work, present ranked candidates
and evidence; do not mass-move commands without change authorization.

## On-demand references

| Need | Reference |
|---|---|
| Scale decision evidence; derive Job Boundaries, Contract Profiles, and project-owned placement | [`classification-methods.md`](references/classification-methods.md) |
| Derive fail-closed input, resolver, state, secret, output, and preview behavior from command evidence | [`script-contract.md`](references/script-contract.md) |
| Move, rename, or delete a command and reconcile callers | [`path-migrations.md`](references/path-migrations.md) |
| Adopt the optional path-only structural inventory | [`inventory-contract.md`](references/inventory-contract.md) |
| Migrate the retired flat surface manifest and checker | [`migration-from-surface-manifest.md`](references/migration-from-surface-manifest.md) |
| Select syntax, help, dry-run, inventory, stale-reference, and real-target checks | [`verification.md`](references/verification.md) |
