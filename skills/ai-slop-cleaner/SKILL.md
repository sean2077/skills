---
name: ai-slop-cleaner
description: Use when behaviorally correct code needs bounded simplification of duplication, dead code, needless abstraction, boundary leaks, or weak coverage without changing intended behavior.
---

# ai-slop-cleaner

Simplify noisy or over-produced code without changing intended behavior. Work deletion-first, protect behavior before editing, and keep each pass bounded to one smell class.

## Workflow

1. Define the requested scope and the behavior that must remain unchanged.
2. Establish a focused behavior lock: run or add the narrowest meaningful regression test before cleanup. When no automated seam exists, record the exact alternative verifier and why.
3. Inventory concrete smells: duplication, dead code, needless abstraction, boundary leakage, masking fallback, weak tests, or naming/error-handling noise.
4. Order work from safest deletion to riskier consolidation. Do not bundle unrelated redesign.
5. Apply one smell-focused pass, then run the relevant verifier before starting another pass.
6. Run touched-area tests, lint, type checks, and existing static/security checks that apply.
7. Report changed files, deleted or consolidated behavior, commands and observed results, and remaining risks.

## Completion gate

The pass is complete only when a verifier actually run over the touched behavior is green, or the user explicitly accepts a documented no-test rationale. “Looks cleaner” is not evidence.

## Reviewer-only mode

When asked only to review a cleanup, do not edit. Check preserved behavior, deletion safety, leftover duplication/dead code, boundary drift, and test strength. A high-impact cleanup must not be both authored and independently approved by the same pass.

## Hard rules

- Preserve behavior unless the user explicitly authorizes a behavior change.
- Prefer deletion and reuse over new dependencies or speculative abstraction.
- A simplification that moves complexity into many callers is not a simplification.
- Never swallow errors or introduce catch-all defaults merely to make tests pass.
- When run inside an iterative workflow, report the observed verifier result to that workflow; do not start a nested cleanup loop.

## On-demand references

- Read [cleanup safety](references/cleanup-safety.md) only when deciding whether an abstraction, fallback, or test seam can be removed safely.
