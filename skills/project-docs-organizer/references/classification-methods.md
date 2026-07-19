# Documentation Classification Methods

Read this when project evidence supports several possible information-architecture boundaries.
Treat these as reasoning lenses, not required categories or directory names.

## Reader role

- **Signals**: readers have different prerequisites, permissions, vocabulary, or outcomes.
- **Ask**: which material does each reader need without traversing another role's concerns?
- **Fits when**: user, integrator, contributor, maintainer, or operator routes rarely overlap.
- **Fails when**: most material is shared and role-based grouping would duplicate it.
- **Axis role**: primary for genuinely separate reader journeys; otherwise an entry-point index.
- **Micro-example**: operators start from recovery tasks while integrators start from contracts;
  both link to one canonical authentication explanation.

## Task or journey

- **Signals**: readers search by goal, workflow, sequence, support question, or incident stage.
- **Ask**: what is the reader trying to accomplish, and what is the safest next step?
- **Fits when**: documentation primarily guides repeatable work or an end-to-end journey.
- **Fails when**: workflows change frequently or hide stable domain and ownership boundaries.
- **Axis role**: primary for task-led manuals; secondary for workflows that cross domains.
- **Micro-example**: a release journey links preparation, publication, and recovery guidance
  while each underlying command remains defined once in reference material.

## Domain capability, ownership, and language

- **Signals**: capabilities have distinct decision owners, lifecycles, handoffs, or meanings for
  the same term.
- **Ask**: which capability owns this fact or decision, and where is its language valid?
- **Fits when**: a long-lived, domain-rich project needs cohesive ownership boundaries.
- **Fails when**: it merely mirrors teams, services, or source directories without domain evidence.
- **Axis role**: primary when capabilities own complete documentation lifecycles; otherwise a
  glossary, context map, or ownership annotation.
- **Micro-example**: billing and entitlement use “account” differently, so each owns its meaning
  while shared onboarding routes to both canonical definitions.

## Product, subsystem, or interface surface

- **Signals**: readers navigate by stable products, features, components, APIs, CLIs, or SDKs.
- **Ask**: does the reader's mental model follow this surface rather than the source tree?
- **Fits when**: the documented machinery and its public contracts are stable and recognizable.
- **Fails when**: grouping exposes incidental implementation layout or churns with refactors.
- **Axis role**: primary for stable product or reference surfaces; otherwise a component index.
- **Micro-example**: CLI and SDK references remain distinct surfaces but link to one shared
  explanation of the system's authorization model.

## Content purpose or information type

- **Signals**: readers need to learn, complete work, understand concepts, or look up facts.
- **Ask**: what must the reader do with this content now?
- **Fits when**: mixed tutorials, how-to guidance, explanation, and reference compete in pages.
- **Fails when**: named frameworks become mandatory top-level boxes regardless of reader needs.
- **Axis role**: usually secondary within a product or domain; primary can fit a simple,
  single-product documentation set.
- **Micro-example**: a first-success lesson links to a concise flag reference rather than
  repeating the flags inside the lesson.

## Lifecycle or authority

- **Signals**: stable guidance, proposals, decisions, generated outputs, deprecated material,
  and retained history have different owners or trust rules.
- **Ask**: which source is authoritative now, and what retention value justifies older material?
- **Fits when**: readers risk following active drafts, generated copies, or superseded guidance.
- **Fails when**: status buckets become junk drawers or archives hide unresolved ownership.
- **Axis role**: normally a secondary trust boundary; primary only for record-centric systems.
- **Micro-example**: an active specification cannot compete with the released contract, and a
  generated page identifies the source that owns future updates.

## Framework boundary

Diátaxis and DITA inform the content-purpose lens; domain-driven design informs capability,
language, and ownership questions; product content models inform surface and task lenses. Use
their questions where they fit, but never require a project to reproduce a named framework.
