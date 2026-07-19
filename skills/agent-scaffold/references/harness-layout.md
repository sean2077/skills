# Agent Scaffold Harness Layout

Read this only when changing installed file placement, optional profiles, SSOT projections, or third-party skill coexistence.

## Contents

- [Bundled files: provenance + landing](#bundled-files-provenance--landing)
- [Light profile](#light-profile)
- [The `.agents/` SSOT model](#the-agents-ssot-model)
- [Project-owned skill authoring](#project-owned-skill-authoring)
- [Project-owned third-party policy](#project-owned-third-party-policy)
- [Runtime workflow troubleshooting](#runtime-workflow-troubleshooting)

## Bundled files: provenance + landing

`npx skills` installs each skill as a self-contained directory, so this skill carries every file
it installs. `scripts/managed-assets.json` is the internal source of truth for source, target,
strategy, profile, executable intent, and required `.gitignore` / `.gitattributes` lines.
`agent-scaffold.sh` resolves that manifest rather than maintaining another file list.

| Bundled asset | Lands at (target) | Notes |
|---|---|---|
| `assets/runtime/worktree.sh` | `.agents/tools/worktree.sh` | default profile only: worktree-per-change lifecycle |
| `assets/runtime/hooks/trunk_edit_guard.sh` | `.agents/tools/hooks/trunk_edit_guard.sh` | default profile only: PreToolUse trunk-edit blocker |
| `assets/runtime/hooks/authority_doc_budget.sh` | `.agents/tools/hooks/authority_doc_budget.sh` | PostToolUse AGENTS.md line/character-budget advisor |
| `assets/runtime/hooks/hook-common.sh` + `hook-paths.py` | `.agents/tools/hooks/` | shared path parsing and normalization |
| `assets/runtime/relink-skills.sh` | `.agents/relink-skills.sh` | idempotent skill symlink rebuild |
| `assets/runtime/symlink-manager.py` | `.agents/symlink-manager.py` | doctor, atomic real-link creation, sync, and verification |
| `assets/runtime/generate-subagents.py` | `.agents/tools/generate-subagents.py` | subagent projection + `--check` drift mode |
| `assets/host/claude.settings.json` | merged into `.claude/settings.json` | Claude Code managed hook source |
| `assets/host/codex.hooks.json` | merged into `.codex/hooks.json` | Codex managed hook source |
| `assets/scaffold/AGENTS.harness.md` | managed block in `AGENTS.md` | only the marker-bounded block is scaffold-owned |
| `assets/scaffold/agents-skills.README.md` | `.agents/skills/README.md` if missing | lean ownership boundary |
| `assets/scaffold/agents-subagents.README.md` | `.agents/subagents/README.md` if missing | lean ownership boundary |

Project prose, nested authority-document structure, subagent examples, Codex settings,
package scripts, and CI/hook-manager integration are reference recipes rather than installed
templates. Existing project-owned copies are preserved on upgrade. Formatter, linter, test, and
code-generation hooks likewise stay outside `.agents/tools/`; see
[format hooks](format-hooks.md) and
[subagents](subagents.md#project-owned-drift-integration).

The vendored scripts derive their own paths (git-common-dir / `$BASH_SOURCE`), so they are
layout-independent once they land at the paths above. **They are intentionally tuned for the
`.agents/tools/` install depth** — e.g. `trunk_edit_guard.sh` resolves `proj` three levels up
(`.agents/tools/hooks/` → repo root) plus a git-toplevel fallback for Codex. Do not "simplify" that
resolver to a shallower path: the git-toplevel fallback is what makes the hooks work under Codex
(which has no `$CLAUDE_PROJECT_DIR`), and `scripts/check-agent-scaffold.sh` guards this invariant.

### Light profile

`--profile light` omits worktree governance while retaining the rest of the harness. A clean apply
omits `worktree.sh`, `trunk_edit_guard.sh`, their dual-host hook entries, the managed worktree
section in `AGENTS.md`, and new worktree-specific ignore lines. A default-to-light apply
removes only the managed guard/policy; existing script copies and unmarked `.gitignore` lines are
preserved as dormant project-owned content. Select the profile on every `plan`, mutating, and
`verify` call. `verify` checks only active-profile assets; dormant default-profile scripts are
outside the light-profile comparison.

## The `.agents/` SSOT model

`.agents/` is the single source of truth; `.claude/` and `.codex/` are **projections**.

| | Source (edit here) | Claude Code | Codex |
|---|---|---|---|
| **Skills** | `.agents/skills/<name>/SKILL.md` | `.claude/skills/<name>` **symlink** (via `relink-skills.sh`) | reads `.agents/skills/` directly |
| **Subagents** | `.agents/subagents/<name>/{metadata.json,instructions.md}` | `.claude/agents/<name>.md` **generated** | `.codex/agents/<name>.toml` **generated** |

- **Skills**: `relink-skills.sh` rebuilds the symlinks idempotently. Codex needs no symlinks.
- **Subagents**: `generate-subagents.py` projects each source into both host formats (YAML
  frontmatter + body for CC; TOML with `developer_instructions` for Codex). **Never hand-edit**
  the generated files — they carry a "do not edit" banner. `--check` exits 1 on drift; wire it
  into pre-commit / CI (`python .agents/tools/generate-subagents.py --check`). `--import` does the
  reverse — adopt hand-authored host agents into sources
  ([retrofit.md](retrofit.md#adopt-hand-authored-host-agents)).
- **Drift guard**: the scaffold supplies `python .agents/tools/generate-subagents.py --check`, but
  the project decides whether it belongs in CI, Husky, pre-commit, lefthook, another manager, or
  nowhere. The installer prints the command and leaves project integration untouched.

### Project-owned skill authoring

Each project skill lives at `.agents/skills/<name>/SKILL.md`, with optional category-specific
`references/`, scripts, or other resources beside it. After any add, rename, or removal, run
`bash .agents/relink-skills.sh` and commit the authoritative source plus the matching real symlink.

A minimal skill starts with strict YAML frontmatter:

```markdown
---
name: <kebab-case>
description: "<what it does and when to use it>"
---

# <name>

## Router
## Workflow
```

Keep the resident `SKILL.md` to routing, invariants, and the workflow skeleton. Put long
checklists and worked examples in descriptive lowercase-kebab-case reference files linked directly
from `SKILL.md`; avoid catch-alls such as `reference.md`, `misc.md`, or `references/README.md`.
Directories prefixed with `_` are support material and are skipped by the relinker.

## Project-owned third-party policy

Where third-party skills live and how they are installed is project-owned policy. A project may
allow vendor-native directories under `.claude/skills/`, or require locked vendor dependencies to
live under `.agents/skills/` and use the same projection path as project-authored skills. The
scaffold does not choose between those policies.

The runtime still partitions entries by **managed target (ours) vs unrelated entry (theirs)**:

- **Project-authored** skills/subagents live in `.agents/` and project into `.claude/`/`.codex/`.
- **Unrelated entries** in `.claude/skills/` are preserved by `relink-skills.sh`; preserving them
  is a runtime safety property, not permission to keep them under a stricter project policy.
- **Same-name ownership** is always a conflict: the existing entry is preserved and the relinker
  exits 2 rather than silently choosing one owner.
- **Real-link repair**: a Git target-text placeholder can be materialized as its tracked relative
  link; drifted content is preserved as a reported conflict.

## Runtime workflow troubleshooting

- If `relink-skills.sh` reports a same-name conflict, the differing real directory or unrelated
  symlink in `.claude/skills/` remains untouched. Rename one owner and rerun the relinker.
- If `worktree.sh done` reports a rejected push, the feature worktree and branch remain available.
  Fetch and merge the remote trunk in the trunk worktree, resolve conflicts there, then run the
  printed retry command. Do not automatically force-push.
