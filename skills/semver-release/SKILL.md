---
name: semver-release
description: Cut a semantic-version release from conventional commits — infer the MAJOR/MINOR/PATCH bump since the last tag, update CHANGELOG.md and the project version file, create the release commit and annotated tag, optionally publish a GitHub/GitLab release, and push. Use when the user wants to release, tag a version, bump the version, or update the changelog for a release; handles prerelease (beta/rc) and promoting a prerelease to final. Not for per-commit messages (use conventional-commit) or pushing feature branches.
compatibility: Requires git and a clean release-capable checkout; publishing additionally requires authenticated gh or glab.
---

# Semver Release

Cut a clean semantic-version release: infer the bump from conventional commits, update the changelog and version file, tag, optionally publish a forge release, and push. This is the natural sequel to per-commit work done with the `conventional-commit` skill.

Detailed bump rules, changelog format, and prerelease/promote handling live in `reference.md` — read it when finalizing a prerelease or when the changelog write is non-trivial.

## When To Use

Use this skill when the user wants to:

- release / 发版 / tag a version / bump the version / publish a release
- update `CHANGELOG.md` for a release and tag it
- finalize a prerelease (beta/rc) into a stable version

Do not use this skill for:

- writing a single commit message (use `conventional-commit`)
- pushing a feature branch or opening a PR/MR
- rewriting history or moving an existing tag

## Invariants

- **Tags this skill creates** use `vX.Y.Z` or `vX.Y.Z-<pre>.N` (e.g. `v1.2.0`, `v0.3.0-beta.1`, `v1.0.0-rc.2`). Reject `v1.0`, `0.1.0`, underscores, and build-metadata suffixes on new tags; historical base tags are validated against full SemVer 2.0.0 in step 2.
- **Version file stays semantically in sync with the tag.** Node and Rust manifests use the full SemVer value (`1.2.0-beta.1`); Python uses the equivalent PEP 440 value (`1.2.0b1` / `1.2.0rc1`); CMake's `project(... VERSION ...)` stays numeric and any project-defined prerelease suffix is updated separately. Never publish a prerelease package whose manifest still identifies it as the final release.
- **A tag push is not the finish line.** A tag-triggered release CI (if the repo has one) turns the push into the release; verify the forge release actually appeared and the release commit is on the trunk.
- **Build/publish from a clean trunk**, not a dirty working tree. Refuse a detached HEAD.
- **Never move or overwrite an existing tag.** If the target tag exists, stop and report.

## Workflow

### 1. Preflight

```bash
git status --porcelain          # must be empty
git rev-parse --abbrev-ref HEAD # refuse detached HEAD
git fetch --tags origin
git rev-parse --is-shallow-repository
```

If the branch is not the trunk (`main`/`master`) or a `release/*` line, call that out before continuing. If the shallow-repository check prints `true`, list apparent roots with `git rev-list --max-parents=0 HEAD` and inspect each raw commit with `git cat-file -p <root>`. A true root has no parent header; stop before base selection only if an apparent HEAD root has a raw `parent` header. A repository can remain shallow because of an unrelated ref, so the repository-level flag alone must not block the release.

### 2. Choose base and version

List every `v`-prefixed candidate whose tag commit is HEAD-reachable:

```bash
git tag --merged HEAD --list 'v[0-9]*'
```

Strip exactly one leading `v`, validate every candidate as strict SemVer 2.0.0, then rank all valid candidates by SemVer 2.0.0 precedence. Collect the full set and do not sort or truncate before validation. Git's version sort is configurable and is not a SemVer selector. Peel tied tag objects with `git rev-parse '<tag>^{commit}'`. When highest-precedence tags differ only by build metadata, use their shared commit as `<base>` only if they all resolve to that commit; otherwise stop and report the ambiguity.

Defensively confirm the selected base before collecting commits:

```bash
git merge-base --is-ancestor <base> HEAD
```

Exit status 1 means the selected base is not actually HEAD-reachable; any other nonzero status is a Git error. Stop in either case.

Collect commits since the base, subjects **and** bodies, to infer the bump:

```bash
git log <base>..HEAD --pretty='%h %s%n%b%n---'
```

Infer the bump (highest match wins):

| Trigger in any commit | Bump |
|---|---|
| `!` before the subject colon (e.g. `feat!:`) or an uppercase `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer | **MAJOR** |
| any `feat:` / `feat(scope):` | **MINOR** |
| only `fix:` / `perf:` / `refactor:` / `docs:` / `chore:` / `test:` / `build:` / `style:` / `ci:` | **PATCH** |

Commit types are case-insensitive (`FEAT:` and `feat:` are equivalent). The breaking footer token remains uppercase; treat `BREAKING CHANGE:` and `BREAKING-CHANGE:` as synonymous.

Confirm the computed next version with the user when it is ambiguous or when they may want a prerelease. A first-ever release has no HEAD-reachable valid SemVer base → default `v0.1.0` (or the version file's current value), changelog base = repo root. Prerelease and promote-to-final mechanics: `reference.md`.

### 3. Write release files

- **`CHANGELOG.md`** — insert a new `## [vX.Y.Z] — YYYY-MM-DD` section, conventional-commit grouped (Added / Fixed / Changed / Docs / Chore, breaking changes called out on top). Format + write strategy: `reference.md`. Edit in place; never overwrite the whole file.
- **Version file(s)** — write the ecosystem-canonical release value, including prerelease identity where the ecosystem supports it. Update coupled lockfiles (`package-lock.json`, `Cargo.lock`) through the ecosystem tool when applicable. If the project pins its version in more than one place (a code constant, manifest + lockfile, docs badge), update **all** of them — `git grep -F <old-version>` to find them. The exact mapping and promote-to-final behavior are in `reference.md` → *Version-file sync*.
- Optionally a per-release notes doc if the project keeps one.

Get the date from the environment (`date +%F`); do not guess it.

### 4. Commit, tag, push

```bash
git add CHANGELOG.md <version-file> [release-notes]
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin <branch>
git push origin vX.Y.Z
```

### 5. Publish the release

Two models — detect which the repo uses and prefer the first:

**a. Tag-triggered release CI (preferred when present).** If the repo has a workflow that fires on a version tag — `.github/workflows/*` with `on: push: tags: ['v*']`, or `.gitlab-ci.yml` with a job gated on `$CI_COMMIT_TAG` — then **pushing the tag in step 4 is the finish line**: CI builds the release and extracts this version's CHANGELOG section as the release note. The skill's contract with that CI is the section's shape (`## [vX.Y.Z] — …` up to the next `## [`); keep it clean and do **not** also create the release by hand (that races/duplicates CI). After the push, confirm the workflow ran and the release appeared.

**b. No release CI — create it directly.** Only when no tag-triggered workflow exists, create the release from the **pushed tag** (don't let the forge cut a second tag), body = the new CHANGELOG section:

```bash
gh release create vX.Y.Z   --title vX.Y.Z --notes-file <changelog-section.md>   # GitHub
glab release create vX.Y.Z --notes-file <changelog-section.md>                  # GitLab
```

If neither CLI is available/authenticated, leave the tag pushed and report that the release still needs creating.

To pull one version's section (the CI contract in model **a**, or the `--notes-file` body in model **b**), see `reference.md` → "Extract one version's section".

## Output Contract

Report: the chosen version + bump level and why, the changelog section written, the version-file change(s), the pushed commit and tag, and the forge release URL (or that it was left to tag-triggered CI / skipped / failed). If anything blocked the release (dirty tree, existing tag, ambiguous bump), stop and report it rather than guessing.
