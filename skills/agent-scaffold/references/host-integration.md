# Agent Scaffold Host Integration

## Contents

- [Hook semantics](#hook-semantics)
- [Dual-host wiring](#dual-host-wiring)
- [Hook configuration reconciliation](#hook-configuration-reconciliation)
- [Codex project trust and hook review](#codex-project-trust-and-hook-review)
- [Integration troubleshooting](#integration-troubleshooting)

## Hook semantics

Both scaffold-owned hooks read the tool-call JSON on **stdin**. Host configs invoke **one** Python 3.8+ process whose command is **host-specific**, because each host decides who expands the command string before the shell runs it:

- **Claude Code and Grok** (`.claude/settings.json`) run `python -X utf8 "${CLAUDE_PROJECT_DIR}/.agents/tools/hooks/hook-paths.py" --guard|--budget`. Both hosts inject `CLAUDE_PROJECT_DIR` (Grok's `GROK_WORKSPACE_ROOT` is an alias, set on every hook) and expand `${VAR}` in `command` themselves before the shell sees it, so the anchored path is independent of the hook `cwd` — which follows a `cd`, a worktree, or a temp directory. The command must **not** use bash's `${VAR:-default}`: Grok does not implement that modifier, the unexpanded text reaches Windows PowerShell, `${CLAUDE_PROJECT_DIR:-.}` there names an undefined PowerShell variable, and the path collapses to `/.agents/...` — which Python on Windows opens as `C:\.agents\...`.
- **Codex** (`.codex/hooks.json`) runs `python -X utf8 .agents/tools/hooks/hook-paths.py --guard|--budget`. Codex injects no project-root variable and expands nothing, and its PowerShell empties every `$VAR`/`${VAR}` it sees, so the command carries **no `$`** and stays cwd-relative; Codex runs hooks from the project root.

Quoting only a project-root placeholder (`"${ROOT}"/.agents/...`) is valid bash concatenation but splits on Windows, so Python receives the repository directory and fails with `can't find '__main__' module`. Both commands keep `.agents/tools/hooks/hook-paths.py --guard|--budget` contiguous, which is the reconciler identity; the light-profile filter matches `--guard` on that script after stripping quotes. That avoids a Git-alias plus Bash launcher on every Edit/Write. `hook-paths.py` parses the payload, converts `C:/…`, backslash, UNC, Git Bash, relative, spaces, and Unicode paths in-process, and classifies the checkout from `.git` (a directory is the primary worktree; a `gitdir:` file is a linked worktree). The budget hook returns immediately unless a payload path is `AGENTS.md` or `CLAUDE.md`. The trunk guard skips per-file Git identity probes for edits already inside a linked worktree; `git check-ignore` runs only when a same-repository primary-worktree edit might be blocked. The parser accepts payloads up to 16 MiB without copying them into an environment variable or process argument. Each hook only acts on files in the **project repo** (same git-common-dir as the resolved project root), so edits to nested/sibling repos pass through; gitignored paths are exempt. `hook-launcher.sh` and `hook-common.sh` remain installed for project-owned Bash hooks. `hook-common.sh` still exposes `hook_extract_paths` and `cygpath` conversion for format-on-edit. Missing compatible Python, malformed/non-UTF-8/oversized input, or another parse failure exits 2 for `--guard` because the guard cannot prove that the requested edit is safe; the advisory PostToolUse budget reports the same failure and exits 0. The budget hook emits PostToolUse `additionalContext` JSON itself and does not call `jq`.

### trunk_edit_guard.sh — PreToolUse, blocking

- Installed and wired only by `--profile default`; `--profile light` removes the scaffold-owned wiring.
- **Exit 0** allow · **exit 2** block (message on stderr). Invalid hook transport/input also exits 2; other unexpected host errors are reported according to host semantics.
- Blocks non-ignored project edits in the **primary worktree**; its checked-out branch is the active trunk regardless of branch name. Linked worktrees pass unless another guard applies.
- **Escape hatches** (only when the user explicitly authorizes a trunk edit):
  - `WORKTREE_ALLOW_TRUNK_EDIT=1` — one-shot env bypass.
  - `touch <repo>/.claude/allow-trunk-edit` — flag file, auto-expires **2 h** (mtime check `now - mtime <= 7200`); re-touch to renew.
- `WORKTREE_GUARD_CMD` overrides the command shown in the block message (default `bash .agents/tools/worktree.sh`).

### authority_doc_budget.sh — PostToolUse, advisory (never blocks)

- Watches `AGENTS.md` / `CLAUDE.md` writes; resolves the `CLAUDE.md → AGENTS.md` symlink so each contract is measured once.
- Line and character budgets plus the four `AUTHORITY_DOC_*` override variables are documented in [`authority-docs.md`](authority-docs.md).
- Over budget → emits a nudge as PostToolUse `additionalContext` JSON. Always **exit 0**.

## Dual-host wiring

Both hosts invoke the **same** enabled `hook-paths.py` entry under `.agents/tools/hooks/`, but each host's command string is its own: Claude Code and Grok anchor on `${CLAUDE_PROJECT_DIR}`, Codex stays cwd-relative with no `$`. The hot path never looks up `bash` and cannot land on the Windows WSL launcher. Python resolves the repository root inside `hook-paths.py` from its own location and Git, so only *locating the script* depends on the host. Python 3.8+ on `PATH` is a harness prerequisite. `hook-launcher.sh` remains available for project-owned Bash hooks that still need Git for Windows `/usr/bin/bash`; `AGENT_SCAFFOLD_BASH` overrides that Bash only. The PreToolUse examples below describe the default worktree profile; the lightweight profile omits `--guard` while retaining `--budget`.

**Claude Code — `.claude/settings.json` shape** (the canonical full command strings live in `assets/host/claude.settings.json`). Grok reads this same project file through Claude compatibility and expands the same anchor:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit|MultiEdit|Write|NotebookEdit",
        "hooks": [ { "type": "command", "command": "python -X utf8 \"${CLAUDE_PROJECT_DIR}/.agents/tools/hooks/hook-paths.py\" --guard" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          { "type": "command", "command": "python -X utf8 \"${CLAUDE_PROJECT_DIR}/.agents/tools/hooks/hook-paths.py\" --budget" }
        ] }
    ]
  }
}
```

**Codex — `.codex/hooks.json`:** matcher `Edit|Write|apply_patch`; Codex injects no project-root variable and expands nothing, so the command carries no `$` and stays cwd-relative (Codex runs hooks from the project root); `hook-paths.py` resolves the repository root internally from Git/install depth:

```json
{ "type": "command",
  "command": "python -X utf8 .agents/tools/hooks/hook-paths.py --guard",
  "statusMessage": "Checking worktree policy" }
```

`hook-common.sh` still resolves the project independently from the managed runtime path, using `$CLAUDE_PROJECT_DIR` when supplied and Git/install depth otherwise:

```bash
raw="${CLAUDE_PROJECT_DIR:-$(git -C "$hook_dir" rev-parse --show-toplevel 2>/dev/null || (cd "$hook_dir/../../.." && pwd))}"
proj="$(hook_posix_path "$raw")"
```

## Hook configuration reconciliation

Apply/upgrade refresh scaffold-owned hook definitions without clobbering user hooks. The Python reconciler parses JSON, removes only entries whose command invokes the exact owned paths under `.agents/tools/hooks/` (`trunk_edit_guard.sh`, `authority_doc_budget.sh`, and `hook-paths.py`), then merges the current assets by event plus complete group metadata and deduplicates complete hook objects. Verification compares the complete managed hook object, including `type`, `command`, `statusMessage`, and future JSON fields, so execution-affecting drift cannot hide behind an unchanged command string. Basename lookalikes and every command outside those exact current paths remain project-owned. Case-equivalent spellings reconcile only when the target filesystem resolves them to the same installed hook; case-distinct paths remain user-owned. `--profile light` omits the guard and removes its scaffold-owned entry while leaving every user command and unrelated config key intact. Empty scaffold-owned events are removed rather than written as empty matcher groups. Python is a harness prerequisite, so this path has no jq-dependent behavior or unsafe paste fallback.

Harness-owned runtime, hook JSON, authority-contract, ignore, and attributes updates are written
to unique siblings in the destination directory, flushed, and atomically replaced. An interrupted
candidate write therefore leaves the previous project file intact; fixed project-owned `.tmp`
paths are never claimed. Package scripts, CI jobs, and hook-manager configuration are project-owned;
see [subagent drift integration](subagents.md#project-owned-drift-integration).

**Idempotency keys:** scaffold-owned path identity + complete event/group/hook JSON; `.gitignore` lines by `grep -qxF`; the `AGENTS.md` harness section by the `<!-- agent-scaffold:start … end -->` markers.

## Codex project trust and hook review

Codex applies two independent gates to this scaffold:

1. **Project layer trust.** Codex skips project-local `.codex/` config, hooks, and rules until the repository is trusted. The scaffold also writes project-scoped agent projections; verify their discovery after trust instead of treating file presence alone as proof that the host loaded them. Trust through the host prompt, or record the repository in user config:

   ```toml
   # ~/.codex/config.toml
   [projects."<repo absolute path>"]
   trust_level = "trusted"
   ```

2. **Exact hook-definition review.** Scaffold command hooks are project-local, non-managed hooks. Even after project trust, open `/hooks`, inspect their source and command, and trust the exact definitions before expecting them to run. Codex records this trust against a hash; `upgrade` can legitimately change the hash, after which the hook is skipped until reviewed again.

`plan`/`verify` can report these reminders but cannot assert or automate user trust. The scaffold creates `.codex/hooks.json` because that file carries scaffold-owned dual-host wiring. In Codex terminology these project hooks are non-managed hooks; “managed hooks” are policy-distributed definitions. The scaffold does **not** create a project `.codex/config.toml`: repository settings are project-owned and user trust belongs in the host/user layer. Existing config files are preserved; create one only when the project needs actual settings.

## Integration troubleshooting

- **Hooks don't fire in Codex**: trust the project, open `/hooks`, review/trust the exact current hook definitions, confirm the matcher, then confirm `python` and the cwd-relative `.agents/tools/hooks/hook-paths.py --guard` command resolve from the project root. Project-owned Bash hooks still use `hook-launcher.sh` and Git for Windows `/usr/bin/bash`. Hook commands do not depend on checkout executable bits.
- **Grok `pre_tool_use`/`post_tool_use` timeouts on Windows**: Grok observe hooks default to 5 seconds. Scaffold host JSON sets `timeout` to 30. Host JSON invokes Python directly. The guard skips per-file Git probes inside a linked worktree, and the budget hook returns immediately unless the path is `AGENTS.md` or `CLAUDE.md`. `hook-paths.py` accepts both `tool_input` and Grok `toolInput`. Restart the host session after upgrade so it reloads project hooks.
- **`can't find '__main__' module in '<project root>'`**: Windows PowerShell split a `"${CLAUDE_PROJECT_DIR:-.}"/.agents/...` command so Python received the repository directory as the script. The managed command quotes the entire anchored path. Run `upgrade` and restart the host session.
- **Hooks don't fire in Claude Code**: validate `.claude/settings.json`, confirm the command path,
  and restart the host session after changing settings.
- **`can't open file 'C:\\.agents\\tools\\hooks\\hook-paths.py'`**: a command reached Windows PowerShell with `${CLAUDE_PROJECT_DIR:-.}` or a bare `$VAR` still in it, and PowerShell emptied the reference, leaving `/.agents/...` on drive `C:`. The managed Claude/Grok command keeps only `${CLAUDE_PROJECT_DIR}`, which both hosts expand themselves; the managed Codex command carries no `$` at all. Run `upgrade` and restart the host session.
- **`can't open file '.../.agents/tools/hooks/hook-paths.py': No such file or directory`**: the host's hook `cwd` drifted off the project root (a `cd`, a worktree, or a temp directory) and a command that depends on `cwd` resolved against it. The managed Claude/Grok command anchors on the host-expanded `${CLAUDE_PROJECT_DIR}` and is cwd-independent; only the Codex command is cwd-relative, and it expects Codex's project-root hook `cwd`. If an older `python -c`, `${CLAUDE_PROJECT_DIR:-.}`, or bare relative command is still installed, run `upgrade` to converge it. A host that injects no project-root variable leaves `/.agents/...`, which fails loudly rather than resolving elsewhere.
- **The installer rejects an existing hook config**: repair the named JSON file. Mutating modes
  require a regular file, strict UTF-8 JSON, an object at the top level, and well-typed hook arrays.
- **Scaffold-owned hook entries are duplicate or stale**: run `upgrade` with the installed profile flags.
  It converges owned identities while preserving user hooks.
- **The trunk guard blocks every edit**: start a worktree with
  `bash .agents/tools/worktree.sh new <name>`. Use the two-hour escape hatch only with explicit
  authorization, or select `apply --profile light` when the project does not use this governance.

Patch payload checks include both `Update File` and `Move to` paths, so a rename cannot hide its destination from the primary-worktree guard or authority-document budget. Repository checks remain subject to the existing foreign-repository and ignored-file boundaries; this hook is not an OS sandbox.
