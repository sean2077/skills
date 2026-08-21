# Resume and recovery

Read this only when an interview is interrupted or reports discovery, revision, binding, lock, or state-health trouble.

State is stored at `.agent-workflows/deep-interview/<session>/<id>.json`. Git worktrees share discovery through the common repository root while mutation ownership stays bound to one worktree and branch. Outside Git, invoke every command with the same `--root <directory>`.

Use read-only discovery first:

```bash
python3 "<installed-skill-dir>/scripts/interview_state.py" list --all-sessions --limit 20
python3 "<installed-skill-dir>/scripts/interview_state.py" status --session <session> --latest
python3 "<installed-skill-dir>/scripts/interview_state.py" history --id <slug> --tail 5
```

On revision conflict, reload and reconcile the winning topology/round. On binding mismatch, confirm the prior owner is inactive and use explicit `rebind --expected-revision <n>`.

Run `doctor` before recovery. Use `recover` only when the primary is corrupt and the reported single-generation backup is valid; `--force` is an intentional rollback. Recovery refuses a different worktree/branch unless `--rebind` explicitly transfers the restored owner after you confirm the prior owner is inactive. Use `unlock --stale-after <seconds>` only after confirming the recorded process is dead. Never hand-edit topology, scores, ontology, phase, revision, lock, or approval fields.

A pending scoring phase resumes from the runtime's current weakest target and next contiguous round. A crystallized run awaits approval; an approved run awaits unchanged-digest completion. `completed` and `aborted` are terminal.

## Response and exit contract

Every command emits one `agent-workflow-response/2` JSON object. Exit `0` means the command or read succeeded; `2` means invalid input; `3` means no selected run; `4` means a gate or terminal refusal; `5` means a revision, lock, binding, or transition conflict; `6` means unsafe or corrupt state; `70` means an unexpected internal failure. Do not infer workflow completion from the process code alone; read `terminal`, `status`, and `stage`.
