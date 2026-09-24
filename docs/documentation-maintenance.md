# Documentation maintenance

Keep durable facts in their authoritative home and maintain the routes readers use to find them. This page owns documentation practice, not a mandatory review workflow.

For reusable structure, numbering, metadata, pruning, and migration methods, use the installed [documentation conventions](../.agents/conventions/docs.md). The sections below add this repository's owners and verification boundaries.

## Ownership

| Source | Responsibility |
|---|---|
| `README.md` | Consumer orientation, concise catalog, installation entry point, and navigation |
| `AGENTS.md` / linked `CLAUDE.md` | Frequently needed repository instructions; preserve scaffold ownership of its managed block |
| `docs/skill-composition.md` | Selecting and combining catalog routes; retired-installation cleanup |
| `docs/architecture.md` | Product surfaces and source/generated ownership |
| `docs/development.md` | Maintainer commands, checks, generation, and this repository's release procedure |
| `docs/compatibility.md` | Dated installer/host claims and their evidence limits |
| `docs/harness-constraint-policy.md` | Skill design and validation principles |
| `CONTEXT.md` | Repository terminology |
| `CHANGELOG.md` and `docs/audits/*.md` | Pending changes, release history, and dated review evidence |
| `skills/<name>/SKILL.md` and references | Self-contained installed skill guidance; with its tests, the skill's behavior specification (there is no separate spec tree; rationale lives in PRs, `CHANGELOG.md` and dated audits) |
| `evals/agent-skills/README.md` / `evals/tasks/README.md` | Routing-probe / task-outcome procedures and measurement limits |
| Scaffold assets and shared runtime source | Generated/installed content; see the [ownership map](architecture.md#source-and-generated-ownership) |

## Editing and reorganization

Entry points summarize and route; do not copy full skill descriptions, command manuals, or test inventories into every page. A source-backed paragraph that remains accurate needs no rewrite just to refresh its date.

Consumers of changed guidance here include templates, generated projections, and manifests as well as links and command examples. Keep catalog-skill references inside their installable payload; repository-level manuals can link across the repository. See the scaffold's [project conventions](../skills/agent-scaffold/references/project-conventions.md) for first-use setup and upgrade ownership; ordinary document maintenance does not require invoking scaffold.

## Evidence and verification

Derive repository facts from the inspected revision: paths, flags, generators, pins, counts, schemas, and commands. For external product contracts, retain first-party sources and the actual review date or tested version. Editing surrounding prose is not a new host test or source review; a reproducibility pin is not an upstream-latest claim.

Use the [changed-surface checks](development.md#select-checks-by-changed-surface). Catalog reference validation checks contained Markdown file targets and reachability; it does not validate every repository document or heading fragment. Review those links and anchors separately, including incoming links after a move. Verify working directory, scope, quoting, identity, effects, confirmation, and expected result for changed commands; keep preview, authorization, mutation, and verification distinct for consequential writes. Distinguish commands inspected from commands executed.

Record reader-journey gaps from a material reorganization in the PR rather than adding a permanent audit page for routine maintenance. Add user- or maintainer-visible changes under Unreleased.

## Historical records

The [2026-09-24 live evaluation](audits/2026-09-24-live-evaluation.md), [2026-09-20 native-first audit](audits/2026-09-20-native-first.md), and [2026-09-06 harness audit](audits/2026-09-06-harness.md) retain review-time evidence and rationale. Their catalog counts, paths, recommendations, and host observations may have been superseded. Use current architecture, compatibility, and skill guidance for new work.

Preserve released changelog sections and useful audit evidence. Put corrections in the owning current document and Unreleased; do not rewrite history to look like current-main behavior. Keep old paths only when they still serve a reader or compatibility need, not as parallel current manuals.
