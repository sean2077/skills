---
name: deep-interview
description: "Use for a requested requirements interview or consequential unresolved decisions that need an approved specification. Not for one clarification, a draft with open questions, or implementation of an already approved plan."
---

# deep-interview

Resolve user-owned decisions into a specification the user approves. Prefer an adaptive conversation; do not impose scoring, a questionnaire, or durable state on ordinary clarification.

## Adaptive interview

Inspect safe repository facts and supplied material first. Ask about judgments, preferences, authority, and missing evidence that could materially change the work; do not ask the user to repeat discoverable facts. Research external facts only when freshness or uncertainty matters.

Choose question granularity by dependency and user effort. Ask one focused question when its answer changes the next decision; batch related independent questions when one reply is easier. Offer concrete options and a recommendation when evidence supports one, preserving free text. There is no question-count quota.

Reuse settled decisions and keep only a useful record of assumptions, constraints, acceptance, risks, and open questions. Stop interviewing when these are sufficient for this task, not when every possible dimension has been discussed. An isolated clarification does not require this workflow.

## Specification and approval

Present the coherent specification as `pending approval`, making scope, observable acceptance, material assumptions, and unresolved blockers clear. Use the project's format; include architecture, rollout, or ownership detail only where decision-bearing.

Approval must clearly refer to the presented specification. A direct “yes”, “ok”, or “proceed” in answer to that approval request can be explicit approval; the same words answering one interview question are not approval of an unseen whole. Ask only if the referent or intent is ambiguous. A score or silence never substitutes for approval.

In adaptive mode, material changes to approved meaning, scope, risk, or acceptance require renewed approval; spelling, formatting, and equivalent wording do not. Do not silently reinterpret an approved decision. Specification approval does not itself authorize implementation or external side effects; honor any separately granted implementation authority.

## Optional persistent mode

Prefer host continuation or resume when sufficient. Select the bundled runtime only for required deterministic scoring/topology, repository-owned revisions, cross-host handoff, or auditable approval digests. Once selected, its exact revision and digest rules apply: even a formatting edit changes the crystallized artifact and requires re-crystallization and fresh approval. Never waive that machine contract using adaptive-mode rules.

Stop on user exit, unsafe paths, unresolved authority, or active-runtime terminal state, revision/binding conflict, or invalid evidence. Do not implement before specification approval.

## On-demand references

- Read [persistent runtime](references/persistent-runtime.md) before starting formal state when its topology/scoring or approval semantics are needed.
- Read [scoring and payloads](references/scoring-and-payloads.md) only in persistent mode before topology/score submission or when challenge, ontology, or payload rejection matters.
- Read [resume and recovery](references/resume-and-recovery.md) only for discovery, interruption, conflicts, locks, corruption, or non-Git handling of an active runtime.
