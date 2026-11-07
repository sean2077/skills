# Agent Scaffold Platform Support

## Windows / Git Bash: enable and repair real symlinks

Windows is supported through **Git Bash only**. Install Python 3.8+ and Git for Windows, then use this sequence before running a mutating installer mode. Scaffold-owned Edit/Write hooks invoke `hook-paths.py` through Python. The managed Bash hooks run through `hook-launcher.sh`, which selects Git for Windows `/usr/bin/bash` rather than a native `bash` that may resolve to WSL. `AGENT_SCAFFOLD_BASH` overrides that launcher selection; see [host integration](host-integration.md).

1. Enable Windows **Developer Mode** so non-elevated processes can create native symlinks. Open
   Settings and search for `Developer Mode`; on Windows 11 25H2 and newer the path is
   **System → Advanced → For developers**. Toggle it on and accept the administrator prompt. See
   [Microsoft's current instructions](https://learn.microsoft.com/en-us/windows/advanced-settings/developer-mode).
   If the Settings switch is unavailable, run the documented registry fallback from an
   **elevated PowerShell**:

   ```powershell
   reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" /t REG_DWORD /f /v "AllowDevelopmentWithoutDevLicense" /d "1"
   ```

   Running an elevated Git Bash is the alternative when Developer Mode cannot be enabled. If an
   administrator instead assigns `SeCreateSymbolicLinkPrivilege` directly to the account, sign out
   and back in so Windows creates a new access token; then open a new Git Bash session.

2. Enable native Git symlink checkout. Set the global default once for future clones, then set the
   target repository explicitly because a repo-local `false` overrides the global value:

   ```bash
   git config --global core.symlinks true
   git config --local core.symlinks true
   git config --show-origin --get core.symlinks
   ```

   The last command must report `true`; inspect its origin if it does not.

3. From the target repository root, run the read-only capability probe. Both the file and directory
   probes must pass:

   ```bash
   bash <skill-dir>/agent-scaffold.sh doctor
   ```

4. If Git previously checked a tracked link out as a small target-text file, setting
   `core.symlinks=true` does not rewrite that existing file automatically. For `CLAUDE.md`, first
   require a clean path and confirm that the index mode is `120000`, then remove and restore only
   that path:

   ```bash
   git status --short -- CLAUDE.md
   git ls-files -s -- CLAUDE.md
   # Continue only when status is empty and the index entry starts with 120000.
   rm -f CLAUDE.md
   git checkout -- CLAUDE.md
   test -L CLAUDE.md && test "$(readlink CLAUDE.md)" = AGENTS.md
   ```

   Preserve and resolve the file manually if it has uncommitted content or is not recorded as a
   symlink. For installed harness skill projections, run `bash .agents/relink-skills.sh` after the
   doctor passes; it replaces recognized target-text placeholders but preserves real conflicts.

5. Run the reported mutating mode (`apply` or `upgrade`) with the selected profile, then repeat the
   profile for verification. For example:

   ```bash
   bash <skill-dir>/agent-scaffold.sh apply --profile default
   bash <skill-dir>/agent-scaffold.sh verify --profile default
   ```

   Link creation uses Python `os.symlink`, not MSYS `ln -s`. The installer pins vendored
   shell/Python files to LF and adds repository EOL defaults; existing project-owned files
   keep their bytes. See [line endings](line-endings.md) for editor alignment, exceptions,
   and separately authorized normalization of existing files.
   Capability failure exits 2 before target writes and leaves no copy or partial harness.

## Windows / Git Bash: finish a worktree without leaving a locked directory

Use `done` only for the authorized merge/push/removal lifecycle. It refuses invocation from
the target worktree or a descendant before merging, pushing, or removing it. On Windows it
also checks native delete access to the root directory before mutation. This catches an
already-held root directory even when the command runs from elsewhere; it does not guarantee
that another process or a handle inside a subdirectory cannot block later removal.

Windows locks a process's [current directory against deletion](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory).
Move the **owning persistent shell or Agent process** out first. `git -C`, the helper's own
`cd`, and a `cd` inside a child tool invocation cannot release the parent process's handle.
In an interactive Git Bash shell that owns the directory, run these commands in that shell:

```bash
wt="$(git rev-parse --show-toplevel)"
root="$(dirname "$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir)")"
cd "$root"
bash "$root/.agents/tools/worktree.sh" done --dir "$wt"
```

`new` prints the equivalent command with absolute paths. Cleanup also retries transient sharing violations while the worktree remains registered and clean, then separately retries `rmdir` when Git has already unregistered the worktree but Windows still holds the empty root directory. The defaults are eight retries at one-second intervals; bounded overrides are available when a host needs a longer shutdown window:

```bash
WORKTREE_REMOVE_RETRIES=20 \
WORKTREE_REMOVE_RETRY_DELAY_SECONDS=1 \
bash "$root/.agents/tools/worktree.sh" done --dir "$wt"
```

Longer retries cannot release a persistent process's current-directory handle. If an Agent
host owns it, finish or reopen that session from the primary checkout or another stable
directory. Close other terminals, editors, dev servers, or MCP processes only as appropriate
for their owner; the helper does not terminate them.

For a single-runspace interactive PowerShell that holds the directory, set both locations
in that **same process**, using the actual primary checkout path:

```powershell
$repoRoot = 'C:\path\to\repo'
Set-Location -LiteralPath $repoRoot
[Environment]::CurrentDirectory = (Get-Location).ProviderPath
```

PowerShell's [`Set-Location`](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-location)
changes a runspace location, which is distinct from the process-wide current directory.
Do not apply this process-wide change inside a shared multi-runspace host; reopen that host
outside the target instead. A child PowerShell command cannot change its parent's location.
The worktree helper itself still runs through Git Bash.

### Recover an already-unregistered directory

Git registration and filesystem removal are separate results. If `done` unregisters the
worktree but leaves residue, it exits **3 (cleanup pending)** and keeps the local branch.
Any merge or push already completed remains completed. Do not rerun `done` for this state:
without its `.git` file, Git can discover the enclosing primary repository instead.

After releasing the owning process's handle, run the installed helper from a stable
directory with the **original absolute path**, rather than deriving it from Git inside the
residue:

```bash
root='/c/path/to/repo'
wt="$root/.worktrees/change-name"
cd "$root"
bash "$root/.agents/tools/worktree.sh" cleanup --dir "$wt"
```

`cleanup` only removes an unregistered, ordinary empty directory directly under the primary
checkout's `.worktrees/`; a missing target is already clean. It rejects registered
worktrees, non-empty directories, symlinks/junctions, and paths outside that scope with exit
2; an empty directory still locked after bounded retries returns exit 3. It does not merge,
push, prune registrations, or delete branches. Inspect non-empty or externally
managed residue with its owner. A junction must not be treated as an empty directory:
Windows can [remove the junction itself regardless of its target's contents](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-removedirectoryw).

If the worktree is **still registered**, release its handles and rerun the original `done`
command from outside it instead. The helper validates retry settings before mutation and
never uses `git worktree remove --force` or recursive deletion to overcome a failure.

## Claude Code checkpoint boundary

The harness intentionally uses real symlinks, but Claude Code checkpoint restore does not rewind symlinked or hard-linked files. In this layout that can affect `CLAUDE.md` and entries under `.claude/skills/`: `/rewind` may report success while skipping those paths and leaving the real `AGENTS.md` or `.agents/skills/<name>/` target changed.

After a rewind that touched harness-linked content:

1. Inspect `git status` and `git diff` for the real target, not only the projection path.
2. Reverse the edit explicitly or restore the target from version control.
3. Rerun `bash .agents/relink-skills.sh` when project skill projections changed.
4. Run `agent-scaffold verify`; do not treat checkpoint completion as symlink verification.
