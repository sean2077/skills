# Project-Owned Formatting Hooks

Read this only when a target project wants format-on-edit behavior. Agent Scaffold deliberately
does **not** install or wire a formatter because formatter selection, file scope, working directory,
generated-file exclusions, monorepo routing, and failure policy vary by project.

## Integration recipe

1. Implement the formatter at a project-owned path outside `.agents/tools/`, such as
   `.agents/hooks/format-on-edit.sh` or an existing command under `tools/`.
2. Let it consume the raw tool-call JSON on stdin. It may source
   `.agents/tools/hooks/hook-common.sh` and call `hook_extract_paths` for the scaffold's
   cross-platform path parsing, but it owns every formatting decision.
3. Add user-owned `PostToolUse` entries to both host configs.

For `.agents/hooks/format-on-edit.sh`, use these command fields after validating the script through
the target project's own gates.

Claude Code:

```json
"command": "bash -lc 'root=\"${CLAUDE_PROJECT_DIR:-}\"; [ -n \"$root\" ] || root=\"$(git rev-parse --show-toplevel 2>/dev/null)\" || exit 0; command -v cygpath >/dev/null 2>&1 && root=\"$(cygpath -u \"$root\")\"; bash \"$root/.agents/hooks/format-on-edit.sh\"'"
```

Codex:

```json
"command": "bash -lc 'root=\"$(git rev-parse --show-toplevel 2>/dev/null)\" || exit 0; bash \"$root/.agents/hooks/format-on-edit.sh\"'"
```

The installer preserves these commands because they do not target the managed
`.agents/tools/hooks/` identities. `agent-scaffold verify` checks only scaffold-owned runtime and
wiring; the project owns formatter verification.
