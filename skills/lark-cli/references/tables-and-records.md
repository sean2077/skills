# Tables and records

Read this only when the request involves Sheets or Base/多维表格, including worksheets, cells,
ranges, formulas, formatting, records, fields, views, forms, dashboards, workflows, roles, or
BaseApp/AppMode.

## Fast-path contract

For the documented shortcuts below, execute directly. Do not preflight `sheets --help`,
`base --help`, shortcut help, schema, workbook inspection, or URL resolution when the needed URL,
token, sheet/table ID, and range are already supplied.

- Known Sheet URL + sheet name/range: normally one read or one write command.
- Known Base token + table ID: normally one query/write command; do not resolve the Base again.
- Base URL without coordinates: one `+url-resolve`, then the requested operation.
- Base title only: one `+title-resolve`, then the requested operation.
- Inspect workbook/table/field metadata only when the operation truly depends on unknown structure.
- Batch rows, cells, records, or styles instead of looping one command per item.

Use `sheets` for spreadsheet grids and `base` for typed records. A BaseApp/AppMode is a
presentation layer over Base data, not a Miaoda/Spark app. Route `/sheets/` to Sheets and `/base/`
or Base-style `/app/` links to Base regardless of hostname. Preserve URLs/tokens exactly.

## Sheets read fast paths

Read ordinary values as CSV. Omit `--range` to read the whole named sheet; do not first probe row
or column counts merely to construct a range.

```bash
lark-cli sheets +csv-get --url '<sheet-url>' --sheet-name '<sheet>' --as user
lark-cli sheets +csv-get --url '<sheet-url>' --sheet-name '<sheet>' \
  --range 'A1:F50' --as user
```

Read formula/style/comment details only when requested or needed for a dependent edit:

```bash
lark-cli sheets +cells-get --url '<sheet-url>' --sheet-name '<sheet>' \
  --range 'A1:F50' --include value,formula,style,comment,data_validation --as user
```

Use `+workbook-info` only when sheet names/IDs or workbook-wide objects are unknown. Use
`+sheet-info` only for layout facts such as merges, hidden dimensions, row heights, or column
widths. A simple value read needs neither.

## Sheets write fast paths

For plain text that may safely use CSV coercion:

```bash
lark-cli sheets +csv-put --url '<sheet-url>' --sheet-name '<sheet>' \
  --start-cell 'A2' --csv '<csv-text>' --as user
```

Do not use plain CSV for identifiers with leading zeroes, dot-formatted dates, or values that need
numeric/date/percentage semantics. Use typed table input for ordinary rectangular business data:

```bash
lark-cli sheets +table-put --url '<sheet-url>' \
  --sheets '{"sheets":[{"name":"Data","columns":["ID","Amount"],"dtypes":{"ID":"object","Amount":"float"},"data":[["001",12.5]]}]}' \
  --as user
```

Use `+cells-set` for formulas, rich cells, exact rectangular placement, or sparse writes. `--cells`
is always a two-dimensional array, even for one cell; use `--writes` when one request changes
multiple ranges.

```bash
lark-cli sheets +cells-set --url '<sheet-url>' --sheet-name '<sheet>' --range 'A1:B1' \
  --cells '[[{"value":"名称"},{"formula":"=SUM(B2:B9)"}]]' --as user
```

Apply compatible styling in one command rather than repeated cell-format calls:

```bash
lark-cli sheets +styles-put --url '<sheet-url>' --styles - --as user <<'JSON'
{"styles":[{"name":"Data","cell_styles":[{"range":"A1:D1","font_weight":"bold"}],"col_sizes":[{"range":"A:D","type":"pixel","size":120}],"freeze":{"rows":1}}]}
JSON
```

Known structural fast paths include:

```bash
lark-cli sheets +dim-freeze --url '<sheet-url>' --sheet-name '<sheet>' --rows 1 --cols 0 --as user
lark-cli sheets +dim-insert --url '<sheet-url>' --sheet-name '<sheet>' --position 3 --count 2 --inherit-style before --as user
lark-cli sheets +cols-resize --url '<sheet-url>' --sheet-name '<sheet>' --range 'A:C' --width 120 --as user
lark-cli sheets +sheet-copy --url '<sheet-url>' --sheet-name '<source>' --title '<copy>' --as user
```

Use `+batch-update` only for cross-type operations with ordering dependencies. It is high risk and
fail-fast without rollback: preview once, show the exact operations, obtain confirmation, then resend
the same payload with `--yes`. Do not use it merely to combine writes already supported by
`--writes`, `--ranges`, `+table-put`, or `+styles-put`.

## Sheets verification budget

Sheets are the main exception to the global no-ritual-readback rule because a successful request may
not prove that formulas/types/layout are correct. Verify only the affected range or object, not the
whole workbook. Formula writes must run the known verifier directly; do not inspect its help first:

```bash
lark-cli sheets +formula-verify --url '<sheet-url>' --sheet-name '<sheet>' \
  --range 'A1:B50' --as user
```

Do not claim completion while it reports errors, `has_more=true`, or partial status. Ordinary value
writes usually cost one focused `+csv-get`; rich writes use one focused `+cells-get`. Never read after
every row/cell in a batch.

## Base resolution and read fast paths

Skip resolution when `base_token`, `table_id`, and any needed record/field IDs are already known.
Otherwise use exactly one resolver:

```bash
lark-cli base +url-resolve --url '<base-or-app-url>' --as user
lark-cli base +title-resolve --title '<keyword>' --as user
```

For a normal table, the stable discovery chain is `+table-list -> +field-list -> +record-list` or
`+record-search`. Stop as soon as the request is answerable: a known table ID skips `+table-list`; a
plain row listing that does not need type-aware mutation may skip `+field-list`. Inspect existing
metadata before writes whose CellValue shape depends on field types, select options, links, formulas,
or read-only fields.

Use `+data-query` directly for aggregation/grouping when the Base token and table are known:

```bash
lark-cli base +data-query --base-token '<base-token>' --dsl \
  '{"datasource":{"type":"table","table":{"tableId":"<table-id>"}},"dimensions":[{"field_name":"城市","alias":"city"}],"measures":[{"field_name":"金额","aggregation":"sum","alias":"total"}],"shaper":{"format":"flat"}}' \
  --as user
```

## Base write fast paths

Prefer one bounded batch request. Each record is an independent field map; do not loop over rows.

```bash
lark-cli base +record-batch-create --base-token '<base-token>' --table-id '<table-id>' \
  --json '{"create_records":[{"标题":"任务 A","状态":"Open"},{"标题":"任务 B","状态":"Done"}]}' \
  --as user
```

Use `+record-batch-update` for multiple known records. Before either command, read `+field-list` only
when field names/types/options are not already established. Formula, lookup, system, and automatic
number fields are read-only; remove them if returned as ignored/read-only rather than retrying the
whole payload unchanged. Split batches at the documented limit and retry only the failed batch,
never successful records.

Most Base table writes are asynchronous. Prefer the write response and returned record IDs; do not
read each record immediately. When verification is required, finish the related writes, allow the
service to settle, then perform one focused `+record-list`/`+record-search` acceptance read. Preview
and reconfirm record deletion, bulk replacement, role/member changes, advanced permissions,
workflow enable/disable, or AppMode publication-visible changes.

## Drift fallback

For a documented shortcut, run exact help only after an unknown option/command or payload-shape
error. For complex shortcut JSON, prefer its targeted `--print-schema`/flag schema when exposed;
use registered method schema only after selecting the exact method. Do not begin a common Sheet or
Base task with broad service help.

**Official coverage:** `lark-base`, `lark-sheets`.
