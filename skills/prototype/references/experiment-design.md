# Experiment design

Read this only when choosing the experiment seam, deciding what may be faked, or interpreting an inconclusive prototype.

## Seam selection

Exercise the narrowest boundary whose behavior determines the decision. Keep upstream/downstream pieces fake only when their behavior is already known and the fake cannot manufacture the desired result.

## Oracle

Define an observable signal independent of the implementation under test: protocol response, persisted state, external side effect in a sandbox, performance measurement, or user interaction outcome. Logging produced by the same untrusted path is supporting evidence, not the sole oracle.

## Inconclusive results

A result is inconclusive when the environment, fake fidelity, sample size, instrumentation, or uncontrolled variable can explain both success and failure. Name the confounder and propose the smallest revised experiment rather than claiming partial confirmation.

## Promotion boundary

Before retaining prototype code, reassess ownership, error handling, security, compatibility, tests, operability, migration, and maintenance. Promotion is a new implementation decision, not a default continuation.
