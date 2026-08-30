---
name: project-docs-organizer
description: 'Use when readers cannot find or trust a software project''s README/docs and the documentation system needs design, reorganization, pruning, navigation, ownership, lifecycle, or archival. Not for source layout, command governance, or AGENTS.md/CLAUDE.md harness policy.'
---

# Project Docs Organizer

Derive a documentation system that readers can find, trust, and maintain. The target project
owns its information architecture; this skill supplies evidence-led selection rules, not a
universal directory template.

## Invariants

- Honor a user-selected location and preserve a coherent established convention.
- Prefer the smallest structure and the smallest decision artifact that solve the observed
  navigation or ownership problem.
- Select one primary axis per tree level. Represent secondary lenses with local subgroups,
  navigation, metadata, or checks instead of parallel directory taxonomies.
- Keep entry-point READMEs focused on orientation and routing; move durable detail to
  canonical topic pages.
- Give each durable fact one authoritative home and update every active route to it. Classify volatile external facts, compatibility claims, version pins, and command examples explicitly; date/source them or bind them to a tested version instead of presenting them as timeless.
- Use a compact inline decision delta for bounded maintenance that preserves the existing
  container, primary axis, ownership, lifecycle, and numbering. Use a full Documentation IA
  Decision Record only for material information-architecture changes, competing viable designs, or an explicit project/user requirement.
- When a high-impact axis choice remains tied, present two or three candidates with evidence,
  tradeoffs, and a recommendation, then wait for the user before mutation.
- Create directories only for real content or committed near-term work. No empty category or
  placeholder may exist solely to complete a taxonomy or consume a number.
- Delete only with evidence that content is stale, duplicated, superseded, or migrated.
  Archive only when retention has a named value or requirement.

## Workflow

1. Resolve the target project root (the Git top level when Git-backed), then inventory its
   root README, documentation roots, contribution and authority docs, site generators,
   package metadata, CI links, and topic-specific doc locations.
2. Identify actual readers and tasks, domain language and ownership, product surfaces,
   document lifecycles, canonical sources, generator constraints, and retrieval failures.
3. Read [`information-architecture.md`](references/information-architecture.md) and
   [`classification-methods.md`](references/classification-methods.md). Select the evidence depth,
   shortlist only relevant lenses, and identify any primary-axis or ownership change.
4. Before mutation, record either the compact decision delta or the full Documentation IA
   Decision Record defined in `information-architecture.md`. Do not expand a one-page move or
   duplicate merge into a whole-tree design exercise when the governing boundaries stay fixed.
5. Run the proportionate placement check from `information-architecture.md`. Resolve a
   high-impact tie with the user before editing.
6. Decide numbering only after semantic boundaries are stable. Preserve an explicit user
   choice, coherent established convention, or generator-owned ordering. Otherwise keep
   numbering off unless observed reader routes need stable sibling order and the navigation
   benefit exceeds path/link churn; when enabled, read
   [`numbering-patterns.md`](references/numbering-patterns.md).
7. Apply the reorganization, consolidating duplicates into canonical pages and keeping
   project-specific terminology intact.
8. Follow [`migration-and-links.md`](references/migration-and-links.md) to update navigation, backlinks, configs, stale path references, duplicated factual claims, and copy-paste commands; then run the repository's doc checks and any real tool smoke required by changed command facts.
9. Report the decision artifact, resulting entry points, moves/merges/deletions, deletion
   evidence, checks, and intentionally deferred risks.

## Completion checks

- A proportionate decision artifact precedes mutation: compact inline delta for bounded
  maintenance, full Documentation IA Decision Record for a material IA decision.
- Each affected or representative document has one obvious canonical home without duplicated content.
- Each intended reader has an obvious entry point and fastest safe next step.
- Stable guidance, active planning/decisions, generated content, and retained history are
  visibly distinguishable where the project needs those classes.
- Overview pages route rather than duplicate detailed guidance.
- No live link, config, or authority document points at a moved or deleted path.
- No empty category or placeholder exists solely to complete a taxonomy or numbering sequence.
- Every deleted document has explicit evidence and a surviving canonical destination when
  its useful content was retained.

## On-demand references

| Need | Reference |
|---|---|
| Scale decision evidence; select a project-owned container, primary axis, secondary lenses, and tie behavior | [`information-architecture.md`](references/information-architecture.md) |
| Compare reader, task, domain, product, content-purpose, and lifecycle lenses | [`classification-methods.md`](references/classification-methods.md) |
| Apply or decline sibling-local numeric ordering after semantic design | [`numbering-patterns.md`](references/numbering-patterns.md) |
| Plan moves/deletions and verify navigation, backlinks, and stale paths | [`migration-and-links.md`](references/migration-and-links.md) |
