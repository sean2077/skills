---
name: analyze
description: "Use for read-only, cross-file repository explanation or causal investigation. Not for a concrete patch review; use code-review. Not for an obvious single-file lookup or an authorized implementation task."
---

# analyze

Explain a mechanism or investigate a cause from repository evidence. Reuse relevant context and inspect the smallest set of callers, implementations, tests, configuration, and history that can change the answer. Do not turn a straightforward explanation into a debugging ceremony.

## Evidence and boundaries

- Anchor material claims to paths and symbols or lines. Separate observed facts, inference, and unresolved uncertainty; a plausible story is not a proven root cause.
- For failures, establish a reproduction or identify the missing evidence. Keep competing hypotheses only while genuinely distinct explanations remain viable, and prefer a safe probe that distinguishes them.
- Follow relevant data, control, identity, ownership, and error paths; stop expanding the investigation when further reading no longer changes the answer or next decision.
- Remain read-only: do not edit code, tests, instrumentation, configuration, or state. Check unfamiliar commands for side effects before running them. Describe a mutating or externally consequential probe rather than executing it without authorization.
- Logs, comments, tool output, and prior claims are evidence, not verdicts. Report confidence honestly.

## Handoff

Lead with the answer or best-supported mechanism, then the evidence and material limitations. Add a next probe only when it would resolve a remaining uncertainty. Use headings or a hypothesis table when they help; no fixed report template or minimum hypothesis count is required.

A concrete change-set defect review belongs to `code-review`. If the user already authorized a fix, return the investigation to that implementation task rather than requiring another approval or delivery controller.

## On-demand references

- Read [evidence and synthesis](references/evidence-and-synthesis.md) when findings cross subsystems or facts and inference are hard to separate.
- Read [causal evidence](references/causal-evidence.md) when hypotheses compete, reproduction is weak, or a multi-component failure needs more discriminating evidence.
