# agent-scaffold — reference

Deep material for the `agent-scaffold` skill. Read on demand; `SKILL.md` is the lean router.

> **Platform target:** macOS / Linux / Windows (**Git Bash only**), with Bash 3.2 as the
> shell baseline. Bundled scripts stay **LF-only**. Real file + directory symlinks are a hard
> prerequisite: `doctor` and every mutating entry fail before target writes when capability is
> missing. There is no copy fallback. Windows/Git Bash specifics: [§11](#11-troubleshooting).

- [1. Bundled files: provenance + landing](#1-bundled-files-provenance--landing)
- [2. Hook semantics](#2-hook-semantics)
- [3. Dual-host wiring](#3-dual-host-wiring)
- [4. The JSON-merge algorithm](#4-the-json-merge-algorithm)
- [5. The `.agents/` SSOT model](#5-the-agents-ssot-model)
- [6. AGENTS.md governance & budget](#6-agentsmd-governance--budget)
- [7. Codex trust gate](#7-codex-trust-gate)
- [8. Subagent generator (python)](#8-subagent-generator-python)
- [9. format_on_edit genericization](#9-format_on_edit-genericization)
- [10. Coexistence with `npx skills`](#10-coexistence-with-npx-skills)
- [11. Troubleshooting](#11-troubleshooting)
- [12. End-to-end test recipe](#12-end-to-end-test-recipe)
- [13. Retrofitting an in-flight project (migration & adoption)](#13-retrofitting-an-in-flight-project-migration--adoption)

---

## 1. Bundled files: provenance + landing

`npx skills` installs each skill as a self-contained directory — a skill cannot reference
files from a sibling skill at runtime, so this skill carries its **own** copy of every script
it installs. The installer (`harness-init.sh`) reads from `templates/` and writes into the target.

| `templates/` file | Lands at (target) | Notes |
|---|---|---|
| `worktree.sh` | `tools/agent/worktree.sh` | default profile only: worktree-per-change lifecycle (new/done/release/list) |
| `trunk_edit_guard.sh` | `tools/agent/hooks/trunk_edit_guard.sh` | default profile only: PreToolUse trunk-edit blocker (dual-host `proj=` resolver) |
| `authority_doc_budget.sh` | `tools/agent/hooks/authority_doc_budget.sh` | PostToolUse AGENTS.md line-budget advisor |
| `format_on_edit.sh` | `tools/agent/hooks/format_on_edit.sh` | PostToolUse formatter (default Prettier; env-overridable) |
| `hook-common.sh` + `hook-paths.py` | `tools/agent/hooks/` | shared Python JSON parser + Git Bash/native path normalization |
| `relink-skills.sh` | `.agents/relink-skills.sh` | idempotent skill symlink rebuild |
| `symlink-manager.py` | `.agents/symlink-manager.py` | doctor, atomic real-link creation, migration, sync, and verification |
| `generate-subagents.py` | `tools/agent/generate-subagents.py` | subagent projection + `--check` drift mode (python) |
| `claude.settings.json` | merged into `.claude/settings.json` | CC hook block (merge source) |
| `codex.hooks.json` | merged into `.codex/hooks.json` | Codex hook block (merge source) |
| `codex.config.toml` | `.codex/config.toml` (create if missing) | trust-gate note; sets nothing else |
| `AGENTS.root.md` | `AGENTS.md` (init) / harness block injected (retrofit) | the `<!-- agent-scaffold:start … end -->` block is the reusable contract |
| `AGENTS.nested.md` | `<dir>/AGENTS.md` (on request) | hierarchical, parent-linked nested template w/ `<!-- Parent -->` |
| `agents-skills.README.md` | `.agents/skills/README.md` | authoring contract |
| `agents-subagents.README.md` | `.agents/subagents/README.md` | authoring contract |
| `subagent.metadata.json` + `subagent.instructions.md` | `.agents/subagents/code-reviewer/` (init) | deletable example, exercises the source → projection round-trip |
| `husky.pre-commit` | merged into `.husky/pre-commit` (npm/husky projects) | only the `--check` drift line is harness-owned |
| `gitignore.snippet` | appended to `.gitignore` | always `.claude/settings.local.json`; default profile also adds `.worktrees/` and `.claude/allow-trunk-edit` |

The vendored scripts derive their own paths (git-common-dir / `$BASH_SOURCE`), so they are
layout-independent once they land at the paths above. **They are intentionally tuned for the
`tools/agent/` install depth** — e.g. `trunk_edit_guard.sh` resolves `proj` three levels up
(`tools/agent/hooks/` → repo root) plus a git-toplevel fallback for Codex. Do not "simplify" that
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

## 2. Hook semantics

All three hooks read the tool-call JSON on **stdin**. `hook-paths.py` only parses raw paths and
payload cwd; `hook-common.sh` converts `C:/…`, backslash, UNC, Git Bash, relative, spaces, and
Unicode paths into the Bash namespace (using `cygpath` on Windows). Each hook only acts on files
in the **project repo** (same git-common-dir as the resolved project root), so edits to
nested/sibling repos pass through; gitignored paths are exempt. A damaged/missing helper fails open.

### trunk_edit_guard.sh — PreToolUse, blocking

- Installed and wired only by the default profile; `--no-worktree` removes the managed wiring.
- **Exit 0** allow · **exit 2** block (message on stderr) · any other exit = non-blocking error (fails open).
- Blocks an edit to a file in a worktree whose branch is a **trunk** (`main` / `master` / `release/*` / `maintenance/*`), unless an escape hatch is active.
- **Escape hatches** (only when the user explicitly authorizes a trunk edit):
  - `WORKTREE_ALLOW_TRUNK_EDIT=1` — one-shot env bypass.
  - `touch <repo>/.claude/allow-trunk-edit` — flag file, auto-expires **2 h** (mtime check `now - mtime <= 7200`); re-touch to renew.
- `WORKTREE_GUARD_CMD` overrides the command shown in the block message (default `bash tools/agent/worktree.sh`).

### authority_doc_budget.sh — PostToolUse, advisory (never blocks)

- Watches `AGENTS.md` / `CLAUDE.md` writes; resolves the `CLAUDE.md → AGENTS.md` symlink so each contract is measured once.
- Budgets: **root `AGENTS.md` 320** lines, **nested `AGENTS.md` 120** lines. Override with `AUTHORITY_DOC_MAX_ROOT` / `AUTHORITY_DOC_MAX_NESTED`.
- Over budget → emits a nudge as PostToolUse `additionalContext` (via jq), else to stderr. Always **exit 0**.

### format_on_edit.sh — PostToolUse, advisory (never blocks)

- Runs the project's formatter on edited files; reports what it rewrote as `additionalContext` so you re-read before further exact-string edits. See [§9](#9-format_on_edit-genericization) for the `FORMAT_ON_EDIT_CMD` / `FORMAT_ON_EDIT_EXTS` overrides and the runtime self-skip.

## 3. Dual-host wiring

Both hosts invoke the **same** enabled scripts under `tools/agent/hooks/`. The installer writes both
forms; do **not** "simplify" one host's path form to match the other — they differ on purpose.
The PreToolUse examples below describe the default worktree profile; the lightweight profile
omits them entirely while retaining the PostToolUse hooks.

**Claude Code — `.claude/settings.json` shape** (the canonical full command strings live in
`templates/claude.settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit|MultiEdit|Write|NotebookEdit",
        "hooks": [ { "type": "command", "command": "bash -lc '<normalize project root>; bash \"$root/tools/agent/hooks/trunk_edit_guard.sh\"'" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          { "type": "command", "command": "bash -lc '<normalize project root>; bash \"$root/tools/agent/hooks/format_on_edit.sh\"'" },
          { "type": "command", "command": "bash -lc '<normalize project root>; bash \"$root/tools/agent/hooks/authority_doc_budget.sh\"'" }
        ] }
    ]
  }
}
```

**Codex — `.codex/hooks.json`:** matcher `Edit|Write|apply_patch`; each command wrapped so
Codex (which has no `$CLAUDE_PROJECT_DIR`) resolves the repo root itself:

```json
{ "type": "command",
  "command": "bash -lc 'root=\"$(git rev-parse --show-toplevel 2>/dev/null)\" || exit 0; bash \"$root/tools/agent/hooks/trunk_edit_guard.sh\"'",
  "statusMessage": "Checking worktree policy" }
```

**Why two forms:** Claude Code sets `$CLAUDE_PROJECT_DIR`; Codex does not, so its hook resolves
`git rev-parse --show-toplevel` at call time. Either way, `hook-common.sh` bridges both and
retains the install-depth fallback:

```bash
raw="${CLAUDE_PROJECT_DIR:-$(git -C "$hook_dir" rev-parse --show-toplevel 2>/dev/null || (cd "$hook_dir/../../.." && pwd))}"
proj="$(hook_posix_path "$raw")"
```

## 4. The JSON-merge algorithm

Retrofit/upgrade must refresh our hook commands without clobbering user hooks or retaining stale
N-1 strings. The Python reconciler parses JSON, removes only commands that invoke the exact owned
paths under `tools/agent/hooks/` (`trunk_edit_guard.sh`, `authority_doc_budget.sh`, or
`format_on_edit.sh`), then merges the current templates by event + matcher and deduplicates exact
commands. Legacy launchers and path prefixes still reconcile; basename lookalikes elsewhere remain
user-owned. Case-equivalent spellings reconcile only when the target filesystem resolves them to
the same installed hook; case-distinct paths remain user-owned. `--no-worktree` and
`--no-format-hook` omit their current managed commands and remove older managed entries while
leaving every user command and unrelated config key intact. Empty managed events are removed
rather than written as empty matcher groups. Python is a harness prerequisite, so this path has no
jq-dependent behavior or unsafe paste fallback.

Writes are atomic (`> tmp && mv`). `package.json` script keys (`gen:subagents`, `check:agents`,
optional `prepare: husky`) are merged the same way — added only when absent.

**Idempotency keys:** managed hook identity + current `.command`/`.matcher`; `.gitignore`/`.husky/pre-commit`
lines by `grep -qxF`; `package.json` scripts by key presence; the `AGENTS.md` harness section by
the `<!-- agent-scaffold:start … end -->` markers.

## 5. The `.agents/` SSOT model

`.agents/` is the single source of truth; `.claude/` and `.codex/` are **projections**.

| | Source (edit here) | Claude Code | Codex |
|---|---|---|---|
| **Skills** | `.agents/skills/<name>/SKILL.md` | `.claude/skills/<name>` **symlink** (via `relink-skills.sh`) | reads `.agents/skills/` directly |
| **Subagents** | `.agents/subagents/<name>/{metadata.json,instructions.md}` | `.claude/agents/<name>.md` **generated** | `.codex/agents/<name>.toml` **generated** |

- **Skills**: `relink-skills.sh` rebuilds the symlinks idempotently. Codex needs no symlinks.
- **Subagents**: `generate-subagents.py` projects each source into both host formats (YAML
  frontmatter + body for CC; TOML with `developer_instructions` for Codex). **Never hand-edit**
  the generated files — they carry a "do not edit" banner. `--check` exits 1 on drift; wire it
  into pre-commit / CI (`python tools/agent/generate-subagents.py --check`). `--import` does the
  reverse — adopt hand-authored host agents into sources ([§13](#13-retrofitting-an-in-flight-project-migration--adoption)).
- **Drift guard**: the installer adds `python tools/agent/generate-subagents.py --check` to
  `.husky/pre-commit` on a husky/npm project (alongside the `gen:subagents` / `check:agents` npm
  scripts; activate husky with `npm install -D husky && npm run prepare`). If the project uses a
  different hook manager (lefthook / pre-commit) or no `package.json` at all, the installer leaves it
  alone and prints the one line to wire into your pre-commit / CI.

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
- Unbalanced, duplicated, or reversed markers → abort before target mutation; repair the marker
  pair manually, then rerun `plan` or the requested install/upgrade command.

Keep project prose **outside** the `<!-- agent-scaffold:start … end -->` markers; `upgrade`
refreshes everything between them. The template's inner worktree boundary is installer-owned:
`--no-worktree` removes that complete policy and its worktree-only layout rows.

When the contract lives in a **real `CLAUDE.md`** with no `AGENTS.md` yet, retrofit adopts that
prose as the `AGENTS.md` SSOT and replaces `CLAUDE.md` with the symlink — see
[§13](#13-retrofitting-an-in-flight-project-migration--adoption).

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
project is trusted, the entire project-level `.codex/` — including configured hooks and the
optional worktree guard — is
silently skipped, so the harness looks half-installed on the Codex side. Trust once:

- run `codex` in the repo and accept the prompt, **or**
- add to `~/.codex/config.toml`:
  ```toml
  [projects."<repo absolute path>"]
  trust_level = "trusted"
  ```

`verify` cannot read your `~/.codex/config.toml` reliably across machines, so it always prints
the trust reminder rather than asserting trust.

## 8. Subagent generator (python)

| Capability | Needs | Without it |
|---|---|---|
| full harness, real-link manager, hooks, and subagent projection | git + Bash 3.2+ + Python 3.8+ + real file/directory links | preflight exits 2 before target mutation |
| `gen:subagents` / `check:agents` npm scripts + husky `--check` hook | a `package.json` (npm/husky) | other hook managers / CI: installer prints the one line to wire |

`generate-subagents.py`, `symlink-manager.py`, and `hook-paths.py` use only the Python standard
library — no Node or `package.json`. Resolve Python with `PYTHON_BIN`, `python`, `python3`, or
Windows `py -3`. Node remains an optional convenience surface only.

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

Two mechanisms live side by side, partitioned by **managed target (ours) vs other entry (theirs)**:

- **Project-authored** skills/subagents live in `.agents/` and project into `.claude/`/`.codex/`.
- **Third-party** skills install via `npx skills add <repo> -a claude-code -a codex` and land as
  **real directories** in `.claude/skills/`. `relink-skills.sh` never touches unrelated real
  directories or symlinks. A same-name project source is a conflict: it is preserved and the
  relinker exits 2 rather than silently choosing one owner.
- **Legacy migration**: a Git target-text placeholder or byte-identical historical copy is safe to
  replace with a real relative link; drifted content is always preserved as a reported conflict.

## 11. Troubleshooting

- **Hooks don't fire (Codex)** → the project isn't trusted ([§7](#7-codex-trust-gate)); or a matcher typo; or `bash` resolves outside the supported Unix/Git Bash runtime. Hook commands explicitly invoke Bash and do not depend on checkout executable bits.
- **Hooks don't fire (Claude Code)** → confirm `.claude/settings.json` parses and the command path is right; restart the session after editing settings.
- **Duplicate/stale managed hook entries** → run `upgrade` with the same profile flags used for install; it removes only agent-scaffold-owned identities and writes the enabled current commands while preserving user hooks.
- **`generate-subagents --check` fails in CI** → run `python tools/agent/generate-subagents.py` and commit the regenerated `.claude/agents/*` + `.codex/agents/*`.
- **`relink-skills.sh` reports a conflict** → a differing real directory or unrelated symlink of the same name exists in `.claude/skills/` (often an `npx`-installed skill). It was preserved; rename one owner ([§10](#10-coexistence-with-npx-skills)).
- **`trunk_edit_guard` blocks everything** → you're using the default profile on a trunk branch. Start a worktree: `bash tools/agent/worktree.sh new <name>`. Only with explicit authorization: `touch .claude/allow-trunk-edit` (2 h). If the project intentionally does not use this workflow, rerun `upgrade --no-worktree` and keep that flag on later verify/upgrade calls.
- **Windows / Git Bash** (the only supported Windows surface) → install Python, enable Developer Mode (or run with native symlink privilege), and make the target repo's **effective** `git config --get core.symlinks` equal `true` (remove a local `false` override if necessary). Run `bash <skill-dir>/harness-init.sh doctor`; it must pass both file and directory probes. Link creation uses Python `os.symlink`, so it no longer depends on MSYS `ln -s` behavior. The installer also pins vendored shell/Python files and `.husky/pre-commit` to LF. Capability failure exits 2 before target writes and leaves no copy or partial harness.

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
bash "$H" doctor
bash "$H" init
[ -z "$(ls -A .claude/skills)" ]                                             # no bogus '*' symlink
test -f tools/agent/worktree.sh && test -f tools/agent/hooks/trunk_edit_guard.sh
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
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$PWD" | CLAUDE_PROJECT_DIR="$PWD" bash tools/agent/hooks/trunk_edit_guard.sh; echo "exit=$?"   # 2
printf '{"tool_input":{"file_path":"%s/README.md"}}' "$PWD" | WORKTREE_ALLOW_TRUNK_EDIT=1 CLAUDE_PROJECT_DIR="$PWD" bash tools/agent/hooks/trunk_edit_guard.sh; echo "exit=$?"  # 0

# subagents: generator + drift guard (python — no package.json needed)
bash "$H" upgrade
python tools/agent/generate-subagents.py --check      # exit 0, in sync
# opt-in npm convenience + husky hook on a Node project:
echo '{"name":"scratch","version":"1.0.0"}' > package.json
bash "$H" upgrade
grep -q 'generate-subagents.py --check' .husky/pre-commit
jq -e '.scripts["check:agents"]' package.json

# authority budget advises over-budget
seq 1 400 | sed 's/^/line /' > AGENTS.md
printf '{"tool_input":{"file_path":"%s/AGENTS.md"}}' "$PWD" | AUTHORITY_DOC_MAX_ROOT=320 CLAUDE_PROJECT_DIR="$PWD" bash tools/agent/hooks/authority_doc_budget.sh   # prints budget nudge, exit 0

# relink coexistence: project skill symlinked, npx-installed real dir untouched
mkdir -p .agents/skills/proj-skill && printf -- '---\nname: proj-skill\n---\n' > .agents/skills/proj-skill/SKILL.md
mkdir -p .claude/skills/vendor-skill && echo x > .claude/skills/vendor-skill/SKILL.md
bash .agents/relink-skills.sh
test -L .claude/skills/proj-skill && test -d .claude/skills/vendor-skill && ! test -L .claude/skills/vendor-skill

# verify mode (read-only) reports OK on a clean install
bash "$H" verify

# lightweight profile (separate throwaway repo)
rm -rf /tmp/scratch-light && mkdir -p /tmp/scratch-light && cd /tmp/scratch-light
git init -q -b main && git config user.email t@t.t && git config user.name tester
git commit --allow-empty -qm init
bash "$H" plan --no-worktree | grep -qF 'retrofit --no-worktree'   # copyable apply command keeps the flag
bash "$H" init --no-worktree --no-husky --no-example-subagent
test ! -e tools/agent/worktree.sh && test ! -e tools/agent/hooks/trunk_edit_guard.sh
! grep -q trunk_edit_guard .claude/settings.json && ! grep -q trunk_edit_guard .codex/hooks.json
! grep -qF 'Worktree-per-change (hard rule)' AGENTS.md
bash "$H" verify --no-worktree
# The profile flag is per-invocation; plain `upgrade` deliberately restores the default profile.

# plan is read-only; retrofit adopts a real CLAUDE.md as the AGENTS.md SSOT
rm -rf /tmp/scratch2 && mkdir -p /tmp/scratch2 && cd /tmp/scratch2
git init -q -b main && git config user.email t@t.t && git config user.name tester
git commit --allow-empty -qm init
printf '# Legacy\n\nrules\n' > CLAUDE.md && git add -A && git commit -qm legacy
bash "$H" plan | grep -q migrate                                             # plan flags the migration
bash "$H" retrofit
test -L CLAUDE.md && [ "$(readlink CLAUDE.md)" = AGENTS.md ] && grep -q rules AGENTS.md

# adopt a hand-authored subagent into the SSOT (python — no package.json needed)
mkdir -p .claude/agents
printf -- '---\nname: rev\ndescription: hand-authored\ntools: Read\n---\n\nReview.\n' > .claude/agents/rev.md
bash "$H" upgrade
test -f .agents/subagents/rev/metadata.json && python tools/agent/generate-subagents.py --check
```

## 13. Retrofitting an in-flight project (migration & adoption)

`init` and `retrofit` share one code path; what makes `retrofit` safe on a project already
mid-development is that it **adopts** existing assets into the SSOT instead of ignoring or
clobbering them. Preview any of it with `plan` (read-only).

### plan — preview before you write

`bash <skill-dir>/harness-init.sh plan` reports, per concern, whether the run would **create**,
**merge**, **migrate**, or leave something for you (**needs you**), and writes nothing. Use it to
see — before touching the repo — what an existing `CLAUDE.md`, hook config, or hand-authored
subagent will turn into.

### Adopting a real CLAUDE.md

Many live projects already carry a hand-written `CLAUDE.md`. Retrofit treats `AGENTS.md` as the
SSOT and `CLAUDE.md` as its symlink, so:

- **real `CLAUDE.md`, no `AGENTS.md`** → the prose is copied into `AGENTS.md`, the harness block is
  appended (or refreshed if the prose already carried the markers), and the real `CLAUDE.md` is
  replaced with the `CLAUDE.md → AGENTS.md` symlink. Nothing is lost — the content moves, it is not
  deleted.
- **real `CLAUDE.md` *and* real `AGENTS.md`** → ambiguous (two authored files); the installer keeps
  both and exits with a conflict after telling you to merge `CLAUDE.md` into `AGENTS.md` by hand.
- **already the correct symlink** → left as-is; a different symlink target is preserved as a conflict.

### Adopting hand-authored subagents (`--import`, python)

A project may already have hand-written `.claude/agents/*.md` or `.codex/agents/*.toml`. Python is
a harness prerequisite, and the installer runs `generate-subagents.py --import` before projecting:

1. For each host agent file with **no** `.agents/subagents/<name>/` source and **no** canonical,
   name-matched generated marker at the host format's expected position, it preflights the
   losslessly representable subset: simple Claude frontmatter (`name`, one-line `description`,
   comma-separated `tools`, `model`, plus the Markdown body) or the Codex fields emitted by this
   harness. Codex `developer_instructions` accepts both TOML multiline literal (`'''`) and basic
   (`"""`) strings. Mentioning the generated source path in ordinary prose does not claim ownership.
2. The filename must match the declared host `name`. A same-name Claude/Codex pair must have equal
   descriptions and instructions (an absent final newline is normalized). A parse failure, complex
   YAML/TOML, or any host field this harness cannot project back — such as Claude `memory` or Codex
   `mcp_servers` / `skills.config` — exits nonzero with the file/field named. Resolve, remove, or
   manually model that configuration in the SSOT before retrying; import never silently chooses a
   side or drops a field.
3. Only after **every** candidate and prospective projection passes preflight does import write
   `.agents/subagents/<name>/{metadata.json,instructions.md}` sources. It then projects every source
   back, so each adopted agent reappears as a generated file carrying the do-not-edit banner.

Adoption is idempotent (a name that already has a source is skipped) and **never destructive**: the
projection step that finds a sourceless, banner-less file **keeps** it and tells you to `--import`
it, rather than pruning it as an orphan. If Python is unavailable, the installer fails at preflight
before changing the target repository.
