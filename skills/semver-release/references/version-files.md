# Release Version Files

Read this when synchronizing ecosystem manifests, lockfiles, or prerelease identities.

## Version-file sync

Keep the manifest identity aligned with what that ecosystem will publish. A git
tag is not a substitute for a package version: publishing `v0.5.0-beta.1` from a
manifest that says `0.5.0` can occupy or mislabel the final version.

| Ecosystem | Prerelease tag `v1.2.0-beta.1` | Final `v1.2.0` | Coupled files/tooling |
|---|---|---|---|
| Node | `package.json` version `1.2.0-beta.1` | `1.2.0` | update the package lock with the repository's package manager |
| Rust | `Cargo.toml` version `1.2.0-beta.1` | `1.2.0` | let Cargo update `Cargo.lock` when the package is represented there |
| Python | PEP 440 `1.2.0b1` / `1.2.0rc1` (`alpha.N` → `aN`, `beta.N` → `bN`, `rc.N` → `rcN`) | `1.2.0` | update the authoritative static version field; respect dynamic-version tooling |
| C/C++ (CMake) | keep `project(... VERSION 1.2.0)` numeric and update the repo's separate suffix field to `beta.1` | clear the suffix | stop and ask if the project has no defined suffix mechanism but ships prerelease artifacts |
| generic `VERSION` | follow the repo's documented format; default to `1.2.0-beta.1` when it is package-facing | `1.2.0` | update any generated mirrors through their authoritative command |

### Python prerelease mapping boundary

[SemVer 2.0.0](https://semver.org/spec/v2.0.0.html) permits arbitrary valid prerelease
identifiers, while the [Python packaging version
scheme](https://packaging.python.org/en/latest/specifications/version-specifiers/) defines
`a`, `b`, and `rc` as its prerelease phases and gives `.devN` separate ordering semantics.
Therefore `v1.2.0-canary.1` remains a valid SemVer tag for historical base selection and
non-Python ecosystems, but it has no built-in Python mapping here.

For a Python version field, map only the lowercase numbered forms shown in the table by
default. If the repository documents another mapping in its packaging or dynamic-version
tooling, follow that rule and verify the resulting package identity. Otherwise stop before
writing release files, committing, tagging, or pushing. Never silently reinterpret an unknown
label as `.devN`, a local version, or the final release; those forms have different identity or
ordering semantics. This boundary does not narrow full-SemVer historical tag validation or the
values used by Node, Rust, and generic version files.

### Bounded coupled-file updates

Ecosystem tools synchronize release files; they do not own the release commit, tag, or push, and
they must not widen the change into dependency upgrades.

- **Node (single-package npm project with an existing `package-lock.json`).** Inspect
  `preversion`, `version`, and `postversion` before invoking npm. If one is the repository's
  authoritative version-mirror or release flow, follow the repository documentation only after
  confirming it leaves commit/tag/push ownership to this workflow; if that is unclear, stop and
  ask. When those scripts are absent or confirmed unnecessary for release-file synchronization,
  do not hand-edit `package.json` first; run:

  ```bash
  npm version <version> --no-git-tag-version --ignore-scripts
  ```

  Verify that `package.json.version`, `package-lock.json.version`, and, when present,
  `package-lock.json.packages[""].version` all equal `<version>`, then inspect the diff for only
  the intended manifest and lock changes. For workspaces or another package manager, use the
  repository's bounded, documented equivalent instead of guessing.
- **Rust (standalone or shared-version workspace).** First locate the authoritative version source.
  If the member declares `version.workspace = true`, update the root
  `[workspace.package].version` and preserve that inheritance marker; otherwise update the direct
  member `[package].version`. Independently versioned workspaces stay on the repository's release
  tooling boundary below. With an existing `Cargo.lock` that already represents the target package,
  run:

  ```bash
  cargo update --workspace
  cargo metadata --locked --format-version 1
  ```

  The metadata call resolves the dependency graph so `--locked` fails if resolution would change
  the lock; it may fetch according to the repository's Cargo configuration but cannot rewrite the
  lock. Confirm it reports the intended workspace-package version and review `Cargo.lock` so
  unrelated dependency versions remain locked. If the lock is absent, the package is not
  represented, or the pinned Cargo lacks `--workspace`, follow the repository's documented flow or
  stop; never fall back to a bare dependency update or create a lockfile implicitly.

If the project has no version file, skip this step and say so.
