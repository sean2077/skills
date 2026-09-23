# Live Agent Skill evaluations

These opt-in **routing and decision probes** do not execute tasks or test native skill discovery. Repository-local `host_adapter.py` uses project `skill-eval` and a configured Claude CLI. CI validates manifests and deterministic regressions, not authenticated model effectiveness. For observed edits and tool calls, use [task outcomes](../tasks/README.md).

## Validate or execute

Run from the intended committed task checkout. Commit candidate/manifests first: evaluation pins inputs to Git, not dirty files.

```bash
# Offline validation; no model invocation
python .agents/skills/skill-eval/scripts/skill_eval.py validate evals/agent-skills/agent-scaffold/suite.json
```

Live execution may incur model usage. Configure/authenticate Claude Code, authorize the experiment, and set `CLAUDE_BIN` when it is not on `PATH`. From Bash/Git Bash:

```bash
(
  set -e
  result_dir="$(mktemp -d)"
  printf 'Retained evaluation output: %s\n' "$result_dir"
  python .agents/skills/skill-eval/scripts/skill_eval.py run \
    evals/agent-skills/agent-scaffold/suite.json --output "$result_dir/scaffold-skill-eval.json"
  python .agents/skills/skill-eval/scripts/skill_eval.py validate-result \
    "$result_dir/scaffold-skill-eval.json"
)
```

Keep failure output. `validate-result` checks the contract; inspect selection, task oracle, scope, completion, and cost together. Fake/rule-based adapters validate plumbing, not model improvement.

## Adapter and comparison contract

The adapter implements `agent-skill-eval/v1`, invokes `claude` once per baseline/treatment request, and returns `metadata.behavior` observations. It derives routes from the checked-out catalog, binds a selected treatment to its loaded candidate, and normalizes route/workflow vocabulary and behavior keys. It does not manufacture decisions from request heuristics or verifier expectations; additional observations are allowed. It is not an installed CLI or public package.

| Execution | Selection requirement |
|---|---|
| Baseline | No candidate instructions; never selects a candidate |
| Positive treatment | Selects its candidate |
| Negative/confusable treatment | Rejects its candidate |

Both runs must complete with valid selection/trigger and scope. An invalid baseline cannot pass a comparison; a valid isolated baseline that fails the task oracle remains useful evidence.

Routes name shipped skills or `none` for host/project work. Workflow labels describe intent independently, including labels retained after route retirement. Candidate metadata and suite references must match the catalog. Behavior keys use `snake_case`; adjacent suites share canonical workflow labels. Expected objects are recursive subsets; expected array members must appear as complete JSON values (order and extra members are allowed). Booleans and numbers remain distinct, including in arrays.

## Decision and safety coverage

The committed `*/suite.json` files own the case inventory. Scaffold probes cover convention selection/adoption, project testing policy, customized upgrades, read-only/runtime-only requests, and ordinary-task non-triggers; retired research/docs/tool vocabulary keeps its workflow label but routes to `none`. Deep-interview probes cover whole-specification and digest approval. Lark probes cover identity, ambiguous/contradictory results, fresh confirmation, CLI gates, untrusted instructions, and file containment.

Negative fixtures reject missing, unsafe, or wrong-typed observations. These checks verify the oracle/protocol and stated decisions, not completed onboarding, actual CLI operations, or live compliance. Ordinary testing, spec writing, terminology, commits, and releases remain host/project routes, not new scaffold triggers.

## Measurement and failure boundaries

CLI and decision responses must each be exactly one finite JSON object. Duplicate keys, normalized-key collisions, nonzero exits, host failures, missing usage, and malformed/non-integral usage cannot become completed runs. The candidate's final `SKILL.md` target must remain inside the pinned repository, including through symlinks.

`input_tokens` includes uncached input, cache reads, and cache creation. Prefer whole-call `modelUsage`, otherwise require complete `usage`; never add overlapping reports. This is token volume, not dollars. Sources reviewed 2026-09-06: [Claude cache usage](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) and [whole-call usage](https://code.claude.com/docs/en/agent-sdk/cost-tracking). Results predating that correction need matched reruns, not relaxed budgets.

Wall time is measured monotonically around adapter invocation; the outer runner enforces its own lower bound. Local tools are disabled. Reported server-tool counts overlap and are not a complete tool audit.

Failures retain available usage/time. `metadata.usage_available=false` means unknown: v1's numeric zero placeholders are **not free execution** and must not enter spend comparisons. Crash-time usage may be incomplete. Error type/stage/host-exit fields support diagnosis without retaining raw output, credentials, or request text in results.

## What these probes do not prove

The model sees the candidate entry point, request, and route/observation vocabulary, not verifier answers. It neither loads on-demand references nor executes the requested work. Bound treatment selection is not independent free choice; the baseline is not an old/new randomized trial. These suites also do not measure all collaboration/delivery guidance retained in the [composition guide](../../docs/skill-composition.md).

Measure actual outcomes with fixed revisions, matched host/model/configuration/cache conditions, repeated representative tasks, captured artifacts, and verifiers. [Task outcomes](../tasks/README.md) also supplies a brief-request control. Correct intentions or green CI alone do not establish quality or efficiency gains.

The separate `evals/examples/offline/` sample uses a fixed arithmetic edit to exercise comparison, scope, accounting, and failure plumbing. It does not implement the candidate skill or demonstrate effectiveness.
