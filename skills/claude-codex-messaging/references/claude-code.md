# Codex → native Claude Code

Post to the inbox of the intended, still-running Claude Code process. The address is a Unix domain socket on macOS/Linux/WSL, or a named pipe on native Windows. Keep sender and receiver in a reachable local IPC environment; host/container and WSL/native-Windows boundaries are not interchangeable paths.

## Locate the receiver

Obtain the receiver's `CLAUDE_CODE_MESSAGING_SOCKET` from its own tool environment, or its `Peer address` in `/status`. The status display prefixes the address with `uds:`; the environment variable contains the transport address itself.

The receiver also exports `CLAUDE_CODE_MESSAGING_TOKEN` to its tools/hooks. Authentication with that token is optional on Unix and required on native Windows. A session ID alone does not supply the address or token. Variables inherited by the sending Codex process are not evidence that they identify the intended CC receiver.

Pass any required token through an already authorized environment or secret-handling channel, not chat text or command-line arguments. The example below calls the receiver-supplied values `TARGET_CC_SOCKET` and `TARGET_CC_TOKEN`; these are example variable names, not CC configuration keys.

## Native wire format

Send UTF-8 newline-delimited JSON over the raw inbox connection:

```json
{"type":"auth","token":"RECEIVER_TOKEN"}
{"type":"user","message":{"role":"user","content":"MESSAGE"}}
```

Omit the auth line only where the platform permits it. Serialize the text as JSON so quotes and embedded newlines remain inside one message frame. `content` is arbitrary communication text.

The inbox address/auth mechanism is documented by Anthropic. This minimal user-message frame follows Pairroom's native sender at commit `5d43855`; it is an implementation-based integration, not a fully published, version-stable peer protocol. Pairroom sends a wake-up nudge in `content`; direct communication can put the actual message there.

## Minimal sender

With Node.js available, use this inline sender with a Unix socket or Windows named-pipe address. Run it from Bash/Git Bash in the receiver's reachable OS environment, after supplying the target values above and the message as exported environment variables (`MESSAGE` holds the text). No sender file or daemon is installed.

```bash
node --input-type=module <<'JS'
import net from "node:net";

const address = process.env.TARGET_CC_SOCKET;
const token = process.env.TARGET_CC_TOKEN;
const content = process.env.MESSAGE;
if (!address || content === undefined) {
  throw new Error("Missing target inbox or message");
}
if (process.platform === "win32" && !token) {
  throw new Error("The native Windows inbox requires its receiver token");
}

const frames = [];
if (token) frames.push({ type: "auth", token });
frames.push({ type: "user", message: { role: "user", content } });
const wire = frames.map(frame => JSON.stringify(frame)).join("\n") + "\n";

const connection = net.createConnection({ path: address });
connection.setTimeout(5000, () => {
  connection.destroy(new Error("Inbox write timed out"));
});
connection.on("error", () => {
  console.error("Inbox submission failed; check the intended live receiver");
  process.exitCode = 1;
});
connection.once("connect", () => connection.end(wire));
connection.once("finish", () => {
  console.log("Submitted; receiver acceptance is not acknowledged");
  connection.destroy();
});
JS
```

Use an address freshly supplied by the intended receiver. On Windows it has the native `\\\\.\\pipe\\...` form; a Unix path is not a Windows pipe address. Read/prepare any slow input before connecting: CC closes connections that do not produce a complete line within its timeout.

## Delivery semantics

Ordinary native inbox delivery is read between tool calls in the current turn, or starts a turn when idle; it does not interrupt a running tool. The receiver's `crossSessionInbound` controls can hold or refuse input. A valid token does not override an explicit hold/refuse setting.

A successful socket write confirms submission only. This minimal integration has no documented acceptance acknowledgement, and it does not provide a native Codex peer identity or automatic reply address. Do not infer consumption from a successful write or resend solely because no reply arrived. Do not copy SDK `priority` / `origin` fields into this frame to promise steer or interrupt behavior.

If the original inbox is unavailable, report the missing native capability. `--resume`, a new CC process, or a different SDK/cloud host does not establish delivery to that original process.

## Sources

Reviewed 2026-10-22; transport examples are not a claim of authenticated CLI/Desktop or Windows end-to-end verification.

- [Claude Code inbox, delivery, inbound policy and availability](https://code.claude.com/docs/en/cross-session-messaging).
- [Receiver environment variables](https://code.claude.com/docs/en/env-vars).
- Pairroom's pinned [native inbox writer](https://github.com/sean2077/pairroom/blob/5d43855fd54468ccf96275225ddacf9b2a0be653/internal/claudewake/inbox.go) and [target environment capture](https://github.com/sean2077/pairroom/blob/5d43855fd54468ccf96275225ddacf9b2a0be653/internal/relayclient/claude_inbox.go). Pairroom remains a source reference, not a dependency.
