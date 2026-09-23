# Compatibility and verification matrix

## Evidence baselines

Track each interface independently. A repository change does not invalidate every host observation, and an editorial update is not a new runtime certification. The dates below are the original evidence/review dates, not the last edit date of this page. A static configuration file, a simulated payload, an actual host invocation, and a task outcome are different levels of evidence.

| Surface | Basis | Evidence and limit |
|---|---|---|
| Installer | CI pin `skills@1.5.17`; initial review 2026-08-25 | [CI](../.github/workflows/validate.yml) checks real discovery, installation, regular-file inventory, and byte fidelity. The pin is not a latest-version claim. |
| Claude / Codex scaffold | Layout review 2026-08-25; overlap review 2026-09-20; subagent review 2026-09-22 | Core/workspace/E2E tests cover source/projection ownership and simulated hook payloads. Authenticated discovery, trust, and effective permissions need actual host observations. |
| Grok-compatible payloads | Explicit branches in the shared hook parser | Simulated payload/expansion tests, not independent Grok installation or live-host certification. |
| Lark CLI | Recipes reviewed against v1.0.93 on 2026-09-04 | Domain references and mock task cases are not live CLI/service certification. Preserve recipe-specific evidence when changing syntax. |
| Task capture | Claude CLI/stream documentation reviewed 2026-09-22 | Importer/negative-fixture tests; actual host runs require a configured CLI and retained results. Unknown usage stays unknown. |

For a new observation retain version, platform, relevant configuration, operation, source revision, command/result, and the supported claim in its existing result or review record. Recheck the changed interface, not every interface on a recurring schedule.

The initial installer review used revision `8fa013752416a7aa082d023489e8141a0764f8b6` and observed upstream `v1.5.23`. These are historical facts, not current-main or latest-release labels. An installer upgrade needs its own discovery/install/payload evidence.

## Support layers

| Layer | Repository evidence | Does not establish |
|---|---|---|
| Agent Skills format | Catalog validators and pinned official `skills-ref` | Identical discovery, optional fields, or executable-language support across clients |
| Installer discovery/copying | Pinned catalog-root discovery and byte-compared install smoke tests | Runtime support for every installer target |
| Host wiring | Scaffold core/workspace/static/E2E checks | Trust, hook approval, organization policy, cloud variants, or effective live-host permissions |
| Owned runtime behavior | Workflow/P0/hardening, protocol, and adapter/oracle tests | Universal task effectiveness, model compliance, or token savings |

The catalog is the set under `skills/`. Project `skill-eval` under `.agents/skills/` is excluded by its internal metadata, manifest/README boundary, and normal discovery filtering; explicitly enabling internal discovery is a different operation. The [architecture](architecture.md) owns source and generated-file details. Routing probes and task outcomes have separate [measurement guides](../evals/agent-skills/README.md).

## Native overlap and visibility (2026-09-20)

This dated documentation review does not certify authenticated runs or refresh the installer, hook, or Lark evidence.

| Documented capability at review | Catalog decision |
|---|---|
| Codex discovers names/descriptions before selected instructions, with a discovery-context budget | Keep routing descriptions focused and install needed routes rather than loading every workflow. |
| Native planning, continuation, and subagents support ordinary delivery | Use the host/project workflow; keep formal runtimes for their required owned semantics. |
| Claude Code bundles review, debugging, looping, and app run/verify skills | Do not repeat adequate native work; app verification does not replace unrelated project tests. |
| A local Claude `code-review` shadows bundled `/code-review`, not `/review` | The catalog no longer ships it; remove only obsolete copies from this catalog, not unrelated same-name skills. |
| Claude exposes `/skills` visibility and `/skill-doctor` usage/cost controls | Prefer available host-local controls over shared-frontmatter edits or a custom always-on router. |

Check the installed host's actual menus and organization policy. Plugin namespaces are separate from this catalog's installer grouping metadata. Native tools do not expand user authorization, bypass worktree ownership, or prove a remote deliverable exists.

