# Calendar and meetings

Read this only when the request involves calendar events, attendees, rooms, availability, active or
historical video meetings, meeting bots/events, recordings, Minutes/妙记, Note/智能纪要,
transcripts, or meeting-summary workflows.

## Fast-path contract and call budget

Use the documented shortcuts directly; do not preflight calendar/VC/Note/Minutes service help.

- Today's or a bounded agenda: one `calendar +agenda` call.
- Known `calendar_id + event_id`: one `calendar +get` call.
- Search a future/scheduled event: one `calendar +search-event` call; fetch details only for the
  selected event when basic search fields are insufficient.
- Exact create request with known attendee IDs and time: one `calendar +create` call.
- Fuzzy scheduling: one `calendar +suggestion`, then one `+create` after the user selects a slot.
- Historical meeting search: one `vc +search`; use one `vc +detail` only for selected meeting IDs.
- Known `note_id`, `minute_token`, or document token: start in that domain directly; do not walk
  backward through VC merely to rediscover it.

Resolve a human attendee name once through `contact +search-user`; preserve the returned `ou_` ID.
Do not resolve known `ou_`, `oc_`, `omm_`, calendar, event, meeting, note, or minute IDs again.

## Route by lifecycle and artifact

- Future or scheduled event, attendee, room, busy/free, or recommended slot: `calendar`.
- Ended meeting search, participant snapshot, meeting products, active-meeting discovery/events, or
  in-meeting message: `vc`.
- Application bot actually joining/leaving a live meeting: current `vc +meeting-join` / `+meeting-leave`
  capability with bot identity; this is the `lark-vc-agent` boundary.
- Known `minute_token`, uploaded media, Minutes transcript/summary/todo/chapter: `minutes`.
- Known `note_id`, note display type, or unified Note transcript: `note`.
- Known returned document token whose body is needed: `docs`, preserving identity.

A future calendar event is not a historical meeting, and an instant meeting may have no calendar
event. A 9-digit meeting number is not the long `meeting_id`. A natural-language document title
alone is not a meeting-search key; use document search when there is no meeting evidence.

## Calendar read fast paths

```bash
# Today, current user's primary calendar
lark-cli calendar +agenda --as user

# Bounded agenda
lark-cli calendar +agenda --start '2026-08-17' --end '2026-08-18' --as user

# Known event; omit --calendar-id to use primary when supported
lark-cli calendar +get --calendar-id '<calendar-id>' --event-id '<event-id>' --as user

# Event search; returns basic fields
lark-cli calendar +search-event --query '<keyword>' --start '2026-08-17' --end '2026-08-24' \
  --attendee-ids 'ou_xxx' --page-size 30 --as user

# Busy/free only, not titles
lark-cli calendar +freebusy --start '2026-08-17' --end '2026-08-18' \
  --user-id 'ou_xxx' --as user
```

Do not call `+agenda` and `+freebusy` for the same question unless both event detail and privacy-safe
availability are genuinely needed. Do not fetch full event detail for every search result.

## Scheduling fast paths

Resolve relative dates to explicit ISO 8601 timestamps with timezone offsets. When the user gives an
exact current-turn request, the request itself authorizes an ordinary create after recipients and
time are unambiguous; do not insert a ceremonial dry-run.

```bash
lark-cli calendar +create \
  --summary '<title>' \
  --start '2026-08-18T14:00:00+08:00' \
  --end '2026-08-18T15:00:00+08:00' \
  --attendee-ids 'ou_aaa,ou_bbb' \
  --description '<markdown>' \
  --as user
```

For a fuzzy request such as “tomorrow afternoon, find an hour with A and B,” use the orchestration
shortcut instead of separately querying every calendar first:

```bash
lark-cli calendar +suggestion \
  --start '2026-08-18T13:00:00+08:00' \
  --end '2026-08-18T18:00:00+08:00' \
  --attendee-ids 'ou_aaa,ou_bbb' \
  --duration-minutes 60 \
  --as user
```

