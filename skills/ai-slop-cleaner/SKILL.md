---
name: ai-slop-cleaner
description: "Use for requested behavior-preserving cleanup of duplication, dead code, needless abstraction, or boundary leaks. Not for an unrelated redesign or merely because code was AI-generated."
---

# ai-slop-cleaner

Simplify the authorized scope while preserving intended behavior. Prefer deletion and reuse where they reduce overall complexity.

Establish the behavior to preserve and a focused verification baseline. Reuse applicable observed checks or run a meaningful verifier; an alternative to automated tests should adequately exercise the affected behavior.

Remove demonstrated duplication, dead code, unnecessary abstractions, and masking fallbacks in coherent slices. Judge code by its behavior and maintenance cost rather than its origin.

Verify behavior-risk boundaries and the integrated result. Rerun invalidated checks and required project gates. Preserve legitimate failures and error handling; a smaller diff is not evidence of unchanged behavior.

For review-only requests, report findings without editing. Obtain authority for behavior changes outside the cleanup scope. Report simplifications, observed verification, and residual risk to the delivery owner, distinguishing self-checks from independent review.

## References

- [Cleanup safety](references/cleanup-safety.md): evaluating abstraction, fallback, and test-seam removal.
