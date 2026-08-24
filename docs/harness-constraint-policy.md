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

## Native orchestration: select topology and state separately

Subagents, durable goals, and persistence runtimes solve different problems. Do not adopt one merely because another is useful. A task can use temporary workers without durable state, or a durable objective without workers. Select the smallest execution topology and the smallest state plane independently.

### Execution topology

- Default to one Agent. Coordination must earn its context, latency, and integration cost.
- Delegate only a bounded unit whose inputs, write scope, and acceptance evidence can be stated before dispatch. Isolation is most valuable for verbose read-only investigation, independent verification, or genuinely disjoint implementation.
- Keep one active writer at a time for each mutable file, path set, or external resource; hand off ownership explicitly. Parallel read-only analysis is cheap, while overlapping speculative edits are not.
- The primary Agent owns the objective, authority boundary, integration decisions, and final verifier. A worker returns conclusions, evidence, changed paths, observed verification, risks, and unresolved questions—not a transcript or a repeated copy of the task.
- Create a project-owned custom subagent only when a repeated stable role or a versioned tool, model, reasoning, or sandbox boundary justifies durable configuration. Prefer an ephemeral host subagent for one-off work.

### State and control plane

- Use the native session loop when ordinary conversational context is sufficient.
- Use a host-provided durable objective or goal when work needs continuation or resume but does not need repository-owned phase, revision, binding, receipt, or stall state.
- Use a skill runtime only when its explicit machine-state semantics materially improve recovery, auditability, bounded retries, or handoff. Once started, it is the sole controller for the state it owns.
- Use `work-protocol` only when coordination state itself must survive: multiple isolated writers, one lease owner, commit-fixed review, evidence integrity, or high-risk cross-session delivery. Native subagents or a long-running goal alone do not justify it.

If the host lacks a capability, degrade to the next simpler available shape rather than emulating the host with another prompt framework. Never nest retry or ownership controllers around the same work.

## Hybrid workflows

Some skills benefit from both modes. Keep the native mode as the default and make persistent state opt-in when interruption, multiple writers, formal audit, or high consequence makes it valuable. The runtime may become authoritative only after it is explicitly started; it must not create work solely to justify its own state.

## Contract selection

Catalog-wide validation should cover universal structure: frontmatter, routing metadata, references, installer manifests, generated payload inventory, and stale links.

Add a targeted `scripts/contracts/<skill>.py` module for executable or high-risk invariants that generic validation cannot express. Prompt-only skills do not need one by default. Register every intentionally retained targeted module in `scripts/contracts/__init__.py` so accidental deletion fails closed. Avoid substring fixtures that only restate prose; prefer parsing, execution, adversarial fixtures, or generator drift checks.

Reject missing registered modules and orphaned contract modules, but do not require one module per skill.

Always-resident routing metadata is a catalog-wide cost and selection boundary. Keep every published `description` on one physical line and within the repository's 320-character budget, retaining the decisive positive trigger and only the exclusions needed to distinguish adjacent routes. Reject normalized duplicate route descriptions mechanically; evaluate semantic selection quality with real-host positive, negative, and confusable cases rather than adding phrase quotas.

Published skill source trees may contain only regular files and directories. A skill runtime may create target symlinks after its documented preflight, but the installable payload itself must not carry symlinks or special filesystem entries that ordinary file inventories can omit.

## Documentation and compatibility claims

Documentation needs two different controls:

- Use deterministic checks for repository-owned structure: skill/manifests parity, frontmatter, references, generated templates, local links, and executable examples that can run safely.
- Use dated primary-source review for external host paths, trust models, installer flags, releases, and platform limitations. A substring assertion cannot prove a volatile product fact.

Never promote format conformance, installer discovery, or a manifest into a universal host-support claim. State the verified layer and leave untested hosts explicitly unclassified. Keep those claims in [`compatibility.md`](compatibility.md) and follow [`documentation-maintenance.md`](documentation-maintenance.md) rather than duplicating volatile facts throughout resident skill instructions.

## Skill addition and merge gate

Before adding a new skill, compare it with existing routes:

- Does its frontmatter describe a distinct user intent rather than a different internal technique?
- Would combining it as a mode preserve a coherent mutation, authority, and evidence boundary?
- Does treatment evaluation through a real host adapter show benefit over the baseline after token and latency cost? Manifest validation or a fake adapter proves only protocol plumbing.
- Is the full body truly on-demand, with only routing and hard invariants resident?

Merge skills when their triggers, evidence model, side-effect boundary, and handoff are substantially the same. Keep them separate when one mutates and the other is read-only, one performs external side effects, or their verifier/authority boundaries differ.
