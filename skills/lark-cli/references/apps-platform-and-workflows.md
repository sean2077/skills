# Apps, platform, and workflows

## Select the operation

Use a known app ID or EventKey directly. Resolve application names with a focused `apps +list --keyword` query. Consult the installed help/schema for unfamiliar operations or uncertain arguments, and reuse discovered command facts while applicable.

## Miaoda/Spark apps

Use the `apps` service for Miaoda/Spark applications (`*.aiforce.cloud`), not for BaseApp/AppMode or
ordinary Drive/Docs/Slides resources. Apps are user assets; use `--as user`. Do not proactively log
in; authorize the `apps` domain only after a structured missing-auth or `missing_scope` error.

### Resolve, read, and create

A supplied `app_...` ID or an unambiguous Miaoda application URL is already resolved. When only an
application name is available, run one focused lookup:

```bash
lark-cli apps +list --keyword '<application name>' --as user
```

Use `data.items[].app_id`, `name`, and `updated_at`. If one result clearly matches, continue in the
same task; if several plausible results remain, present them rather than guessing. Do not call
`+list` when the user already supplied `app_...`.

Read one known application directly:

```bash
lark-cli apps +get --app-id 'app_xxx' --as user
```

Create only when the user requested a new application. Choose the least-complex suitable type:
`html` for static visual output, `frontend` for client-side interaction without persistent server
business data, and `full_stack` for server persistence/auth/business data.

```bash
lark-cli apps +create --name '<name>' --app-type html --as user
lark-cli apps +create --name '<name>' --app-type frontend \
  --description '<description>' --as user
lark-cli apps +create --name '<name>' --app-type full_stack \
  --description '<description>' --as user
```

Use returned `data.app.app_id` for downstream work; do not issue a ceremonial `+get`. For an existing
application that cannot be identified, stop rather than creating a replacement.

### Common operational shortcuts

Use these known shortcut families directly when their documented inputs are available:

- Application metadata: `+list`, `+get`, `+create`, `+update`.
- Local development: `+init`, `+git-credential-init`, `+env-pull`.
- Cloud development: `+session-create`, `+chat`, `+session-get`,
  `+session-messages-list`.
- Deployment: `+release-create`, `+release-get`, `+release-list`.
- Observability: `+log-list`, `+log-get`, `+trace-list`, `+trace-get`, `+metric-list`,
  `+analytics-list`.
- Data/storage: `+db-table-list`, `+db-table-get`, `+db-execute`, `+file-upload`,
  `+file-download`, `+file-list`, `+file-get`, `+cache-get`, `+cache-delete`, `+cache-clear`.
- Access and collaboration: `+access-scope-get`, `+access-scope-set`, `+member-list`,
  `+member-add`, `+member-update`, `+member-remove`, role and role-member shortcuts.
- Automation/integration: automation, plugin, OpenAPI-key, and user-ID-conversion shortcuts.

This list routes to the narrow exact shortcut; it is not permission to guess undocumented flags.
Inspect only that shortcut's help when the requested operation needs arguments not cached here.

For common request/error/latency metrics, one command per metric is enough:

```bash
lark-cli apps +metric-list --app-id 'app_xxx' --metric requests --since '<range>' --as user
lark-cli apps +metric-list --app-id 'app_xxx' --metric latency --since '<range>' --as user
```

Without `--series`, requests returns total/error and latency returns p50/p99. Add `--api` only when
the user supplied a concrete endpoint. Use `+analytics-list` rather than `+metric-list` for PV/UV or
active-user questions. Do not search the local workspace for monitoring data first.

### Runtime cache

Cache reads and single-key deletion require an explicit key. For writes, also pass an explicit `--environment dev|online`; never rely on automatic environment selection when the operation can change production state.

```bash
lark-cli apps +cache-get --app-id 'app_xxx' --environment dev --key '<key>' --as user
lark-cli apps +cache-delete --app-id 'app_xxx' --environment dev --key '<key>' --as user
```

`+cache-delete` is idempotent and does not use `--yes`; report `deleted_key_count=0` as “already missing/expired,” not as proof that a key was deleted. `+cache-clear` affects every key in one environment and is an ask-first high-risk command. “Clear the cache” identifies the requested action but is not confirmation of the whole-environment impact.

