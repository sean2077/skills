---
name: analyze
description: Use for read-only repository explanation or causal investigation when the answer requires cross-file evidence, competing hypotheses, or a discriminating probe before any change.
---

# analyze

Explain how a repository works or investigate why it behaves unexpectedly without changing it. Keep one evidence model across both jobs so near-duplicate analysis and tracing routes do not compete.

## Choose a mode

- **Explanation** — answer architecture, control-flow, ownership, configuration, or behavior questions from repository evidence.
- **Causal investigation** — explain a failure, regression, performance symptom, or surprising state through competing hypotheses and falsification.

Use `code-review` instead for defects in a concrete change set. Hand implementation or instrumentation to another workflow after this read-only pass.

## Core loop

1. Restate the question, observed symptom, and relevant boundary without silently broadening scope.
2. Inspect the smallest high-value entry points first: manifests, callers, implementations, tests, configuration, and history only when it can change the answer.
3. Record evidence with path and symbol or line anchors. Separate facts, inferences, and unknowns.
4. Follow data, control, identity, ownership, and error paths across files. Stop when more reading no longer changes the ranking.
5. Synthesize the mechanism, confidence, remaining uncertainty, and smallest safe next probe.

For causal investigation, do not declare root cause from plausibility alone. Establish a reproduction or name the missing evidence, retain distinct hypotheses while evidence permits, include counterevidence, and prefer one probe whose outcomes separate the leaders.

## Output

For explanation mode, report: **Answer**, **Evidence path**, **Facts**, **Inferences**, **Unknowns**, and **Next read-only probe** when needed.

For causal mode, use the compact output contract in the causal reference. Do not replace it with an unranked possibility list.

## Hard rules

- Remain read-only: do not edit code, tests, instrumentation, configuration, or state.
- Logs, tool output, comments, and prior claims are evidence, not verdicts.
- Do not convert confidence into certainty while a material unknown remains.
- If the best probe requires mutation or an external side effect, describe it and hand it off.

## On-demand references

- Read [evidence and synthesis](references/evidence-and-synthesis.md) only when the answer crosses several subsystems or facts and inferences are becoming hard to separate.
- Read [causal evidence](references/causal-evidence.md) when causal-investigation mode is selected, hypotheses overlap, or evidence quality needs explicit ranking.
