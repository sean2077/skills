---
name: domain-modeling
description: "Use to define, challenge, group, split, or migrate project terminology in CONTEXT.md or CONTEXT-MAP.md. Not for consuming established terms, routine coding, or general documentation layout."
---

# Domain Modeling

Sharpen project language and ownership. Ordinary work consumes the applicable glossary; this skill changes the model. A request to assess terminology alone does not authorize edits.

## Modeling contract

Locate the terminology source declared by applicable `AGENTS.md`; otherwise inspect `CONTEXT-MAP.md`, `CONTEXT.md`, and the established glossary. Reuse settled definitions and inspect only evidence relevant to disputed or changed concepts.

Honor an explicit up-front or incremental modeling choice. Otherwise evolve incrementally: a local term or language-equivalent addition does not require redesigning context topology. Ask user-owned questions only where scenarios, code, schemas, tests, and docs cannot settle meaning or ownership.

- Give each concept one owning definition, keeping all equally valid canonical language equivalents together. Do not force one language or duplicate definitions across contexts.
- Choose the smallest useful topology: flat glossary, subject groups, or mapped context-local glossaries. Split only for durable semantic or ownership boundaries, not term count or directory shape. No empty contexts or ownerless catch-alls.
- Capture resolved terminology during authorized work. Keep unresolved boundaries explicit rather than inventing a taxonomy. A glossary owns language; behavior, architecture, and decisions belong in their project sources.
- For authorized topology changes, migrate entries and update all active routes atomically, including `CONTEXT-MAP.md` and `AGENTS.md`. Verify links, unique ownership, and attached language equivalents.

Report changed concepts, evidence, and remaining ambiguity. No approach report, topology comparison, or full-repository vocabulary sweep is needed for a bounded change that preserves those boundaries.

## On-demand references

- Read [context topology](references/context-topology.md) only when choosing or changing flat/grouped/mapped organization or deciding whether to split contexts.
- Read [elicitation and migration](references/elicitation-and-migration.md) when concepts need scenario-driven clarification or entries/routes must migrate between owners.
