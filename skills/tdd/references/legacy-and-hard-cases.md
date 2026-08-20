# Legacy and Hard Cases

Read this when working on a bug, legacy code, a repository without a test harness, generated code, concurrency, distributed behavior, migrations, compatibility, security, performance, visual output, property-based testing, data/ML systems, or embedded targets.

## Bug fixes

Reproduce the defect through the narrowest stable affected seam before changing production code. Minimize the case without removing the causal condition. Confirm the new test fails on the unpatched behavior and passes with the fix; where practical, temporarily reverse only the production fix to prove the regression test is sensitive. Preserve the minimized case after any broader property or fuzz test that discovered it.

## Legacy code and weak seams

Use a characterization test when current behavior must be understood or preserved before a safe change. Label whether the captured behavior is a compatibility contract, an observation pending product decision, or an existing defect; characterization is not automatic approval of every quirk.

When no stable seam exists, make the smallest behavior-preserving preparatory refactor while existing checks remain green, then begin the RED cycle. Prefer extracting a dependency, clock, parser, adapter, or pure decision over exposing private state solely for tests. If no trustworthy baseline exists, combine narrow observations, production evidence, specifications, and owner decisions rather than pretending the current output is an oracle.

## Repositories without a harness

First search project instructions, CI, build targets, examples, and sibling modules. If no supported harness exists, adding one changes dependencies, maintenance, and developer workflow. Choose the smallest project-consistent option, explain alternatives when they materially differ, and obtain the authority required for new dependencies or services. For a mechanical or generated change with no stable behavior to drive, use the authoritative verifier instead. Do not manufacture a low-value test solely to claim TDD.

## Concurrency and distributed systems

Control clocks, schedulers, barriers, executors, message delivery, and fault injection where the architecture permits. Assert invariants, state transitions, idempotency, ordering contracts, and observable completion rather than wall-clock sleeps. Exercise duplicate, reordered, delayed, partitioned, cancelled, and partial-failure paths only when relevant. Do not use retries to turn a flaky RED into GREEN; diagnose nondeterminism and retain replay data.

## Compatibility, protocols, schemas, and migrations

Test both sides of the supported compatibility window: old reader/new writer, new reader/old writer, client/provider versions, upgrade/rollback, or expand/migrate/contract phases as applicable. Use representative real fixtures stripped of secrets. Verify data preservation, idempotency, interrupted runs, constraints, defaults, unknown fields, and rollback policy. A migration test must use the engine semantics that carry the risk, not an incompatible in-memory substitute.

## Security and privacy

Turn the smallest safe exploit or policy violation into a boundary-level regression without including live credentials, personal data, malware payloads, or destructive targets. Assert both rejection and absence of forbidden effects, such as data disclosure, external contact, privilege change, or audit omission. Keep secret scanning and redaction active in fixtures and logs.

## Performance and resource behavior

Separate functional correctness from performance evidence. Prefer algorithmic invariants, operation counts at a contractual boundary, bounded resources, or project-owned benchmarks over fragile single-run timings. Warm-up, sampling, variance, hardware, load, and baseline policy must be explicit. Treat noisy benchmark movement as evidence to investigate, not a deterministic RED/GREEN signal.

## Visual, snapshot, and golden behavior

Use a small deterministic artifact and an independently reviewed baseline. Normalize only unstable fields that are not part of the contract. A bulk baseline update is not GREEN by itself; inspect the diff and pair it with semantic assertions where possible. Record platform/font/renderer limits when pixel identity is not portable.

## Property-, model-, and fuzz-driven slices

State the invariant or model independently, bound the input space and resource budget, retain the seed/corpus, and minimize failures. Promote each important minimized failure to a durable regression example. A fuzzer crash caused by harness exhaustion or invalid setup is not the intended RED.

## Data and ML systems

Version small representative datasets and schemas, control seeds where meaningful, and test pipeline contracts such as parsing, leakage prevention, feature shape, determinism bounds, and serving compatibility. Model-quality thresholds require an approved evaluation set and statistical policy; they are not ordinary deterministic unit assertions. Never copy sensitive production data into a test fixture without authorization and sanitization.

## Embedded and target-specific systems

Split pure logic from target effects, but retain target-level evidence for compiler, linker, ABI, interrupt, timing, memory, power, radio, sensor, or peripheral risks. Use simulator, emulator, loopback, hardware-in-the-loop, or device tests according to the behavior card. Report the exact board, toolchain, firmware, and unavailable target checks; host-only GREEN is not target GREEN.
