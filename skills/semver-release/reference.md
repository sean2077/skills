# semver-release — reference

On-demand depth for bump selection, the CHANGELOG format, and prerelease handling. The resident `SKILL.md` covers the common path; read this when finalizing a prerelease or when the changelog write is non-trivial.

## Choosing the next version

### Bump inference (highest match wins)

Read subjects **and** bodies (`git log <base>..HEAD --pretty='%h %s%n%b%n---'`):

| Trigger | Bump | Example |
|---|---|---|
| `!` before the subject colon (`feat!:`, `fix!:`) or an uppercase `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer | MAJOR | `0.4.2 → 1.0.0` |
| any `feat:` / `feat(scope):` | MINOR | `0.4.2 → 0.5.0` |
| only `fix:` / `perf:` / `refactor:` / `docs:` / `chore:` / `test:` / `build:` / `style:` / `ci:` | PATCH | `0.4.2 → 0.4.3` |

Commit types are case-insensitive (`FEAT:` and `feat:` are equivalent). The breaking footer token remains uppercase; treat `BREAKING CHANGE:` and `BREAKING-CHANGE:` as synonymous.

Pre-1.0 caution: many projects treat a breaking change before `1.0.0` as a MINOR bump rather than jumping to `1.0.0`. When the repo is still `0.y.z`, confirm with the user before auto-promoting a breaking change to `1.0.0`.

### When to cut a prerelease

Default to a stable release. Use a prerelease only when the user wants a preview round:

- **customer/early trial** — ship to a few users first, gather feedback, then finalize → `v0.5.0-beta.1` … `v0.5.0`.
- **large change, want a bubble** — before a MAJOR, collect a round → `v1.0.0-rc.1` → `v1.0.0-rc.2` → `v1.0.0`.

Prerelease increment rules:

- first beta: `-beta.1`; subsequent under the same `vX.Y.Z`: `-beta.2`, `-beta.3`.
- beta → rc: switch prefix and restart at `.1` → `v0.5.0-rc.1`.
- final: drop all suffixes → `v0.5.0`.

### Base selection

Before enumerating tags, run `git rev-parse --is-shallow-repository`. In a shallow repository that flag covers every ref, so a repository-level `true` is not sufficient to prove that HEAD history is incomplete. List each apparent HEAD root with `git rev-list --max-parents=0 HEAD`, then inspect its raw commit headers before the first blank line with `git cat-file -p <root>`. A true root has no `parent` header; an apparent root whose raw object still records a `parent` is a HEAD-reachable shallow boundary. Stop before base selection only if an apparent HEAD root has a raw `parent` header, then deepen or unshallow the checkout; fetched tag refs alone do not restore missing ancestry. Never interpret tags hidden by such a boundary as a first release.

Enumerate every HEAD-reachable `v`-prefixed candidate first with `git tag --merged HEAD --list 'v[0-9]*'`. Strip exactly one leading `v`, then validate the remainder as full SemVer 2.0.0 before ranking it. Historical base tags may use the full specification even though this skill deliberately creates the narrower stable or numbered-prerelease forms documented in `SKILL.md`.

Strict validity requires:

- exactly three numeric core identifiers with no leading zeroes (except `0` itself);
- non-empty prerelease identifiers containing only ASCII alphanumerics or hyphens, with no leading zeroes in numeric identifiers;
- optional non-empty build identifiers containing only ASCII alphanumerics or hyphens.

Thus `v01.2.3` and `v1.2.3-rc.01` are invalid. Reject them before ordering or truncating the candidate set.

Rank valid candidates by SemVer 2.0.0 precedence: compare major, minor, and patch numerically; a prerelease is lower than the matching stable version; compare prerelease identifiers numerically when both are numeric, otherwise by the SemVer numeric/non-numeric and ASCII rules. For example, `v1.1.0-rc.1 < v1.1.0`. Build metadata is valid but build metadata does not affect precedence. Git's `version:refname` order is not SemVer precedence and can change with `versionsort.suffix`, so never use Git version sort (or `sort -V`) as the selector.

Peel each tied tag object with `git rev-parse '<tag>^{commit}'`. When highest-precedence tags differ only by build metadata, use their shared commit as `<base>` only if they all resolve to that commit; otherwise stop and report the ambiguity.

Before using the result, run `git merge-base --is-ancestor <base> HEAD`. Status 1 means it is not HEAD-reachable; another nonzero status is a Git error. Stop instead of choosing a different tag by incidental list order.

- For a **prerelease** (`v0.5.0-beta.2`): base = the previous HEAD-reachable valid SemVer tag (including an earlier prerelease of the same version). The CHANGELOG appends a new section; older prerelease sections stay (fragmentation is expected during a preview round).
- For a **stable** `vX.Y.Z` when same-`X.Y.Z` prereleases exist: see **Promote-and-merge** below.
- First-ever release means there is no HEAD-reachable valid SemVer base: base = repo root (`git log` with no range, or `--root`); default start tag `v0.1.0` or the version file's current value.

## Version-file sync

Keep the manifest identity aligned with what that ecosystem will publish. A git
tag is not a substitute for a package version: publishing `v0.5.0-beta.1` from a
manifest that says `0.5.0` can occupy or mislabel the final version.

| Ecosystem | Prerelease tag `v1.2.0-beta.1` | Final `v1.2.0` | Coupled files/tooling |
|---|---|---|---|
| Node | `package.json` version `1.2.0-beta.1` | `1.2.0` | update the package lock with the repository's package manager |
| Rust | `Cargo.toml` version `1.2.0-beta.1` | `1.2.0` | let Cargo update `Cargo.lock` when the package is represented there |
| Python | PEP 440 `1.2.0b1` (`alpha.1` → `a1`, `rc.1` → `rc1`) | `1.2.0` | update the authoritative static version field; respect dynamic-version tooling |
| C/C++ (CMake) | keep `project(... VERSION 1.2.0)` numeric and update the repo's separate suffix field to `beta.1` | clear the suffix | stop and ask if the project has no defined suffix mechanism but ships prerelease artifacts |
| generic `VERSION` | follow the repo's documented format; default to `1.2.0-beta.1` when it is package-facing | `1.2.0` | update any generated mirrors through their authoritative command |

If the project has no version file, skip this step and say so.

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

## Out of scope

- **Signed / GPG tags** — this skill creates an annotated tag (`git tag -a`). If the project requires signed tags, swap in `git tag -s` (with a configured signing key) by hand.
- **Monorepo / multi-package versioning** — version-file sync assumes one project version. For independently-versioned packages in one repo, run the release per package (or use a dedicated monorepo release tool); this skill does not coordinate multiple version lines under one tag.
