---
name: deep-interview
description: Use when a vague or consequential idea needs an adaptive interview and an explicitly approved specification before implementation; use deterministic scoring state only when persistence or auditability adds value.
---

# deep-interview

Turn uncertainty into a specification the user explicitly approves. Default to an adaptive interview driven by model judgment and inspected evidence; persistent formal scoring is optional rather than the default tax on every vague request.

## Choose the interview mode

Use the adaptive interview by default for one-session product, engineering, or workflow clarification.

Use the persistent runtime only when at least one condition is material:

- the interview must survive context resets, sessions, worktrees, or handoffs;
- a regulated, high-risk, or disputed decision needs auditable revisions and approval digests;
- several independently successful components make formal topology and gap scoring useful;
- the user explicitly asks for deterministic scoring, resumability, or durable receipts.

## Adaptive interview

1. Inspect safe repository facts and supplied material before asking the user to repeat discoverable information. Consult current primary sources only when external or time-sensitive facts can materially change a decision.
2. Keep a compact ledger of decisions, assumptions, constraints, acceptance examples, risks, owners, and open questions. Do not narrate a heavyweight state machine.
3. Choose question granularity by dependency and user effort. Default to one to three related decision-bearing questions, but treat that range as a usability heuristic, not a ceiling. Ask one focused question when its answer may change the next question or the decision needs depth. Batch more than three only when the questions are independent, low-effort, and one structured reply is clearly easier—especially for explicit intake/checklist requests or a stated preference to minimize turns. Never dump a long or unrelated questionnaire merely to reduce round trips.
4. Offer concrete options and a recommendation when evidence supports one while preserving free text. For multi-question batches, add a compact answer template when it reduces effort.
5. Adapt depth to consequence and uncertainty. Skip low-value dimensions, but label material assumptions instead of silently deciding them.
6. Continue until the goal and users, scope and non-goals, key constraints, decision ownership, acceptance evidence, and material risks are resolved enough for this task.

## Specification and approval gate

Write a coherent specification marked `pending approval`, including the resolved goal, scope/non-goals, behavior or topology where relevant, constraints, decision boundaries, acceptance criteria, assumptions, risks, rollout/rollback when material, and remaining gaps.

Ask the user to review the whole specification. Only explicit approval of that specification clears the gate; a casual “ok”, an answer to the latest question, or a score does not. Changed specification content invalidates prior approval. Completion of the interview does not authorize implementation.

When persistent runtime mode is selected, read its control-plane reference before starting state. Formal scores never override an explicit blocker, risk, owner decision, or approval boundary.

## Hard rules

- Discover safe facts yourself; reserve user turns for judgments, authority, preferences, and unresolved evidence.
- Stop on user exit, terminal state, binding or revision conflict, unsafe path, invalid evidence, or unresolved authority.
- Do not begin implementation before explicit specification approval.

## On-demand references

- Read [persistent runtime](references/persistent-runtime.md) only when deterministic topology/scoring, resumability, revisions, or approval digests are materially useful.
- Read [scoring and payloads](references/scoring-and-payloads.md) only after runtime mode is selected, before the first topology/score submission, or when challenge, ontology, or payload rejection matters.
- Read [resume and recovery](references/resume-and-recovery.md) only after runtime mode is active and discovery, interruption, mismatch, conflict, lock, corruption, or non-Git root handling is needed.
