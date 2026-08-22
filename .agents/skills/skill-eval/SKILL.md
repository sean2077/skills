---
name: skill-eval
description: Use in this repository when adding, changing, accepting, or benchmarking an Agent Skill and evidence is needed that it improves behavior without trigger leakage, scope violations, or unjustified cost.
metadata:
  internal: true
---

# skill-eval

Evaluate one skill against a fixed Git revision and fixture. This project-private Python 3.8+ standard-library runtime executes the same case as a baseline and treatment through a host adapter, then applies deterministic trigger, verifier, changed-path, comparability, and cost gates. It never calls a model by itself and never treats an LLM self-report as correctness evidence.

Invoke the repository-local entry point from the repository root:

```bash
python .agents/skills/skill-eval/scripts/skill_eval.py validate <suite.json>
python .agents/skills/skill-eval/scripts/skill_eval.py run <suite.json> --output <result.json>
python .agents/skills/skill-eval/scripts/skill_eval.py validate-result <result.json>
```

Use `python3` when that is the repository's Python 3 command, or `py -3` on Windows. The `metadata.internal: true` marker keeps the project skill out of the `skills` CLI's public discovery unless internal skills are explicitly enabled. This skill is part of the project harness and must not be added to the published catalog manifest or advertised as an install target.

## Evaluation loop

1. Pin one repository revision, immutable fixture, adapter contract, verifier contract, and scope contract. The runtime materializes the resolved commit as a clean detached worktree; commit a HEAD-targeting manifest before running.
2. Include positive, negative, and confusable cases. Positive treatment runs must select the skill; negative and confusable runs must not.
3. Run baseline and treatment from separate fixture copies. Baseline receives no skill path; treatment receives the declared skill path.
4. Let the adapter modify only its isolated fixture copy. The runtime independently computes changed paths, rejects escaping symlinks, and fails if the adapter mutates any other repository path.
5. Run a read-only deterministic verifier. Any verifier mutation of the fixture or surrounding repository is a protocol failure.
6. Compare only compatible pairs. Correctness must pass before absolute or relative token, tool-call, time, and intervention budgets are considered.
7. Keep the result JSON as CI evidence; add or revise a skill only when the measured result justifies its routing and context cost.

## Hard rules

- Commands are argv arrays executed with `shell=False`, a reduced environment, bounded output, and a timeout.
- Fixture paths and command arguments may not escape the repository; fixture symlinks are rejected. A repository snapshot digest makes baseline/treatment environment drift incomparable.
- Do not hide failed trigger, verifier, or scope checks behind a lower cost score.
- Do not put credentials in a manifest, adapter response, verifier response, or retained run.
- Treat an adapter as trusted executable code; run untrusted agents inside the host's own sandbox.

## On-demand references

- Read [evaluation contract](references/evaluation-contract.md) only when authoring an adapter, verifier, suite manifest, CI gate, or result consumer.
