<!-- agent-scaffold:convention=docs -->
# Documentation conventions

Generic guide installed and refreshed by agent-scaffold; do not edit it here. The project's
own documentation, navigation, and nested `AGENTS.md` files win where they are more specific;
record project-specific facts there, not in this file. Use the sections relevant to the task;
an isolated wording fix does not need an inventory, migration plan, or reader exercise.

## Find the owner before writing

- Follow the project's documentation map or navigation to the page that owns the fact. Keep
  one owner per detailed contract and link to it from overviews, recipes, and entry points
  instead of repeating it.
- Preserve the existing layout, language, filenames, numbering, and frontmatter. A directory
  name is a clue, not authority; do not restructure while making an unrelated content change.
- Change generated output (API references, rendered sites, inventories) through its generator
  or source, never by patching the output.
- Leave content owned by a Wiki, another repository, or a symlinked location with that owner;
  do not copy it in or write through it without authority.
- Add a page only for a distinct responsibility and link it from the existing navigation;
  otherwise extend the owning page. Do not seed empty directories or template catalogs.

## Choose structure from reader tasks

For a material reorganization, inspect the affected readers, recurring tasks, search terms,
ownership, lifecycle, and site-generator constraints. Scope the inventory to the change;
a focused README can suffice for a small project. Compare viable groupings only where a
meaningful choice remains unresolved:

| Grouping | Useful when | Watch for |
|---|---|---|
| Reader role | Prerequisites, permissions, or outcomes differ | Duplicating shared facts across roles |
| Task or journey | Readers seek an outcome or incident procedure | Hiding stable owners inside cross-cutting workflows |
| Domain and ownership | Concepts and decisions have distinct owners or lifecycles | Mistaking team names or source folders for domain boundaries |
| Product or interface | Readers recognize stable products, APIs, CLIs, or SDKs | Path churn from incidental implementation boundaries |
| Content purpose | Learning, how-to, explanation, and reference need different treatment | Fragmenting a small coherent page just to fill categories |
| Lifecycle and authority | Proposals, current contracts, generated output, and history differ | Status buckets that leave subject ownership unclear |

Use representative documents and reader tasks to test whether homes are predictable, owners
are clear, and routine changes avoid unrelated moves or excessive nesting. Subtrees may use
different groupings; secondary routes should link to the same canonical information. Retain
consequential rationale in the existing decision process or PR, not a mandatory new record.
Use delegated authority; surface costly unresolved choices without blocking independent safe work.

Keep the root README focused on orientation and a useful start. A docs landing page exposes
setup, design, development, and operational routes where applicable, and distinguishes current
guidance from proposals, generated copies, and history. Neither needs to duplicate the manuals.

### Optional local ordering

Preserve coherent numbering or generator-owned navigation. Add numeric prefixes only when a
stable sibling reading/display order justifies path and link churn. Name groups by meaning;
`10-`, `20-`, and `30-` leave insertion gaps, and `00-` can mark a genuine first stop. A prefix
is a sibling position, not a universal category code. Files, directories, both, or neither may
be numbered; deeper ordering needs its own reader benefit. Reconcile consumers after renumbering.

## Current, intended, and historical content

- Distinguish implemented behavior, approved intent, drafts, and history. A plan, an
  approval, or a recent edit is not evidence of implementation. Compare current code and
  verified contracts with intended behavior; surface material disagreement rather than
  silently treating either a proposal as implemented or an implementation defect as policy.
- Keep dated evidence (release notes, validation records, measurements, external
  comparisons) as history with its date and source revision; do not rewrite it to match the
  present.
- When a plan is completed or superseded, stop it from instructing readers: keep its useful
  rationale and a pinned historical source, and point to the current owner. Use the project's
  status convention; do not keep completed steps as a parallel operating manual.
- One-off plans and audits normally belong in the issue or PR, not a permanent page, unless
  they record a durable decision.

### Lightweight metadata

Follow the project's convention. When status or freshness would otherwise be ambiguous, a
small flat header can help; neither these fields nor these status values are mandatory:

```yaml
---
status: needs-revision
updated: "2026-09-08"
---
```

`status` describes the document's condition in project terms; `updated` records the last
meaningful content change when known, not proof of review, approval, or correctness. Interpret
them alongside content, implementation, relevant decisions, and user intent. When a search
excerpt omits this context, inspect the source header before using it as implementation guidance.

Update metadata when meaning or status changes; moving or polishing a draft does not approve
it. Preserve useful project fields and repair source/replacement links in them during migration.
Add flat fields only for an actual consumer, not a universal schema or lifecycle gate. Formats
with their own frontmatter, including `SKILL.md`, permit only fields within that schema;
change generated metadata through its source.

## Merge, prune, and migrate safely

For each affected source, identify its action and destination: keep, rename, move, split,
merge, delete, or retain as history. A small change can keep this map in the working diff or PR;
do not introduce a permanent inventory. Before deleting, establish that useful content is
preserved at a named maintained destination, is already duplicated by its canonical owner,
is no longer true and has no remaining historical need, or is generated residue with a known
source/output policy. Mere age or an unfamiliar filename is not deletion evidence.

Archive only for an identifiable reader, audit, migration, or incident-review need. Do not
use an archive as a dumping ground for uncertain active content; preserve the ambiguous part
and report unresolved ownership. Merges preserve unique facts, qualifications, rationale,
and metadata meaning; reorganization does not adopt the documents' decisions.

Search old paths, relevant filename variants, and changed headings across active consumers,
including hidden configuration directories. Update navigation/backlinks, Markdown and code
comments, contributor guides, package metadata, docs-site configuration, CI, issue templates,
release instructions, and applicable Agent authority routes. For example, from the task checkout:

```bash
rg -n --hidden --glob '!.git/**' -F -- 'old/path.md' .
```

Rebase relative links from each moved page's new location, reconcile incoming anchors, and
update generators rather than managed projections. Preserve deliberate historical references
as history instead of blanket-replacing old paths. Redirects need a publishing-system or
external-consumer reason; they are not automatic compatibility wrappers. Treat external Wikis,
issue trackers, and inaccessible consumers as coordination gaps, not surfaces already updated.

## Changing documentation

- Update the owning page in the same change as the behavior it describes, and fix readers,
  links, and callers when content moves. Preserve unique content when merging pages.
- Take flags, routes, fields, and schemas from their implementation authority (source,
  `--help`, registrations, parsers), not from other prose. Check command cwd and effects before
  execution; even discovery wrappers are not automatically safe to run.
- Keep entry points such as root READMEs and `AGENTS.md` lean: route to detail rather than
  duplicate it. Keep translated entry points equivalent when the project maintains them.
- Recheck primary sources before changing an external claim; retain its applicable date/version
  and actual review date. An editorial edit alone is not a fresh external verification.

## Verification

Run applicable project Markdown, site-build, link, spelling, and navigation checks. Without
checkers, inspect changed relative links and anchors from their source files, active references
to removed paths, and navigation to the intended owners; run `git diff --check`. Existing
checkers may miss external links or anchors and do not prove semantic accuracy or runnable
examples. Review affected commands safely and report which were executed versus only inspected.

For a material reorganization, walk a realistic reader journey using only the resulting entry
points, not the editing conversation: for example, starting at README, find authentication
setup and identify the page that owns the requirement. Repair dead ends or missing context;
a fresh reader/subagent is optional, not a fixed reviewer count or approval gate.

Report resulting entry points, significant moves/deletions and their evidence, checks, and
unresolved external consumers or risks. A plausible directory tree or green link check alone
is not evidence that a reader can find the right current contract.
