# agent-scaffold — reference

Deep material for the `agent-scaffold` skill. Read on demand; `SKILL.md` is the lean router.

- [1. Bundled files: provenance + landing](#1-bundled-files-provenance--landing)
- [2. Hook semantics](#2-hook-semantics)
- [3. Dual-host wiring (exact snippets)](#3-dual-host-wiring-exact-snippets)
- [4. The JSON-merge algorithm](#4-the-json-merge-algorithm)
- [5. The `.agents/` SSOT model](#5-the-agents-ssot-model)
- [6. AGENTS.md governance & budget](#6-agentsmd-governance--budget)
- [7. Codex trust gate](#7-codex-trust-gate)
- [8. Node vs non-Node degradation](#8-node-vs-non-node-degradation)
- [9. format_on_edit genericization](#9-format_on_edit-genericization)
- [10. Coexistence with `npx skills`](#10-coexistence-with-npx-skills)
- [11. Troubleshooting](#11-troubleshooting)
- [12. End-to-end test recipe](#12-end-to-end-test-recipe)

---

## 1. Bundled files: provenance + landing

`npx skills` installs each skill as a self-contained directory — a skill cannot reference
files from a sibling skill at runtime, so this skill carries its **own** copy of every script
it installs. The installer (`harness-init.sh`) reads from `templates/` and writes into the target.

| `templates/` file | Lands at (target) | Notes |
|---|---|---|
| `worktree.sh` | `tools/agent/worktree.sh` | worktree-per-change lifecycle (new/done/release/list) |
| `trunk_edit_guard.sh` | `tools/agent/hooks/trunk_edit_guard.sh` | PreToolUse trunk-edit blocker (dual-host `proj=` resolver) |
| `authority_doc_budget.sh` | `tools/agent/hooks/authority_doc_budget.sh` | PostToolUse AGENTS.md line-budget advisor |
| `format_on_edit.sh` | `tools/agent/hooks/format_on_edit.sh` | PostToolUse formatter (default Prettier; env-overridable) |
| `relink-skills.sh` | `.agents/relink-skills.sh` | idempotent skill symlink rebuild |
| `generate-subagents.mjs` | `tools/agent/generate-subagents.mjs` | subagent projection + `--check` drift mode (Node) |
| `claude.settings.json` | merged into `.claude/settings.json` | CC hook block (merge source) |
| `codex.hooks.json` | merged into `.codex/hooks.json` | Codex hook block (merge source) |
| `codex.config.toml` | `.codex/config.toml` (create if missing) | trust-gate note; sets nothing else |
| `AGENTS.root.md` | `AGENTS.md` (init) / harness block injected (retrofit) | the `<!-- agent-scaffold:start … end -->` block is the reusable contract |
| `AGENTS.nested.md` | `<dir>/AGENTS.md` (on request) | hierarchical, parent-linked nested template w/ `<!-- Parent -->` |
| `agents-skills.README.md` | `.agents/skills/README.md` | authoring contract |
| `agents-subagents.README.md` | `.agents/subagents/README.md` | authoring contract |
| `subagent.metadata.json` + `subagent.instructions.md` | `.agents/subagents/code-reviewer/` (init) | deletable example, exercises the Node round-trip |
| `husky.pre-commit` | merged into `.husky/pre-commit` (Node) | only the `--check` drift line is harness-owned |
| `gitignore.snippet` | appended to `.gitignore` | `.worktrees/`, `.claude/settings.local.json`, `.claude/allow-trunk-edit` |

The vendored scripts derive their own paths (git-common-dir / `$BASH_SOURCE`), so they are
layout-independent once they land at the paths above. **They are intentionally tuned for the
`tools/agent/` install depth** — e.g. `trunk_edit_guard.sh` resolves `proj` three levels up
(`tools/agent/hooks/` → repo root) plus a git-toplevel fallback for Codex. Do not "simplify" that
resolver to a shallower path: the git-toplevel fallback is what makes the hooks work under Codex
(which has no `$CLAUDE_PROJECT_DIR`), and `scripts/check-agent-scaffold.sh` guards this invariant.

## 2. Hook semantics

All three hooks read the tool-call JSON on **stdin**, extract the touched file path(s) with
`python3` (preferred) or `jq` (fallback), and **fail open** when neither is available. Each
only acts on files in the **project repo** (same git-common-dir as the resolved project root),
so edits to nested/sibling repos pass through; gitignored paths are exempt.

### trunk_edit_guard.sh — PreToolUse, blocking

- **Exit 0** allow · **exit 2** block (message on stderr) · any other exit = non-blocking error (fails open).
- Blocks an edit to a file in a worktree whose branch is a **trunk** (`main` / `master` / `release/*` / `maintenance/*`), unless an escape hatch is active.
- **Escape hatches** (only when the user explicitly authorizes a trunk edit):
  - `WORKTREE_ALLOW_TRUNK_EDIT=1` — one-shot env bypass.
  - `touch <repo>/.claude/allow-trunk-edit` — flag file, auto-expires **2 h** (mtime check `now - mtime <= 7200`); re-touch to renew.
- `WORKTREE_GUARD_CMD` overrides the command shown in the block message (default `tools/agent/worktree.sh`).

### authority_doc_budget.sh — PostToolUse, advisory (never blocks)

- Watches `AGENTS.md` / `CLAUDE.md` writes; resolves the `CLAUDE.md → AGENTS.md` symlink so each contract is measured once.
- Budgets: **root `AGENTS.md` 320** lines, **nested `AGENTS.md` 120** lines. Override with `AUTHORITY_DOC_MAX_ROOT` / `AUTHORITY_DOC_MAX_NESTED`.
- Over budget → emits a nudge as PostToolUse `additionalContext` (via jq), else to stderr. Always **exit 0**.

### format_on_edit.sh — PostToolUse, advisory (never blocks)

- Runs the project's formatter on edited files; reports what it rewrote as `additionalContext` so you re-read before further exact-string edits. See [§9](#9-format_on_edit-genericization) for the `FORMAT_ON_EDIT_CMD` / `FORMAT_ON_EDIT_EXTS` overrides and the runtime self-skip.

## 3. Dual-host wiring (exact snippets)

Both hosts invoke the **same** scripts under `tools/agent/hooks/`. The installer writes both
forms; do **not** "simplify" one host's path form to match the other — they differ on purpose.

**Claude Code — `.claude/settings.json`:**

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit|MultiEdit|Write|NotebookEdit",
        "hooks": [ { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/tools/agent/hooks/trunk_edit_guard.sh" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/tools/agent/hooks/format_on_edit.sh" },
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/tools/agent/hooks/authority_doc_budget.sh" }
        ] }
    ]
  }
}
```

**Codex — `.codex/hooks.json`:** matcher `Edit|Write|apply_patch`; each command wrapped so
Codex (which has no `$CLAUDE_PROJECT_DIR`) resolves the repo root itself:

```json
{ "type": "command",
  "command": "bash -lc 'root=\"$(git rev-parse --show-toplevel 2>/dev/null)\" || exit 0; \"$root/tools/agent/hooks/trunk_edit_guard.sh\"'",
  "statusMessage": "Checking worktree policy" }
```

**Why two forms:** Claude Code sets `$CLAUDE_PROJECT_DIR`; Codex does not, so its hook resolves
`git rev-parse --show-toplevel` at call time. Either way, the **hook script itself** bridges
both via its `proj=` line:

```bash
proj="${CLAUDE_PROJECT_DIR:-$(git -C "$hook_dir" rev-parse --show-toplevel 2>/dev/null || (cd "$hook_dir/../../.." && pwd))}"
```

## 4. The JSON-merge algorithm

Retrofitting must **add** our hook entries without clobbering existing ones or duplicating on
re-run. The installer never string-munges JSON; it uses **jq → node → "paste this block"**:

1. **Missing config** → write the template verbatim.
2. **Existing config** → for each event (`PreToolUse`/`PostToolUse`) and our matcher, ensure a
   matcher group exists; within it, **union hooks by `.command`** (exact string). Idempotent:
   re-running adds nothing because the command strings are identical.
3. **Neither jq nor node** → print the block to paste by hand and flag the run as deferred
   (`HARNESS_MERGE_DEFERRED`), rather than risk corrupting the file.

The jq core (`mergeEvent` matches groups by `.matcher`; `unionByCommand` dedups by `.command`):

```jq
def unionByCommand($a; $b):
  reduce $b[] as $h ($a; if (map(.command) | index($h.command)) then . else . + [$h] end);
def mergeEvent($cur; $add):
  reduce $add[] as $g ($cur;
    (map(.matcher == $g.matcher) | index(true)) as $i
    | if $i == null then . + [$g]
      else .[$i].hooks = unionByCommand((.[$i].hooks // []); ($g.hooks // [])) end);
```

Writes are atomic (`> tmp && mv`). `package.json` script keys (`gen:subagents`, `check:agents`,
optional `prepare: husky`) are merged the same way — added only when absent.

**Idempotency keys:** hooks by exact `.command` + `.matcher`; `.gitignore`/`.husky/pre-commit`
lines by `grep -qxF`; `package.json` scripts by key presence; the `AGENTS.md` harness section by
the `<!-- agent-scaffold:start … end -->` markers.

## 5. The `.agents/` SSOT model

`.agents/` is the single source of truth; `.claude/` and `.codex/` are **projections**.

| | Source (edit here) | Claude Code | Codex |
|---|---|---|---|
| **Skills** | `.agents/skills/<name>/SKILL.md` | `.claude/skills/<name>` **symlink** (via `relink-skills.sh`) | reads `.agents/skills/` directly |
| **Subagents** | `.agents/subagents/<name>/{metadata.json,instructions.md}` | `.claude/agents/<name>.md` **generated** | `.codex/agents/<name>.toml` **generated** |

- **Skills**: `relink-skills.sh` rebuilds the symlinks idempotently. Codex needs no symlinks.
- **Subagents**: `generate-subagents.mjs` projects each source into both host formats (YAML
  frontmatter + body for CC; TOML with `developer_instructions` for Codex). **Never hand-edit**
  the generated files — they carry a "do not edit" banner. `--check` exits 1 on drift; wire it
  into pre-commit / CI (`npm run check:agents`).
- **Drift guard**: on a Node project the installer adds `node tools/agent/generate-subagents.mjs --check`
  to `.husky/pre-commit` and the `gen:subagents` / `check:agents` npm scripts. Activate husky with
  `npm install -D husky && npm run prepare` if it is not installed yet. If the project uses a
  different hook manager (lefthook / pre-commit), the installer leaves it alone and prints the one
  line to wire in.

## 6. AGENTS.md governance & budget

`AGENTS.md` (root + every subdirectory; `CLAUDE.md` is a symlink to the root) is an **entry
point, not a detail dump** — put depth in `docs/` and link back; inline only important,
frequently-needed points. The `authority_doc_budget.sh` hook advises when a contract crosses its
line budget (root 320 / nested 120). Nested contracts carry `<!-- Parent: ../AGENTS.md -->` and
stay subordinate to the root.

**Retrofit never overwrites a hand-authored `AGENTS.md`.** The installer manages only the marked
block:

- No `AGENTS.md` → write `AGENTS.root.md` (stub project sections + the harness block).
- `AGENTS.md` with the markers → replace **only** the block, preserving surrounding prose.
- `AGENTS.md` without the markers → append the block (review placement).

Keep project prose **outside** the `<!-- agent-scaffold:start … end -->` markers; `upgrade`
refreshes everything between them.

### Generating the nested AGENTS.md tree

For a multi-directory codebase, give each **significant** directory its own `AGENTS.md` from
`templates/AGENTS.nested.md`, so an agent dropped anywhere can answer "what is this directory, how
does it relate to the rest, how do I work here" without re-deriving the repo. The tree is
parent-linked and refreshable:

- **Pick significant dirs.** A directory earns an `AGENTS.md` when it holds source / config / assets
  an agent reads or edits. **Skip** generated/vendored noise: `node_modules`, `.git`, `dist`,
  `build`, `out`, `target`, `.venv`, `__pycache__`, `coverage`, `.next`, `.nuxt`, `vendor`. Empty
  dir → skip; subdir-only dir → a minimal Purpose + Subdirectories file.
- **Generate parent-first.** Root first (no parent tag), then level 1, then level 2 … so every
  `<!-- Parent: ../AGENTS.md -->` resolves the moment it is written. Independent dirs at the same
  depth can be done in parallel; never a child before its parent.
- **Fill from real content** — accurate file roles, real subdirectory purposes, the conventions an
  agent must follow here, actual dependencies. No generic filler.
- **Update, don't clobber.** If an `AGENTS.md` exists, preserve everything below
  `<!-- MANUAL: notes below this line are preserved on regeneration -->` verbatim, refresh the auto
  sections to match current files, and fix the parent path if the file moved.
- **Validate.** Root has no parent tag; every other file's parent path resolves and chains to the
  single root (no orphans, no cycles); every significant dir is covered; no `AGENTS.md` survives in
  a deleted dir. Keep each file under the nested budget (120 lines) — an entry point, not a dump.

## 7. Codex trust gate

Project-level `.codex/` (config + hooks + agents) **only loads for a TRUSTED project**. Until the
project is trusted, the entire project-level `.codex/` — including the worktree guard — is
silently skipped, so the harness looks half-installed on the Codex side. Trust once:

- run `codex` in the repo and accept the prompt, **or**
- add to `~/.codex/config.toml`:
  ```toml
  [projects."<repo absolute path>"]
  trust_level = "trusted"
  ```

`verify` cannot read your `~/.codex/config.toml` reliably across machines, so it always prints
the trust reminder rather than asserting trust.

## 8. Node vs non-Node degradation

| Capability | Needs | Without it |
|---|---|---|
| worktree flow, 3 hooks, `relink-skills.sh`, both host configs, `AGENTS.md` contract | bash (+ python3 **or** jq for hook JSON; jq **or** node for the config merge) | always installed |
| subagent projection (`generate-subagents.mjs`) + `--check` drift guard + npm scripts | Node (`package.json` at root) | cleanly skipped; installer says how to enable |

To enable subagents later on a project that gained Node: add a `package.json`, then re-run
`agent-scaffold upgrade`.

## 9. format_on_edit genericization

`format_on_edit.sh` defaults to the project's Prettier on `ts tsx js mjs cjs json`, but is not
Prettier-locked:

- **Runtime self-skip**: if the formatter launcher isn't on `PATH` (e.g. no `npx`), it exits 0 as
  a no-op — safe to wire into any project.
- **Overrides** (env, e.g. in `.claude/settings.local.json`): `FORMAT_ON_EDIT_CMD` (the file path
  is appended as the last arg; default `npx --no-install prettier --write`) and
  `FORMAT_ON_EDIT_EXTS` (space-separated, no dots; default `ts tsx js mjs cjs json`). Examples:
  `FORMAT_ON_EDIT_CMD="gofmt -w" FORMAT_ON_EDIT_EXTS="go"`, `FORMAT_ON_EDIT_CMD="ruff format" FORMAT_ON_EDIT_EXTS="py pyi"`.
- **Install gating**: `--no-format-hook` omits it from the wiring (the script is still copied so
  `upgrade` can enable it later). Because it self-skips, wiring it into a non-JS project is also
  harmless — it just never fires.

## 10. Coexistence with `npx skills`

Two mechanisms live side by side, partitioned by **symlink (ours) vs real directory (theirs)**:

- **Project-authored** skills/subagents live in `.agents/` and project into `.claude/`/`.codex/`.
- **Third-party** skills install via `npx skills add <repo> -a claude-code -a codex` and land as
  **real directories** in `.claude/skills/`. `relink-skills.sh` only manages **symlinks**, so it
  skips and never touches a real directory (`skip … not a symlink (vendor-native skill?)`).
- **Name-clash caveat**: if a project skill and an installed skill share a name, the relinker
  skips yours and the installed one wins under that name in CC. Keep names distinct.

## 11. Troubleshooting

- **Hooks don't fire (Codex)** → the project isn't trusted ([§7](#7-codex-trust-gate)); or a matcher typo; or the script isn't executable (`chmod +x tools/agent/hooks/*.sh`).
- **Hooks don't fire (Claude Code)** → confirm `.claude/settings.json` parses and the command path is right; restart the session after editing settings.
- **Duplicate hook entries after a re-run** → shouldn't happen (dedup by `.command`); if you hand-edited a command string, the dedup key changed — align it with the template or run `upgrade`.
- **`generate-subagents --check` fails in CI** → run `npm run gen:subagents` and commit the regenerated `.claude/agents/*` + `.codex/agents/*`.
- **`relink-skills.sh` skipped my skill** → a real directory of the same name exists in `.claude/skills/` (likely an `npx`-installed skill). Rename one ([§10](#10-coexistence-with-npx-skills)).
- **`trunk_edit_guard` blocks everything** → you're on a trunk branch. Start a worktree: `tools/agent/worktree.sh new <name>`. Only with explicit authorization: `touch .claude/allow-trunk-edit` (2 h).
- **Symlinks on Windows** → `CLAUDE.md → AGENTS.md` and the `.claude/skills/*` symlinks need symlink support (`git config core.symlinks true` + privilege). If creation fails, the installer warns; create a `CLAUDE.md` mirror by hand.

## 12. End-to-end test recipe

Run on a throwaway repo (all writes are inside it). This is the recipe the skill is validated
against; every assertion below passes against a clean install.

```bash
SKILL=<this skill dir>            # the dir holding harness-init.sh
H="$SKILL/harness-init.sh"
rm -rf /tmp/scratch && mkdir -p /tmp/scratch && cd /tmp/scratch
git init -q -b main && git config user.email t@t.t && git config user.name tester
git commit --allow-empty -qm init

# init (greenfield)
bash "$H" init
[ -z "$(ls -A .claude/skills)" ]                                             # no bogus '*' symlink
test -x tools/agent/worktree.sh && test -x tools/agent/hooks/trunk_edit_guard.sh
test -L CLAUDE.md && [ "$(readlink CLAUDE.md)" = AGENTS.md ]
jq -e '.hooks.PreToolUse[0].matcher=="Edit|MultiEdit|Write|NotebookEdit"' .claude/settings.json
jq -e '.hooks.PreToolUse[0].matcher=="Edit|Write|apply_patch"'              .codex/hooks.json
grep -q '^\.worktrees/$' .gitignore

# idempotent re-run — PostToolUse stays 2 hooks, not 4
bash "$H" retrofit
jq -e '[.hooks.PostToolUse[0].hooks[].command]|length==2' .claude/settings.json

# retrofit-merge preserves a pre-existing user hook
jq '.hooks.PreToolUse[0].hooks += [{"type":"command","command":"user-custom.sh"}]' .claude/settings.json > t && mv t .claude/settings.json
bash "$H" retrofit
jq -e '[.hooks.PreToolUse[].hooks[].command]|any(test("trunk_edit_guard"))' .claude/settings.json
jq -e '[.hooks.PreToolUse[].hooks[].command]|any(test("user-custom"))'      .claude/settings.json

# worktree round-trip (commit the harness first so the worktree has the scripts)
git add -A && git commit -qm harness
bash tools/agent/worktree.sh new demo --type chore && test -d .worktrees/demo
( cd .worktrees/demo && echo hi > note.txt && git add -A && git commit -qm "feat: note" && bash tools/agent/worktree.sh done --no-push )
test ! -d .worktrees/demo && git log --oneline | grep -q "Merge branch 'chore/demo'"

# trunk guard blocks on main; escape hatch allows
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$PWD" | CLAUDE_PROJECT_DIR="$PWD" tools/agent/hooks/trunk_edit_guard.sh; echo "exit=$?"   # 2
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$PWD" | WORKTREE_ALLOW_TRUNK_EDIT=1 CLAUDE_PROJECT_DIR="$PWD" tools/agent/hooks/trunk_edit_guard.sh; echo "exit=$?"  # 0

# Node path: generator + drift guard + scripts
echo '{"name":"scratch","version":"1.0.0"}' > package.json
bash "$H" upgrade
node tools/agent/generate-subagents.mjs --check        # exit 0, in sync
grep -q 'generate-subagents.mjs --check' .husky/pre-commit
jq -e '.scripts["check:agents"]' package.json

# authority budget advises over-budget
seq 1 400 | sed 's/^/line /' > AGENTS.md
printf '{"tool_input":{"file_path":"%s/AGENTS.md"}}' "$PWD" | AUTHORITY_DOC_MAX_ROOT=320 CLAUDE_PROJECT_DIR="$PWD" tools/agent/hooks/authority_doc_budget.sh   # prints budget nudge, exit 0

# relink coexistence: project skill symlinked, npx-installed real dir untouched
mkdir -p .agents/skills/proj-skill && printf -- '---\nname: proj-skill\n---\n' > .agents/skills/proj-skill/SKILL.md
mkdir -p .claude/skills/vendor-skill && echo x > .claude/skills/vendor-skill/SKILL.md
bash .agents/relink-skills.sh
test -L .claude/skills/proj-skill && test -d .claude/skills/vendor-skill && ! test -L .claude/skills/vendor-skill

# verify mode (read-only) reports OK on a clean install
bash "$H" verify
```
