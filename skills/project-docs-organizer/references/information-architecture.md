# Documentation Information Architecture

Read this when choosing the documentation root and deciding whether the project needs a
README-only, named-directory, generated-site, or numbered organization.

## Choose from evidence

| Project evidence | Smallest fitting model |
|---|---|
| One audience, short setup, little durable history | Focused root `README.md` |
| Several stable topics or audiences, modest doc count | Existing docs root with plain reader-oriented names |
| A documentation generator already owns navigation | Preserve its content and navigation model |
| Large long-lived corpus where stable grouping and sort order both matter | Optional semantic numbered zones |

Use the user's explicit path first. Otherwise prefer a coherent existing documentation
root; create `docs/` only when no convention exists and a dedicated tree is justified.
Do not rename `doc/`, `documentation/`, or generator-owned paths merely to normalize them.

## Classification dimensions

Choose boundaries from real differences in:

- audience: user, integrator, contributor, maintainer, operator
- lifecycle: stable guidance, active proposal, decision record, generated output, retained history
- ownership: source-maintained, tool-generated, externally synchronized
- retrieval: task, subsystem, workflow, reference lookup, incident response

Prefer reader tasks and lifecycle over file-format or team-name buckets. A directory is
justified when it has multiple durable pages, a distinct owner/lifecycle, or meaningful
navigation value.

## Entry-point roles

The root README should identify the project, intended users, fastest safe start, and routes
to deeper user and contributor material. A docs-root README or generated landing page should
map the available areas and distinguish stable, active, generated, and historical material.

Neither entry point should duplicate long setup guides, architecture descriptions, ADRs,
tool manuals, or runbooks. Link to one canonical page instead.

## When numbering helps

Use numbering only when maintainers want durable grouping plus deterministic ordering and
will preserve its semantics. Do not add it solely because the corpus is large. When selected,
read [`numbering-patterns.md`](numbering-patterns.md) and
[`zone-catalog.md`](zone-catalog.md) before designing the tree.
