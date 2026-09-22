# Development guide

This page owns contributor workflow, local verification, generation, platform checks, and release procedure. `.github/workflows/validate.yml` remains the normative definition of CI; update this summary when that workflow changes.

## Prerequisites

- Git with real symlink support for harness validation.
- Python 3.11 for the primary local/CI suite; generated workflow runtimes also have a separately exercised Python 3.8 floor.
- Bash on Linux/macOS or Git Bash on Windows.
- Node.js and `npx` for installer discovery and payload smoke tests.
- ShellCheck for bundled shell scripts.

Use UTF-8 and suppress Python bytecode during payload-sensitive checks:

```bash
export PYTHONUTF8=1
export PYTHONDONTWRITEBYTECODE=1
```

## Worktree flow

Prefer starting a new implementation/review session in its task worktree. A session may
remain in the primary checkout for planning or coordination, provided every task read,
edit, test, and review targets the exact task checkout. Reuse a worktree already assigned
by the user or an external workbench; never create another just to satisfy the scaffold.
The [managed rule](../AGENTS.md#worktree-per-change-hard-rule) still prohibits primary
worktree edits. See [workspace context](../skills/agent-scaffold/references/workspace-context.md)
for persistent user preferences, branch-local harness files, and host permission limits.

For an existing task checkout, inspect it without changing session ownership:

```bash
# Replace with the assigned absolute path, not the session's presumed repository root.
task="/absolute/path/to/task-checkout"
git -C "$task" rev-parse --show-toplevel
git -C "$task" status --short --branch
git -C "$task" rev-parse HEAD
# Run each project check with cwd set to "$task" (or its documented subdirectory).
```

Only if no task checkout is assigned and the scaffold owns creation, run from the primary:

```bash
bash .agents/tools/worktree.sh new docs-example
# Use the printed path for a new session or explicit per-tool working directories.
```

Record the intended base and actual task revision. The helper records its resolved local
trunk; a workbench may use a different base. Follow the project's delivery policy and
compare with the intended remote base before publication. For a PR/MR, publish the task
branch and open the change request; do not call `done` as an implicit merge or cleanup.

`done --dir <absolute-wt>` is only for an authorized scaffold-owned local-trunk lifecycle:
it merges, pushes, and removes the worktree. External owners keep control of their own
integration/archive operations. Leave the target before removal; on Windows a live Agent,
terminal, or server can keep it locked even after a command shell changes directory.

## Select checks by changed surface

| Changed surface | Minimum focused evidence before the full applicable suite |
|---|---|
| README or documentation only | `git diff --check`, local Markdown link/anchor review, `python scripts/validate_skills.py`, and verification of every changed command or external claim |
| Skill frontmatter, name, route, references, manifest, or layout | Catalog health, catalog validation, their regression fixtures, official `skills-ref`, and audited `npx skills` discovery/install smoke tests |
| Shared or generated runtimes | Both generator `--check` commands plus migration, P0 behavior, hardening, private-skill, and relevant skill-contract tests |
| `agent-scaffold` source or managed projections | Core Python test, static shell gate, full throwaway-repository E2E, real-symlink checks, and platform matrix |
| Shell scripts | Targeted behavior tests plus ShellCheck |
| Evaluation suites or adapters | Suite validation, representative execution, `validate-result`, cost/scope gates, and repository-isolation checks |
| Release or version logic | SemVer planner fixtures, changelog validation, reusable validation workflow, and tagged release dry review |

Changes to shared routing, frontmatter, validators, generators, installer behavior, scaffold logic, contracts, or CI require the complete repository suite—not only a targeted test.

## Core local verification

Install the pinned validation dependencies, then run the repository-owned checks:

```bash
python -m pip install -r requirements-validation.txt

python scripts/catalog_health.py
python scripts/test_catalog_health.py
python scripts/validate_skills.py
python scripts/test_validate_skills.py
python scripts/tests/test_semver_release_plan.py
python scripts/tests/test_tdd_contract.py
python scripts/tests/test_private_skill_eval_contract.py
python scripts/tests/test_live_skill_eval_adapter.py
python scripts/tests/test_task_outcomes.py
python scripts/tests/test_release_execution.py

python scripts/generate_workflow_runtimes.py --check
python scripts/generate_p0_runtimes.py --check
python scripts/tests/test_workflow_runtimes.py
python -m unittest -v scripts.tests.test_p0_agent_workflows
python -m unittest -v scripts.tests.test_p0_hardening
python scripts/tests/test_protocol_primitives.py

python .agents/skills/skill-eval/scripts/skill_eval.py validate evals/examples/tdd/suite.json
for suite in evals/agent-skills/*/suite.json; do
  python .agents/skills/skill-eval/scripts/skill_eval.py validate "$suite"
done
result="$(mktemp)"
trap 'rm -f "$result"' EXIT
python .agents/skills/skill-eval/scripts/skill_eval.py run \
  evals/examples/tdd/suite.json --output "$result"
python .agents/skills/skill-eval/scripts/skill_eval.py validate-result "$result"
rm -f "$result"
trap - EXIT

for skill in skills/*; do
  [[ -d "$skill" ]] && python -m skills_ref.cli validate "$skill"
done
python -m skills_ref.cli validate .agents/skills/skill-eval

python scripts/tests/test_agent_scaffold_core.py
python scripts/tests/test_workspace_entry.py
bash scripts/check-agent-scaffold.sh
bash scripts/tests/test-tooling-inventory.sh
AGENT_SCAFFOLD_E2E_REQUIRE_SYMLINKS=1 bash scripts/e2e-agent-scaffold.sh

NO_COLOR=1 DISABLE_TELEMETRY=1 npx --yes skills@1.5.17 add . -l
find scripts skills -type f -name '*.sh' -print0 | xargs -0 shellcheck
git diff --check
```

The CI workflow additionally:

- runs the primary suite on Ubuntu, macOS, and Windows;
- asserts Bash/platform expectations and real `CLAUDE.md` symlink behavior;
- installs every skill into a throwaway repository, rejects symlink/special entries in public payloads, and byte-compares source with installed files;
- reruns generated-runtime and behavior checks under an actual Python 3.8 interpreter.

Do not report those platform, installer-fidelity, or Python-floor results unless those exact environments/checks ran.

## Evaluation evidence

The [live routing guide](../evals/agent-skills/README.md) owns measurement semantics and probe limitations. `test_live_skill_eval_adapter.py` covers host exits, strict JSON, cache-inclusive usage, revision-contained candidate files, and typed verifier comparisons. `test_tdd_contract.py` protects distribution and attribution; it deliberately does not enforce English sentence fixtures as a substitute for behavior evaluation. Commit changed suite manifests before validating them because evaluation pins inputs to Git.

The optional [task outcome fixtures](../evals/tasks/README.md) inspect actual artifacts and captured tool results under no-skill, brief-request, and pinned-skill conditions. Their CI reference actions validate the oracles, not model effectiveness. The release execution fixture runs repository-owned shell scripts against local Git and a mock publisher; it never publishes.

### Optional skill-verifier

Use the project-owned `skill-verifier` subagent for substantive skill changes, task-artifact review, or uncertain evaluation claims. Routine wording fixes need no extra reviewer. Pass the absolute task checkout, revision (and dirty changes when relevant), scope, acceptance, and existing result paths. For example:

> Use skill-verifier to inspect the spec-writing change at <revision> in <absolute-task-checkout> and the supplied results. Look for regressions and assertions that could pass a wrong output. Return findings and evidence; do not modify the reviewed files.

The source is `.agents/subagents/skill-verifier/{metadata.json,instructions.md}`. Generate the Claude/Codex projections with `python .agents/tools/generate-subagents.py`; `--check` verifies drift. The existing private-harness test and static scaffold gate cover this wiring. It is not installed by catalog/scaffold consumers, and neither the project `skill-eval` nor its manuals are duplicated in the role.

Models and reasoning effort are left to the host. Claude exposes Read/Grep/Glob/Bash, not editing or delegation tools; Bash can still write. Codex requests `read-only`, but parent runtime overrides can change effective permissions. Inspect the actual host policy; tests needing writes belong in a separately authorized disposable environment, not the reviewed checkout. The parent handles blocked execution and corrections.

A cold-reader/anonymous A/B judgment needs a fresh instance with only the task, acceptance, and anonymized artifacts. Do not reuse the source-review instance or give it version identities; inherited project context may prevent a truly blind claim. Keep baseline/treatment execution separate from this evaluator, and follow the [task outcome guide](../evals/tasks/README.md) for measured comparisons. The parent evaluates the findings rather than treating the subagent's verdict as approval.

These are configured boundaries, not live-host certification. Host discovery, actual permissions and inherited context need an observed run; the [compatibility matrix](compatibility.md) records the dated host documentation for subagent definitions and what it does not prove.

## Generated files

```bash
# After editing scripts/workflow_runtime/
python scripts/generate_workflow_runtimes.py

# After editing scripts/p0_runtime/
python scripts/generate_p0_runtimes.py
```

Review the generated diff, then rerun the corresponding `--check` command and behavior tests. For scaffold runtime under `.agents/tools/`, edit the `agent-scaffold` catalog skill source and use `agent-scaffold upgrade`; for project skills and subagents, use the relink/generator commands documented in the managed `AGENTS.md` block.

## Installer checks

The audited reproducibility pin is `skills@1.5.17`; the current upstream release is tracked separately in [compatibility.md](compatibility.md). After changing catalog skill names, frontmatter, catalog metadata, or layout:

1. Run local root discovery with the audited pin.
2. Install into a fresh temporary Git repository for the intended target.
3. Compare every installed file with the source and reject non-regular payload entries.
4. After pushing an intended discovery fix, repeat the smoke test against the remote repository path.
5. Evaluate a newer CLI version only as an explicit dependency change; do not silently substitute it for the pin.

Use top-level `npx skills --help` to inspect options. With the audited pin, `npx skills add <source> --help` can execute the add flow. Never run project-scope `skills remove` from this catalog root because it can delete product `skills/*`.

## Release flow

1. Keep release-facing changes under `CHANGELOG.md` Unreleased and use Conventional Commits without `Co-Authored-By`.
2. Merge only after the required local checks and `main` CI succeed.
3. Create and push an annotated `vX.Y.Z` or numbered `-alpha.N`, `-beta.N`, or `-rc.N` tag from the validated snapshot.
4. Let `.github/workflows/release.yml` call the complete validation workflow, extract the matching changelog section, and create the GitHub Release.
5. Do not create a competing manual release while the repository workflow owns publication.

See [repository architecture](architecture.md) for source ownership and [compatibility.md](compatibility.md) before changing platform or host-support language.
