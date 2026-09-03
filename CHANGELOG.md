# Changelog

All notable changes to this project are documented in this file. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Made `project-docs-organizer` and `tooling-conventions` use compact inline decision deltas for contract-preserving maintenance while reserving full decision records for material information-architecture, command-boundary, contract, or placement changes.
- Reworked the live Agent Skill adapter to derive route vocabulary from the checked-out catalog, preserve host-classified workflows, normalize only route/workflow/key spelling, and stop synthesizing expected fields from prompt heuristics.
- Added an explicit `code-review` exclusion to the `analyze` routing description so defect review of a concrete change set is decided on the always-resident routing surface, not only inside the body.
- Reduced the scaffold-managed `AGENTS.md` harness block while preserving its worktree, authority, ownership, trust, and checkpoint boundaries.
- Added an always-on, project-owned terminology contract to `agent-scaffold`: every Agent, skill, and subagent consumes the declared glossary; multilingual glossaries may define equal canonical equivalents per language without imposing a primary discussion language; multi-context repositories can route through `CONTEXT-MAP.md`; and empty glossaries are never seeded or overwritten during upgrades.
- Made terminology topology proportional: projects may model contexts up front or evolve from a flat glossary to subject groups and then mapped contexts, while early projects with insufficient evidence require focused owner input instead of invented domains.
- Moved the live Agent Skill host adapter into `evals/agent-skills/host_adapter.py` and updated routing suites to invoke it through the repository's Python runtime instead of requiring a user-level `PATH` installation.
- Recast `deep-interview`'s one-to-three question range as a soft default, allowing larger structured batches for independent low-effort intake while preserving sequential probing for branching or consequential decisions.
- Extended `spec-writing` to preserve semantic boundaries, distinguish current from target behavior, compare material implementation options, resolve detail against the project's authority model, and keep only high-value rationale in the reader document.

### Added

- Added deterministic live-adapter and verifier regressions plus positive, negative, and confusable routing suites for proportional documentation and command governance.
- Added a README catalog-count parity gate to `validate_skills.py`: a declared `catalog of N reusable` count must match the `skills/` directory inventory, and a README that declares no count has nothing to drift.
- Added `domain-modeling`, adapted from Matt Pocock's MIT-licensed skill, for active terminology discovery, ambiguity challenges, user-selectable up-front or incremental context modeling, evidence-based glossary partitioning, and atomic `CONTEXT.md`/`CONTEXT-MAP.md` migration.
- Added `spec-writing`, a focused skill for concise human-facing requirements and architecture documents that preserves settled meaning, keeps material rationale with the reader narrative, and routes working history to separate records.

### Fixed

- Collapsed scaffold PreToolUse/PostToolUse work into one Python process: skip the separate version probe, classify linked vs primary worktrees from `.git` metadata, run `git check-ignore` only when a primary-worktree edit might be blocked, and emit the authority-doc nudge without jq or a second interpreter, cutting Windows hook latency from extra git/cygpath/python spawns.
- Set scaffold-owned PreToolUse/PostToolUse hook `timeout` to 30 seconds and taught `hook-paths.py` to parse Grok `toolInput`/`workspaceRoot` as well as Claude/Codex `tool_input`, so Windows Git-Bash hook chains no longer fail-open on Grok's 5-second default.
- Made live evaluation gate adapter completion and candidate selection separately from behavior so positive, negative, and confusable routing failures cannot be hidden by normalized metadata; selection checks honor explicit positive-case overrides, and malformed adapter input now returns a stable failed envelope instead of crashing in the exception path.
- Corrected the stale public-catalog count in `compatibility.md` and removed hard-coded catalog counts from `AGENTS.md` and `compatibility.md` prose so repository-derived skill counts stay in the inventory-checked README instead of drifting across authority documents.
- Made the hook launcher's Bash availability guard an explicit conditional, preserving its fail-closed behavior while satisfying the Linux CI ShellCheck rule.
- Made the primary worktree's checked-out branch the default active trunk, recorded that trunk per generated change branch for `done`, and guarded the primary worktree by Git role rather than fixed branch names.
- Made `worktree.sh done` leave and target worktrees explicitly in its generated guidance, validate retry settings before merge or push, retry transient Windows sharing violations while the worktree remains registered and clean, and retry only empty residual directories after Git unregisters them, without force or recursive deletion.
- Made scaffold-owned Windows hooks enter through Git for Windows and select its Bash explicitly, avoiding accidental resolution to the native WSL launcher; hook payloads now parse stdin once without argv/environment-size exposure, and malformed guard input fails closed while the document-budget hook remains advisory.
- Made hook reconciliation and verification compare complete managed hook/group JSON rather than command strings alone, so drift in `type`, `statusMessage`, or future execution fields is repaired and reported.
- Bound `worktree.sh done --dir` to an exact registered worktree in the helper's own common Git directory before reading status or merging, preventing a foreign repository or same-named branch from crossing the lifecycle boundary.
- Replaced symlink projections atomically without unlinking the prior projection first, preserving the old link or placeholder when replacement fails.

