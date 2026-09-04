---
name: code-review
description: Use when a change set, pull request, patch, or implementation needs an evidence-based defect review focused on correctness, regressions, security, maintainability, and verification gaps. Not for read-only explanation or causal investigation without a change set; use analyze.
---

# code-review

Review a concrete change set for defects and risks. Lead with actionable findings; do not summarize the diff before establishing whether it is safe.

## Workflow

1. Identify the review base, intended behavior, scope, and acceptance criteria.
2. Inspect the full diff plus relevant callers, contracts, tests, configuration, migrations, and generated boundaries.
3. Trace changed behavior through normal, error, boundary, concurrency, compatibility, and rollback paths that apply.
4. Compare implementation claims with executable evidence. Run focused read-only checks when safe and available.
5. For every candidate finding, prove the triggering condition, affected behavior, and why existing guards/tests do not prevent it.
6. Rank only actionable findings by impact and confidence; discard style preferences that are not project policy or risk.
7. End with residual risks and verification gaps. State explicitly when no findings survive review.

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
- Do not edit in reviewer-only mode. An author pass is not an independent approval.
- Treat tests as evidence, not proof that untested paths are safe.

## On-demand references

- Read [review rubric](references/review-rubric.md) only when calibrating severity, checking a high-risk boundary, or deciding whether a concern is actionable.
