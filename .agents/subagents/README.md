# .agents/subagents/ — authoritative subagent source (CC + Codex)

This directory is the **single source of truth** for this project's subagents. A small
python3 generator projects each source into the two runtime formats. **Never hand-edit the
generated files.**

| | Source (edit here) | Claude Code (generated) | Codex (generated) |
|---|---|---|---|
| Path | `.agents/subagents/<name>/` | `.claude/agents/<name>.md` | `.codex/agents/<name>.toml` |
| Files | `metadata.json` + `instructions.md` | one `.md` (frontmatter + body) | one `.toml` (fields + `developer_instructions`) |

## Add / edit a subagent

1. Create/edit `.agents/subagents/<name>/metadata.json` and `instructions.md`.
2. Run `python3 tools/agent/generate-subagents.py` (writes both projections).
3. `git add .agents/subagents/<name> .claude/agents/<name>.md .codex/agents/<name>.toml`.

Verify projections are in sync (use in CI / pre-commit):

```bash
python3 tools/agent/generate-subagents.py --check   # exit 1 on drift
```

## metadata.json shape

```json
{
  "name": "<kebab-case>",                  // must match the directory name
  "description": "<one line: what it audits + when to dispatch it>",
  "claude": { "tools": ["Read", "Grep", "Glob", "Bash"] },
  "codex": {
    "model_reasoning_effort": "high",       // optional
    "sandbox_mode": "read-only",            // optional
    "nickname_candidates": ["...", "..."]   // optional
    // "model": "..."  // optional — omit to let Codex pick its default
  }
}
```

`instructions.md` is the full behavioral prompt (becomes the CC body and the Codex
`developer_instructions`). Keep subagents **read-only reviewers** unless a write surface is justified.

> Why `metadata.json` (not `.toml`): one machine-mergeable source the generator reads with the
> Python standard library, with no extra dependency to write TOML. The generated **Codex**
> projection is still valid TOML.

> Requires python3 (the generator + the `--check` drift guard) — no Node or `package.json` needed.
> On a host without python3 the agent-scaffold skill skips subagent projection; install python3 and
> re-run `agent-scaffold upgrade` to enable it.
