---
name: spec-writing
description: Use when writing or revising a PRD, requirements, RFC, design doc, or architecture proposal from settled or authoritative inputs. Preserve meaning; clarify behavior, ownership, interfaces, failures, acceptance; remove process history. Not for unresolved intake, whole-project docs reorganization, or contract review.
---

# Human-facing Specification Writing

Turn settled or authoritative facts and decisions into the smallest coherent document a reviewer, implementer, or tester can use. This skill governs document quality; it does not choose product behavior, replace approval, or become the authority for evidence or machine contracts.

## Establish the document boundary

- Identify the audience, review object, document status, authority model, and whether each statement describes current or target behavior.
- Follow project-local templates, terminology, lifecycle metadata, and source-of-truth rules.
- Preserve identifiers, exact values, compatibility constraints, and normative strength. Do not silently reconcile conflicting sources, invent decisions, or present an assumption as fact.
- Keep material assumptions and unresolved questions visible with their impact and owner where known. Surface conflicting sources and their impact; continue a bounded draft unless a blocking authority decision is required. Omit debate transcripts and approval history.

## Write for the reader

- Lead with the outcome, problem, scope, and status. Explain the main behavior or architecture flow before detailed fields.
- Define each important concept once; cross-reference instead of repeating definitions, tables, or failure rules.
- State requirements positively and observably, naming the responsible actor, relevant condition, and expected result when useful.
- List a non-goal only when a reasonable reader might otherwise assume it is included or when the boundary prevents real scope creep; do not treat silence as proof of exclusion.
- Keep the concise rationale needed to understand a non-obvious constraint, compatibility requirement, or design choice.
- Move deliberation history, rejected alternatives, and durable cross-cutting decisions to a linked ADR or decision record when one exists. Create one only when project convention or an explicit need calls for recording a materially costly-to-reverse, cross-cutting, or compatibility- or migration-sensitive choice; otherwise keep concise rationale here.

## Present material choices for review

- When an implementation or technology choice can change behavior, compatibility, reliability, security, operations, cost, or schedule, include a concise options-and-recommendation section in the same human-facing document.
- Compare only viable, decision-bearing options against explicit criteria. A small table should show the option, relevant benefits, trade-offs or risks, and the recommended choice; record the decision status and owner when it is still open.
- Describe the selected option and resulting behavior in the main document. Keep exhaustive alternatives, historical debate, and detailed rationale in a linked decision record; do not enumerate trivial or speculative branches.

## Route detail to the right authority

- Use one document for one review object when requirements and solution share an audience, owner, and lifecycle. Split when authority, reuse, approval, update cadence, scale, or reader job differs.
- Requirements cover outcomes, scenarios, constraints, dependencies, quality expectations, and observable acceptance criteria.
- Solution sections cover responsibilities, topology, flow, state, persistence, interfaces, and material failure or recovery behavior.
- Keep enough protocol detail for human understanding. When a project-documented machine-readable or executable contract, generated schema, code source, or other explicit authority exists, link it for volatile machine-checkable fields, enums, codes, and limits while retaining a readable summary. Otherwise include the exact detail needed here and identify its intended authority.
- Keep delivery sequencing, commands, observed test evidence, activation status, and rollback evidence in plans or verification records.

## Review before handoff

Check that:

- current and target behavior are not conflated;
- every material behavior, authority, compatibility, ownership, or acceptance claim is settled or verified, explicitly assumed, or visibly open;
- responsibility, source authority, main flow, material failures, recovery, and acceptance are clear;
- acceptance criteria are observable and cover the material requirements and scenarios;
- terms, identifiers, tables, diagrams, links, and authority references agree;
- no definition, volatile contract fact, decision history, or process narrative is unnecessarily duplicated.

## Boundaries

Use `deep-interview` when decisions need clarification and explicit approval. Use `project-docs-organizer` for documentation information architecture, navigation, moves, pruning, lifecycle, and archival. Follow repository-local specification or evidence skills for current-state discovery, authority resolution, contract validation, diagrams, and project gates. Do not add interview ledgers, approval gates, or a universal document template here.
