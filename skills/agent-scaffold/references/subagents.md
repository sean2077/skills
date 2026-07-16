# Agent Scaffold Subagents

Read this only when changing subagent source, import, projection, or drift behavior.

## Subagent generator

| Capability | Needs | Without it |
|---|---|---|
| full harness, real-link manager, hooks, and subagent projection | git + Bash 3.2+ + Python 3.8+ + real file/directory links | preflight exits 2 before target mutation |
| `gen:subagents` / `check:agents` npm scripts + husky `--check` hook | a `package.json` (npm/husky) | other hook managers / CI: installer prints the one line to wire |

`generate-subagents.py`, `symlink-manager.py`, and `hook-paths.py` use only the Python standard
library — no Node or `package.json`. Resolve Python by executing a 3.8+ probe on `PYTHON_BIN`,
`python`, `python3`, then Windows `py -3`; an unusable or older candidate falls through to the
next one. Before the first target write, the installer reuses the symlink manager and generator in
read-only preflight modes so deterministic contract, skill-projection, and subagent-import conflicts
leave the repository unchanged. Node remains an optional convenience surface only.

## Adopting hand-authored subagents

A project may already have hand-written `.claude/agents/*.md` or `.codex/agents/*.toml`. Python is
a harness prerequisite, and the installer runs `generate-subagents.py --import` before projecting:

1. For each host agent file with **no** canonical, name-matched generated marker at the host
   format's expected position, it parses a bounded, round-trippable subset. Claude supports the
   emitted `name`, `description`, comma-separated `tools`, `model`, and Markdown body. Quoted YAML
   strings retain whitespace and escapes; plain scalars that YAML would resolve as booleans, nulls,
   numbers, or dates, or whose indicators would change YAML structure, fail closed instead of being
   reinterpreted. Double-quoted values use the JSON-compatible subset of YAML escapes. Explicit
   `tools` / `model` fields must contain usable values; empty strings and empty comma-separated tool
   entries fail instead of disappearing during import. Mentioning the generated source path in
   ordinary prose does not claim ownership.
2. Codex supports ordinary basic (`"..."`) and literal (`'...'`) strings plus triple-quoted
   multiline basic (`"""..."""`) and literal (`'''...'''`) strings whose content starts either on
   the opening line or the next line. Ordinary basic strings accept raw UTF-8, raw TAB, and the shared
   JSON/TOML escapes `\"`, `\\`, `\b`, `\t`, `\n`, `\f`, `\r`, and valid `\uXXXX`; multiline basic
   instructions are accepted only without backslash escapes or an internal matching triple-quote
   delimiter. Explicit optional scalar fields must be non-empty. Raw characters forbidden by the
   host format are rejected, while valid escaped values are preserved semantically and re-emitted as
   escapes. Comments and fields this harness cannot project back — such as Claude `memory` or Codex
   `mcp_servers` / `skills.config` — fail closed because canonical projection cannot preserve them.
3. This is a dual-host SSOT, so directory, filename, Claude `name`, and Codex `name` use one portable
   identity: lowercase ASCII letter groups separated by single hyphens, excluding Windows-reserved
   device names. Claude requires that general name shape; Codex also permits broader identities and
   a different filename, but import rejects those Codex-only forms rather than silently changing the
   name callers use. Codex nickname candidates must be unique and use its documented ASCII character
   set. A same-name Claude/Codex pair must also have equal descriptions and instructions (an absent
   final newline is normalized).
4. A banner-less host file whose name already has an `.agents/subagents/<name>/` source is an
   ownership conflict, not an idempotent skip. `plan` reports it as **needs you**, and both import
   and ordinary projection exit before replacing that file or creating another host projection.
5. Import first builds the combined source model in memory and renders every prospective projection.
   It then preflights name collisions, the complete host and source inventories (including
   dot-prefixed entries and broken links), canonical lowercase host extensions, required directory
   shapes, target and temporary file paths, stale projections, and ownership before writing
   `.agents/subagents/<name>/{metadata.json,instructions.md}`. Each adopted agent is finally projected
   back with the do-not-edit banner. Individual file replacement is atomic; an external I/O failure
   after preflight is not a cross-file transaction.

Within `.agents/subagents/`, `.gitkeep`, `README.md`, and underscore-prefixed helper entries are the
only non-agent inventory. Every other child must be an agent directory; a file or broken link fails
before orphan projections can be removed. Source `claude.tools` entries are already-trimmed,
comma-free strings because the Claude projection uses a comma-separated scalar.

Adoption is idempotent once the host files carry canonical generated markers. The projection step
that finds a sourceless, banner-less file **keeps** it and tells you to `--import` it rather than
pruning it as an orphan. If Python is unavailable, the installer fails at preflight before changing
the target repository.

## Drift troubleshooting

- If `generate-subagents.py --check` fails, run
  `python .agents/tools/generate-subagents.py` and commit the regenerated
  `.claude/agents/*` and `.codex/agents/*` projections with their SSOT source.
- If a banner-less host projection has no source, import it; do not delete it as stale output.
- If a same-name source and host file disagree, resolve the ownership conflict before generation.
