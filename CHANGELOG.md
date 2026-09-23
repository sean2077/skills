# Changelog

All notable changes to this project are documented in this file. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking

- Retire `work-protocol`, `best-practice-research`, `tooling-conventions`, and `project-docs-organizer` (12 → 8 catalog skills), including coordination runtime, inventory checker, generated payloads, contracts, and retired routing candidates. Preserve existing consumer installations/state until their owner completes or explicitly migrates them; no aliases, automatic uninstall, state migration, or replacement controller is introduced.

- Retire `ralph` from the catalog (13 → 12 skills), including its loop runtime, references, source, contract, generator target, and route alias. Use native goals or the host/project workflow for new continuation tasks; exact attempt/stall/plateau semantics remain project-owned, not claimed as native-goal parity. Finish or explicitly abort active runs with the original installed runtime before removing it; preserve existing state and evidence, with no automatic migration or consumer uninstall.

### Added

- Make full `agent-scaffold` setup adopt and fill project-specific test-quality guidance: independent oracles, contractual observations, risk-based levels, real/double boundaries, sensitivity and honest baselines. Preserve existing runners/layouts, coverage gates and scoped TDD policy; no framework, mandatory test-first or managed AGENTS expansion is introduced.
- Expand `agent-scaffold` full initialization/upgrade to adopt and fill project-owned documentation, command, verification, source, and environment guidance. Respect existing layouts and project customizations; use current successors instead of recreating deleted/merged templates, without growing the managed AGENTS block or adding a layout registry.
- Add explicit installer-report scope (`harness-assets`, project guidance `not-assessed`), real installer layout/read-only/idempotence preservation tests, scaffold decision probes, and bounded task-outcome fixtures. These checks distinguish runtime installation from Agent-authored guidance and do not claim live-host/model effectiveness.

### Fixed

- Accept a directory reader route (`[docs](website/content/)`) in the scaffold guidance fixtures. The traversal read every local link as a file, so naming a documentation owner by directory failed the oracle as a missing artifact; a heading fragment on such a route and a missing file still fail, and workspace/symlink containment is unchanged.
- Hold `agent-scaffold`'s new upstream MIT attribution in its targeted contract. Generic validation only routes a shipped `NOTICE.md`, so the notice could be emptied to a stub with every catalog check green — the same drift already closed for `tdd` and `domain-modeling`.

### Changed

- Separate reusable project testing conventions from explicit TDD execution. `tdd` reads project guidance first and keeps compact, independently installable fallback material plus RED/GREEN evidence requirements. The scaffold testing adaptation ships its own upstream attribution notice; neither skill depends on the other.
- Preserve shared state-safety coverage by moving lock, concurrency, binding, session, strict-JSON, and compact-history regressions from the retired loop to `deep-interview`; remove loop-only tests and the now-unused score helper, then regenerate the approval payload. Keep `work-protocol` ownership semantics and historical release/audit records unchanged.

- Refresh repository documentation against v8: distinguish catalog sources from consumer installation destinations, clarify canonical/generated ownership, preserve dated evidence, and align release guidance with main reachability, supported tags, and schema-2 local analysis.
- Make maintainer and evaluation examples fail safely, retain failure output, and require an explicit observed cache condition instead of assuming cold-cache execution. Keep all catalog routes, runtime behavior, historical records, and optional-review boundaries unchanged.

## [v8.0.0] — 2026-09-23

### Added

- Add a `lark-invented-syntax` task fixture whose oracle reads the mock's call log: an undocumented argument shape fails it, and the run must observe the data through a documented command. The `lark-cli` ban on inventing flags, methods, enums, IDs, URLs, or parameter shapes had no executable or fixture coverage, and its contract deferred to a live-eval suite that contains no such case.
- Add an opt-in, project-owned `skill-verifier` subagent with generated Claude Code/Codex projections. It reviews skill changes, artifacts and evaluation evidence using existing checks, returns findings without editing reviewed sources, and adds no catalog skill or automatic approval gate.

### Fixed

