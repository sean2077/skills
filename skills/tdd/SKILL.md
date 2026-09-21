---
name: tdd
description: "Use when the user or project explicitly requires test-first/TDD, RED-GREEN-REFACTOR, or a failing regression before a fix. Not for coverage-only work, ordinary testing, or exploratory prototypes with an unstable oracle."
---

# Test-Driven Development

Demonstrate a missing behavior, implement it, and improve the design while green.

## RED–GREEN–REFACTOR

Choose an observable behavior, stable seam, independent oracle, test level, and expected missing-behavior failure. Resolve choices that materially affect the contract, cost, safety, or confidence.

**RED:** add an example for one coherent capability and run the command that exercises it. Confirm the test ran and failed because the behavior is missing. Compile, type, schema, or collection failures qualify when they demonstrate the requested contract; unrelated syntax, fixture, setup, or dependency failures do not.

**GREEN:** make a general production change that satisfies the behavior, then rerun the RED command. Keep the implementation within the selected capability and expose unrelated failures separately.

**REFACTOR:** improve the design while green, keeping the behavior unchanged. Rerun invalidated checks after cleanup. Continue with the next needed behavior and finish with required project checks and integrated verification.

## Safety and evidence

Derive commands, working directories, layout, and frameworks from project instructions, manifests, CI, wrappers, and tests. Inspect unfamiliar wrappers for effects before running them. Deployment, publication, flashing, shared-state migration, and production access require explicit authority and suitable isolation.

Preserve legitimate failing tests; never weaken, delete, skip, quarantine, or regenerate a legitimate failure merely to reach GREEN. Change an oracle only when evidence shows its contract is wrong, and explain the correction.

Retain observed RED and GREEN evidence for each capability, including commands and relevant failures. Report pre-existing failures, unrun checks, changed test contracts, and residual risk.

## References

- [Test design and oracles](references/test-design.md): seams, test levels, snapshots, and coverage boundaries.
- [Test doubles and effects](references/test-doubles-and-effects.md): time, randomness, IO, networks, and other dependencies.
- [Cross-stack execution](references/cross-stack-execution.md): adapting to project languages, builds, and test tools.
- [Legacy and hard cases](references/legacy-and-hard-cases.md): regressions, legacy seams, untestable boundaries, and environment failures.

See [NOTICE.md](NOTICE.md) for upstream attribution.
