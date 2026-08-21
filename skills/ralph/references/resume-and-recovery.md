# Resume and recovery

Read this only when a ralph run is interrupted or reports a pending round, discovery problem, revision conflict, binding mismatch, lock, or corrupt state.

State is stored at `.agent-workflows/ralph/<session>/<id>.json`. Git worktrees share discovery through the common repository root but not mutation ownership. Outside Git, use the same explicit `--root <directory>` every time.

Use `list --all-sessions --limit 20`, `status --latest`, and `history --tail <n>` to locate bounded evidence. A pending round means an attempt was opened but no result was recorded: inspect the working tree and verifier evidence, then submit that exact round once or `abort`; never call `next` again.

On revision conflict, reload and reconcile the winning result. On binding mismatch, confirm the old owner is inactive and run `rebind --expected-revision <n>` from the intended owner.

Run `doctor` before recovery. Use `recover` only when the primary is corrupt and the reported backup is valid; `--force` is an explicit rollback. Recovery refuses another worktree or branch unless `--rebind` explicitly transfers the restored owner after you confirm the prior owner is inactive. Use `unlock --stale-after <seconds>` only after confirming the lock owner is dead. Never hand-edit state or lock JSON.

## Response and exit contract

Every command emits one `agent-workflow-response/2` JSON object. Exit `0` means the command or read succeeded; `2` means invalid input; `3` means no selected run; `4` means a gate or terminal refusal; `5` means a revision, lock, binding, or transition conflict; `6` means unsafe or corrupt state; `70` means an unexpected internal failure. Do not infer workflow completion from the process code alone; read `terminal`, `status`, and `stage`.
