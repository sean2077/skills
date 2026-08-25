# Compatibility and verification matrix

Review baseline:

- Repository: local `main` at `8fa013752416a7aa082d023489e8141a0764f8b6`
- Repository and official documentation reviewed: **2026-08-25**
- CI-audited installer pin: `skills@1.5.17`
- Upstream release observed on the review date: [`v1.5.23`](https://github.com/vercel-labs/skills/releases/tag/v1.5.23)

“Compatible” is not one binary property. Carry a claim forward only when the named evidence still applies to the current commit.

## Support layers

| Layer | Repository evidence | Bounded claim | Does not prove |
|---|---|---|---|
| Agent Skills format | `requirements-validation.txt`, `scripts/validate_skills.py`, `scripts/catalog_health.py`, and the pinned official `skills-ref` validation in `.github/workflows/validate.yml` | Published skill payloads are checked for repository rules and the pinned Agent Skills specification. | Identical discovery, optional-field support, or executable-language support in every client. |
| Installer discovery | CI runs `skills@1.5.17` against the catalog root, compares the discovered names, installs the catalog, rejects special entries, and byte-diffs installed payloads. | The audited CLI pin discovers and copies this catalog as tested by the workflow. | Runtime support for every target listed by any installer version. |
| Host wiring | `agent-scaffold` static, core, and throwaway-repository E2E checks cover `.agents/`, Claude Code symlink projections, Codex project paths, hooks, and generated subagents. | The repository can create and verify its project-owned Claude Code + Codex harness shape. | User trust, hook approval, organization policy, cloud variants, or untested hosts. |
| Harness behavior | Runtime generators, P0 behavior/hardening tests, skill-eval contracts, and work-protocol risk checks exercise owned state and safety boundaries. | The checked repository behavior is bounded by those executable tests. | Universal task effectiveness or host behavior outside the tested permissions and fixtures. |

The public catalog contains 16 skills. `.agents/skills/skill-eval` is project-private: its `metadata.internal: true` marker, manifest exclusion, README exclusion, and normal discovery exclusion keep it outside public catalog claims unless internal skills are explicitly enabled.

## Codex facts

Official Codex documentation reviewed on 2026-08-25 establishes that:

- Codex scans `.agents/skills` from the working directory through the repository root and follows symlinked skill directories.
- Native Codex plugins use `.codex-plugin/plugin.json` and may bundle skills, an MCP server, or both. This is a separate distribution boundary from this repository's installer-oriented `.claude-plugin/plugin.json` grouping manifest.
- Project `.codex/` configuration, hooks, and rules load only from a trusted project layer.
- Scaffold command hooks are non-managed hooks. Project trust and hook-definition review are independent gates; Codex records approval against the exact definition hash and skips an unreviewed or changed hook until it is reviewed again in `/hooks`.

References: [skills](https://developers.openai.com/codex/build-skills), [plugins](https://developers.openai.com/codex/build-plugins), [hooks](https://developers.openai.com/codex/hooks), and [configuration](https://developers.openai.com/codex/config-reference).

## Claude Code facts

Official Claude Code documentation reviewed on 2026-08-25 establishes that:

- Project skills live in `.claude/skills/<name>/SKILL.md`; Claude Code follows a symlinked skill directory to its target.
- Shared project settings sit below managed settings, command-line overrides, and project-local settings in the documented precedence. Trust-gated keys such as `permissions.allow`, `permissions.additionalDirectories`, `extraKnownMarketplaces`, and most `env` values apply only after folder trust; `deny` and `ask` rules apply immediately.
- Checkpoint restore does not rewind symlinked or hard-linked files. A successful `/rewind` can therefore leave changes in real targets reached through `CLAUDE.md` or `.claude/skills/*`; inspect and restore the target with Git or an explicit reverse edit.

References: [skills](https://code.claude.com/docs/en/skills), [settings](https://code.claude.com/docs/en/settings), and [checkpointing](https://code.claude.com/docs/en/checkpointing).

## Installer semantics

The upstream `skills` CLI target list is discovery metadata, not this repository's certification matrix.

```bash
# Selected skills to selected targets; repeat --skill and -a as needed
npx skills add sean2077/skills --skill analyze -a claude-code -a codex

# Every catalog skill to only these two targets
npx skills add sean2077/skills --skill '*' -a claude-code -a codex

# Use root catalog metadata from a local checkout
npx skills add . --skill agent-scaffold -a codex

# Direct directory install; the explicit ./ prevents repository-name parsing
npx skills add ./skills/agent-scaffold -a codex
```

- Omitting `--skill` opens selection in the audited CLI flow.
- Quote `'*'` so the shell does not expand it. `--all` is broader: all discovered skills to all supported agents without prompts.
- Root installation uses `.claude-plugin/plugin.json` as installer catalog-grouping metadata. It is not a native Codex `.codex-plugin/plugin.json` package manifest; direct skill-directory installation bypasses root metadata.
- With the current audited pin, inspect global options with `npx skills --help`; `npx skills add <source> --help` may execute the add flow.
- A reproducibility pin and the current upstream release answer different questions. Upgrade the pin only as an explicit dependency change with discovery, install, payload, and platform smoke tests.

Official installer reference: [vercel-labs/skills](https://github.com/vercel-labs/skills).

## Maintenance trigger

Reverify this page when a host path, trust model, hook schema, installer flag, compatibility claim, audited pin, or public/private catalog boundary changes. Prefer dated, bounded language over “universal,” “all hosts,” or unqualified “latest.” Follow the [documentation maintenance policy](documentation-maintenance.md) for source selection and duplication rules.
