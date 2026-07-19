# Changelog

All notable changes to this project are documented in this file. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Catalog reference validation now accepts equivalent imperative load-boundary wording while
  still requiring each on-demand reference to state a conditional load boundary near the top.
- Resident documentation and tooling workflows now route decision-record field detail to their
  canonical references instead of carrying a second always-loaded copy.
- Project documentation numbering is now evidence-gated instead of default-on when a dedicated
  tree lacks a convention; absence of a convention alone no longer triggers path prefixes.
- Tool command contracts now preserve project-owned CLI, language, output, and state mechanisms;
  only safety and behavior cards supported by the command's Contract Profile are applied.

### Fixed

- README skill summaries now participate in the documentation/tooling domain guards, preventing
  public catalog copy from retaining behavior that those skills have retired.
- `conventional-commit` now treats mixed-ownership hunks within one path as a staging boundary
  and requires inspection of the actual cached patch before commit.
- Ordinary commit mode now stops on in-progress merge, rebase, cherry-pick, revert, bisect, and
  unresolved-conflict states even when `HEAD` remains attached.
- Ordinary commit verification now proves that the new commit contains the exact reviewed index
  tree and directly advances the recorded parent, including the unborn-branch case.
- `semver-release` now rejects active Git operations in its read-only plan even when the branch is
  attached and the porcelain worktree status is empty.
- `agent-scaffold` trunk-guard guidance now requires explicit authorization for a trunk edit;
  merely mentioning a trunk branch no longer appears to authorize the escape hatch.
- The pinned `npx skills` installation smoke test now compares every installed skill's complete
  file inventory and bytes, covering executable scripts and assets as well as references.
- `semver-release` now derives completion from repository policy instead of treating a forge
  release and URL as universal; explicit tag-only, workflow, registry, artifact, and handoff
  boundaries remain valid and are verified only when applicable.
- The structural tooling inventory checker now resolves Python 3.8+ through `PYTHON_BIN`,
  `python`, `python3`, or Windows `py -3` instead of rejecting non-`python` environments.
- The release planner no longer treats a standalone stale `REBASE_HEAD` as an active rebase;
  worktree-aware `rebase-merge` or `rebase-apply` state remains blocking.
- Non-conventional merge commits now remain audit-visible as `kind: "merge"` without masking the
  Conventional Commit signals in their child history; explicit merge-level signals still count.

## [v4.0.0] — 2026-07-19

### ⚠ Breaking

- `tooling-conventions` retires its exactly-one surface taxonomy and semantic manifest contract.
  The bundled `<skill-dir>/scripts/manifest-check.sh` is replaced by
  `<skill-dir>/scripts/inventory-check.sh` without a compatibility wrapper or legacy mode;
  `MANIFEST_CHECK_SKIP` is replaced by `INVENTORY_CHECK_SKIP`.
- `project-docs-organizer` removes `references/zone-catalog.md` and the universal numbered-zone
  vocabulary without a compatibility alias. Consumers must derive project-owned information
  architecture from the new classification methods instead of reusing fixed semantic ranges.

### Changed

- `project-docs-organizer` now selects reader, task, domain, product, content-purpose, and
  lifecycle lenses from repository evidence, records an IA decision before mutation, and treats
  numbering as optional sibling-local presentation rather than cross-project classification.
- `agent-scaffold` now publishes explicit authority-document freshness, residency, scope, and
  conflict laws while leaving third-party skill placement and installation policy project-owned.
- Tool governance now derives Job Boundaries, Contract Profiles, and project-owned Placement
  Decisions through eight boundary/constraint method cards, and requires a Tool Governance
  Decision Record before recommendations or mutation.
- The optional checker now accepts a path-only structural TSV with opaque project-owned columns,
  keeps `tools/tools-inventory.tsv` only as its no-argument default, and derives the scan root
  from an explicit `TOOLS_DIR` or the inventory location. Semantic policy remains target-owned.
- Deterministic fixtures cover default and custom command roots, separated inventories,
  directory non-coverage, syntax and reverse drift, warn/enforce behavior, and safe preflights.

### Fixed

- The structural inventory checker now rejects an exact `..` path as a blocking normalization
  failure even when its row requests warning-level handling.
- Inventory fixtures now compare canonical scan roots across Windows, macOS, and Linux and carry
  the indirect-call ShellCheck annotations required by the CI runner.