- Reject ambiguous previous-stable tag identities when deriving promotion release notes; same-commit build-metadata aliases remain valid and use a deterministic label, while disagreement reports `release-notes-base` attention and leaves the notes base unset.
- Respect up-to-three-space ATX heading indentation in changelog extraction, including target/duplicate detection and section boundaries, while preserving code examples and atomic failure behavior.
- Reject duplicate JSON keys and non-finite constants in task answers and captured records, sharing the runner's decoder so contradictory Lark counts cannot pass by last-key-wins parsing.
- Remove Bash from the project `skill-verifier` Claude tool allowlist and make the role review source and captured evidence without command execution. The parent supplies pinned diffs and runs proposed checks in an authorized disposable environment; configured capabilities are not a claim of verified live-host isolation.
- Check this repository's own managed host hooks against the scaffold assets. Their entries are `merge-json` assets, so the copy-drift gate skipped them and deleting the trunk-guard wiring from `.claude/settings.json` left every check green; the gate now compares the effective managed entries too, and asserts the project-root fallbacks on `hook-paths.py`, the file Codex invokes directly.
- Describe `hook-launcher.sh` as what it is: a dispatcher for the two managed Bash hooks. Four reference pages offered it to project-owned Bash hooks, which it rejects with exit 2, blocking every edit wired that way; project-owned hooks source `hook-common.sh`.
- Verify that a release tag's commit is reachable from the trunk before publishing. The tag workflow's identity assertion is true by construction on a tag push, so any branch could push a tag and publish a GitHub Release; `publishing.md` already lists trunk reachability as required completion evidence.
- End an extracted release-notes section at a level-one heading as well as a level-two one, so a separator such as `# Older releases` is no longer pulled into the notes with the next section's content.
- Match a candidate tag to the repository workflow's accepted tag pattern before pushing it: a valid SemVer prerelease label can still be unsupported by that workflow, and a pushed tag cannot be moved.
- Route and protect skill attribution notices. A shipped `NOTICE.md` must now be linked from `SKILL.md` (otherwise it is an orphan reference) and a linked one must exist, so `domain-modeling`'s upstream MIT notice can no longer be dropped, left unreachable, or hollowed out while every catalog check stayed green. A targeted contract holds its provenance lines and the complete license text, as `tdd`'s attribution contract already did for its own notice.
- Treat an inventory candidate path as a literal Git pathspec. A file name containing `[`, `*`, or `?` previously matched other tracked files, so the checker could read a different file's mode and pass over an unregistered executable Python command. The scaffold gate reads its own asset modes the same way now.
- Let `ralph` `abort` end a run that has an opened round. The unrecorded attempt is now discarded instead of leaving `round` ahead of the recorded history, so the recovery path `resume-and-recovery.md` names no longer fails with `corrupt_state`.
- Check both source and `Move to` destination paths in patch hooks, including cross-worktree moves and authority-document budget notifications. Refresh the installed hook from its canonical scaffold asset.
- Reuse a valid installed scaffold profile when the flag is omitted; mark new installations explicitly and require a choice for ambiguous legacy state. Fresh installs still default to guarded worktrees.

### Changed

- Remove inventory validator dependencies on fixture captions, local variable names, and exact syntax-check prose. Keep payload/retirement checks and require the inventory suite in an enabled CI step, so a statically disabled job or step no longer satisfies the gate; the shell suite owns behavior verification and now covers the `PYTHON_BIN` override, an incompatible override, and every conventional directory name of the neutral reverse scan.
- Replace tag-name/year guessing with explicit local-analysis boundaries in `semver-release`. JSON schema 2 reports `analyzed` rather than `ready`, inventories out-of-model tags without assigning meaning, declines to infer an initial target from unmatched history, and checks a release branch only when supplied from repository policy. Consumers of schema 1 must update their success-status handling.
- Make the Lark syntax fixture check its requested count as well as mock argument validity. Keep the task-only prompt neutral, reject help-only and single-message evidence, cover invalid flags/identities/IDs, and remove catalog checks that merely matched oracle wording and test names. Writable mock logs remain bounded evidence, not tamper-proof execution records or model-performance measurements.
- Replace the Python hook resolver's source-string assertions with behavior tests for host-root precedence, primary and linked-worktree install layouts, real Git fallback, and resolution failures. Managed host-hook parity remains checked by the scaffold gate.
- Name the `round_pending` stage in the `ralph` result list, state that the `project-docs-organizer` metadata convention does not apply to a format that owns its frontmatter (such as `SKILL.md`), and point a route inside a managed block at its generator in `domain-modeling`'s migration steps.
- Replace wording/heading-based skill checks with payload inventories and actual Git/mock-release outcome tests. Workflow display names and comments no longer determine publication or installer validation.
- Add opt-in task fixtures for mixed-index commits, specification preservation, document moves, ambiguous mock writes and actual RED/GREEN traces, with no-skill/brief/pinned-skill controls and honest unknown-cost reporting.
- Apply selected Anthropic/OpenAI authoring principles: task-specific reasons and examples, risk-proportionate freedom, optional cold-reader checks, and concrete terminology boundaries. Keep all 13 routes and existing approval/authorization semantics.
- Track installer, host, Lark and evaluation evidence independently; distinguish documentation, simulated payload, actual-host and task-outcome claims without introducing new orchestration or game workflows.


