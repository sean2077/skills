---
name: semver-release
description: 'Use when a repository needs a SemVer release, version bump, tag, prerelease, stable promotion, or publication verification. Not for one ordinary commit or a feature-branch push.'
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
- Release from a clean attached trunk or repository-approved release line/worktree with no merge, rebase/am, cherry-pick, revert, bisect, or sequencer operation in progress. Supply the expected branch from repository policy with `--release-branch <name>`; the analyzer does not infer it from the remote default branch.
- Preserve the repository's release-note authority: committed changelog, fragments,
  generated notes, or forge-native notes. Do not invent a root changelog by default.
- Use the repository-owned release workflow and obtain authorization for infrastructure changes.
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
   complete and unambiguous, use that established release flow. Read
   [`automated-release-flow.md`](references/automated-release-flow.md) only for a real workflow
   gap or an explicitly requested comparison/adoption. Make no infrastructure change without
   authorization; an ordinary release request does not authorize redesigning its pipeline.
2. Run the bundled read-only analyzer (Python 3.8+):

   ```bash
   python <skill-dir>/scripts/release-plan.py --repo <repo-root> --json [--target vX.Y.Z] [--release-branch <name>]
   ```

   Resolve every `attention` result before mutation. Schema 2's `analyzed` status means only that local `v`-prefixed SemVer analysis completed; repository release policy remains unverified. Inspect `other_format_tags` against that policy instead of treating a candidate as publication approval. Preserve unprefixed or custom tag formats and use [`version-selection.md`](references/version-selection.md) manually when the model does not apply or Python is unavailable; disclose checks that could not run.
3. Follow the repository-owned release-note pipeline. Read
   [`changelog.md`](references/changelog.md) only when the project maintains a committed
   changelog or needs a prepared notes file. Synchronize only authoritative project version
   files using [`version-files.md`](references/version-files.md). For stable promotion after
   alpha/beta/rc tags, also read
   [`prerelease-promotion.md`](references/prerelease-promotion.md). Get the date from the
   environment rather than guessing it.
4. Run repository release gates. Stage every release file and no unrelated path; verify with
   `git diff --cached --check` and short status, create the release commit using the project convention (for example, `release: <exact-tag>`), then require a clean tree. Create the repository-required signed tag or the default annotated tag, push the
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
