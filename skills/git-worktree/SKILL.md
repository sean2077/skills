---
name: git-worktree
description: Run a worktree-per-change git workflow — create an isolated `.worktrees/<name>` branch for each change, merge it back into the local trunk and clean it up with one command, pushing fast-forward-only and never rewriting history. Use when starting a change in an isolated worktree, finishing/merging one back, cutting a tag-pinned packaging worktree, or listing worktrees. Not for writing commit messages (use conventional-commit) or rewriting history.
allowed-tools: Read, Bash(git:*), Grep, Glob
---

# Git Worktree

Drive a **worktree-per-change** workflow: never edit a trunk (`main` / `release/*`) worktree directly — every change gets its own `.worktrees/<name>` branch cut from the trunk tip, merged back into the local trunk and torn down with one command, pushed fast-forward-only with no history rewrites.

A ready-to-use script ships next to this skill as `worktree.sh`. Prefer it; the manual git steps below are the fallback when the script is unavailable or the user wants to see the raw commands.

## When To Use

Use this skill when the user wants to:

- start a new change in an isolated worktree ("开新 worktree / new worktree / scaffold a branch to work on X")
- finish a worktree — merge it back to trunk and clean up ("合回 / done / merge this back / wrap up this worktree")
- cut a tag- or ref-pinned worktree for packaging/release builds
- list or reason about existing worktrees

Do not use this skill for:

- writing commit messages (use the `conventional-commit` skill)
- rewriting history, force-pushing, or interactive rebase
- opening pull/merge requests

## Invariants

- **Never edit a trunk worktree directly.** Trunks (`main`, `master`, `release/*`, `maintenance/*`) are integration points. The sole exception is when the user explicitly names a trunk for a one-off change in this conversation.
- **One editing session per worktree.** Directory names are not branches — check `git worktree list` and `git status --short --branch` before assuming where you are.
- **`.worktrees/` lives inside the repo and stays out of `git status`.** Worktrees go under `<repo-root>/.worktrees/<name>`, never outside the repo. The script keeps them ignored via the repo-local `.git/info/exclude` (so it never dirties the tracked tree and never blocks a later `done`); for a durable, shared rule, add `.worktrees/` to the committed `.gitignore` yourself.
- **Push is fast-forward-only.** Merge back, then `git push` the trunk. On rejection: `git fetch` + `git merge --ff-only` + retry. Never `--force` — that is the user's backstop, not the agent's.
- **Branch naming is `<type>/<name>`** with `type ∈ {feat, fix, docs, chore}` and `name` lowercase kebab-case.

## Subcommands

The script is `worktree.sh` (shipped beside this file). Trunk defaults to `$WORKTREE_TRUNK` or `main`; override any call with `--trunk <branch>`.

| Intent | Command |
|---|---|
| start a change | `worktree.sh new <name> [--type feat\|fix\|docs\|chore] [--trunk <branch>]` |
| finish a change | `worktree.sh done [--message <msg>] [--no-push] [--keep-branch]` (run inside the worktree) |
| packaging worktree | `worktree.sh release <ref>` |
| list worktrees | `worktree.sh list` |

### `new` — start an isolated change

Creates branch `<type>/<name>` and worktree `.worktrees/<name>` from the trunk tip. Optionally hardlink-shares heavy gitignored dirs (see **Sharing heavy directories**).

Manual equivalent:

```bash
git -C <repo-root> worktree add .worktrees/<name> -b <type>/<name> <trunk>
# keep worktrees out of git status without dirtying the tracked tree:
git check-ignore -q .worktrees || echo '.worktrees/' >> "$(git rev-parse --git-common-dir)/info/exclude"
```

Then verify it is clean: `git -C .worktrees/<name> status --short`.

### `done` — merge back and clean up

Run from inside the worktree. It refuses trunk worktrees and a dirty tree, merges the branch into the local trunk with `--no-ff` (skipping the merge if the branch has zero new commits), removes the worktree + branch, prunes, then fast-forward pushes the trunk.

Manual equivalent (from the trunk worktree, with `<wt>`/`<branch>` filled in):

```bash
git merge --no-ff <branch> -m "Merge <branch>"
git worktree remove <wt> || git worktree remove --force <wt>   # --force when shared dirs hold submodules
git branch -d <branch>
git worktree prune
git push origin <trunk>      # ff-only; on rejection: git fetch && git merge --ff-only origin/<trunk> && retry
```

The merge happens in whichever worktree currently has the trunk checked out — keep that worktree clean.

### `release` — tag/ref-pinned packaging worktree

`worktree.sh release <ref>` creates a detached `.worktrees/release-<ref>` pinned at a tag or commit, so formal packaging builds from a fixed point rather than a moving development tree. Remove it with `git worktree remove --force .worktrees/release-<ref>` when packaging is done.

## Sharing heavy directories

For repos with large untracked/gitignored payloads (`node_modules`, vendored binaries, build caches, submodule checkouts), set `WORKTREE_SHARE` to a space-separated list of repo-relative dirs before `new`/`release`:

```bash
WORKTREE_SHARE="node_modules third_party" worktree.sh new my-change
```

Each dir is **hardlink-copied** (`cp -al`) into the new worktree — zero extra disk — and submodule `.git` pointers inside it are repointed at the shared common git dir so they resolve. Only share dirs that are gitignored/untracked, so the shared copy never pollutes `git status`. Re-running submodule setup inside a worktree (e.g. `git submodule update`) would break the shared inodes — don't.

## Workflow

1. Determine intent (new / done / release / list) from the user's words; if ambiguous, ask one concise question.
2. Confirm where you are with `git worktree list` and `git status --short --branch` before acting.
3. Run the matching `worktree.sh` subcommand (or the manual equivalent). For `new`, pass `--type` matching the change; for `done`, run from inside the target worktree.
4. Report the concrete result: for `new`, the worktree path + branch; for `done`, the merge commit (or "no new commits"), cleanup, and push result; for `release`, the pinned path.
5. Stop before any `--force` push or history rewrite — surface the ff-merge-and-retry path instead and let the user decide.
