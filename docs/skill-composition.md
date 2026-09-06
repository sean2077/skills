# Choosing and combining skills

This guide is for catalog consumers choosing the smallest useful installation and workflow. It is not another always-loaded router. Each catalog skill remains independently installable; the linked skill owns its operational rules.

## Start with the requested outcome

| Outcome | Choose | Boundary worth keeping |
|---|---|---|
| Explain repository behavior or investigate a cause | [analyze](../skills/analyze/SKILL.md) | Read-only; not review of a concrete patch |
| Compare external technical approaches | [best-practice-research](../skills/best-practice-research/SKILL.md) | Source-backed recommendation, not implementation authority |
| Test local feasibility | [prototype](../skills/prototype/SKILL.md) | Disposable evidence, not production readiness |
| Resolve user-owned requirements | [deep-interview](../skills/deep-interview/SKILL.md) | Approval of meaning is not permission for external side effects |
| Write settled requirements/design for people | [spec-writing](../skills/spec-writing/SKILL.md) | Preserve settled decisions; don't reopen an interview by default |
| Deliver an authorized task end to end | [autopilot](../skills/autopilot/SKILL.md) | Native loop first; load specialists only for actual gaps |
| Perform explicitly required test-first work | [tdd](../skills/tdd/SKILL.md) | User or applicable project policy must require it; tests alone are not a trigger |
| Clean up while preserving behavior | [ai-slop-cleaner](../skills/ai-slop-cleaner/SKILL.md) | Authoring, not a general defect review |
| Review a concrete change or received findings | [code-review](../skills/code-review/SKILL.md) | Verify claims and revision; review alone does not authorize edits |
| Enforce a mechanically bounded verifier loop | [ralph](../skills/ralph/SKILL.md) | Explicit attempts/stall/resume semantics, not every multi-step task |
| Coordinate durable writers and ownership | [work-protocol](../skills/work-protocol/SKILL.md) | Leases, CAS, integrity, and isolated writers only when materially needed |
| Create a scoped local commit | [conventional-commit](../skills/conventional-commit/SKILL.md) | Commit, not push, PR, merge, or release |
| Plan/publish an authorized release | [semver-release](../skills/semver-release/SKILL.md) | Version, tag, and actual publisher policy are explicit boundaries |
| Install or repair the repository Agent harness | [agent-scaffold](../skills/agent-scaffold/SKILL.md) | Managed sources/projections, not product workflow orchestration |
| Define or evolve project language | [domain-modeling](../skills/domain-modeling/SKILL.md) | Active terminology changes, not a mandatory pass before ordinary work |
| Organize project documentation | [project-docs-organizer](../skills/project-docs-organizer/SKILL.md) | Information placement/ownership, not rewriting settled specifications |
| Design project-owned command boundaries | [tooling-conventions](../skills/tooling-conventions/SKILL.md) | Tool governance, not installing a complete Agent harness |
| Operate Feishu/Lark | [lark-cli](../skills/lark-cli/SKILL.md) | Service-specific identity, permissions, and side-effect checks |

## Compose only at a real boundary

A small known fix needs implementation and verification, not interview, research, prototype, persistence, and parallel review by default. A complex delivery may need clarification for one unresolved decision and a source comparison for another; neither should repeat evidence already established by the other.

For end-to-end work, keep one delivery owner. The [autopilot composition reference](../skills/autopilot/references/composition-and-handoff.md) owns specialist dispatch, compact delegation, capability/cost selection, integration, and transfer. It describes optional capabilities, not mandatory sibling installations or a second runtime. A specialist returns its result to the existing owner.

For feedback on a patch, use the [review feedback reference](../skills/code-review/references/feedback-triage.md). Receiving a comment and applying it are different actions: validate the claim first, and edit only when authorized. A review is tied to the inspected revision, not to an indefinitely reusable approval label.

Do not add `ralph` merely because a task takes several attempts, or `work-protocol` merely because more than one Agent exists. Execution topology and durable state are separate choices. Prefer serial native execution when coordination costs more than it saves; keep genuine ownership, revision, and publication boundaries intact.

## Install selectively; measure the result honestly

Install the routes you actually use with the commands in the [README](../README.md#install). Full instructions and references are on-demand, but every installed description still participates in discovery. No new bundle, universal dispatcher, or mandatory dependency is needed for this guide.

Format validation, routing probes, and real delivery success are different evidence. See the [live evaluation guide](../evals/agent-skills/README.md) before interpreting a passed manifest or a model's stated intention as improved engineering performance. The [2026-09-06 audit](audits/2026-09-06-harness.md) records the keep/change decisions and research behind this revision.