## [v6.0.0] — 2026-08-25

### Added

- Added a cross-platform catalog-health gate and focused fixtures for per-route resident-context budgets, duplicate routing metadata, and non-regular published payload entries.
- Added a dated compatibility/verification matrix and a documentation maintenance policy that separate format validation, installer discovery, host wiring, runtime behavior, and unverified targets.

### Changed

- Refreshed the dated compatibility evidence against current Codex skill, plugin, hook, and configuration documentation, and clarified that the installer's `.claude-plugin/plugin.json` grouping manifest is not a native Codex `.codex-plugin/plugin.json` package.
- Compressed the six longest published routing descriptions while preserving their decisive triggers and adjacent-skill exclusions, reducing always-resident catalog metadata without adding a new route.
- Separated execution topology from durable control state across harness guidance: one Agent remains the default, ephemeral subagents require bounded independent work and compact returns, project-owned subagents require a repeated stable role, and host durable goals precede persistence runtimes unless explicit machine-state semantics add value.
- Tightened `autopilot`, `ralph`, and `work-protocol` selection boundaries to avoid duplicate controllers, overlapping writers, and unnecessary persistent state.
- Reworked README and maintainer guidance to use bounded compatibility claims, identify `skills@1.5.17` as an audited CI pin rather than upstream latest, and use `--skill '*'` when installing the complete catalog to only Claude Code and Codex.
- Updated the Lark command cache to the official `lark-cli` v1.0.89 safety boundary for `apps +cache-clear`: an imperative clear request is not confirmation, the first call must not self-supply `--yes`, and the environment must be explicit.
- Established canonical architecture and development pages, reduced README and AGENTS to audience-specific entry points, and updated documentation ownership and navigation.

### Fixed

- Made the generated `autopilot`, `deep-interview`, and `ralph` runtimes reject non-finite JSON constants at state and input boundaries, forbid them in state and CLI output, and attempt a best-effort parent-directory sync after atomic state replacement on POSIX hosts.
- Made the real-installer payload smoke test fail before file comparison when either source or installed skill contains a symlink or special filesystem entry, closing the `find -type f` omission boundary.
- Documented Codex's two independent gates for project-local hooks: project trust plus review of each exact non-managed hook definition, with re-review after a hook hash changes.
- Documented that Claude Code checkpoint restore skips symlinked and hard-linked files, which affects this harness's `CLAUDE.md` and project-skill projections.
- Reconciled the dogfooded `.agents/skills/README.md` with the scaffold template's project-owned third-party placement policy.
- Repaired the local catalog-root install example so it remains one copy-pasteable command instead of wrapping inside inline code.

### ⚠ Breaking

