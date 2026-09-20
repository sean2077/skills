# Documentation Information Architecture

Read this when existing conventions do not settle a material documentation structure or ownership choice. Routine maintenance can use the entry-point contract without this design exercise.

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

Use the evidence relevant to the changed boundary before naming categories; this is a menu, not a required questionnaire:

- reader roles, prerequisites, permissions, and fastest safe tasks;
- recurring goals, workflows, search terms, and support or incident routes;
- domain capabilities, vocabulary conflicts, decision owners, and handoff contracts;
- products, subsystems, interfaces, and the mental model readers already use;
- stable guidance, active proposals, decisions, generated material, and retained history;
- canonical sources, generator or publishing constraints, and observed retrieval failures.

Do not turn this list into six peer directory axes. Consult
[`classification-methods.md`](classification-methods.md) only when candidate groupings need
comparison; use supported lenses and the project's own terminology.

## Scale the decision evidence

Reuse decisions already established in the task or project. A bounded move, merge, deletion,
or relink needs a clear reason, preserved useful content, and verified consumers, not a new
inline record or form. Explain any consequential choice where it naturally belongs in the
existing plan, PR, or design.

For material changes to the container, primary axis, ownership, lifecycle, or numbering,
compare viable options and their actual migration costs. Use a full Documentation IA Decision
Record only when the project/user requires it or an unresolved cross-cutting choice warrants
one. Neither file count nor a new directory automatically requires a separate artifact.

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

For a new or materially changed structure, try representative affected documents and plausible additions. Check that:

- each sample has one obvious canonical home;
- common reader routes avoid unrelated branches;
- ownership or lifecycle changes do not require unrelated moves;
- no category exists only to complete the method; and
- secondary lenses remain usable without duplicating content.

For bounded maintenance, verify the affected destination, canonical ownership, and live routes. Do not invent hypothetical future documents for a straightforward link repair.

If the check fails, refine the primary axis or choose a smaller container. Ask for a decision
when authority or a costly-to-reverse consequence remains unresolved. When the user delegated
the choice, choose and explain the best-supported option within that authority rather than
requiring a second approval merely because alternatives exist.

## Preserve consequential rationale

When a durable decision record is needed, capture the retrieval problem, selected structure,
important rejected alternatives, and migration/retention/verification consequences. Omit
irrelevant fields and avoid duplicating an existing approved record. No universal seven-field
record or presentation order is required.

## Keep entry points as routers

The root README should identify the project, intended readers, fastest safe start, and routes
to deeper user and contributor material. A docs-root README or generated landing page should
map the available areas and distinguish stable, active, generated, and historical material.
Link to canonical setup, architecture, ADR, tool, and runbook pages instead of duplicating them.

## Decide numbering after semantics

README-only projects have nothing to number. Preserve an explicit user choice, a coherent
established convention, or documentation-generator-owned ordering. In a new or materially
reorganized tree, the absence of a convention is permission to choose, not evidence for
numbering. The enable gate weighs a stable sibling display or reading order against path/link
churn; read [`numbering-patterns.md`](numbering-patterns.md) for the full gate and sibling-local
tokens. Reconsider an existing convention only when evidence shows that it causes the retrieval
or ordering failure being solved.
