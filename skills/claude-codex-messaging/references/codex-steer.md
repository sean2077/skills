# Claude Code → active Codex turn

Use steer when the message should affect ongoing work. It neither cancels that work nor queues a later turn. If later handling is intended, use [queue](codex-queue.md).

## Target

Require Node.js 22.4+ and export the intended receiver's `TARGET_THREAD_ID`. Also set one of:

- `TARGET_CODEX_HOME`: the receiver's native Codex home; the sender uses its `app-server-control/app-server-control.sock`.
- `TARGET_CODEX_ENDPOINT`: its existing `ws://`, `wss://` or `unix://ABSOLUTE_PATH` endpoint. This takes precedence over `TARGET_CODEX_HOME`.

Use the original live server. The sender never guesses from its own inherited `CODEX_HOME`, starts an app-server or resumes a thread. Container/host and WSL/native Windows paths are not interchangeable.

The local socket route requires `codex app-server proxy --sock PATH`, verified in Codex 0.163.0. The sender uses `codex` on PATH; on Windows it runs `codex.exe` or an npm install's JS launcher, never the `.cmd` shim through a shell. Optionally set `CODEX_BIN` to a native executable or `.js`/`.mjs`/`.cjs` launcher. The proxy relays WebSocket bytes through a temporary local bridge and preserves Codex's native socket transport.

Direct WebSocket connections cannot supply custom authentication headers. Use an authorized alternate client if the endpoint requires them; keep tokens out of endpoint URLs. See [raw App Server requests](codex.md) when needed.

## Send

`SKILL_DIR` is this skill's installed directory. Pass an existing UTF-8 file directly:

```bash
node "$SKILL_DIR/scripts/steer-codex.mjs" /path/to/message.txt
```

For stdin, use `-`:

```bash
printf '%s' 'Message text' | node "$SKILL_DIR/scripts/steer-codex.mjs" -
```

With no argument, use exported `MESSAGE`. A file or stdin takes precedence; text, including BOM and trailing newlines, is preserved and never echoed. Empty text is sent as given. Invalid UTF-8 in a file or stdin fails before connecting; use one of those when exact bytes matter, because the environment may already have replaced invalid bytes.

The sender confirms the thread is loaded, following bounded pages; reads recent turn metadata with item bodies unloaded; then sends one `turn/steer` with `expectedTurnId`. It does not download full conversation history. No active turn or changed/unsteerable turn fails without a queue/start fallback. Each request waits at most 5 seconds within a 15-second total budget, so a slow server can produce `not_sent` or `unconfirmed`.

## Result

| JSON `status` | Exit | Meaning |
|---|---|---|
| `accepted` | 0 | Matching server acknowledgement received; not proof the model read or finished handling the message. |
| `not_sent` | 1 | Failed before attempting steer, such as an unloaded thread or no active turn. |
| `rejected` | 1 | The server explicitly rejected steer. |
| `unconfirmed` | 2 | Steer was attempted but its acknowledgement is missing or invalid; delivery may have occurred. |

Success goes to stdout; failures go to stderr. There is no automatic retry. For `unconfirmed`, inspect the target before deciding whether to send again. [Pinned protocol sources](sources.md#codex) are only needed for verification.
