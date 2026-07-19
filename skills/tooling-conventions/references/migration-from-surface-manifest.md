# Migrate From the Retired Surface Manifest

Read this only when a project consumes the former flat surface manifest or
`<skill-dir>/scripts/manifest-check.sh`. This is an explicit breaking migration:
there is no compatibility wrapper, legacy mode, or silent weakening of semantic checks.

## Ownership mapping

| retired concept | new owner |
|---|---|
| `public` / `helper` | Invoker-or-entry lens, Job Boundary, and project-owned entry policy |
| `installed` | Distribution Contract, including the installed/service-bound path |
| `break-glass` | Hazard/recovery/verification lens plus a project-owned trigger |
| `paused` / `legacy` | Lifecycle-or-authority lens plus activation/replacement policy |
| `package` / `native` / `template` / `vendor` | Implementation-form-or-provenance lens and project build/vendor policy |
| `domain` / `audience` | Relevant boundary evidence or Project Tool Policy—not universal values |
| `entry_for` | Job Boundary and authoritative-entry decision |
| `hazard` / `verify` | Contract Profile and project-owned policy/tests |
| `called_by`, `installed_path`, `trigger`, `activation_gate`, `replacement`, provenance fields | Project Tool Policy where reviewers or automation still consume them |

## Hard-cut procedure

1. Inventory every active caller of the old checker, manifest path, environment variables, CI
   job, docs route, and derived human view. An unresolved external consumer blocks the breaking
   release.
2. Write the Tool Governance Decision Record. Re-evaluate legacy rows with the method cards;
   do not mechanically translate one flat label into another mandatory enum.
3. Create a structural TSV with required `path`, optional `audit_level`, and only the project
   semantic columns that still have a named owner or automated consumer.
4. Move semantic validation into a Project Tool Policy wrapper/test, then invoke:

   ```bash
   bash <skill-dir>/scripts/inventory-check.sh [--] [path/to/inventory.tsv]
   ```

5. Replace `MANIFEST_CHECK_SKIP` with the project-owned `INVENTORY_CHECK_SKIP` override when
   needed. Keep or set `TOOLS_DIR` when the inventory is outside the governed command root.
6. Delete old checker calls and obsolete schema guidance in the same coordinated change. Search
   all active docs, CI, skills, units, packaging, and service callers before declaring the cut
   complete.
7. Record the change as breaking. Do not create or retain a generic shim; if consumers cannot
   move together, stop at the coordination boundary.
