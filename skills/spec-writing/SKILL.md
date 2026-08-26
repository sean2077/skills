---
name: spec-writing
description: Write or revise human-facing requirements and architecture/solution documents so final decisions and material implementation choices are clear, concise, and non-redundant, with recommendations in the document and discussion history in separate decision records.
---

# Human-facing Specification Writing

Shape requirements and solution documents for readers who need to understand the intended behavior, architecture, interfaces, and acceptance result. This skill complements repository-specific evidence or contract-review skills; it does not choose product behavior or replace an approval process.

## Separate reader content from working history

- Write the settled goal, scope, responsibilities, behavior, interfaces, and acceptance results in the main document.
- Do not copy interview notes, abandoned names, unresolved debate, approval choreography, or author self-justification into the main document.
- Keep decisions that affect future implementation in a short ADR or decision record: decision, reason, alternatives, impact, and revisit condition.
- If a historical choice is needed for compatibility or migration, state the resulting behavior and link the decision record; do not reconstruct the discussion.

## Keep the document easy to scan

- Start with the outcome and the problem it solves. Introduce architecture and flows before detailed fields.
- Define each important concept once. Use a short cross-reference instead of repeating a definition, table, or failure rule.
- Prefer positive, normative statements describing what the system does. Include a negative boundary only when it prevents a real safety, compatibility, ownership, or acceptance mistake.
- Keep non-goals short and business-relevant. Absence of a topic already means it is outside the document's scope.
- Explain an internal term at first use or replace it with a domain term that readers can understand.

## Present material choices for review

- When an implementation or technology choice can change behavior, compatibility, reliability, security, operations, cost, or schedule, include a concise options-and-recommendation section in the same human-facing document.
- Compare only viable, decision-bearing options against explicit criteria. A small table should show the option, relevant benefits, trade-offs or risks, and the recommended choice; record the decision status and owner when it is still open.
- Describe the selected option and resulting behavior in the main document. Keep exhaustive alternatives, historical debate, and detailed rationale in a linked decision record; do not enumerate trivial or speculative branches.

## Route detail to the right authority

- Prefer one self-contained human-facing document for one review object, combining requirements and solution sections when readers benefit from a continuous explanation. Split human-readable pages only for a distinct authority, lifecycle, or scale-driven reader job.
- Requirements sections describe user/system outcomes, scenarios, quality expectations, dependencies, and observable acceptance.
- Architecture or solution sections describe topology, ownership, data flow, state, persistence, and necessary failure handling.
- Keep the human-facing document self-contained with readable definitions and the field tables needed to understand the protocol. Machine contracts own the exact enforceable fields, enums, error codes, wire limits, and schema constraints; link them from the prose as validation authority.
- Implementation plans and verification records own delivery waves, commands, test evidence, activation status, and rollback evidence.

## Review before handing off

Check that a reader can answer what is being built, who owns each fact, how the main flow works, what happens on important failures, and how success is verified without reading the author's working notes. Remove duplicate sections and process language before polishing terminology. Preserve project-specific lifecycle metadata when a repository validator requires it, but keep its explanatory governance text out of the product narrative when a separate record can carry it.

## Boundaries

Use a repository's local specification skill for authority resolution, current-versus-target evidence, contracts, diagrams, and project gates. Use `deep-interview` for adaptive clarification and explicit approval; do not add interview ledgers or approval gates to this skill.
