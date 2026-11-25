# Message native Antigravity (agy)

Read for Google Antigravity CLI (`agy`) receivers. When Antigravity's built-in `send_message` reaches the intended peer, prefer it. From another harness, use the receiver's live language server through the native `agy agentapi send-message` command.

## Target

Require Node.js and a native `agy` executable in the receiver's environment. This route was checked with CLI **1.5.14**; verify `agy --version` and `agy agentapi send-message --help` when using another version. This is Antigravity CLI, not Gemini CLI's `gemini` command.

Obtain these values from the intended receiver's tool environment and export the corresponding sender variables:

| Receiver value | Sender variable |
|---|---|
| `ANTIGRAVITY_LS_ADDRESS` | `TARGET_AGY_LS_ADDRESS` |
| `ANTIGRAVITY_CSRF_TOKEN` | `TARGET_AGY_CSRF_TOKEN` |
| `ANTIGRAVITY_CONVERSATION_ID` | `TARGET_AGY_CONVERSATION_ID` |

Confirm the conversation belongs to that live server. A saved conversation ID alone is insufficient. Do not assume every host or hook exports these values; if unavailable, obtain them from the receiver or report the missing route. The sender never selects a process from a log/cache or falls back to its own inherited endpoint. It refuses a target equal to its own inherited `ANTIGRAVITY_CONVERSATION_ID`.

Keep the token in an authorized environment/secret channel, out of chat and command arguments. The `TARGET_AGY_*` variables belong to this sender, not Antigravity configuration. Run beside the receiver's local server, including through [SSH](ssh.md) for another device; host/container and Windows/WSL loopback addresses are not interchangeable.

## Send

`SKILL_DIR` is this skill's installed directory. Pass an existing UTF-8 file directly:

```bash
node "$SKILL_DIR/scripts/send-agy.mjs" /path/to/message.txt
```

For stdin, use `-`:

```bash
printf '%s' 'Message text' | node "$SKILL_DIR/scripts/send-agy.mjs" -
```

With no argument, use exported `MESSAGE`. A file or stdin takes precedence; BOM, CRLF/LF and trailing newlines are preserved. Invalid file/stdin UTF-8 and NUL text fail before launching the native client. Use file/stdin for exact input because the host may already have replaced invalid bytes in environment variables.

The sender invokes `agy agentapi send-message -- CONVERSATION_ID CONTENT` once, with a separate argument for the full text and no shell. It maps the receiver's address/token into the child environment and removes inherited conversation/project/trajectory identity and source-step metadata so another server's context is not reused. Include a sender identity or return address in the message when needed.

Use `AGY_BIN` for a native executable at a non-default path; on Windows the default is `agy.exe`. `.cmd`/`.bat` wrappers are rejected. The native command takes content as an argument, so OS argument-size limits apply even when this sender reads a file: Linux caps one argument at 128 KiB, and Windows caps the whole command line at 32,767 characters. An oversized message fails to launch and reports `not_sent`; the sender does not split or truncate messages. Native output echoes content and is suppressed by the sender; content is still present in the short-lived client's process arguments. Tokens remain environment-only.

## Result and delivery

| JSON `status` | Exit | Meaning |
|---|---|---|
| `submitted` | 0 | The native client reported success; model reading/handling is not confirmed. |
| `not_sent` | 1 | Input/target validation or client launch failed before native submission. |
| `unconfirmed` | 2 | The launched client failed, was interrupted, or exceeded 10 seconds; delivery may have occurred. |

Success goes to stdout; failures go to stderr. Timeout or a handled interrupt/termination stops the short-lived sending client and waits for it to exit before reporting `unconfirmed`. This cannot retract a message already submitted. There is no automatic retry. After `unconfirmed`, inspect the receiver before deciding whether to resend.

This route submits to an existing conversation. It does not select Codex-style steer/queue/start/interrupt semantics, and TUI queue settings are not a verified `agentapi` contract. If exact busy behavior is required, verify that receiver/version or report that the requested effect is unavailable. Native permissions remain receiver-owned.

Do not substitute `agy -p --conversation ID`, `agy --continue`, a newly launched ACP server, or a new conversation: those do not establish delivery to the original live process. [Sources and verification limits](sources.md#antigravity-agy) distinguish native-client fixtures from live model consumption.