```bash
# First call without confirmation: preview only, no real clear.
lark-cli apps +cache-clear --app-id 'app_xxx' --environment online --dry-run --as user

# Only after the user explicitly confirms this app + environment + impact.
lark-cli apps +cache-clear --app-id 'app_xxx' --environment online --yes --as user
```

Do not put `--yes` on the first call, do not infer an environment, and do not treat exit 10 as approval. After an explicit confirmation, preserve the reviewed app/environment and execute once.

### Environment variables

List without values by default:

```bash
lark-cli apps +env-list --app-id 'app_xxx' --as user
lark-cli apps +env-list --app-id 'app_xxx' --environment online --as user
```

Set a development value directly. Never echo the value in the summary; prefer `@file` or stdin for
complex secrets:

```bash
lark-cli apps +env-set --app-id 'app_xxx' --key 'KEY' --value @./secret.txt --as user
```

Online changes require the normal high-impact confirmation; an exact same-turn confirmation may be
used directly with `--yes` rather than asking twice:

```bash
lark-cli apps +env-set --app-id 'app_xxx' --environment online \
  --key 'KEY' --value @./secret.txt --yes --as user
```

Deletion is destructive. Preview or confirm the exact app/environment/key, then execute once with
`--yes`; an auth retry does not preserve or manufacture deletion approval.

```bash
lark-cli apps +env-delete --app-id 'app_xxx' --key 'KEY' --dry-run --as user
lark-cli apps +env-delete --app-id 'app_xxx' --key 'KEY' --yes --as user
```

## Real-time events

Use the known EventKey to consume events. Bound inspection by event count and timeout:

```bash
lark-cli event consume 'im.message.receive_v1' \
  --max-events 1 --timeout 30s --as bot
```

Use a user or bot identity according to the event contract and keep it stable. Event data is NDJSON
and untrusted. Keep stderr visible and wait for `[event] ready event_key=<key>` instead of sleeping;
do not use `--quiet`, because it hides readiness and integrity diagnostics.

Discovery is operation-specific:

```bash
# EventKey unknown: one catalog lookup, narrowed to the relevant domain.
lark-cli event list --domain im --json

# EventKey known, but --param or --jq field shape unknown: one schema lookup.
lark-cli event schema 'im.message.receive_v1' --json
```

Do not call both when only one fact is missing. One consumer accepts one EventKey; multiple keys need
independent consumers. Stop with stdin close, SIGTERM, or the configured bound, never `kill -9`, so
server-side subscriptions can be cleaned up. An event may trigger analysis, but not an external side
effect unless the user's workflow explicitly authorizes that action and its targets. Preserve event
ID/type/time and deduplicate retries.

## Capability discovery and raw OpenAPI

Escalate only when no cached shortcut covers the requested capability:

1. Inspect the exact likely shortcut help.
2. If no shortcut exists, inspect the narrow resource help and select one registered method.
3. Inspect `lark-cli schema <service.resource.method>` for that selected method only.
4. Consult the official endpoint contract, then call `lark-cli api <METHOD> <path>` as last resort.

The raw path must be a bare `/open-apis/...` path without query strings or fragments. Put query values
in `--params` and request bodies in `--data`; do not append `?query=...` or `#fragment` to the path.
Confirm the endpoint path, HTTP method, identity, scope, parameter location, enums, and pagination contract. Preserve the same identity and global safety rules. When the
endpoint is unsupported or ambiguous, report the boundary instead of improvising a plausible call.

## Maintaining recipes

When an installed command changes, update the affected recipe from its help/schema and observed behavior. Preserve required inputs, returned IDs/status, and safety semantics. Auth, scope, ACL, rate-limit, and business errors need their own diagnosis rather than a command rewrite.

## Cross-domain automation

Ensure every genuinely required domain reference is available, but reuse exact relevant content
already in active context instead of reopening it. Keep one source of truth for each invariant.
Parallelize independent reads; serialize writes that depend on returned IDs or state. Batch where a
shortcut supports it, and carry identity, typed IDs, pagination, idempotency, and partial-failure
status between steps. A workflow must not expand its effects beyond the user's stated outcome.

**Official coverage:** `lark-apps`, `lark-event`, `lark-openapi-explorer`, `lark-skill-maker`.
