---
name: project-docs-organizer
description: 'Design, reorganize, or prune a software project documentation system: README and docs trees, onboarding, architecture, ADRs, specs, plans, runbooks, reference, archives, and navigation. Use when readers cannot find or trust project docs. Not for application source layout, tool-command governance (use tooling-conventions), or AGENTS.md/CLAUDE.md harness policy (use agent-scaffold).'
---

# Project Docs Organizer

Make project documentation easier to find, trust, and maintain. The target project owns
its information architecture; this skill supplies decision rules and optional patterns,
not a universal directory template.

## Invariants

- Honor a user-selected location and preserve a coherent established convention.
- Prefer the smallest structure that solves observed navigation or ownership problems.
- Keep entry-point READMEs focused on orientation and routing; move durable detail to
  canonical topic pages.
- Give each durable fact one authoritative home and update every active route to it.
- Create directories only for real content or committed near-term work; do not generate
  empty taxonomy scaffolding.
- Delete only with evidence that content is stale, duplicated, superseded, or migrated.
  Archive only when retention has a named value or requirement.

## Workflow

1. Resolve the target project root (the Git top level when Git-backed), then inventory its
   root README, documentation roots, contribution and authority docs, site generators,
   package metadata, CI links, and topic-specific doc locations.
2. Identify actual audiences, document lifecycles, canonical sources, and retrieval
   failures. Distinguish stable guidance from active decisions and historical records.
3. Read [`information-architecture.md`](references/information-architecture.md) and choose
   the smallest fitting model: README-only, named sections, generated-site structure, or
   an optional numbered system.
4. Build a move/merge/delete map before editing. For numbered systems only, read
   [`numbering-patterns.md`](references/numbering-patterns.md) and
   [`zone-catalog.md`](references/zone-catalog.md); never introduce numbering merely
   because the project is large.
5. Apply the reorganization, consolidating duplicates into canonical pages and keeping
   project-specific terminology intact.
6. Follow [`migration-and-links.md`](references/migration-and-links.md) to update navigation,
   backlinks, configs, and stale path references, then run the repository's doc checks.
7. Report the resulting entry points, moves/merges/deletions, deletion evidence, checks,
   and intentionally deferred risks.

## Completion checks

- Each intended audience has an obvious entry point and fastest safe next step.
- Stable guidance, active planning/decisions, generated content, and retained history are
  visibly distinguishable where the project needs those classes.
- Overview pages route rather than duplicate detailed guidance.
- No live link, config, or authority document points at a moved or deleted path.
- No empty zone or placeholder exists solely to complete a taxonomy.
- Every deleted document has explicit evidence and a surviving canonical destination when
  its useful content was retained.

## On-demand references

| Need | Reference |
|---|---|
| Choose between README-only, named, generated-site, or numbered organization | [`information-architecture.md`](references/information-architecture.md) |
| Avoid collapsed categories or meaningless numeric ordering | [`numbering-patterns.md`](references/numbering-patterns.md) |
| Select optional semantic zones for a genuinely numbered documentation system | [`zone-catalog.md`](references/zone-catalog.md) |
| Plan moves/deletions and verify navigation, backlinks, and stale paths | [`migration-and-links.md`](references/migration-and-links.md) |