- Removed `skill-eval` from the published catalog and installer manifest. It now lives under `.agents/skills/skill-eval` as a project-private harness skill, with its generated runtime and evaluation contracts retained for this repository's CI and maintainers.

## [v5.0.0] — 2026-08-21

### Added

- Added `docs/harness-constraint-policy.md`, a decision rule for keeping mechanical controls around costly machine state while leaving reversible single-session reasoning model-native.
- Added live positive/negative/confusable routing suites for `analyze`, `autopilot`, and `deep-interview`. CI validates their manifests, while behavioral acceptance requires a real `agent-skill-host-adapter`; fake adapters are explicitly not treated as model evidence.
- Added `skill-eval`, an independently installable Python 3.8+ standard-library evaluation harness for baseline/treatment runs materialized in a clean detached worktree at one resolved commit. It gates positive, negative, and confusable routing, deterministic verifier evidence, changed-path scope, repository isolation, complete cost metrics, pair comparability, and absolute/relative budgets; an offline TDD fixture makes the contract executable in CI without a model or network.
- Added `work-protocol`, an optional durable task protocol for cross-session, multi-writer, or high-risk delivery. It owns `.agents/work/<task-id>/` artifacts, compare-and-swap state, one expiring and recoverable loop-owner lease, hash-chained evidence, current-cycle verification, commit-pinned reviewer snapshots, isolated writable worktrees, path ownership, and safe cleanup while leaving Agent reasoning and tool use to the native host.
- Added one maintainer SSOT and deterministic generator for both P0 runtimes, plus behavioral, concurrency, repository-mutation, lease, evidence-integrity, worktree-ownership, symlink-boundary, and Python-floor regressions.

- Added `tdd`, an explicitly triggered, stack-neutral RED-GREEN-REFACTOR skill adapted from Matt Pocock's MIT-licensed TDD skill. It derives seams, independent oracles, test levels, working directories, and verification commands from target-project evidence; covers effects and doubles, legacy systems, generated code, concurrency, compatibility and migrations, security, performance, data/ML, infrastructure, and embedded targets; and ships a per-skill contract plus focused regressions against ecosystem defaults and rigid seam, assertion, mocking, or refactoring rules.
- Migrated eight reusable workflows from the former bundled runtime into independently installable
  catalog skills: `analyze`, `ai-slop-cleaner`, `autopilot`, `best-practice-research`,
  `code-review`, `deep-interview`, `prototype`, and `ralph`. `autopilot`, `deep-interview`, and
  `ralph` ship self-contained standard-library Python state runtimes plus behavioral regressions;
  no migrated skill requires a separate project CLI.
- Added one maintainer source and deterministic generator for the standalone `autopilot`,
  `deep-interview`, and `ralph` runtimes, plus cross-platform CI regressions for generation drift,
  interruption, corruption, recovery, concurrency, path safety, worktrees, non-Git roots, and
  terminal behavior. CI also exercises the declared Python 3.8 compatibility floor in addition to
  the Linux/macOS/Windows Python 3.11 matrix.
- Folded research optimization and adversarial end-to-end QA into on-demand `ralph` profiles
  instead of publishing duplicate loop engines. Multi-agent delivery is intentionally outside this
  catalog and remains the responsibility of PairRoom.

- Added `lark-cli`, one lean 飞书/Feishu/Lark entry point that replaces the official
  skill-per-domain context fan-out with eight conditionally loaded domain references. It
  preserves explicit user/bot identity continuity, reference-backed fast paths with targeted
  command-drift discovery, raw OpenAPI fallback, mail/send confirmation, untrusted-content
  handling, and high-risk write gates.

### Changed

