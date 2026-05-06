---
name: project-docs-organizer
description: Build, restructure, or clean up project documentation systems. Use when the user asks to create or organize README files, docs/ or doc/ trees, onboarding docs, maintainer docs, ADRs, specs, plans, tooling docs, standards, runbooks, archives, or documentation navigation for a software project.
---

# Project Docs Organizer

Create or reorganize a project's documentation system so readers can quickly find the right entry point, maintainers can evolve the docs safely, and stale material does not keep competing with current guidance.

## Core Rules

- Use the user's explicitly requested documentation location when provided.
- If the user does not force a location, prefer the existing documentation directory. If none exists, use `docs/`; use `doc/` only when that is already the established project convention.
- For a simple project, keep documentation in the root `README.md` unless multiple audiences, lifecycle stages, or document types justify a dedicated docs tree.
- For a complex project, create or normalize a dedicated documentation directory.
- Keep the root `README.md` and the documentation directory `README.md` as overview and navigation surfaces only. Do not put detailed guides, specifications, ADR content, tool manuals, or long operational procedures there.
- Prefer a small, coherent documentation system over a large taxonomy. Add zones only when there is real content or a near-term place for incoming content.
- Preserve accurate content, but aggressively remove organizational clutter: rename, split, merge, move, or delete existing docs when the evidence supports it.

## Workflow

1. Inventory current documentation surfaces:
   - root `README.md`
   - `docs/`, `doc/`, `documentation/`, `wiki/`, and similarly named directories
   - ADR, RFC, spec, roadmap, planning, operations, tool, architecture, and generated-doc locations
   - links from package metadata, site config, CI, AGENTS/CLAUDE files, and contribution docs
2. Classify the project:
   - **Simple**: one main audience, low setup complexity, little long-lived planning or operations history.
   - **Complex**: multiple audiences, active maintenance workflow, architecture or ADR history, operational docs, tooling standards, or many existing docs.
3. Choose the documentation root:
   - `user-forced path > existing documentation directory > docs > doc`
4. Design the smallest complete information architecture using the major-area and subcategory numbering rules below.
5. Move, split, merge, or delete existing docs into the new structure.
6. Update all navigation links and cross-references.
7. Report changed structure, deleted/merged docs, deletion evidence, and remaining documentation risks.

## Numbered Zone Rules

Use two-digit prefixes for direct children of the documentation root when the project is complex. The two digits are semantic, not just sort order:

- First digit: major documentation area.
- Second digit: subcategory inside that major area.
- `0x`: hot entry area. First-contact material and high-frequency navigation.
- `1x`, `2x`, ... `8x`: main documentation areas.
- `9x`: system area. Archives, deprecated material, generated-doc policy, documentation maintenance metadata, and migration records.
- `x0`: overview, index, or default landing page for that major area.
- `x1` to `x8`: stable subcategories under that major area.
- `x9`: local overflow, legacy, or rare catch-all for that major area. Use sparingly; do not confuse it with the global `9x` system area.

Keep one conceptual class per numbered directory. If a major area has multiple real subcategories, do not collapse everything into only `10/20/30/...` landing folders.

Inside a numbered subcategory, add numeric prefixes only when local reading order matters. Otherwise use plain names.

Good:

```text
docs/
├── README.md
├── 00-start-here/
├── 01-quickstart/
├── 20-development-overview/
├── 21-architecture/
├── 22-codebase/
├── 23-local-development/
├── 30-iteration-overview/
├── 31-planning-roadmap/
├── 32-adrs/
├── 33-specs-rfcs/
├── 40-tooling-overview/
├── 41-development-tools/
├── 42-agent-mcp-tools/
├── 43-ci-build-release-tools/
├── 90-system-overview/
└── 91-archive/
```

Avoid using the first digit alone as the only meaningful classification:

```text
docs/
├── 20-development/
├── 30-iteration/
└── 40-tooling-standards/
```

This loses the subcategory semantics. Prefer:

```text
docs/
├── 21-architecture/
├── 22-codebase/
├── 32-adrs/
├── 33-specs-rfcs/
├── 41-development-tools/
└── 44-coding-standards/
```

Use nested numeric prefixes only when readers must consume documents in sequence:

```text
docs/01-quickstart/
├── 00-install.md
├── 01-first-run.md
└── 02-first-change.md
```

## Default Zone Model

Use an audience-plus-lifecycle taxonomy by default. Create only the subcategories the project actually needs:

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

## README Rules

Root `README.md` should answer:

- What is this project?
- Who is it for?
- How do I get to the right docs?
- What is the fastest safe start?
- Where do contributors and maintainers go next?

Documentation root `README.md` should answer:

- What major areas and subcategories exist?
- Which reader should start where?
- Which docs are stable guidance versus planning or historical records?
- Which docs are generated, archived, deprecated, or system-owned?

Do not use either README as a dumping ground for detailed setup, architecture, ADRs, specs, tool manuals, or runbooks. Move those details into the right zone and link to them.

## Reorganization Authority

When organizing existing docs, act decisively:

- Rename unclear files and directories to reader-oriented names.
- Split mixed-purpose documents when different audiences or lifecycles are competing.
- Merge duplicate or near-duplicate docs into one canonical page.
- Move planning, ADR, and spec material out of stable user/developer guidance.
- Move tool installation, usage, explanation, and standards into the `4x` tooling and standards area.
- Update backlinks, indexes, README navigation, and config references after every move.

Deletion is allowed only with evidence. A doc may be deleted when it is stale, duplicated, superseded, or replaced by a clearer canonical page, and when links/navigation have been migrated. If uncertain, archive under `90-system/` or leave a short migration note instead of deleting.

Final output must list:

- new documentation root and zone structure
- files moved, split, merged, or deleted
- deletion evidence for each deleted doc
- updated navigation surfaces
- remaining risks or intentionally deferred cleanup

## Acceptance Checks

Before claiming completion:

- A simple project has a focused root `README.md` and no unnecessary docs tree.
- A complex project has a docs root chosen by the required priority order.
- Direct children of the docs root use two-digit prefixes where the first digit is the major area and the second digit is the subcategory.
- Complex projects with real subcategories do not collapse major areas into only `10/20/30/...` landing folders.
- Root and docs-root READMEs contain only overview and navigation.
- Developer maintainer material lives under `2x`.
- Planning, ADR, spec, and roadmap material lives under `3x`.
- Tool installation, usage, explanation, CI/devtools, and standards live under `4x`.
- Archives, deprecated docs, and documentation-system metadata live under `9x`.
- Cross-links and discovery surfaces are updated.
- Deleted docs have explicit evidence and no live references.
