# Test Design and Oracles

Read this when selecting the observation seam, test level, examples, assertions, expected values, snapshots, or coverage boundary for a TDD slice.

## Start with a behavior card

Write a compact card before the first test:

- **Behavior:** the capability or invariant being added, in domain language.
- **Observation seam:** where an external observer can distinguish success from failure.
- **Independent oracle:** why the expected result is correct without repeating the implementation.
- **Test level:** the cheapest level that can expose the material risk.
- **Effects and fixtures:** state, clocks, randomness, processes, services, data, or hardware involved.
- **Expected RED:** the exact assertion, diagnostic, exit status, compile error, diff, or signal that should prove the behavior is absent.

A public seam is contractually observable, not necessarily a language-level exported function. It may be a library API, command and exit status, process protocol, HTTP or message boundary, rendered artifact, persisted state, schema, compiler/type interface, device signal, or domain service. Prefer the cheapest stable seam: close enough to diagnose, broad enough to survive internal refactoring.

Do not ask the user to approve an obvious existing seam. Ask or record an explicit assumption when multiple reasonable choices change compatibility, ownership, runtime cost, destructive risk, or what the project promises to consumers.

## Choose level by risk, not fashion

No level is universally superior:

| Material risk | Usually useful evidence |
|---|---|
| Pure rule, parser, transform, state transition | Focused function/module/component test |
| Collaborator contract or storage behavior | Component/integration test with a real or faithful boundary |
| Public API, CLI, protocol, packaging, deployment wiring | Process/contract/system test |
| User journey across owned components | A small end-to-end tracer plus lower-level diagnostics |
| Compile-time API, type safety, linker or schema contract | Compile-fail/pass, type, link, or schema fixture |
| Generated artifact, plan, migration, or infrastructure policy | Golden/plan/schema/policy diff plus semantic checks |

Use the narrowest test that can fail for the risk being changed. Add a broader tracer when wiring, packaging, configuration, or compatibility is itself the risk. Avoid duplicating the same assertion at every layer.

## Build an independent oracle

Good sources include an acceptance criterion, protocol or language specification, worked example, known literal, prior released behavior, trusted reference implementation, approved golden artifact, metamorphic relation, model, invariant, or independently calculated result.

Avoid tautologies: do not compute the expected value with the same algorithm, constants, parser, query builder, serializer, or generated output used by production code. For complex calculations, use a small hand-verifiable case, a distinct model, or a property that must hold across cases.

Several assertions are appropriate when they jointly prove one behavior, such as value plus emitted effect, exit status plus stderr, or response plus persisted state. Do not split a coherent contract merely to satisfy a one-assertion rule, and do not combine unrelated behaviors in one opaque test.

## Prefer durable observations

- Assert outcomes and contractually meaningful effects, not private calls, field layout, incidental ordering, allocation count, or internal helper names.
- Interaction assertions are valid when the interaction itself is the contract: for example, a protocol frame, audit event, idempotency key, transaction boundary, or forbidden external call.
- Direct database, filesystem, queue, or wire inspection can be correct when that adapter or stored representation is the subject of the test. It is a side channel when the promised behavior should instead be observed through another public interface.
- Avoid production-only test hooks. Prefer dependency boundaries already justified by design; a small behavior-preserving seam extraction is acceptable while green.

## Examples, tables, properties, and generated cases

Begin with one representative example that reveals the next design decision. Add boundary cases as separate slices when they represent distinct behavior. Parameterize only after examples share one contract and diagnostics remain clear.

Use property-, model-, fuzz-, or metamorphic tests when a few examples cannot cover a large input space. Keep a minimized regression example for any discovered defect, preserve deterministic seeds or replay data, and make shrinking/reproduction part of the evidence.

## Snapshots, goldens, and baselines

Snapshots and golden files are useful when the artifact is itself the contract and a reviewer can understand the diff. Keep them focused, deterministic, normalized only by documented rules, and review the initial baseline independently. Never create or update a baseline from the new production output without inspecting it against another source of truth.

## Coverage and mutation

Coverage is a diagnostic for unexercised paths, not the behavior or the stopping rule. A coverage increase can still assert nothing useful. Mutation testing can reveal insensitive tests, but surviving mutants are investigation signals rather than an instruction to couple tests to implementation.