- Merged the standalone `trace` route into `analyze` as a causal-investigation mode, preserving competing hypotheses, falsification, and discriminating probes while removing one overlapping routing surface.
- Made `autopilot` and `deep-interview` model-native by default for ordinary single-session work. Their generated state runtimes remain available as opt-in control planes for resumability, cross-session handoff, formal audit, or other cases where durable state materially helps.
- Per-skill contract modules are now targeted and optional. Validation still rejects orphaned modules, while prompt-only semantics move to `SKILL.md` and evaluations instead of requiring one brittle phrase-checking module per skill.
- Registered the reviewed high-risk targeted-contract subset so accidental module deletion fails validation, removed exact resident-policy phrase fixtures from the `autopilot` and `deep-interview` contracts, kept runtime/schema checks mechanical, aligned `autopilot` with explicit-only TDD routing, and made deep-interview research conditional on decision value.
- Workflow control state now uses the skill-neutral
  `.agent-workflows/<workflow>/<session>/<id>.json` contract. Runtime mutations use atomic
  replacement, single-generation backups, command locks, monotonic revision/CAS checks, bounded
  inputs/history, token-owned locks, explicit Git worktree/branch binding, portable path segments,
  and a non-Git `--root` fallback. Read-only discovery has no filesystem side effects; newest-first
  `list --limit`, `--latest`, `doctor`, `recover`, `unlock`, and explicit `rebind` cover normal resume
  and repair without manual JSON editing.
- Deterministic workflow output is compact by default, with opt-in `--full` state and bounded
  `history --tail`, avoiding repeated full-history context growth. State loads validate complete
  workflow schemas and derived counters/formulas without leaking tracebacks. Plan/spec and JSON input
  paths must exist inside their allowed roots and may not traverse symlinks.
- Restored topology-aware deep-interview behavior: active-component × dimension scoring, original
  greenfield/brownfield ambiguity weights, weakest-target rotation, ontology stability, challenge
  modes, stall escalation, round guards, explicit waivers, pressure-pass/content gates, and separate
  `crystallize → approve → complete` states with a verified spec digest.

- `lark-cli` domain references now act as a maintained command cache for stable, high-frequency
  operations. Known IDs and URLs normally take one business call; human-readable targets take at
  most one resolver plus the action. Broad help/schema preflight, duplicate discovery, and routine
  post-write readback are rejected by the catalog contract, while exact help/schema remains the
  fallback for real CLI drift and low-frequency APIs.
- `lark-cli` now treats already loaded instructions, domain references, successful command shapes,
  and help/schema output as a trusted session-local context cache. Related turns skip duplicate file
  reads while the exact contract remains present; context loss, a new domain, or real CLI drift
  reloads only the smallest missing part. Recipients, payloads, confirmations, `--yes`,
  `--confirm-send`, and idempotency keys remain transaction-scoped and are never inherited by a new
  logical action.

### Fixed

- Canonicalized the `skill-eval` Python executable before applying repository-boundary checks, so setup-python interpreter symlinks remain valid without allowing arbitrary executable escapes.
- Accepted platform aliases for the bound worktree root in workflow JSON and artifact paths while continuing to reject descendant symlink traversal and resolved paths outside the worktree.
- Prevented validation imports from writing `__pycache__` files that could contaminate installed-payload comparisons later in the same CI job.

### ⚠ Breaking

- The standalone `trace` install target is removed. Existing consumers must replace it with `analyze`, whose causal-investigation mode preserves the read-only hypothesis, falsification, and discriminating-probe workflow, and remove stale `trace` projections to prevent duplicate routing.

### Removed

- Removed six prompt-only keyword contracts (`analyze`, `trace`, `ai-slop-cleaner`, `best-practice-research`, `code-review`, and `prototype`). Executable, concurrency, release, Git-safety, and evaluation contracts remain.

## [v4.1.2] — 2026-07-26

### Fixed

- The release workflow no longer deadlocks against its own reusable validation call. `v4.1.1`
  derived validate.yml's concurrency group from `github.workflow`, which resolves to the *caller*
  inside a `workflow_call` and therefore evaluated to release.yml's own `release-<ref>` group; the
  called workflow queued behind a caller that never cancels, so no GitHub Release was published
  for that tag. The group is now a literal `validate-skills-<ref>`, and validation rejects both a
  `github.workflow`-derived group and any group shared with release.yml.

