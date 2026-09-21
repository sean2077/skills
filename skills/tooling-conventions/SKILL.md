---
name: tooling-conventions
description: "Use when committed project commands need to be added, moved, renamed, split, removed, audited, or have their placement and safety designed. Not for routine internal edits, application layout, or disposable scripts."
---

# Tooling Conventions

Keep committed command surfaces discoverable and safe within the target project's conventions.

Understand each affected job, invoker, owned state or artifact, failure/recovery behavior, and verification. Give independently invokable jobs authoritative entries and keep implementation helpers private.

Merge duplicate commands where their state, failure, and verification boundaries align. Preserve independent recovery paths. Treat installed paths and service-bound commands as external contracts until their consumers migrate.

Use the project's established placement and interfaces. Compare alternatives for unresolved boundary decisions, retaining consequential rationale in the existing design process.

Derive validation, secrets handling, preview, rollback, and repeatability from actual effects. Use established deploy, install, and release paths for dangerous actions.

For moves, renames, or deletions, reconcile services, packages, CI, runbooks, skills, templates, and generated examples. Verify affected behavior and paths, and identify external coordination still needed. Audit-only requests call for findings rather than relocation.

## References

| Need | Reference |
|---|---|
| Decide aggregation, splitting, or placement | [Classification methods](references/classification-methods.md) |
| Implement or audit safety-relevant command behavior | [Script contract](references/script-contract.md) |
| Move, rename, or delete entries and reconcile callers | [Path migrations](references/path-migrations.md) |
| Adopt or check a structural inventory | [Inventory contract](references/inventory-contract.md) |
| Migrate a surface manifest | [Surface-manifest migration](references/migration-from-surface-manifest.md) |
| Select checks for the changed command surface | [Verification](references/verification.md) |

For a project-owned inventory, run:

```bash
bash <skill-dir>/scripts/inventory-check.sh [--] <path/to/tools-inventory.tsv>
```