## [v3.0.2] — 2026-07-17

### Docs

- Catalog maintenance now documents the pinned `npx skills` help/removal hazard and the safe,
  repository-external global-update workflow.

## [v3.0.1] — 2026-07-17

### Fixed

- E2E temporary-directory guards now use explicit control flow and version-compatible
  ShellCheck annotations for cleanup functions invoked indirectly by `EXIT` traps.

## [v3.0.0] — 2026-07-17

### ⚠ Breaking

- `tooling-conventions` moves its reusable checker from `manifest-check.sh` to
  `scripts/manifest-check.sh` and its schema guidance into
  `references/manifest-schema.md`; no compatibility wrapper is retained.

### Changed

- `conventional-commit`, `semver-release`, `project-docs-organizer`, and
  `tooling-conventions` now keep only invariants, workflow skeletons, output contracts,
  and explicit on-demand routers resident in `SKILL.md`.
- `semver-release` adds a read-only, JSON-capable planner for strict reachable SemVer
  bases, shallow-history boundaries, conventional-commit bumps, prerelease promotion,
  explicit targets, and tag ambiguity.
- Release-note ownership is now project-defined; committed changelogs, fragments,
  generated notes, and forge-native notes remain valid, and the planner exposes the
  generic `release_notes_base` range instead of a changelog-specific field.
- Its planner regression suite now covers first releases, empty release ranges,
  unclassified histories, canonical prerelease precedence, same-commit build metadata,
  explicit prerelease advancement, invalid targets, detached HEAD, and real shallow clones.
- `project-docs-organizer` now treats information architecture and numbered zones as
  project-owned choices instead of imposing a complex-project template.
- Catalog validation now enforces lean resident budgets, metadata-only trigger boundaries,
  direct on-demand routing, and conditional load declarations for references.
- Validation and agent-scaffold test entry points now reject unknown arguments before
  doing work, and E2E temporary-directory setup fails closed.
- The optional tooling manifest checker now rejects masked/extra CLI arguments, path
  traversal and non-normalized rows, invalid audit levels, malformed directory rows,
  and temporary-directory setup failures.
- Recursive temporary-directory cleanup now requires a canonical parent, an entry-specific
  prefix, and a non-empty generated suffix; agent-scaffold and tooling regression suites
  inject both creation failures and forged broad paths before target mutation.
- Public scaffold, worktree, relink, validation, manifest, and release-planner entry points
  now reject help mixed with invalid arguments, missing flag values, and extra positional
  arguments before performing their default work.
- Scaffold-managed runtime, hook JSON, authority-contract, ignore, attributes, subagent, and
  symlink updates now use unique destination-local candidates and atomic replacement. Managed
  directory symlinks are rejected before traversal so they cannot redirect writes outside the
  repository, and unrelated legacy temp-name paths remain untouched.
- The installed worktree helper now anchors repository operations to its own location, so commands
  remain correct when invoked from outside the repository. Detached release worktrees use portable
  ref-plus-commit directory names and the guarded `worktree.sh done` cleanup path; dirty release
  outputs remain in place, unsafe temporary registry paths fail closed, and no workflow recommends
  force removal.
- The optional tooling manifest checker now enforces `entry_for` surface semantics and declared
  public/installed CLI-contract evidence when those columns are present; a source comment that
  merely mentions `--help` no longer creates false assurance.
- Repository onboarding now links the complete development gates and changelog, with focused
  regression suites documented as a general catalog testing surface.

## [v2.0.0] — 2026-07-17

### ⚠ Breaking

- `agent-scaffold` replaces the identical `init` / `retrofit` commands with one idempotent
  `apply` mode. `--profile default|light` replaces the negative worktree selector, and
  `upgrade` now refreshes only the current managed layout.
- The single public entry point is now `agent-scaffold.sh`; the historical
  `harness-init.sh` name is removed without an alias.
- Old runtime-path migration, retired formatter cleanup, package/Husky caller rewrites,
  deprecated no-op selection flags, and their verification fixtures are removed outright.
  Current modes inspect and reconcile only the current harness contract.
- `agent-scaffold` installs only harness-owned runtime and contract content. Formatter,
  example-agent, hook-manager, package, CI, project prose, nested-contract, and Codex
  settings choices remain project-owned reference recipes.

