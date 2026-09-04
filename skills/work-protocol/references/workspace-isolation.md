# Workspace isolation

Read this only when adding writers, reviewers, path claims, integration, cleanup, or stale-worktree recovery.

## Create fixed or writable worktrees

```bash
WORKCTL="python3 <installed-skill-dir>/scripts/workctl.py"
SHA=$(git rev-parse HEAD)

$WORKCTL workspace create <task-id> review \
  --role reviewer --path ../review-<task-id> --commit "$SHA" \
  --expect-version <n>

$WORKCTL workspace create <task-id> worker-a \
  --role worker --path ../worker-a --branch <task-id>/worker-a \
  --start-point "$SHA" --expect-version <n>

$WORKCTL workspace claim <task-id> worker-a \
  --path-rule 'src/imports/**' --expect-version <n>
```

Roles are `driver`, `worker`, `reviewer`, and `integrator`. Writable roles require a new branch. A reviewer requires a full 40- or 64-hex commit, is created detached at that exact commit, and is checked for cleanliness and immutability. POSIX write bits are removed as defense in depth; runtime verification remains authoritative on platforms or privileged accounts that can bypass them.

## Parallel ownership

Every additional writable workspace should claim paths before editing. Claims are conservative: parent/child and potentially overlapping globs conflict. Reviewers cannot claim writable paths. At most one integrator may exist. Use the integrator as the sole merge/conflict authority rather than allowing workers to merge each other opportunistically.

Run this guard from a writer before mutation:

```bash
$WORKCTL workspace assert-write <task-id> --cwd "$PWD"
```

`workspace check` verifies the registered path, Git common directory, role, branch or detached commit, resolved base ancestry, cleanliness requirements, and path claims. It evaluates committed, staged, unstaged, unmerged, and untracked paths and rejects changed symlinks that resolve outside the workspace.

## Cleanup

```bash
$WORKCTL workspace remove <task-id> worker-a \
  --merged-into HEAD --expect-version <n>
```

Normal removal requires a registered, unmoved workspace with no unresolved merge, no unsafe dirty state, and—where applicable—a branch merged into the declared target. `--force` still requires `--reason`; the reason and forced flag are appended to evidence. Use `prune-stale` only when both the filesystem path and Git worktree metadata prove the record is stale.
