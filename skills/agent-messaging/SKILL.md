---
name: agent-messaging
description: "Message existing Claude Code, Codex CLI/Desktop or Google Antigravity (agy) sessions locally or over SSH when built-in messaging cannot reach the target with the intended effect. Covers CC inbox, Codex steer/queue/start/interrupt and agy native submission; no SDK/cloud API."
---

# Agent messaging

**Send to Codex now when possible. Fall back to queue when the live route is unavailable and no message was submitted.** Use the bundled [`steer-codex.mjs --auto`](references/codex-steer.md#send) for CLI and Desktop. It steers the active turn or starts one if the chat is idle. Set the receiver's explicit `TARGET_CODEX_HOME` for local fallback, even when using a custom live endpoint. Use a built-in sender when its delivery behavior is verified for that chat. If the skill changes during a long-lived session, reread this file before sending again.

Use `--auto --no-queue` for immediate delivery only, omit `--auto` for explicitly requested steer-only, and use [native queue](references/codex-queue.md) when asked to defer. Report `queued` as queued. A loaded idle CLI or Desktop chat may start it promptly, and a busy chat normally waits for the next turn. Point to [manual Desktop Steer](references/codex-steer.md#desktop-message-stays-queued) if the item is visible there. Verify an unconfirmed delivery in the target before any resend.

Use `command codex` for direct Codex CLI commands in Bash or Zsh to bypass aliases that inject unsupported flags. The steer script spawns its proxy executable directly.

For other receivers, prefer your host's built-in messaging when it reaches the target with the intended effect, including same-product sessions/subagents. Message text, replies and workflow remain caller-owned.

| Receiver | Native route | Effect | Details |
|---|---|---|---|
| Codex | App Server `turn/start` | Send now. Start when idle or steer the active turn when busy. | [Automatic sender](references/codex-steer.md#send) |
| Codex | App Server `turn/steer` | Add input to the active turn, guarded by its turn ID. | [Steer sender](references/codex-steer.md) |
| Codex | `codex queue` | Queue input. A loaded idle target can start it promptly. | [Queue](references/codex-queue.md) |
| Codex | App Server `turn/interrupt` | Cancel current work; this operation carries no message. | [Codex](references/codex.md#interrupt) |
| Claude Code | Native inbox socket / named pipe | Submit to the running CC process. | [Inbox sender](references/claude-code.md) |
| Antigravity (`agy`) | Native `agentapi send-message` | Submit to an existing conversation; busy handling is receiver/version-dependent. | [Antigravity sender](references/antigravity.md) |

When a message from another session is stuck in Codex Desktop's queue, [handle the existing item, then check the live route for future messages](references/codex-steer.md#desktop-message-stays-queued).

For same-machine Linux Desktop sends, prefer its configured [private Unix socket](references/codex-steer.md#connect-desktop-and-the-sender-to-one-server). Get the receiver's socket path and use it as `TARGET_CODEX_ENDPOINT`.

For Codex's `send_message_to_thread`, a fresh task can fail at `thread/resume` with `no rollout found`. If the receiver is already loaded on its daemon, the [automatic sender](references/codex-steer.md#send) can deliver the first message directly.

Use the intended receiver's native environment and endpoint; this skill adds no SDK, Channel or cloud API integration. Target a distinct session or thread, never the sender's own or an inherited parent identity. An ID or shared history alone does not establish access to its live process; CLI/Desktop launches may not expose a control endpoint.

When neither route can reach the intended receiver, report the blocker. Use the receiver's existing history and live process without automatically resuming an unloaded session. No Pairroom service is required.

For another device reached through SSH, read [SSH delivery](references/ssh.md) alongside the chosen route. Otherwise read only the chosen route; reuse guidance and refresh stale target/turn details. Run bundled senders without reading code unless debugging/modifying. [Protocol sources](references/sources.md) are for verification or alternate clients.
