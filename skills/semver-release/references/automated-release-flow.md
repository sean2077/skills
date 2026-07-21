# Preferred Automated Release Flow

Read this when a repository has no complete release path, only part of one, or an established
alternative that must be compared with changelog-backed tag-triggered publication.

## Decide whether to adopt it

Inspect the repository's release policy, historical tags, version authorities, changelog or
fragments, tag workflow, notes producer, publisher, permissions, declared outputs, and prior
completion evidence. Treat the complete repository tag as the release identity; it may be
`v1.2.3`, `1.2.3`, `release-1.2.3`, or another project-owned form. Never add or remove a prefix
just to match an example.

- If the observed flow already satisfies this reference, use it without reopening the design.
- **Adoption offer:** if it is missing, partial, or different—including a mature alternative—
  present one concrete current-versus-preferred comparison and ask once whether to retain the
  existing flow or migrate. Maturity alone is not a retention decision.
- If the owner retains an established alternative, follow it for this release. Do not ask again
  in the same task.
- If the owner does not answer, make no changelog-authority, workflow, permission, publisher, or
  release-surface change. Continue only when the retained flow has an unambiguous safe boundary.
- If the owner chooses migration, land and validate that repository-owned setup on the release
  line before selecting or pushing the release tag, then rerun release planning.

The bundled planner currently models `v`-prefixed SemVer tags. An unprefixed or custom tag model
is an explicit analyzer boundary, not permission to rename the repository's tags. Follow the
repository's documented version mapping and the manual path in `version-selection.md`; ask the
owner when that mapping is absent or ambiguous. This limitation does not apply to the extractor,
which treats `--tag` as an opaque exact string.

## Repository-owned contract

1. Select the semantic version and complete tag from repository policy. Synchronize every
   authoritative version file and write one matching canonical changelog section.
2. Gate and commit the complete release snapshot, create the repository-required tag, then push
   the release line and tag without force.
3. Let tag-triggered CI check out that tag's commit and validate release notes before any forge
   Release creation, registry publication, artifact upload, deployment, or external handoff.
4. Extract the trimmed body for exactly one matching heading with the bundled helper or an
   equivalent repository-owned implementation:

   ```bash
   python <skill-dir>/scripts/extract-changelog.py \
     --changelog <changelog-path> \
     --tag "<complete-ci-tag>" \
     --output <temporary-notes-path>
   ```

5. Publish that notes file through the repository's declared publisher. Do not generate fallback
   notes or publish empty notes when extraction fails.
6. Wait for CI and verify that the workflow, published release or artifacts, complete tag, and
   release commit all identify the same release. Report each downstream state separately.

Copy or adapt the extractor into a repository-owned tool path when CI cannot access the installed
skill. The target repository owns that copy, its tests, and future format changes.

## Adaptable GitHub Actions illustration

This is a sequencing example, not a copy-ready universal workflow. Replace the trigger, action
ref, tool path, build, artifacts, permissions, prerelease flags, and verification with the target
repository's approved contract. Omit the forge Release step when another boundary owns completion.

```yaml
name: Release
on:
  push:
    tags: ["<repository-tag-pattern>"]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<repository-approved-ref>
      - name: Validate release notes before publication
        shell: bash
        run: |
          python <repository-tool-path>/extract-changelog.py \
            --changelog <changelog-path> \
            --tag "$GITHUB_REF_NAME" \
            --output "$RUNNER_TEMP/release-notes.md"
      # Run repository-owned build and verification steps here.
      - name: Publish the repository-owned GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create "$GITHUB_REF_NAME" \
            --verify-tag \
            --notes-file "$RUNNER_TEMP/release-notes.md"
      # Verify the Release, artifacts, tag, and checked-out commit here.
```

The exact CI tag is the join key across the workflow trigger, changelog heading, publisher, and
verification. Do not reconstruct it from a package version or assume a `v` prefix.
