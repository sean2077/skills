# Agent Scaffold Host Integration

Read this only when changing hook behavior, Claude Code or Codex wiring, managed JSON reconciliation, trust, or project-owned hook integration.

## Hook semantics

Both scaffold-managed hooks read the tool-call JSON on **stdin**. `hook-paths.py` only parses raw paths and
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

## Dual-host wiring

Both hosts invoke the **same** enabled scaffold scripts under `.agents/tools/hooks/`. The installer writes both
forms; do **not** "simplify" one host's path form to match the other — they differ on purpose.
The PreToolUse examples below describe the default worktree profile; the lightweight profile
omits them entirely while retaining the authority-document PostToolUse hook.

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
paths under `.agents/tools/hooks/` (`trunk_edit_guard.sh` and `authority_doc_budget.sh`), then merges
the current templates by event + matcher and deduplicates exact commands. The retired
`format_on_edit.sh` identity remains cleanup-owned for one migration cycle: `upgrade` removes its
old managed command, but no replacement is installed. Legacy launchers and path prefixes still
reconcile; basename lookalikes elsewhere remain user-owned.
Case-equivalent spellings reconcile only when the target filesystem resolves them to the same
installed hook; case-distinct paths remain user-owned. `--no-worktree` omits the guard and removes
its older managed entries while leaving every user command and unrelated config key intact. Empty
managed events are removed rather than written as empty matcher groups. Python is a harness
prerequisite, so this path has no jq-dependent behavior or unsafe paste fallback.

Writes are atomic (`> tmp && mv`). Package scripts, CI jobs, and hook-manager configuration are
project-owned; see [subagent drift integration](subagents.md#project-owned-drift-integration).

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
  authorization, or select `upgrade --no-worktree` when the project does not use this governance.

## Project-owned formatting hooks

Agent Scaffold deliberately does **not** install or wire a formatter. Formatter selection, file
scope, working directory, generated-file exclusions, monorepo routing, and failure policy vary by
project and stay under that project's ownership.

When format-on-edit is useful:

1. Implement it at a project-owned path outside `.agents/tools/`, such as
   `.agents/hooks/format-on-edit.sh` or an existing command under `tools/`.
2. Let that implementation consume the raw tool-call JSON on stdin. It may source
   `.agents/tools/hooks/hook-common.sh` and call `hook_extract_paths` for the scaffold's
   cross-platform path parsing, but it owns every formatting decision.
3. Add user-owned PostToolUse entries to both host configs. For example, after choosing
   `.agents/hooks/format-on-edit.sh`:

Claude Code command field:

```json
"command": "bash -lc 'root=\"${CLAUDE_PROJECT_DIR:-}\"; [ -n \"$root\" ] || root=\"$(git rev-parse --show-toplevel 2>/dev/null)\" || exit 0; command -v cygpath >/dev/null 2>&1 && root=\"$(cygpath -u \"$root\")\"; bash \"$root/.agents/hooks/format-on-edit.sh\"'"
```

Codex command field:

```json
"command": "bash -lc 'root=\"$(git rev-parse --show-toplevel 2>/dev/null)\" || exit 0; bash \"$root/.agents/hooks/format-on-edit.sh\"'"
```

The installer preserves these commands because they do not target its managed
`.agents/tools/hooks/` identities. Test and verify the formatter through the project's own gates;
`agent-scaffold verify` checks only scaffold-owned runtime and wiring.
