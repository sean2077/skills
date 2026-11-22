# Protocol sources

Read only to verify an interface/version or implement an alternate client. Claude Code and the base Codex sources were reviewed 2026-10-22; later checks are dated below. This is not authenticated CLI/Desktop or Windows end-to-end certification.

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
- Proxy source additionally reviewed 2026-10-25: [`app-server proxy --sock`](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/cli/src/main.rs) and [stdio-to-socket byte relay](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/stdio-to-uds/src/lib.rs). It connects to an existing socket without starting a server; bytes still carry HTTP Upgrade and WebSocket frames, not newline-delimited JSON.
- [Windows AF_UNIX](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/uds/src/lib.rs) and [native peer checks](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/uds/src/windows_peer.rs).
- [Turn input semantics](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/request_processors/turn_processor.rs), [live turn reads](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/request_processors/thread_processor.rs), and [request schemas](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-protocol/src/protocol/v2/thread.rs).

## Antigravity (agy)

Reviewed 2026-11-22:

- [Official CLI 1.5.14 release](https://github.com/google-antigravity/antigravity-cli/releases/tag/1.5.14) and its `agy_cli_linux_x64.tar.gz` asset. Actual Linux executable checks confirmed `agy agentapi send-message [--title=<title>] <recipient_id> <content>` and `--` argument termination. Archive SHA-256: `d58386322d2073e96b33f7cc32b4e9ae2db6228f58440369725967b2de48c7b5`.
- [Google's native notifier](https://github.com/google/artemis/blob/351ca8422f7b5b54e80a9c1ce03a222e02415b6b/mcp_server/notifiers/agentapi.py) corroborates the receiver environment variables and native command invocation. Do not copy its process-scanning/retry policy into target selection.
- [Official sidecar `agentapi` documentation](https://antigravity.google/docs/sidecars/#agentapi) describes sending to existing conversations, but is App-scoped. CLI evidence comes from the executable checks above. [Native peer tools](https://antigravity.google/docs/hooks/#supported-tools) remain preferable when they can reach the target.
- [Headless continuation](https://antigravity.google/docs/cli/headless/#continue-a-conversation) starts a new process; [ACP](https://antigravity.google/docs/ide/extensions/acp) uses its own client connection. Neither proves attachment to an arbitrary existing CLI session.

The native executable and bundled sender were exercised against disposable local HTTP/2 gRPC fixtures: successful delivery, exact UTF-8 text, option-like text, explicit rejection, missing/malformed acknowledgement, dropped connection and timeout. Checks observed one `SendAgentMessage` call per send, receiver-selected address/token, no inherited source-step metadata, and no message/token echo from the wrapper. This verifies client/transport behavior, not authenticated model consumption, busy-target steer/queue behavior or native Windows execution. Use the native client; the observed internal RPC is not a stable public wire contract.
