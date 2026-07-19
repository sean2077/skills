---
name: conventional-commit
description: 'Create exactly one local Git commit with a Conventional Commits subject, or return one subject when explicitly asked for message-only output. Use for scoped commit requests and history-aware message selection. Not for releases or tags (use semver-release), pushes or PRs, history rewriting, worktree cleanup, or continuing an in-progress merge, rebase, cherry-pick, revert, or bisect.'
---

# Conventional Commit

Create one scoped local commit or one message-only subject. Treat the skill like
a terse Git command: perform the work, verify it, and avoid narrating routine
message-selection decisions unless the user asks.

## Invariants

- Commit mode creates exactly one local commit and never pushes.
- Resolve the repository root before Git inspection; do not let a subdirectory invocation
  narrow status, history, all-change staging, or post-commit verification by accident.
- Run the attached-HEAD and in-progress-operation preflights before staging anything.
- Stage only the user-owned changes; a named path does not authorize unrelated hunks.
  Preserve unrelated working-tree and index state.
- Use conversation context before rediscovering facts from Git.
- Keep `type` in English and select the summary language from explicit instructions,
  project policy, then relevant repository history; default to English when unclear.
- Never stage secrets or unrelated generated artifacts without explicit authorization.

## Modes

| Mode | Trigger | Effect |
|---|---|---|
| Commit | The user asks to commit, submit, or save current work | Stage the intended scope and create one commit |
| Message-only | The user explicitly asks to draft or suggest a message | Return one subject; do not stage or commit |

## Workflow

1. Select the mode and derive the intended change, file scope, verification evidence,
   and language signals from the current context. Before any Git operation, resolve the
   top level with `git rev-parse --show-toplevel`; preserve the invocation directory long
   enough to normalize user-named relative paths to repository-relative paths.
2. Inspect Git only when those facts are missing, stale, or ambiguous. Read
   [`message-style.md`](references/message-style.md) when type, scope, language,
   breaking notation, or a user-supplied message needs judgment.
3. In message-only mode, return exactly one normalized subject and stop.
4. In commit mode, run `git -C <repo-root> symbolic-ref --quiet --short HEAD` before staging.
   Exit status 1 means detached HEAD; any other nonzero status is a Git preflight
   error. Stop before staging in either case. Then run
   `git -C <repo-root> status --long --branch`; if it reports an in-progress merge,
   rebase, cherry-pick, revert, bisect, or unresolved conflict, stop without completing it.
5. Read [`staging-safety.md`](references/staging-safety.md), stage the exact intended
   changes—including hunk boundaries inside a mixed-ownership path—and verify the actual
   cached patch, not only its file names. Record the current HEAD state and the exact reviewed
   index tree immediately before committing.
6. Commit with the selected subject. Use a message file or stdin when a body,
   trailers, or shell-sensitive text makes inline quoting fragile.
7. Verify status and the recorded subject, tree, and parent boundary as defined in
   `staging-safety.md`; report any mismatch without rewriting history.

## Output contract

- Message-only success: exactly the subject as plain text.
- Commit success: one line, `Committed: <short-hash> <subject>` or its localized equivalent.
- Blocked: one short sentence naming the blocker. Include extra diagnostics only when
  needed to act on a failed verification.

## On-demand references

| Need | Reference |
|---|---|
| Choose language, type, scope, summary, breaking marker, body, or trailers | [`message-style.md`](references/message-style.md) |
| Inspect minimally, protect staged state, stage exact paths, commit, and verify | [`staging-safety.md`](references/staging-safety.md) |