## [v7.0.0] — 2026-09-21

### Breaking

- Retire `autopilot`, `analyze`, `prototype`, `ai-slop-cleaner`, and generic `code-review` from the catalog (18 → 13 skills), including their payloads, catalog entries, and evaluation suites. The duplicate `autopilot_state.py` controller is also removed. Finish active old runs with the prior installed runtime; use host/project workflows for new work. Previously installed copies need explicit consumer/global cleanup; unrelated same-name skills are not removed.
- Replace deep-interview's scoring/topology engine with `agent-workflow/deep-interview/3` exact-file specification approval. Questions and document format remain caller-owned. Legacy `/2` runs are preserved and rejected rather than silently converted; use the old runtime to finish them or a new ID with fresh approval.
- Change work-protocol to `agent-work/v2`: caller-chosen owner IDs and nonterminal phases, generic `writer`/`reviewer` workspaces, and no mandatory brief, plan, integrator, risk heuristic, or retry count. Existing v1 tasks stay untouched and require their original runtime; new tasks use new IDs.
- Evidence input now accepts `--payload-file`; ordinary output is a compact sequence/kind/hash receipt. Use `--full` when the complete event is needed.

### Security and correctness

- Require consistent, correctly typed verification signals at task completion, rejecting contradictory results and boolean/string exit codes. Recheck current workspace scope and review snapshots before entering `done`; terminal tasks permit ownership housekeeping and cleanup but not additional work.
- Hash original UTF-8 specification bytes, including LF/CRLF, and bind recorded approval to that digest. Bound artifact reads even if the file grows after its initial size check.
- Reserve internal coordination event kinds and avoid force-removing workspaces during failed registration, preserving concurrent work.
- Reject terminal-label near-misses such as `Done` or `done.` as caller-chosen phases, so they cannot skip the completion gate or terminal protection.
- Keep path claims a parallel-writer requirement: a sole writer owning its whole worktree completes without inventing a catch-all claim.

### Changed

- Move the concise feedback-verification, revision-freshness, authority, and real remote-deliverable checks from the retired review/delivery skills into the existing composition guide, without new routes, aliases, or resident AGENTS instructions.
- Remove retired candidates from evaluation guidance and update surviving experiment cases to route to the host (`none`) while preserving their workflow and non-selection requirements. Check candidate metadata and suite route references against the shipped catalog; keep workflow synonyms whose canonical workflow still exists.
- Remove historical workflow disclaimers, fixed question/report/method-card requirements, and repeated process rules throughout skill guidance, references, repository docs, and scaffold templates.
- Let Lark operations use needed help/schema and verification without fixed call budgets or failure-first discovery; retain identity, confirmation, and ambiguous-write protections.
- Replace reference heading/naming/load-sentence checks with payload-contained reference reachability, and remove prose-only method-card and retired-rule fixtures while retaining executable runtime and publication tests.
- Mark past audits as historical and keep current guidance separate from review narratives; refresh the dogfooded scaffold contract from its source template.

### Fixed

- Restore three boundaries lost as collateral to the prose removal: the `lark-cli` ban on inventing flags, methods, enums, IDs, URLs, or parameter shapes; the enumerated `tdd` prohibition on weakening, deleting, skipping, quarantining, or regenerating a legitimate failure to reach GREEN; and the ban on inventing a verifier result, now retained in the composition guide.
- Validate Markdown links after an unterminated code fence instead of treating the rest of the document as an example, and use the containment check's own `relative_to`/`ValueError` form in the orphan report rather than the Python 3.9-only `Path.is_relative_to`. The regression suite covers the unterminated-fence case.
- Align the `docs/architecture.md`, `docs/compatibility.md`, and `README.md` link text with the renamed design-principles and documentation-maintenance pages.

