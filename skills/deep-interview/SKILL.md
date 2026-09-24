---
name: deep-interview
description: "Use for a requested requirements interview or consequential unresolved decisions that need an approved specification. Not for one clarification, a draft with open questions, or implementation of an already approved plan."
---

# deep-interview

Turn unresolved requirements into a coherent specification the user approves.

## Interview

Inspect the supplied material and relevant repository facts. Focus questions on decisions the user owns and uncertainty that could change scope, constraints, or acceptance.

Choose questions by their dependencies: ask one when its answer determines the next decision, or group independent questions when that is easier to answer. Offer concrete options and an evidence-backed recommendation while leaving room for another answer.

Carry settled decisions forward. Keep useful assumptions, constraints, risks, and open questions visible, and conclude the interview when the specification is sufficient for the task.

## Specification and approval

Present scope, observable acceptance, material assumptions, and unresolved blockers in the project's format. Confirm approval of the specification as a whole before implementation; an answer to one interview question approves only that decision.

For conversational specifications, reconfirm material changes to approved scope, meaning, risk, or acceptance. Carry forward separately granted implementation authority; specification approval alone does not authorize external side effects.

## Persistent sessions

Use host continuation or the bundled runtime according to the required handoff and audit semantics. The optional runtime records specification revisions, exact-file digests, and explicit approval; the conversation owns questions and readiness. Stored artifacts follow its exact revision and approval rules: any byte change to an approved file, even whitespace or line endings, needs re-crystallizing and fresh approval.

## References

- [Persistent runtime](references/persistent-runtime.md): setup, transitions, crystallization, and artifact approval. Read before creating runtime state.
- [Resume and recovery](references/resume-and-recovery.md): discovery, interruption, revision conflicts, locks, corruption, and non-Git roots.
