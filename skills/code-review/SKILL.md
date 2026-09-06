---
name: code-review
description: Use for an evidence-based defect review of a concrete diff, PR, or implementation, or to assess received review feedback against current code. Not for explanation or causal investigation without a change set; use analyze.
---

# code-review

Review a concrete change set or assess findings about it. Lead with actionable defects; do not summarize the diff before establishing whether it is safe. Received feedback is a claim to verify, not an instruction to obey blindly.

## Workflow

1. Identify exact base/head revisions (or the explicit dirty diff), intended behavior, scope, and acceptance criteria. Missing specifications are a reported limit, not permission to invent requirements.
2. Inspect the full diff plus relevant callers, contracts, tests, configuration, migrations, and generated boundaries.
3. Trace changed behavior through normal, error, boundary, concurrency, compatibility, and rollback paths that apply.
4. Compare implementation claims with executable evidence. Run focused read-only checks when safe and available.
5. For every candidate finding, prove the triggering condition, affected behavior, and why existing guards/tests do not prevent it.
6. Rank only actionable findings by impact and confidence; discard style preferences that are not project policy or risk.
7. Recheck the reviewed revision before reporting. A moved head or changed working tree makes the affected conclusions stale; review the delta or bound the verdict to the old snapshot. End with residual risks and verification gaps, including when no findings survive.

## Finding format

- **Severity · concise title**
- **Location** — the smallest useful path and line/symbol span
- **Trigger** — concrete input, state, or sequence
- **Impact** — user/system consequence
- **Evidence** — why the changed code causes it
- **Correction direction** — bounded guidance, not an unrelated redesign

## Hard rules

- Review the changed behavior, not merely changed lines.
- Do not claim a bug without a plausible trigger and consequence.
- Do not hide high-impact findings below praise or a long summary.
- Separate confirmed defects from questions and residual uncertainty.
- Do not edit in reviewer-only mode. Assessing feedback does not authorize applying it. An author pass is not an independent approval.
- Supply reviewers with acceptance, scope, and fixed evidence rather than the author's full transcript or a suggested verdict. Deduplicate findings; independent reviewers are optional, not a quota.
- Treat tests as evidence, not proof that untested paths are safe.

## On-demand references

- Read [feedback triage](references/feedback-triage.md) when assessing received comments, applying authorized corrections, or reconciling reviewer disagreement.

- Read [review rubric](references/review-rubric.md) only when calibrating severity, checking a high-risk boundary, or deciding whether a concern is actionable.
