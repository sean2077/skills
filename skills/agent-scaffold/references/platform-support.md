# Agent Scaffold Platform Support

Read this only for platform prerequisites, Windows and Git Bash setup, real-symlink failures, or degraded checkouts.

## Windows / Git Bash: enable and repair real symlinks

Windows is supported through **Git Bash only**. Install Python 3.8+ and Git for Windows, then use
this sequence before running a mutating installer mode:

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
   shell/Python files to LF; project-owned hook-manager files keep their existing line endings.
   Capability failure exits 2 before target writes and leaves no copy or partial harness.
