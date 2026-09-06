# Composition and handoff

Read this only when delivery needs a specialist, delegated work, review feedback, or a transfer. This is guidance for the existing native loop, not another controller, required artifact, or installation dependency.

## Select the missing capability, not a workflow chain

Use only the row that resolves the current bottleneck. Skill names identify optional installed capabilities; when one is absent, perform the bounded method directly. Do not install dependencies or block routine work merely to satisfy this table.

| Missing evidence or outcome | Bounded capability | Return to delivery with |
|---|---|---|
| Repository mechanism or cause is unknown | `analyze`: read-only investigation | Evidence path, competing explanations, discriminating probe |
| A technical choice depends on external practice | `best-practice-research` | Source-backed recommendation and assumptions to test |
| Local feasibility remains uncertain | `prototype`: authorized disposable experiment | Observed result and what it does not prove |
| User-owned requirements are unresolved | `deep-interview` | Settled decisions and explicit approval, not implied implementation authority |
| Decisions are settled but need a human-facing contract | `spec-writing` | Specification and observable acceptance, without re-interviewing settled points |
| Test-first is explicitly required by the user or project | `tdd` | Behavior-level RED/GREEN evidence; no new delivery loop |
| Authorized cleanup must preserve behavior | `ai-slop-cleaner` | Bounded diff and preservation evidence |
| A concrete change or received finding needs checking | `code-review` | Revision-bound findings, disputed claims, and verification gaps |
| An explicit local commit or release is requested | `conventional-commit` or `semver-release` | The authorized Git result; never infer release/merge authority from delivery |

Do not run every row sequentially. Analysis, research, and prototyping answer different uncertainties; interviews and writing have different decision authority. Reuse outputs while their scope, inputs, and revision remain valid. Load a reference only for the selected operation, not its entire directory.

## Delegate only work with a useful return boundary

Before a delegation, provide the objective, authorized read/write scope, relevant acceptance, fixed inputs/revision, available verification, and stop condition. A compact inline packet is enough. Link to existing evidence rather than copying transcripts or entire plans; include the decisive facts needed to interpret those links.

Keep one integration owner and one active writer per mutable surface. Do not send overlapping edits to workers merely because their task titles differ. Independent reviews may run read-only against the same fixed snapshot; they do not gain integration or publication authority. A helper returns findings or a bounded result to the existing owner, not a nested retry controller.

Choose capability for the actual uncertainty and consequence of error. Prefer a lower-cost execution path for well-specified, verifiable work; spend stronger reasoning on ambiguous planning or difficult review when useful. Honor user/provider settings, avoid hard-coded model rankings, and escalate on failed evidence rather than repeatedly retrying a cheaper path. No available subagents is a reason to execute serially, not to abandon the task or simulate independent review.

## Integrate, review, and converge

Verify the combined change, not just each worker's successful check. Inspect cross-file contracts and shared assumptions. When review is warranted, supply the acceptance and exact base/head or dirty-diff identity; the review must distinguish confirmed defects from preferences and unverified concerns.

For received feedback, validate the trigger against current code before editing. Fix confirmed in-scope defects; challenge incorrect claims with evidence; keep unresolved or out-of-scope issues visible. Re-run affected verification after a correction and invalidate claims tied to the old revision. Do not blindly implement comments, repeat already-dismissed findings without new evidence, or repeatedly ask the author to approve the author's own work.

For a broad iterative improvement request, keep a short issue ledger: value, evidence, disposition, and verification. Continue while an actionable material issue remains in the inspected scope. Stop when the last pass adds no such finding, acceptance evidence is current, and further changes would be speculative, cosmetic, or unauthorized. Report inspected boundaries and remaining uncertainty; never claim that all possible improvements are exhausted.

## Transfer only when continuation actually needs it

Return the objective/authority, branch or workspace and exact revision, completed changes, observed verifier results, unresolved decisions/risks, and the next executable step. Keep credentials and unrelated conversation out. Distinguish completed, blocked, and unverified work.

On resumption, re-read applicable repository instructions and compare the current revision and working state before trusting old evidence. A changed input invalidates only the affected assumptions/checks, not every settled decision. Use a native summary for a session transfer; repository-owned persistent state is reserved for the durable semantics selected in `SKILL.md`.
