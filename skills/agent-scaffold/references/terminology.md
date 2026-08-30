# Agent Scaffold Project Terminology

Read this only when choosing, adopting, or changing a project's terminology source. Ordinary work follows the managed `AGENTS.md` rule and reads the applicable glossary directly.

## Design decision

`agent-scaffold` owns the **loading contract**, not the project's terms. Its managed `AGENTS.md` block makes canonical language an always-on obligation for every Agent, project skill, and subagent. The project owns the glossary content, so `apply` and `upgrade` never overwrite it.

Do not add or install a terminology skill merely to make other workflows consume vocabulary. Skill discovery is conditional and contributes routing metadata; project language is a cross-cutting contract that must apply even when no terminology-focused workflow is invoked. The optional `domain-modeling` catalog skill owns active work such as term discovery, ambiguity challenges, scenario stress-testing, context partitioning, translation review, and vocabulary migration. It reads and updates the same project-owned glossary rather than creating another SSOT. `agent-scaffold` does not install it automatically; projects install that route separately when active modeling is useful.

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

## Progressive context topology

Glossary organization evolves through three proportional shapes:

| Shape | Use |
|---|---|
| Flat root `CONTEXT.md` | The glossary is small and coherent in one scan. |
| Grouped root `CONTEXT.md` | Subject headings improve retrieval, but terms still share one semantic and ownership context. |
| Root `CONTEXT-MAP.md` plus context-local glossaries | Durable semantic or ownership boundaries justify separate loading and one glossary would conflate concepts. |

Headings are retrieval groups, not bounded contexts. Promote a group to its own context only when evidence shows a stable language owner, materially different meanings, independent evolution, or repeated task-local loading value. Term count and directory structure alone do not justify a split, and no hard threshold applies.

Both **up-front** and **incremental** modeling are valid:

- Honor an explicit project-owner choice.
- Use up-front modeling when the owner requests it or established product capabilities, actors, workflows, ownership, events, or semantic collisions already support defensible boundaries.
- Otherwise use incremental evolution: start with root `CONTEXT.md`, add headings when useful, and split only after durable evidence emerges.
- When an early project lacks enough context for an up-front map, obtain focused owner input about scope, actors, workflows, ownership, and overloaded terms. Do not manufacture empty domains or placeholder files.

Create root `CONTEXT-MAP.md` only when mapped contexts are justified. Point each entry to the smallest stable owner and state cross-context relationships:

```markdown
# Context Map

## Contexts

- [System language](CONTEXT.md): concepts owned across the whole product
- [Ordering](src/ordering/CONTEXT.md): accepts and tracks orders
- [Billing](src/billing/CONTEXT.md): issues invoices and records payment

## Relationships

- Billing references order identities owned by Ordering; it does not own order state.
```

A multi-context repository may retain root `CONTEXT.md` for genuinely system-wide terms, but the map must route to it and every concept still has exactly one owning glossary. Keep uncertain terms in their current glossary until ownership resolves; do not create ownerless `Shared`, `Common`, or `Misc` contexts.

The optional `domain-modeling` catalog skill performs the active elicitation, scenario testing, topology selection, and migration workflow. The scaffold keeps only this loading and proportionality contract so ordinary projects do not pay another installed-route cost.

## Maintenance contract

- Resolve terminology against repository evidence and owner intent; do not infer a new canonical name or translation from one isolated file.
- Update the glossary in the same change that introduces, translates, renames, splits, merges, or deprecates a durable concept.
- Update controlled code, APIs, tests, docs, plans, examples, and commit language when the change owns those surfaces; preserve compatibility names only where required.
- Surface disagreement between the glossary, code, user language, and translated equivalents instead of silently choosing one.
- Prefer one precise concept per entry and at most one canonical term per maintained language. Record intentional exceptions explicitly.
