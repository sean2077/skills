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

Never edit the primary worktree directly. Its checked-out branch is the active trunk unless `--trunk` overrides it; the scaffold-managed rule and escape-hatch boundary in [AGENTS.md](../AGENTS.md#worktree-per-change-hard-rule) are authoritative.

```bash
bash .agents/tools/worktree.sh new docs-example
cd .worktrees/docs-example
# edit, validate, and commit here
wt="$(git rev-parse --show-toplevel)"
root="$(dirname "$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir)")"
cd "$root"
bash "$root/.agents/tools/worktree.sh" done --dir "$wt"
```

Leave the target worktree before invoking cleanup. This is required for reliable deletion on Windows, where the calling shell or Agent process may otherwise keep the directory open; `new` prints the exact outside-worktree command.

`done` is not a local-only cleanup command: the scaffold-managed contract defines it as merge-to-local-trunk, cleanup, and an ff-only push. Run it only when that publication step is intended.

Before editing, record the exact local active-trunk commit used to create the worktree. When publication is intended, also fetch and compare the corresponding remote trunk; replay the change if the target trunk advanced.

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

python scripts/generate_workflow_runtimes.py --check
python scripts/generate_p0_runtimes.py --check
python scripts/tests/test_oma_migration_workflows.py
python -m unittest -v scripts.tests.test_p0_agent_workflows
python -m unittest -v scripts.tests.test_p0_hardening

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
python skills/work-protocol/scripts/workctl.py risk --cross-session

for skill in skills/*; do
  [[ -d "$skill" ]] && python -m skills_ref.cli validate "$skill"
done
python -m skills_ref.cli validate .agents/skills/skill-eval

python scripts/tests/test_agent_scaffold_core.py
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
