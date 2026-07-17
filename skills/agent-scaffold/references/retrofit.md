# Agent Scaffold Retrofit

Read this only when adopting an existing `AGENTS.md`, `CLAUDE.md`, hook config,
or hand-authored host agent into the current harness.

## Preview before mutation

Run `plan` from the target repository. It reports stable concern IDs with a
status such as `create`, `merge`, `adopt`, `refresh`, `present`, or `attention`.
Resolve every `attention` item, then run the reported `apply_mode`:

```bash
bash <skill-dir>/agent-scaffold.sh plan --profile default
bash <skill-dir>/agent-scaffold.sh apply --profile default
```

Use `upgrade` instead of `apply` when `plan` reports runtime `refresh` states.
`apply` preserves matching runtime files and refuses drift; `upgrade` refreshes
current managed runtime files from the skill assets.

## Adopt an existing CLAUDE.md

The current contract treats `AGENTS.md` as the authored SSOT and `CLAUDE.md` as
its symlink:

- Real `CLAUDE.md`, no `AGENTS.md`: copy the prose to `AGENTS.md`, add the
  managed harness block, then replace `CLAUDE.md` with the real symlink.
- Real `CLAUDE.md` and real `AGENTS.md`: stop for manual reconciliation; merge
  the authored prose into `AGENTS.md`, then rerun.
- Correct `CLAUDE.md → AGENTS.md` symlink: preserve it.
- Any other symlink target: stop and let the project owner choose the authority.

The installer owns only the marked block inside `AGENTS.md`. Project prose stays
outside that block.

## Adopt hand-authored host agents

The installer runs the generator's import preflight before target mutation, then
imports current `.claude/agents/*.md` and `.codex/agents/*.toml` into
`.agents/subagents/<name>/`. Divergent dual-host definitions, invalid names, or
parse errors stop before writes. Read [subagent import](subagent-import.md) for accepted host syntax,
portable identity, and conflict rules.

## Preserve project-owned integrations

Existing formatter hooks, package scripts, CI jobs, hook-manager files, Codex
config, nested contracts, and unrelated host hooks are not scaffold assets.
Keep or change them using the target project's own policy; the installer only
reconciles exact current harness hook identities.
