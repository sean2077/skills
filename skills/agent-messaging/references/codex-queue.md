# Queue input for native Codex

Read for queued delivery to an existing native Codex thread. To affect an active turn, use [steer](codex-steer.md). Prefer the receiver's thread UUID over an ambiguous name. Never queue to the sender's own `CODEX_THREAD_ID`, and verify the chosen thread belongs to the receiver.

For a **local receiver**, set `TARGET_CODEX_HOME` to its actual Codex home as seen by the CLI process (not an inherited sender home), then pass it explicitly. `codex queue` selects its local daemon using `CODEX_HOME` or the calling user's default even when `--thread` is a UUID. An unset or wrong home can target the wrong server. Do not guess a Windows/WSL/container path.

```bash
CODEX_HOME="${TARGET_CODEX_HOME:?Set the receiver's Codex home}" \
  codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE"
```

For a **remote receiver**, use its verified reachable endpoint instead of local daemon discovery:

```bash
codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE" --remote "$TARGET_ENDPOINT"
```

If authenticated, `--remote-auth-token-env NAME` names the environment variable containing its token. `--no-daemon` is rejected for `codex queue`, with or without `--remote`: queuing must reach the shared server rather than a separate one. The native CLI handles transport selection; it does not need a separate App Server client.

The CLI uses `thread/queue/add`. On Codex CLI **0.166.0+**, use `--resume` only if the recipient should be activated rather than merely queued:

```bash
CODEX_HOME="${TARGET_CODEX_HOME:?Set the receiver's Codex home}" \
  codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE" --resume
```

`--resume` tries to resume an unloaded thread on the local daemon or selected `--remote` server. It leaves loaded threads alone. A failed resume warns but **still exits successfully** if the message was queued; it cannot take over another active writer. Verified by [Codex 0.166.0's release](https://github.com/openai/codex/releases/tag/rust-v0.166.0) and [PR #57232's implementation/tests](https://github.com/openai/codex/pull/57232), not by live-session execution.

Queue semantics:

- Loaded + idle can begin the queued turn; busy normally waits for a turn boundary. Under an active `/goal`, continuations may starve the queue ([open Windows App 26.1002.7124.0 / CLI 0.160.1 report](https://github.com/openai/codex/issues/52705)); this was not reproduced or verified on newer builds.
- Unloaded input persists until the thread resumes; optional `--resume` attempts activation, not guaranteed delivery.
- An interrupted target is not automatically restarted; archived/ephemeral threads reject delivery.
- Success means **queued**, not read/completed, even when `--resume` warns. Check target consumption where needed; do not blindly retry, since each repeat adds another message.

Core queue semantics reviewed at Codex 0.163.0; `--resume` and local home selection source-reviewed at 0.166.0 (2026-11-06 and 2026-11-13 respectively). The [version-pinned queue implementation](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/session_queue_commands.rs) and [home resolution](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/utils/home-dir/src/lib.rs) establish routing, not live consumption. Check `codex --version` / `codex queue --help` before using a version-specific flag. [Version-pinned evidence](sources.md#codex) is for verification, not required for each send.
