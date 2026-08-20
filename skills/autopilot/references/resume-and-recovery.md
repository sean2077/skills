# Resume and recovery

Read this only when an autopilot run is interrupted or reports a revision conflict, worktree/branch mismatch, blocked state, or lock error.

## State location and ownership

The runtime stores state under the repository-shared `.agent-workflows/autopilot/<id>.json`, derived from Git's common directory. The file is bound to one worktree and branch even though linked worktrees can discover it.

A mismatch is evidence of a different owner, not permission to take over. Inspect the recorded owner and active processes. Rebind only with the latest reported revision and an explicit decision that continuation in the current worktree is intended:

```bash
$AUTOPILOT rebind --id <slug> --expected-revision <n>
```

## Revision conflict

Reload status, reconcile what changed, and retry from the new revision. Never overwrite a newer state or decrement the revision.

## Lock failure

The lock is command-scoped. First confirm no command is running. If a process crashed and left `<id>.json.lock`, inspect its JSON owner record before removing only that exact lock. Never delete the workflow directory broadly.

## Blocked terminal state

`blocked` records a second failed verification and its summary. Report the evidence and propose a materially different strategy. Start a new run only when the user authorizes a fresh budget; do not mutate blocked back to implement.

The `.bak` file is a single-generation recovery aid. Restore it only after preserving the corrupt primary and validating workflow, id, schema, and revision.
