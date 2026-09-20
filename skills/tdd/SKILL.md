---
name: tdd
description: "Use when the user or project explicitly requires test-first/TDD, RED-GREEN-REFACTOR, or a failing regression before a fix. Not for coverage-only work, ordinary testing, or exploratory prototypes with an unstable oracle."
---

# Test-Driven Development

Prove one requested behavior is absent, implement it, and improve the design while green. TDD is selected by the user or applicable project policy, not merely because a task needs tests. Preserve the active delivery scope and completion contract; do not start another orchestrator.

## RED–GREEN–REFACTOR

Choose an observable behavior, stable seam, independent oracle, test level, and expected missing-behavior failure. This can be evident in the test and a short explanation; no separate behavior card or ritual seam approval is required. Surface choices only when they materially change the contract, cost, destructive risk, or confidence.

**RED:** add the smallest example for one coherent capability and run the exact command that exercises it. Confirm it actually ran and failed because the behavior is missing. Compile/type/schema/collection failures count only when they demonstrate the requested contract; unrelated syntax, fixture, setup, or dependency failures are not RED.

**GREEN:** make the smallest general production change that satisfies the behavior, then rerun the RED command. Several assertions may belong to one slice; do not hard-code the example or batch speculative capabilities. Keep unrelated failures visible without silently expanding scope.

**REFACTOR:** improve the design only while green, without adding the next behavior. Rerun invalidated checks after meaningful cleanup, not an unrelated full suite after every cosmetic edit. Continue with the next needed behavior and finish with project-required affected checks and proportionate integrated verification.

## Safety and evidence

- Derive commands, working directories, layout, and frameworks from the target project's instructions, manifests, CI, wrappers, and tests. A test-like name is not proof of safety; inspect unfamiliar wrappers before executing them.
- Do not deploy, publish, flash, migrate shared state, or contact production without explicit authority and isolation.
- Never weaken, delete, skip, quarantine, or regenerate a legitimate failure merely to get GREEN. Change an oracle only when evidence proves its contract wrong, and explain why.
- Preserve observed RED and GREEN evidence for each capability, with exact commands and relevant failures. Summarize rather than repeating logs or fields already visible in the task. State pre-existing failures, unrun checks, changed test contracts, and residual risks; do not imply an unrun check passed.

## On-demand references

- Read [test design and oracles](references/test-design.md) when seams, test levels, snapshots, or coverage boundaries are uncertain.
- Read [test doubles and effects](references/test-doubles-and-effects.md) when dependencies involve time, randomness, IO, networks, or other effects.
- Read [cross-stack execution](references/cross-stack-execution.md) when translating the discipline to the project's language, build, or test tooling.
- Read [legacy and hard cases](references/legacy-and-hard-cases.md) when legacy seams, regressions, untestable boundaries, or environment failures complicate the cycle.

See [NOTICE.md](NOTICE.md) for upstream attribution.
