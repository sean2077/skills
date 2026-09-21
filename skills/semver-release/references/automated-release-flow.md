# Changelog-backed Release Automation

## Adoption and scope

Use this changelog-backed sequence when the repository owns it or the user authorizes its adoption. For a requested redesign or a demonstrated gap, compare alternatives and agree the affected changelog authority, workflow, permissions, publisher, and completion boundary.

Land and validate an authorized setup change before choosing or pushing its release tag, then rerun release planning. Existing release requests follow the established project flow.

Treat the complete repository tag as the release identity: it may be `v1.2.3`, `1.2.3`,
`release-1.2.3`, or another project-owned form. Do not change a prefix to fit an example.
The planner currently models `v`-prefixed SemVer tags. Preserve custom models and use
`version-selection.md` manually; resolve a missing or ambiguous mapping with the owner.
The extractor treats `--tag` as an opaque exact string, independently of the planner.

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
