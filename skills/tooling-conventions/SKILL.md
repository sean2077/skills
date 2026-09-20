---
name: tooling-conventions
description: "Use to design or audit committed command boundaries, placement, safety, or path migrations. Not for routine internal edits, application layout, or disposable scripts."
---

# Tooling Conventions

Keep committed command surfaces discoverable and safe. The target repository owns names and roots; no universal directory layout, taxonomy, or decision template is imposed.

## Boundary contract

- Understand the affected job, invoker, owned state/artifact, failure and rollback behavior, and verification before changing its public contract. Reuse existing knowledge rather than producing a separate Contract Profile for routine maintenance.
- Give each independently invokable job an authoritative entry and keep helpers private. Merge duplicate commands only when state, failure, and verification boundaries align; do not bury independent recovery jobs inside a happy-path mega-CLI.
- Installed paths and service-bound commands remain external contracts until active consumers migrate together. Callers include services, packages, CI, runbooks, skills, templates, and generated examples.
- Preserve coherent project placement and interfaces. Compare alternatives only for a real boundary decision; record consequential rationale in the existing task/design rather than mandating a Tool Governance Decision Record. Project-required records still apply.
- Derive input validation, secrets handling, preview, rollback, and repeatability from actual risks. Do not invent flags, exit codes, languages, logging formats, or deployment mechanisms. Dangerous actions use the project's authorized deploy/install/release path.
- There is no required `tools/`, `scripts/`, or `bin/` root and no mandatory semantic inventory schema. Only the structural `path` contract is universal when an inventory is adopted; adopt one only for demonstrated scale or recurring drift.

For a move, rename, or deletion, reconcile all active consumers and report external coordination that cannot be completed here. Verify the changed behavior and path contracts with the smallest complete set of relevant checks, including real-target smoke only when required and authorized. An audit alone does not authorize mass relocation.

## On-demand references

| Need | Reference |
|---|---|
| Decide aggregation, splitting, or placement when existing boundaries are insufficient | [Classification methods](references/classification-methods.md) |
| Implement or audit command behavior with safety-relevant effects | [Script contract](references/script-contract.md) |
| Move, rename, or delete entries and reconcile callers | [Path migrations](references/path-migrations.md) |
| Adopt or check an explicitly selected structural inventory | [Inventory contract](references/inventory-contract.md) |
| Migrate an existing retired surface manifest | [Surface-manifest migration](references/migration-from-surface-manifest.md) |
| Select syntax, help, preview, inventory, stale-reference, or real-target checks | [Verification](references/verification.md) |

When inventory reconciliation is selected, run the installed tool against the explicit project-owned inventory:

```bash
bash <skill-dir>/scripts/inventory-check.sh <path/to/tools-inventory.tsv>
```
