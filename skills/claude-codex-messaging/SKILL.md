---
name: claude-codex-messaging
description: "Use only for communication between existing native Claude Code and Codex CLI/Desktop sessions through their native interfaces. Covers delivery routes such as queue and steer. Not for communication within Claude Code or within Codex."
---

# Claude–Codex messaging

Connect an existing Claude Code session with an existing Codex CLI/Desktop thread. Read only the reference for the receiving product. Choose the operation by its effect; message content, reply conventions, and collaboration workflow remain task-specific.

| Direction | Native route | Effect | Details |
|---|---|---|---|
| Claude Code → Codex | `codex queue` | Queue input for a later turn; a loaded idle target can start it. | [Codex](references/codex.md#queue) |
| Claude Code → Codex | App Server `turn/steer` | Add input to the active turn, guarded by its turn ID. | [Codex](references/codex.md#steer) |
| Claude Code → Codex | App Server `turn/start` | Start when idle; the verified implementation can steer when busy. | [Codex](references/codex.md#start) |
| Claude Code → Codex | App Server `turn/interrupt` | Cancel current work; this operation carries no message. | [Codex](references/codex.md#interrupt) |
| Codex → Claude Code | Native inbox socket / named pipe | Post to the running CC process; see its delivery timing and inbound controls. | [Claude Code](references/claude-code.md) |

Use the receiver's actual native environment and connection details. A thread/session ID identifies a conversation but is not necessarily enough to connect to its running process. CLI/Desktop branding alone does not establish that an external control endpoint is available.

Keep the intended operation explicit: queue, steer, start, and interrupt have different effects. If the required endpoint or operation is unavailable, report that limitation; do not silently replace it with a different operation or a newly resumed process.

This route does not cover same-product sessions/subagents, SDK-hosted agents, Channels, or cloud-session APIs. No Pairroom service is required. The JSON examples are native transport envelopes, not a required format for the agents' message text.
