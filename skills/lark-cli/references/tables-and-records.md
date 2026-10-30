# Tables and records

## Select the object

Use `sheets` for spreadsheet grids and `base` for typed records. A BaseApp/AppMode is a presentation layer over Base data, not a Miaoda/Spark app. Route `/sheets/` to Sheets and `/base/` or Base-style `/app/` links to Base regardless of hostname. Preserve URLs/tokens exactly.

Use known coordinates directly. Resolve missing Base coordinates through `+url-resolve` or `+title-resolve`, and inspect workbook, table, or field metadata when needed to interpret the operation. Batch compatible row, cell, record, and style changes.

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

Borders belong inside each `cell_styles` item. Use the nested `border` shorthand for one uniform border, or the nested `border_styles` object only when sides need different styles; do not put `border_styles` alongside the top-level `cell_styles` array. Preserve the existing non-border fields when extending a styled range.

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

## Sheets verification

A successful request may not establish correct formulas, types, or layout. Verify the affected range or object. For formula writes, run:

```bash
lark-cli sheets +formula-verify --url '<sheet-url>' --sheet-name '<sheet>' \
  --range 'A1:B50' --as user
```

Do not claim completion while it reports errors, `has_more=true`, or partial status. Ordinary value
writes usually cost one focused `+csv-get`; rich writes use one focused `+cells-get`. Never read after
every row/cell in a batch.

## Base resolution and read fast paths

Skip resolution when `base_token`, `table_id`, and any needed record/field IDs are already known.
Resolve the missing coordinates with:

```bash
lark-cli base +url-resolve --url '<base-or-app-url>' --as user
lark-cli base +title-resolve --title '<keyword>' --as user
```

For a normal table, the stable discovery chain is `+table-list -> +field-list -> +record-list` or
`+record-search`. Stop as soon as the request is answerable: a known table ID skips `+table-list`; a
plain row listing that does not need type-aware mutation may skip `+field-list`. Inspect existing
metadata before writes whose CellValue shape depends on field types, select options, links, formulas,
or read-only fields.

For known record IDs, use `+record-get` with repeated `--record-id` instead of scanning the table.
In v1.0.98, `+record-list`, `+record-search`, and `+record-get` default to NDJSON files plus a
manifest. Stdout contains that manifest directly, without an `ok`/`data` envelope; check exit
status and the command's result shape, then process `record_file` for the actual rows. The
manifest's examples and statistics describe this export, not the complete table.

Project only needed fields and choose a new cwd-relative output path:

```bash
lark-cli base +record-list --base-token '<base-token>' --table-id '<table-id>' \
  --field-id '<field-name-or-id>' --format ndjson --output ./records.ndjson --as user
```

For small inline reads or environments without file I/O, use `--format json`; list/search can
also take a bounded `--limit` (inline JSON accepts at most 200 records; NDJSON up to 2000).
This format returns the raw matrix through the usual JSON envelope. v1.0.98 rejects
`--format markdown`. Preserve working older-version recipes; consult the installed command's
exact help when its output or supported flags differ.

In v1.0.98, each list/search call fetches one page, up to 2000 records. A requested preview may
stop at its bound. When the task requires all matching rows, continue only while `has_more=true`,
passing the returned `next_offset` as `--offset`, keeping the same query/projection, and using a
different output file per page.
Treat the result as complete only when the last page reports `has_more=false` and the query scope
matches the question. For a consistent multi-page snapshot, check `rev` and `query_context`;
restart or disclose the limitation if they change or consistency cannot be established.
`+record-get` addresses selected IDs and does not use this pagination loop; inspect
`record_not_found` for missing records.

These output rules were source-reviewed on 2026-10-30 against the
[v1.0.98 change](https://github.com/larksuite/cli/pull/2782),
[record export implementation](https://github.com/larksuite/cli/blob/v1.0.98/shortcuts/base/record_export.go),
and [analysis SOP](https://github.com/larksuite/cli/blob/v1.0.98/skills/lark-base/references/lark-base-record-query-and-analysis-sop.md).
Live CLI/service behavior remains unverified by that review.

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
service to settle, then perform one focused acceptance read: `+record-get` for known IDs, or
`+record-list`/`+record-search` for the required scope. For NDJSON output, verify the affected rows
in the returned file. Preview and reconfirm record deletion, bulk replacement, role/member changes,
advanced permissions, workflow enable/disable, or AppMode publication-visible changes.

## Command discovery

Consult the installed help/schema for unfamiliar or changed operations. Confirm parameter types before consequential writes; use the [setup and safety guide](setup-auth-and-safety.md) for identity, confirmation, and uncertain outcomes.

**Official coverage:** `lark-base`, `lark-sheets`.
