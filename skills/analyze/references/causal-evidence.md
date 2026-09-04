# Causal evidence

Read this when causal-investigation mode is selected, hypotheses overlap, a failure crosses several components, or evidence quality needs explicit ranking.

## Entry gate

Do not name a root cause merely because one explanation is plausible.

- Establish a reliable reproduction or state precisely what is missing.
- When no useful reproduction exists, produce a minimal reproduction plan before ranking causes.
- State the observed result separately from the expected result and from any prior interpretation.

## Distinct hypotheses

Keep two to four genuinely distinct hypotheses while evidence permits. Two labels are distinct only when they imply different observations or probes; merge explanations that reduce to the same state transition or ownership defect.

For each leading hypothesis record:

- the mechanism it predicts;
- evidence for it;
- evidence against it;
- the observation that would falsify or materially down-rank it.

Down-rank explicitly when evidence conflicts. Do not merely reorder a list.

## Evidence hierarchy

In causal mode, prefer controlled reproduction and minimized counterexample; then direct state or trace at the failing boundary; executable code and configuration; focused tests; correlated logs or metrics; documentation; history; intuition.

Correlation can locate a boundary without proving mechanism. A test may prove one path and say nothing about the observed environment.

## Discriminating probe

Choose the safe probe with the highest expected information gain: at least two leading hypotheses should predict different outcomes. State those predictions before running or recommending it.

For multi-component failures, probe one boundary at a time and capture request/input, identity, relevant state, response/output, timing, and retry/cancellation context. Avoid broad logging that creates noise or leaks secrets.

If the best probe requires mutation, instrumentation, or an external side effect, describe it and hand it off after the read-only investigation.

## Output contract

Without a reproduction, report: **Observed symptom**, **Critical missing evidence**, **Minimal reproduction plan**, and **Recommended discriminating probe**.

With useful evidence, report: **Observed result**, **Ranked hypotheses**, **Evidence for/against**, **Most likely mechanism**, **Critical unknown**, and **Recommended discriminating probe**.
