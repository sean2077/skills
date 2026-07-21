# Release Notes and Committed Changelogs

Read this when the repository maintains a committed changelog, a tag workflow consumes one, or
direct publication needs a prepared release-notes file. Skip the template when an existing
workflow owns note generation independently of a changelog.

## Detect the release-note authority

Inspect release docs, existing changelog or fragment directories, and tag workflows before
editing. The repository's existing release-note contract wins:

- update its committed changelog in its current location and format;
- add or compile fragments through the repository's documented tool;
- let the tag workflow or forge generate notes when that is the established owner; or
- prepare a temporary notes file for direct publication without committing a new doc system.

Do not create `CHANGELOG.md` solely because this skill ran. Create or adopt a committed changelog
only when repository policy, the user, or an existing publication consumer requires it.

Keep the semantic version and complete repository tag distinct. The tag may be `v1.2.3`,
`1.2.3`, `release-1.2.3`, or another documented form; preserve it exactly in the changelog and
publisher instead of adding or removing a prefix.

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

## [<exact-tag>] — YYYY-MM-DD

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

`<exact-tag>` is the complete stable or prerelease tag supplied by the repository, not a fixed
`vX.Y.Z` shape. For example, `## [v1.2.3] — 2026-07-21`,
`## [1.3.0-rc.1] — 2026-07-21`, and `## [release-1.2.3] — 2026-07-21` are all valid when they
match the actual tag exactly.

## Extract the preferred-flow notes

When a repository adopts this fallback heading for the preferred automated flow, extract the
trimmed body after the one matching heading through—but not including—the next level-two heading.
Do not include the release heading itself in the notes file. The bundled reference implementation
treats the complete tag as an opaque exact string:

```bash
python <skill-dir>/scripts/extract-changelog.py \
  --changelog <changelog-path> \
  --tag "<complete-tag>" \
  --output <temporary-notes-path>
```

The command must fail before publication when the exact heading is missing, duplicated,
malformed, tag-mismatched, calendar-invalid, or empty. It never falls back to generated notes and
does not modify an existing output unless all validation succeeds. See
[`automated-release-flow.md`](automated-release-flow.md) for adoption and CI ordering. Otherwise
use the consumer's actual parser contract rather than reshaping the changelog to fit this example.
