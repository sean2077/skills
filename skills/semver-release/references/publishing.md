# Release Publishing and Verification

Read this when deciding how the pushed tag becomes a forge release and proving that publication
finished on the intended commit.

## Detect ownership before pushing

Inspect GitHub/GitLab workflows and project release docs before creating the tag. Prefer an
existing workflow that triggers on version tags and owns artifact building or release creation.
Do not race it with a second manual release. Preserve the workflow's configured release-note
source—committed changelog, fragments, generated notes, or another repository-owned file.

### Tag-triggered release workflow

Push the release branch/trunk, then the tag. Wait for the tag workflow and verify that it created
the expected release and artifacts. Do not substitute the fallback changelog format for a
workflow that already owns another note-generation contract.

If CI succeeds but no release appears, the workflow is incomplete or failed after its visible
jobs; report that as a publication failure rather than treating the tag push as done.

### Direct forge release

Use this only when no tag-triggered release owner exists. Create the release from the already
pushed tag so the forge cannot create a different tag. Pass the repository-owned or prepared
notes file; when the project explicitly uses GitHub-generated notes, use `--generate-notes`
instead of fabricating a committed changelog:

```bash
gh release create vX.Y.Z --title vX.Y.Z --notes-file <release-notes.md> --verify-tag
gh release create vX.Y.Z --title vX.Y.Z --generate-notes --verify-tag
glab release create vX.Y.Z --notes-file <release-notes.md>
```

If the required CLI is unavailable or unauthenticated, stop after the safe pushed state and
report exactly what remains. Do not substitute an unverified web flow.

## Completion evidence

Verify all of the following:

- the release commit is reachable from the intended remote trunk or release line;
- local and remote tags exist and peel to that release commit;
- the tag workflow, when present, completed successfully;
- the forge release exists, is not an unintended draft/prerelease, and targets the tag;
- expected artifacts or deployment handoffs exist when the repository owns them;
- the final release URL is recorded.

Report partial success precisely. A release commit, pushed tag, CI run, forge release, and
deployment are distinct states; never collapse a failure in a later state into “released.”
