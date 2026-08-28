# Agent Scaffold Project Terminology

Read this only when choosing, adopting, or changing a project's terminology source. Ordinary work follows the managed `AGENTS.md` rule and reads the applicable glossary directly.

## Design decision

`agent-scaffold` owns the **loading contract**, not the project's terms. Its managed `AGENTS.md` block makes canonical language an always-on obligation for every Agent, project skill, and subagent. The project owns the glossary content, so `apply` and `upgrade` never overwrite it.

Do not add a terminology skill merely to make other workflows consume vocabulary. Skill discovery is conditional and contributes routing metadata; project language is a cross-cutting contract that must apply even when no terminology-focused workflow is invoked. A separate domain-modeling skill is justified only when the project repeatedly needs active facilitation such as term discovery, ambiguity workshops, scenario stress-testing, or broad vocabulary migrations. That skill must still read and update the same project-owned glossary rather than create another SSOT.

The scaffold deliberately does not seed an empty glossary. An empty file carries no useful authority, adds noise to every repository, and may compete with an established `GLOSSARY.md`, `TERMINOLOGY.md`, or documentation-owned glossary.

## Select one terminology source

Declare the canonical source with a direct link in project-owned root `AGENTS.md` prose, commonly in its reference table:

```markdown
| Canonical project terminology | [CONTEXT.md](CONTEXT.md) |
```

Use this precedence when adopting or retrofitting a repository:

1. An explicit project-owned `AGENTS.md` declaration wins.
2. Otherwise, root `CONTEXT-MAP.md` routes a multi-context repository.
3. Otherwise, root `CONTEXT.md` is the default single-context source.
4. Otherwise, adopt one existing dedicated glossary and add the explicit `AGENTS.md` declaration instead of copying it.
5. If multiple plausible sources exist, resolve ownership with the project owner before editing terms.
6. If no source exists, create root `CONTEXT.md` only when the first durable project-specific term is resolved.

The source may use another project-owned path. The explicit `AGENTS.md` link is what makes that exception discoverable to all hosts and workflows.

## Glossary shape

Keep the file small and opinionated:

```markdown
# <Context Name>

<One or two sentences defining the context's scope.>

## Language

**Canonical term**:
A one- or two-sentence definition of what the concept is.
_Avoid_: synonym, overloaded name, retired name
```

Include only project-specific concepts whose naming materially affects understanding. Do not turn the glossary into a specification, architecture guide, decision log, command reference, or implementation inventory. Link those owning sources from `AGENTS.md` or normal project documentation.

`_Avoid_` records names that an Agent may need to recognize while searching history, migrating code, or translating an external system. It is not permission to introduce those names into new project-controlled surfaces. Externally fixed API, protocol, schema, or vendor names remain unchanged at their compatibility boundary; translate to canonical language behind that boundary when practical.

## Multiple bounded contexts

Create root `CONTEXT-MAP.md` only when one flat glossary would merge concepts that genuinely have different meanings or owners. Point each entry to the smallest stable context file:

```markdown
# Context Map

## Contexts

- [Ordering](src/ordering/CONTEXT.md): accepts and tracks orders
- [Billing](src/billing/CONTEXT.md): issues invoices and records payment

## Relationships

- Billing references order identities owned by Ordering; it does not own order state.
```

Read the map plus only the context files relevant to the current work. A directory layout alone does not justify multiple contexts, and nested `AGENTS.md` files do not need to duplicate glossary entries; they may link to a local context when the root map is not sufficient.

## Maintenance contract

- Resolve terminology against repository evidence and owner intent; do not infer a new canonical name from one isolated file.
- Update the glossary in the same change that introduces, renames, splits, merges, or deprecates a durable concept.
- Update controlled code, APIs, tests, docs, plans, examples, and commit language when the change owns those surfaces; preserve compatibility aliases only where required.
- Surface disagreement between the glossary, code, and user language instead of silently choosing one.
- Prefer one precise term per concept and one concept per term. Record intentional exceptions explicitly.
