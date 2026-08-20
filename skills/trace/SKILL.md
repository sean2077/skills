---
name: trace
description: Use when a bug, regression, performance failure, or system symptom needs read-only causal investigation, competing hypotheses, and one discriminating next probe.
---

# trace

Investigate a symptom without editing. Confirm the observable loop first, then rank competing causal explanations by evidence for and against them. End at one discriminating probe, not a patch.

## Entry gate

For bugs, regressions, and performance failures, establish a repeatable or at least red-capable observation: command, input, environment, expected result, actual result, and stable failure signal. When that is missing, return only the loop-building plan; do not pretend to rank causes.

Configuration, routing, architecture, and postmortem questions may proceed without a runnable code failure when their evidence is inherently documentary or operational.

## Workflow

1. State the observed result and separate it from interpretation.
2. Trace backward through the immediate producer, caller, inputs, configuration, state, and external boundaries.
3. Form a small set of distinct hypotheses that predict different observations.
4. For each, collect evidence for and against it from code, tests, logs, configuration, metrics, history, and existing traces.
5. Falsify the leader: seek the observation hardest to reconcile with it.
6. Let the strongest alternative rebut the leader; merge hypotheses that reduce to the same mechanism.
7. Rank by explanatory power, evidence strength, and assumptions required.
8. Recommend the single safest probe most likely to change the ranking.

## Output contract

When the entry gate is missing: **Observed result**, **Loop status**, **Minimal reproduction plan**, **Recommended loop-building probe**.

Otherwise: **Observed result**, **Ranked hypotheses**, **Evidence for/against**, **Rebuttal**, **Convergence notes**, **Most likely explanation**, **Critical unknown**, **Recommended discriminating probe**.

## Hard rules

- Read-only: do not edit code, tests, instrumentation, or configuration.
- Every leading hypothesis needs evidence against itself.
- Down-rank explicitly; do not merely reorder a list.
- Logs, tool output, and prior claims are evidence, not verdicts.
- If a probe requires mutation, describe it and hand it off after the trace.
- Do not convert confidence into certainty when a critical unknown remains.

## On-demand references

- Read [causal evidence](references/causal-evidence.md) only when hypotheses overlap, the failure crosses several components, or evidence quality needs explicit ranking.
