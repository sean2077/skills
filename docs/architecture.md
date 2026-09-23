# Repository architecture

This page owns the map of product surfaces, source/generated ownership, and validation responsibility. Contributor commands live in [development](development.md); host and installer claims live in [compatibility](compatibility.md).

## Product surfaces

| Surface | Source | Consumer and boundary |
|---|---|---|
| Published skill catalog | `skills/<name>/` | Installers consume independently installable payloads containing only regular files and directories. |
| Catalog metadata | `.claude-plugin/plugin.json` and README catalog rows | Installer grouping and human navigation, not universal host certification or a native Codex plugin package. |
| Project Agent harness | `.agents/` | This repository's Claude Code and Codex project layers; `.claude/` and `.codex/` hold projections or host configuration. |
| Maintainer tooling | `scripts/`, `evals/`, `.github/workflows/` | Validation, generation, evaluation fixtures, installer smoke tests, and release automation. |

`skills/` is the product and is consumed directly: catalog skills have no generated `.claude/skills` or `.codex/skills` projections, and `.claude/skills/` carries only project skills. `.agents/skills/` holds those project skills, including `skill-eval`, and is not a second catalog copy. The opt-in project subagent `skill-verifier` reviews source and captured evidence. The parent owns execution, fixes, and delivery; see [its use and limits](development.md#optional-skill-verifier). Neither project component is installed for catalog/scaffold consumers.

## Published skill layout

```text
skills/<name>/
├── SKILL.md                 # discovery metadata and on-demand instructions
├── references/<topic>.md    # optional on-demand guidance
├── scripts/                 # optional runtime/helper; may be generated
└── assets/                  # optional installed templates/resources
```

Discovery metadata contributes routing context; selected instructions and resources are loaded as needed by the host. Keep entry points focused and references reachable from `SKILL.md`, directly or through another reference. Shipped attribution notices must remain reachable and intact. Links inside a catalog skill must not depend on repository manuals absent from its installed payload.

## Source and generated ownership

| Edit here | Produces or reconciles | Update path |
|---|---|---|
| `skills/<name>/SKILL.md`, references, and non-generated scripts/assets | Catalog skill payload | Edit directly, except for the generated payloads listed below. Reconcile routes, manifests, tests, and notices when affected. |
| `scripts/workflow_runtime/{common,deep_interview}.py` | Exact-file approval runtime shipped by `deep-interview` | `python scripts/generate_workflow_runtimes.py` |
| `scripts/p0_runtime/{common,skill_eval}.py` | Project `skill-eval` runtime package | `python scripts/generate_p0_runtimes.py` |
| `.agents/skills/<name>/` | `.claude/skills/<name>` symlink projections; Codex uses the project skill source | `bash .agents/relink-skills.sh`; preserve unrelated entries and reject ownership conflicts |
| `.agents/subagents/<name>/` | `.claude/agents/*.md` and `.codex/agents/*.toml` | `python .agents/tools/generate-subagents.py` |
| `agent-scaffold` catalog assets | Scaffold runtime under `.agents/tools/`, relinking tools, managed contract, and owned hook entries | Use the catalog skill's `upgrade`, then `verify`; do not edit installed runtime or generated projections directly |
| `agent-scaffold` EOL assets | Prepended `.gitattributes` defaults and a missing-only `.editorconfig` seed | Preserve project exceptions and existing editor settings; normalization is a separate authorized operation |

`CLAUDE.md` is a tracked symlink to `AGENTS.md`; only the marker-bounded scaffold block is managed, not the entire authority document. Real symlinks are required for this harness even though catalog payloads themselves cannot contain symlinks. Windows CI enables native symlink checkout and verifies the materialized link before testing.

## Project-convention ownership

A full `agent-scaffold` initialization or upgrade has two responsibilities: deterministic
asset reconciliation, and Agent-authored project guidance. The latter adopts actual entry
points, layouts, commands, verification limits and source ownership before filling gaps.
New guidance is project-owned, not managed-template content. Later runs preserve renamed,
merged or deliberately removed guides and repair confirmed drift in their current homes.
The managed AGENTS block does not grow, and no layout registry or new controller is added.

Installer reports explicitly scope `ok` to `harness-assets` with `project_guidance` set to
`not-assessed`. Semantic coverage is evaluated separately; see the installed
[project-conventions guide](../skills/agent-scaffold/references/project-conventions.md).
The repository dogfoods that separation through this ownership map, the development guide,
and documentation maintenance rather than generating parallel documents.

## Runtime boundaries

| Component | Owned semantics |
|---|---|
| `deep-interview` | Optional approval bound to the exact specification bytes and revision; conversation and document structure remain caller-owned. |
| Project `skill-eval` | Comparable evaluation execution and repository-isolated evidence; isolation is not an OS sandbox. |

Generated workflow runtimes reject non-standard JSON numbers and attempt best-effort parent-directory sync after atomic state replacement on POSIX hosts. Use one state owner for each mutable surface; combining skills does not imply running every controller. The [design principles](harness-constraint-policy.md) explain when extra machinery earns its cost.

## Validation ownership

| Concern | Owning checks |
|---|---|
| Route budget, duplicate descriptions, payload entry types | `scripts/catalog_health.py` and fixtures |
| Frontmatter, names, README coverage, reference targets/reachability, manifests | `scripts/validate_skills.py` and fixtures |
| High-risk skill-specific interfaces and executable invariants | Registered `scripts/contracts/` modules and targeted tests |
| Generated runtime parity and behavior | Runtime generators and workflow/evaluation/hardening tests |
| Official Agent Skills format | Pinned `skills-ref` for every catalog skill and project `skill-eval` |
| Scaffold shape, drift, managed hooks, symlinks, installation | Core/workspace/layout-preservation tests, static gate, and throwaway-repository E2E |
| Installer discovery and payload fidelity | Audited CLI discovery and byte-compared installation in CI |
| Shell/platform behavior and runtime floor | ShellCheck, Linux/macOS/Windows matrix, and Python 3.8 job |
| Evaluation plumbing and task oracles | Suite/result validation, adapter regressions, and task-outcome fixtures |

[Validation CI](../.github/workflows/validate.yml) is the executable inventory. These checks do not establish live-host discovery, model effectiveness, or measured savings. Catalog reference checks also do not cover all repository links or heading fragments; see [documentation verification](documentation-maintenance.md#evidence-and-verification).

## Release boundary

[Release CI](../.github/workflows/release.yml) owns GitHub Release publication after reusable validation, supported-tag checks, main reachability, and exact changelog extraction. See the [release flow](development.md#release-flow) for preparation and completion evidence; a planner result or pushed tag alone is not completion.
