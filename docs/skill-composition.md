# Choosing and combining skills

Each catalog skill is independently installable and owns its operational guidance. Choose the routes that add useful methods or controls to your host and project. Host capability and invocation details are described in the dated [compatibility notes](compatibility.md).

## Start with the requested outcome

| Outcome | Choose | Boundary worth keeping |
|---|---|---|
| Explain repository behavior or investigate a cause | [analyze](../skills/analyze/SKILL.md) | Read-only; not review of a concrete patch |
| Compare external technical approaches | [best-practice-research](../skills/best-practice-research/SKILL.md) | Source-backed recommendation, not implementation authority |
| Test local feasibility | [prototype](../skills/prototype/SKILL.md) | Disposable evidence, not production readiness |
| Resolve user-owned requirements | [deep-interview](../skills/deep-interview/SKILL.md) | Approval of meaning is not permission for external side effects |
| Write settled requirements/design for people | [spec-writing](../skills/spec-writing/SKILL.md) | Preserve settled decisions; don't reopen an interview by default |
| Deliver an authorized task end to end | [autopilot](../skills/autopilot/SKILL.md) | Own the authorized outcome, integration, and verification |
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
| Operate Feishu/Lark through the selected CLI | [lark-cli](../skills/lark-cli/SKILL.md) | Service-specific identity, permissions, and side-effect checks |

## Combining routes

Combine skills when the task crosses their boundaries. An implementation may need a source comparison for an uncertain dependency or clarification of an unresolved requirement. Reuse settled decisions and applicable verification rather than restarting the work.

Keep one delivery owner. Specialists return their findings to that owner; shared writers coordinate their scope. The [autopilot composition reference](../skills/autopilot/references/composition-and-handoff.md) covers delegation and handoff. The [review feedback reference](../skills/code-review/references/feedback-triage.md) covers validating received findings before authorized corrections.

Choose persistent state for the semantics needed: bounded attempts in `ralph`, exact-file approval in `deep-interview`, or durable leases and workspace evidence in `work-protocol`. `autopilot` reuses the selected host or project state rather than starting another controller. Temporary delegation and persistence are separate choices.

## Installation and evidence

Use the [README installation commands](../README.md#install). Installed descriptions contribute discovery context; bodies and references are loaded as needed.

The [evaluation guide](../evals/agent-skills/README.md) explains measured baseline/treatment comparisons. Historical review records are in the [September 20 audit](audits/2026-09-20-native-first.md) and [September 6 audit](audits/2026-09-06-harness.md).
