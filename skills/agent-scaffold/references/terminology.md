# Agent Scaffold Project Terminology

Use when `terminology` is selected. Establish project-wide language and ongoing maintenance,
not a mandatory modeling pass before every task. The managed terminology section follows the
saved domain choice; existing project definitions remain project-owned even when excluded.
Resolve known durable concepts during authorized setup and route readers to their actual source.
Routine concept changes follow the project glossary and the installed
[terminology guide](../assets/conventions/terminology.md) (`.agents/conventions/terminology.md`,
routed from the managed block); no separate skill is required.

## Select the source

Use the glossary declared by project-owned `AGENTS.md`; otherwise use root `CONTEXT-MAP.md`, then `CONTEXT.md`. Adopt an existing dedicated glossary by linking to it rather than copying its definitions. Resolve competing owners before changing terms. Create a glossary when the first durable project-specific concept is resolved.

```markdown
| Canonical project terminology | [CONTEXT.md](CONTEXT.md) |
```

## Language and entries

Keep a concept's definition and canonical language equivalents together. Those equivalents are equally valid names, so use the one clearest in context. Preserve exact code, protocol, vendor, and API identifiers at their owning boundaries.

Follow the project's glossary convention. One possible entry format is:

```markdown
# System language

## Canonical term languages

- `en`
- `zh-CN`

## Language

**Worktree**:
A checked-out Git working tree used for an isolated change.
_Equivalent (zh-CN)_: 工作树
_Avoid (en)_: workspace clone
```

Language coverage records maintained equivalents. Add translations when their meaning is established; preserve a stable original where no natural equivalent exists. Record historical or misleading names when recognizing them helps search, migration, or compatibility.

## Context organization

| Shape | Use |
|---|---|
| Flat root `CONTEXT.md` | A small, coherent glossary |
| Grouped root `CONTEXT.md` | Subject headings help retrieval within one owner |
| `CONTEXT-MAP.md` with local glossaries | Distinct meanings or ownership need separate contexts |

Honor the owner's up-front or incremental modeling choice. Otherwise evolve from established concepts and scenarios. Keep each concept under one owner and migrate definitions with their language equivalents and reader routes.

For mapped contexts:

```markdown
# Context Map

## Contexts

- [System language](CONTEXT.md): shared product concepts
- [Ordering](src/ordering/CONTEXT.md): order acceptance and tracking
- [Billing](src/billing/CONTEXT.md): invoicing and payment

## Relationships

Billing references order identities owned by Ordering.
```

A map can retain a root glossary for system-wide terms. Resolve uncertain ownership before moving definitions.

## Maintenance

The installed guide carries the daily maintenance rules: evidence for a durable concept,
visible disagreements, and updating definitions, equivalents and reader routes together on a
rename, split, merge or deprecation without authorizing an API, wire or database migration. Do
not restate them in project docs. During setup, resolve known durable concepts from repository
evidence and owner intent; when meaning or ownership is unknown, keep the boundary visible rather
than inventing a definition. A route inside a managed block must be updated through its
source/renderer, not patched by hand. Existing local meanings can coexist under different owners.
