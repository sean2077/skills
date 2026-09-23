# Project Git, delivery and release conventions

Use the sections whose `git` or `release` domain was selected. Establish the project's actual
policy and executable entries, not a universal Git workflow. Keep guidance in its current home
and route from the Agent entry point. Later tasks use that guidance and native tools directly.

## Git and delivery

Inspect project instructions, contributor docs, hook/configuration and relevant history. Record
whether conventions apply to every commit or the final squash title; retain type/scope language,
summary language, signing, required trailers and attribution choices. Do not infer a mandatory
format from a few commits or impose Conventional Commits on every project. Prefer an existing
host/project setting for attribution rather than repeating a host-specific command recipe.

Use native commit/review tools for ordinary Git work. Preserve the small boundaries not guaranteed
by a generic “commit” request: a named file does not authorize unrelated hunks; inspect the actual
cached patch; never silently include or unstage pre-existing unrelated work. Use an established
safe scoped-index workflow or stop at the ambiguous scope. Existing hooks may change the staged
snapshot: inspect material post-commit differences instead of assuming the reviewed tree survived.
Do not impose a universal one-commit count, attached-HEAD ban or fixed branch/worktree location.
Respect host-managed detached worktrees; establish a durable branch/retention path for delivery.
Do not continue somebody else's merge/rebase or rewrite history as an ordinary commit side effect.

Record the requested completion boundary: local commit, branch, PR/MR or another established
handoff. A commit does not authorize push/merge/release, while a PR request is not complete at a
local commit. Verify the real object, target and reviewed revision; preserve incomplete verification.
Do not install commit linting, change hooks/branch protection, or mutate global user configuration
merely while adopting conventions. Keep credentials and shell-sensitive message data out of syntax.

## Release

When `release` is selected, the installer maintains `.agents/tools/release/`: the complete
release conventions (`README.md`: version selection, version files, notes, prerelease promotion,
publication and completion evidence) plus the read-only analyzer and changelog extractor. That
page is the task-time reference, not setup reading. Do not load it in full during setup, copy it
into project docs, or route to it from resident `AGENTS.md` content. Instead, give the project's
own release documentation one direct route, for example “before any version bump, tag or
publication, read `.agents/tools/release/README.md`”, next to the project-specific facts below.
Those facts win over the page's generic defaults.

Identify stable relationships: version authorities (including per-package/release-line scope),
complete tag format, release-notes authority, signing requirements, supported release branch,
producer commands/CI, destinations and the project's completion evidence. Do not freeze today's
version or the next proposed version in permanent guidance. Preserve changelog/fragments/generated
or forge-native notes; do not create a root CHANGELOG or another publisher by default.

Document existing executable checks before adding new ones. Release inputs, reviewed commit,
version identities, tag and outputs must agree. Preserve clean-snapshot and branch/reachability
rules where the project requires them. Never move/recreate a published tag or race an existing
workflow with manual publication. Unknown publication outcomes need inspection, not a blind retry.
Plan/analyzer success and a tag push are not authorization or proof that publication completed.

State whether completion is a verified remote tag, CI publication, registry/artifact, external
handoff or forge release. Observe every applicable downstream identity and status; do not invent
a missing release surface. An existing annotated/signed-tag policy belongs to this project, not
the scaffold. Keep immutable notes and version sources consistent during prerelease promotion
using the project's supported commands and compatibility rules.

Scaffold setup does not create tags, publish, install a release framework or redesign CI. For a
selected domain with no release flow, write the known boundary (for example “no release process
is defined; publication requires a project decision”) and a minimal proposal where useful; do
not manufacture a release merely to fill coverage. Required tooling changes need their own scope.

The installed copies are committed scaffold runtime, so the route keeps working without the
catalog skill; CI may call the committed extractor directly. Deselecting `release` stops their
maintenance but does not delete them. A consumer must keep or explicitly migrate any direct
dependency on retired `semver-release` skill paths before uninstalling that skill.
