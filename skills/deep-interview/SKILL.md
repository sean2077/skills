---
name: deep-interview
description: Use when an idea is vague and needs thorough clarification before implementation, or the user asks to be interviewed without unstated assumptions.
---

# deep-interview

Run a topology-aware Socratic interview that turns a vague idea into an explicitly approved specification. The agent owns questions, evidence gathering, and rubric judgment; the bundled standard-library runtime owns schema validation, component × dimension scoring, ambiguity math, weakest-target rotation, ontology stability, challenge/stall guards, revisions, binding, and completion gates.

Invoke the quoted script path directly:

```bash
python3 "<installed-skill-dir>/scripts/interview_state.py" status
```

Use `python` when that is the host's Python 3 command, or `py -3` on Windows. Python 3.8+ is required; no third-party package is required.

## Start or resume

Exit `3` from `status` means the default run does not exist:

```bash
python3 "<installed-skill-dir>/scripts/interview_state.py" start \
  --idea "<one-line summary>" --depth deep --type greenfield
```

Use `brownfield` when changing an existing system. Depth thresholds are quick `0.30`, standard `0.20`, and deep `0.10`; `--threshold 0..1` overrides the depth default. Use `--id` for parallel runs and explicit `--session`, `list --all-sessions --limit 20`, or `--latest` for discovery. Default output is compact; use `--full` and bounded `history --tail <1..20>` only when needed.

## Topology round

Before normal scoring, identify one to six top-level components whose outcomes can succeed or fail independently. Confirm the proposed topology once, then submit `topology --input <json> --expected-revision <n>`. Every deferred component needs an explicit reason and is excluded from all later scores.

## Interview loop

1. Read the runtime's `metrics.weakest` component × dimension and latest revision.
2. Decide whether the gap is a discoverable fact or a user-owned judgment. Inspect safe code/docs/research yourself for facts. Spend a user turn only when the answer can change scope boundary, acceptance criterion, rollback contract, lane assignment, or handoff target.
3. Ask at most one decision-bearing user question in a round. Offer 2–4 concrete choices plus free text; mark exactly one Recommended only when inspected evidence supports it, otherwise say No reliable default.
4. Preserve answer provenance using `[from-user]`, `[from-code]`, `[from-research]`, or `[from-prototype]`. After two consecutive rounds without `[from-user]`, the next round must include a user-owned decision; the runtime enforces this cadence guard.
5. Score every required dimension for every active component and submit one contiguous round with `score --input <json> --expected-revision <n>`.
6. Follow the next weakest target. Never hand-calculate ambiguity or silently choose another target.
7. Obey challenge suggestions. A three-round ambiguity stall requires the ontologist stance; the runtime allows that stance to recur while the stall persists.
8. At round 10 reassess whether remaining questions are decision-bearing. Round 20 is a hard scoring cap: explicitly waive remaining ambiguity or abort.

## Gate, crystallization, and approval

Run `gate` after scoring. Exit `0` means the numeric gate passed or an explicit waiver already exists; exit `4` means it has not.

- When ambiguity is acceptable, write a full specification marked `pending approval` and run `crystallize --spec-path <existing-file> --expected-revision <n>`.
- When the numeric gate cannot be met within the authorized time-box, record the user's explicit acceptance with `waive --reason <text>`; the spec must then preserve a non-empty Remaining Gaps/Risks section.
- Ask the user to review the crystallized digest. Only after explicit approval run `approve --evidence <text>`.
- Run `complete` only from the separately approved state and only while the spec digest is unchanged. Completion does not authorize implementation.

The content gate requires Goal, Topology, Constraints, Non-goals, Decision Boundaries with owner and revisit trigger, Acceptance Criteria, Ontology, and Open Assumptions. At least one earlier answer must have a recorded pressure pass before crystallization.

## Hard rules

- Ask one user question per round; discover safe repository facts yourself.
- Never edit state JSON, invent evidence, omit an active component/dimension, or reuse a stale revision.
- Never score a deferred component.
- A numeric gate does not erase an explicit unresolved blocker or decision boundary.
- Preserve user approval as a separate event; changed spec content invalidates the old approval digest. Casual acknowledgements such as “yes”, “ok”, or “proceed” answer the current question and never count as spec approval unless the user explicitly approves the crystallized specification.
- Stop on user exit, terminal state, binding/revision conflict, unsafe path, invalid evidence, or unresolved authority.

## On-demand references

- Read [scoring and payloads](references/scoring-and-payloads.md) before the topology/first score, when challenge/ontology behavior matters, or after payload rejection.
- Read [resume and recovery](references/resume-and-recovery.md) only for discovery, interruption, mismatch, conflict, lock, corruption, or non-Git root handling.
