# Agent Scaffold Host Integration

Read this only when changing managed hook behavior, Claude Code or Codex wiring, JSON
reconciliation, or trust. For project-owned format-on-edit, read
[format hooks](format-hooks.md).

## Contents

- [Hook semantics](#hook-semantics)
- [Dual-host wiring](#dual-host-wiring)
- [Hook configuration reconciliation](#hook-configuration-reconciliation)
- [Codex trust gate](#codex-trust-gate)
- [Integration troubleshooting](#integration-troubleshooting)

## Hook semantics

Both scaffold-managed hooks read the tool-call JSON on **stdin**. `hook-paths.py` only parses raw paths and
payload cwd; `hook-common.sh` converts `C:/…`, backslash, UNC, Git Bash, relative, spaces, and
Unicode paths into the Bash namespace (using `cygpath` on Windows). Each hook only acts on files
in the **project repo** (same git-common-dir as the resolved project root), so edits to
nested/sibling repos pass through; gitignored paths are exempt. A damaged/missing helper fails open.

### trunk_edit_guard.sh — PreToolUse, blocking

- Installed and wired only by `--profile default`; `--profile light` removes the managed wiring.
- **Exit 0** allow · **exit 2** block (message on stderr) · any other exit = non-blocking error (fails open).
- Blocks an edit to a file in a worktree whose branch is a **trunk** (`main` / `master` / `release/*` / `maintenance/*`), unless an escape hatch is active.
- **Escape hatches** (only when the user explicitly authorizes a trunk edit):
  - `WORKTREE_ALLOW_TRUNK_EDIT=1` — one-shot env bypass.
  - `touch <repo>/.claude/allow-trunk-edit` — flag file, auto-expires **2 h** (mtime check `now - mtime <= 7200`); re-touch to renew.
- `WORKTREE_GUARD_CMD` overrides the command shown in the block message (default `bash .agents/tools/worktree.sh`).

### authority_doc_budget.sh — PostToolUse, advisory (never blocks)

- Watches `AGENTS.md` / `CLAUDE.md` writes; resolves the `CLAUDE.md → AGENTS.md` symlink so each contract is measured once.
- Line budgets: **root `AGENTS.md` 320**, **nested `AGENTS.md` 120**. Override with `AUTHORITY_DOC_MAX_ROOT` / `AUTHORITY_DOC_MAX_NESTED`.
- Character budgets: **root `AGENTS.md` 25,600**, **nested `AGENTS.md` 9,600**. Override with `AUTHORITY_DOC_MAX_ROOT_CHARS` / `AUTHORITY_DOC_MAX_NESTED_CHARS`.
- Over budget → emits a nudge as PostToolUse `additionalContext` (via jq), else to stderr. Always **exit 0**.

## Dual-host wiring

Both hosts invoke the **same** enabled scaffold scripts under `.agents/tools/hooks/`. The installer writes both
forms; do **not** "simplify" one host's path form to match the other — they differ on purpose.
The PreToolUse examples below describe the default worktree profile; the lightweight profile
omits them entirely while retaining the authority-document PostToolUse hook.

**Claude Code — `.claude/settings.json` shape** (the canonical full command strings live in
`assets/host/claude.settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit|MultiEdit|Write|NotebookEdit",
        "hooks": [ { "type": "command", "command": "bash -lc '<normalize project root>; bash \"$root/.agents/tools/hooks/trunk_edit_guard.sh\"'" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          { "type": "command", "command": "bash -lc '<normalize project root>; bash \"$root/.agents/tools/hooks/authority_doc_budget.sh\"'" }
        ] }
    ]
  }
}
```

**Codex — `.codex/hooks.json`:** matcher `Edit|Write|apply_patch`; each command wrapped so
Codex (which has no `$CLAUDE_PROJECT_DIR`) resolves the repo root itself:

```json
{ "type": "command",
  "command": "bash -lc 'root=\"$(git rev-parse --show-toplevel 2>/dev/null)\" || exit 0; bash \"$root/.agents/tools/hooks/trunk_edit_guard.sh\"'",
  "statusMessage": "Checking worktree policy" }
```

**Why two forms:** Claude Code sets `$CLAUDE_PROJECT_DIR`; Codex does not, so its hook resolves
`git rev-parse --show-toplevel` at call time. Either way, `hook-common.sh` bridges both and
retains the install-depth fallback:

```bash
raw="${CLAUDE_PROJECT_DIR:-$(git -C "$hook_dir" rev-parse --show-toplevel 2>/dev/null || (cd "$hook_dir/../../.." && pwd))}"
proj="$(hook_posix_path "$raw")"
```

## Hook configuration reconciliation

Apply/upgrade refresh managed hook commands without clobbering user hooks. The Python reconciler
parses JSON, removes only commands that invoke the exact owned
paths under `.agents/tools/hooks/` (`trunk_edit_guard.sh` and `authority_doc_budget.sh`), then merges
the current assets by event + matcher and deduplicates exact commands. Basename lookalikes and
every command outside those exact current paths remain project-owned.
Case-equivalent spellings reconcile only when the target filesystem resolves them to the same
installed hook; case-distinct paths remain user-owned. `--profile light` omits the guard and removes
its managed entry while leaving every user command and unrelated config key intact. Empty
managed events are removed rather than written as empty matcher groups. Python is a harness
prerequisite, so this path has no jq-dependent behavior or unsafe paste fallback.

Harness-owned runtime, hook JSON, authority-contract, ignore, and attributes updates are written
to unique siblings in the destination directory, flushed, and atomically replaced. An interrupted
candidate write therefore leaves the previous project file intact; fixed project-owned `.tmp`
paths are never claimed. Package scripts, CI jobs, and hook-manager configuration are project-owned;
see [subagent drift integration](subagents.md#project-owned-drift-integration).

**Idempotency keys:** managed hook identity + current `.command`/`.matcher`; `.gitignore` lines by
`grep -qxF`; the `AGENTS.md` harness section by the
`<!-- agent-scaffold:start … end -->` markers.

## Codex trust gate

Project-level `.codex/` (config + hooks + agents) **only loads for a TRUSTED project**. Until the
project is trusted, the entire project-level `.codex/` — including configured hooks and the
optional worktree guard — is
silently skipped, so the harness looks half-installed on the Codex side. Trust once:

- run `codex` in the repo and accept the prompt, **or**
- add to `~/.codex/config.toml`:
  ```toml
  [projects."<repo absolute path>"]
  trust_level = "trusted"
  ```

`verify` cannot read your `~/.codex/config.toml` reliably across machines, so it always prints
the trust reminder rather than asserting trust.

The scaffold creates `.codex/hooks.json` because that file carries managed dual-host wiring. It
does **not** create `.codex/config.toml`: a comment-only placeholder changes no behavior, while real
project-scoped Codex settings vary by repository. Existing config files are preserved; create one
only when the project needs actual settings.

## Integration troubleshooting

- **Hooks don't fire in Codex**: trust the project, confirm the matcher, and confirm `bash` resolves
  to the supported Unix/Git Bash runtime. Hook commands do not depend on checkout executable bits.
- **Hooks don't fire in Claude Code**: validate `.claude/settings.json`, confirm the command path,
  and restart the host session after changing settings.
- **The installer rejects an existing hook config**: repair the named JSON file. Mutating modes
  require a regular file, strict UTF-8 JSON, an object at the top level, and well-typed hook arrays.
- **Managed hook entries are duplicate or stale**: run `upgrade` with the installed profile flags.
  It converges owned identities while preserving user hooks.
- **The trunk guard blocks every edit**: start a worktree with
  `bash .agents/tools/worktree.sh new <name>`. Use the two-hour escape hatch only with explicit
  authorization, or select `apply --profile light` when the project does not use this governance.
