---
name: work-protocol
description: 'Use when a task needs repository-owned coordination state: one loop owner, isolated writers, commit-fixed review, or evidence-backed high-risk delivery. Not for native goals or temporary subagents unless durable lease, CAS, evidence, or workspace state is required.'
---

# work-protocol

Use only when coordination state must survive. The Python 3.8+ standard-library runtime owns CAS state, one expiring loop-owner lease, hash-chained evidence, and Git worktree isolation; native Agent loops still own reasoning and tools. Task length, native subagents, or a durable goal alone do not trigger it.

Invoke the quoted installed path:

```bash
python3 "<installed-skill-dir>/scripts/workctl.py" risk --cross-session
python3 "<installed-skill-dir>/scripts/workctl.py" init <task-id> --title "<goal>"
```

Use `python` when that is the host's Python 3 command, or `py -3` on Windows.

## Task spine

1. Use `risk` first. Skip the protocol for a low-risk task with one writer and clear acceptance.
2. `init` creates `.agents/work/<task-id>/brief.md`, `plan.md`, `state.json`, and `evidence.jsonl` in one authoritative worktree.
3. Acquire exactly one loop owner: `native`, `autopilot`, `ralph`, `pairroom`, or `custom:<slug>`. Pass the returned token through a protected environment variable or file; use `owner check` before owned actions and `owner heartbeat` only with the current state version.
4. Every mutation supplies `--expect-version`; stale writers fail instead of overwriting newer state.
5. Follow `clarifying → planned → executing → verifying → done`. A bounded verify retry may return to executing; `done` requires the latest deterministic verification event in the current verifying cycle to pass. Explicit `blocked` (resumable) and `cancelled` (terminal) states remain visible.
6. Append commands, exit codes, commits, approvals, and review verdicts as evidence. Never write secrets into committed artifacts.
7. Run `verify` before handoff or delivery, then release or hand off the owner explicitly.

## Workspace boundary

Writable driver, worker, and integrator roles receive distinct new-branch worktrees pinned to a resolved base commit. Parallel writers claim conservative, non-overlapping path rules; committed, staged, unstaged, unmerged, and untracked changes are checked against those claims, and changed symlinks may not escape. One task has at most one integrator. Reviewers require an exact full commit SHA and receive a clean detached snapshot. Reviewer evidence is appended through the authoritative task, not written into the snapshot.

## Hard rules

- Do not edit `state.json`, the machine-local registry, lease, transaction journal, or evidence hashes manually.
- Do not start a second orchestration loop while another valid owner lease exists.
- Do not let two writers share one writable worktree.
- Do not remove a dirty, unmerged, moved, foreign, or active workspace without an explicit recorded force reason.
- Machine-local token hashes, leases, locks, authority paths, and worktree paths stay under the Git common directory, never in committed task artifacts.

## On-demand references

- Read [task state and evidence](references/task-state-and-evidence.md) only when creating, resuming, handing off, recovering, or verifying a durable task.
- Read [workspace isolation](references/workspace-isolation.md) only when adding writers, reviewers, path claims, integration, cleanup, or stale-worktree recovery.
