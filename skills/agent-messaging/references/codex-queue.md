# Queue input for native Codex

Use this command for an explicit request to defer. For ordinary delivery, the [automatic sender](codex-steer.md#send) prefers live input and uses queue as its fallback. Verify the receiver's exact thread UUID and ensure it differs from the sender's `CODEX_THREAD_ID`.

For a **local receiver**, run on its host from its absolute Codex home with `CODEX_HOME` set to that directory. This keeps the sender's project config out of the queue call. If the receiver sets `CODEX_SQLITE_HOME` in its environment, use the same value. Otherwise unset any inherited override from the sender. The native CLI can use a local daemon or a short-lived embedded App Server. An existing saved thread can be queued even when no shared listener is running. [Codex 0.172.0 server selection](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/tui/src/session_archive_commands.rs#L273-L294) · [Native queue command](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/tui/src/session_queue_commands.rs#L29-L88)

```bash
(
  receiver_home="${TARGET_CODEX_HOME:?Set the receiver's Codex home}"
  cd -- "$receiver_home" || exit
  CODEX_HOME="$receiver_home" command codex queue --thread "$TARGET_THREAD_ID" --message="$MESSAGE"
)
```

For a **remote receiver**, use its verified reachable endpoint instead of local daemon discovery:

```bash
command codex queue --thread "$TARGET_THREAD_ID" --message="$MESSAGE" --remote "$TARGET_CODEX_ENDPOINT"
```

Use `command codex` in Bash or Zsh to bypass aliases that add unsupported interactive flags such as `--dangerously-bypass-approvals-and-sandbox`. Omit `--no-daemon` from the sending command and leave server selection to the CLI, even if the receiver was launched with `--no-daemon`. For an authenticated remote endpoint, `--remote-auth-token-env NAME` specifies the environment variable containing its token.

The CLI uses `thread/queue/add`. On Codex CLI **0.166.0+**, append `--resume` to the chosen command only if the recipient should also be activated.

`--resume` tries to resume an unloaded thread on the local daemon or selected `--remote` server. It leaves loaded threads alone. A failed resume warns but **still exits successfully** if the message was queued; it cannot take over another active writer. Verified by [Codex 0.166.0's release](https://github.com/openai/codex/releases/tag/rust-v0.166.0) and [PR #57232's implementation/tests](https://github.com/openai/codex/pull/57232), not by live-session execution.

Report a queue acknowledgement as queued. In Desktop, use the existing item's [manual Steer](codex-steer.md#desktop-message-stays-queued) if available. In the interactive CLI, typing a follow-up and pressing Enter while Codex works can steer. That composer action is separate from running the external `codex queue` command. [Interactive steering and queuing](https://learn.chatgpt.com/docs/prompting#steering-and-queuing)

Queue semantics:

- A loaded idle thread can start the queued message promptly. A busy thread can accept it immediately into the queue and process it in a later turn. Separate servers sharing the same storage may discover the change on a poll. Under an active `/goal`, consecutive continuations can delay dispatch. [Dispatch source](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/ext/queue/src/service.rs#L418-L495) · [Earlier Windows report](https://github.com/openai/codex/issues/52705)
- An existing saved thread can keep queued input until it is loaded. A fresh thread with no saved history needs to be loaded on the receiving server. Interrupted threads are not automatically restarted, and archived or ephemeral threads can reject queueing. [Queue target validation](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/app-server/src/request_processors/thread_queue_processor.rs#L249-L311)
- A successful command acknowledges storage of the queue item, even when optional `--resume` warns. Check the target's queue and history when delivery is uncertain. Repeating the command can add a second item.

Linux tests with CLI 0.172.0 and the Desktop-bundled 0.171.0-alpha.13.2 verified queue storage and dispatch with isolated sessions. Check `codex --version` and `codex queue --help` for the installed command. [Verification details](sources.md#queue-and-fallback)

## First message to a fresh Codex task

In Codex CLI 0.172.0, the built-in `send_message_to_thread` reads the thread, then calls `thread/resume` before submitting the message. A fresh task can already be loaded and idle on its daemon while its session record (rollout) is still unwritten. The explicit `thread/resume failed: no rollout found` error occurs before the tool submits the message. [Built-in sender](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/tui/src/dynamic_tools.rs#L714-L755) · [Zero-turn resume test](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/app-server/tests/suite/v2/thread_resume.rs#L518-L565)

Confirm the exact thread ID is loaded on the receiver's App Server using `thread/loaded/list`. If queueing suits the request, use the receiver's confirmed `CODEX_HOME` or endpoint with the queue command above. Omit `--resume` for a loaded receiver. An idle receiver can start the queued turn and persist its rollout. [App Server connection and thread lookup](codex.md#connect-to-the-existing-server) · [Loaded-thread queue path](https://github.com/openai/codex/blob/rust-v0.172.0/codex-rs/app-server/src/request_processors/thread_queue_processor.rs#L267-L292)

A queue acknowledgement only confirms that the message was queued. In a live Linux check on 2026-11-25 with Codex CLI 0.172.0, the queued message started the target's first turn and created the rollout. The next built-in send succeeded and appeared in the same thread. For subsequent deliveries, choose the route by the requested timing.
