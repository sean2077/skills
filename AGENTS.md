# PROJECT — Agent Contract

> `AGENTS.md` is the canonical repository-level contract; `CLAUDE.md` is a symlink to it. Keep this file an actionable entry point and put durable detail in `docs/`.

## Project

`sean2077/skills` publishes 17 independently installable Agent Skills under `skills/`. The repository-private `.agents/skills/skill-eval` workflow belongs to the dogfooded project harness and is not a catalog target. Consumers need no build step; maintainers must regenerate checked-in runtime payloads from their source modules before committing.

## Required workflow

1. Read this contract and any applicable nested `AGENTS.md` before changing files.
2. Follow the scaffold-managed worktree rule below; documentation-only work is not an exception.
3. Edit the canonical source, not a generated projection or scaffold-owned managed copy. Use the ownership map in [repository architecture](docs/architecture.md).
4. Run the changed-surface checks and the appropriate full gates from the [development guide](docs/development.md). `.github/workflows/validate.yml` is the normative CI definition.
5. Add an Unreleased changelog entry for user- or maintainer-visible behavior. Use Conventional Commits, omit `Co-Authored-By`, and keep all required gates green before merging to `main`.

## Repository boundaries

- `skills/` is the published product; `.agents/skills/` is the private project harness. Never infer one catalog from the other.
- `scripts/workflow_runtime/` and `scripts/p0_runtime/` are maintainer source. Run their generators instead of editing generated skill runtime payloads.
- Format validation, installer discovery, host wiring, and runtime behavior are different evidence layers. Keep support claims in [compatibility.md](docs/compatibility.md).
- Prefer model-native reasoning for reversible single-session work. Add deterministic controls only for the costly machine-checkable boundaries described in the [harness constraint policy](docs/harness-constraint-policy.md).
- Skills and bundled scripts target Linux, macOS, and Windows through Git Bash, with LF line endings and real symlinks where the scaffold requires them.

## High-cost maintenance traps

- Keep frontmatter strict-YAML compatible. Quote a scalar containing `: `.
- Keep every published `description` on one physical line and within the 320-character routing budget; preserve decisive triggers and exclusions.
- Treat copy-paste commands as interfaces: verify working directory, scope, quoting, identity, side effects, and expected result. Quote shell globs such as `'*'`.
- Prefix local skill directories with `./`; otherwise the installer may interpret the value as a GitHub repository.
- Do not describe the CI-audited `skills@1.5.17` pin as upstream latest. Do not run project-scope `skills remove` from the catalog root.

## Canonical references

| Topic | Source |
|---|---|
| Product surfaces, generated ownership, and validation boundaries | [docs/architecture.md](docs/architecture.md) |
| Local workflow, commands, platform checks, and releases | [docs/development.md](docs/development.md) |
| Host, installer, trust, and certification claims | [docs/compatibility.md](docs/compatibility.md) |
| Documentation ownership, evidence, and freshness | [docs/documentation-maintenance.md](docs/documentation-maintenance.md) |
| Mechanical-control selection | [docs/harness-constraint-policy.md](docs/harness-constraint-policy.md) |
| Pending and historical release changes | [CHANGELOG.md](CHANGELOG.md) |

<!-- agent-scaffold:start — managed; keep project prose outside; upgrade refreshes this block. -->
## Agent Harness (Claude Code + Codex)

`.agents/` is the SSOT for harness-owned skills, subagents, and runtime; `.claude/` and `.codex/` contain host projections.

### Worktree-per-change (hard rule)

The primary worktree's checked-out branch is the active trunk (`--trunk` overrides); `new` records it and `done` merges back. Never edit the primary worktree directly, including docs:

```bash
bash .agents/tools/worktree.sh new <name>  # work in .worktrees/<name>/
bash .agents/tools/worktree.sh done        # merge, clean up, and ff-only push
```

On Windows, leave the target worktree and run `done --dir <absolute-wt>` from the primary worktree; `new` prints the exact command.

The trunk guard blocks non-ignored project-file edits in the primary worktree, regardless of branch name. Bypass it only with explicit user approval: `WORKTREE_ALLOW_TRUNK_EDIT=1`, or `touch .claude/allow-trunk-edit` for a 2 h flag.

### Authority documents (hard rules)

`AGENTS.md` is the canonical repository-level contract for Agent work. Read the root contract and applicable nested chain before acting.

- **Keep it current.** When a durable Agent-relevant change makes guidance stale, update it in the same change.
- **Keep it lean.** Keep only frequent or costly-to-miss behavior; route depth to project docs.
- **Keep scopes honest.** Add nested `AGENTS.md` only for a concrete local difference; directory structure alone never justifies one.
- **Resolve conflicts explicitly.** Surface conflicts, follow higher-priority instructions, ask the owner when authority is unclear, and repair stale guidance when authorized.

The authority-document budget hook remains advisory; projects may override its default line and character limits.

### Sources and projections

- Edit project skills in `.agents/skills/<name>/`, then run `bash .agents/relink-skills.sh`; commit source and symlink.
- Edit project subagents in `.agents/subagents/<name>/`, then run `python .agents/tools/generate-subagents.py`; commit source and projections.
- Do not hand-edit harness projections: `CLAUDE.md`, `.claude/skills/<name>` entries owned by `.agents/skills/`, `.claude/agents/*.md`, or `.codex/agents/*.toml`.
- Do not hand-edit scaffold runtime: `.agents/tools/**`, `.agents/relink-skills.sh`, or `.agents/symlink-manager.py`. Refresh it from the bundled skill with `agent-scaffold upgrade`, then run `agent-scaffold verify`.
- **Third-party skills** follow project-owned placement and installation policy. The relinker preserves unrelated names and rejects same-name conflicts.

For Codex, trust the project, confirm generated agents are discoverable, and review each exact hook definition in `/hooks`; re-review changed definitions. Claude checkpoints do not rewind symlinked or hard-linked targets (`CLAUDE.md`, `.claude/skills/*`); inspect and restore the real target with Git.
<!-- agent-scaffold:end -->
