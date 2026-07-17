# Agent Scaffold Subagent Import

Read this only when adopting hand-written `.claude/agents/*.md` or
`.codex/agents/*.toml` into the dual-host `.agents/subagents/` SSOT.

Python is a harness prerequisite, and the installer runs `generate-subagents.py --import` before
projecting:

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
3. Directory, filename, Claude `name`, and Codex `name` use one portable identity: lowercase ASCII
   letter groups separated by single hyphens, excluding Windows-reserved device names. Codex permits
   broader identities and a different filename, but import rejects those forms rather than silently
   changing the name callers use. Codex nickname candidates must be unique and use its documented
   ASCII set. A same-name Claude/Codex pair must also have equal descriptions and instructions; an
   absent final newline is normalized.
4. A banner-less host file whose name already has an `.agents/subagents/<name>/` source is an
   ownership conflict, not an idempotent skip. `plan` reports `attention`, and import and ordinary
   projection stop before replacing that file or creating another host projection.
5. Import first builds the combined source model in memory and renders every prospective projection.
   It then preflights name collisions, complete host/source inventories, canonical lowercase host
   extensions, required directory shapes, target and temporary paths, stale projections, and
   ownership before writing `.agents/subagents/<name>/{metadata.json,instructions.md}`. Individual
   replacement is atomic; an external I/O failure after preflight is not a cross-file transaction.

Within `.agents/subagents/`, `.gitkeep`, `README.md`, and underscore-prefixed helper entries are the
only non-agent inventory. Every other child must be an agent directory; a file or broken link fails
before orphan projections can be removed. Source `claude.tools` entries are already-trimmed,
comma-free strings because the Claude projection uses a comma-separated scalar.

Adoption is idempotent once host files carry canonical generated markers. A sourceless, banner-less
file is preserved with an instruction to run `--import`; it is never pruned as generated output. If
Python is unavailable, installation fails at preflight before changing the target repository.
