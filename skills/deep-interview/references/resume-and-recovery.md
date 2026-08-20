# Resume and recovery

Read this only when an interview is interrupted or reports a revision conflict, binding mismatch, lock error, or corrupt state.

State lives at `.agent-workflows/deep-interview/<id>.json` under the Git common repository root. It is visible across linked worktrees but bound to one worktree and branch.

On revision conflict, reload status and reconcile the newer topology/round before retrying. On binding mismatch, do not continue until ownership is resolved; then use `rebind --expected-revision <n>` explicitly.

A command-scoped `.lock` file means another mutation may be active. Confirm no process is running before removing only the exact stale lock after inspecting its owner record.

The `.bak` file is a single-generation recovery copy. Preserve a corrupt primary before restoring it, and verify schema, workflow, id, dimensions, phase, and monotonically increasing revision.
