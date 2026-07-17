# Optional Documentation Numbering Patterns

Read this only after the project has chosen a numbered tree and the proposed structure may
collapse distinct subcategories or misuse numeric prefixes.

## Numbering pitfalls

Use these examples only after the information-architecture decision selects numbering.

**Don't let the first digit be the only classification** — collapsing every major area into a single landing folder loses the subcategory semantics:

```text
# avoid
docs/
├── 20-development/
├── 30-iteration/
└── 40-tooling-standards/
```

```text
# prefer — real subcategories under each major area
docs/
├── 21-architecture/
├── 22-codebase/
├── 32-adrs/
├── 33-specs-rfcs/
├── 41-development-tools/
└── 44-coding-standards/
```

**Nested numeric prefixes only for required reading order** — inside a numbered subcategory, add `00-`/`01-`/… prefixes only when readers must consume the files in sequence:

```text
docs/01-quickstart/
├── 00-install.md
├── 01-first-run.md
└── 02-first-change.md
```
