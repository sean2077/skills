# Document Metadata

Read this when choosing or interpreting document metadata. These are starting points and
judgment principles, not a schema, fixed lifecycle, or development gate.

## Start small

For a project without an existing convention, two optional top-level YAML fields are usually
enough:

```yaml
---
status: needs-revision
updated: "2026-09-08"
---
```

`status` describes the document's current condition. Values such as `draft`, `needs-revision`,
`active`, or `superseded` are examples, not a required vocabulary or transition sequence.
`updated` records the last meaningful content update when known; it is a freshness clue,
not proof of review, approval, or correctness. Omit dates that cannot be established.

## Read and maintain in context

Consider metadata together with the content, current code, relevant decisions, and user
intent. Check the source header when a retrieved excerpt leaves that context unclear.
A revision-needed plan normally supplies discussion context rather than settled requirements;
an explicit request to revise or try it can still guide the task without making it generally
approved. Keep consequential uncertainty visible instead of applying a fixed status filter.

Missing metadata alone neither establishes trust nor blocks work. Use available evidence and
project conventions to judge what is usable, and seek clarification when an unresolved
substantive decision matters, not merely because a field is absent.

Keep metadata aligned with meaningful content or status changes. Polishing or moving a draft
does not approve it. Preserve existing fields, and update metadata links when moving docs.

Project Agents choose which documents benefit, how they are organized, what fields and values
mean, and how to use them. Prefer an established convention over renaming or bulk migration.
Add a flat field, such as a scope or replacement link, only for a concrete project need; avoid
nested metadata frameworks. Respect formats with their own frontmatter, including `SKILL.md`,
and edit generated documentation through its source. No extra policy file or validator is
needed just to adopt these principles.
