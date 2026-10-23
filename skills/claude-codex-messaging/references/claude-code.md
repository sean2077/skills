# Codex → native Claude Code

Read for sending to an existing CC process.

## Target

Obtain `CLAUDE_CODE_MESSAGING_SOCKET` from the **receiver's** tool environment, or its `/status` Peer address (remove the display prefix `uds:`). Export that address as `TARGET_CC_SOCKET`. The sending process's inherited CC variables do not identify the intended receiver.

Use a reachable local IPC environment: Unix socket on macOS/Linux/WSL, native `\\.\pipe\...` on Windows. Container/host and WSL/Windows paths are not interchangeable.

Obtain the receiver's `CLAUDE_CODE_MESSAGING_TOKEN` and export it as `TARGET_CC_TOKEN` when needed: optional on Unix, required on native Windows. Keep tokens in an authorized environment/secret channel, out of chat and command arguments. The `TARGET_CC_*` names belong to this sender, not CC configuration.

## Send

With Node.js available, call the bundled sender; `SKILL_DIR` is this skill's installed directory:

```bash
node "$SKILL_DIR/scripts/send-claude.mjs" /path/to/message.txt
```

Pass an existing UTF-8 file directly instead of reading its body into tool output and regenerating it. For stdin, use `-`:

```bash
printf '%s' 'Message text' | node "$SKILL_DIR/scripts/send-claude.mjs" -
```

With no argument, the sender uses exported `MESSAGE`. A file or `-` takes precedence over `MESSAGE`; text is preserved, including trailing newlines. Input is read before connecting, sent once, and never echoed. Exit 0 reports **submission only**, without receiver acceptance.

## Delivery

CC reads ordinary inbox input between tool calls, or starts a turn when idle; it does not interrupt a running tool. Receiver `crossSessionInbound` may hold/refuse input even with a valid token.

There is no acceptance/read acknowledgement, native Codex peer identity or automatic reply address. Do not resend merely because no reply arrived, or add SDK `priority`/`origin` fields to promise steer/interrupt behavior.

The native frame follows pinned Pairroom code, not a fully published stable peer protocol. [Raw frames and evidence](sources.md#claude-code) are available for alternate clients or protocol checks.
