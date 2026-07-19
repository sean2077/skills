# Commit Staging Safety

Read this when Git inspection or staging is required before creating the local commit.

## Inspect only what is missing

Do not rerun discovery when the conversation already provides reliable paths, diffs,
test results, or recent subjects. When evidence is missing or stale, use the lightest
useful commands:

```bash
git -C <repo-root> status --short
git -C <repo-root> diff --staged
git -C <repo-root> diff
git -C <repo-root> log --format=%s -20
```

## Protect scope and index state

- A named path does not authorize every hunk inside it. When the current context does not
  establish whole-file ownership, inspect both the existing staged and unstaged changes first:

  ```bash
  git -C <repo-root> diff --cached -- <paths>
  git -C <repo-root> diff -- <paths>
  ```

- If a path mixes intended and unrelated hunks, do not stage the whole path. Use a hunk-level
  selection only when the exact authorized patch can be selected and verified without modifying
  the working tree or unrelated pre-existing index state; otherwise stop and name the mixed path.
- If the user named files and every hunk is authorized, normalize them without changing their
  meaning, then stage only those repository-relative paths with
  `git -C <repo-root> add -- <paths>`.
- If the user asked to commit all current work, inspect status first; use
  `git -C <repo-root> add -A -- .`
  only after confirming that every visible change belongs to the request.
- If unrelated paths are already staged, stop and report them instead of silently
  including, unstaging, or working around them.
- After staging, check `git diff --cached --name-only`, inspect the actual cached patch with
  `git diff --cached -- <paths>`, and run `git diff --cached --check`.
- Do not stage credentials, `.env` files, secrets, or unrelated generated output unless
  explicitly authorized.
- If the intended paths contain no committable change, stop with a concise result.

The mandatory attached-HEAD preflight is:

```bash
git -C <repo-root> symbolic-ref --quiet --short HEAD
```

Exit status 1 means HEAD is detached. Any other nonzero status is a Git error. Neither
case permits staging.

## Commit and verify

Use `git commit -m <subject>` only when quoting is simple. For bodies, trailers, or
untrusted shell-sensitive text, pass the message through a file or stdin rather than
interpolating it into a shell command.

After committing, verify:

```bash
git -C <repo-root> status --short
git -C <repo-root> log -1 --format=%H%n%s
```

Report the short hash and actual recorded subject. If post-commit verification fails,
the commit may still exist; report both facts without attempting history rewriting.
