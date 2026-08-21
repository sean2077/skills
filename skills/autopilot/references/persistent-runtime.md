# Persistent runtime

Read this only when autopilot needs durable workflow state for resume, handoff, revision/binding ownership, bounded retry, or formal receipts.

The generated script targets Python 3.8+, uses only the standard library, and owns phase, revision, workspace binding, plan-path validation, retry count, and terminal state. The Agent still owns judgment, implementation, tool use, and verification.

## Invoke and select a run

Use the quoted installed path so directories containing spaces work:

```bash
python3 "<installed-skill-dir>/scripts/autopilot_state.py" status
python3 "<installed-skill-dir>/scripts/autopilot_state.py" start --goal "<one-line goal>"
```

Use `python` when that is the host's Python 3 command, or `py -3` on Windows. Exit `3` from `status` means the selected run does not exist.

Use `--id` only for parallel runs. Host session variables isolate runs automatically; use `--session`, bounded `list --all-sessions --limit 20`, or `status --latest` only for explicit discovery. Default responses are compact; add `--full` or bounded `history --tail <1..20>` only for diagnosis.

## Runtime flow

1. Start only after persistent state is justified. Every later mutation uses the latest `--expected-revision`.
2. Complete clarification, then `advance --to plan`.
3. Write a proportional plan and register it with `plan --path <existing-file>`. The runtime rejects missing, escaping, symlink-traversing, or non-file paths before entering implementation.
4. Implement small slices, then `advance --to verify`.
5. Execute the real verifier yourself and record only the actually observed result with `verify --exit-code <0..255> --summary <text>`.
6. Exit `0` enters delivery. The first failed verification returns to implementation; the second enters terminal **blocked**. Never reinterpret blocked as delivery.
7. Report changes and evidence, then run `finish` to enter terminal **done**.

A read-only status may report `binding.ok=false`; do not mutate until ownership is resolved or explicitly rebound. Never edit state JSON or invent a revision.

## Coordination and side effects

Inside a `work-protocol` task, mutate only while holding its explicit autopilot owner lease; never acquire or start a nested loop owner. Use PairRoom for an independent peer rather than recreating a relay protocol here.

The runtime does not authorize merge, push, deployment, publication, or any other external side effect. Stop on terminal state, unsafe path, revision or binding conflict, user interruption, or unresolved authority.