### Changed

- Catalog skills now route on-demand depth through category-named `references/*.md`
  files instead of root-level catch-all `reference.md` documents.
- `agent-scaffold` now uses an internal managed-assets manifest and a deterministic Python
  core for asset resolution, hook JSON, and read-only reports while retaining one public
  Bash entry point. Target assets live under `assets/`; installer internals live under
  `scripts/`.
- `plan`, `doctor`, and `verify` support schema-versioned `--json` output with stable check
  IDs, statuses, paths, fixes, profile, and `plan.apply_mode`.
- `plan` and mutation preflight now share one inspection model. `apply` rejects managed runtime
  drift that requires `upgrade`, while `verify` checks the complete managed AGENTS block and
  manifest-owned line invariants in addition to runtime, hooks, links, and projections.
- The resident `SKILL.md` is reduced to routing, invariants, and workflow. Current retrofit
  and diagnostic guidance is loaded on demand; maintainer E2E recipes no longer ship as
  skill reference content.
- Deterministic core behavior is covered by focused Python unit tests; generator/import and
  conflict preflights live in an internal failure-domain suite, while the one public E2E command
  remains responsible for real installation, symlink, worktree, hook, profile, and projection
  interactions.

## [v1.0.0] — 2026-06-30

First stable release of the **`sean2077/skills`** catalog — a universal
[SKILL.md](https://github.com/anthropics/skills) collection of reusable agent skills
installable into any project via `npx skills` (Claude Code + Codex and other
Agent-Skills hosts).

### Added

- **`conventional-commit`** — create one local git commit with a Conventional Commits
  subject whose summary language follows repository history, defaulting to English when
  history is absent or unclear.
- **`semver-release`** — cut a semantic-version release from conventional commits: infer
  the MAJOR/MINOR/PATCH bump since the last tag, update `CHANGELOG.md` and the version
  file, create the release commit and annotated tag, optionally publish a GitHub/GitLab
  release, and push. Handles prerelease (beta/rc) and promotion to final.
- **`project-docs-organizer`** — build, restructure, or clean up a project's documentation
  system: README files, `docs/` trees, onboarding/maintainer docs, ADRs, specs, plans,
  runbooks, archives, and documentation navigation.
- **`tooling-conventions`** — govern a project's `tools/` or `scripts/` directory at scale:
  classify each script by surface, aggregate commands by failure-domain, enforce a script
  contract (`-h/--help` + exit codes, secrets hygiene, atomic + idempotent writes), and
  keep a machine-readable surface manifest in sync. Ships `manifest-check.sh`.
- **`agent-scaffold`** — install or retrofit the dual-host (Claude Code + Codex) agent
  harness into a project: the `.agents/` single-source-of-truth layout, worktree-per-change
  flow with a trunk-edit guard, `AGENTS.md` budget + format-on-edit hooks, the
  `CLAUDE.md`→`AGENTS.md` contract, skill symlinks, and a python subagent generator with a
  drift guard. One idempotent, merge-aware installer with `init`, `retrofit`, `plan`,
  `verify`, and `upgrade` modes.

### Infrastructure

- CI quality gates run on push/PR via `.github/workflows/validate.yml`:
  `validate_skills.py` (frontmatter, name↔dir, link + allowed-tools hygiene),
  `check-agent-scaffold.sh` (static gate), and `e2e-agent-scaffold.sh` (behavioral gate that
  installs the harness into a throwaway repo and asserts it works).
- The repository dogfoods the `agent-scaffold` harness (`.agents/` SSOT + `tools/agent/`), so
  the catalog is developed with the same governance it ships.

[Unreleased]: https://github.com/sean2077/skills/compare/v4.0.0...HEAD
[v4.0.0]: https://github.com/sean2077/skills/compare/v3.0.2...v4.0.0
[v3.0.2]: https://github.com/sean2077/skills/compare/v3.0.1...v3.0.2
[v3.0.1]: https://github.com/sean2077/skills/compare/v3.0.0...v3.0.1
[v3.0.0]: https://github.com/sean2077/skills/compare/v2.0.0...v3.0.0
[v2.0.0]: https://github.com/sean2077/skills/compare/v1.0.0...v2.0.0
[v1.0.0]: https://github.com/sean2077/skills/releases/tag/v1.0.0
