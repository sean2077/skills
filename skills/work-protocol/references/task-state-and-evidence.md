# Task state and evidence

Read this only when creating, resuming, handing off, recovering, or verifying a durable `work-protocol` task.

## Portable and local state

Committed artifacts live at `.agents/work/<task-id>/`:

- `brief.md`: goal, non-goals, acceptance evidence, and authority boundaries.
- `plan.md`: ordered slices, dependencies, risks, and ownership.
- `state.json`: `agent-work/v1`, current phase, state version, loop owner, and bounded verify retry count.
- `evidence.jsonl`: append-only sequence with previous-hash and SHA-256 event hash.

The Git common directory stores `agent-work-v1/tasks`, `locks`, and `transactions`. This lets linked worktrees share one lease and registry while keeping absolute paths and token hashes out of Git.

## Owner lifecycle

```bash
WORKCTL="python3 <installed-skill-dir>/scripts/workctl.py"
$WORKCTL owner acquire <task-id> autopilot --expect-version 1 --ttl 1800
export WORKCTL_LEASE_TOKEN='<shown-once token>'
$WORKCTL owner check <task-id>
$WORKCTL owner heartbeat <task-id> --expect-version 2 --ttl 1800
$WORKCTL transition <task-id> planned --expect-version 3 --reason 'brief approved'
$WORKCTL owner handoff <task-id> pairroom --expect-version 4
$WORKCTL owner release <task-id> --expect-version 5
```

Use `--token-file` instead of an environment variable where process-environment inspection is a concern. `show` redacts token hashes. An expired lease is not silently stolen: use `owner recover` with the current version, then record why recovery was safe.

## State graph

The main path is `clarifying → planned → executing → verifying → done`. Active phases may enter `blocked` or `cancelled`. `blocked` may resume to an explicitly selected active phase. `verifying → executing` increments `verify_retry_count` and is rejected after `max_verify_retries`. A transition to `done` accepts only the latest deterministic verification event recorded after the most recent transition into `verifying`; an older pass cannot mask a later failure.

Every mutation performs compare-and-swap against `--expect-version`. Exit `10` signals a stale version or ownership conflict; reread state rather than retrying blindly.

## Evidence

```bash
$WORKCTL evidence <task-id> --expect-version 5 --kind test \
  --payload '{"command":"python -m unittest","exit_code":0,"commit":"<sha>"}'
$WORKCTL verify <task-id>
```

Payloads must be JSON objects. Keys that look like passwords, credentials, secrets, or tokens are rejected recursively. Store durable evidence, not full hidden reasoning or private transcripts.

## Exit classes

- `0`: success.
- `2–3`: usage or invalid data/schema.
- `10`: compare-and-swap or ownership conflict.
- `11`: missing, invalid, active, or expired lease.
- `12`: invalid state transition or retry exhaustion.
- `13`: workspace isolation or cleanup failure.
- `14`: task, evidence, lease, or workspace integrity failure.
