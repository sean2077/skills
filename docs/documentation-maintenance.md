# Documentation maintenance policy

Documentation is a product surface in this repository: users copy README commands, hosts route from skill metadata, references define operational contracts, templates are installed elsewhere, and compatibility wording carries support expectations.

## Canonical document map

| Document | Canonical responsibility | Keep out |
|---|---|---|
| `README.md` | Catalog orientation, safe first install, skill discovery, and top-level navigation | Maintainer command matrices, generated ownership detail, and volatile host facts |
| `AGENTS.md` / `CLAUDE.md` | Frequently needed repository rules that change Agent behavior | Long procedures, rationale, release recipes, and duplicated architecture |
| `docs/architecture.md` | Product surfaces, source/generated ownership, control planes, and validation boundaries | Volatile host versions and contributor command transcripts |
| `docs/development.md` | Worktree flow, changed-surface checks, full local commands, generation, and release process | Product overview and host certification claims |
| `docs/compatibility.md` | Dated host, installer, trust, version, and verification claims | General architecture and timeless contribution policy |
| `docs/documentation-maintenance.md` | Documentation ownership, evidence classes, information architecture, and change checklist | Product-specific procedures already owned elsewhere |
| `docs/harness-constraint-policy.md` | Decision rule for adding deterministic controls or skill contracts | Tool-specific facts unless the boundary requires an example |
| `skills/*/SKILL.md` | Resident route, hard invariants, and shortest safe workflow | Low-frequency explanation and catch-all reference material |
| `skills/*/references/*.md` | One directly routed on-demand topic | Unrelated procedures or duplicate canonical facts |
| `skills/*/assets/**` | Installed product templates | Unreconciled dogfood edits or generated projections |
| `CHANGELOG.md` | Unreleased changes and immutable release history | Silent retroactive normalization of old behavior |

## Information architecture rules

- Design around actual readers and tasks. At the root, `README.md` serves consumers, `AGENTS.md` serves repository Agents, and `docs/` serves maintainers by topic.
- Use one primary axis at each level. Add navigation or local subgroups for secondary views instead of parallel taxonomies.
- Keep entry points short enough to scan and route to one canonical home for each durable fact.
- Create a new page only when it has a clear reader, task, owner, and load boundary. Do not create empty categories, numbering for its own sake, or catch-all files.
- Delete or merge only with evidence that content is duplicated, stale, superseded, or migrated; update every active route in the same change.

## Evidence and claim rules

1. **Repository-derived facts**—skill count, paths, generators, CI pins, and commands—must come from the same commit as the edit. Prefer manifests, workflows, and executable validators over prose.
2. **External stable contracts**—specifications and durable host path rules—must cite first-party documentation.
3. **External volatile facts**—releases, flags, trust flows, discovery behavior, and platform limits—require a review date and first-party source. Bind claims to a tested version instead of calling a pin “latest.”
4. **Historical facts** stay historical. Record a correction under Unreleased rather than rewriting old releases as though the corrected behavior always existed.

Do not infer runtime compatibility from format conformance, installer discovery, a manifest, or successful parsing. Distinguish **validated**, **installer-tested**, **host-wired**, **behavior-tested**, and **not certified**.

## Command examples

- Treat every copy-paste command as an interface. Verify its working directory, option scope, quoting, identity, confirmation, side effects, and expected result.
- Quote shell globs such as `'*'`; use `./` for local paths that could otherwise be parsed as repository names.
- Keep preview, authorization, mutation, and verification together for risky writes.
- Mark pins as pins and record the source/date for any current-release comparison.

## Change checklist

1. Fix the repository commit used as the evidence baseline.
2. Record the readers, tasks, primary axis, canonical homes, and representative placement decisions before reorganizing.
3. Inventory affected entry points, backlinks, templates, generated projections, manifests, and command snippets.
4. Update the canonical page first; shorten or repair every summary and route that points to it.
5. Verify changed external facts against first-party sources and record the date/version boundary.
6. Run repository-owned catalog checks, targeted tests, local-link checks, and any real CLI/host smoke test required by the changed claim.
7. Add an Unreleased changelog entry and report verified, intentionally unchanged, and unverified boundaries.

Do not add phrase-only CI checks for prose. Mechanical validation should own inventories, links, schemas, generated parity, and executable behavior; dated source review should own volatile external facts.
