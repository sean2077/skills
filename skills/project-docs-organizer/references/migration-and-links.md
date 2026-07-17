# Documentation Migration and Links

Read this when moving, merging, deleting, archiving, or relinking existing project docs.

## Build the migration map

For every source path, record its destination and action: keep, rename, move, split, merge,
delete, or retain as history. Before deleting, establish at least one of these facts:

- the content is duplicated by a clearly named canonical page;
- the claim or workflow is no longer true and no historical requirement remains;
- all useful material has been migrated into a maintained destination;
- the file is generated residue and its authoritative generator/output policy is known.

Archive only when readers, audits, migrations, or incident review still need the record.
Do not use an archive as a default destination for uncertain clutter; leave uncertain active
content in place and report the unresolved ownership instead.

## Update discovery surfaces

Search and update active references in:

- root and docs-root navigation
- Markdown and code comments
- contribution and maintainer guides
- package metadata and documentation-site configuration
- CI, issue templates, release instructions, and agent authority docs

Use repository search for every moved or deleted path, for example:

```bash
rg -n -F 'old/path.md' <project-root>
```

Treat external wikis or issue trackers as coordination items rather than silently claiming
they were updated. Preserve redirects only when the target project's publishing system or
external consumers require them.

## Verify

Run the repository's existing Markdown, site-build, link, spelling, and navigation checks.
When no checker exists, at minimum verify that:

- every new relative link resolves from its source file;
- no active reference contains an old path;
- navigation reaches each intended canonical page;
- generated docs were changed through their source or documented generator;
- `git diff --check` is clean.

Report deletion evidence and any external surface that still needs coordination.
