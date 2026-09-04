# Persistent runtime

Read this only when deep-interview needs deterministic topology/scoring, cross-session resume, revision ownership, formal audit, or an approval digest.

The generated script targets Python 3.8+, uses only the standard library, and owns schema validation, topology, component × dimension scoring, ambiguity math, weakest-target rotation, ontology/challenge guards, revisions, binding, crystallization, approval digest, and completion state. The Agent still owns questions, evidence gathering, and rubric judgment.

## Invoke and select a run

Use the quoted installed path:

```bash
python3 "<installed-skill-dir>/scripts/interview_state.py" status
python3 "<installed-skill-dir>/scripts/interview_state.py" start \
  --idea "<one-line summary>" --depth deep --type greenfield
```

Use `python` when that is the host's Python 3 command, or `py -3` on Windows. Exit `3` from `status` means the selected run does not exist. `--depth` sets the ambiguity gate (`quick` 0.30, `standard` 0.20, `deep` 0.10); `--threshold <0..1>` overrides it explicitly.

Use `brownfield` for an existing system. Use `--id` only for parallel runs and bounded `list --all-sessions --limit 20`, `--latest`, `--full`, or `history --tail <1..20>` only when discovery or diagnosis requires them.

## Topology and scoring loop

1. Identify one to six top-level components whose outcomes can succeed or fail independently. Confirm the topology once and submit it with the latest `--expected-revision`; every deferred component needs a reason.
2. Follow the runtime's current weakest component × dimension. Inspect safe facts yourself and spend user turns on judgments that can change scope, acceptance, rollback, ownership, or handoff.
3. In this mode only, ask at most one decision-bearing user question per scoring round and preserve answer provenance.
4. Submit every required active dimension in one contiguous round. Never hand-calculate ambiguity, omit an active dimension, score a deferred component, or silently choose another target.
5. Obey `metrics.cadence_user_required`, challenge suggestions, stall escalation, score thresholds, and the runtime's round cap. Waive remaining ambiguity only with explicit user acceptance and preserved risks.

## Crystallization and approval

After `gate` passes or an authorized waiver exists, write the full specification marked `pending approval` and run `crystallize --spec-path <existing-file> --expected-revision <n>`.

Ask the user to review the crystallized specification. Only explicit approval may be recorded with `approve --evidence <text>`. Run `complete` only from the separately approved state and only while the spec digest is unchanged. Completion does not authorize implementation.

Never edit state JSON, invent evidence or revisions, or treat a numeric gate as authority over an unresolved blocker. Apply the stop conditions in the SKILL.md hard rules.
