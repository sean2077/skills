# Claude Code → native Codex

Use the target's `thread.id`, Codex home, and native endpoint. These examples address an existing CLI/Desktop conversation. The implementation details below were reviewed against Codex `rust-v0.163.0` on 2026-10-22; check the installed command/schema when they differ.

## Queue

Send through the recipient's native Codex environment:

```bash
codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE"
```

For an endpoint already used by the recipient:

```bash
codex queue --remote "$TARGET_ENDPOINT" \
  --thread "$TARGET_THREAD_ID" --message "$MESSAGE"
```

Use `codex --version` and `codex queue --help` to check availability. The thread argument accepts a UUID or exact name; prefer the UUID when names may be ambiguous. Use the target's `CODEX_HOME` / endpoint when installations differ. For an authenticated remote endpoint, `--remote-auth-token-env` names the environment variable containing its token.

The CLI submits through `thread/queue/add`. A loaded idle target can begin the queued turn; a busy target keeps it until its current turn finishes. An unloaded thread can retain input until it is resumed in its native client. An interrupted target is not automatically restarted; archived and ephemeral threads reject queue delivery. Success means queued, not read or completed. Repeating the CLI command creates another queued message.

## Connect to the existing App Server

For steer, start, and interrupt, connect to the server that already holds the target's live thread. Use its existing `ws://`, `wss://`, or `unix://` endpoint. In the verified version the shared control socket is located at:

```text
<target CODEX_HOME>/app-server-control/app-server-control.sock
```

This is a version-specific native path, not a guarantee that every Desktop/CLI launch exposes it. The control socket uses **WebSocket over the local socket**, including an HTTP Upgrade handshake; it does not accept bare JSON lines. Use a client supporting the actual transport. An existing stdio connection belongs to its owning client.

On native Windows, this Codex control socket uses Windows AF_UNIX, not CC's named-pipe transport. Use a client with that support; a WSL/POSIX path or ordinary Windows named-pipe client is not interchangeable. The native queue CLI handles its own transport selection.

Do not start another `codex app-server` and `thread/resume` the ID as a substitute for reaching the original live session. Shared history does not establish ownership of its active turn.

Send each JSON object below as a separate WebSocket text frame. Wait for the successful `initialize` response before sending `initialized` and further requests:

```json
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"claude-codex-messaging","version":"0.1.0"}}}
```

```json
{"method":"initialized","params":{}}
```

Confirm the target ID appears in this server's loaded threads, following `nextCursor` as `cursor` when needed:

```json
{"id":2,"method":"thread/loaded/list","params":{}}
```

Read current metadata and recent turns:

```json
{"id":3,"method":"thread/read","params":{"threadId":"TARGET_THREAD_ID"}}
```

```json
{"id":4,"method":"thread/turns/list","params":{"threadId":"TARGET_THREAD_ID","limit":10,"sortDirection":"desc","itemsView":"notLoaded"}}
```

Take `ACTIVE_TURN_ID` from the turn whose `status` is `inProgress`; the native turn-list implementation includes live state. An already subscribed connection can also use `turn/started` events. A plain `thread/read` neither resumes the thread nor subscribes to events. If the target is absent from the loaded list, this connection has not established control of the original session.

## Steer

```json
{"id":5,"method":"turn/steer","params":{"threadId":"TARGET_THREAD_ID","expectedTurnId":"ACTIVE_TURN_ID","input":[{"type":"text","text":"MESSAGE"}]}}
```

This adds input to the current turn without creating another. The expected ID must match; no active turn, a stale ID, or an unsteerable review/compaction turn causes rejection. Re-read changed state before choosing how to proceed. Steer is distinct from cancelling the turn.

## Start

```json
{"id":6,"method":"turn/start","params":{"threadId":"TARGET_THREAD_ID","input":[{"type":"text","text":"MESSAGE"}]}}
```

In the verified implementation this calls `start_or_steer_turn`: idle starts a new turn; an active normal turn can receive the input in that turn. It is neither queue nor a strict idle-only operation. A preceding state read does not eliminate that race.

## Interrupt

```json
{"id":7,"method":"turn/interrupt","params":{"threadId":"TARGET_THREAD_ID","turnId":"ACTIVE_TURN_ID"}}
```

This requests cancellation of the specified active turn. Its acknowledgement is not replacement input; the completed turn has status `interrupted`. Any subsequent message is a separate operation with its own timing.

## Sources

- [Official command reference](https://learn.chatgpt.com/docs/developer-commands) and [App Server protocol](https://learn.chatgpt.com/docs/app-server).
- Version-pinned [queue command](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/session_queue_commands.rs) and [queue dispatch](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/ext/queue/src/service.rs).
- [Control socket path](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-transport/src/transport/mod.rs) and [WebSocket acceptance](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-transport/src/transport/unix_socket.rs).
- [Windows AF_UNIX implementation](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/uds/src/lib.rs) and [native peer checks](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/uds/src/windows_peer.rs).
- [Turn input semantics](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/request_processors/turn_processor.rs), [live turn reads](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/request_processors/thread_processor.rs), and [thread request schemas](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-protocol/src/protocol/v2/thread.rs).
