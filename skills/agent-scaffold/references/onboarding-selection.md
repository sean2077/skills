# One-time convention selection

Use for full initialization or an upgrade that may not yet have an accepted convention
selection. This selects **guidance coverage**, not new project policies or permissions.

## First setup or older installation

Run the read-only asset `plan --json` and inspect `guidance_selection`. A managed `AGENTS.md`
block without a domains marker (and no legacy `.agents/scaffold.json`) is `pending`, whether the
harness is new or already installed.
Offer all eight domains together as the default and ask **once**, before full setup writes:

> By default I will establish or maintain documentation, tools, testing, specifications,
> terminology, Git/delivery, release, and environment/collaboration guidance, preserving this
> project's existing choices. Which should I exclude? “None” keeps all eight.

Use the user's language and reuse an explicit selection already supplied in the current
request instead of asking again. Explanations/preview/doctor/verify and an explicitly
runtime-only update do not require this question and do not record a choice. If a full-setup
answer is unavailable, keep it pending; silence is not an answer. Read-only discovery can
continue, but do not implicitly accept all or introduce the conventions.

| Domain ID | Coverage, not a mandatory file or tool |
|---|---|
| `docs` | Documentation ownership, navigation, status and maintenance |
| `tools` | Existing command entries, placement, effects and caller compatibility |
| `testing` | Test design, discovery, trustworthy evidence and scoped test-first policy |
| `specs` | Specification meaning, status, source ownership and observable acceptance |
| `terminology` | Project language, context ownership and incremental glossary maintenance |
| `git` | Commit conventions, change/index scope and the requested delivery boundary |
| `release` | Version/notes authorities, existing publication flow and completion evidence; installs `.agents/tools/release/` for task-time use |
| `environment` | Setup, shared resources, supported platforms and collaboration handoff |

After an accepted answer, pass it to the same planned mutating command:

```bash
# Accepted default: no exclusions
bash <skill-dir>/agent-scaffold.sh apply --domains all
# Example: user excludes release and environment; retain these exact domains
bash <skill-dir>/agent-scaffold.sh upgrade --domains docs,tools,testing,specs,terminology,git
# Explicitly exclude all optional guidance (core harness safeguards still apply)
bash <skill-dir>/agent-scaffold.sh apply --domains none
```

Keep the profile from `plan` if an explicit override is needed. `plan --domains ... --json`
previews the proposed selection without saving. `--domains` is only an interface for an
actual user choice, not permission for the Agent to choose exclusions on its own.

## Persist scope, not a completion claim

The installer records the accepted list in the managed `AGENTS.md` block, beside the profile
marker, when it writes that block:

```markdown
<!-- agent-scaffold:domains=docs,tools,testing,specs,terminology,git,release,environment -->
```

`none` records an empty choice, which is complete, not missing data; an absent marker is
pending. The list is always explicit, never `all`, so a later upstream domain stays unselected.
`AGENTS.md` is tracked, so later sessions and worktrees inherit the decision. The whole block is
scaffold-owned: hand edits to the marker are drift, and scope changes go through `--domains`.

The selection gates domain-scoped assets: each selected domain's generic daily guide in
`.agents/conventions/` with one route in the managed block (release routes to its
`.agents/tools/release/` runtime), the attribution notice for adapted testing/terminology
guidance, and the optional managed terminology section. Excluded domains are not newly authored
or expanded by scaffold, and existing project rules/files remain in force and are not deleted.
Core authority, safe mutation, source/projection, and permission boundaries are not optional.
Existing unselected legacy installations retain their old managed contract until a full setup
records a choice.

Earlier releases stored the choice in `.agents/scaffold.json`. A valid legacy file still counts
as the recorded choice; the next apply/upgrade writes the marker and removes the file. A legacy
file that disagrees with an existing marker is a conflict to resolve, not something to overwrite.

The marker is written with the managed block, before guidance authorship, so an interrupted
setup can resume **without asking again**. It does not certify that any guide was written or
that a host loaded it. Repeat the pending guidance work for selected domains and report gaps
honestly.

## Later updates

For `recorded`, reuse the saved list and omit `--domains`. **Do not repeat the onboarding
question**, append newly offered domains, or infer exclusions from missing directories.
A new upstream domain remains outside an existing explicit list until the user adds it.
A user can explicitly change scope with `--domains`; removing a domain stops future scaffold
maintenance of it, not the project's existing policy or already installed release copies.
No recurring prompt or reset mode.

Malformed, conflicting, unknown-schema or symlinked records are errors, not first-use
signals. Preserve them and recover the accepted scope from the project/history; do not reset
to all, quietly replace them, or start a new preference questionnaire. Narrowly clarify an
unrecoverable conflict rather than re-asking choices already known. A deliberately moved or
removed guide does not remove the selection record or justify restoring its former template.

The CLI never asks questions or reads stdin. Raw asset-only calls without `--domains` remain
noninteractive and do not manufacture a selection; `project_guidance: not-assessed` and the
selection status expose their limits. The Agent is responsible for the one-time dialogue and
for authoring useful, discoverable project guidance within the accepted scope.
