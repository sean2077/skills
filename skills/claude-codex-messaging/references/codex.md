# Claude Code → Codex App Server

Read for start, interrupt or an alternate App Server client. For ordinary steer delivery, use the [bundled sender](codex-steer.md). Behavior below was checked against Codex 0.163.0; consult the installed schema if it differs. [Pinned sources](sources.md#codex).

## Connect to the existing server

Use the server already holding the target's live thread: its `ws://`, `wss://` or `unix://` endpoint. In the checked version, the shared socket is `<target CODEX_HOME>/app-server-control/app-server-control.sock`; availability depends on the native launch.

The control socket uses **WebSocket with HTTP Upgrade**, not raw JSON lines. Native Windows uses AF_UNIX, not CC named pipes; WSL/POSIX paths and pipe clients are not substitutes. Use a client supporting the actual transport. An existing stdio connection belongs to its owning client. A new app-server plus `thread/resume` does not control the original live turn.

On a new connection, send each object as a separate WebSocket text frame. Wait for successful `initialize` before `initialized` and further requests:

```json
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"claude-codex-messaging","version":"0.1.0"}}}
{"method":"initialized","params":{}}
```

Confirm the target is loaded on this server. If not already established by live connection state, request bounded pages; follow `nextCursor` as `cursor` and stop when found:

```json
{"id":2,"method":"thread/loaded/list","params":{"limit":50}}
```

If the target is absent, control of the original session is not established. Read metadata only when needed:

```json
{"id":3,"method":"thread/read","params":{"threadId":"TARGET_THREAD_ID","includeTurns":false}}
```

`thread/read` neither resumes nor subscribes to the thread.

## Active turn ID: steer / interrupt only

Use current subscribed `turn/started` state, or fetch recent turn metadata:

```json
{"id":4,"method":"thread/turns/list","params":{"threadId":"TARGET_THREAD_ID","limit":10,"sortDirection":"desc","itemsView":"notLoaded"}}
```

Take `ACTIVE_TURN_ID` from `status:"inProgress"`; the list includes live state. Keep item bodies unloaded. Refresh stale state before deciding how to proceed; a start request does not need this lookup.

## Steer

```json
{"id":5,"method":"turn/steer","params":{"threadId":"TARGET_THREAD_ID","expectedTurnId":"ACTIVE_TURN_ID","input":[{"type":"text","text":"MESSAGE"}]}}
```

Add input to the current turn, without creating or cancelling one. A mismatched ID, no active turn, or an unsteerable review/compaction turn is rejected.

## Start

```json
{"id":6,"method":"turn/start","params":{"threadId":"TARGET_THREAD_ID","input":[{"type":"text","text":"MESSAGE"}]}}
```

The checked `start_or_steer_turn` implementation starts when idle and can steer an active normal turn. It is not queue or a strict idle-only operation; a prior state read cannot eliminate that race.

## Interrupt

```json
{"id":7,"method":"turn/interrupt","params":{"threadId":"TARGET_THREAD_ID","turnId":"ACTIVE_TURN_ID"}}
```

Cancel the specified active turn. Acknowledgement carries no replacement input; the completed turn has status `interrupted`. A later message is a separate operation.