## [v6.2.0] — 2026-09-20

### Added

- `agent-scaffold` now installs repository-level LF text defaults and CRLF batch-file exceptions in both profiles, seeds `.editorconfig` only when absent, and verifies effective runtime attributes and tracked EOL bytes. Existing project attributes/editor settings, binary and exact-byte exceptions, Git configuration, and staged work are preserved; normalization remains an explicitly authorized separate migration.

### Fixed

- Give each host its own scaffold-owned hook command instead of one shell-agnostic string. Claude Code and Grok both inject `CLAUDE_PROJECT_DIR` and expand `${VAR}` in `command` themselves, so `.claude/settings.json` anchors on `"${CLAUDE_PROJECT_DIR}/.agents/tools/hooks/hook-paths.py"` with no bash `${VAR:-default}` modifier — Grok does not implement that modifier, and on Windows PowerShell the leftover text named an undefined variable and collapsed to `/.agents/...`, which Python opened as `C:\.agents\...`. Codex injects no project-root variable and expands nothing, so `.codex/hooks.json` keeps the plain cwd-relative `python -X utf8 .agents/tools/hooks/hook-paths.py --guard|--budget` and carries no `$` for its PowerShell to empty. The `python -c` launcher this replaces was host-agnostic but unreadable, duplicated across four files, and its Codex branch was dead: Codex never sets those variables, so it only ever fell back to the cwd-relative path. `upgrade` still converges the `python -c`, `${CLAUDE_PROJECT_DIR:-.}`, and split-quoted commands as managed identities. Host expansion is now modeled explicitly in the shell tests and in the E2E, which dispatches the anchored command from a drifted cwd after the host expands it.

- Invoke scaffold-owned Claude/Codex/Grok hooks through a `python -c` launcher that reads `CLAUDE_PROJECT_DIR` or `GROK_WORKSPACE_ROOT` in-process and has no `$` for the shell to expand. Grok on Windows PowerShell does not apply bash `${VAR:-default}`; the previous `"${CLAUDE_PROJECT_DIR:-.}/.agents/..."` command expanded to empty and Python opened `C:\.agents\tools\hooks\hook-paths.py`. The trailing `.agents/tools/hooks/hook-paths.py --guard|--budget` keeps reconciler and light-profile identity, and `upgrade` converges the quoted-placeholder commands as managed identities.

- Quote the entire `hook-paths.py` script path in scaffold-owned Claude/Codex/Grok hook commands (`"${CLAUDE_PROJECT_DIR:-.}/.agents/tools/hooks/hook-paths.py"`). POSIX shells already expanded inside one quoted word; Windows PowerShell/CreateProcess split the previous `"${CLAUDE_PROJECT_DIR:-.}"/.agents/...` form so Python received the repository directory and failed with `can't find '__main__' module`. Light-profile filtering and `upgrade` identity matching ignore those quotes, and `upgrade` converges the split-quoted commands as managed identities.

- Follow up PR #9 without reverting its routing or answer-leakage fixes: parse Lark discovery metadata as YAML, reject triggers present only in comments, and remove new exact-English safety/exception gates while preserving all installed safety instructions. Add verifier-tested confirmation, untrusted-content, and file-boundary scenarios rather than treating prose matches as enforcement.
- Restore outcome checks to four docs/tooling evaluation cases that had become route-only when optional decision-depth fields were removed. Require the requested comparison, preserved decisions, and reconciled consumers without imposing an output template; keep project-required records exact. The live intention suite now has 107 scenarios; no live-model pass is implied.

- Restore decisive routing tokens dropped by the native-first pass (`飞书`/`Larksuite`, `CONTEXT.md`/`CONTEXT-MAP.md`, add/move/rename, analyze/code-review destinations, and the AGENTS.md/CLAUDE.md exclusion) and make the lark-cli other-interface exclusion unambiguous.
- Keep lark-cli resident identity, confirmation, untrusted-data, and path-containment rules mechanically checked; domain fast paths now defer to those identity/uncertainty exceptions instead of forbidding needed preflight.
- Stop live-eval adapter prompts from assigning expected observation values, alias candidate skill names onto canonical workflows, and drop optional decision-depth/ceremony keys that the revised skills no longer teach.

