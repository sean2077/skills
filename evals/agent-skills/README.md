# Live Agent Skill evaluations

These suites measure routing and decision behavior for changed skills through the existing `skill-eval` runtime. They require an executable named `agent-skill-host-adapter` on `PATH`; CI validates every manifest but does not claim a behavioral pass without a configured model host.

The adapter implements `agent-skill-eval/v1`, invokes the real host once per baseline or treatment request as a read-only decision probe, reports exact available metrics, and returns its normalized observation under `metadata.behavior`. It must derive that observation from the host result, not copy `case.metadata.expected_behavior`, even though the trusted adapter receives the complete case envelope. The prompts describe realistic work, but the suite measures routing and control-plane choice rather than authorizing the adapter to perform that work.

The shared verifier treats each mode's expected behavior as a required recursive subset, so adapters may report additional observations without coupling suites to one host's prose. A fake or rule-based adapter can exercise protocol plumbing but is not evidence that a skill improves model behavior.

Run a configured suite from a committed revision:

```bash
python .agents/skills/skill-eval/scripts/skill_eval.py validate evals/agent-skills/analyze/suite.json
python .agents/skills/skill-eval/scripts/skill_eval.py run evals/agent-skills/analyze/suite.json --output /tmp/analyze-skill-eval.json
python .agents/skills/skill-eval/scripts/skill_eval.py validate-result /tmp/analyze-skill-eval.json
```

Review treatment selection, verifier results, scope, and cost together. Do not accept a routing change merely because the manifest validates or an offline adapter can reproduce the expected JSON.
