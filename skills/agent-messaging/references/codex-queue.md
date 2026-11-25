# Queue input for native Codex

Use this route when the caller wants the message handled later. When sending to a running Codex thread with no timing specified, use [steer](codex-steer.md). Prefer the receiver's thread UUID over an ambiguous name. Never queue to the sender's own `CODEX_THREAD_ID`, and verify the chosen thread belongs to the receiver.

For a **local receiver**, set `TARGET_CODEX_HOME` to its actual Codex home as seen by the CLI process (not an inherited sender home), then bind it to `CODEX_HOME` for the call. `codex queue` selects its local daemon using `CODEX_HOME` or the calling user's default, even when `--thread` is a UUID. An unset or wrong home can target the wrong server. Do not guess a Windows/WSL/container path.

```bash
CODEX_HOME="${TARGET_CODEX_HOME:?Set the receiver's Codex home}" \
  codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE"
```

For a **remote receiver**, use its verified reachable endpoint instead of local daemon discovery:

```bash
codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE" --remote "$TARGET_ENDPOINT"
```

If authenticated, `--remote-auth-token-env NAME` names the environment variable containing its token. `--no-daemon` is rejected for `codex queue` in both local and `--remote` modes; local queueing must reach the shared daemon rather than a separate server. The native CLI handles transport selection; it does not need a separate App Server client.

The CLI uses `thread/queue/add`. On Codex CLI **0.166.0+**, use `--resume` only if the recipient should be activated rather than merely queued:

```bash
CODEX_HOME="${TARGET_CODEX_HOME:?Set the receiver's Codex home}" \
  codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE" --resume
```

`--resume` tries to resume an unloaded thread on the local daemon or selected `--remote` server. It leaves loaded threads alone. A failed resume warns but **still exits successfully** if the message was queued; it cannot take over another active writer. Verified by [Codex 0.166.0's release](https://github.com/openai/codex/releases/tag/rust-v0.166.0) and [PR #57232's implementation/tests](https://github.com/openai/codex/pull/57232), not by live-session execution.

For a queued message that needs attention during a busy Desktop turn, use the [Desktop queue and live-steer procedure](codex-steer.md#desktop-message-stays-queued).

Queue semantics:

- Loaded + idle can begin the queued turn; busy normally waits for a turn boundary. Under an active `/goal`, continuations may starve the queue ([open Windows App 26.1002.7124.0 / CLI 0.160.1 report](https://github.com/openai/codex/issues/52705)); this was not reproduced or verified on newer builds.
- Unloaded input persists until the thread resumes; optional `--resume` attempts activation, not guaranteed delivery.
- An interrupted target is not automatically restarted; archived/ephemeral threads reject delivery.
- Success means **queued**, not read/completed, even when `--resume` warns. Check target consumption where needed; do not blindly retry, since each repeat adds another message.

Core queue semantics reviewed at Codex 0.163.0; `--resume` and local home selection source-reviewed at 0.166.0 (2026-11-06 and 2026-11-13 respectively). The [version-pinned queue implementation](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/session_queue_commands.rs) and [home resolution](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/utils/home-dir/src/lib.rs) establish routing, not live consumption. Check `codex --version` / `codex queue --help` before using a version-specific flag. [Version-pinned evidence](sources.md#codex) is for verification, not required for each send.

## First message to a fresh Codex task

In Codex CLI 0.172.0, the built-in `send_message_to_thread` reads the thread, then calls `thread/resume` before submitting the message. A fresh task can already be loaded and idle on its daemon while its session record (rollout) is still unwritten. The explicit `thread/resume failed: no rollout found` error occurs before the tool submits the message. [Built-in sender](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/tui/src/dynamic_tools.rs#L714-L755) · [Zero-turn resume test](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/app-server/tests/suite/v2/thread_resume.rs#L518-L565)

Confirm the exact thread ID is loaded on the receiver's App Server using `thread/loaded/list`. If queueing suits the request, use the receiver's confirmed `CODEX_HOME` or endpoint with the queue command above. Omit `--resume` for a loaded receiver. An idle receiver can start the queued turn and persist its rollout. [App Server connection and thread lookup](codex.md#connect-to-the-existing-server) · [Loaded-thread queue path](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/app-server/src/request_processors/thread_queue_processor.rs#L267-L292)

A queue acknowledgement only confirms that the message was queued. In a live Linux check on 2026-11-25 with Codex CLI 0.172.0, the queued message started the target's first turn and created the rollout. The next built-in send succeeded and appeared in the same thread. For subsequent deliveries, choose the route by the requested timing.
