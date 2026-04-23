---
name: conventional-commit-zh
description: Create one local git commit with a Chinese commit message that follows Conventional Commits. Use when the user asks to commit current changes, generate a Chinese commit message, or submit work with a conventional commit format such as "帮我提交", "生成中文 commit message", or "按 conventional commit 提交".
allowed-tools: Read, Bash, Grep, Glob
---

# Conventional Commit ZH

Create exactly one local git commit with this format:

```text
type(scope): 中文摘要
```

Examples:

- `feat(auth): 支持短信验证码登录`
- `fix(api): 修复用户详情接口空指针问题`
- `docs(readme): 补充本地开发说明`
- `refactor(parser): 简化配置解析流程`

## When To Use

Use this skill when the user wants the agent to:

- inspect the current git diff
- generate a Chinese conventional commit message
- stage the intended files
- create one local commit

Do not use this skill for:

- pushing branches
- creating pull requests
- cleaning branches or worktrees
- rewriting git history

## Required Checks

Before committing, inspect:

- `git status --short`
- `git diff --staged`
- `git diff`
- `git log --oneline -10`

If the user scoped the request to specific files, only stage those files.
If the request is simply to commit current work, staging the relevant current changes is acceptable.
Do not stage secrets, `.env` files, credentials, or obviously unrelated generated artifacts unless the user explicitly asked for them.
If there are no changes, stop and report that there is nothing to commit.

## Message Rules

The commit subject must follow Conventional Commits:

```text
<type>(<optional-scope>): <中文摘要>
```

Common types:

- `feat`
- `fix`
- `docs`
- `refactor`
- `test`
- `chore`
- `build`
- `ci`
- `perf`
- `style`

Guidelines:

1. Keep `type` in English.
2. Keep the summary in Chinese.
3. Make the summary specific and concise.
4. Use a lower-case scope only when it adds value.
5. Omit the scope when it does not help.
6. Use `!` only for real breaking changes.

## Workflow

1. Review the current git state and diff.
2. Infer the dominant change and choose the best `type`.
3. Draft one Chinese conventional commit subject.
4. Stage the intended files.
5. Run `git commit -m "<message>"`.
6. Verify with:
   - `git status --short`
   - `git log -1 --format=%s`

## If The User Supplies A Message

If the user already gave a commit idea, normalize it into valid Chinese Conventional Commits format instead of copying it verbatim when needed.
