# Test Doubles and Effects

Read this when a slice touches time, randomness, files, databases, networks, processes, remote services, queues, operating-system resources, or hardware.

## Double only for a reason

Replace an uncontrolled boundary when using the real dependency would be unsafe, destructive, non-deterministic, unavailable, prohibitively slow, or unable to produce the required condition. Do not mock an owned collaborator merely because mocking is convenient; a real collaborator often preserves more design freedom and gives stronger evidence.

Choose the least powerful double that answers the question:

- **Stub:** returns controlled data; useful when only an input from the boundary matters.
- **Fake:** a working, cheaper implementation; useful for stateful behavior, provided its contract is kept aligned with the real dependency.
- **Spy:** records an effect that is itself observable or contractually important.
- **Mock/expectation:** constrains an interaction; reserve for protocols, safety boundaries, or effects whose call shape is part of the requirement.
- **Simulator/emulator/sandbox:** exercises a larger external contract without production impact.

Do not assert internal call sequences when only the outcome matters. Do assert that a forbidden call never occurred when non-contact, privacy, billing, idempotency, or safety is part of the behavior.

## Effects by category

### Time and randomness

Inject or control a clock, timer scheduler, random source, seed, or entropy boundary. Advance virtual time or trigger events deterministically; do not turn sleeps and generous timeouts into correctness proof. Preserve replay information for randomized failures.

### Files and processes

Use isolated temporary directories and real file semantics when practical. For CLIs, prefer invoking the built artifact or real entry point as a process when parsing, exit status, signals, stdout/stderr, environment, or working-directory behavior is under test. Clean up only paths created by the test and make parallel execution safe.

### Databases, caches, and queues

Prefer an isolated real engine, disposable container, transaction, schema, or project-supported fake when engine semantics matter. An in-memory substitute is insufficient for locking, isolation, collation, query planning, migrations, or vendor-specific behavior unless a contract suite proves fidelity. Use unique namespaces and deterministic cleanup.

### HTTP, RPC, messages, and third-party services

Prefer a local fake server, protocol stub, recorded approved fixture, provider sandbox, or consumer/provider contract. Do not contact production. Model transport errors, retries, partial responses, ordering, duplication, timeouts, and idempotency only when they belong to the behavior being added. Redact secrets and personal data from fixtures.

### Hardware and operating-system resources

Choose the lowest layer that exposes the risk: pure logic, driver boundary, simulator, emulator, loopback, hardware-in-the-loop, or target device. Record capabilities and skipped target checks. Never represent simulator success as physical-device evidence when timing, power, radio, sensor, interrupt, memory, or toolchain behavior is material.

## Keep doubles honest

- Run contract tests against both a fake and the real adapter or provider sandbox when divergence is plausible and affordable.
- Keep fixtures minimal and versioned with the external contract; fail visibly on unknown fields or protocol changes when compatibility matters.
- Do not reproduce the production implementation inside a fake. Model the boundary semantics needed by tests, not its internal algorithm.
- Make failure injection explicit and local to the test; reset global hooks, environment variables, patched functions, ports, clocks, and state in reliable cleanup.
- A double-induced failure is not a valid RED until the production path actually reaches the boundary and the diagnostic demonstrates the requested missing behavior.