- Recognize clear specification approval by context rather than rejecting short acknowledgements; adaptive wording-only edits no longer invalidate approval, while persistent runtime digests remain exact. Stop forcing migration interviews for already coherent release pipelines.
- Let selected Lark CLI tasks check unclear identity/contracts before consequential actions instead of enforcing a call quota or failed-write-first discovery. Do not treat contradictory exit/envelope signals as success or override an explicitly selected connected interface.

- Fixed an `agent-scaffold` E2E fixture that had silently degraded into a no-op: it corrupted the managed `AGENTS.md` block by replacing one specific resident sentence, so any legitimate rewording made the injection match nothing and left "verify rejects managed AGENTS block drift" passing vacuously. The fixture now corrupts the block positionally and asserts that the mutation really changed the file.

- Corrected trunk-guard diagnostics that required `.worktrees/` creation even when a user or workbench had already supplied a linked task worktree; primary-checkout protection is unchanged.

- Anchored the scaffold-owned Claude/Codex hook command's script path on `${CLAUDE_PROJECT_DIR:-.}` so `hook-paths.py` is found when the host's hook `cwd` drifts off the project root (a `cd`, a worktree, or a temp directory), which previously failed with `can't open file '.../.agents/tools/hooks/hook-paths.py': No such file or directory`. The `:-.` floor keeps the cwd-relative path on hosts that export no project-root variable (Codex/Grok run hooks from the project root), so they are unchanged; `upgrade` converges the prior relative-path commands as managed identities.

- Require valid baseline execution, trigger, and scope before accepting an evaluation comparison; reject historical false-green pairs while allowing a functioning baseline to fail the task oracle.

- Made live routing evaluations reject nonzero host exits, ambiguous/non-finite JSON, normalized-key collisions, escaped candidate files, incomplete usage, and boolean/number equality false positives; preserve observed failure usage and mark unknown measurements explicitly.
- Count cached input and whole-call model usage without double counting, and measure adapter wall time rather than labeling API duration as elapsed time. Old and new token measurements require fresh paired runs.

- Skip authority-document budget work unless a payload path is `AGENTS.md` or `CLAUDE.md`, and skip per-file Git identity probes for edits already inside a linked worktree.

### Changed

- Audited all 18 catalog skills against current native-host capabilities and revised 15 entrypoints. Remove duplicated process/reporting templates, routine decision-record requirements, redundant reference reads and hypothesis/smell-pass quotas; retain project-required evidence, explicit test-first discipline, authorization, and durable runtime contracts.
- Make existing decisions and still-valid verification reusable across skill boundaries. Clarify selective installation, Claude's bundled/custom review name collision, and native skill visibility controls without adding a router, dependency, or global host setting.
- Replace changed resident prose-pinning assertions with payload/interface checks and scenario coverage. Expand live-host intention probes from 9 suites / 56 cases to 15 / 103, without claiming that manifest validation proves model efficacy or token savings.

- Reduced the `agent-scaffold` managed `AGENTS.md` block from 6,808 to 3,059 rendered characters (63 → 32 default-profile lines, 49 → 26 light-profile lines) while keeping every costly-to-miss rule resident: `done`'s ff-only push, the prohibition on merging or cleaning up externally managed worktrees, the canonical-contract statement that a greenfield install cannot get from project prose, and equal cross-language terminology names with no forced language. Explanatory prose, glossary field formats, budget parameters, topology authoring, and projection inventories remain in the existing conditionally loaded references.

- Replaced `agent-scaffold` substring fixtures that only restated managed-block prose with structural and generated-drift checks, as the harness constraint policy requires. The gates now assert required section anchors, exactly one marker pair, a resident size ceiling, and terminology load targets, and a new check reconciles this repository's `AGENTS.md` managed block against the installer's own rendered template. Resident wording is review-owned, so legitimate rewording no longer breaks CI, while a hand-edited managed copy fails closed.

- Made the `agent-scaffold` managed contract heading host-neutral (`## Agent Harness` instead of naming Claude Code + Codex): the block governs every Agent working in the repository regardless of host, while the body still identifies `.claude/` and `.codex/` as generated host projections. `upgrade` refreshes the installed heading; product support claims elsewhere remain dual-host specific.

- Separated session entry, task checkout, and lifecycle ownership in `agent-scaffold`: prefer task-local implementation/review sessions while retaining primary-checkout coordination and project-owned user preferences; reuse external worktrees without a new mode, controller, or automatic cleanup. Added branch-local harness and PR/MR handoff guidance, refreshed the vendored contract, and wired real-Git entry-path regressions into the platform matrix.

