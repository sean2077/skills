# Task state and evidence

`agent-work/v2` stores the title, caller-owned phase, and version in `.agents/work/<task-id>/state.json`, with events in `evidence.jsonl`. Only those two files are initialized. Put plans or specifications in the project's chosen location.

The local registry, leases, locks, transaction journal, and workspace paths live under the Git common directory's `agent-work/`. Worktrees discover the same task, whose authoritative checkout must remain available. `show` redacts the token hash; `verify` checks state/evidence consistency and registered workspaces.

## Ownership and revisions

An owner is a stable identifier chosen by the caller, such as `delivery` or `pairroom`. Acquire returns a token once. Use a protected token file or environment variable and retain the returned version. A current, unexpired lease is required for mutations; explicit `owner recover` replaces an expired lease and revokes its old token.

Example, starting just after `init`:

```bash
workctl() { python3 "<installed-skill-dir>/scripts/workctl.py" "$@"; }
workctl owner acquire task delivery --expect-version 1
# Store the returned token securely in WORKCTL_LEASE_TOKEN, without committing it.
workctl owner check task
workctl owner heartbeat task --expect-version 2 --ttl 1800
workctl transition task implementation --expect-version 3 --reason 'requirements settled'
workctl owner handoff task peer --expect-version 4
# Replace WORKCTL_LEASE_TOKEN with the NEW returned token before continuing.
workctl owner release task --expect-version 5
```

Actual versions come from command responses. Heartbeats and handoffs also advance them. A stale version fails rather than overwriting another owner's changes. Another valid owner is not silently displaced.

## Caller-owned phases and completion

A nonterminal phase is an identifier chosen by the caller; changing it records an event. The protocol supplies no mandatory sequence, planning artifact, or retry budget. `done` and `cancelled` are reserved terminal labels. Terminal tasks permit lease housekeeping and workspace cleanup, not new work, evidence, or reopening.

To enter `done`, the latest `test`, `verify`, `verification`, `ci`, or `quality-gate` event after the most recent nonterminal phase change must contain a successful result. At least one of the following is required, and **every present result field must agree**:

- `passed`: boolean `true`;
- `exit_code`: integer `0`, not a boolean or string;
- `status`: `"passed"` or `"success"`.

A newer failure or malformed result supersedes an earlier pass. A phase change invalidates earlier verification. The caller must also refresh verification whenever code, inputs, environment, or acceptance changes within a phase; the protocol cannot infer those external changes. Completion checks current workspace scope and snapshot integrity, but it does not run a verifier itself.

## Evidence input and receipts

```bash
workctl evidence task --kind test --payload '{"exit_code":0,"command":"pytest tests/unit"}' --expect-version <n>
workctl evidence task --kind review --payload-file review-evidence.json --expect-version <n>
workctl transition task done --expect-version <n> --reason 'verified delivery'
workctl verify task
```

Inline/file payloads are alternative JSON-object inputs, bounded to 1 MiB. Include only actually observed results. The ordinary response contains the new `version` and a `receipt` with event `seq`, `kind`, and `hash`; `--full` additionally returns the event. The log remains complete, so large input need not be echoed into the Agent's context.

Internal `task-init`, `state-transition`, `owner-*`, and `workspace-*` event kinds are reserved. User evidence cannot impersonate protocol transitions. The hash chain detects broken or inconsistent records, not a malicious rewrite by an actor who controls the repository and can recompute hashes. It is not signed attestation of command execution.

## Recovery and earlier versions

Interrupted mutations use the transaction journal for recovery. Resolve corruption or unavailable authority paths from preserved evidence; do not rewrite hashes, registries, or task state by hand. Use `doctor --task-id <id>` and `verify <id>` for diagnosis. Cleanup follows [workspace isolation](workspace-isolation.md).

`agent-work/v1` tasks are not automatically adopted. A matching legacy registry is rejected before v2 state is created, and existing task directories are preserved. Finish or inspect old tasks using the previous runtime. For v2, use a new task ID, caller-chosen owner/phase labels, and `writer` in place of `driver`, `worker`, or `integrator`. The old `risk` selector and `--max-verify-retries` are removed; retain those policies in the calling workflow where needed.

Process success means the requested operation succeeded, not that the task is complete. Inspect the returned phase and verification result. Error classes distinguish usage/data, Git, lock, version conflict, lease, terminal/completion, workspace, and integrity failures.
