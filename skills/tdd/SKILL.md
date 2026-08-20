---
name: tdd
description: "Use when the user explicitly requests test-driven or test-first implementation, RED-GREEN-REFACTOR, or a failing regression test before a bug fix. Applies across languages, frameworks, services, CLIs, libraries, data systems, infrastructure, and embedded targets by deriving seams and commands from the target project. Do not use merely because a change should include tests, for coverage-only work, or for exploratory prototypes whose behavior has not stabilized."
---

# Test-Driven Development

TDD here is a bounded implementation discipline: prove one requested behavior is absent, add the smallest production change that makes it present, improve the design while green, and repeat. Do not activate merely because a change should have tests.

This skill does not own requirements discovery, task orchestration, commits, code review, release, or persistent iteration state. When a parent workflow is active, preserve its plan, authority, verification, and completion contract.

## Invariants

- Derive commands and layout from project-owned instructions, CI, manifests, task runners, wrappers, and neighboring tests. Do not invent a framework, command, working directory, or test layout.
- A test-like target name is not proof of safety. Inspect unfamiliar wrappers before execution; do not deploy, publish, flash, migrate shared state, or contact production without explicit authority and isolation.
- Before editing, state the behavior, observation seam, independent oracle, test level, and expected RED reason. Prefer the cheapest stable seam that can disprove the behavior.
- Do not ask for ritual seam confirmation. Surface a choice only when plausible seams materially change the public contract, implementation cost, destructive risk, or verification confidence.
- A RED result is valid only when the failure directly demonstrates the missing behavior. A compile-, type-, link-, schema-, or collection-time failure can be valid when that failure is the requested contract; unrelated setup, fixture, syntax, dependency, or environment failures are not.
- Use one vertical behavior slice per cycle. A slice may need several assertions or tests, but it must establish one coherent capability rather than a speculative batch.
- GREEN is the smallest production change that satisfies the current behavior, not the fewest characters and not permission to hard-code only the example.
- REFACTOR only while green. Preserve behavior, keep the relevant checks passing, and do not smuggle the next capability into cleanup.
- Never weaken, delete, skip, quarantine, or silently regenerate a legitimate failing test merely to obtain GREEN. Change a test only when its stated contract or oracle is proven wrong, and record why.

## Workflow

1. **Read the project contract.** Resolve repository and package/module scope, applicable authority files, existing test conventions, and the narrowest supported verification commands. Establish whether relevant failures already exist when a cheap baseline check can distinguish them.
2. **Define one behavior card.** Record the observable behavior, stable seam, independent oracle, selected test level, fixtures/effects, and the exact failure expected before implementation.
3. **RED.** Add the smallest clear example through the selected seam. Run the narrowest command that exercises it. Confirm the test actually ran and failed for the predicted missing-behavior reason; repair the harness instead of continuing on a false RED.
4. **GREEN.** Make the smallest general production change. Re-run the exact RED command until it passes. Keep unrelated failures visible and do not broaden scope to fix them without authority.
5. **REFACTOR.** Improve names, duplication, boundaries, or structure exposed by the slice while the suite stays green. Re-run the focused check after each meaningful cleanup.
6. **Repeat.** Choose the next behavior from what the last cycle taught, not from an upfront inventory of imagined tests. Stop when the requested acceptance boundary is covered.
7. **Verify.** Run project-required affected checks, then the broadest proportionate suite available. Report skipped or unavailable checks and any residual risk; never imply they passed.

## Completion evidence

Report:

- each completed behavior with its seam, oracle, and test level;
- the RED command and predicted failure evidence for every slice;
- focused and broader verification commands with outcomes;
- any pre-existing failure, skipped check, environmental limit, changed test contract, or residual risk.

## On-demand references

- [Test design and oracles](references/test-design.md) — read when choosing seams, levels, assertions, examples, snapshots, or coverage boundaries.
- [Test doubles and effects](references/test-doubles-and-effects.md) — read when code touches time, randomness, files, databases, networks, processes, services, or hardware.
- [Cross-stack execution](references/cross-stack-execution.md) — read when discovering the correct scope, working directory, toolchain, commands, and meaning of RED across ecosystems.
- [Legacy and hard cases](references/legacy-and-hard-cases.md) — read for bug reproduction, legacy code, missing harnesses, generated code, concurrency, migrations, security, performance, visual, property-based, data, or embedded work.

## Attribution

This adaptation preserves upstream attribution in [NOTICE.md](NOTICE.md).
