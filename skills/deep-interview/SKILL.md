---
name: deep-interview
description: Use when an idea is vague and needs thorough clarification before implementation, or the user asks to be interviewed without unstated assumptions.
---

# deep-interview

Run a Socratic interview that turns a vague idea into an approval-ready specification. The agent owns questions, evidence, and rubric judgments; the bundled runtime owns schema validation, ambiguity math, weakest-target rotation, revisions, binding, and completion gates.

Set `INTERVIEW="python <skill-dir>/scripts/interview_state.py"` using this installed skill directory.

## Start or resume

Probe with `$INTERVIEW status --id <slug>`. Exit `3` means no run. Start with:

```bash
$INTERVIEW start --id <slug> --idea "<one-line summary>" --depth deep --type greenfield
```

Use `--type brownfield` when modifying an existing system. Thresholds are quick `0.30`, standard `0.20`, and deep `0.10`; an explicit `--threshold` overrides the depth default.

## Topology round

Before scoring, propose one to six top-level outcomes that can succeed or fail independently. Ask one confirmation question, then submit the confirmed topology with `topology --input <json>`. Deferred components are excluded from scoring and cannot be scored later.

## Interview loop

1. Read status and use its `next_target` and `revision`.
2. Decide whether the missing information is discoverable fact or user judgment. Inspect code/docs yourself for facts; ask the user one decision-bearing question per round.
3. Score every required dimension for every active component against observed evidence and submit one round with `score --input <json> --expected-revision <n>`. Deferred components are never included.
4. Repeat from the runtime-reported weakest target. Never compute ambiguity or choose a different target silently.
5. When `gate_passed` is true, write the full spec marked `pending approval`, then record it with `complete --spec-path <path>`.

The score payload schema, dimensions, formula, and examples live in the reference below. Keep question and answer evidence in the payload; scores without evidence are invalid.

## Spec output

Include confirmed topology and deferrals, users and problem, scope/non-goals, behavior and flows, constraints, brownfield context when applicable, acceptance scenarios, risks, decisions, unresolved items, and an explicit `pending approval` marker. Completion does not authorize implementation.

## Hard rules

- Ask one user question per round; discover repository facts yourself when safe.
- Never hand-calculate ambiguity, revise state JSON, or reuse a stale revision.
- Score every active component on every required dimension; do not score deferred components or omit required dimensions.
- A passed numeric gate does not erase an explicit unresolved blocker.
- Stop on user exit, binding mismatch, revision conflict, or invalid evidence; preserve the run for exact resume.

## On-demand references

- Read [scoring and payloads](references/scoring-and-payloads.md) before submitting topology or score JSON, and again only when validation rejects a payload.
- Read [resume and recovery](references/resume-and-recovery.md) only when the run is interrupted, mismatched, locked, or needs an explicit rebind.
