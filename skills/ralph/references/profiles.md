# Ralph profiles

Read this only when the loop is explicitly optimizing research quality or adversarial end-to-end safety rather than a normal implementation verifier.

## Research profile

Define a scored evidence rubric before starting: primary-source coverage, claim support, source freshness, disagreement handling, repository applicability, and unresolved uncertainty. Use `score-improvement`; each round must add or correct evidence, not merely rewrite prose. The verifier exit is zero only when the required evidence bar and deliverable checks pass.

## Adversarial QA profile

Design a scenario matrix before the first round. Select applicable axes: malformed/hostile input, lifecycle interruption, boundaries, stale/partial state, permissions, network failure, concurrency, authorization, tenant isolation, and misleading success. Each scenario states setup, action, and expected safe behavior.

Use a stable failing scenario as the signature. For large matrices, score the fraction of scenarios with observed safe behavior. Expand the matrix when a defect reveals a missed axis, but keep probes bounded, non-destructive, sandboxed, and free of secret-exfiltration behavior.

A profile changes the work and verifier, not the runtime engine or stop semantics.
