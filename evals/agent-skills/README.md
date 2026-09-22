# Live Agent Skill evaluations

These are opt-in **routing and decision probes**, not task execution or native skill-discovery tests. The repository-local `host_adapter.py` uses the project `skill-eval` runtime and a configured Claude CLI. CI validates manifests and deterministic regressions; it does not run an authenticated model or establish effectiveness.

## Validate or execute

Run from the intended committed task checkout. Commit changed candidate/manifests first: evaluation pins inputs to Git, not an uncommitted editing session.

```bash
# Offline manifest validation; no model invocation
python .agents/skills/skill-eval/scripts/skill_eval.py validate evals/agent-skills/tdd/suite.json
```

Live execution is separate and may incur model usage. Configure and authenticate Claude Code, authorize the experiment, and set `CLAUDE_BIN` when it is not on `PATH`. From Bash/Git Bash:

```bash
(
  set -e
  result_dir="$(mktemp -d)"
  printf 'Retained evaluation output: %s\n' "$result_dir"
  python .agents/skills/skill-eval/scripts/skill_eval.py run \
    evals/agent-skills/tdd/suite.json --output "$result_dir/tdd-skill-eval.json"
  python .agents/skills/skill-eval/scripts/skill_eval.py validate-result \
    "$result_dir/tdd-skill-eval.json"
)
```

Keep the result even on failure. `validate-result` is a contract check, not a replacement for inspecting selection, task oracle, scope, completion, and cost together. A fake/rule-based adapter can test plumbing but cannot show that a skill improves model behavior.

## Adapter and comparison contract

The adapter implements `agent-skill-eval/v1`, invokes `claude` once per baseline/treatment request, and returns observations under `metadata.behavior`. It derives routes from the checked-out catalog, binds a selected treatment to its loaded candidate, and normalizes route/workflow vocabulary and behavior-key spelling. It does not manufacture decision fields from request heuristics or verifier expectations.

| Execution | Required selection behavior |
|---|---|
| Baseline | Never selects a candidate; receives no candidate instructions |
| Positive treatment | Selects its candidate |
| Negative/confusable treatment | Rejects its candidate |

Both executions must complete with valid selection/trigger and scope boundaries. An invalid baseline cannot produce a passing comparison; a valid isolated baseline that fails the task oracle can still be useful evidence.

Routes name shipped skills or `none` for host/project work; workflow labels describe intent independently. Candidate metadata and suite references must match the shipped catalog. Behavior keys use `snake_case`; share canonical workflow labels across adjacent suites. Expected objects are recursive subsets; expected array members must appear as complete JSON values, with order and extra members allowed. Booleans and numbers remain distinct, including in arrays.

## Decision and safety coverage

Current manifests are the case inventory. They cover whole-specification and digest approval, explicit test-first work, documentation/tooling decisions, selected Lark CLI use, and release boundaries. Observations target decision outcomes rather than incidental wording; explicit project-required records retain exact expectations.

Lark probes cover identity, ambiguous/contradictory results, fresh confirmation, CLI confirmation gates, untrusted instructions, and file containment. Negative fixtures test missing, unsafe, and wrong-typed observations. They verify the oracle/protocol, not real CLI operation or live model compliance. Historical coverage changes remain in the [September 20 audit](../../docs/audits/2026-09-20-native-first.md).

## Measurement and failure boundaries

Both the CLI response and decision response must be exactly one finite JSON object. Duplicate keys, normalized-key collisions, nonzero host exits, host-reported failures, missing usage, or malformed/non-integral usage cannot become completed runs. The candidate's final `SKILL.md` target must stay inside the pinned repository, including through symlinks.

`input_tokens` includes uncached input, cache reads, and cache creation. Prefer whole-call `modelUsage`, otherwise require complete `usage`; never add overlapping reports. This is token volume, not dollars. The interpretation follows [Claude cache usage](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) and [whole-call usage](https://code.claude.com/docs/en/agent-sdk/cost-tracking), reviewed 2026-09-06. Results predating that correction require matched baseline/treatment reruns, not relaxed budgets.

Wall time uses a monotonic clock around adapter invocation; the outer runner enforces its own measured lower bound. Local tools are disabled for the probe. Reported server-tool counts are overlapping observations, not a complete tool audit.

Failures retain available usage/time. `metadata.usage_available=false` means unknown usage: v1's numeric zero placeholders are **not free execution** and must not enter spend comparisons. Even reported failure usage may be incomplete after a crash. Error type/stage/host-exit fields support diagnosis without retaining raw output, credentials, or request text in results.

## What these probes do not prove

The model sees the candidate entry point, route/observation vocabulary, and request, but not the verifier's answers. It does not load on-demand references or execute the requested work. Selection binding means a treatment route is not an independent free-choice measurement. The baseline is not an old-version/new-version randomized trial.

TDD includes project-policy and non-trigger cases. Experiments retain the `prototype` workflow label but route to `none`; the catalog has no such skill. Retired composition/review suites do not measure the feedback/delivery guidance retained in the composition guide.

For observed edits, mock calls, test sequences, and a brief-request control, use [task outcomes](../tasks/README.md). Establish quality or efficiency gains with fixed old/new revisions, matched host/model/configuration/cache conditions, repeated representative tasks, and captured artifacts/verifiers. Correct stated intentions or green CI alone do not establish those gains.