## [v4.1.1] — 2026-07-26

### Added

- Per-skill catalog contracts now live in `scripts/contracts/<skill>.py`, one module per
  `skills/<name>/`, discovered by filename. Validation now fails when a skill has no contract
  module or a module names a skill the catalog does not ship, so coverage cannot silently lapse.
- Dependabot keeps the SHA-pinned workflow actions and the pinned validation requirements moving.

### Changed

- `validate_skills.py` keeps only catalog-wide rules and shrank from 1558 to 510 lines; shared
  state and path constants moved to `catalog_core.py`. The flat module API is re-exported, so the
  regression suite and any external caller are unaffected.
- Both workflows now pin `actions/checkout` and `actions/setup-python` by commit SHA, cache the
  pinned pip requirements, and supersede an in-flight validation run for the same ref while never
  cancelling a tag run.
- `agent-scaffold` contracts now state that everything under `.agents/tools/` is a managed copy
  refreshed by `agent-scaffold upgrade`, not a hand-editable file.
- Validation runs on trunk pushes and pull requests instead of every branch push, so a PR branch
  no longer runs the full three-platform matrix twice. Validation rejects a reintroduced
  `branches: ["**"]`.

### Fixed

- Release-note extraction fixtures are now written byte-exact instead of inheriting `os.linesep`,
  and a CRLF changelog is covered explicitly so the LF release-note guarantee is enforced on
  every platform rather than only where the runner happens to translate line endings.

## [v4.1.0] — 2026-07-21

### Added

- `semver-release` now prefers changelog-backed, tag-triggered publication for a new release
  path, with a one-time adoption offer before changing an existing repository's release
  infrastructure.
- Release-note extraction now treats the complete repository tag as an opaque exact identity and
  fails closed on missing, duplicate, malformed, mismatched, calendar-invalid, or empty changelog
  sections. Executable fixtures cover stable, prerelease, prefixed, unprefixed, and custom tags.
- This catalog now dogfoods that model: stable and numbered-prerelease `v` tags invoke the full
  reusable validation matrix, extract notes from the tagged commit, publish the GitHub Release
  only after validation, and verify the resulting tag, notes, and release state without replacing
  an existing release.

### Changed

- Release guidance now keeps the repository's semantic version separate from its complete tag
  format and preserves retained generated-notes, tag-only, external-handoff, direct-publisher,
  and direct-forge models instead of silently migrating them.

### Fixed

- `agent-scaffold` authority-document budgets now support character limits alongside advisory
  line limits, allowing managed contracts to keep semantic source lines without enforcing hard
  wrapping.

## [v4.0.1] — 2026-07-19

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

[Unreleased]: https://github.com/sean2077/skills/compare/v5.0.0...HEAD
[v5.0.0]: https://github.com/sean2077/skills/compare/v4.1.2...v5.0.0
[v4.1.2]: https://github.com/sean2077/skills/compare/v4.1.1...v4.1.2
[v4.1.1]: https://github.com/sean2077/skills/compare/v4.1.0...v4.1.1
[v4.1.0]: https://github.com/sean2077/skills/compare/v4.0.1...v4.1.0
[v4.0.1]: https://github.com/sean2077/skills/compare/v4.0.0...v4.0.1
[v4.0.0]: https://github.com/sean2077/skills/compare/v3.0.2...v4.0.0
[v3.0.2]: https://github.com/sean2077/skills/compare/v3.0.1...v3.0.2
[v3.0.1]: https://github.com/sean2077/skills/compare/v3.0.0...v3.0.1
[v3.0.0]: https://github.com/sean2077/skills/compare/v2.0.0...v3.0.0
[v2.0.0]: https://github.com/sean2077/skills/compare/v1.0.0...v2.0.0
[v1.0.0]: https://github.com/sean2077/skills/releases/tag/v1.0.0
