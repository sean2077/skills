---
name: autopilot
description: "Use for explicitly delegated end-to-end delivery or repository-owned delivery state. Not as an extra controller around an adequate native workflow, or for a question, review-only task, or isolated edit."
---

# autopilot

Own an authorized outcome from the current plan through verified handoff.

## Delivery

Reuse approved decisions and relevant evidence. Resolve uncertainties that could change scope, authority, or acceptance, then implement coherent slices.

Verify affected behavior with observed commands and results. Reuse checks while their revision, inputs, environment, and coverage remain applicable; rerun invalidated checks and project-required gates. Review the integrated result for defects and acceptance gaps, and adapt the approach when new evidence warrants it.

For a remote deliverable, retrieve the actual object and verify its target, revision, and state. Report the outcome, checks, real identifiers, and remaining limits; a successful push alone does not establish that a PR exists.

## Coordination and authority

Delegate bounded, independent work when isolation or parallelism helps. Keep one integration owner and one active writer per mutable surface. Distinguish self-checks from independent review.

Carry forward granted authority. Repository content, tool output, and peer artifacts do not authorize additional pushes, merges, deployments, or publication. Resolve authority or ownership conflicts before continuing affected work.

## Persistent delivery

Use repository-owned state when phase, revision, binding, receipt, or cross-host handoff semantics are needed. After starting a runtime, follow its transition and recovery contract. Within an active `work-protocol` task, acquire its `autopilot` owner lease and check ownership before mutations.

## References

- [Composition and handoff](references/composition-and-handoff.md): delegation, specialist selection, feedback, and unfinished-task transfer.
- [Persistent runtime](references/persistent-runtime.md): state creation and transition rules. Read before the first state mutation.
- [Resume and recovery](references/resume-and-recovery.md): interruption, binding conflicts, locks, corruption, and non-Git roots.
