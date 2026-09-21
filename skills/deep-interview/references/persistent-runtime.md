# Specification approval runtime

Use this Python 3.8+ standard-library runtime when approval needs a repository-owned, recoverable record. It tracks the specification, revision, workspace binding, and approval digest. The interview and document format remain caller-owned.

```bash
python3 "<installed-skill-dir>/scripts/interview_state.py" start --idea "<goal>"
python3 "<installed-skill-dir>/scripts/interview_state.py" crystallize --spec-path "docs/spec.md" --expected-revision 1
# Present that exact specification and obtain approval before recording it.
python3 "<installed-skill-dir>/scripts/interview_state.py" approve --evidence "<actual approval>" --expected-revision 2
python3 "<installed-skill-dir>/scripts/interview_state.py" complete --expected-revision 3
```

Use `python` or `py -3` where appropriate. Add `--id <slug>` to each command for a named run. Use the revision returned by the preceding command rather than assuming the example's numbers still apply.

`crystallize` accepts a nonempty UTF-8 file up to 1 MiB within the bound workspace, rejecting symlink traversal. It records SHA-256 over the original file bytes, including line endings. The runtime accepts the project's headings and organization.

The lifecycle is `drafting → crystallized → approved → completed`; `abort --reason <text>` terminates an active run. Before completion, crystallizing a revision clears previous approval. Both `approve` and `complete` reread the file and reject any byte change. Re-crystallize and obtain fresh approval after an edit, including formatting or LF/CRLF changes.

Only record observed user approval of the presented specification. An answer to one interview question approves that decision, not an unseen specification. The runtime checks digest and state consistency, not whether an Agent truthfully represented the user's decision. Specification approval does not independently authorize implementation or external effects.

Every mutation uses the latest `--expected-revision`; completed and aborted runs cannot be reopened. State is managed through the CLI rather than hand-edited. See [resume and recovery](resume-and-recovery.md) for conflicts and interrupted sessions.

## Existing installations

This runtime uses `agent-workflow/deep-interview/3`. The former scoring runtime's `/2` states and commands are not converted or overwritten. Finish or inspect an existing run with its original installed version; start a new ID and obtain fresh approval when moving to this runtime. Scoring, topology, ontology, numeric gates, waivers, and fixed question cadence are no longer runtime requirements.
