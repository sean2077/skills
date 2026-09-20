# Native-first skill audit — 2026-09-20

## Scope and evidence

Base: `de02c169cf095ac351f5b996a1b8c71f75e8b5d7` (main, including the September 17
managed-AGENTS reduction). Reviewed all 18 catalog entrypoints, their dispatch/authority
boundaries, affected on-demand references, prose-pinning validators, composition/compatibility
claims, and the live-evaluation adapter/manifests. This is a prompt and boundary audit, not a
claim to have exhaustively re-audited every unchanged runtime algorithm or every Lark API.

The guiding distinction is **missing capability versus repeated procedure**. Native competence
can replace a generic itinerary; it cannot prove a Git snapshot, approve a specification, own a
lease, or confirm a remote publication. The existing [constraint policy](../harness-constraint-policy.md)
already makes that distinction; this revision removes remaining contradictions rather than
adding another policy framework.

Primary documentation checked on 2026-09-20:

| Source | Relevant evidence | Local implication, not a vendor guarantee |
|---|---|---|
| [OpenAI: rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | Old scaffolding can overconstrain stronger models; routing descriptions and instructions should be focused. | Remove generic step quotas and boilerplate, retain task-specific constraints, and measure locally rather than assuming efficacy. |
| [OpenAI skills](https://learn.chatgpt.com/docs/build-skills) | Discovery is metadata-first and budgeted; full instructions are selected on demand. | Shorter descriptions and selective installation matter separately from entrypoint size. |
| [Claude skills](https://code.claude.com/docs/en/skills) | Bundled review/debug/loop/run/verify, local name precedence, and native visibility/usage tools. | Avoid duplicate workflows and document the `code-review` collision instead of silently renaming a public skill. |
| [Claude best practices](https://code.claude.com/docs/en/best-practices) | Native subagents/continuation and verification; excessive instructions and indiscriminate review findings can create waste. | Keep native ownership, meaningful evidence, and actionable review rather than extra mandatory passes. |

These are dated documentation facts, not a live Codex/Claude compatibility certification.
The [compatibility matrix](../compatibility.md#native-overlap-and-visibility-2026-09-20) owns
host-specific details. The Lark recipes retain their documented September 4 / v1.0.93 command
review boundary; this pass changes routing and safety reasoning, not every command's version.

## Whole-catalog decisions

All 18 installation names remain stable. Fifteen entrypoints change. No new catalog skill,
global router, profile schema, runtime state, or sibling installation dependency is introduced.

| Skill | Decision | Capability/boundary retained; burden removed |
|---|---|---|
| `agent-scaffold` | Keep entrypoint/runtime | Native init is not evidence of equivalent source/projection reconciliation, ownership preservation, real symlinks, or external-worktree lifecycle. Preserve the recent AGENTS simplification. |
| `ai-slop-cleaner` | Simplify | Keep behavior preservation and adequate verification. Combine related smells coherently; remove one-smell-per-pass and ritual approval of a sufficient alternative verifier. Unverified material risk is still not green. |
| `analyze` | Simplify | Keep read-only cross-file/causal evidence. Remove mandatory six-heading output, hypothesis count, and a next-probe ritual after the question is resolved. |
| `autopilot` | Thin delivery overlay | Prefer native execution/resume and reuse current decisions/evidence. Keep scope, one writer, integrated verification, honest review and actual PR readback. Durable state needs explicit missing semantics, not task length. |
| `best-practice-research` | Simplify | Keep primary citations, freshness, repository fit and meaningful alternatives. Remove fixed reporting sections and redundant source sweeps. |
| `code-review` | Simplify, retain public name | Keep revision-bound trigger/consequence/evidence and reviewer-only authority. Do not repeat a native review or full valid verifier run; no finding quota or six-field ceremony. Document intentional native command shadowing. |
| `conventional-commit` | Narrow exemption | A fully specified message-only request needs no Git preflight. Actual commits retain attached-HEAD/operation, exact hunk/index/tree/parent, and unrelated-state protection. |
| `deep-interview` | Fix approval semantics | Clear approval refers to the complete presented specification, not specific magic words. Adaptive cosmetic changes preserve meaning; material changes need renewed approval. Formal runtime file digests remain exact even for whitespace. |
| `domain-modeling` | Simplify | Keep one owning definition, multilingual equivalents and atomic routes. A term addition no longer opens a topology study or requires both references. |
| `lark-cli` | Narrow routing and relax unsafe optimization rules | Respect a selected non-CLI interface; URLs alone are not a trigger. Permit needed identity/schema checks before writes, not only after errors. Keep identity continuity, scope/ACL distinction, confirmations, idempotency and untrusted-data safety; contradictory result signals cannot be success. |
| `project-docs-organizer` | Simplify | Preserve canonical content, retention, links and project-owned structure. Remove routine decision artifacts, whole-tree inventory for a local move, forced method reads and reapproval of delegated choices. |
| `prototype` | Simplify | Keep bounded disposable experiments, independent oracle, real/mock distinction, inconclusive results and cleanup. Remove the fixed itinerary/report without treating a spike as production delivery. |
| `ralph` | Keep entrypoint/runtime | Native conversational iteration/scheduled loops are not the same contract as mechanically bounded attempts, stalls, scores and terminal state. Optional, not a route for every iterative request. |
| `semver-release` | Remove migration interview | Retain an established safe release flow without demanding a current-versus-preferred debate. Keep deterministic version analysis, exact tags, release authority, clean snapshot and actual downstream completion. |
| `spec-writing` | Simplify | Keep authoritative meaning, exact constraints, human-readable behavior and acceptance. Do not reopen settled technology choices or require an interview to draft visible open questions. |
| `tdd` | Simplify explicit discipline | Keep user/project opt-in, independent oracle, valid RED, general GREEN and safe refactor. Behavior cards and duplicate evidence reports are optional; real failing-before-fix evidence is not. |
| `tooling-conventions` | Simplify | Keep public/installed consumers, state/failure/rollback and safe command contracts. No mandatory Job Boundary → Contract Profile → record ceremony or inventory for routine maintenance. |
| `work-protocol` | Keep entrypoint/runtime | Native subagents alone do not establish durable CAS leases, evidence-chain integrity, isolated writer claims and commit-fixed review. Do not activate just because two Agents exist. |

### Merge, delete and addition candidates

**Do not merge unlike authority boundaries.** `analyze`/`code-review` share read-only tools but
answer different questions and bind different evidence; `code-review`/`ai-slop-cleaner` differ
in mutation authority. `deep-interview` resolves and approves meaning while `spec-writing`
preserves supplied meaning; merging would recreate approval gates in ordinary writing.
Docs organization, terminology ownership and command governance manipulate different contracts.
They can share decisions without sharing one mandatory workflow.

**Do not collapse the three optional runtimes.** Delivery state, bounded verifier attempts and
durable writer coordination are distinct acceptance contracts. Deleting them because native
subagents or resume exist would remove capability without demonstrated equivalence. Their
scripts and generated projections are unchanged; native delivery is the default instead.

**Do not add another generic planning/debugging/review/verification skill.** Current native
hosts and existing routes already cover those mechanisms. Use an actual missing project
contract to justify future additions. Keep the private evaluator private; it checks pinned
baseline/treatment isolation and evidence, not just interactive skill authoring.

**Avoid name churn masquerading as simplification.** Native alternatives are a reason to install
or enable fewer skills, not to break all existing paths. In Claude Code, installing this
`code-review` replaces bundled `/code-review`; bundled `/review` remains native. The README
now makes the collision visible before an optional full-catalog installation.

## Constraint classification

Removed/relaxed: fixed headings and hypothesis/smell-pass counts; mandatory standalone or inline
records for bounded work; repeated interviews/design comparisons; unconditional reference reads;
refreshing still-visible instructions; repeating still-valid verification; checking exact English
approval words; mandatory migration offers; CLI discovery allowed only after a failed attempt.

Retained: user/project authority, read-only versus authoring boundaries, real verifier evidence,
untrusted-content separation, no secret exposure, current revision and public API/consumer
integrity, external side-effect confirmation, exact Git/index/tag identity, formal digest/CAS/lease
semantics, generated-source parity, and non-destructive installer/worktree behavior.

Conditionally retained: project-required decision records, explicit test-first work, material
approval changes, extra reviewers where worthwhile, target smoke for actual target risk, formal
persistence where the host does not meet the required semantics. The existence of a cheaper
path is not permission to skip acceptance or safety.

## Iteration record

1. **Inventory and native overlap:** reviewed all routes against existing policy and current
   primary sources; retained prior September fixes and separated optional machine contracts
   from generic conversation instructions.
2. **Entrypoints and downstream references:** removed routine ceremony, then found that causal,
   TDD, documentation, tooling and domain references still reinstated it. Aligned these sources;
   preserved formal interview digest rules and domain-specific hazardous actions.
3. **Validation and adversarial scenarios:** found that exact-string validators and the live
   adapter's artifact vocabulary pinned old behavior. Removed the changed prose requirements,
   kept executable/payload/interface protections, and added scenarios for both sides of approval,
   validity, identity, permission and publication boundaries. Oracle metadata is still not sent
   to the model, and missing observations are not synthesized.
4. **Integrated review:** checked active links, catalog/manifest alignment, final diff, runtime
   parity and observed verification. Caught an over-broad changelog edit, limited the entries
   to Unreleased, and verified released history byte-for-byte against the base. Inspected
   unresolved risks rather than manufacturing more changes. The stopping criterion is no remaining identified medium/high-value issue in this
   inspected change, not a proof that every possible future improvement is exhausted.

## Static size and measurement limits

Measured across the 18 tracked `skills/*/SKILL.md` files, from the base above to this revision:

| Static measure | Before | After | Change |
|---|---:|---:|---:|
| Decoded description characters | 4,170 | 3,607 | −13.5% |
| Whole entrypoint Unicode characters | 77,435 | 59,473 | −23.2% |
| Whole entrypoint UTF-8 bytes | 77,522 | 59,509 | −23.2% |
| Physical entrypoint lines | 1,047 | 727 | −30.6% |

These are file measurements, **not model tokens, resident context in every host, or latency/cost
savings**. Full entrypoints are loaded selectively. Some safety-sensitive entrypoints grow
slightly to make exemptions unambiguous; reducing line count is not the acceptance criterion.
The larger audit and evaluation payloads are not installed skill prompts.

Live intention-probe coverage expands from 9 suites / 56 cases to 15 suites / 102 cases.
Manifest validation and deterministic adapter tests do not establish actual model compliance,
old/new task success, fewer tool calls, or token savings. No authenticated live-host trial is
claimed. Keep budget thresholds unchanged and use matched old/new revisions, host/model settings,
cache conditions, repeated representative tasks, real edits and real verifiers to measure those
outcomes later. The adapter remains a decision probe, not native discovery or full delivery.

Validation commands and observed outcomes belong in the PR's verification report; CI runs the
pinned official format check, installer payload smoke, platform matrix and executable regressions.
Do not interpret an unavailable local dependency or an unrun host trial as a pass.
