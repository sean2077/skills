# Agent Scaffold Harness Layout

Read this only when changing installed file placement, optional profiles, SSOT projections, or third-party skill coexistence.

## Bundled files: provenance + landing

`npx skills` installs each skill as a self-contained directory — a skill cannot reference
files from a sibling skill at runtime, so this skill carries its **own** copy of every script
it installs. The installer (`harness-init.sh`) reads from `templates/` and writes into the target.

| `templates/` file | Lands at (target) | Notes |
|---|---|---|
| `worktree.sh` | `.agents/tools/worktree.sh` | default profile only: worktree-per-change lifecycle (new/done/release/list) |
| `trunk_edit_guard.sh` | `.agents/tools/hooks/trunk_edit_guard.sh` | default profile only: PreToolUse trunk-edit blocker (dual-host `proj=` resolver) |
| `authority_doc_budget.sh` | `.agents/tools/hooks/authority_doc_budget.sh` | PostToolUse AGENTS.md line-budget advisor |
| `hook-common.sh` + `hook-paths.py` | `.agents/tools/hooks/` | shared Python JSON parser + Git Bash/native path normalization |
| `relink-skills.sh` | `.agents/relink-skills.sh` | idempotent skill symlink rebuild |
| `symlink-manager.py` | `.agents/symlink-manager.py` | doctor, atomic real-link creation, migration, sync, and verification |
| `generate-subagents.py` | `.agents/tools/generate-subagents.py` | subagent projection + `--check` drift mode (python) |
| `claude.settings.json` | merged into `.claude/settings.json` | CC hook block (merge source) |
| `codex.hooks.json` | merged into `.codex/hooks.json` | Codex hook block (merge source) |
| `AGENTS.harness.md` | `AGENTS.md` (init) / harness block injected (retrofit) | only the `<!-- agent-scaffold:start … end -->` block is scaffold-owned |
| `agents-skills.README.md` | `.agents/skills/README.md` (create if missing) | lean resident commands + ownership boundary |
| `agents-subagents.README.md` | `.agents/subagents/README.md` (create if missing) | lean resident commands + ownership boundary |
| `gitignore.snippet` | appended to `.gitignore` | always `.claude/settings.local.json`; default profile also adds `.worktrees/` and `.claude/allow-trunk-edit` |

Project prose, nested authority-document structure, subagent examples, Codex settings,
package scripts, and CI/hook-manager integration are reference recipes rather than installed
templates. Existing project-owned copies are preserved on upgrade. Formatter, linter, test, and
code-generation hooks likewise stay outside `.agents/tools/`; see
[host integration](host-integration.md#project-owned-formatting-hooks) and
[subagents](subagents.md#project-owned-drift-integration).

The vendored scripts derive their own paths (git-common-dir / `$BASH_SOURCE`), so they are
layout-independent once they land at the paths above. **They are intentionally tuned for the
`.agents/tools/` install depth** — e.g. `trunk_edit_guard.sh` resolves `proj` three levels up
(`.agents/tools/hooks/` → repo root) plus a git-toplevel fallback for Codex. Do not "simplify" that
resolver to a shallower path: the git-toplevel fallback is what makes the hooks work under Codex
(which has no `$CLAUDE_PROJECT_DIR`), and `scripts/check-agent-scaffold.sh` guards this invariant.

### Optional lightweight profile

`--no-worktree` disables worktree governance while retaining the rest of the harness. A clean
install omits `worktree.sh`, `trunk_edit_guard.sh`, their dual-host hook entries, the managed
worktree section in `AGENTS.md`, and new worktree-specific ignore lines. A default→light upgrade
removes only the managed guard/policy; existing script copies and unmarked `.gitignore` lines are
preserved as dormant/user-owned content. The option is per-invocation: repeat it for `plan`,
`retrofit`/`upgrade`, and `verify`. Omitting it on a later upgrade selects the default profile and
re-enables worktree governance. `verify` fails on wiring mismatches or script drift in the selected
profile; dormant worktree scripts left by a default→light transition are outside that comparison.

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
  ([harness-migration.md](harness-migration.md#retrofitting-an-in-flight-project)).
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

## Coexistence with `npx skills`

Two mechanisms live side by side, partitioned by **managed target (ours) vs other entry (theirs)**:

- **Project-authored** skills/subagents live in `.agents/` and project into `.claude/`/`.codex/`.
- **Third-party** skills install via `npx skills add <repo> -a claude-code -a codex` and land as
  **real directories** in `.claude/skills/`. `relink-skills.sh` never touches unrelated real
  directories or symlinks. A same-name project source is a conflict: it is preserved and the
  relinker exits 2 rather than silently choosing one owner.
- **Legacy migration**: a Git target-text placeholder or byte-identical historical copy is safe to
  replace with a real relative link; drifted content is always preserved as a reported conflict.

## Runtime workflow troubleshooting

- If `relink-skills.sh` reports a same-name conflict, the differing real directory or unrelated
  symlink in `.claude/skills/` remains untouched. Rename one owner and rerun the relinker.
- If `worktree.sh done` reports a rejected push, the feature worktree and branch remain available.
  Fetch and merge the remote trunk in the trunk worktree, resolve conflicts there, then run the
  printed retry command. Do not automatically force-push.
