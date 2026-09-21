# .agents/subagents/ — project subagent SSOT

Each project-owned subagent lives in
`.agents/subagents/<name>/{metadata.json,instructions.md}`. The generator writes
the Claude Code and Codex projections; never hand-edit those generated files.

Use project-owned subagents for reusable instructions or versioned tool, model, reasoning, and sandbox settings. The parent owns integration and verification; coordinate overlapping writes and return the evidence needed for that task.

```bash
python .agents/tools/generate-subagents.py
python .agents/tools/generate-subagents.py --check
```

Commit the source plus `.claude/agents/<name>.md` and
`.codex/agents/<name>.toml` together. Names use lowercase ASCII letter groups
separated by single hyphens. `.gitkeep`, this README, and `_`-prefixed support
entries are the only non-agent children allowed here.

Hook-manager and CI integration are project-owned. Wire the `--check` command
where it fits the project rather than expecting the scaffold to choose a tool.

For the full metadata schema, import rules, validation, and an optional example,
load the `agent-scaffold` skill's `references/subagents.md` on demand.
