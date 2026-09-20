---
name: spec-writing
description: "Use to write or revise a PRD, RFC, requirements, or design document while preserving settled meaning. Not for a requirements interview, whole-project docs reorganization, or implementation."
---

# Human-facing Specification Writing

Write the smallest coherent document a reviewer, implementer, or tester can use. Document quality is not authority to invent product decisions or approve them.

## Writing contract

- Establish the audience, review object, status, and current versus target behavior. Follow project templates, terminology, and source ownership; metadata helps judge freshness but does not establish truth or approval.
- Preserve identifiers, exact values, compatibility constraints, and normative strength. Label material assumptions, conflicts, and open decisions rather than silently resolving them. A useful bounded draft can proceed with visible gaps; not every gap requires a separate interview.
- Lead with the outcome and main behavior or architecture flow. Make material responsibility, interfaces, failure/recovery behavior, and observable acceptance clear. Include non-goals only where they prevent a plausible misunderstanding.
- Define concepts once and link to their authority. Summarize executable/generated contracts for people without copying volatile machine fields; where no other authority exists, include the exact detail this document must own.
- Compare options only for unresolved, decision-bearing choices or a requested reconsideration. Do not reopen an approved design merely because technology, cost, or schedule is involved. Keep concise rationale for the chosen behavior; link detailed history or an existing ADR when useful.
- Split documents when audiences, ownership, approval, or lifecycles differ, not to satisfy a universal template. Keep working transcripts, delivery commands, and observed verification logs out of the reader narrative; preserve necessary evidence in its owning record.

Before handoff, check that terms, links, diagrams, exact constraints, main flow, and acceptance agree, and that material claims are evidenced, explicitly assumed, or visibly open. Polishing a draft does not approve it. Optional flat `status` and `updated` hints may help where no convention exists; do not introduce a schema or require metadata.

Unresolved user-owned decisions may need clarification; documentation moves/navigation belong to `project-docs-organizer`. These are boundaries, not mandatory sibling skill calls.
