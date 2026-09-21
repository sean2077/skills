---
name: work-protocol
description: "Use when work needs durable ownership leases, CAS revisions, hash-chained evidence, or isolated writer/reviewer workspaces. Not for ordinary single-session work already covered by the host."
---

# work-protocol

Coordinate repository-owned state without prescribing a delivery workflow. This Python 3.8+ standard-library runtime provides leases, compare-and-swap revisions, evidence receipts, and Git worktree isolation.

```bash
python3 "<installed-skill-dir>/scripts/workctl.py" init <task-id> --title "<goal>"
python3 "<installed-skill-dir>/scripts/workctl.py" owner acquire <task-id> <owner-id> --expect-version 1
```

Use `python` or `py -3` where appropriate. Protect the returned lease token outside committed files; later mutations accept `--token-file` or `WORKCTL_LEASE_TOKEN` and require the current `--expect-version`. Check ownership before acting, renew a live lease as needed, and explicitly hand off or release it.

## State and evidence

`init` creates `state.json` and `evidence.jsonl` under `.agents/work/<task-id>/` in the authoritative checkout. Plans and briefs use the project's existing documents. Owner IDs and nonterminal phase labels are caller-chosen; `active` is the initial phase. The protocol imposes neither a stage sequence nor a retry count.

Append observed commands, outcomes, commits, approvals, and review findings as evidence. Large payloads can use `evidence --payload-file <json>`; the default result is a compact receipt, and `--full` returns the recorded event. Never invent verifier results or store secrets in evidence.

`done` and `cancelled` are terminal. `done` requires the latest verification event since the last phase change to pass and the registered workspaces to satisfy their isolation/scope checks. Contradictory or wrong-typed result fields cannot pass. Run `verify` at handoff to inspect the evidence chain, state, ownership, and workspaces; this checks records, not the truth of an unobserved command.

## Workspace ownership

Use `writer` workspaces for isolated new-branch edits and `reviewer` workspaces for clean snapshots at an exact commit. Multiple writers need non-overlapping path claims; integration responsibility stays with the caller rather than a special runtime role. Review snapshots receive no authoring authority.

Externally created worktrees keep their lifecycle owner unless control is explicitly transferred. The runtime manages only workspaces it creates and records. Preserve dirty, unmerged, foreign, or active work rather than forcing cleanup; a force operation needs an explicit reason and authorization.

State, registries, leases, transaction journals, and evidence hashes are CLI-managed. Machine-local paths, token hashes, and locks stay under the Git common directory. Resolve version, binding, or ownership conflicts before further mutations.

## References

- [Task state and evidence](references/task-state-and-evidence.md): phases, result validation, ownership, receipts, recovery, and existing installations.
- [Workspace isolation](references/workspace-isolation.md): writers, reviewers, path claims, integration, and cleanup.
