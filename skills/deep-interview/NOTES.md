# `deep-interview` — maintainer notes

Not loaded at runtime. Provenance and refresh steps for maintainers only.

## Provenance

Standalone extraction (2026-06-11) of OMC 4.14.6 `skill-bodies/deep-interview`,
de-coupled from the oh-my-claudecode plugin (now disabled).

Changes vs upstream:

- `state_write` / `state_read` MCP tools → plain file state at `.omc/state/deep-interview-state.json`
- `explore` OMC agent → built-in `Explore` subagent, with a host-neutral fallback (plain-text question + ordinary read/search tools) for non-Claude hosts
- `--autoresearch` mode and the omc-plan / autopilot / ralph / team execution bridges removed (final handoff = main conversation / Codex relay)
- depth flags now map to thresholds explicitly
- `{{ARGUMENTS}}` → `$ARGUMENTS` (Claude Code's documented placeholder; `npx skills` copies the body verbatim and does not transform moustache placeholders)
- verbose scoring prompt, final spec template, and the Advanced tables moved to `reference.md` to cut resident context cost

To refresh from a newer OMC: re-extract from the plugin cache and re-apply these changes.
