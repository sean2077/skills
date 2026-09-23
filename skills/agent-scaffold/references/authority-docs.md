# Agent Scaffold Authority Documents

## Authority and scope

The root `AGENTS.md` and applicable nested chain govern repository Agent work; root `CLAUDE.md` links to it. Product facts remain owned by code, configuration, specifications, and topic documentation. Higher-priority instructions govern conflicts.

Keep frequently needed commands, non-obvious invariants, ownership boundaries, and useful navigation in the authority document. Route procedures and background to project docs. Update or remove guidance made stale by a durable change, and surface material disagreement when authority is unclear.

## Managed block

Apply and upgrade manage only `<!-- agent-scaffold:start ... end -->`:

- An absent `AGENTS.md` is created with the managed block.
- Existing balanced markers delimit the replacement; surrounding project prose is preserved.
- An existing file without markers receives an appended block.
- Unbalanced, duplicated, or reversed markers abort before mutation.

Keep project-authored guidance outside the markers. The block records the convention selection in its domains marker. The optional terminology section and the convention-guide routes follow that selection; a recorded exclusion
omits only those scaffold-owned lines, not project-authored definitions or policy. The inner worktree boundary belongs to the installer; `--profile light` removes that policy. The managed template uses one paragraph, list item, table row, or command per source line. Project-owned prose is not reflowed.

When only a real `CLAUDE.md` exists, apply adopts its prose into `AGENTS.md` and creates the link. See [retrofit](retrofit.md#adopt-an-existing-claudemd) for conflicting sources and other adoption cases.

## Size feedback

`authority_doc_budget.sh` gives advisory feedback. Defaults are 320 lines / 25,600 characters at the root and 120 lines / 9,600 characters for nested files. Override with `AUTHORITY_DOC_MAX_ROOT`, `AUTHORITY_DOC_MAX_NESTED`, `AUTHORITY_DOC_MAX_ROOT_CHARS`, and `AUTHORITY_DOC_MAX_NESTED_CHARS`.

Use this signal to find redundant or misplaced content; retain guidance whose value warrants its space.

## Project-owned guidance

Add sections that help this project: an overview, recurring development commands, important boundaries, and links to architecture or terminology. The installer preserves that prose; during an authorized full initialization or upgrade, the Agent adopts and fills missing project guidance using [project conventions](project-conventions.md). Initial authorship does not make it a managed template.

Interpret document metadata alongside repository evidence and user intent. Follow an established convention; flat `status` and `updated` are useful starting fields where status/freshness needs to be recorded. The project owns metadata and any extensions.

## Nested contracts

Create a nested `AGENTS.md` for a local command, invariant, ownership, or risk difference. State that difference and link to the nearest existing ancestor contract; sparse trees may require `../../AGENTS.md` or deeper.

Example:

```markdown
<!-- Parent: ../../AGENTS.md -->
# Component guidance

## Local differences

<Commands or boundaries specific to this component.>
```

Check that parent links resolve to the root without cycles. Include purpose or file navigation where it helps apply the local guidance. Existing nested contracts remain project-owned.
