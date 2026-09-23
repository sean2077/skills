# Project testing conventions

Use when `testing` is selected for full project-harness initialization or upgrade, including a read-only preview.
Establish how this project writes trustworthy tests, not just how to launch them. This is
project guidance work, not a request to implement tests or invoke TDD for every change.

## Adopt the project's testing contract

Read applicable instructions, existing test/development guidance, runner/discovery settings,
CI and a few relevant tests/fixtures. Follow explicit project policy and actual configuration;
resolve contradictions rather than inferring policy from a directory name or one old test.
Preserve module-local differences, colocated tests, `test/`, `tests/`, `spec/`, `__tests__/`,
existing frameworks, wrappers, naming, test data and coverage gates. No new universal layout.

Identify whether test-first is required, optional or unspecified for each relevant scope.
General test quality does not establish that choice. Preserve scoped TDD requirements and
coverage thresholds unless a policy change is explicitly authorized; coverage alone is not
correctness. Do not infer new requirements from onboarding or a missing test guide.
When a user instruction conflicts with project policy, surface the conflict under the existing
authority rules rather than silently changing either. No new approval ceremony is needed.

## Generic rules ship separately

The installed [testing guide](../assets/conventions/testing.md) (`.agents/conventions/testing.md`,
routed from the managed block) carries the generic daily rules: independent oracles, stable seams,
test level and doubles, reproducibility, sensitivity, difficult boundaries and explicit test-first
work. Do not restate them in project docs. Setup connects them to this project's facts: the runner
and discovery arguments, where real engines, faithful fakes, local servers or sandboxes are used
and what each cannot prove, existing credential and environment restrictions, and any permitted
quarantine or recovery policy. Property, fuzz, mutation, performance and hardware methods remain
conditional on the actual risk and the project's supported tools; do not install them as part of
onboarding.

## Write project-owned guidance, not a second testing system

For authorized full setup, fill useful gaps in the current testing/development guide and
connect it from the applicable Agent entry point. Keep only high-frequency commands and
non-obvious limits resident; deeper guidance belongs in project docs. Preserve language,
existing numbering/frontmatter and local scopes. No required `TESTING.md`, new wrapper,
shared runtime, skill dependency, or generated testing-policy file is introduced.

For a CLI project, a useful addition might identify its real process-test entry for exit codes
and cwd, its local service fake, and the separate opt-in provider check. It should not invent
commands or claim that a fake proves vendor compatibility. Ordinary testing follows this
project guide; an explicitly selected TDD task additionally follows RED–GREEN–REFACTOR.

If no test harness exists, identify that gap and a minimal project-consistent option. Adding
a framework, dependencies, services, production/device access or a full test suite is a
separate scope decision, not implicit permission from scaffold setup. Complete independent
safe guidance rather than manufacturing placeholder tests or an unverifiable quality claim.

## Upgrade and verify

Apply the [project ownership rules](project-conventions.md#upgrade-by-current-ownership-and-coverage):
follow relocated/merged guides, preserve equivalent customizations and fix confirmed drift.
An upstream reference change does not authorize lowering gates or changing TDD policy. Follow
explicitly authorized policy changes in their existing scope; otherwise do not recreate old
test directories, duplicate policy or refresh dates merely to match upstream.

Walk a representative test-writing task from the resulting entry points: can a new Agent find
the correct scope/runner, an independent source of expected behavior, the real/double boundary,
the applicable test-first policy and the checks it cannot claim? Inspect or safely execute only
the affected checks; a command listing, green asset verification or matching headings does not
prove test effectiveness. Record observed, inspected and unavailable evidence separately.
