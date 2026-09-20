# Causal evidence

Read this when hypotheses overlap, reproduction is weak, a failure crosses components, or evidence quality needs explicit ranking; an obvious, directly evidenced cause needs no extra hypothesis exercise.

## Entry gate

Do not name a root cause merely because one explanation is plausible.

- Establish a reliable reproduction or state precisely what is missing.
- When no useful reproduction exists, produce a minimal reproduction plan before ranking causes.
- State the observed result separately from the expected result and from any prior interpretation.

## Distinct hypotheses

Keep only genuinely distinct hypotheses while evidence permits; there is no minimum or target count. Two labels are distinct only when they imply different observations or probes; merge explanations that reduce to the same state transition or ownership defect.

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

When hypotheses compete, choose a safe probe whose outcomes distinguish them and state the predictions. When only one supported mechanism remains, verify its critical prediction instead of inventing alternatives.

For multi-component failures, probe one boundary at a time and capture request/input, identity, relevant state, response/output, timing, and retry/cancellation context. Avoid broad logging that creates noise or leaks secrets.

If the best probe requires mutation, instrumentation, or an external side effect, describe it and hand it off after the read-only investigation.

## Present the conclusion

Report the observed symptom, best-supported mechanism, evidence, and material unknowns. Without a useful reproduction, identify the missing evidence and a feasible reproduction or discriminating probe. Use a ranked table only when alternatives remain; omit empty headings and a next-probe ritual after the question is resolved.
