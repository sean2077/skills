# Agent Scaffold Host Integration

Read this only when changing scaffold-owned hook behavior, Claude Code or Codex wiring, JSON reconciliation, or trust. For project-owned format-on-edit, read [format hooks](format-hooks.md).

## Contents

- [Hook semantics](#hook-semantics)
- [Dual-host wiring](#dual-host-wiring)
- [Hook configuration reconciliation](#hook-configuration-reconciliation)
- [Codex project trust and hook review](#codex-project-trust-and-hook-review)
- [Integration troubleshooting](#integration-troubleshooting)

## Hook semantics

Both scaffold-owned hooks read the tool-call JSON on **stdin**. `hook-paths.py` only parses raw paths and payload cwd; `hook-common.sh` converts `C:/…`, backslash, UNC, Git Bash, relative, spaces, and Unicode paths into the Bash namespace (using `cygpath` on Windows). Each hook only acts on files in the **project repo** (same git-common-dir as the resolved project root), so edits to nested/sibling repos pass through; gitignored paths are exempt. A damaged/missing helper fails open.

### trunk_edit_guard.sh — PreToolUse, blocking

- Installed and wired only by `--profile default`; `--profile light` removes the scaffold-owned wiring.
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

Apply/upgrade refresh scaffold-owned hook commands without clobbering user hooks. The Python reconciler parses JSON, removes only commands that invoke the exact owned paths under `.agents/tools/hooks/` (`trunk_edit_guard.sh` and `authority_doc_budget.sh`), then merges the current assets by event + matcher and deduplicates exact commands. Basename lookalikes and every command outside those exact current paths remain project-owned. Case-equivalent spellings reconcile only when the target filesystem resolves them to the same installed hook; case-distinct paths remain user-owned. `--profile light` omits the guard and removes its scaffold-owned entry while leaving every user command and unrelated config key intact. Empty scaffold-owned events are removed rather than written as empty matcher groups. Python is a harness prerequisite, so this path has no jq-dependent behavior or unsafe paste fallback.

Harness-owned runtime, hook JSON, authority-contract, ignore, and attributes updates are written
to unique siblings in the destination directory, flushed, and atomically replaced. An interrupted
candidate write therefore leaves the previous project file intact; fixed project-owned `.tmp`
paths are never claimed. Package scripts, CI jobs, and hook-manager configuration are project-owned;
see [subagent drift integration](subagents.md#project-owned-drift-integration).

**Idempotency keys:** scaffold-owned hook identity + current `.command`/`.matcher`; `.gitignore` lines by `grep -qxF`; the `AGENTS.md` harness section by the `<!-- agent-scaffold:start … end -->` markers.

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

- **Hooks don't fire in Codex**: trust the project, open `/hooks`, review/trust the exact current hook definitions, confirm the matcher, and confirm `bash` resolves to the supported Unix/Git Bash runtime. Hook commands do not depend on checkout executable bits.
- **Hooks don't fire in Claude Code**: validate `.claude/settings.json`, confirm the command path,
  and restart the host session after changing settings.
- **The installer rejects an existing hook config**: repair the named JSON file. Mutating modes
  require a regular file, strict UTF-8 JSON, an object at the top level, and well-typed hook arrays.
- **Scaffold-owned hook entries are duplicate or stale**: run `upgrade` with the installed profile flags.
  It converges owned identities while preserving user hooks.
- **The trunk guard blocks every edit**: start a worktree with
  `bash .agents/tools/worktree.sh new <name>`. Use the two-hour escape hatch only with explicit
  authorization, or select `apply --profile light` when the project does not use this governance.
