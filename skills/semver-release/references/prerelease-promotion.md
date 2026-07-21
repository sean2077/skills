# Prerelease Promotion

Read this when promoting alpha, beta, or rc tags into a stable release and selecting the
final release-note range, version identity, and any committed-changelog consolidation.

The examples use the analyzer's `v`-prefixed tag model. For an established unprefixed or custom
mapping, apply the same SemVer-core comparison while preserving each complete repository tag;
stop for owner input when the stable/prerelease mapping is not documented and unambiguous.

## Promotion range and identity

When tagging a **stable** `vX.Y.Z` and same-`X.Y.Z` prerelease tags already exist (`vX.Y.Z-beta.N` / `-rc.N` / `-alpha.N`):

- **release-notes base** = the previous HEAD-reachable stable release, or repo root if none exists (skip all same-`X.Y.Z` prereleases), so final notes cover the whole span once regardless of their storage or publication owner.
- rewrite prerelease-aware manifests from their prerelease value to the final value (for example `1.2.0-rc.2` / `1.2.0rc2` → `1.2.0`); CMake clears its separate suffix while retaining numeric `X.Y.Z`.

When the project maintains a committed changelog with one section per prerelease, use a
replace-style update: delete the same-`X.Y.Z` prerelease sections and insert one final section
covering the previous-stable-to-HEAD range. Preserve the project's existing heading and category
format rather than forcing the fallback example from `changelog.md`.

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
