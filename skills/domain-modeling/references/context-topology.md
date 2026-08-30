# Context Topology

Read this only when choosing whether project terminology should stay in one glossary, gain subject headings, or split behind a `CONTEXT-MAP.md`.

## Maturity ladder

Use the lightest shape that solves the current retrieval and ambiguity problem:

| Shape | Use when | Do not promote yet when |
|---|---|---|
| **Flat `CONTEXT.md`** | The glossary is small and one scan gives a coherent model. | Terms still share one meaning and owner. |
| **Grouped `CONTEXT.md`** | Natural subject clusters improve scanning, but the terms still belong to one project context. | Headings are enough and no term changes meaning across groups. |
| **Mapped contexts** | Durable semantic or ownership boundaries require separate glossaries and task-local loading. | The proposed files merely mirror directories, teams, or an arbitrary size threshold. |

Headings are retrieval aids, not bounded contexts. A group becomes a context only when it owns a coherent language boundary that can evolve with limited knowledge of the others.

## Up-front and incremental modes

Both modes are valid and remain revisable.

### Up-front modeling

Use it when the user explicitly requests it or the project already provides enough evidence: named product capabilities, actors, end-to-end workflows, ownership boundaries, domain events, independent lifecycles, or known words with different meanings.

Before creating files, obtain enough owner input to explain:

- what each proposed context owns and excludes;
- which workflows cross contexts;
- which concepts are shared and who owns them;
- where the same word has different meanings.

If those answers are unavailable, continue elicitation or use a grouped root glossary. Do not turn an early architecture guess into an authoritative context map.

### Incremental evolution

This is the default when the user has not chosen and evidence is incomplete:

1. Create no glossary until the first durable project-specific term resolves.
2. Start with root `CONTEXT.md`.
3. Add subject headings when scanning becomes harder or clusters emerge.
4. Promote to mapped contexts only after durable split signals appear.

Incremental does not mean postponing terminology maintenance. During authorized editing work, add and repair terms as they resolve; defer only the heavier file topology.

## Split signals

A split is usually justified by several reinforcing signals:

- the same term has materially different meanings;
- different owners or product capabilities govern the concepts;
- terms and invariants change together inside a cluster but rarely across clusters;
- normal tasks need only one subset of the glossary;
- relationships between candidate contexts can be stated precisely;
- keeping one file causes repeated ambiguity, accidental coupling, or unnecessary context loading.

No hard term-count threshold is authoritative. A long coherent glossary may remain one file; a short glossary with semantic collisions may need several contexts.

## File placement and ownership

Keep root `CONTEXT-MAP.md` as the router. Place each glossary at a stable domain-owned path, which may be a source-domain root or a documentation-owned context directory. Do not force the code tree to mirror the context model.

A multi-context repository may retain root `CONTEXT.md` for genuinely system-wide terms, but the map must route to it and every concept still has exactly one owning glossary:

```markdown
# Context Map

## Contexts

- [System language](CONTEXT.md): concepts owned across the whole product
- [Ordering](src/ordering/CONTEXT.md): accepts and tracks orders
- [Billing](src/billing/CONTEXT.md): issues invoices and records payment

## Relationships

- **Ordering → Billing**: Billing references order identities; Ordering owns order state.
```

Do not create `Shared`, `Common`, or `Misc` merely for terms that are hard to classify. Keep an unresolved term in its current glossary until ownership is known. A genuinely shared context needs a named owner, scope, and relationship to its consumers.

## Context glossary shape

Each context file keeps one definition per concept and the project's multilingual contract:

```markdown
# Ordering Language

Defines concepts owned by the ordering context.

## Canonical term languages

- `en`
- `zh-CN`

## Language

**Order**:
A customer's accepted request for the product to provide one or more items.
_Equivalent (zh-CN)_: 订单
_Avoid (en)_: purchase
```

The heading term and `_Equivalent (<language-tag>)_` names are equal canonical equivalents. Keep all equivalents and avoided names with the one owning definition.
