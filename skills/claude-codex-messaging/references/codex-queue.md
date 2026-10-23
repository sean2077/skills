# Claude Code → Codex queue

Read for queued delivery to an existing native Codex thread. Use the recipient's `CODEX_HOME` / endpoint and prefer its thread UUID over an ambiguous name.

```bash
codex queue --thread "$TARGET_THREAD_ID" --message "$MESSAGE"
```

For the recipient's existing remote endpoint, add `--remote "$TARGET_ENDPOINT"`. If authenticated, `--remote-auth-token-env NAME` names the environment variable containing its token. The native CLI handles transport selection; it does not need a separate App Server client.

The CLI uses `thread/queue/add`:

- Loaded + idle can begin the queued turn; busy waits until the current turn finishes.
- Unloaded input persists until the native client resumes that thread.
- An interrupted target is not automatically restarted; archived/ephemeral threads reject delivery.
- Success means **queued**, not read/completed. Repeating the command adds another message.

Checked against Codex 0.163.0. Check `codex --version` / `codex queue --help` when availability or syntax is uncertain. [Version-pinned evidence](sources.md#codex) is for verification, not required for each send.
