# Semantic Version Selection

Read this when selecting a release base, inferring a bump, choosing a prerelease, or checking unsupported release models.

## Analyzer first

After fetching tags, prefer the bundled read-only analyzer:

```bash
python <skill-dir>/scripts/release-plan.py --repo <repo-root> --json [--target vX.Y.Z]
```

It checks clean/attached state, active Git operations, incomplete shallow history, reachable
strict-SemVer tags, equal-precedence build-metadata ambiguity, conventional-commit bump signals,
target availability, and prerelease decisions. Resolve its `attention` entries before mutation.
The manual rules below are the fallback and the review contract for the analyzer.

For a manual fallback, an attached branch and empty `git status --porcelain` are not sufficient:
run `git status --long --branch` and stop if it reports a merge, rebase/am, cherry-pick, revert,
bisect, sequencer, or unresolved-conflict state. Finish or abort the owning Git operation before
release planning; never turn its pending commit into a release commit.

When the user supplied an exact valid target, keep it as the selected version. Compare it with
the inferred bump and report any mismatch, but ask only when the requested value is invalid,
already exists, not newer than the reachable base, or conflicts with project release policy.

## Choosing the next version

### Bump inference (highest match wins)

Read subjects **and** bodies (`git log <base>..HEAD --pretty='%h %s%n%b%n---'`):

| Trigger | Bump | Example |
|---|---|---|
| `!` before the subject colon (`feat!:`, `fix!:`) or an uppercase `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer | MAJOR | `0.4.2 → 1.0.0` |
| any `feat:` / `feat(scope):` | MINOR | `0.4.2 → 0.5.0` |
| only `fix:` / `perf:` / `refactor:` / `docs:` / `chore:` / `test:` / `build:` / `style:` / `ci:` | PATCH | `0.4.2 → 0.4.3` |

A multi-parent commit without its own Conventional Commit or breaking-footer signal remains in
the JSON report with `kind: "merge"` for audit, but it does not become an unclassified bump
blocker; its child commits carry the version signal. A merge commit with an explicit conventional
or breaking signal is classified normally.

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

- For a **prerelease** (`v0.5.0-beta.2`): base = the previous HEAD-reachable valid SemVer tag (including an earlier prerelease of the same version). Release notes cover that incremental range. If the project maintains a committed changelog, append its next section and retain earlier prerelease sections during the preview round.
- For a **stable** `vX.Y.Z` when same-`X.Y.Z` prereleases exist: see **Promote-and-merge** below.
- First-ever release means there is no HEAD-reachable valid SemVer base: base = repo root (`git log` with no range, or `--root`); default start tag `v0.1.0` or the version file's current value.

## Unsupported models

- **Signed / GPG tags** — follow the repository's signing policy; the generic analyzer does not
  create or verify signatures.
- **Monorepo / multi-package versioning** — version-file sync assumes one project version. For independently-versioned packages in one repo, run the release per package (or use a dedicated monorepo release tool); this skill does not coordinate multiple version lines under one tag.