- Added lightweight document-metadata guidance to `agent-scaffold`, `project-docs-organizer`, and `spec-writing`: optional flat `status`/`updated` fields and context-aware reading, with conventions and extensions left to project Agents rather than a universal schema or lifecycle gate.

- Strengthened native `autopilot` composition with approved-decision reuse, bounded evidence handoffs, capability/cost-aware delegation, integrated review, and verified remote delivery; no new skill or mandatory state/controller was added.
- Extended `code-review` to evidence-first feedback triage and revision freshness while preserving reviewer-only authority; aligned `tdd` discovery with explicit user or project policy and bounded external research by decision value.
- Replaced TDD sentence/keyword quotas with distribution and attribution invariants, retaining generic catalog validation and adding live routing cases rather than claiming prose matching proves behavior.

- Made scaffold-owned Claude/Codex hooks invoke `python -X utf8 "${CLAUDE_PROJECT_DIR:-.}"/.agents/tools/hooks/hook-paths.py --guard|--budget` directly, dropping the Git-alias plus Bash launcher from the Edit/Write hot path. `hook-launcher.sh` remains installed for project-owned Bash hooks. Upgrade replaces the previous Git-alias commands as managed identities.
- Reviewed the Lark command cache against official `lark-cli` v1.0.93 on 2026-09-04: `calendar +get` does not include attendees or rooms (`+list-attendees` is the attendee path), share-token joins use `calendar +join-event`, official meeting coverage includes `lark-meeting`, and the documented sheets surface stays on `+` shortcuts after the legacy command surface was removed. `apps +cache-clear` and cwd-relative file paths remain the agent-facing safety boundary.

## [v6.1.0] — 2026-09-04

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
- Reduced reference duplication without changing load boundaries: the `project-docs-organizer` numbering enable gate is hosted once, `agent-scaffold` budget numbers and override variables live only in `authority-docs.md`, the `agent-scaffold` retrofit reference no longer restates the plan/apply workflow, and `autopilot`/`deep-interview` persistent-runtime references defer stop conditions to their resident hard rules.
- Clarified in `agent-scaffold` that `scripts/check-agent-scaffold.sh` is this repository's CI guard, not an installed asset, and matched `tooling-conventions`' stale-path search example to fixed-string matching.
- Routed general defect review from `ai-slop-cleaner`'s reviewer-only mode to `code-review`, and scoped `analyze`'s two evidence rankings to their modes so explanation and causal investigations no longer carry conflicting ladders.


### Added

- Added consumer skill-selection guidance, a dated whole-catalog audit, on-demand composition/feedback references, and review/TDD plus delivery-boundary evaluation cases with explicit measurement limits.

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
- Documented `deep-interview` persistent-mode gates that previously existed only in the runtime: `crystallize` requires at least one recorded `pressure_pass` round, every answer must carry one of the four provenance tags, the `gate` exit-4 wording accounts for waivers, and `--depth`/`--threshold` gate values are published.
- Corrected `work-protocol` state documentation: `blocked` is resumable rather than terminal, only `test`/`verify`/`verification`/`ci`/`quality-gate` evidence kinds count toward the `done` gate, exit classes `5`/`6` are listed, and forced workspace removal evidence records the reason and forced flag.
- Documented `autopilot`'s `abort --reason` path to the `aborted` terminal in the persistent-runtime reference.
- Fixed a stale `semver-release` pointer that sent readers to `SKILL.md` for created tag forms now defined by the prerelease increment rules, added the missing alpha increment rule, and surfaced the extractor's fail-closed contract in its `--help` text.
- Added a `code-review` routing exclusion so read-only explanation or causal investigation without a change set routes to `analyze` on the always-resident surface.


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

[Unreleased]: https://github.com/sean2077/skills/compare/v8.0.0...HEAD
[v8.0.0]: https://github.com/sean2077/skills/compare/v7.0.0...v8.0.0
[v7.0.0]: https://github.com/sean2077/skills/compare/v6.2.0...v7.0.0
[v6.2.0]: https://github.com/sean2077/skills/compare/v6.1.0...v6.2.0
[v6.1.0]: https://github.com/sean2077/skills/compare/v6.0.0...v6.1.0
[v6.0.0]: https://github.com/sean2077/skills/compare/v5.0.0...v6.0.0
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
