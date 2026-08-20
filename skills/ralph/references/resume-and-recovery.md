# Resume and recovery

Read this only when a ralph run is interrupted or reports a pending round, revision conflict, worktree/branch mismatch, lock error, or corrupt state.

State is repository-shared at `.agent-workflows/ralph/<id>.json` and bound to one worktree and branch. A pending round means an attempt was opened but no result was recorded; inspect the working tree and verifier evidence, then submit that round exactly once or abort the run. Do not call `next` again.

On revision conflict, reload and reconcile the newer result. On ownership mismatch, confirm the old owner is inactive and use explicit `rebind --expected-revision <n>`.

A `.lock` file is command-scoped. Inspect its owner record and active processes before removing only a confirmed stale lock. Preserve a corrupt primary before restoring the single-generation `.bak`; validate schema, id, workflow, revision, and history first.
