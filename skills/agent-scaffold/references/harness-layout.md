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
| `codex.config.toml` | `.codex/config.toml` (create if missing) | trust-gate note; sets nothing else |
| `AGENTS.root.md` | `AGENTS.md` (init) / harness block injected (retrofit) | the `<!-- agent-scaffold:start … end -->` block is the reusable contract |
| `AGENTS.nested.md` | `<dir>/AGENTS.md` (on request) | nearest-ancestor-linked template for a real local difference |
| `agents-skills.README.md` | `.agents/skills/README.md` | authoring contract |
| `agents-subagents.README.md` | `.agents/subagents/README.md` | authoring contract |
| `subagent.metadata.json` + `subagent.instructions.md` | `.agents/subagents/code-reviewer/` (init) | deletable example, exercises the source → projection round-trip |
| `husky.pre-commit` | merged into `.husky/pre-commit` (npm/husky projects) | only the `--check` drift line is harness-owned |
| `gitignore.snippet` | appended to `.gitignore` | always `.claude/settings.local.json`; default profile also adds `.worktrees/` and `.claude/allow-trunk-edit` |

Formatter, linter, test, and code-generation hooks are project policy rather than bundled runtime.
Keep their implementations outside `.agents/tools/` and wire them as user-owned hook entries; see
[host integration](host-integration.md#project-owned-formatting-hooks).

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
- **Drift guard**: the installer adds `python .agents/tools/generate-subagents.py --check` to
  `.husky/pre-commit` on a husky/npm project (alongside the `gen:subagents` / `check:agents` npm
  scripts; activate husky with `npm install -D husky && npm run prepare`). If the project uses a
  different hook manager (lefthook / pre-commit) or no `package.json` at all, the installer leaves it
  alone and prints the one line to wire into your pre-commit / CI.

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
