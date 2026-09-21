---
name: code-review
description: "Use for defect review of a concrete diff, PR, or implementation, or triage of received findings. Not for general repository explanation or debugging without a change set; use analyze."
---

# code-review

Find actionable defects in a concrete change and verify received feedback against the code.

## Review

Identify the base/head revisions or dirty snapshot, intended behavior, and acceptance. Treat missing requirements as uncertainty to resolve or disclose.

Inspect the whole diff and relevant callers, contracts, tests, configuration, and generated boundaries. Trace applicable error, concurrency, compatibility, and rollback paths.

For each finding, establish a trigger, consequence, and evidence that existing guards do not prevent it. Separate defects from questions and style preferences. Run safe, focused checks where useful, reusing applicable evidence while accounting for untested paths.

Check revision freshness before reporting. Review a moved head's delta or bind conclusions explicitly to the inspected snapshot.

Lead with confirmed findings ranked by impact and confidence. Give precise locations, triggers, consequences, and supporting evidence; include a bounded correction where useful. Report material verification gaps even when no defect is found.

## Collaboration

Review-only requests do not authorize edits. Validate received findings before applying authorized corrections. Additional reviewers need fixed scope, acceptance, and evidence; verify and deduplicate their findings. Distinguish self-checks from independent approval.

## References

- [Feedback triage](references/feedback-triage.md): received comments, authorized corrections, and reviewer disagreement.
- [Review rubric](references/review-rubric.md): severity and high-risk or uncertain concerns.
