---
name: claude-codex-messaging
description: "Message between existing native Claude Code and Codex CLI/Desktop sessions only. Excludes same-product sessions/subagents, SDKs, Channels and cloud APIs."
---

# Claude–Codex messaging

Choose the intended effect and read only its reference. Reuse guidance already in context; refresh stale connection details and active turn IDs. Message text, reply conventions and workflow remain caller-owned.

| Direction | Native route | Effect | Details |
|---|---|---|---|
| Claude Code → Codex | `codex queue` | Queue input for a later turn; a loaded idle target can start it. | [Queue](references/codex-queue.md) |
| Claude Code → Codex | App Server `turn/steer` | Add input to the active turn, guarded by its turn ID. | [Codex](references/codex.md#steer) |
| Claude Code → Codex | App Server `turn/start` | Start when idle; the verified implementation can steer when busy. | [Codex](references/codex.md#start) |
| Claude Code → Codex | App Server `turn/interrupt` | Cancel current work; this operation carries no message. | [Codex](references/codex.md#interrupt) |
| Codex → Claude Code | Native inbox socket / named pipe | Submit to the running CC process. | [Inbox sender](references/claude-code.md) |

Use the intended receiver's native environment and endpoint. An ID or shared history alone does not establish access to its live process; CLI/Desktop launches may not expose a control endpoint.

If the required endpoint or operation is unavailable, report it; do not silently substitute another operation or a newly resumed process. No Pairroom service is required.

Read [protocol sources and raw CC frames](references/sources.md) only for verification or an alternate client. Run the bundled sender without reading its implementation unless debugging or modifying it.
