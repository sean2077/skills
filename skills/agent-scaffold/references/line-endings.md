# Repository line endings

Read this when adopting or diagnosing LF/CRLF policy, aligning editor settings, or migrating
existing files. Both scaffold profiles install the same EOL policy; worktree governance is
an independent choice.

## Ownership and precedence

`apply` / `upgrade` prepend a managed defaults block in the root `.gitattributes`:

```gitattributes
* text=auto eol=lf
*.[bB][aA][tT] text eol=crlf
*.[cC][mM][dD] text eol=crlf
```

New auto-detected text uses LF in Git and in the working tree. Batch/command files use CRLF
in the working tree but still normalize to LF in Git. Auto-detected binaries are not converted.
Existing project rules remain byte-preserved after the block and take precedence per attribute;
nested attributes also take precedence. Keep LFS rules, filters, encodings, and intentional
exceptions project-owned. For example:

```gitattributes
# Project-owned exceptions below the managed block.
legacy/*.txt text eol=crlf
fixtures/wire-response.fixture -text
*.png -text
```

Use `-text` for exact-byte fixtures or binaries; merely setting `eol=crlf` still normalizes
text in Git. Do not force `text` on unknown encodings or binary data. The existing scaffold
runtime pins stay in place; `verify` checks their effective attributes, including overrides
from nested files or `.git/info/attributes`, rather than relying on line presence alone.

A missing `.editorconfig` is seeded with LF defaults and matching batch-file exceptions.
The seed sets only `end_of_line`, without cutting off inherited non-EOL preferences.
It then belongs to the project: existing indentation, charset, rules, and comments are never
rewritten, even by `upgrade`. Align its `end_of_line` rules with Git exceptions yourself;
editor support varies, and this file is not a substitute for Git attributes. The installer
neither parses existing EditorConfig semantics nor changes local/global `core.autocrlf`,
`core.eol`, editor preferences, formatters, hooks, or CI.

## Existing-file migration is separate

Installing attributes does not rewrite existing worktree or index content. Git's `text=auto`
can also preserve CRLF content already stored in Git until explicitly renormalized.
The scaffold never runs `git add --renormalize`, checkout, restore, reset, or a whole-tree
converter. Preserve staged work and unrelated changes.

From the repository root of the target checkout, inspect:

```bash
git status --short
git ls-files --eol
git check-attr text eol -- path/to/file
bash <skill-dir>/agent-scaffold.sh verify --profile default --json
```

Use the same `--profile` that installed the harness (`default` or `light`). A
mismatched profile can fail unrelated worktree-policy checks.

`line-endings.tracked` reports mismatching **tracked** text using Git's effective rules:
CRLF/mixed normalized index content or mismatching worktree endings. Empty/no-newline files,
binaries, `-text` fixtures, and explicit CRLF checkout rules are not blanket LF violations.
Untracked files and existing EditorConfig semantics are outside that check. A tracked file
can have a clean `git diff` after conversion yet still have incorrect worktree bytes.

For an approved migration, first settle exceptions and use a dedicated clean task worktree
with no unrelated staged/unstaged work. Prefer reviewed explicit paths. A whole-tree operation
is justified only when the entire migration is authorized:

```bash
# From that same repository root, only after the checks above.
git add --renormalize -- .
git diff --cached --stat
git diff --cached --check
```

Inspect the staged diff and run affected tests before committing. Renormalization stages
tracked content; it does not rewrite existing working files. After the migration is committed
and the policy is tracked, a fresh checkout avoids destructive refresh of a dirty worktree.
For selected existing files, let the project editor/formatter convert them only after confirming
encoding, scope, and absence of unrelated edits. Never reset/clean to make verification green.

## Evidence

Git's [attributes specification](https://git-scm.com/docs/gitattributes) defines precedence,
`text=auto`, `-text`, and index versus checkout normalization;
[`ls-files --eol`](https://git-scm.com/docs/git-ls-files) exposes both byte states.
[EditorConfig](https://editorconfig.org/) defines `end_of_line` and filename patterns.
Checked 2026-09-20; the repository's real-Git tests exercise these behaviors rather than
inferring them from a contributor's operating system.
