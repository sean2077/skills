# .agents/subagents/ — authoritative subagent source (CC + Codex)

This directory is the **single source of truth** for this project's subagents. A small
python generator projects each source into the two runtime formats. **Never hand-edit the
generated files.**

| | Source (edit here) | Claude Code (generated) | Codex (generated) |
|---|---|---|---|
| Path | `.agents/subagents/<name>/` | `.claude/agents/<name>.md` | `.codex/agents/<name>.toml` |
| Files | `metadata.json` + `instructions.md` | one `.md` (frontmatter + body) | one `.toml` (fields + `developer_instructions`) |

## Add / edit a subagent

1. Create/edit `.agents/subagents/<name>/metadata.json` and `instructions.md`.
2. Run `python tools/agent/generate-subagents.py` (writes both projections).
3. `git add .agents/subagents/<name> .claude/agents/<name>.md .codex/agents/<name>.toml`.

Verify projections are in sync (use in CI / pre-commit):

```bash
python tools/agent/generate-subagents.py --check   # exit 1 on drift
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

`<name>` is the portable intersection used by both hosts: lowercase ASCII letter groups separated
by single hyphens, excluding Windows-reserved device names. Keep that exact value in the directory,
`metadata.json`, and both generated filenames; the generator rejects Codex-only underscore
identities instead of silently renaming them. Codex nickname candidates must be unique and contain
only ASCII letters, digits, spaces, hyphens, and underscores.

The generator validates this documented JSON shape before rendering: object fields must be objects,
all projected scalar fields must be non-empty strings, `claude.tools` must be a non-empty string
array of already-trimmed, comma-free entries when present, and unsupported fields fail closed instead
of being coerced or silently omitted. Apart from this README, `.gitkeep`, and underscore-prefixed
helpers, every child of this directory must be a subagent directory.
Host import applies the same presence rule to explicit optional fields. Generated YAML/TOML strings
escape their shared non-printable range; instruction bodies that cannot be represented by the TOML
multiline literal projection are rejected before any source or projection is written.

`instructions.md` is the full behavioral prompt (becomes the CC body and the Codex
`developer_instructions`). Keep subagents **read-only reviewers** unless a write surface is justified.

> Why `metadata.json` (not `.toml`): one machine-mergeable source the generator reads with the
> Python standard library, with no extra dependency to write TOML. The generated **Codex**
> projection is still valid TOML.

> The harness requires Python 3.8+ (resolved from `PYTHON_BIN`, `python`, `python3`, or `py -3`)
> for real-link management, hook JSON parsing, and subagent projection. No Node or `package.json`
> is needed; without Python the installer fails before changing the target repository.
