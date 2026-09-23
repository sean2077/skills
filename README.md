# skills

A curated catalog of reusable [Agent Skills](https://agentskills.io/specification) for Agent harness setup, requirements interviews, and Feishu/Lark operations.

Install only what adds value to your host or project. Ordinary investigation, testing, cleanup, review, and delivery use the host/project workflow; there is no mandatory skill chain. See the [selection guide](docs/skill-composition.md) for route boundaries and retired installations.

## Install

Run from the **consumer project**, not this catalog checkout. These examples use the audited installer pin, not a claim about the latest version.

```bash
# One skill for Claude Code and Codex
npx --yes skills@1.5.17 add sean2077/skills --skill agent-scaffold -a claude-code -a codex

# Complete catalog for just these two targets
npx --yes skills@1.5.17 add sean2077/skills --skill '*' -a claude-code -a codex

# Local catalog source; replace the absolute path
npx --yes skills@1.5.17 add /absolute/path/to/skills --skill agent-scaffold -a codex
```

Repeat `--skill` and `-a` for selective installs; quote `'*'`. Relative local sources need `./` or `../`. [Installer semantics](docs/compatibility.md#installer-semantics) covers discovery-only checks, global scope, and safe removal. **Project-scope removal from this catalog checkout can delete product files.**

Installing `agent-scaffold` makes the skill available; it does not initialize the consumer's harness. Its [entry point](skills/agent-scaffold/SKILL.md) starts with a read-only plan. Full setup adopts existing project guidance and records one-time convention exclusions; see [onboarding selection](skills/agent-scaffold/references/onboarding-selection.md). Host trust and hook approval remain separate from installation.

## Catalog

Each skill is independently installable. Its entry point owns the workflow and on-demand references.

| Skill | Use |
|---|---|
| [agent-scaffold](skills/agent-scaffold/) | Initialize or maintain the harness and selected project conventions; preserve existing layouts and remember one-time exclusions. |
| [deep-interview](skills/deep-interview/) | Resolve requirements into an approved specification; exact-file approval records are optional. |
| [lark-cli](skills/lark-cli/) | Perform selected 飞书/Feishu/Lark CLI operations with identity and side-effect safeguards. |

Project skill `skill-eval` and subagent `skill-verifier` support this repository's evaluations. Neither is a catalog install target.

## Documentation

| Need | Start here |
|---|---|
| Choose routes or remove retired installations | [Selection and composition](docs/skill-composition.md) |
| Find the source to edit | [Architecture and ownership](docs/architecture.md) |
| Contribute, verify, regenerate, or release | [Development](docs/development.md) |
| Check installer behavior, host trust, and dated evidence | [Compatibility](docs/compatibility.md) |
| Maintain docs or design a skill | [Documentation maintenance](docs/documentation-maintenance.md) · [Harness principles](docs/harness-constraint-policy.md) |
| Evaluate decisions or actual task outcomes | [Routing probes](evals/agent-skills/README.md) · [Task outcomes](evals/tasks/README.md) |
| Work as a repository Agent | [AGENTS.md](AGENTS.md) · [Terminology](CONTEXT.md) |
| Review changes and past decisions | [CHANGELOG.md](CHANGELOG.md) · [Historical records](docs/documentation-maintenance.md#historical-records) |

## License

MIT. Preserve skill-specific attribution notices when redistributing payloads.
