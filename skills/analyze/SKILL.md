---
name: analyze
description: "Use for read-only, cross-file repository explanation or causal investigation. Not for a concrete patch review; use code-review. Not for an obvious single-file lookup or an authorized implementation task."
---

# analyze

Explain a mechanism or investigate a cause from repository evidence.

Inspect relevant callers, implementations, tests, configuration, and history. Follow data, control, identity, ownership, and error paths that could change the answer.

For failures, establish a reproduction or identify the missing evidence. Compare viable explanations using a safe probe that distinguishes them. Narrow the investigation as evidence resolves uncertainty.

Anchor material claims to paths and symbols or lines. Separate observations, inference, and unresolved questions; logs and prior claims need corroboration just like other evidence.

Keep the investigation read-only. Check unfamiliar commands for side effects, and obtain authorization before executing a mutating or externally consequential probe.

Lead with the best-supported answer, then its evidence and limits. Suggest a next probe where it could resolve a material uncertainty. Return findings to any already-authorized implementation task.

## References

- [Evidence and synthesis](references/evidence-and-synthesis.md): cross-subsystem findings and distinctions between facts and inference.
- [Causal evidence](references/causal-evidence.md): competing hypotheses, weak reproductions, and multi-component failures.
