# Agent Scaffold Project Terminology

Read this only when choosing, adopting, or changing a project's terminology source. Ordinary work follows the managed `AGENTS.md` rule and reads the applicable glossary directly.

## Design decision

`agent-scaffold` owns the **loading contract**, not the project's terms. Its managed `AGENTS.md` block makes canonical language an always-on obligation for every Agent, project skill, and subagent. The project owns the glossary content, so `apply` and `upgrade` never overwrite it.

Do not add a terminology skill merely to make other workflows consume vocabulary. Skill discovery is conditional and contributes routing metadata; project language is a cross-cutting contract that must apply even when no terminology-focused workflow is invoked. A separate domain-modeling skill is justified only when the project repeatedly needs active facilitation such as term discovery, ambiguity workshops, scenario stress-testing, translation review, or broad vocabulary migrations. That skill must still read and update the same project-owned glossary rather than create another SSOT.

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

## Multilingual model

A multilingual glossary has one concept entry, one definition, and at most one canonical name for that concept in each maintained language. Cross-language equivalents are not aliases: they are equally valid names for the same concept. Use whichever canonical equivalent is clearest in the current conversation or document. Matching the surrounding language is a useful default, not a hard rule, and no glossary language becomes the mandatory discussion language.

When useful, declare maintained coverage once near the top of the glossary with BCP 47-style language tags:

```markdown
## Canonical term languages

- `en`
- `zh-CN`
```

This list states which language equivalents the project intentionally maintains. It does not rank them, select a primary language, or require every technical term to be translated. Omit an equivalent when no stable and natural project term exists; never invent one through unattended machine translation.

Do not add `_Preferred_` or `_Aliases_` fields by default. They create an unnecessary middle state for this contract. If a name is safe for new project use, make it the single canonical term for that language. If it is historical, ambiguous, misleading, mistranslated, or retired, record it under `_Avoid_`. Well-established abbreviations may appear in the canonical term itself, for example `Command-line interface (CLI)`.

## Glossary shape

Keep the file small and opinionated:

```markdown
# <Context Name>

<One or two sentences defining the context's scope.>

## Canonical term languages

- `en`
- `zh-CN`

## Language

**Worktree**:
A checked-out Git working tree used for an isolated change.
_Equivalent (zh-CN)_: 工作树
_Avoid (en)_: workspace clone
_Avoid (zh-CN)_: 临时仓库
```

The entry heading and each `_Equivalent (<language-tag>)_` value are equal canonical names. `_Equivalent_` is for cross-language names, not same-language synonyms. Keep at most one canonical name per language so two Agents using the same language do not drift into competing vocabulary.

`_Avoid (<language-tag>)_` records names that an Agent may need to recognize while quoting, searching history, migrating code, or interpreting an external system. It is not permission to introduce those names into new project-controlled surfaces. Existing untagged `_Avoid_` fields remain valid and inherit the entry or document language.

Include only project-specific concepts whose naming materially affects understanding. Do not turn the glossary into a specification, architecture guide, decision log, command reference, or implementation inventory. Link those owning sources from `AGENTS.md` or normal project documentation.

Code identifiers, APIs, schemas, protocols, commands, vendor terms, and proper names remain unchanged at the boundary that owns them. A natural-language equivalent may be used in discussion without renaming that external or machine-facing surface.

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

- Resolve terminology against repository evidence and owner intent; do not infer a new canonical name or translation from one isolated file.
- Update the glossary in the same change that introduces, translates, renames, splits, merges, or deprecates a durable concept.
- Update controlled code, APIs, tests, docs, plans, examples, and commit language when the change owns those surfaces; preserve compatibility names only where required.
- Surface disagreement between the glossary, code, user language, and translated equivalents instead of silently choosing one.
- Prefer one precise concept per entry and at most one canonical term per maintained language. Record intentional exceptions explicitly.
