# Release Notes and Committed Changelogs

Read this when the repository maintains a committed changelog or direct publication needs a
prepared release-notes file. Skip it when an existing workflow owns note generation end to end.

## Detect the release-note authority

Inspect release docs, existing changelog or fragment directories, and tag workflows before
editing. The repository's existing release-note contract wins:

- update its committed changelog in its current location and format;
- add or compile fragments through the repository's documented tool;
- let the tag workflow or forge generate notes when that is the established owner; or
- prepare a temporary notes file for direct publication without committing a new doc system.

Do not create `CHANGELOG.md` solely because this skill ran. Create or adopt a committed changelog
only when repository policy, the user, or an existing publication consumer requires it.

## Build the selected notes

Use the planner's `release_notes_base` through `HEAD` range. Group commits according to the
repository's format and preserve user-facing wording, required issue links, migration impact,
and breaking-change notices. Omit internal-only detail unless the project normally publishes it.

For a stable promotion after same-version prereleases, follow
[`prerelease-promotion.md`](prerelease-promotion.md): consolidate the full previous-stable-to-HEAD
range when the committed changelog model needs one final section.

## Fallback committed changelog

Use this only when the project explicitly chooses a committed changelog but has no established
shape. Place it at the project-selected path; `<repo-root>/CHANGELOG.md` is a conventional fallback,
not a required location.

```markdown
# Changelog

## [vX.Y.Z] — YYYY-MM-DD

### ⚠ Breaking
- <impact and migration note>

### Added
- <feat subject> (`<short-hash>`)

### Fixed
- <fix subject> (`<short-hash>`)

### Changed
- <refactor or perf subject> (`<short-hash>`)
```

- Omit empty sections and add project-relevant sections such as Docs or Chore only when useful.
- Keep one canonical release section and preserve the file's existing newest-first/oldest-first order.
- Use an unambiguous Git short hash; do not hard-code seven characters when repository scale
  requires a longer abbreviation.
- Insert with a bounded edit; never overwrite an existing changelog wholesale.

If a consumer adopts this fallback heading, extract one version from `## [vX.Y.Z]` to the next
`## [` into a temporary notes file. Otherwise use the consumer's actual parser contract rather
than reshaping the changelog merely to fit this example.
