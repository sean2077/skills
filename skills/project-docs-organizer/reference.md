# `project-docs-organizer` — reference

The full default zone catalog plus numbering-pitfall examples for the `project-docs-organizer` skill. `SKILL.md` keeps the
operative rules resident — location priority, simple-vs-complex classification, two-digit
numbering semantics, README role rules, the deletion-evidence rule, and the acceptance
checks — plus the major-area summary. Read this catalog before designing a complex docs
tree, and create only the subcategories the project actually needs.

## Default zone catalog

Use an audience-plus-lifecycle taxonomy by default:

- `00-start-here`: docs map and first-contact overview.
- `01-quickstart`: fastest safe path to install, run, or understand the project.
- `02-first-run`: first successful execution, smoke test, or first contribution path.
- `10-user-overview`: user-facing map for external users, operators, or integrators.
- `11-user-guide`: stable usage guidance.
- `12-integrations`: integration, embedding, or extension guidance.
- `20-development-overview`: developer and long-term maintainer map.
- `21-architecture`: stable architecture, boundaries, data flow, and module ownership.
- `22-codebase`: codebase map, important files, packages, and internal concepts.
- `23-local-development`: local setup, build, test, debug, and common troubleshooting.
- `24-testing`: test strategy, fixtures, coverage expectations, and smoke checks.
- `25-release-maintenance`: release process, dependency policy, migration chores, and maintainer handoff.
- `30-iteration-overview`: planning and decision-history map.
- `31-planning-roadmap`: roadmap, milestones, project plans, and active risk registers.
- `32-adrs`: architecture decision records.
- `33-specs-rfcs`: specs, RFCs, proposals, and design drafts.
- `34-risk-decisions`: risk logs, decision logs, tradeoff records, and unresolved design notes.
- `40-tooling-overview`: tooling and standards map.
- `41-development-tools`: local developer tools, editor setup, language servers, package managers, and debug tools.
- `42-agent-mcp-tools`: agent, MCP, automation, prompt, skill, and assistant-tooling setup.
- `43-ci-build-release-tools`: CI, build, release, deployment tooling, and reproducible command surfaces.
- `44-coding-standards`: coding conventions, formatter/linter rules, review policy, and contribution norms.
- `45-doc-standards`: documentation conventions, naming rules, generated-doc policy references, and doc review expectations.
- `50-operations-overview`: operations map.
- `51-deployment`: deployment procedures and environment setup.
- `52-runbooks`: runbooks and operational procedures.
- `53-observability-debugging`: logs, metrics, tracing, debugging, and incident investigation.
- `54-security-backup`: security operations, backup, restore, and recovery.
- `60-reference-overview`: reference map.
- `61-api`: API reference and public contract details.
- `62-schemas-protocols`: schemas, protocols, wire formats, and compatibility tables.
- `63-domain-reference`: domain concepts, glossary, and source-backed background.
- `64-research-compatibility`: external research, tool comparisons, version notes, and compatibility references.
- `90-system-overview`: documentation-system map.
- `91-archive`: retained historical docs that are no longer primary guidance.
- `92-deprecated`: deprecated docs kept for compatibility or migration context.
- `93-generated`: generated documentation outputs or generated-doc instructions.
- `94-doc-migrations`: documentation migration notes and old-to-new map records.

The developer area is `2x`. The iteration area is `3x`. The tooling and standards area is `4x`. Keep tools in `4x` even when they are primarily used by developers, operators, or release managers.

If a project needs fewer zones, collapse them. If it needs more, choose the next unused first digit and keep the one-class-per-zone rule.

## Numbering pitfalls

Worked examples for the numbering rules in `SKILL.md` → *Numbered Zone Rules*.

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
