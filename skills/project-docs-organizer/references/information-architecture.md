# Documentation Information Architecture

Read this when selecting the documentation container, primary axis, secondary lenses, decision
depth, and numbering behavior before proposing or applying a reorganization.

## Start with the smallest container

| Project evidence | Smallest fitting container |
|---|---|
| One main reader, short setup, little durable detail | Focused root `README.md` |
| Several durable topics or reader routes | Existing documentation root with project-owned names |
| A documentation generator already owns navigation | Preserve its content and navigation model |
| No coherent convention and a dedicated tree is justified | Create a project-named docs root; use `docs/` only as the neutral fallback |

Honor the user's explicit location first. Otherwise preserve a coherent `docs/`, `doc/`,
`documentation/`, generated site, or other established root. Do not normalize paths merely
because another project uses a different convention.

## Gather boundary evidence

Record evidence before naming categories:

- reader roles, prerequisites, permissions, and fastest safe tasks;
- recurring goals, workflows, search terms, and support or incident routes;
- domain capabilities, vocabulary conflicts, decision owners, and handoff contracts;
- products, subsystems, interfaces, and the mental model readers already use;
- stable guidance, active proposals, decisions, generated material, and retained history;
- canonical sources, generator or publishing constraints, and observed retrieval failures.

Do not turn this list into six peer directory axes. Read
[`classification-methods.md`](classification-methods.md), shortlist only lenses supported by
the evidence, and keep the project's own terminology.

## Scale the decision evidence

Use the smallest artifact that preserves the decision boundary:

- **Compact inline decision delta** — use for a bounded move, merge, deletion, relink, or entry-point
  repair when the documentation container, primary axis, ownership, lifecycle, and numbering remain
  unchanged. Record the observed retrieval or duplication issue, the governing boundaries that stay
  fixed, the affected paths/actions, deletion evidence when applicable, and the verification plan.
- **Full Documentation IA Decision Record** — use when the change selects or changes a container,
  primary axis, ownership or lifecycle topology, numbering policy, multi-area navigation model, or
  when several viable structures need comparison, or when project policy or the user explicitly
  requires the full record.

A small patch is not automatically compact: use the full record when it establishes a durable new
boundary. A large mechanical link repair is not automatically full when no IA decision changes.

## Choose one primary axis per level

Compare candidate lenses qualitatively:

- **Reader-route separation**: will readers usually remain inside one group?
- **Vocabulary and ownership cohesion**: does one owner or language govern the material?
- **Lifecycle consistency**: can content in the group evolve under compatible trust rules?
- **Stability under change**: will the boundary survive normal product or team changes?
- **Duplication pressure**: does the choice give each fact one canonical home?

Choose one primary axis for each relevant tree level. A different subtree may choose a
different primary axis. Keep secondary lenses as local subgroups, navigation or generated
views, metadata, or validation rules; do not create a Cartesian-product hierarchy or duplicate
canonical content to simulate multiple views.

## Run a proportionate placement check

For a full record, place representative current documents and plausible new documents into the
candidate design. It passes only when:

- each sample has one obvious canonical home;
- common reader routes avoid unrelated branches;
- ownership or lifecycle changes do not require unrelated moves;
- no category exists only to complete the method; and
- secondary lenses remain usable without duplicating content.

For a compact delta, verify that the destination is already governed by the existing axis and
owner, the change leaves one canonical home, and no new category or lifecycle rule is introduced.

If the check fails, refine the primary axis or choose a smaller container. If a high-impact
choice remains tied, present two or three candidates with their evidence, migration cost,
tradeoffs, and a recommendation, then wait for the user before mutation. For a minor,
reversible tie that preserves semantic ownership, use and report the smallest coherent change.

## Record a full decision

When the full record is required, report before presenting the proposed tree:

1. project evidence and retrieval failures;
2. candidate lenses and why each was considered;
3. the primary axis at every relevant level;
4. secondary lenses and how readers access them;
5. rejected alternatives and their failure modes;
6. whether numbering is enabled and the evidence for that decision; and
7. the proposed tree plus move, merge, delete, and retention actions.

## Keep entry points as routers

The root README should identify the project, intended readers, fastest safe start, and routes
to deeper user and contributor material. A docs-root README or generated landing page should
map the available areas and distinguish stable, active, generated, and historical material.
Link to canonical setup, architecture, ADR, tool, and runbook pages instead of duplicating them.

## Decide numbering after semantics

README-only projects have nothing to number. Preserve an explicit user choice, a coherent
established convention, or documentation-generator-owned ordering. When creating or materially
reorganizing a dedicated tree with no governing convention, treat the absence of a convention as
permission to choose, not evidence for numbering. Enable local numbering only when the full record
shows that a stable sibling display or reading order improves an observed reader route and the
navigation benefit exceeds path/link churn; otherwise keep semantic paths unnumbered. Read
[`numbering-patterns.md`](numbering-patterns.md) when that evidence exists. Reconsider an existing
convention only when evidence shows that it causes the retrieval or ordering failure being solved.
