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

- If the user named files, normalize them without changing their meaning, then stage only
  those repository-relative paths with `git -C <repo-root> add -- <paths>`.
- If the user asked to commit all current work, inspect status first; use
  `git -C <repo-root> add -A -- .`
  only after confirming that every visible change belongs to the request.
- If unrelated paths are already staged, stop and report them instead of silently
  including, unstaging, or working around them.
- After staging, check `git diff --cached --name-only` and `git diff --cached --check`.
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
