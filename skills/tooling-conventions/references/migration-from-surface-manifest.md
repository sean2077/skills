# Surface Manifest Migration

## Ownership mapping

| retired concept | new owner |
|---|---|
| `public` / `helper` | Invoker-or-entry lens, job boundary, and project-owned entry policy |
| `installed` | distribution contract, including the installed/service-bound path |
| `break-glass` | Hazard/recovery/verification lens plus a project-owned trigger |
| `paused` / `legacy` | Lifecycle-or-authority lens plus activation/replacement policy |
| `package` / `native` / `template` / `vendor` | Implementation-form-or-provenance lens and project build/vendor policy |
| `domain` / `audience` | Relevant boundary evidence or project policy—not universal values |
| `entry_for` | job boundary and authoritative-entry decision |
| `hazard` / `verify` | command contract and project-owned policy/tests |
| `called_by`, `installed_path`, `trigger`, `activation_gate`, `replacement`, provenance fields | project policy where reviewers or automation still consume them |

## Migration

1. Inventory every active caller of the old checker, manifest path, environment variables, CI
   job, docs route, and derived human view. An unresolved external consumer blocks the breaking
   release.
2. Preserve the consequential migration rationale in the existing task or project-required
   decision record. Map fields from their actual consumers and semantics.
3. Create a structural TSV with required `path`, optional `audit_level`, and only the project
   semantic columns that still have a named owner or automated consumer.
4. Move semantic validation into a project policy wrapper/test, then invoke:

   ```bash
   bash <skill-dir>/scripts/inventory-check.sh [--] [path/to/inventory.tsv]
   ```

5. Replace `MANIFEST_CHECK_SKIP` with the project-owned `INVENTORY_CHECK_SKIP` override when
   needed. Keep or set `TOOLS_DIR` when the inventory is outside the governed command root.
6. Delete old checker calls and obsolete schema guidance in the same coordinated change. Search
   all active docs, CI, skills, units, packaging, and service callers before declaring the cut
   complete.
7. Record the change as breaking. Coordinate any transition required by consumers that cannot move together.
