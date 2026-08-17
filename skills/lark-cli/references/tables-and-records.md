# Tables and records

Read this only when the request involves Sheets or Base/多维表格, including worksheets, cells,
ranges, formulas, formatting, charts, pivots, records, fields, views, forms, dashboards, workflows,
roles, BaseApp/AppMode, or Workspace organization.

## Route by data model

- Use `sheets` for spreadsheet grids, A1 ranges, rows/columns, formulas, formatting, filters,
  conditional formatting, charts, pivots, comments, images, and worksheet structure.
- Use `base` for typed records and fields, tables/views/forms, dashboards, Base workflows, roles,
  advanced permissions, Workspace, and BaseApp/AppMode pages/components.
- A BaseApp/AppMode is a presentation/application layer over Base data; it is not a Miaoda/Spark
  app and must not be routed to the `apps` service.
- Search, import, export, move, or permission management for the containing cloud file belongs to
  Drive. Return here for data inside the Sheet/Base.

Path routing is host-independent: `/sheets/` means Sheets; `/base/` and Base-style `/app/` links mean
Base. Preserve the supplied token/URL exactly.

## Discover schema before mutation

```bash
lark-cli sheets --help
lark-cli base --help
lark-cli <service> +<shortcut> --help
lark-cli schema <service.resource.method>
```

Never infer field types, record schemas, enum values, A1 ranges, table/view IDs, or formula syntax
from a display label alone. Inspect existing metadata and a representative data sample first.

## Sheets workflow

1. Resolve the spreadsheet and worksheet IDs; identify the exact range and whether the operation
   changes values, formulas, styles, comments, dimensions, or objects.
2. Read the current range/structure. Preserve formulas and data types unless the user explicitly
   requests conversion.
3. Prefer one bounded batch write over per-cell loops when the installed shortcut/API supports it.
4. Preview large clears, replacements, row/column deletes, merges, and structure changes. Confirm
   destructive or bulk effects, then verify the affected range and formulas.
5. Do not claim a financial/modeling result merely because values were written; recalculate/read
   back outputs and surface formula errors or unsupported Excel functions.

## Base workflow

1. Resolve app/base, table, view, field, and record identifiers from metadata; never use field
   display names as IDs unless help explicitly accepts names.
2. Read field definitions before writing. Validate values against field type, required fields,
   linked-record cardinality, date/time semantics, formulas/lookups, and select options.
3. Use bounded batch record operations where supported. Preserve record IDs and report partial
   failures individually rather than retrying successful creates.
4. Treat role/member and advanced-permission changes as high impact: preview typed member IDs,
   scope, and affected resources; use dry-run when exposed and confirm before applying.
5. Verify created/updated records, view/filter behavior, workflow state, or AppMode component links
   with a focused read.

**Official coverage:** `lark-base`, `lark-sheets`.
