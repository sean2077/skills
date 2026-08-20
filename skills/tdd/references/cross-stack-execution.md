# Cross-Stack Execution

Read this when discovering repository scope, working directory, test toolchain, focused commands, verification breadth, or what counts as RED in an unfamiliar ecosystem.

## Derive commands from repository evidence

Use this authority order, stopping as soon as the project contract is clear:

1. Applicable agent/maintainer instructions and contributor documentation.
2. CI and release workflows that define supported environments and required checks.
3. Project-owned wrappers and task runners.
4. Workspace, build, dependency, and tool configuration manifests.
5. Neighboring tests and recent repository-consistent changes.
6. Exact tool help or schema for a command already evidenced by the project.

Do not infer a command solely from a file extension, install a new framework/runtime/compiler/service, or switch package managers to begin TDD. When no harness exists, treat adding one as a design change and use the guidance in `legacy-and-hard-cases.md`.

A target named `test` is not proof of safety. Inspect unfamiliar wrappers or task definitions before running them. Do not deploy, publish, flash devices, migrate shared state, mutate production data, or contact production merely because a repository target is test-shaped; require explicit authority and an isolated environment for such effects.

Resolve the repository root, then the smallest owning workspace/package/module. In a monorepo, run commands from the directory required by its wrapper or workspace configuration; record that working directory with the command. Reuse lockfile-selected tooling and checked-in launchers where present.

## Ecosystem signals, not prescriptions

The following are discovery clues only. Project-owned commands always win.

| Ecosystem | Inspect before choosing commands |
|---|---|
| JavaScript/TypeScript | workspace and package manifests, lockfile, scripts, test/build/type configs |
| Python | project/lock/config files, environment manager, test discovery and type/lint config |
| Go | module/workspace files, package boundaries, build tags, generated files |
| Rust | workspace manifests, feature flags, target triples, examples and compile fixtures |
| JVM | build wrapper, module graph, source sets, test tasks, language/plugin versions |
| .NET | solution/project files, target frameworks, test projects, repository build props |
| C/C++ | build presets/files, toolchain, targets, compile definitions, test registration |
| Ruby | dependency lock, task files, framework config, application test conventions |
| PHP | dependency/config files, framework runner, extensions and service fixtures |
| Swift/Objective-C | package/workspace/project, schemes, destinations, platform availability |
| Elixir/Erlang | project/rebar config, umbrella apps, environment and supervision fixtures |
| Dart/Flutter | package/workspace config, platform targets, widget/integration conventions |
| Infrastructure/data | validation/plan/schema tools, migration runner, query engine, local sandbox |
| Embedded/hardware | build system, board/target config, simulator, flashing and target test harness |

Do not make npm, Jest, Vitest, pytest, Cargo, Gradle, Maven, dotnet, CMake, or any other familiar tool a universal default. Use one only when repository evidence selects it.

## Interpret RED by contract

- **Runtime behavior:** the test executes and its assertion, exit status, output, state, or effect differs for the predicted missing behavior.
- **Compile/type/link behavior:** a compile-pass or compile-fail fixture produces the expected diagnostic boundary; unrelated syntax or missing dependency failures are harness failures.
- **Schema/plan/policy behavior:** the validator or semantic diff rejects exactly the absent rule; parse errors and missing providers are not evidence.
- **Packaging/configuration behavior:** the produced artifact or isolated consumer fails at the supported entry point, not merely inside a test-only path.
- **Target behavior:** the selected simulator/device signal fails for the intended condition and the harness confirms that the test actually ran on the claimed target.

Capture enough output to prove the predicted reason without pasting unrelated logs. When a command runs zero tests, selects the wrong target, uses stale artifacts, or exits because setup is broken, repair the harness and rerun RED.

## Verification ladder

After each edit, prefer a cost-aware ladder supported by the project:

1. the exact failing example;
2. the owning test file/package/target;
3. affected static, compile, schema, formatting, or generation checks;
4. affected integration/contract suites;
5. the broad project-required suite.

Broaden earlier when shared infrastructure, global configuration, public compatibility, packaging, or generated artifacts are changed. Do not omit a mandated check merely because a focused command is green, and do not claim an unavailable platform or external target passed.

## Generated and cached artifacts

Identify ownership before editing. Test and change the source, generator, schema, template, or build rule rather than hand-editing generated output. Regenerate with the project-owned command, include the reviewable diff, and verify reproducibility. Invalidate or bypass caches when stale results could make RED or GREEN ambiguous; do not delete broad user caches without authorization.
