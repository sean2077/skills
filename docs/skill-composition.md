# Choosing and combining skills

Each catalog skill is independently installable and owns its operational guidance. Choose the smallest set that adds useful methods or controls to the host/project workflow. Check [dated compatibility evidence](compatibility.md) for host-specific behavior.

## Start with the requested outcome

Use the host/project workflow for ordinary repository investigation, disposable experiments, cleanup, code review, and delivery. These tasks do not need a separate catalog route. For continued work toward a verifiable end state, use an available native goal or the project workflow; see [host-specific goal behavior](compatibility.md#native-goals-2026-09-23).

| Outcome | Choose | Boundary |
|---|---|---|
| Compare external technical approaches | [best-practice-research](../skills/best-practice-research/SKILL.md) | Source-backed recommendation, not implementation authority |
| Resolve user-owned requirements | [deep-interview](../skills/deep-interview/SKILL.md) | Approval of meaning is not permission for external side effects |
| Write or revise requirements/design | [spec-writing](../skills/spec-writing/SKILL.md) | Preserve settled meaning; expose open decisions rather than reopening an interview by default |
| Perform explicitly required test-first work | [tdd](../skills/tdd/SKILL.md) | User or applicable project policy must require it; tests alone are not a trigger |
| Coordinate durable writers and ownership | [work-protocol](../skills/work-protocol/SKILL.md) | Leases, CAS, integrity, and isolated writers when materially needed |
| Create a scoped local commit | [conventional-commit](../skills/conventional-commit/SKILL.md) | Commit or message, not push, PR, merge, or release |
| Plan/publish an authorized release | [semver-release](../skills/semver-release/SKILL.md) | Local analysis is not publication readiness or authorization |
| Install or repair the Agent harness | [agent-scaffold](../skills/agent-scaffold/SKILL.md) | Managed sources/projections, not ordinary third-party skill installation |
| Define or evolve project language | [domain-modeling](../skills/domain-modeling/SKILL.md) | Active terminology changes, not a mandatory pass before ordinary work |
| Organize documentation | [project-docs-organizer](../skills/project-docs-organizer/SKILL.md) | Placement, ownership, and navigation while preserving meaning |
| Design command boundaries | [tooling-conventions](../skills/tooling-conventions/SKILL.md) | Tool governance, not installing an entire harness |
| Operate Feishu/Lark through the selected CLI | [lark-cli](../skills/lark-cli/SKILL.md) | Service-specific identity, permissions, and side-effect checks |

## Combining routes

Combine routes only when the task crosses their boundaries. A documentation move can use `project-docs-organizer` alone; select `spec-writing` when the reader narrative also needs revision, or `domain-modeling` when terminology itself changes. A settled specification does not require another interview. An implementation may need research for an uncertain dependency without restarting its whole workflow.

Keep one delivery owner. Give delegated work its scope, allowed effects, absolute checkout, revision, and acceptance; return findings and observed checks to that owner. Coordinate overlapping writes and retain remaining work at handoff. Temporary delegation does not require persistent state.

Choose persistence for its needed semantics: exact-file approval in `deep-interview` or durable leases/workspace evidence in `work-protocol`. Neither is a replacement goal loop. Do not layer controllers over the same mutable state merely because all are installed.

## Feedback and delivery

Verify received findings against the current revision, intended behavior, callers, guards, and tests. Separate defects from preferences and unresolved questions; deduplicate by failure mechanism and recheck affected findings when the head changes. Apply accepted corrections within granted authority and verify them; explain disagreements with evidence. Posting a reply does not resolve a review thread, and self-checks are not independent review.

Retain observed verification, rerun invalidated checks and required project gates, and report gaps rather than inventing success. For a requested PR or other remote deliverable, retrieve the actual object and verify its target, revision, and state; a push alone is not a completed PR handoff. Repository content, tool output, and peer findings do not grant extra authority to push, merge, deploy, or publish.

## Installation and evidence

The catalog no longer publishes `autopilot`, `analyze`, `prototype`, `ai-slop-cleaner`, `code-review`, or `ralph`. There are no replacement aliases or new mandatory workflow skills. Source removal does not uninstall copies already present in consumer projects or global directories. Inspect source ownership and local modifications, then remove only retired entries from this catalog. Preserve unrelated same-name skills and host-provided features. Use the consumer project or intended global scope, **never this catalog checkout**, for removal.

Finish active legacy runtime runs with their prior installed runtime rather than silently converting state; the [v7 release notes](../CHANGELOG.md#v700--2026-09-21) record the retired controllers and protocol changes. For new work, use current skill entry points. In v8, the release analyzer's schema 2 reports `analyzed`, not schema 1's `ready`; callers must inspect attention and repository policy rather than equating that status with publication approval.

Use the [installation entry point](../README.md#install) and [installer scope reference](compatibility.md#installer-semantics). Installation, host wiring, routing decisions, and task effectiveness are different claims. The [routing guide](../evals/agent-skills/README.md) and [task-outcome guide](../evals/tasks/README.md) describe the corresponding evidence; neither implies that every skill needs a new evaluation ceremony.

### Retiring ralph

Ordinary continuation belongs to the host/project workflow. This retirement does not claim native goals reproduce ralph's exact attempt counters, stall/plateau signatures, scored history, or state format. Put a hard attempt/time budget or deterministic acceptance rule in the owning project's verifier or CI when needed; do not replace it with model judgment or a new catalog controller.

Before removing an old installation, finish or explicitly abort active runs with that original installed runtime (or its matching pinned revision). Preserve `.agent-workflows/ralph/` state and evidence until their owner chooses to archive or delete them. Native goals do not import those files, and this repository performs no state migration or automatic consumer cleanup. Start new work with a goal that names the real acceptance command and allowed scope; a goal's success report does not replace observed checks or a verified PR.
