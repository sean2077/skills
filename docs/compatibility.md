# Compatibility and verification matrix

## Evidence baselines

Track each interface independently. A new repository commit does not invalidate every host observation, and a recent documentation edit is not a new runtime certification.

| Surface | Pinned or reviewed basis | Evidence and unverified boundary |
|---|---|---|
| Installer | CI uses `skills@1.5.17`; original review 2026-08-25 | Real discovery, install, regular-file inventory and byte comparison in [validation CI](../.github/workflows/validate.yml). This is a reproducibility pin, not a claim to be latest. |
| Claude / Codex scaffold | Project layouts; documentation review 2026-08-25, subagent-definition review 2026-09-22, overlap notes 2026-09-20 | [Core tests](../scripts/tests/test_agent_scaffold_core.py), [workspace tests](../scripts/tests/test_workspace_entry.py) and installer E2E cover source/projection ownership and hook payloads. Real authenticated discovery, trust and hook execution are separate observations. |
| Grok-compatible payloads | Explicit compatibility branches in the shared hook parser | Simulated payload/expansion tests only. No independent Grok installation or live-host certification is inferred from Claude compatibility. |
| Lark CLI | Command recipes reviewed against v1.0.93 on 2026-09-04 | Domain references and [mock outcome case](../evals/tasks/README.md) are not live service/API certification. Preserve recipe-specific evidence when updating CLI syntax. |
| Task evaluation capture | Claude CLI/stream documentation reviewed 2026-09-22 | Importer and negative-fixture tests; actual host runs require a configured CLI and retained results. Unknown usage stays unknown. |

For a new observation, retain the host/tool version, platform, relevant configuration, exact operation, source revision, command/result, and the claim it supports in the existing test result or review record. Recheck the affected interface when it changes; do not impose a universal recurring approval process. A static configuration file, simulated payload, actual host invocation, and task outcome are different levels of evidence.

The initial installer review used repository revision `8fa013752416a7aa082d023489e8141a0764f8b6` and observed upstream `v1.5.23`. Those are historical facts, not current-main or latest-release labels. Upgrading the tested pin is a separate change with discovery/install/payload checks.

## Support layers

| Layer | Repository evidence | Bounded claim | Does not prove |
|---|---|---|---|
| Agent Skills format | `requirements-validation.txt`, `scripts/validate_skills.py`, `scripts/catalog_health.py`, and the pinned official `skills-ref` validation in `.github/workflows/validate.yml` | Published skill payloads are checked for repository rules and the pinned Agent Skills specification. | Identical discovery, optional-field support, or executable-language support in every client. |
| Installer discovery | CI runs `skills@1.5.17` against the catalog root, compares the discovered names, installs the catalog, rejects special entries, and byte-diffs installed payloads. | The audited CLI pin discovers and copies this catalog as tested by the workflow. | Runtime support for every target listed by any installer version. |
| Host wiring | `agent-scaffold` static, core, and throwaway-repository E2E checks cover `.agents/`, Claude Code symlink projections, Codex project paths, hooks, and generated subagents. | The repository can create and verify its project-owned Claude Code + Codex harness shape. | User trust, hook approval, organization policy, cloud variants, or untested hosts. |
| Harness behavior | Runtime generators, P0 behavior/hardening tests, skill-eval contracts, and coordination primitive tests exercise owned state and safety boundaries. | The checked repository behavior is bounded by those executable tests. | Universal task effectiveness or host behavior outside the tested permissions and fixtures. |

The public catalog is exactly the set of skills published under `skills/`. `.agents/skills/skill-eval` is project-private: its `metadata.internal: true` marker, manifest exclusion, README exclusion, and normal discovery exclusion keep it outside public catalog claims unless internal skills are explicitly enabled.

## Native overlap and visibility (2026-09-20)

This is a documentation review, not certification of locally authenticated host runs. It does
not update the older installer pin, hook tests, or Lark command-version evidence above/below.

| Current documented native capability | Catalog decision |
|---|---|
| Codex discovers skill names/descriptions before loading selected instructions; discovery has a context budget | Shorten and front-load routing descriptions; install only routes needed. Do not turn every skill into an always-loaded prompt. |
| Native planning, continuation/resume, and subagents can own ordinary delivery | Use the host/project workflow for ordinary delivery. Keep formal runtimes only for the required repository-owned semantics. |
| Claude Code bundles review, debugging, looping, and app run/verify skills | Do not repeat an adequate native workflow just to run a catalog route. Native app verification is useful evidence but does not replace unrelated project-required tests. |
| A local Claude `code-review` shadows bundled `/code-review`, not the bundled `/review` alias | This catalog no longer publishes `code-review`; inspect and remove any old installation from this catalog to undo its local override. Preserve unrelated same-name skills. |
| Claude exposes `/skills` visibility controls and `/skill-doctor` usage/cost inspection | Prefer host-local visibility choices over editing shared SKILL frontmatter or adding a custom always-on routing layer. |

Check the installed host's actual command/menu availability and organization policy before
using a host-specific control. Plugin namespace behavior is separate from this repository's
installer grouping manifest; these notes do not claim the catalog is a native plugin bundle.
No host's native tool availability expands user authorization, bypasses worktree ownership,
or proves that a remote deliverable exists.

Sources checked 2026-09-20: [OpenAI skills](https://learn.chatgpt.com/docs/build-skills),
[OpenAI prompt/skill adaptation](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra),
[Claude skills and visibility](https://code.claude.com/docs/en/skills), and
[Claude best practices](https://code.claude.com/docs/en/best-practices).

## Project subagent definitions (2026-09-22)

This is a documentation review of the two host formats, not certification of a locally authenticated host run. Claude Code project subagents are Markdown files in `.claude/agents/<name>.md` with required `name` and `description`; optional `tools` is a comma-separated list, and omitting it inherits every subagent tool. Codex project subagents are one TOML file per `.codex/agents/<name>.toml` with required `name`, `description`, and `developer_instructions`, where `sandbox_mode` narrows that agent's permission level. Both hosts load these only from a trusted project layer, and Codex reapplies the parent turn's live sandbox and approval overrides when it spawns a child, so a configured `read-only` value is not evidence of the effective sandbox. This repository's `.agents/subagents/skill-verifier/` source and its two projections are covered by the [private-harness contract test](../scripts/tests/test_private_skill_eval_contract.py) and the generator `--check`; discovery, real permissions, and inherited context remain unverified.

Sources checked 2026-09-22: [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) and [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

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
npx skills add sean2077/skills --skill tdd -a claude-code -a codex

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

Reverify this page when a host path, trust model, hook schema, installer flag, compatibility claim, audited pin, or public/private catalog boundary changes. Prefer dated, bounded language over “universal,” “all hosts,” or unqualified “latest.” Follow the [documentation maintenance](documentation-maintenance.md) policy for source selection and duplication rules.
