# Prerelease Promotion

Read this when promoting beta or rc tags into a stable release and consolidating their changelog history.

## Promote-and-merge (prerelease → stable)

When tagging a **stable** `vX.Y.Z` and same-`X.Y.Z` prerelease tags already exist (`vX.Y.Z-beta.N` / `-rc.N` / `-alpha.N`):

- **changelog base** = the previous HEAD-reachable stable release, or repo root if none exists (skip all same-`X.Y.Z` prereleases), so the final section covers the whole span in one place.
- **CHANGELOG write is replace-style**: delete the same-`X.Y.Z` prerelease sections and insert one new `## [vX.Y.Z] — YYYY-MM-DD` covering the full previous-stable..HEAD range. A reader sees one consolidated `[vX.Y.Z]` section instead of stitching `beta.1`/`beta.2`/`rc.1` together.
- rewrite prerelease-aware manifests from their prerelease value to the final value (for example `1.2.0-rc.2` / `1.2.0rc2` → `1.2.0`); CMake clears its separate suffix while retaining numeric `X.Y.Z`.

Illustration:

```markdown
# before
## [v0.5.0-rc.1] — 2026-02-02
## [v0.5.0-beta.1] — 2026-01-20
## [v0.4.2] — 2026-01-10     ← keep

# after
## [v0.5.0] — 2026-02-10     ← consolidated v0.4.2..v0.5.0
## [v0.4.2] — 2026-01-10     ← keep
```

Tagging a prerelease itself (`v0.5.0-beta.2`, `v0.5.0-rc.1`) does **not** merge — it appends and leaves older prerelease sections in place.
