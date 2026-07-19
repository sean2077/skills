# Release Publishing and Verification

Read this when deciding what repository-owned completion boundary follows the pushed tag and
proving that every applicable publication or handoff finished on the intended commit.

## Declare the completion boundary before pushing

Inspect project release docs, GitHub/GitLab workflows, package or artifact publishers, deployment
handoffs, and prior release evidence before creating the tag. Record which boundary the repository
defines as complete. If policy and evidence are ambiguous, stop before downstream publication and
ask the owner; absence of a tag workflow does not authorize a new forge release. Preserve the
selected owner's release-note source—committed changelog, fragments, generated notes, or another
repository-owned file.

### Tag-only or external handoff

Use a pushed tag as the terminal boundary only when project policy or an explicit user decision
says so. Push the release branch and tag, verify both remote identities, and record any named
external handoff. Do not create a forge release or require a release URL for a tag-only boundary.

### Tag-triggered release workflow

Push the release branch/trunk, then the tag. Wait for the tag workflow and verify the outputs it
actually owns: packages, artifacts, deployments, a forge release, or a downstream handoff. Do not
race it with a second manual publisher or substitute the fallback changelog format for a workflow
that already owns another note-generation contract.

If CI succeeds but an output required by that workflow's contract does not appear, report the
missing output as a publication failure. A workflow that intentionally publishes no forge release
is not incomplete merely because the forge has no release page.

### Project-owned direct publisher

When the repository publishes through an explicit package, artifact, deployment, or internal
release command, use that command and its authentication and preview policy. Verify the published
version or artifact resolves to the release commit/tag. Do not replace a registry or internal
publisher with `gh release create` or `glab release create`.

### Direct forge release

Use this only when GitHub/GitLab is the repository's established public release surface and no
workflow owns release creation. Create the release from the already-pushed tag so the forge cannot
create a different tag. Pass the repository-owned or prepared notes file; when the project
explicitly uses GitHub-generated notes, use `--generate-notes` instead of fabricating a committed
changelog:

```bash
gh release create vX.Y.Z --title vX.Y.Z --notes-file <release-notes.md> --verify-tag
gh release create vX.Y.Z --title vX.Y.Z --generate-notes --verify-tag
glab release create vX.Y.Z --notes-file <release-notes.md>
```

If the required publisher or CLI is unavailable or unauthenticated, stop after the safe pushed
state and report exactly what remains. Do not substitute an unverified web flow or a different
publication surface.

## Completion evidence

Always verify:

- the release commit is reachable from the intended remote trunk or release line;
- local and remote tags exist and peel to that release commit;
- the selected repository-owned completion boundary is explicit.

Then verify only the applicable downstream evidence:

- a tag workflow completed successfully and produced every output it owns;
- a package, artifact, deployment, or external handoff carries the intended version and identity;
- a forge release exists, has the intended draft/prerelease state, and targets the tag;
- each selected surface's URL or immutable identity is recorded when that surface exposes one.

Only the evidence for the selected boundary is mandatory. Do not require a forge release, package,
artifact, deployment, or URL that repository policy does not own.

Report partial success precisely. A release commit, pushed tag, CI run, registry publication,
artifact, forge release, handoff, and deployment are distinct states; never collapse a failure in
an applicable later state into “released.”
