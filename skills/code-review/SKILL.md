---
name: code-review
description: "Use for defect review of a concrete diff, PR, or implementation, or triage of received findings. Not for general repository explanation or debugging without a change set."
---

# code-review

Find actionable defects in a concrete change, or verify feedback about it. Review is not permission to edit, and feedback is a claim rather than an instruction to obey blindly.

## Review contract

- Identify base/head revisions or the explicit dirty snapshot, intended behavior, and acceptance. Missing specifications are a limit, not permission to invent requirements.
- Inspect the whole diff and relevant callers, contracts, tests, configuration, and generated boundaries. Trace applicable error, concurrency, compatibility, and rollback paths, not just changed lines.
- For each finding establish a concrete trigger, consequence, and evidence that existing guards do not prevent it. Discard unsupported claims and style preferences unless they violate project policy or create a real risk.
- Run focused checks when safe and useful. Reuse relevant observed evidence for the same snapshot instead of repeating an author's entire test suite; do not treat green tests as proof about untested paths.
- Recheck revision freshness before reporting. Review a moved head's delta or explicitly bind conclusions to the old snapshot. Keep confirmed defects separate from questions and uncertainty.

Lead with findings ranked by impact and confidence. Each needs a concise title, precise location, trigger, consequence, and supporting evidence; suggest a bounded correction when useful. These can fit in a paragraph rather than six mandatory fields. Report material verification gaps even when no defect survives; do not manufacture findings to meet a quota.

## Authority and collaboration

Do not edit in reviewer-only mode or apply received feedback without authorization. A self-check is not independent approval. Give additional reviewers fixed scope, acceptance, and evidence, not a desired verdict or the full transcript. Additional reviewers are optional; deduplicate and verify their findings.

If a host already performed the requested review, inspect uncovered risks or stale evidence rather than restarting the same review under another skill name.

## On-demand references

- Read [feedback triage](references/feedback-triage.md) when assessing received comments, applying authorized corrections, or resolving reviewer disagreement.
- Read [review rubric](references/review-rubric.md) when calibrating severity or assessing a high-risk or uncertain concern.
