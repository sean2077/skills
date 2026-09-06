# Feedback triage

Read this only when review comments arrive or reviewers disagree. Use the existing concrete change, acceptance, and review revision; do not create another orchestration workflow.

## Verify before agreeing or changing

Read each material claim and inspect its referenced code at the current revision. Reproduce the triggering condition or trace a concrete counterexample. A confident reviewer, passing tests, or consensus alone does not settle the claim. Check whether it is already fixed, contradicted by a guard, based on an obsolete diff, or outside the requested contract.

Assign a compact disposition only where useful:

- **Accept:** a supported, in-scope defect. Apply a bounded correction only with authoring authority; otherwise return the finding.
- **Challenge:** show the existing guard, counterexample, or contract that makes the proposed change incorrect. Technical disagreement needs evidence, not defensive language or performative agreement.
- **Needs evidence:** name the unresolved trigger, assumption, or requirement and the cheapest discriminating check. Ask a human only for genuinely user-owned intent that repository evidence cannot settle.
- **Defer:** a legitimate issue outside this change, with its impact and reason. Do not silently expand scope to redesign unrelated code.

Group duplicates by root cause and affected behavior, not by wording. Resolve reviewer disagreement using the contract and evidence; do not average severities or count votes. Preserve a new independent concern even when it resembles an already-dismissed comment.

## Apply and close with current evidence

Prioritize impact and dependencies. Preserve unrelated work, add a regression where it can establish the failure, make the smallest coherent correction, and rerun the affected checks. Do not weaken an oracle just to satisfy a comment or obtain green tests.

Return the disposition, changed path/revision, and observed verification to the integration owner. Review the changed seam again after a fix; review freshness follows the new snapshot, not an earlier approval label. Keep unverifiable findings and blocked checks visible. A reply, a local commit, or a self-review is not independent approval or proof that a remote review thread was resolved.
