# Composition and handoff

## Use specialists at the decision boundary

Choose help for a concrete bottleneck: causal investigation, external evidence, a feasibility experiment, unresolved requirements, test-first implementation, cleanup, or review. Reuse settled decisions and an adequate existing workflow.

Delegate independent investigations or disjoint implementation surfaces when the benefit exceeds coordination cost. Provide the objective, allowed effects, checkout and revision, owned surface, acceptance, and relevant evidence. Keep one integration owner and one active writer for a mutable surface.

Match capability to risk: ambiguous architecture or high-impact review may warrant stronger reasoning; bounded work with deterministic checks may use a lighter executor. With one worker, perform the needed steps serially and distinguish self-review from independent review.

## Integrate and verify

Inspect returned changes and findings against current code and acceptance. Check cross-component contracts, shared configuration, generated outputs, and error handling that isolated work may miss. Validate and deduplicate feedback by mechanism rather than reviewer count.

For an iterative audit, track unresolved material findings and repeat targeted review after corrections. Conclude when current verification and the final integrated review leave no actionable finding in the inspected scope. Report meaningful coverage limits.

## Handoff and resume

An unfinished handoff should identify the objective and authority, checkout and revision, completed work, observed checks, unresolved issues, and next action. Preserve durable state or receipts where the active workflow requires them.

On resumption, compare the current checkout with the recorded revision and reconcile any concurrent work. Reuse evidence that remains applicable, rerun invalidated checks, and transfer ownership through the active protocol before another writer continues.
