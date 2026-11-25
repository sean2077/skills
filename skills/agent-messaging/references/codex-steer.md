# Steer an active Codex turn

Invoke the bundled [steer sender](#send) directly for an ordinary message to a running Codex turn. Use [queue](codex-queue.md) only when the caller explicitly requests later handling.

## Target

Require Node.js 22.4+ and export the intended receiver's `TARGET_THREAD_ID`. Also set one of:

- `TARGET_CODEX_HOME`: the receiver's native Codex home; the sender uses its `app-server-control/app-server-control.sock`.
- `TARGET_CODEX_ENDPOINT`: its existing `ws://`, `wss://` or `unix://ABSOLUTE_PATH` endpoint. This takes precedence over `TARGET_CODEX_HOME`.

Use the original live server. The sender never guesses from its own inherited `CODEX_HOME`, starts an app-server or resumes a thread. It refuses `TARGET_THREAD_ID` equal to the sending process's own `CODEX_THREAD_ID`. Container/host and WSL/native Windows paths are not interchangeable.

The local socket route requires `codex app-server proxy --sock PATH`, verified in Codex 0.163.0. The sender spawns `codex` from PATH directly, bypassing shell aliases. On Windows it resolves a native `codex.exe` or the JS launcher from an npm install. Optionally set `CODEX_BIN` to a native executable or `.js`/`.mjs`/`.cjs` launcher. The proxy relays WebSocket bytes through a temporary local bridge and preserves Codex's native socket transport.

Direct WebSocket connections cannot supply custom authentication headers. Use an authorized alternate client if the endpoint requires them; keep tokens out of endpoint URLs. See [raw App Server requests](codex.md) when needed.

## Desktop message stays queued

1. **Handle the existing message.** In the receiving Desktop chat, find it in the queue above the composer and use **Steer** if offered. This can apply the existing item to the current turn. During compaction, Desktop may have to wait. [Desktop queue controls](https://learn.chatgpt.com/docs/prompting#steering-and-queuing) · [Compaction behavior](https://learn.chatgpt.com/docs/changelog?date=2026-10-15)
2. **Check the route for the next message.** If the sender used `codex queue`, Desktop's **Settings → General → Follow-up behavior** changes the composer's default. The external command explicitly enqueues its input. Run [the read-only check](#check-the-live-route) from the sending environment, or on the receiver over [SSH](ssh.md) if its socket is local to that machine. With an `active` result, use [steer](#send) by default. An `idle` result allows a separate [start](codex.md#start) when the caller intends a new turn. Check the existing queue before resending the same text. [CLI queue command](https://learn.chatgpt.com/docs/developer-commands#codex-queue)
3. **If the live route is unavailable.** Report the blocker from [the check](#check-the-live-route). Confirm the receiver environment, exact thread ID, and Desktop transport. If the turn belongs to a private stdio server, use Desktop's queue controls for that turn. If the caller chooses to queue, report deferred delivery and point to the manual **Steer** action when available. For recurring automatic delivery, use a receiver whose shared App Server the sender can reach. [Connection details](codex.md#connect-to-the-existing-server)

### Connect Desktop and the sender to one server

On Linux Desktop 26.1120.50957, an isolated Desktop initialized against an external App Server via `CODEX_APP_SERVER_WS_URL`. For an operator who chooses this setup, let active work finish and fully quit Desktop. Start a compatible App Server using the receiver's normal Codex home and an unused loopback port. Leave it running, then launch Desktop from a second terminal with the same URL:

~~~bash
# First terminal on the Desktop host
command codex app-server --listen ws://127.0.0.1:4500

# Second terminal on the Desktop host
CODEX_APP_SERVER_WS_URL=ws://127.0.0.1:4500 chatgpt
~~~

Open the intended chat in that Desktop instance. Set `TARGET_CODEX_ENDPOINT=ws://127.0.0.1:4500` and `TARGET_THREAD_ID` to the intended receiver, then run [the read-only check](#check-the-live-route). For repeated use, save the URL in the Desktop launch command and the sender setup. Start the App Server before Desktop and recheck the target after reconnecting. Keep the listener on loopback and run cross-machine sends over SSH on the Desktop host. The URL override is version-specific. The Linux Desktop test covered initialization and same-server steering in an isolated profile. Reopening an existing signed-in chat still requires the target check. The local-daemon environment switch alone left this Desktop build on stdio in the isolated test. [Build evidence and limits](sources.md#desktop) · [App Server command](https://learn.chatgpt.com/docs/developer-commands#codex-app-server)

## Check the live route

With the receiver's target variables set, use the skill's installed directory as `SKILL_DIR`:

```bash
node "$SKILL_DIR/scripts/steer-codex.mjs" --check
```

`--check` ignores message input and reads the loaded thread's live state without sending. `active` means one active turn was found, `idle` means the loaded thread had no active turn, and `not_sent` reports a failed check. Both successful results exit 0. A freshly opened thread can report idle through thread metadata before it has saved a first turn. The sender rechecks the live turn when it sends.

When a failed check includes `reason`, use it to choose the next check.

| JSON `reason` | What to check |
|---|---|
| `control_socket_refused` | The selected local socket refused the connection. Even an existing socket file can lack a listening App Server. Verify the endpoint for the receiver's live launch. |
| `control_socket_missing` | The selected local socket path could not be resolved. Verify the receiver's native Codex home and socket path. |
| `control_proxy_failed` | The proxy exited before the handshake. Check the Codex launcher and intended endpoint. Socket availability remains unknown. |
| `thread_not_loaded` | This App Server is reachable and does not have the target thread loaded. Verify the exact thread ID and the server that holds it. |

Use the Desktop launch or its server logs to establish whether Desktop owns a private stdio server. Both a missing or refused endpoint and a thread missing from a reachable server leave that ownership open.

## Send

Pass an existing UTF-8 file directly:

```bash
node "$SKILL_DIR/scripts/steer-codex.mjs" /path/to/message.txt
```

For stdin, use `-`:

```bash
printf '%s' 'Message text' | node "$SKILL_DIR/scripts/steer-codex.mjs" -
```

With no argument, use exported `MESSAGE`. A file or stdin takes precedence; text, including BOM and trailing newlines, is preserved and never echoed. Empty text is sent as given. Invalid UTF-8 in a file or stdin fails before connecting; use one of those when exact bytes matter, because the environment may already have replaced invalid bytes.

The sender confirms the thread is loaded, reads recent turn metadata with item bodies unloaded, and sends one `turn/steer` with `expectedTurnId`. An absent, changed, or unsteerable turn fails without a queue/start fallback. Each request waits at most 5 seconds within a 15-second total budget, so a slow server can produce `not_sent` or `unconfirmed`.

## Result

| JSON `status` | Exit | Meaning |
|---|---|---|
| `accepted` | 0 | Matching server acknowledgement received; not proof the model read or finished handling the message. |
| `not_sent` | 1 | Failed before attempting steer, such as an unloaded thread or no active turn. |
| `rejected` | 1 | The server explicitly rejected steer. |
| `unconfirmed` | 2 | Steer was attempted but its acknowledgement is missing or invalid; delivery may have occurred. |

Success goes to stdout; failures go to stderr. There is no automatic retry. For `unconfirmed`, inspect the target before deciding whether to send again. [Pinned protocol sources](sources.md#codex) are only needed for verification.
