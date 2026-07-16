# Agent Scaffold Host Integration

Read this only when changing hook behavior, Claude Code or Codex wiring, managed JSON reconciliation, trust, or formatter integration.

## Hook semantics

All three hooks read the tool-call JSON on **stdin**. `hook-paths.py` only parses raw paths and
payload cwd; `hook-common.sh` converts `C:/…`, backslash, UNC, Git Bash, relative, spaces, and
Unicode paths into the Bash namespace (using `cygpath` on Windows). Each hook only acts on files
in the **project repo** (same git-common-dir as the resolved project root), so edits to
nested/sibling repos pass through; gitignored paths are exempt. A damaged/missing helper fails open.

### trunk_edit_guard.sh — PreToolUse, blocking

- Installed and wired only by the default profile; `--no-worktree` removes the managed wiring.
- **Exit 0** allow · **exit 2** block (message on stderr) · any other exit = non-blocking error (fails open).
- Blocks an edit to a file in a worktree whose branch is a **trunk** (`main` / `master` / `release/*` / `maintenance/*`), unless an escape hatch is active.
- **Escape hatches** (only when the user explicitly authorizes a trunk edit):
  - `WORKTREE_ALLOW_TRUNK_EDIT=1` — one-shot env bypass.
  - `touch <repo>/.claude/allow-trunk-edit` — flag file, auto-expires **2 h** (mtime check `now - mtime <= 7200`); re-touch to renew.
- `WORKTREE_GUARD_CMD` overrides the command shown in the block message (default `bash .agents/tools/worktree.sh`).

### authority_doc_budget.sh — PostToolUse, advisory (never blocks)

- Watches `AGENTS.md` / `CLAUDE.md` writes; resolves the `CLAUDE.md → AGENTS.md` symlink so each contract is measured once.
- Budgets: **root `AGENTS.md` 320** lines, **nested `AGENTS.md` 120** lines. Override with `AUTHORITY_DOC_MAX_ROOT` / `AUTHORITY_DOC_MAX_NESTED`.
- Over budget → emits a nudge as PostToolUse `additionalContext` (via jq), else to stderr. Always **exit 0**.

### format_on_edit.sh — PostToolUse, advisory (never blocks)

- Runs the project's formatter on edited files; reports what it rewrote as `additionalContext` so you re-read before further exact-string edits. See [format_on_edit genericization](#format_on_edit-genericization) for the `FORMAT_ON_EDIT_CMD` / `FORMAT_ON_EDIT_EXTS` overrides and the runtime self-skip.

## Dual-host wiring

Both hosts invoke the **same** enabled scripts under `.agents/tools/hooks/`. The installer writes both
forms; do **not** "simplify" one host's path form to match the other — they differ on purpose.
The PreToolUse examples below describe the default worktree profile; the lightweight profile
omits them entirely while retaining the PostToolUse hooks.

**Claude Code — `.claude/settings.json` shape** (the canonical full command strings live in
`templates/claude.settings.json`):

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
          { "type": "command", "command": "bash -lc '<normalize project root>; bash \"$root/.agents/tools/hooks/format_on_edit.sh\"'" },
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

Retrofit/upgrade must refresh our hook commands without clobbering user hooks or retaining stale
N-1 strings. The Python reconciler parses JSON, removes only commands that invoke the exact owned
paths under `.agents/tools/hooks/` (`trunk_edit_guard.sh`, `authority_doc_budget.sh`, or
`format_on_edit.sh`), then merges the current templates by event + matcher and deduplicates exact
commands. Legacy launchers and path prefixes still reconcile; basename lookalikes elsewhere remain
user-owned. Case-equivalent spellings reconcile only when the target filesystem resolves them to
the same installed hook; case-distinct paths remain user-owned. `--no-worktree` and
`--no-format-hook` omit their current managed commands and remove older managed entries while
leaving every user command and unrelated config key intact. Empty managed events are removed
rather than written as empty matcher groups. Python is a harness prerequisite, so this path has no
jq-dependent behavior or unsafe paste fallback.

Writes are atomic (`> tmp && mv`). `package.json` script keys (`gen:subagents`, `check:agents`,
optional `prepare: husky`) are merged the same way — added only when absent.

**Idempotency keys:** managed hook identity + current `.command`/`.matcher`; `.gitignore`/`.husky/pre-commit`
lines by `grep -qxF`; `package.json` scripts by key presence; the `AGENTS.md` harness section by
the `<!-- agent-scaffold:start … end -->` markers.

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
  authorization, or select `upgrade --no-worktree` when the project does not use this governance.

## format_on_edit genericization

`format_on_edit.sh` defaults to the project's Prettier on `ts tsx js mjs cjs json`, but is not
Prettier-locked:

- **Runtime self-skip**: if the formatter launcher isn't on `PATH` (e.g. no `npx`), it exits 0 as
  a no-op — safe to wire into any project.
- **Overrides** (env, e.g. in `.claude/settings.local.json`): `FORMAT_ON_EDIT_CMD` (the file path
  is appended as the last arg; default `npx --no-install prettier --write`) and
  `FORMAT_ON_EDIT_EXTS` (space-separated, no dots; default `ts tsx js mjs cjs json`). Examples:
  `FORMAT_ON_EDIT_CMD="gofmt -w" FORMAT_ON_EDIT_EXTS="go"`, `FORMAT_ON_EDIT_CMD="ruff format" FORMAT_ON_EDIT_EXTS="py pyi"`.
- **Install gating**: `--no-format-hook` omits it from the wiring (the script is still copied so
  `upgrade` can enable it later). Because it self-skips, wiring it into a non-JS project is also
  harmless — it just never fires.
