# Send to a Codex chat

Use [`steer-codex.mjs --auto`](#send) for ordinary CLI and Desktop delivery. A loaded chat on a reachable server starts a turn when idle or receives the input in its active turn. When the live route is unavailable, automatic mode can [queue once](#queue-fallback). Use [native queue](codex-queue.md) directly for an explicit request to defer.

## Target

Require Node.js 22.4+ and export the intended receiver's exact `TARGET_THREAD_ID` UUID. Set the receiver's home for local delivery and add its endpoint if it uses a custom socket:

- `TARGET_CODEX_HOME`: the receiver's existing, absolute Codex home. Supplies the default `app-server-control/app-server-control.sock` and the local queue fallback destination.
- `TARGET_CODEX_ENDPOINT`: the receiver's existing `ws://`, `wss://` or `unix://ABSOLUTE_PATH` endpoint. Takes precedence for the live connection. A reachable endpoint can also accept a queue fallback for an unloaded chat.
- `TARGET_CODEX_SQLITE_HOME`: the receiver's existing, absolute SQLite home, when its process uses a separate `CODEX_SQLITE_HOME` environment override. If the receiver uses its config or the default store, omit this.

Use the server that owns the live turn. The sender refuses its own `CODEX_THREAD_ID`. Container, host, WSL and native Windows each have their own paths and sockets. For a receiver on another machine with no reachable endpoint, [run the sender on that machine over SSH](ssh.md) with the receiver's home.

The local socket route requires `codex app-server proxy --sock PATH`, verified in Codex 0.163.0. The sender starts the native proxy or queue command without a shell, bypassing aliases. On Windows it resolves `codex.exe` or the npm JS launcher. Set `CODEX_BIN` to a native executable or `.js`/`.mjs`/`.cjs` launcher when required, including the bundled executable if only Desktop is installed. The proxy relays WebSocket bytes through a local bridge.

Direct WebSocket connections cannot supply custom authentication headers. Use an authorized alternate client if the endpoint requires them; keep tokens out of endpoint URLs. See [raw App Server requests](codex.md) when needed.

## Desktop message stays queued

1. **Handle the existing message.** In the receiving Desktop chat, find it in the queue above the composer and use **Steer** if offered. This can apply the existing item to the current turn. During compaction, Desktop may have to wait. [Desktop queue controls](https://learn.chatgpt.com/docs/prompting#steering-and-queuing) · [Compaction behavior](https://learn.chatgpt.com/docs/changelog?date=2026-10-15)
2. **Check the route for the next message.** Desktop's **Settings → General → Follow-up behavior** controls its composer. The external `codex queue` command always adds a queued item. Use [the read-only check](#check-the-live-route) to diagnose whether the sender can reach the live chat. Check the existing queue or turn before resending the same text. [CLI queue command](https://learn.chatgpt.com/docs/developer-commands#codex-queue)
3. **For recurring sends.** A private stdio Desktop can use [local queue fallback](#queue-fallback) with the receiver's home. For automatic delivery into a busy turn, connect the Desktop and sender to the same reachable App Server.

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

Open the intended chat in that Desktop instance. Give the sender `TARGET_CODEX_ENDPOINT="unix://$socket_path"`, its exact `TARGET_THREAD_ID`, and the receiver's `TARGET_CODEX_HOME` for fallback. The Desktop URL includes `localhost` and `:/rpc` in the tested build. The sender uses the plain `unix://` path. Confirm that the socket is owned by the receiving user with mode `0600` and that its parent directory has mode `0700`. If the socket path is a symlink, verify the permissions on the resolved socket and its actual parent too. Processes running as the receiving user can still connect. [Read-only check](#check-the-live-route) · [App Server transport](https://learn.chatgpt.com/docs/app-server#protocol)

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
| `websocket_unavailable` | The direct WebSocket could not be used. Verify the endpoint and its authentication requirements. |
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

When the thread is loaded, the sender makes one [`turn/start`](codex.md#start) request. The App Server chooses whether to start or steer when handling the request. Its acknowledgement identifies the receiving turn. Use `--auto --no-queue` when the caller requires live delivery.

To require an existing active turn, omit `--auto`. The sender checks the live thread status and newest turn without loading item bodies. Only that turn is eligible, even if older history is still marked in progress after a restart. The server rejects a stale or changed `expectedTurnId`. Each request waits at most 5 seconds within a 15-second total budget.

## Queue fallback

If a reachable App Server has not loaded the target, automatic mode calls `codex queue --remote` on that same endpoint. If the live endpoint is unavailable, it uses native `codex queue` from the confirmed receiver's `TARGET_CODEX_HOME` on that host. A private stdio session or an existing saved chat can receive queued input without a persistent daemon. The sender uses the exact UUID, omits `--resume`, and ignores the sender's storage environment override for the local fallback. It waits up to 10 seconds for the native queue acknowledgement. [Queue behavior](codex-queue.md)

Fallback is attempted only before a live message request is sent. An explicit RPC rejection or an uncertain acknowledgement ends the send. The queue command takes text as one argument, so native argument size limits apply and process inspection can expose the message while it runs. Use live-only mode for text that must stay out of process arguments.

## Result

| JSON `status` | Exit | Meaning |
|---|---|---|
| `accepted` | 0 | The App Server acknowledged live delivery into the returned turn. |
| `queued` | 0 | Native Codex acknowledged a queue item for the exact thread. `queueId` identifies the item and `reason` identifies the live-route failure. |
| `not_sent` | 1 | Failed before attempting message submission. |
| `rejected` | 1 | The server explicitly rejected the input request. |
| `unconfirmed` | 2 | The sender attempted delivery or launched the queue command and could not confirm the outcome. |

Success goes to stdout and failures go to stderr. An acknowledgement confirms submission. For `unconfirmed`, inspect the target queue and history before deciding whether to resend.
