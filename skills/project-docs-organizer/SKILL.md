---
name: project-docs-organizer
description: 'Design, reorganize, or prune a software project documentation system from observed readers, tasks, domains, ownership, lifecycles, and retrieval failures. Covers README and docs trees, onboarding, architecture, ADRs, specs, plans, runbooks, reference, archives, navigation, and optional default-on local numbering when no coherent convention governs. Use when readers cannot find or trust project docs. Not for application source layout, tool-command governance (use tooling-conventions), or AGENTS.md/CLAUDE.md harness policy (use agent-scaffold).'
---

# Project Docs Organizer

Derive a documentation system that readers can find, trust, and maintain. The target project
owns its information architecture; this skill supplies evidence-led selection rules, not a
universal directory template.

## Invariants

- Honor a user-selected location and preserve a coherent established convention.
- Prefer the smallest structure that solves observed navigation or ownership problems.
- Select one primary axis per tree level. Represent secondary lenses with local subgroups,
  navigation, metadata, or checks instead of parallel directory taxonomies.
- Keep entry-point READMEs focused on orientation and routing; move durable detail to
  canonical topic pages.
- Give each durable fact one authoritative home and update every active route to it.
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
   [`classification-methods.md`](references/classification-methods.md). Shortlist lenses,
   choose one evidence-backed primary axis at each relevant level, and place secondary lenses.
4. Write a documentation IA decision record before proposing or applying a reorganization:
   evidence and retrieval failures; candidate lenses; chosen primary axes; secondary-lens
   representations; rejected alternatives; numbering decision and evidence; proposed tree;
   and the move/merge/delete map.
5. Run the representative placement test from `information-architecture.md`. Resolve a
   high-impact tie with the user before editing.
6. Decide numbering only after semantic boundaries are stable. Preserve an explicit user
   choice, coherent established convention, or generator-owned ordering. Otherwise enable
   numbering by default and read [`numbering-patterns.md`](references/numbering-patterns.md).
7. Apply the reorganization, consolidating duplicates into canonical pages and keeping
   project-specific terminology intact.
8. Follow [`migration-and-links.md`](references/migration-and-links.md) to update navigation,
   backlinks, configs, and stale path references, then run the repository's doc checks.
9. Report the IA decision record, resulting entry points, moves/merges/deletions, deletion
   evidence, checks, and intentionally deferred risks.

## Completion checks

- The IA decision record precedes the proposed tree and any mutation.
- Each representative document has one obvious canonical home without duplicated content.
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
| Select a project-owned container, primary axis, secondary lenses, and tie behavior | [`information-architecture.md`](references/information-architecture.md) |
| Compare reader, task, domain, product, content-purpose, and lifecycle lenses | [`classification-methods.md`](references/classification-methods.md) |
| Apply or decline sibling-local numeric ordering after semantic design | [`numbering-patterns.md`](references/numbering-patterns.md) |
| Plan moves/deletions and verify navigation, backlinks, and stale paths | [`migration-and-links.md`](references/migration-and-links.md) |
