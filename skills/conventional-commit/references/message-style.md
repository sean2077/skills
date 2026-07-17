# Conventional Commit Message Style

Read this when selecting the subject language, type, scope, breaking marker, or
normalizing a user-supplied message.

## Language priority

1. Follow an explicit user request.
2. Follow repository instructions already in context.
3. Follow relevant recent commit subjects.
4. Default to English when history is absent, mixed, sparse, or unclear.

When history is needed, prefer `git -C <repo-root> log --format=%s -20 -- <paths>` for
the intended area, then fall back to `git -C <repo-root> log --format=%s -20`. Analyze the text after the first
`: ` in Conventional Commits subjects and the whole subject otherwise. A supplied
full message or summary is an explicit language signal unless project policy overrides it.

## Subject shape

```text
<type>(<optional-scope>): <summary>
```

Use the dominant change, not every file touched:

| Type | Use for |
|---|---|
| `feat` | User-visible capability |
| `fix` | Correctness defect |
| `docs` | Documentation-only change |
| `refactor` | Structural change without intended behavior change |
| `test` | Test-only change |
| `perf` | Performance improvement |
| `build` / `ci` | Build or automation infrastructure |
| `style` | Formatting-only change |
| `chore` | Maintenance that fits no more specific type |

- Add a lowercase scope only when it improves routing.
- Make the summary concise and specific; use imperative wording in English.
- Add `!` only for a real breaking change.
- Put required detail, migration impact, issue references, and trailers after a blank
  line; keep the subject conventional.

Examples:

```text
feat(auth): support SMS verification login
fix(api): handle null user detail response
docs(readme): 补充本地开发说明
refactor(parser): 简化配置解析流程
```

If the user supplied a message, preserve its intent and language while normalizing
invalid type, scope, delimiter, or breaking notation.
