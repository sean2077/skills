# Workspace isolation

Create only workspaces the protocol will own. An externally managed checkout keeps its current lifecycle owner; registering an unrelated worktree by hand is not an adoption mechanism.

```bash
workctl() { python3 "<installed-skill-dir>/scripts/workctl.py" "$@"; }
workctl workspace create task implementation --role writer --path /absolute/task-writer --branch task/implementation --start-point <base> --expect-version <n>
workctl workspace claim task implementation --path-rule 'src/imports/**' --expect-version <n>
workctl workspace create task review --role reviewer --path /absolute/task-review --commit <full-commit-sha> --expect-version <n>
```

Each mutation uses the current owner token and returned version. Writer branches are new and pinned to a resolved base commit. Reviewers use an exact full SHA (40 or 64 hexadecimal characters), a detached checkout, and a clean immutable snapshot. POSIX write bits provide defense in depth; runtime checks remain necessary on platforms or privileged accounts that can bypass them.

## Claims and verification

One writer can own a whole isolated worktree without claiming paths. Multiple writers require conservative, non-overlapping path claims, and each writer's changes are then checked against its own claim. Integration may be performed by the caller or another claimed writer; it does not require a distinct `integrator` role.

`workspace check` and task verification consider committed, staged, unstaged, untracked, and unmerged changes relative to the recorded base. They detect scope escapes, moved/deleted workspaces, reviewer modifications, changed symlink escapes, and overlapping ownership. Shell globs in claim arguments must be quoted.

Run `owner check` before owned actions. `workspace assert-write --cwd <path>` checks that the selected context is a writer rather than a review snapshot; it does not grant a lease or sandbox arbitrary shell commands. Keep one active writer for a mutable surface.

## Removal and stale records

`workspace remove` verifies identity, cleanliness, merge status, and active-work constraints before removal. Run it from outside the target checkout. Preserve a dirty or unmerged workspace unless the user authorized the actual loss; `--force --reason <text>` records that explicit exception. Removing a workspace does not itself authorize a merge or push.

A failed registration attempts non-forced Git cleanup. Work arriving concurrently is preserved, even if it leaves an unregistered worktree or branch to inspect. Do not force-remove that residue just to make the failed operation disappear.

Use `workspace prune-stale --reason <text>` only for a recorded path that no longer exists and is no longer registered by Git. A moved, foreign, dirty, or still-registered checkout needs reconciliation rather than silent pruning. Terminal tasks still allow authorized cleanup and lease release.
