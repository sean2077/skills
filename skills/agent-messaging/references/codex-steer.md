# Send to a live Codex chat

Use the bundled [sender with `--auto`](#send) for ordinary delivery. A loaded chat starts a new turn when idle or receives the input in its current turn when busy. Use [queue](codex-queue.md) for an explicit request to defer.

## Target

Require Node.js 22.4+ and export the intended receiver's `TARGET_THREAD_ID`. Also set one of:

- `TARGET_CODEX_HOME`: the receiver's native Codex home; the sender uses its `app-server-control/app-server-control.sock`.
- `TARGET_CODEX_ENDPOINT`: its existing `ws://`, `wss://` or `unix://ABSOLUTE_PATH` endpoint. This takes precedence over `TARGET_CODEX_HOME`.

Use the original live server. The sender never guesses from its own inherited `CODEX_HOME`, starts an app-server or resumes a thread. It refuses `TARGET_THREAD_ID` equal to the sending process's own `CODEX_THREAD_ID`. Container/host and WSL/native Windows paths are not interchangeable.

The local socket route requires `codex app-server proxy --sock PATH`, verified in Codex 0.163.0. The sender spawns `codex` from PATH directly, bypassing shell aliases. On Windows it resolves a native `codex.exe` or the JS launcher from an npm install. Optionally set `CODEX_BIN` to a native executable or `.js`/`.mjs`/`.cjs` launcher. The proxy relays WebSocket bytes through a temporary local bridge and preserves Codex's native socket transport.

Direct WebSocket connections cannot supply custom authentication headers. Use an authorized alternate client if the endpoint requires them; keep tokens out of endpoint URLs. See [raw App Server requests](codex.md) when needed.

## Desktop message stays queued

1. **Handle the existing message.** In the receiving Desktop chat, find it in the queue above the composer and use **Steer** if offered. This can apply the existing item to the current turn. During compaction, Desktop may have to wait. [Desktop queue controls](https://learn.chatgpt.com/docs/prompting#steering-and-queuing) · [Compaction behavior](https://learn.chatgpt.com/docs/changelog?date=2026-10-15)
2. **Check the route for the next message.** If the sender used `codex queue`, Desktop's **Settings → General → Follow-up behavior** changes the composer's default. The external command explicitly enqueues its input. Run [the read-only check](#check-the-live-route) from the sending environment, or on the receiver over [SSH](ssh.md) if its socket is local to that machine. Both `active` and `idle` allow [automatic delivery](#send). Check the existing queue before resending the same text. [CLI queue command](https://learn.chatgpt.com/docs/developer-commands#codex-queue)
3. **If the live route is unavailable.** Report the blocker from [the check](#check-the-live-route). Confirm the receiver environment, exact thread ID, and Desktop transport. If the turn belongs to a private stdio server, use Desktop's queue controls for that turn. If the caller chooses to queue, report deferred delivery and point to the manual **Steer** action when available. For recurring automatic delivery, use a receiver whose shared App Server the sender can reach. [Connection details](codex.md#connect-to-the-existing-server)

### Connect Desktop and the sender to one server

Linux Desktop 26.1120.50957 and an independent Claude Code session were tested over the same private Unix socket. If Desktop is already connected to that server, get the socket path from the receiver and go directly to the check. To change the Desktop transport, let active work finish and fully quit Desktop. Stop any old App Server serving the chat before starting its replacement with the receiver's normal Codex home. [Build evidence](sources.md#desktop)

~~~bash
# First terminal on the Desktop host. Leave the App Server running.
socket_dir="${XDG_RUNTIME_DIR:?Set the receiver runtime directory}/codex-desktop-steer"
mkdir -m 0700 -p -- "$socket_dir"
socket_path="$socket_dir/app.sock"
command codex app-server --listen "unix://$socket_path"

# Second terminal on the Desktop host
socket_path="${XDG_RUNTIME_DIR:?Set the receiver runtime directory}/codex-desktop-steer/app.sock"
CODEX_APP_SERVER_WS_URL="ws+unix://localhost${socket_path}:/rpc" chatgpt
~~~

Open the intended chat in that Desktop instance. Give the sender `TARGET_CODEX_ENDPOINT="unix://$socket_path"` and its exact `TARGET_THREAD_ID`, then run the read-only check. The Desktop URL includes `localhost` and `:/rpc` in the tested build. The sender uses the plain `unix://` path. Confirm that the socket is owned by the receiving user with mode `0600` and that its parent directory has mode `0700`. If the socket path is a symlink, verify the permissions on the resolved socket and its actual parent too. Processes running as the receiving user can still connect. [Read-only check](#check-the-live-route) · [App Server transport](https://learn.chatgpt.com/docs/app-server#protocol)

For repeated use, save the Desktop launch command and receiver endpoint. Start the App Server before Desktop and check the reopened chat. For cross-machine sends to this Unix socket, use SSH to run the sender on the Desktop host. An existing loopback TCP setup can use its verified `ws://127.0.0.1:PORT` endpoint with both clients. Direct TCP without WebSocket authentication makes the endpoint accessible to local processes that can reach the port. [SSH delivery](ssh.md) · [WebSocket authentication](https://learn.chatgpt.com/docs/app-server#protocol)

## Check the live route

With the receiver's target variables set, use the skill's installed directory as `SKILL_DIR`:

```bash
node "$SKILL_DIR/scripts/steer-codex.mjs" --check
```

`--check` ignores message input and reads the loaded thread's live state without sending. For an active thread it checks the newest turn ID. An idle thread can report idle before it has saved a first turn. Both results exit 0. `not_sent` reports a failed check. Use this check to diagnose the route. The server uses its live state when handling an automatic send.

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
node "$SKILL_DIR/scripts/steer-codex.mjs" --auto /path/to/message.txt
```

For stdin, use `-`:

```bash
printf '%s' 'Message text' | node "$SKILL_DIR/scripts/steer-codex.mjs" --auto -
```

Omit the file or `-` to read exported `MESSAGE`. A file or stdin takes precedence; text, including BOM and trailing newlines, is preserved and never echoed. Empty text is sent as given. Invalid UTF-8 in a file or stdin fails before connecting; use one of those when exact bytes matter, because the environment may already have replaced invalid bytes.

The sender confirms the thread is loaded and makes one [`turn/start`](codex.md#start) request in automatic mode. The App Server decides whether to start or steer when it handles that request, so callers do not need to check whether the chat is busy first. The acknowledgement identifies the turn that received the input.

To require an existing active turn, omit `--auto`. The sender checks the live thread status and newest turn without loading item bodies. Only that turn is eligible, even if older history is still marked in progress after a restart. The server rejects a stale or changed `expectedTurnId`. Each request waits at most 5 seconds within a 15-second total budget.

## Result

| JSON `status` | Exit | Meaning |
|---|---|---|
| `accepted` | 0 | Matching server acknowledgement received; not proof the model read or finished handling the message. |
| `not_sent` | 1 | Failed before attempting delivery, such as an unloaded thread or a steer-only send to an idle chat. |
| `rejected` | 1 | The server explicitly rejected the input request. |
| `unconfirmed` | 2 | Delivery was attempted but its acknowledgement is missing or invalid; delivery may have occurred. |

Success goes to stdout; failures go to stderr. There is no automatic retry. For `unconfirmed`, inspect the target before deciding whether to send again. [Pinned protocol sources](sources.md#codex) are only needed for verification.
