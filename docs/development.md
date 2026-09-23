# Development guide

This page owns contributor commands, verification, generation, and this repository's release procedure. [Validation CI](../.github/workflows/validate.yml) is the executable definition of the full suite; [architecture](architecture.md) identifies which sources to edit.

## Prerequisites

Use Git with real symlink support, Python 3.11 for the primary suite, Bash on Linux/macOS or Git Bash on Windows, Node.js/`npx` for installer checks, and ShellCheck for shell validation. Generated runtimes and the release runtime have a separately exercised Python 3.8 floor; do not confuse that with the maintainer environment or certify all scripts at that floor.

Install pinned validation dependencies with `python -m pip install -r requirements-validation.txt`. Use UTF-8 and avoid bytecode files contaminating installable payloads:

```bash
export PYTHONUTF8=1
export PYTHONDONTWRITEBYTECODE=1
```

## Worktree flow

Prefer a task-local implementation/review session, but honor the user's session entry. Resolve the actual task checkout and its authority chain before reads, edits, tests, or review. Reuse a user/workbench-assigned worktree; the [managed rule](../AGENTS.md#worktree-per-change-hard-rule) prohibits primary-worktree edits, not primary-checkout planning.

```bash
# Use the assigned absolute path, not the session's presumed repository root.
task="/absolute/path/to/task-checkout"
git -C "$task" rev-parse --show-toplevel
git -C "$task" status --short --branch
git -C "$task" rev-parse HEAD
# Run subsequent checks with cwd set to "$task" (or its documented subdirectory).
```

Only when no task checkout is assigned and the scaffold owns creation, run `bash .agents/tools/worktree.sh new <name>` from the primary checkout. Record the intended base and actual task revision; the helper's resolved local trunk is not proof of the latest remote base. A shell `cd` does not reload host instructions or permissions. See [workspace context](../skills/agent-scaffold/references/workspace-context.md).

For a PR/MR, publish the task branch and verify the created change request; do **not** call `done` as an implicit merge or cleanup. `done --dir <absolute-wt>` merges, pushes, and removes a scaffold-owned worktree only with explicit authorization. External workbench owners retain lifecycle control. Leave a worktree before removal; Windows processes can keep it locked.

## Select checks by changed surface

| Changed surface | Focused evidence |
|---|---|
| Repository documentation only | Unstaged and staged whitespace checks; changed local links/anchors and reader routes; `python scripts/validate_skills.py`; inspect or execute changed commands and identify unverified external claims |
| Skill entry point, references, frontmatter, route, manifest, or layout | Catalog health/validation and fixtures; official `skills-ref`; applicable payload/contract checks; installer smoke tests when distribution changes |
| Shared/generated runtimes | Both generator `--check` commands and affected workflow, P0, hardening, private-skill, and evaluation tests |
| Scaffold source or managed projections | Core/workspace/layout-preservation tests, static shell gate, full throwaway E2E, real-symlink checks, and platform matrix |
| Shell scripts | Targeted behavior tests and ShellCheck |
| Evaluation manifests/adapters | Suite/result validation, adapter/oracle regressions, scope/cost/isolation checks; live execution only when separately configured and authorized |
| Release/version logic | Planner/extractor fixtures, release execution tests, and review of the exact tagged snapshot/workflow |

