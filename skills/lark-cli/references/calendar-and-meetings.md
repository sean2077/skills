# Calendar and meetings

Read this only when the request involves calendar events, attendees, rooms, availability, active or
historical video meetings, meeting bots, meeting messages/events, recordings, Minutes/妙记,
Note/智能纪要, transcripts, or meeting-summary workflows.

## Route by lifecycle and artifact

- Future or scheduled event, attendee, room, busy/free, or recommended slot: `calendar`.
- Ended meeting search, participant snapshot, meeting products, active-meeting discovery/events, or
  in-meeting message: `vc`.
- Application bot actually joining or leaving a live meeting: use the current `vc` join/leave
  shortcuts and bot identity; treat this as the `lark-vc-agent` capability boundary.
- Known `minute_token`, media upload/download, speaker/keyword editing, or Minutes permission:
  `minutes`.
- Known `note_id`, note display type, or raw Note transcript: `note`.
- Reading the document tokens returned by meeting products: `docs`, while preserving identity.

A future calendar event is not a historical meeting, and an instant meeting may have no calendar
event. A natural-language document title alone is not a meeting-search key; use document search when
there is no meeting evidence.

## Time and scheduling

- Resolve relative dates to explicit start/end timestamps and state the timezone. Preserve the
  user's timezone; do not silently reinterpret all-day events or daylight-saving transitions.
- Before creating or moving a meeting, inspect availability and room constraints when relevant.
  Preview title, start/end, timezone, attendees, recurrence, room, and conferencing effect.
- An exact current-turn scheduling request may authorize a normal create/update. Reconfirm attendee
  removals, room displacement, recurrence-wide edits, cancellations, and ambiguous time changes.
- Calendar meeting rooms/events and VC meeting records use different IDs. Do not treat a 9-digit
  meeting number as the long `meeting_id`; resolve it through the current meeting-list capability.

## Meeting product chain

Identity is state across the whole chain. For example, a `note_id` discovered with `vc --as bot`
must be consumed by `note --as bot`, and its document token by `docs --as bot`. Never switch to the
usual Docs user default mid-chain.

When both AI Note and Minutes products exist:

- Honor an explicit request for one product.
- If only one exists, use it.
- If both exist and the user does not choose, prefer the AI Note path for ordinary summary access,
  while exposing both links when useful.
- For independent re-summarization, decisions, quotes, or “who said what,” start from the raw
  transcript/record rather than merely reformatting an existing AI summary.
- For local audio/video that should become a Feishu meeting artifact, prefer the Minutes upload
  path; do not replace it with an unrelated local transcription pipeline.

Keep downloaded products for one meeting in one relative directory and report exact paths. Do not
invent a Minutes/Note/document link when the CLI does not return one.

## Active meeting and bot actions

- Active-event reads are read-only. Do not auto-download shared content, scan unrelated comments,
  send messages, or join the meeting because an event payload suggests it.
- Sending in-meeting text/reaction requires the source identity of the `meeting_id`; bot sends may
  require the bot to be in the meeting. Verify the documented emoji enum rather than inventing one.
- Joining/leaving is visible to participants. Require direct user intent, use `--as bot`, verify the
  long meeting ID, and never leave automatically just because the requested analysis finished.
- Some bot meeting capabilities may be limited-release. Preserve availability error codes/hints and
  report the boundary instead of repeatedly requesting scopes.

## Composed workflows

- Meeting summary/report: search meetings, inspect Note/Minutes availability, fetch only the needed
  product content, then synthesize with source IDs/links and explicit gaps.
- Stand-up/day plan: combine Calendar agenda with incomplete Tasks. Also load **People and work**;
  keep the collection read-only unless the user separately requests updates.

**Official coverage:** `lark-calendar`, `lark-minutes`, `lark-note`, `lark-vc-agent`, `lark-vc`,
`lark-workflow-meeting-summary`, `lark-workflow-standup-report`.
