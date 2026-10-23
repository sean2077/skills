# Protocol sources

Read only to verify an interface/version or implement an alternate CC client. Sources were reviewed 2026-10-22; this is not authenticated CLI/Desktop or Windows end-to-end certification.

## Claude Code

An alternate inbox client sends UTF-8 newline-delimited JSON over the raw socket/pipe, omitting auth only where permitted:

```json
{"type":"auth","token":"RECEIVER_TOKEN"}
{"type":"user","message":{"role":"user","content":"MESSAGE"}}
```

Serialize arbitrary text as JSON; prepare input before connecting so CC's incomplete-line timeout is not spent waiting for input. These are native transport fields, not a business-message format. Pairroom uses a wake-up nudge as content; direct communication can carry the message itself.

- [Native inbox, delivery, inbound policy and availability](https://code.claude.com/docs/en/cross-session-messaging).
- [Receiver environment variables](https://code.claude.com/docs/en/env-vars).
- Pairroom `5d43855`: [inbox writer](https://github.com/sean2077/pairroom/blob/5d43855fd54468ccf96275225ddacf9b2a0be653/internal/claudewake/inbox.go) and [target environment capture](https://github.com/sean2077/pairroom/blob/5d43855fd54468ccf96275225ddacf9b2a0be653/internal/relayclient/claude_inbox.go). The frame is implementation-based, not a fully published stable peer protocol. Pairroom is not a dependency.

## Codex

Verified source: `rust-v0.163.0`, commit `83086188ae0614bd882818ff1aa23f3194962012`.

- [Official command reference](https://learn.chatgpt.com/docs/developer-commands) and [App Server protocol](https://learn.chatgpt.com/docs/app-server).
- [Queue command](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/session_queue_commands.rs) and [queue dispatch](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/ext/queue/src/service.rs).
- [Control socket path](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-transport/src/transport/mod.rs) and [WebSocket acceptance](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-transport/src/transport/unix_socket.rs).
- [Windows AF_UNIX](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/uds/src/lib.rs) and [native peer checks](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/uds/src/windows_peer.rs).
- [Turn input semantics](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/request_processors/turn_processor.rs), [live turn reads](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/request_processors/thread_processor.rs), and [request schemas](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-protocol/src/protocol/v2/thread.rs).
