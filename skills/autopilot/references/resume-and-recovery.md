# Resume and recovery

Read this only when an autopilot run is interrupted or reports discovery, binding, revision, lock, or state-health trouble.

## Locate the run

State is stored at `.agent-workflows/autopilot/<session>/<id>.json`. In Git repositories the root is shared through Git's common directory, so linked worktrees can discover the same run while mutations remain bound to one worktree and branch. Outside Git, pass a stable `--root <directory>` from every invocation.

Use read-only discovery before touching files:

```bash
python3 "<installed-skill-dir>/scripts/autopilot_state.py" list --all-sessions --limit 20
python3 "<installed-skill-dir>/scripts/autopilot_state.py" status --session <session> --latest
python3 "<installed-skill-dir>/scripts/autopilot_state.py" history --id <slug> --tail 5
```

`status`, `list`, `history`, and `doctor` do not create a missing state tree. Add `--full` only when compact fields are insufficient.

## Resolve ownership and concurrency

A revision conflict means another mutation won. Reload status, reconcile its result, and retry from the new revision. A binding mismatch means another worktree or branch owns the run. Confirm that owner is inactive, then transfer deliberately:

```bash
python3 "<installed-skill-dir>/scripts/autopilot_state.py" rebind --id <slug> --expected-revision <n>
```

Never decrement a revision or copy state between session directories.

## Diagnose and recover

Run `doctor --id <slug>` first. It validates the primary, backup, and lock without printing full history.

- For a corrupt primary with a valid single-generation backup, run `recover --id <slug>`. Recovery preserves monotonic revision. Use `--force` only for an intentional rollback from a valid primary; add `--rebind` only to explicitly transfer a restored run after confirming the prior owner is inactive.
- For a lock, verify its recorded process is no longer alive, then run `unlock --id <slug> --stale-after <seconds>`. Use `--force` only after an explicit local safety decision.
- Do not hand-edit, delete, or broadly move `.agent-workflows` files.

`blocked`, `done`, and `aborted` are terminal. Report their evidence; start a new run only with a new authorized budget.

## Response and exit contract

Every command emits one `agent-workflow-response/2` JSON object. Exit `0` means the command or read succeeded; `2` means invalid input; `3` means no selected run; `4` means a gate or terminal refusal; `5` means a revision, lock, binding, or transition conflict; `6` means unsafe or corrupt state; `70` means an unexpected internal failure. Do not infer workflow completion from the process code alone; read `terminal`, `status`, and `stage`.
