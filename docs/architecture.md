# Repository architecture

This page maps product surfaces, source/generated ownership, and validation ownership. [Development](development.md) owns contributor procedures; [compatibility](compatibility.md) owns installer and host evidence.

## Product surfaces

| Surface | Source | Boundary |
|---|---|---|
| Published skill catalog | `skills/<name>/` | Independently installable payloads containing regular files and directories only. |
| Catalog metadata | `.claude-plugin/plugin.json` and README catalog rows | Installer grouping and navigation, not universal host certification or a native Codex plugin package. |
| Project Agent harness | `.agents/` | This repository's project skills, subagents, and scaffold runtime; `.claude/` and `.codex/` contain host projections/configuration. |
| Release runtime | `skills/agent-scaffold/assets/runtime/release/` → `.agents/tools/release/` | Task-time conventions, read-only version analysis, and changelog extraction, installed only for the selected `release` domain and never resident. |
| Maintainer tooling | `scripts/`, `evals/`, `.github/workflows/` | Validation, generation, evaluation fixtures, installer tests, and release automation. |

The catalog is consumed directly; it has no generated `.claude/skills` or `.codex/skills` copies. `.agents/skills/` holds project skills, including `skill-eval`; `.claude/skills/` projects only those project skills. Project subagent `skill-verifier` reviews source and captured evidence, with [execution and delivery owned by its parent](development.md#optional-skill-verifier). Neither evaluator is installed for catalog/scaffold consumers.

## Published skill layout

```text
skills/<name>/
├── SKILL.md                 # discovery metadata and on-demand instructions
├── references/<topic>.md    # optional on-demand guidance
├── scripts/                 # optional runtime/helper; may be generated
└── assets/                  # optional installed templates/resources
```

Keep entry points focused and references reachable from `SKILL.md`, directly or through another reference. Attribution notices must remain reachable and intact. Catalog links cannot depend on repository manuals absent from the installed payload.

## Source and generated ownership

| Edit here | Produces or reconciles | Update path |
|---|---|---|
| `skills/<name>/SKILL.md`, references, and non-generated scripts/assets | Catalog payload | Edit directly, except for the generated content below; reconcile affected routes, manifests, tests, and notices. |
| `scripts/workflow_runtime/{common,deep_interview}.py` | Exact-file approval runtime shipped by `deep-interview` | `python scripts/generate_workflow_runtimes.py` |
| `scripts/p0_runtime/{common,skill_eval}.py` | Project `skill-eval` runtime package | `python scripts/generate_p0_runtimes.py` |
| `.agents/skills/<name>/` | `.claude/skills/<name>` symlinks; Codex uses the project source | `bash .agents/relink-skills.sh`; preserve unrelated entries and reject ownership conflicts |
| `.agents/subagents/<name>/` | `.claude/agents/*.md` and `.codex/agents/*.toml` | `python .agents/tools/generate-subagents.py` |
| `agent-scaffold` catalog assets | `.agents/tools/`, relinking tools, managed contract, and owned hook entries | Catalog skill `upgrade`, then `verify`; do not patch installed runtime or projections |
| `agent-scaffold` EOL assets | Prepended `.gitattributes` defaults and missing-only `.editorconfig` seed | Preserve project exceptions/settings; normalization requires separate authorization |

`CLAUDE.md` is a tracked symlink to `AGENTS.md`. Only its marker-bounded scaffold block is managed; surrounding prose is project-owned. This harness requires real symlinks even though catalog payloads cannot contain them. Windows CI enables native symlink checkout and verifies the materialized link.

## Project-convention ownership

A full scaffold setup combines deterministic asset reconciliation with Agent-authored guidance in the project's existing locations. `.agents/scaffold.json` records the accepted convention domains, not layout or completed guidance. [Onboarding selection](../skills/agent-scaffold/references/onboarding-selection.md) owns first-use defaults, exclusions, pending state, and reuse; [project conventions](../skills/agent-scaffold/references/project-conventions.md) owns guidance adoption and maintenance.

Selected guidance remains project-owned, outside the managed AGENTS block. Preserve existing policies and deliberate guide renames, merges, or removals; repair confirmed drift in their current homes. The installer reports `scope: harness-assets` and `project_guidance: not-assessed`. A successful installation or saved selection does not establish semantic coverage. This repository uses its existing manuals rather than a parallel scaffold-generated documentation tree.

## Runtime boundaries

| Component | Owned semantics |
|---|---|
| `deep-interview` | Optional approval bound to exact specification bytes and revision; conversation and document structure remain caller-owned. |
| Project `skill-eval` | Comparable evaluation execution and repository-isolated evidence; not an OS sandbox. |

Generated workflow runtimes reject non-standard JSON numbers and attempt best-effort parent-directory sync after atomic state replacement on POSIX. Keep one state owner per mutable surface; combining skills does not require running every controller. See [harness principles](harness-constraint-policy.md).

## Validation ownership

[Validation CI](../.github/workflows/validate.yml) is the executable check inventory. Catalog health/validation own routing, payloads, frontmatter, manifests, and reference reachability; registered `scripts/contracts/` modules own skill-specific interfaces. Generators and targeted tests check runtime/projection parity and behavior. Installer, scaffold, platform, and evaluation checks cover their respective boundaries.

Use [changed-surface checks](development.md#select-checks-by-changed-surface) to select local evidence. Green CI does not establish live-host discovery, model effectiveness, or savings. Catalog reference validation does not cover all repository links or heading fragments; see [documentation verification](documentation-maintenance.md#evidence-and-verification).

## Release boundary

[Release CI](../.github/workflows/release.yml) owns publication after reusable validation, supported-tag checks, main reachability, and exact changelog extraction. The [release flow](development.md#release-flow) defines preparation and completion evidence; a planner result or pushed tag is not a completed release.
