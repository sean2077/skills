# Harness constraint policy

Use this policy when adding, merging, or tightening a catalog skill. The goal is to preserve costly boundaries without turning model-capable reasoning into a scripted ceremony.

## Default rule

Prefer model-native reasoning and tool use for reversible, single-session work. Add a deterministic helper or semantic contract only when all of these are true:

1. The failure is observable in files, process results, state, or external-system evidence.
2. Missing the boundary has meaningful cost: irreversible side effects, concurrency corruption, security exposure, invalid publication, lost work, or non-comparable evaluation.
3. Conversation instructions alone cannot reliably preserve the state across the relevant boundary.
4. The check catches the failure directly instead of merely searching for wording that describes it.
5. The expected safety or repeatability benefit exceeds the runtime, maintenance, routing, and context cost.

A prose invariant belongs in `SKILL.md`. A behavior whose value is uncertain belongs in an evaluation. A script should own only machine state or a machine-checkable boundary.

## Boundaries to keep mechanical

Keep fail-closed code around:

- external side effects, authorization gates, release publication, and destructive operations;
- Git index/history preservation, exact tag/version calculation, and generated-artifact drift;
- concurrency, leases, compare-and-swap revisions, ownership, locks, and recovery;
- path containment, symlink traversal, identity continuity, secrets, and evidence integrity;
- executable verifier outcomes, repository isolation, changed-path scope, and comparable evaluation cost;
- platform or installer compatibility that can be exercised deterministically.

These are not substitutes for model judgment. They are the narrow control plane around state the model cannot safely infer or remember.

## Boundaries to leave model-native

Do not introduce a mandatory state machine merely to enforce:

- how many questions to ask in a normal interview;
- a fixed number of planning, retry, review, or reflection rounds;
- one universal output template for every task size;
- hypothesis generation, evidence synthesis, or proportional investigation depth;
- a standalone plan or decision record for a small, obvious, reversible change;
- exact phrases in a prompt-only skill when no executable invariant depends on them.

Use explicit outcome and safety boundaries, then let the current model choose the shortest adequate path.

## Hybrid workflows

Some skills benefit from both modes. Keep the native mode as the default and make persistent state opt-in when interruption, multiple writers, formal audit, or high consequence makes it valuable. The runtime may become authoritative only after it is explicitly started; it must not create work solely to justify its own state.

## Contract selection

Catalog-wide validation should cover universal structure: frontmatter, routing metadata, references, installer manifests, generated payload inventory, and stale links.

Add a targeted `scripts/contracts/<skill>.py` module for executable or high-risk invariants that generic validation cannot express. Prompt-only skills do not need one by default. Register every intentionally retained targeted module in `scripts/contracts/__init__.py` so accidental deletion fails closed. Avoid substring fixtures that only restate prose; prefer parsing, execution, adversarial fixtures, or generator drift checks.

Reject missing registered modules and orphaned contract modules, but do not require one module per skill.

## Skill addition and merge gate

Before adding a new skill, compare it with existing routes:

- Does its frontmatter describe a distinct user intent rather than a different internal technique?
- Would combining it as a mode preserve a coherent mutation, authority, and evidence boundary?
- Does treatment evaluation through a real host adapter show benefit over the baseline after token and latency cost? Manifest validation or a fake adapter proves only protocol plumbing.
- Is the full body truly on-demand, with only routing and hard invariants resident?

Merge skills when their triggers, evidence model, side-effect boundary, and handoff are substantially the same. Keep them separate when one mutates and the other is read-only, one performs external side effects, or their verifier/authority boundaries differ.
