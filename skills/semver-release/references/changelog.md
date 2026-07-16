# Release Changelog

Read this when creating, updating, or extracting a release section from CHANGELOG.md.

## CHANGELOG.md

### Location and header

`<repo-root>/CHANGELOG.md`. Create it if missing with this header (then add releases below it, newest first):

```markdown
# Changelog

All notable changes to this project are documented here. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/), with conventional-commit grouping.
```

### Per-release entry

```markdown
## [vX.Y.Z] — YYYY-MM-DD

### ⚠ Breaking
- <short description of the breaking change and its impact>

### Added
- <feat subject> (`<short-hash>`)

### Fixed
- <fix subject> (`<short-hash>`)

### Changed
- <refactor / perf subject> (`<short-hash>`)

### Docs
- <docs subject> (`<short-hash>`)

### Chore
- <chore / build / test / style / ci subject> (`<short-hash>`)
```

Rules:

- Type → section: `feat`→Added, `fix`→Fixed, `refactor`/`perf`→Changed, `docs`→Docs, `chore`/`build`/`test`/`style`/`ci`→Chore. Breaking changes get the top **⚠ Breaking** section.
- **Omit empty sections** (no `_(none)_` placeholders).
- Keep the subject verbatim, including scope (`fix(api): …` stays `fix(api): …`).
- 7-char short hash (`git rev-parse --short`).
- Within a section, newest commit first.

### Write strategy

Do not overwrite the whole file with `>`:

1. Read the current `CHANGELOG.md` (if absent, create with header + this entry).
2. Use an edit that keeps the header block intact and inserts the new section **immediately after the header**, above the previous newest release.

### Extract one version's section (release-note contract)

A tag-triggered release CI — or a `--notes-file` body — pulls just the current version's block out of `CHANGELOG.md`. The stable contract is "from `## [vX.Y.Z]` up to the next `## [`":

```bash
awk -v v="vX.Y.Z" '
  $0 ~ "^## \\[" v "\\]" { p=1; print; next }
  p && /^## \[/          { exit }
  p                      { print }
' CHANGELOG.md > release-notes.md
```

Keep the heading shape exactly `## [vX.Y.Z] — YYYY-MM-DD` so this extraction — and common GitHub release actions / GitLab `release:` jobs — reliably finds the block.
