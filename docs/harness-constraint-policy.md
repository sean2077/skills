# Harness design principles

Design each skill around a useful outcome, the reasoning or tools that help achieve it, and the boundaries that protect the user's work. Keep instructions that change decisions; let the Agent adapt question order, investigation depth, delegation, and presentation to the task.

## Choosing guidance and machinery

Use prose for judgment and scripts for observable state or repeatable operations. A deterministic check is valuable when it catches a consequential failure directly and earns its implementation and maintenance cost.

Examples include Git/index preservation, exact release identity, publication ordering, source/projection drift, path containment, concurrent ownership, revision conflicts, evidence integrity, and executable verification. Protect those behaviors through parsing, execution, adversarial fixtures, and generated-parity checks. Matching an English sentence establishes its presence, not the behavior it describes.

Evaluate uncertain behavioral or efficiency claims with representative tasks. Compare applicable baseline and treatment evidence, including token, latency, and integration costs. Static checks remain useful evidence of structure and deterministic behavior; they are not measurements of model performance.

## Delegation and persistent state

Choose delegation and persistence according to separate needs. Isolation or parallelism can help a bounded task; durable state can support recovery, handoff, or audit. A reusable project subagent can encode stable instructions, tools, models, or sandbox settings.

Keep one integration owner and one active writer per mutable surface. Pass workers the relevant objective, authority, input revision, and acceptance. Return findings and verification that the owner needs to integrate the work.

Choose the state owner whose semantics fit the task. Native continuation may suffice; repository-owned runtimes provide explicit phases, revisions, bindings, receipts, bounded attempts, and leases. Once selected, follow that runtime's transitions and recovery rules. Coordinate ownership when composing runtimes rather than letting competing controllers mutate the same state.

## Catalog validation

Catalog-wide checks protect frontmatter, routing metadata, reference reachability, manifests, installation payloads, and generated inventory. Descriptions have a repository-owned 320-character, single-line budget because every installed route contributes discovery context. Preserve decisive triggers and distinguish confusable routes.

Targeted modules under `scripts/contracts/` cover payload-specific interfaces and executable boundaries. Register retained modules in `scripts/contracts/__init__.py`; the registry catches missing and orphaned modules. Keep prose adaptable instead of treating headings, templates, question counts, or retired-policy disclaimers as machine interfaces.

Published skill payloads contain regular files and directories. Installers may create target symlinks after their preflight; the payload inventory must remain complete and portable.

## Skill boundaries and maintenance

Compare new or overlapping routes by user intent, mutation authority, evidence, and handoff. Merge when a shared skill remains coherent; keep distinct read-only, authoring, and external-publication boundaries visible. Put detailed references where readers can reach them from the skill entry point.

Maintain current guidance in its owning document. Historical audits record decisions and evidence at their review date. Compatibility claims belong in [compatibility.md](compatibility.md); documentation ownership and evidence practice are in [documentation-maintenance.md](documentation-maintenance.md).
