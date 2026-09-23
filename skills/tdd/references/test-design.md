# Test Design for a TDD Slice

Use the project's applicable test-quality guidance first. The following is a self-contained
fallback for choosing the next slice, not a second project-wide policy or a dependency on
another installed skill.

## Choose an observable missing behavior

Identify the capability, stable observation seam, independent expected result, smallest test
level that exposes its risk, necessary fixtures/effects and the predicted RED reason. Resolve
material uncertainty before asserting an invented contract; no separate behavior form is needed.
A seam may be an API, CLI exit/output, persisted state, wire interaction, compiled interface,
rendered artifact or device signal, not necessarily a language-level exported function.

Use acceptance criteria, a specification, a hand-verifiable literal, independently calculated
model or invariant for the oracle. Do not call or duplicate the production algorithm to compute
its own expected result. Several assertions can jointly establish one behavior. Internal calls,
incidental order and wording matter only when they are themselves part of the contract.

Observe through a public seam. Inspecting a database, filesystem, queue or wire directly is
correct only when that adapter or stored form is the subject; otherwise it is a side channel.
Avoid production-only test hooks: prefer an existing dependency boundary, or a small
behavior-preserving seam extraction while green.

For pure rules, start near the function/module. For wiring, packaging, configuration or storage
semantics, exercise the real boundary; add a broader tracer when lower-level tests cannot expose
the risk. Test-first does not mandate unit-only or E2E-only testing, nor changing the framework.

## Prove sensitivity, then keep the contract stable

Run the selected example on unimplemented behavior and verify that it actually executes and
fails for the predicted reason. Zero tests, stale artifacts and unrelated setup errors are not
RED. With a double or fault injection, check the real production path reaches that boundary.
Keep that example unchanged through GREEN unless evidence proves its contract is wrong.

Use the project's snapshots/goldens only for meaningful artifacts with an independently
reviewed baseline; generated production output is not its own approval. Keep property/fuzz
failures as minimized examples with seeds/replay data. Coverage and mutation tools may expose
gaps, but do not replace RED evidence or justify weakening gates/coupling to private details.
See [effects](test-doubles-and-effects.md) and [hard cases](legacy-and-hard-cases.md) only when
those risks arise; specialized methods are not required for every slice.
