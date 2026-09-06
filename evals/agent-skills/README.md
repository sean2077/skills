# Live Agent Skill evaluations

These suites measure routing and decision behavior for changed skills through the existing `skill-eval` runtime. Their adapter is the repository-local `evals/agent-skills/host_adapter.py`; CI validates every manifest but does not claim a behavioral pass without a configured model host.

The adapter implements `agent-skill-eval/v1`, invokes the local `claude` CLI once per baseline or treatment request as a read-only decision probe, reports usage metrics, and returns the observation under `metadata.behavior`. It derives catalog routes from the checked-out `skills/` tree, binds a selected treatment to its loaded candidate and normalizes route/workflow vocabulary and behavior-key spelling, and never manufactures task-specific decision fields from prompt heuristics or `case.metadata.expected_behavior`. Set `CLAUDE_BIN` when `claude` is not on `PATH`; Claude Code must be installed and authenticated before a live run.

The shared verifier checks adapter completion and selection separately from behavior: baseline is never selected, a positive treatment must select its candidate, and negative/confusable treatments must reject it. Expected objects remain recursive subsets; expected array members must occur as complete JSON values (order and extra members are allowed). Booleans are distinct from numbers, including inside arrays. Adapters may report additional observations without coupling suites to one host's prose. A fake or rule-based adapter can exercise protocol plumbing but is not evidence that a skill improves model behavior.

Behavior keys use `snake_case`. Workflow values come from the adapter's canonical vocabulary; adjacent suites should use the same label for the same user intent rather than defining candidate-local synonyms.

Run a configured suite from a committed revision:

```bash
python .agents/skills/skill-eval/scripts/skill_eval.py validate evals/agent-skills/analyze/suite.json
python .agents/skills/skill-eval/scripts/skill_eval.py run evals/agent-skills/analyze/suite.json --output /tmp/analyze-skill-eval.json
python .agents/skills/skill-eval/scripts/skill_eval.py validate-result /tmp/analyze-skill-eval.json
```

On Windows, use a temporary output path and the same commands from PowerShell. The adapter is not a public package and is not installed into a user-level bin directory.

Review treatment selection, verifier results, scope, and cost together. Both executions must complete with valid selection/trigger and scope boundaries; an invalid baseline cannot yield a passing comparison. A completed, correctly isolated baseline may still fail the task oracle. Do not accept a routing change merely because the manifest validates or an offline adapter can reproduce the expected JSON.

## Measurement and failure boundaries

The adapter requires exactly one finite JSON object from both the CLI and its decision response. Duplicate JSON keys, colliding normalized behavior keys, nonzero host exit, host-reported failure, missing usage, and malformed/non-integral usage cannot become a completed run. A candidate directory's final `SKILL.md` target must remain inside the pinned repository even through a symlink.

`input_tokens` counts uncached input plus cache reads and cache creation. Prefer whole-call `modelUsage` when available, otherwise require complete `usage`; never add both overlapping reports. This is token volume, not a dollar-cost estimate. The meanings follow the [Claude cache usage contract](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) and [whole-call usage guidance](https://code.claude.com/docs/en/agent-sdk/cost-tracking), checked 2026-09-06. Historical results produced before this correction are not directly comparable: rerun both baseline and treatment rather than loosening budgets to hide the changed measurement.

Wall time is measured with a monotonic clock around the adapter invocation, not copied from API duration; the outer runner also enforces its independently measured lower bound. Local tools are disabled for this routing probe; reported server-tool counts are overlapping observations, not a general tool-usage audit.

Failed envelopes preserve available host usage and elapsed time. `metadata.usage_available=false` identifies unknown usage: the numeric zero fields are required v1 placeholders, **not proof of free execution**. Do not aggregate such runs into spend comparisons. `error_type`, `error_stage`, and `host_exit_code` aid diagnosis without copying raw output, credentials, or request text into results. Even available failure usage may be incomplete after a host crash.

## What these probes do not prove

The host receives the candidate entry-point text, a vocabulary of routes/observations, and a request, but not the verifier's expected answers. It does not load on-demand references, execute the requested implementation, or reproduce the host's native skill discovery. Baseline has no candidate instructions; it is a diagnostic comparison, not an old-version/new-version randomized trial. Selection binding also means the reported treatment route is not an independent free-choice route measurement.

The composition cases cover approved-plan reuse, avoiding nested controllers, PR readback, and honest self-review; the review cases cover received feedback, revision freshness, and missing specifications; TDD cases include project policy and non-trigger boundaries. These are structured intention probes. A model can state the right intention and still fail actual work. Establish delivery or token-efficiency gains separately with fixed old/new revisions, matched host/model/configuration, repeated representative tasks, observed edits/verifiers, and comparable cache conditions. CI validates manifests and deterministic regressions only; no live-host efficacy claim follows from that pass.
