---
name: agent-messaging
description: "Message existing native Claude Code or Codex CLI/Desktop sessions from any harness when your host's built-in messaging cannot reach the target with the intended effect. Covers CC inbox and Codex steer/queue/start/interrupt."
---

# Agent messaging

Prefer your host's built-in messaging when it reaches the target with the intended effect, including same-product sessions/subagents. Otherwise choose by receiver and effect: steer for ongoing work, queue for later handling. Message text, replies and workflow remain caller-owned.

| Receiver | Native route | Effect | Details |
|---|---|---|---|
| Codex | App Server `turn/steer` | Add input to the active turn, guarded by its turn ID. | [Steer sender](references/codex-steer.md) |
| Codex | `codex queue` | Queue input for a later turn; a loaded idle target can start it. | [Queue](references/codex-queue.md) |
| Codex | App Server `turn/start` | Start when idle; the verified implementation can steer when busy. | [Codex](references/codex.md#start) |
| Codex | App Server `turn/interrupt` | Cancel current work; this operation carries no message. | [Codex](references/codex.md#interrupt) |
| Claude Code | Native inbox socket / named pipe | Submit to the running CC process. | [Inbox sender](references/claude-code.md) |

Use the intended receiver's native environment and endpoint; this skill adds no SDK, Channel or cloud API integration. Target a distinct session or thread, never the sender's own or an inherited parent identity. An ID or shared history alone does not establish access to its live process; CLI/Desktop launches may not expose a control endpoint.

If the required endpoint or operation is unavailable, report it; do not silently substitute another operation or a newly resumed process. No Pairroom service is required.

Read only the chosen route; reuse guidance and refresh stale target/turn details. Run bundled senders without reading code unless debugging/modifying. [Protocol sources](references/sources.md) are for verification or alternate clients.