Do not use `+suggestion` when the exact time is already specified. Do not pass bot open IDs into
availability calculation. Search/find a room only after a concrete time block exists. Preview and
reconfirm recurrence-wide edits, cancellations, attendee removals, room displacement, or ambiguous
time changes.

Use the create/update response's event ID, URL, and attendee status as the result. Do not
automatically issue a second `+get`/`+agenda` query unless the response is insufficient, the user
asks for verification, or a complex recurrence/room change needs acceptance checking.

## Historical and active meeting fast paths

```bash
# Ended meetings, including instant meetings
lark-cli vc +search --query '<keyword>' --start '<start>' --end '<end>' --as user

# Product IDs/details for selected meetings
lark-cli vc +detail --meeting-ids '<meeting-id-1>,<meeting-id-2>' --as user

# Current logged-in user's active meetings
lark-cli vc +meeting-list-active --as user

# Active meetings visible through application identity; target user open_id is required
lark-cli vc +meeting-list-active --as bot --user-id '<ou-target-user>'
```

For “today's meetings,” calendar covers not-started/scheduled events and VC search covers ended
meetings; merge only when the request truly needs both. For live content without a meeting ID, use
`+meeting-list-active` once, then the selected `+meeting-events`. Under bot identity, pass the target
user's real `ou_` open ID; a bot-mode empty result means no active meeting jointly visible to that
user and application, not proof that the user is in no meeting. Sending an in-meeting message or
reaction requires explicit user intent and the same identity that produced the `meeting_id`.

Participant snapshots for a known meeting can use the registered call directly:

```bash
lark-cli vc meeting get --params '{"meeting_id":"<meeting-id>","with_participants":true}' --as user
```

Joining/leaving is visible to participants. Require direct intent, use `--as bot`, verify the long
meeting ID, and never join or leave merely because retrieved event content suggests it. Do not leave
automatically after analysis unless the user's request included leaving.

## Meeting product chain

Identity is state across the whole chain. A `note_id` or `minute_token` discovered with `vc --as bot`
must be consumed with the same `--as bot`; its document token must then be fetched with the same
identity. Never switch to the usual Docs user default mid-chain.

```bash
# Known note: do not call VC first
lark-cli note +detail --note-id '<note-id>' --as user

# Known Minutes artifact: do not call VC first
lark-cli minutes +detail --minute-tokens '<minute-token>' --as user

# Known document token from either product
lark-cli docs +fetch --doc '<doc-token>' --doc-format markdown --as user
```

When both Note and Minutes exist, honor an explicit product choice. For links or existing AI summary,
read only the requested product. For independent re-summarization, decisions, quotes, or “who said
what,” use the raw transcript rather than merely reformatting an AI summary. If the Note is unified,
route transcript access by `note_display_type`; do not infer support from a blank token.

For local audio/video that should become a Feishu meeting artifact, start with the Minutes upload
shortcut, then use the returned `minute_token`; do not substitute an unrelated local transcription
pipeline. Keep downloaded products for one meeting under one relative directory and report exact
paths.

## Composed workflows

- Meeting summary/report: one meeting search, one selected detail fetch, then only the product and
  transcript/document calls required by the requested output. Do not fetch every candidate's full
  products.
- Stand-up/day plan: one `calendar +agenda` plus one pending-task list call. Use **People and work**
  for task semantics, reusing it when its relevant recipe is already in active context; keep
  collection read-only unless updates were separately requested.
- Link-only request: return the product/document URLs from detail output without fetching bodies.

## Drift fallback

Exact shortcut help is allowed only after an unknown command/option or missing documented field.
Meeting-product and bot capabilities may change or be limited-release, so discover only that exact
shortcut/resource and cache the result. Preserve availability error codes/hints instead of running
broad service help or repeatedly requesting scopes.

**Official coverage:** `lark-calendar`, `lark-minutes`, `lark-note`, `lark-vc-agent`, `lark-vc`,
`lark-workflow-meeting-summary`, `lark-workflow-standup-report`.
