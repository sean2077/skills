# Repository architecture

This page is the canonical map of product surfaces, source ownership, generated projections, and validation responsibility. Update it in the same change as any durable ownership or generation boundary.

## Product surfaces

| Surface | Canonical source | Consumer | Boundary |
|---|---|---|---|
| Published skill catalog | `skills/<name>/` | `npx skills` and other Agent Skills clients | Every skill must remain independently installable; public payloads contain only regular files and directories. |
| Catalog metadata | `.claude-plugin/plugin.json` plus README rows | The repository's tested discovery flow and human readers | This installer grouping manifest is neither universal host certification nor a native Codex `.codex-plugin/plugin.json` package. |
| Project-private harness | `.agents/` | Trusted Claude Code and Codex project layers in this repository | It is not part of the public catalog; `.claude/` and `.codex/` are projections or host configuration. |
| Maintainer control plane | `scripts/`, `evals/`, and `.github/workflows/` | Contributors and CI | Owns validation, generation, behavior fixtures, installer smoke tests, and release automation. |

`skills/` and `.agents/skills/` intentionally coexist. The first is the product; the second is this repository's dogfooded harness and currently includes the private `skill-eval` workflow.

## Published skill layout

```text
skills/<name>/
├── SKILL.md                 # resident route, invariants, shortest safe workflow
├── references/<topic>.md    # optional reference material
├── scripts/                 # optional deterministic runtime/helper
└── assets/                  # optional installed templates or output resources
```

Keep `SKILL.md` lean because its frontmatter is always-resident routing metadata. Reference pages must be reachable from `SKILL.md`, directly or through another reference. Validation checks local targets and containment; names and headings are editorial choices.

## Source and generated ownership

| Edit here | Produces or reconciles | Rule |
|---|---|---|
| `skills/<name>/SKILL.md`, references, scripts, and assets | Public installable payload | Edit the skill source directly; update README/catalog metadata and tests when its route or payload changes. |
| `scripts/workflow_runtime/{common,deep_interview,ralph}.py` | Standalone approval and bounded-loop runtimes shipped by `deep-interview` and `ralph` | Run `python scripts/generate_workflow_runtimes.py`; do not hand-edit generated runtime files. |
| `scripts/p0_runtime/{common,skill_eval,workctl}.py` | Private `skill-eval` and public `work-protocol` runtime packages | Run `python scripts/generate_p0_runtimes.py`; keep the public/private publication boundary intact. |
| `.agents/skills/<name>/` | `.claude/skills/<name>` real-directory symlink projections | Run `.agents/relink-skills.sh`; preserve unrelated entries and fail on ownership conflicts. |
| `.agents/subagents/<name>/` | `.claude/agents/*.md` and `.codex/agents/*.toml` | Run `.agents/tools/generate-subagents.py`; generated projections are not edit targets. |
| `agent-scaffold` EOL assets | Prepended `.gitattributes` defaults and a missing-only `.editorconfig` seed | Project exceptions and existing editor settings remain owned by the target; no automatic normalization. |
| The `agent-scaffold` catalog skill assets | Scaffold runtime under `.agents/tools/` and related harness files | Change the catalog skill source and run `agent-scaffold upgrade`; direct edits are drift. |

`CLAUDE.md` is a tracked symlink to `AGENTS.md`. On Windows, CI enables native symlink checkout, rematerializes `CLAUDE.md`, and verifies the link before testing.

## Runtime design

- `autopilot` is delivery guidance without its own persistent controller. `deep-interview` adds an optional exact-file approval record; conversation and document structure remain caller-owned.
- Generated workflow runtimes reject non-standard JSON numbers and attempt a best-effort parent-directory sync after atomic state replacement on POSIX hosts.
- `ralph` normally uses its deterministic bounded verifier loop because fixed attempts and mechanical terminal states are its user-facing boundary.
- `skill-eval` owns comparable A/B execution and repository-isolated evidence for this project's evaluations.
- `work-protocol` is public and owns optional durable coordination state such as CAS revisions, leases, hash-chained evidence, and commit-fixed review. Owner IDs and nonterminal phases are caller-owned; completion still requires consistent verification and workspace checks.
- Coordinate state ownership when composing runtimes and keep one active writer per mutable surface.

The [harness design principles](harness-constraint-policy.md) are authoritative for deciding whether a new script, state machine, or targeted contract earns its maintenance and context cost.

## Validation ownership

| Concern | Primary repository checks |
|---|---|
| Route budget, duplicate descriptions, and payload entry types | `scripts/catalog_health.py` and focused fixtures |
| Frontmatter, names, README coverage, references, manifests, and generic catalog rules | `scripts/validate_skills.py` and focused fixtures |
| High-risk skill-specific executable invariants | Registered `scripts/contracts/<skill>.py` modules and targeted tests |
| Generated runtime parity and behavior | Runtime generators plus P0, hardening, coordination primitive, and approval/loop tests |
| Official Agent Skills format | Pinned `skills-ref` validation for every catalog skill and the `skill-eval` project skill |
| Scaffold shape, managed drift, symlinks, hooks, and throwaway installation | Agent-scaffold core, static, and E2E checks |
| Installer discovery and payload fidelity | The audited `skills` CLI discovery/install smoke tests and byte comparison in CI |
| Shell and platform behavior | ShellCheck, the Linux/macOS/Windows matrix, and the separate Python 3.8 runtime-floor job |
| Routing/evaluation contracts | `skill_eval.py` suite validation, offline example execution, and result validation |

`.github/workflows/validate.yml` is the normative CI definition. See the [development guide](development.md) for contributor commands and changed-surface selection.

## Release boundary

Release-facing changes accumulate under `CHANGELOG.md` Unreleased. After the release snapshot passes `main` validation, an annotated stable or numbered prerelease `v` tag invokes `.github/workflows/release.yml`; that workflow reuses full validation, extracts the exact tagged changelog section, and owns GitHub Release creation. Do not race it with a manual publisher.

## Change routing

| Change | Start with |
|---|---|
| Catalog skill route, workflow, reference, script, or asset | The affected `skills/<name>/` source and its targeted contract/evaluation |
| Shared deterministic runtime logic | `scripts/workflow_runtime/` or `scripts/p0_runtime/`, then regenerate |
| Project harness tool, hook, or projection | The owning `agent-scaffold` asset or `.agents/` SSOT—not the managed/generated copy |
| Support, trust, installer, or host claim | `docs/compatibility.md` with dated first-party evidence |
| Contributor command or release procedure | `docs/development.md` and the normative workflows |
| Repository-level Agent rule | `AGENTS.md`, keeping the managed scaffold block intact |
