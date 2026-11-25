---
name: agent-messaging
description: "Message existing Claude Code, Codex CLI/Desktop or Google Antigravity (agy) sessions locally or over SSH when built-in messaging cannot reach the target with the intended effect. Covers CC inbox, Codex steer/queue/start/interrupt and agy native submission; no SDK/cloud API."
---

# Agent messaging

Prefer your host's built-in messaging when it reaches the target with the intended effect, including same-product sessions/subagents. Message text, replies and workflow remain caller-owned.

**For Codex, default to steering the active turn.** A request to send a message to a running Codex session with no timing specified uses the [steer sender](references/codex-steer.md), or a built-in sender verified to steer. Use [queue](references/codex-queue.md) only when the caller wants later handling. If steering fails or the receiver is unreachable, report the result and the blocker. An unconfirmed result needs a target check before any resend. For an idle receiver, use [start](references/codex.md#start) when the caller wants a new turn to run now.

| Receiver | Native route | Effect | Details |
|---|---|---|---|
| Codex | App Server `turn/steer` | Add input to the active turn, guarded by its turn ID. | [Steer sender](references/codex-steer.md) |
| Codex | `codex queue` | Queue input for a later turn; a loaded idle target can start it. | [Queue](references/codex-queue.md) |
| Codex | App Server `turn/start` | Start when idle; the verified implementation can steer when busy. | [Codex](references/codex.md#start) |
| Codex | App Server `turn/interrupt` | Cancel current work; this operation carries no message. | [Codex](references/codex.md#interrupt) |
| Claude Code | Native inbox socket / named pipe | Submit to the running CC process. | [Inbox sender](references/claude-code.md) |
| Antigravity (`agy`) | Native `agentapi send-message` | Submit to an existing conversation; busy handling is receiver/version-dependent. | [Antigravity sender](references/antigravity.md) |

When a message from another session is stuck in Codex Desktop's queue, [handle the existing item, then check the live route for future messages](references/codex-steer.md#desktop-message-stays-queued).

For Codex's `send_message_to_thread`, a fresh task can fail at `thread/resume` with `no rollout found`. If the receiver is already loaded on its daemon and the caller wants queued delivery, [queue the first message](references/codex-queue.md#first-message-to-a-fresh-codex-task).

Use the intended receiver's native environment and endpoint; this skill adds no SDK, Channel or cloud API integration. Target a distinct session or thread, never the sender's own or an inherited parent identity. An ID or shared history alone does not establish access to its live process; CLI/Desktop launches may not expose a control endpoint.

If the required endpoint or operation is unavailable, report it; do not silently substitute another operation or a newly resumed process. No Pairroom service is required.

For another device reached through SSH, read [SSH delivery](references/ssh.md) alongside the chosen route. Otherwise read only the chosen route; reuse guidance and refresh stale target/turn details. Run bundled senders without reading code unless debugging/modifying. [Protocol sources](references/sources.md) are for verification or alternate clients.
