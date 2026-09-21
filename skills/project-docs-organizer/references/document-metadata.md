# Document Metadata

Follow the project's existing metadata convention. For documents that need status and freshness context, a small flat header is a useful starting point:

```yaml
---
status: needs-revision
updated: "2026-09-08"
---
```

`status` describes the document's condition, using values meaningful to the project. `updated` records the last meaningful content change when known. Interpret both alongside the content, current implementation, relevant decisions, and user intent; a date is not proof of review or correctness.

A proposal or superseded plan can inform discussion without becoming settled implementation guidance. Check the source header when an excerpt loses that context, and expose consequential uncertainty.

Update metadata when the document's meaning or status changes. Moving or polishing a draft does not approve it. Preserve useful project fields and repair replacement/source links during migration.

Add flat fields where they serve an actual consumer. Respect formats with their own frontmatter, including `SKILL.md`, and edit generated documentation through its source.
