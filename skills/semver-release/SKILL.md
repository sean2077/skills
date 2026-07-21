---
name: semver-release
description: 'Cut and publish a SemVer release from conventional commits: choose or validate the target, update project-owned notes and version files, create the release commit/tag, push, and verify the repository-owned completion boundary. Prefer changelog-backed tag-triggered automation for a new release path; preserve or explicitly migrate existing policy. Use for releases, tags, bumps, prereleases, or stable promotion. Not for one ordinary commit (use conventional-commit) or a feature-branch push.'
---

# Semver Release

Drive one release from read-only planning through its verified repository-owned completion boundary. Keep generic
Git and SemVer analysis deterministic; leave version authorities, build commands, signing,
and artifact publication under the target repository's policy.

## Invariants

- A valid exact version supplied by the user is the target; infer a bump only when the user
  did not choose one. Surface conflicts, but do not reopen an explicit release choice.
- Plan without mutation first. Do not edit release files until the base, target, release
  workflow, and version authority are unambiguous.
- Release from a clean attached trunk or repository-approved release line/worktree with no
  merge, rebase/am, cherry-pick, revert, bisect, or sequencer operation in progress.
- Preserve the repository's release-note authority: committed changelog, fragments,
  generated notes, or forge-native notes. Do not invent a root changelog by default.
- Prefer changelog-backed tag-triggered automation only when the repository already owns it or
  the user approves its adoption after a concrete comparison with the current flow.
- Keep every package/version identity semantically aligned with the tag.
- Stage the exact release snapshot, run its gates, and return to a clean tree before tagging.
- Never move, replace, or recreate an existing tag.
- Treat a pushed tag as completion only when repository policy explicitly makes it terminal.
  Otherwise verify every applicable downstream publisher or handoff; never invent a forge,
  registry, artifact, or deployment surface merely because another one is absent.

## Workflow

1. Read repository release policy and inspect the branch, worktree, remotes, version sources,
   complete tag format, changelog or fragments, notes producer, signing requirements, publisher,
   outputs, and release workflows. Fetch tags before selecting a base. When the observed flow is
   missing, partial, or different from the preferred automation, follow
   [`automated-release-flow.md`](references/automated-release-flow.md) and ask once whether to
   retain or migrate; this gate also applies to a mature alternative, and maturity alone is not
   a retention decision. Make no infrastructure change without an answer.
2. Run the bundled read-only analyzer (Python 3.8+):

   ```bash
   python <skill-dir>/scripts/release-plan.py --repo <repo-root> --json [--target vX.Y.Z]
   ```

   Resolve every `attention` result before mutation. The analyzer models `v`-prefixed SemVer tags;
   preserve an established unprefixed or custom tag format and follow
   [`version-selection.md`](references/version-selection.md) manually. If Python is unavailable
   or another custom release model exceeds the analyzer, report the unsupported boundary.
3. Follow the repository-owned release-note pipeline. Read
   [`changelog.md`](references/changelog.md) only when the project maintains a committed
   changelog or needs a prepared notes file. Synchronize only authoritative project version
   files using [`version-files.md`](references/version-files.md). For stable promotion after
   alpha/beta/rc tags, also read
   [`prerelease-promotion.md`](references/prerelease-promotion.md). Get the date from the
   environment rather than guessing it.
4. Run repository release gates. Stage every release file and no unrelated path; verify with
   `git diff --cached --check` and short status, create `release: <exact-tag>`, then require a clean
   tree. Create the repository-required signed tag or the default annotated tag, push the
   release branch/trunk, and push the tag without force.
5. Follow [`publishing.md`](references/publishing.md) and declare the repository-owned completion
   boundary before pushing. Stop at a verified pushed tag only when policy makes it terminal;
   otherwise run or observe the established workflow, publisher, or handoff. Create a direct
   forge release only when the forge is the established release surface and no workflow owns it.
6. Verify local, remote-branch, peeled-tag, and every applicable downstream publisher identity,
   then report the selected version and rationale, files changed, commit, tag, checks, and only
   the URLs or identities that the selected boundary actually exposes.

## On-demand references

| Need | Reference |
|---|---|
| Manual SemVer validation, reachable-base selection, bump inference, or unsupported models | [`version-selection.md`](references/version-selection.md) |
| Node, Rust, Python, CMake, generic version files, and bounded lock synchronization | [`version-files.md`](references/version-files.md) |
| Maintain a committed changelog or prepare a release-notes file | [`changelog.md`](references/changelog.md) |
| Compare, adopt, or run changelog-backed tag-triggered automation | [`automated-release-flow.md`](references/automated-release-flow.md) |
| Consolidate same-version prerelease history into a stable release | [`prerelease-promotion.md`](references/prerelease-promotion.md) |
| Select tag-only, workflow, registry/artifact, handoff, or forge completion and verify it | [`publishing.md`](references/publishing.md) |
