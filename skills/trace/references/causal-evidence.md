# Causal evidence

Read this only when hypotheses overlap, a failure crosses several components, or evidence quality needs explicit ranking.

## Evidence hierarchy

Prefer controlled reproduction and minimized counterexample; then direct state/trace at the failing boundary; executable code and configuration; focused tests; correlated logs/metrics; documentation; history; intuition.

Correlation can locate a boundary without proving mechanism. A test may prove one path and say nothing about the observed environment.

## Distinct hypotheses

Two hypotheses are distinct only when they imply different observations or probes. Merge labels that reduce to the same state transition or ownership defect. Keep separate explanations that require different conditions even when they share a symptom.

## Discriminating probe

Choose the probe with the highest expected information gain under safe cost: it should make at least two leading hypotheses predict different outcomes. State both predictions before running or recommending it.

For multi-component failures, probe one boundary at a time and capture request/input, identity, relevant state, response/output, timing, and retry/cancellation context. Avoid broad logging that creates noise or leaks secrets.