Sources reviewed 2026-09-20: [OpenAI skills](https://learn.chatgpt.com/docs/build-skills), [OpenAI prompt/skill adaptation](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra), [Claude skills](https://code.claude.com/docs/en/skills), and [Claude best practices](https://code.claude.com/docs/en/best-practices).

## Project subagent definitions (2026-09-22)

The documentation review recorded Claude project definitions at `.claude/agents/<name>.md` with `name`, `description`, and an optional comma-separated `tools` allowlist; omitting `tools` inherits all subagent tools. Codex project definitions are `.codex/agents/<name>.toml` with `name`, `description`, and `developer_instructions`; `sandbox_mode` requests an agent permission level. Both use trusted project layers. Codex parent-turn overrides can affect the effective child sandbox, so configured `read-only` is not enforcement evidence.

The project `skill-verifier` declares Claude Read/Grep/Glob and Codex `read-only`, and instructs both not to execute commands. [Private-harness tests](../scripts/tests/test_private_skill_eval_contract.py) and generator parity check the definitions, not host reload, inherited context, or actual permissions. No authenticated run certifies this revision's effective boundaries. See [invocation and execution ownership](development.md#optional-skill-verifier); the parent runs checks in an authorized environment, and a worktree/clone is not a process sandbox.

Sources reviewed 2026-09-22: [Claude subagents](https://code.claude.com/docs/en/sub-agents) and [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Codex facts

Documentation reviewed 2026-08-25 recorded these contracts:

- Codex scans `.agents/skills` from the working directory through the repository root and follows symlinked skill directories.
- Native plugins use `.codex-plugin/plugin.json`; this is not the catalog's `.claude-plugin/plugin.json` installer grouping format.
- Project configuration, hooks, and rules require a trusted project layer. Scaffold command hooks are non-managed hooks: trust and hook-definition approval are independent. Approval is recorded against the exact definition hash, so an unreviewed or changed hook stays skipped until it is reviewed again in `/hooks`.

Sources: [skills](https://developers.openai.com/codex/build-skills), [plugins](https://developers.openai.com/codex/build-plugins), [hooks](https://developers.openai.com/codex/hooks), and [configuration](https://developers.openai.com/codex/config-reference).

## Claude Code facts

Documentation reviewed 2026-08-25 recorded these contracts:

- Project skills use `.claude/skills/<name>/SKILL.md`; symlinked directories are followed.
- Managed settings, command-line overrides, and project-local settings take precedence over shared project settings. Trust-gated keys such as `permissions.allow`, `permissions.additionalDirectories`, `extraKnownMarketplaces`, and most `env` values require folder trust; `deny` and `ask` rules apply immediately.
- Checkpoints do not rewind symlinked or hard-linked targets. After `/rewind`, inspect actual `AGENTS.md` and project skill sources reached through projections; restore with Git or an explicit reverse edit when needed.

Sources: [skills](https://code.claude.com/docs/en/skills), [settings](https://code.claude.com/docs/en/settings), and [checkpointing](https://code.claude.com/docs/en/checkpointing).

## Installer semantics

The source supplies the catalog; the command's working directory determines the project installation destination. Keep the **catalog checkout** and **consumer project** distinct.

```bash
# Discovery only, from the catalog checkout; no consumer installation
NO_COLOR=1 DISABLE_TELEMETRY=1 npx --yes skills@1.5.17 add . -l

# Installation from a separate consumer project
# Replace both absolute paths before running.
(
  cd /absolute/path/to/consumer || exit 1
  npx --yes skills@1.5.17 add /absolute/path/to/skills --skill agent-scaffold -a codex
)
```

The [README](../README.md#install) owns remote-source examples. Keep the catalog root as the local source to use `.claude-plugin/plugin.json` grouping. A direct skill-directory source bypasses that metadata: use an explicit `./` or `../` prefix for relative paths (for example `./skills/agent-scaffold`), or an absolute path, rather than `skills/agent-scaffold`. Do not install into this repository merely because it holds the source.

Repeat `--skill` and `-a` to select skills and targets. Omitting `--skill` opens selection in the audited flow. Quote `'*'`; `--all` is broader, selecting all discovered skills and all supported agents without prompts. `npx --yes` approves obtaining the CLI; it is distinct from the CLI's own selection/confirmation options.

Inspect options with `npx --yes skills@1.5.17 --help`. With this pin, `add <source> --help` may execute the add flow. Choose global scope explicitly using the CLI's documented option and inspect intended targets; changing source paths does not select global scope. Remove retired installations only from the consumer project or intended global scope, preserving unrelated entries and local modifications. **Project-scope removal from the catalog root can delete `skills/*` product files.** See [retired-installation guidance](skill-composition.md#installation-and-evidence).

Installer target lists are discovery metadata, not certification. Upgrading the pin is an explicit dependency change with discovery, installation, payload, and platform checks. Official installer reference: [vercel-labs/skills](https://github.com/vercel-labs/skills).

## Maintenance trigger

Reverify the affected claim when host paths, trust, hook schemas, installer semantics, pins, or catalog boundaries change. Preserve older evidence dates unless the underlying observation was actually repeated. Follow [documentation maintenance](documentation-maintenance.md); prefer bounded claims to “universal,” “all hosts,” or unqualified “latest.”
