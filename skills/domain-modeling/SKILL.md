---
name: domain-modeling
description: 'Use when a project needs to define, challenge, group, split, or migrate terminology in CONTEXT.md or CONTEXT-MAP.md, especially when a glossary grows, terms cross domain boundaries, or contexts need up-front modeling. Not for reading established terms, general docs organization, or unrelated architecture decisions.'
---

# Domain Modeling

Actively sharpen project language and context ownership. Ordinary Agent work consumes the applicable glossary; this skill changes that model.

## Invariants

- The project owns its terminology and context topology. Honor an explicit user choice to model contexts up front or evolve them incrementally.
- Use the smallest topology that keeps concepts clear: one flat glossary, one glossary grouped by subject, or a `CONTEXT-MAP.md` routing to context-local glossaries.
- Split only for durable semantic or ownership boundaries. Term count, source directories, or a desire for a tidy tree are not sufficient by themselves.
- Give each concept one owning glossary and one definition. Keep all canonical language equivalents for that concept together; never duplicate the entry across contexts.
- Do not create empty contexts, placeholder taxonomies, or ownerless `misc`/`shared` catch-alls.
- A request to assess, explain, or review terminology does not authorize file changes. Mutate glossaries or routes only when the user requested or approved those changes.
- When an early project lacks enough domain evidence, ask focused questions before committing file topology. Keep unresolved terms in the current or root glossary rather than guessing.
- Capture resolved language as it crystallizes during authorized editing work. Do not batch durable terminology decisions until the end of unrelated implementation work.
- Keep context files glossary-focused. Put behavior, architecture, requirements, and decisions in their owning project sources rather than turning `CONTEXT.md` into a specification or ADR log.

## Workflow

1. Read the root and applicable nested `AGENTS.md`, then locate the declared terminology source. If no source is declared, inspect `CONTEXT-MAP.md`, `CONTEXT.md`, and any established glossary.
2. Confirm this is active modeling. If the task only needs existing vocabulary, read the applicable glossary and stop; no domain-modeling workflow is needed.
3. Select the approach:
   - honor an explicit **up-front** or **incremental** choice;
   - use up-front modeling when requested or when repository evidence already shows stable contexts;
   - otherwise default to incremental evolution.
4. Read [`elicitation-and-migration.md`](references/elicitation-and-migration.md). Gather only the evidence and owner input needed to distinguish concepts, ownership, workflows, and boundaries.
5. Read [`context-topology.md`](references/context-topology.md). Choose flat, grouped, or mapped topology and state why the next heavier shape is or is not justified.
6. Challenge vague or conflicting terms with concrete scenarios, then cross-check the proposed language against code, schemas, APIs, tests, and existing documentation.
7. When changes are authorized, update the owning glossary as terms resolve. If topology changes, migrate the entries atomically, update `CONTEXT-MAP.md` and `AGENTS.md` routes, and leave no duplicate owner. For read-only work, report the proposed changes without applying them.
8. Verify every active route resolves, every concept has one owner, context relationships are explicit where needed, and multilingual equivalents remain attached to the same definition.
9. Report the selected approach, evidence, user-resolved questions, topology decision, moved or changed terms, verification, and deliberately unresolved boundaries.

## Completion checks

- The chosen topology is proportional to observed semantic and ownership boundaries.
- An explicit user choice was honored; otherwise incremental evolution was the default.
- No domain boundary was invented from directory layout or term count alone.
- No concept is defined in more than one glossary.
- No empty context or catch-all category was introduced.
- Unknown early-project boundaries remain explicit and unsplit rather than falsely settled.
- The glossary contains language only; deeper behavior and decisions remain in their owners.

## On-demand references

| Need | Reference |
|---|---|
| Choose flat, grouped, or mapped topology and compare up-front with incremental modeling | [`context-topology.md`](references/context-topology.md) |
| Elicit missing domain context, test boundaries with scenarios, and migrate without duplicate ownership | [`elicitation-and-migration.md`](references/elicitation-and-migration.md) |