Shared routing, frontmatter, validator, generator, installer, scaffold, contract, or CI changes require the complete applicable repository suite. For a wording-only change, do not turn optional evaluation or independent review into a new gate. See [documentation verification](documentation-maintenance.md#evidence-and-verification) for what catalog link validation does not cover.

## Core local verification

Run from the task checkout in Bash. The subshell stops on failure without replacing the caller's traps or shell settings. The commands mirror CI's core checks; platform-specific and installer-fidelity coverage is described below.

```bash
(
  set -eo pipefail
  export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
  python -m pip install -r requirements-validation.txt

  python scripts/catalog_health.py
  python scripts/test_catalog_health.py
  python scripts/validate_skills.py
  python scripts/test_validate_skills.py
  python scripts/tests/test_semver_release_plan.py
  python scripts/tests/test_scaffold_distribution.py
  python scripts/tests/test_private_skill_eval_contract.py
  python scripts/tests/test_live_skill_eval_adapter.py
  python scripts/tests/test_task_outcomes.py
  python scripts/tests/test_release_execution.py

  python scripts/generate_workflow_runtimes.py --check
  python scripts/generate_p0_runtimes.py --check
  python scripts/tests/test_workflow_runtimes.py
  python -m unittest -v scripts.tests.test_p0_agent_workflows
  python -m unittest -v scripts.tests.test_p0_hardening

  python .agents/skills/skill-eval/scripts/skill_eval.py validate evals/examples/offline/suite.json
  for suite in evals/agent-skills/*/suite.json; do
    python .agents/skills/skill-eval/scripts/skill_eval.py validate "$suite"
  done
  result="$(mktemp)"
  trap 'rm -f "$result"' EXIT
  python .agents/skills/skill-eval/scripts/skill_eval.py run \
    evals/examples/offline/suite.json --output "$result"
  python .agents/skills/skill-eval/scripts/skill_eval.py validate-result "$result"

  for skill in skills/*; do
    if [[ -d "$skill" ]]; then
      python -m skills_ref.cli validate "$skill"
    fi
  done
  python -m skills_ref.cli validate .agents/skills/skill-eval

  python scripts/tests/test_agent_scaffold_core.py
  python scripts/tests/test_workspace_entry.py
  python scripts/tests/test_project_conventions.py
  python scripts/tests/test_guidance_selection.py
  bash scripts/check-agent-scaffold.sh
  AGENT_SCAFFOLD_E2E_REQUIRE_SYMLINKS=1 bash scripts/e2e-agent-scaffold.sh

  NO_COLOR=1 DISABLE_TELEMETRY=1 npx --yes skills@1.5.17 add . -l
  find scripts skills -type f -name '*.sh' -print0 | xargs -0 shellcheck
  git diff --check
  git diff --cached --check
)
```

CI also runs on Ubuntu, macOS, and Windows; asserts platform shell/real-symlink behavior; installs every catalog skill into a throwaway repository and byte-compares regular-file payloads; and exercises the runtime floor under Python 3.8. A local run on one platform does not establish those other results; do not report platform, installer-fidelity, or Python-floor results unless those exact environments or checks ran. The offline example above exercises evaluation plumbing, not a live model.

## Writing tests

Tests are standard-library `unittest` modules: catalog validators in `scripts/test_*.py`, everything else in `scripts/tests/`, each runnable as `python <file>` (the two P0 modules as `python -m unittest scripts.tests.<module>`). There is **no test discovery**: [validation CI](../.github/workflows/validate.yml) and the core block above list every file. Register a new test file in both, or it never runs. Code installed into consumers targets Python 3.8+, but the Python 3.8 job exercises only the generated runtimes and the release runtime; add a floor-sensitive test there when a change needs that evidence.

Exercise real Git repositories, the real installer and real symlinks in temporary directories. Mock only external services, as the release tests do for the `gh` publisher. Skip only for a missing platform capability, and state it in the skip reason. Assert observable behavior (bytes, exit codes, JSON reports, Git state), not the English wording of guidance; see [harness principles](harness-constraint-policy.md#choosing-guidance-and-machinery). A bug-fix regression should fail without its fix. Test-first work is not required repository-wide.

## Evaluation evidence

Choose the matching guide rather than treating every check as the same evidence:

| Question | Procedure and limit |
|---|---|
| Are manifests, adapter envelopes, and deterministic oracles sound? | Core regression tests and suite/result validation; no model-effectiveness claim |
| Does a configured model report the intended route/decision? | [Live routing probes](../evals/agent-skills/README.md); not native discovery or actual task execution |
| Does the Agent preserve/change the right artifacts? | [Task outcomes](../evals/tasks/README.md); compare matched no-skill, brief-request, and pinned-skill runs |
| Are meaning and reader navigation intact? | Source review and an optional cold read; not exact-file approval or an automatic gate |

Commit intended candidate/manifests before revision-pinned evaluation; uncommitted skill edits are not the treatment. Preserve unknown usage as unknown. Reference actions and mocked release publication test oracles and owned behavior, not live-host effectiveness or real publication.

### Optional skill-verifier

For substantive skill changes or uncertain evidence, pass the project `skill-verifier` the absolute task checkout, pinned revision, diff/dirty snapshot, scope, acceptance, and existing result paths. The parent captures those artifacts because the reviewer does not run shell commands. For example:

> Review this scaffold-guidance change at <revision> in <absolute-task-checkout> and the supplied results. Find regressions or assertions that accept a wrong output; return findings and proposed checks without modifying sources or executing commands.

[Instructions](../.agents/subagents/skill-verifier/instructions.md) and [metadata](../.agents/subagents/skill-verifier/metadata.json) are the role's source. Generate projections using `python .agents/tools/generate-subagents.py`; use `--check` for drift. The role is opt-in and project-owned, not a catalog/scaffold-consumer install or approval authority. Model and effort remain host-selected.

Claude's configured allowlist is Read/Grep/Glob; Codex requests `read-only`, but effective parent overrides must be checked. Neither configuration nor the no-execution instruction establishes live-host enforcement. The parent runs proposed checks in a separately authorized environment. Linked worktrees, separate clones, and temporary directories are not process sandboxes; filesystem/network/credential isolation must be effective when required. See [dated host evidence](compatibility.md#project-subagent-definitions-2026-09-22).

Use a fresh instance with only task, acceptance, and anonymized artifacts for an explicitly blind/cold-reader comparison. Do not reuse a source-review instance or claim blindness when project context leaks identities. Keep baseline/treatment execution separate from this evaluator. The parent evaluates findings and owns fixes and delivery.

## Scaffold testing conventions

Testing-quality guidance is established by the full scaffold skill and owned by the consumer
project. Test-first execution remains a scoped project/user choice, not a catalog dependency.
The testing-guidance fixture checks source-owned clauses, runner discovery arguments, links
and preservation of tests/coverage configuration. It does not infer prose quality from keywords
or prove live model effectiveness. Installer preservation and TDD RED/GREEN traces remain
separate checks; isolated payload/reference tests protect the retained scaffold installation.

## Scaffold project-guidance changes

The full skill must adopt and fill real project guidance during an authorized initialization
or upgrade, while the installer never guesses project layout or rewrites project-owned prose.
`test_project_conventions.py` executes the installer against doc/tool variants, generated and
external docs, customizations, read-only modes, repeated runs, and staged/dirty state.
The scaffold routing suite probes intended decisions; task-outcome fixtures inspect reachable
project guidance and rejection of stale/default routes. Reference actions validate those
oracles, not live Agent adaptation or host discovery. Do not treat installer `ok` as semantic
onboarding acceptance. Existing doc ownership in this repository already covers its layout;
update the owning pages rather than create a second scaffold manual.

## Generated files

Edit the [canonical source](architecture.md#source-and-generated-ownership), then run the owning generator:

```bash
python scripts/generate_workflow_runtimes.py
python scripts/generate_p0_runtimes.py
```

Run only the affected generator, review its diff, and rerun `--check` plus relevant behavior tests. For scaffold-owned runtime and contract updates, use the catalog `agent-scaffold` installer in `upgrade` mode, then `verify`. Project skill links and subagents use the relink/generator commands in the managed `AGENTS.md` block. Do not patch installed/generated files to hide drift.

## Installer checks

`skills@1.5.17` is the audited reproducibility pin, not an upstream-latest label. `add . -l` is a discovery-only check from the catalog task checkout. Actual install smoke tests run from a fresh consumer Git repository with the catalog path as their source; CI checks each installed file against source and rejects non-regular payload entries. Repeat against the remote source after publishing an intended discovery fix. Evaluate a newer CLI as an explicit dependency change rather than silently replacing the pin.

[Installer semantics](compatibility.md#installer-semantics) owns option scope and destructive-command warnings. In particular, inspect top-level `--help`; `add <source> --help` can execute an add flow. Never run project-scope removal from the catalog checkout.

## Release flow

This repository's completion boundary is a verified GitHub Release created by [release CI](../.github/workflows/release.yml), not a planner status or tag push.

Before any version bump, tag or publication, read the installed [release conventions](../.agents/tools/release/README.md). The repository-specific rules below win over their generic defaults.

1. Accumulate changes under Unreleased. Choose the exact supported tag and move its notes into one matching dated changelog section. The installer grouping manifest `.claude-plugin/plugin.json` has no release-version field; do not invent one for a release. Use Conventional Commits without `Co-Authored-By`, including squash-merge titles: the analyzer infers the bump from `main`'s commit subjects (a merge commit's merged commits, or a squash title).
2. Validate and merge the release snapshot, then verify main CI. Resolve the intended remote main and exact release commit; the workflow rejects tags whose commits are not reachable from `origin/main`.
3. Before tagging, run the analyzer with `--release-branch main` on a clean, attached `main` checkout equal to `origin/main`; a task worktree on another branch reports `release-line` attention by design. With release authorization, create and push an annotated `vX.Y.Z` or numbered `-alpha.N`, `-beta.N`, or `-rc.N` tag. Prerelease numbers start at 1. The workflow does not accept build metadata or arbitrary SemVer prerelease labels. Never move or recreate an existing tag.
4. Observe reusable validation, tag/commit checks, exact changelog extraction, and workflow-owned publication. Do not race it with a manual publisher.
5. Verify the release URL, tag/peeled commit, non-draft state, prerelease state, and body matching the tagged changelog. Report failed or unavailable evidence rather than declaring completion at push.

The [release analyzer](../.agents/tools/release/release-plan.py) is read-only scaffold runtime installed for the selected `release` domain. Its schema 2 `analyzed` status establishes only local supported-format analysis, not branch policy, publishability, or authorization. Pass `--release-branch` only from explicit repository policy and resolve attention before mutation. Documentation-only PRs do not bump the version, create tags, or publish releases.

Release CI calls the committed [changelog extractor](../.agents/tools/release/extract-changelog.py).
Edit the canonical sources under `skills/agent-scaffold/assets/runtime/release/`, then refresh
these copies with `agent-scaffold upgrade`; the scaffold gate rejects drift. Both helpers moved
from the retired skill without compatibility wrappers, and the planner and real-Git/mock-publisher
regressions still cover them. Local analysis:

```bash
python .agents/tools/release/release-plan.py --repo . --release-branch main --json
```

## Convention selection coverage

`test_guidance_selection.py` checks missing/legacy versus recorded/all/none state, proposed
read-only choices, explicit updates, invalid/symlinked input, write failure and unchanged-byte
reruns. Real installation verifies opt-outs, preservation, and the conditional terminology
block. A valid selection is a preference record, not proof of finished guidance or an actual
human dialogue; decision probes and task fixtures exercise those separate boundaries.
The CLI never reads stdin, and runtime-only callers must not manufacture an onboarding answer.
