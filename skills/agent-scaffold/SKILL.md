---
name: agent-scaffold
description: "Use to initialize, inspect, or upgrade a Claude Code + Codex harness with .agents/ SSOT, real-symlink projections, hooks, subagents, authority docs, LF/CRLF policy, and selected project conventions. Adopt existing layouts. Not for ordinary commits, testing, docs, releases, or third-party skill installation."
---

# Agent Scaffold

Establish or incrementally maintain a project's Agent harness **and usable project guidance**.
The installer owns deterministic harness assets; the Agent adopts and fills project-specific
conventions. A successful installer run alone does not complete project onboarding.

```bash
bash <skill-dir>/agent-scaffold.sh <mode> [--profile default|light] [--domains all|none|list] [--json]
```

Run inside the authorized target checkout. The runtime requires git, Python 3.8+, Bash 3.2+,
and real file/directory symlinks. `.agents/` owns harness sources; `.claude/` and `.codex/`
contain host projections/configuration, and `CLAUDE.md` links to the lean `AGENTS.md`.

## Boundaries

- Discussion, preview, `plan`, `doctor`, and `verify` are read-only. A first invocation is
  not automatically permission to initialize; use the requested scope.
- Preserve project layout, language, build tools, CI, permissions, external-worktree ownership,
  and third-party entries. Directory names are clues, not authority or a migration request.
- Never hand-edit generated projections or resolve ownership conflicts by overwriting them.
  Reconcile only exact scaffold-owned hook identities.
- Newly authored project guidance belongs to the project, outside the managed AGENTS block.
  Do not expand that block with generic research, docs/tool governance, or task controllers.
- Keep repository EOL defaults in `.gitattributes`; preserve project exceptions and existing
  `.editorconfig`. Installation never renormalizes, stages, or rewrites unrelated user files.
- Existing guidance is an input, not untouchable: repair confirmed drift within scope without
  imposing a new layout, metadata schema, inventory, or approval process.

## Modes

| Mode | Installer responsibility |
|---|---|
| `apply` | Add/reconcile harness assets; refuse runtime drift requiring `upgrade` |
| `plan` | Preview asset create, merge, adopt, refresh, and attention states without writes |
| `doctor` | Check prerequisites and real-symlink capability |
| `verify` | Check active harness assets, managed drift, hooks, and projections |
| `upgrade` | Refresh current managed runtime and reconcile the contract |

`default` includes worktree/trunk-guard governance; `light` omits it. An omitted profile reuses
an identifiable installed choice; a fresh install uses `default`, and ambiguous legacy state
needs an explicit choice. JSON reports describe harness checks, not project-guidance acceptance.

## Workflow

1. Resolve the task checkout, revision, applicable authority chain, and existing lifecycle
   owner; do not infer them from session cwd or create a second worktree manager.
2. For full initialization or upgrade, follow [one-time selection](references/onboarding-selection.md).
   Offer all domains by default on first use or legacy migration; ask which to exclude once,
   reusing an explicit answer already given. Reuse a recorded selection on later runs without
   asking again. Read [project conventions](references/project-conventions.md) for selected domains.
   Inspect relevant entry points and actual configurations/callers before expanding the scan.
   Reuse existing answers; identify missing document, command, test-quality, verification,
   source, and safety guidance within the accepted selection. Use the relevant references below;
   selected testing does not impose TDD, nor does selected release authorize publication. This assessment also applies to previews, without writing or running setup commands.
3. Run `plan` for assets; combine its `apply_mode` and profile with the needed project-guidance
   changes. Resolve material scope/ownership conflicts. Follow existing authorization instead
   of demanding a new approval round for every routine, already authorized step.
4. For an authorized initialization/upgrade, run the indicated mutating mode. Then **write or
   reconcile the selected missing project guidance** in its existing homes, and link it from the Agent
   entry point. Respect an explicitly runtime-only request. Do not stop at suggestions or copy
   this skill's manual into the target; choose the minimum useful project-specific additions.
5. Verify harness assets with the same profile. Separately walk a new-Agent reader task using
   only the resulting entry points: find the applicable docs, real commands/cwd/effects,
   selected domain conventions, generated-source owners, verification limits, and
   delivery boundary. Check changed links and
   affected commands safely; preserve unavailable evidence as a gap rather than inventing it.
6. Report adopted locations, material additions/repairs, observed checks, and unresolved gaps.
   Distinguish asset installation, project-guidance coverage, and actual host trust/discovery.
   Equivalent existing coverage can require no project edits; repeated runs must not duplicate
   prose or resurrect deliberately merged/deleted guidance just to match an earlier template.

## On-demand references

| Need | Reference |
|---|---|
| Default-all first setup, legacy migration, one-time opt-outs, saved choices | [Onboarding selection](references/onboarding-selection.md) |
| First-use project guidance, layout adoption, docs/tools, and incremental maintenance | [Project conventions](references/project-conventions.md) |
| Specification status, semantic preservation and acceptance | [Specification conventions](references/specification-conventions.md) |
| Commit scope, delivery, version/notes authorities and release completion | [Delivery conventions](references/delivery-conventions.md) |
| Project test design, dependency boundaries, existing gates, and TDD policy | [Testing conventions](references/testing-conventions.md) |
| Session entry, task paths, external worktrees, and lifecycle handoff | [Workspace context](references/workspace-context.md) |
| EOL defaults, exceptions, and authorized migration | [Line endings](references/line-endings.md) |
| Installed assets, profiles, SSOT, and third-party coexistence | [Harness layout](references/harness-layout.md) |
| Hook ownership and host trust | [Host integration](references/host-integration.md) |
| Project-owned format-on-edit integration | [Format hooks](references/format-hooks.md) |
| Lean root/nested authority documents | [Authority documents](references/authority-docs.md) |
| Existing glossaries, language equivalents, and terminology ownership | [Terminology](references/terminology.md) |
| Subagent authoring/projection and existing-agent import | [Subagents](references/subagents.md) · [Import](references/subagent-import.md) |
| Adopting existing authority documents or host agents | [Retrofit](references/retrofit.md) |
| Platforms, symlink repair, and checkpoint limitations | [Platform support](references/platform-support.md) |
| Structured reports and troubleshooting | [Diagnostics](references/diagnostics.md) |

See [NOTICE.md](NOTICE.md) for attribution of adapted testing and terminology guidance.
