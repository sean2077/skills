---
name: conventional-commit-zh
description: Create one local git commit with a Chinese Conventional Commits subject, or generate only the subject when the user explicitly asks for a commit message without committing. Use for requests such as "帮我提交", "生成中文 commit message", or "按 conventional commit 提交".
allowed-tools: Read, Bash, Grep, Glob
---

# Conventional Commit ZH

Create a Chinese Conventional Commits subject:

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

- generate a Chinese conventional commit message
- stage the intended files
- create one local commit

Do not use this skill for:

- pushing branches
- creating pull requests
- cleaning branches or worktrees
- rewriting git history

## Modes

- **Commit mode**: default when the user asks to commit, submit, save the work, or otherwise create a local commit. Create exactly one local commit.
- **Message-only mode**: use when the user explicitly asks only to generate, draft, or suggest a commit message. Do not stage files or run `git commit`.

## Output Discipline

This skill should behave like a terse commit command, not like a planning or review assistant.

In commit mode:

- Do not announce that you are using this skill.
- Do not describe a plan before running git commands.
- Do not print diff summaries, file-by-file explanations, rationale, checklists, or command transcripts.
- Do not explain how you chose the commit type, scope, or wording unless the user explicitly asks.
- Use tool calls to inspect/stage/commit/verify, then return only the result.

Successful commit output should be one short line:

```text
已提交: <short-hash> <subject>
```

Blocked output should be one short sentence that states the blocker, for example:

```text
没有可提交的改动。
```

If verification fails after the commit, report the commit result plus the failed verification in the smallest useful form. Do not paste full command output unless it is needed to diagnose the failure.

In message-only mode, output exactly one commit subject as plain text. Do not wrap it in backticks, bullets, Markdown, or explanatory prose unless the user explicitly asks for rationale.

## Context-First Rule

Use the conversation context first. If the current context already contains a reliable description of the intended changes, affected files, diff snippets, test results, or prior command output, do not run `git status`, `git diff`, or `git log` just to rediscover what changed.

Only inspect git state when the available context is missing, stale, ambiguous, or insufficient to choose the intended files and commit message. When inspection is needed, use the lightest useful command, for example:

- `git status --short`
- `git diff --staged`
- `git diff`
- `git log --oneline -10`

Verification commands after staging or committing are still allowed; do not confuse result verification with rediscovering the change.

## Staging Rules

If the user scoped the request to specific files, only stage those files.
If the relevant files are clear from context, stage those exact files directly with `git add -- <paths>` instead of doing repo-wide discovery first.
If the request is simply to commit current work and context does not identify the intended files, inspect the git state before staging.
Avoid `git add .` unless the user explicitly wants all current changes and git state inspection shows there are no unrelated files.
When skipping discovery, still prevent unrelated staged changes from being committed: either commit with an explicit pathspec for the intended files or run a lightweight staged path check such as `git diff --cached --name-only` after staging.
Do not stage secrets, `.env` files, credentials, or obviously unrelated generated artifacts unless the user explicitly asked for them.
If there are no changes or `git commit` reports nothing to commit, stop and report that there is nothing to commit.

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
7. If repository or user instructions require a commit body or trailers, keep the subject in this format and put the extra content after a blank line.

## Workflow

1. Read the current context for the intended change summary, file scope, and verification evidence.
2. Decide whether this is commit mode or message-only mode.
3. Infer the dominant change and choose the best `type`.
4. Draft one Chinese conventional commit subject.
5. In message-only mode, output only the subject unless the user asked for rationale, then stop.
6. In commit mode, stage the intended files.
7. Run `git commit` with the subject. Prefer a safe message path such as `git commit -F -` when a body/trailers are needed or shell quoting would be fragile. Do not inject untrusted or complex commit text directly into a shell command.
8. Verify with:
   - `git status --short`
   - `git log -1 --format=%s`
9. Return only the concise result required by **Output Discipline**.

## If The User Supplies A Message

If the user already gave a commit idea, normalize it into valid Chinese Conventional Commits format instead of copying it verbatim when needed.
