# Session entry and task workspace

## Separate three decisions

| Decision | Meaning | Default |
|---|---|---|
| Session entry | Directory in which the user or host starts the Agent | Task checkout for new implementation/review; primary checkout remains valid for planning or an existing conversation |
| Task checkout | Exact checkout whose code, instructions, tests, and diff this task concerns | Reuse the explicitly assigned checkout; discover rather than assume it from session cwd |
| Lifecycle owner | User, workbench, or helper responsible for creation, integration, and removal | Keep the existing owner; do not introduce a second manager |

A linked Git worktree has the repository's tracked files at its own revision, not just
a subset of the primary checkout. Starting there does not inherently lose project-wide
context. It makes relative paths and checks naturally refer to the task revision.
Starting in the primary checkout can preserve a long-lived planning session, but task
reads, edits, reviews, and commands then need explicit paths. Neither layout is an OS
sandbox, and neither authorizes overlapping writers.

The scaffold's default profile accepts both entry styles. `--profile light` removes
worktree governance; it is not a prerequisite for external worktrees or a session-entry
selector. A workbench's UI label "workspace" does not prove Git isolation: verify whether
it is a linked checkout, the primary checkout, or a parent containing multiple repos.

## Inspect before acting

Use the user/host-assigned absolute path when available. Otherwise inspect the current
checkout and task context before choosing a target. These are read-only probes:

```bash
task="/absolute/path/to/task-checkout"
git -C "$task" rev-parse --show-toplevel
git -C "$task" rev-parse --path-format=absolute --git-dir --git-common-dir
git -C "$task" worktree list --porcelain
git -C "$task" status --short --branch
git -C "$task" rev-parse HEAD
```

`--show-toplevel` identifies that checkout, not necessarily the primary worktree.
Use Git's registry and repository identity, not directory names, a presumed `.git/`
directory, or `dirname(git-common-dir)` as a universal primary-path resolver. Bare repos
and separate Git directories need their owner's layout-aware workflow; do not assume
the scaffold's conventional-primary-checkout lifecycle helper fits those layouts.
For a multi-repository workspace, identify each affected repository and its task
checkout separately. Do not treat the UI's parent directory as one Git repository.

Confirm the assigned branch/base and task before writing. Do not replace a dirty assigned
checkout, switch its branch, or start a new task there just because it is already linked.
An existing suitable linked worktree fulfils worktree-per-change regardless of who
created it or whether its path is `.worktrees/<name>`, a sibling, or a host cache.
Do not create a nested worktree or move it merely to match the scaffold's example path.

## Keep task context local to its revision

Read the task checkout's root and applicable nested `AGENTS.md`, declared terminology,
relevant project skills, and verification commands. Previously loaded higher-priority
instructions still apply: surface conflicting guidance rather than silently replacing it
with another branch's instructions. In a primary-entry session, give every file tool an
unambiguous task path and every command its explicit task cwd (or documented subdirectory).
A `cd` inside one tool invocation does not reconfigure the Agent session, reload its
instructions/skills, or extend its sandbox. Use the host's approved access or reopen a
task-local session if it cannot safely reach the target; never work around permissions.

Give peers the exact task path, intended base, and revision under review. For uncommitted
review also state that the live diff is the target; a commit SHA alone does not identify
uncommitted changes. Avoid concurrent edits during a live-diff review or refresh stale
findings. One active writer owns each shared mutable surface; a second session is not a
second independent copy of the files.

Keep tracked `.agents/`, `.claude/`, `.codex/`, `AGENTS.md`, and glossary files versioned
with the task. Preserve the scaffold's relative projections, including
`CLAUDE.md -> AGENTS.md`; do not symlink entire tracked harness directories back to the
primary checkout. That would make a task consume another branch's rules or edit its
files. Check actual host skill discovery and trust in the chosen checkout. Having the
files on disk alone does not prove that a particular host loaded or approved them.

Ignored secrets, local settings, dependencies, and caches are a separate setup concern.
Use the project's or workbench's approved setup command; do not blindly copy credentials,
overwrite host settings, or share mutable artifacts between concurrent writers. Avoid
rerunning scaffold installation in every task solely because its directory is new.
Commit an authorized harness upgrade and let future worktrees inherit that revision.

## Leave lifecycle and delivery with their owner

When the workbench/user supplied the task worktree, let that owner integrate, archive,
and remove it. No scaffold adoption command or ownership flag is required to edit a
suitable assigned linked worktree. The trunk guard remains enabled and tests the edited
path's primary/linked role; it is not a worktree-ownership registry or a full filesystem
security boundary.

Only when the scaffold owns creation and no task checkout is assigned, use the installed
`worktree.sh new` helper. It records its resolved local trunk, which need not equal a
workbench's chosen remote base. Do not infer delivery policy from either session cwd or
that trunk record.

`worktree.sh done` merges into local trunk, pushes, and removes the worktree. Do not use it
as a generic "task finished" action, to clean up an externally managed worktree, or in
place of a requested PR/MR. `--no-push` still merges and cleans up. For PR/MR delivery,
leave the review branch and checkout available until their owner authorizes cleanup.
Before removal, release processes using the directory; changing a child shell's cwd
cannot release an Agent or terminal's Windows directory handle.

## User choice and migration

Keep a durable preference in project-owned `AGENTS.md` prose outside the managed block,
or give a task-specific instruction. These are examples, not config keys or parsed modes:

> Prefer new implementation/review sessions in the assigned task worktree. Keep primary
> sessions for cross-task planning. Existing workbench worktrees remain workbench-owned.

> Keep my existing session in the primary checkout. Before task work, identify the
> assigned absolute task path and use it for file tools, commands, and peer review.
> Do not move or replace the session; retain the task worktree's current lifecycle owner.

Preserve an existing preference unless the user changes it. When no preference or task
placement is given, recommend a task-local session without manufacturing a mandatory
setup question. Ask only when target, authority, ownership, or destructive intent cannot
be resolved safely from the supplied task and repository evidence.

For an existing scaffold, run the updated installed skill's `plan` and indicated
`apply`/`upgrade`, then `verify`, in the authorized task checkout with the same selected
profile. Review project-owned prose for old "always create `.worktrees/`" or "always
run `done`" rules; upgrade preserves that prose rather than silently overriding it.
Commit source and generated changes through the normal review path. Existing sessions
may need to explicitly read the updated contract or restart according to their host;
no automatic session migration, permission change, or state rebinding is performed.
