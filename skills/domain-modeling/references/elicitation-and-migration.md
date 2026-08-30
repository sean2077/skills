# Elicitation and Migration

Read this only when domain boundaries or terminology are unclear, a young project needs owner input, or an existing glossary must be regrouped or split safely.

## Evidence before questions

Inspect available evidence first:

- product and architecture entry points;
- code modules, schemas, APIs, events, tests, and examples;
- existing glossary usage and repeated naming conflicts;
- ownership, release, or lifecycle boundaries;
- user language in the current task and prior approved specifications.

Repository structure is evidence, not authority. A folder name may suggest a candidate context but does not establish one.

## Focused early-project elicitation

When the project is young, ask only questions that distinguish the next topology decision. Useful questions include:

- What problem does the product solve, and for whom?
- Which actors and end-to-end workflows are already known?
- Which capabilities change or ship independently?
- Who owns each concept or source of truth?
- Does any word already mean different things to different people or subsystems?
- Which integrations expose externally fixed terminology?
- Which concepts must be understood together to make one safe change?

Use a small coherent batch, explain the ambiguity it resolves, and build on the answers. A broad requirements interview belongs in the project's requirements workflow; domain modeling asks only for the vocabulary and boundary evidence it needs.

If the user selected up-front modeling, continue until proposed contexts have defensible scopes and relationships. If the user selected incremental modeling, collect only enough information to place the current terms safely.

## Scenario probes

Challenge candidate terms and boundaries with concrete cases:

- Can part of an aggregate or request be changed independently?
- Which context decides whether an operation is valid?
- What happens when two contexts use the same noun?
- Which identity crosses the boundary, and who owns its lifecycle?
- Can one context complete its work while another is unavailable?
- Does a proposed shared term carry the same definition everywhere?

Cross-check answers against code and tests. Surface contradictions rather than silently choosing the user's wording or the implementation.

## Topology decision record

Before a material split, state:

- selected mode: up-front or incremental;
- current problem with the existing glossary;
- candidate contexts and evidence for each;
- relationships and one-owner assignments;
- unresolved terms or low-confidence boundaries;
- why headings are insufficient, or why they remain sufficient.

When evidence supports multiple materially different topologies, present the smallest credible options and a recommendation, then obtain owner direction before moving files.

## Atomic migration

1. Inventory every current concept, equivalent, avoided name, and inbound glossary link.
2. Cluster entries provisionally without changing their definitions.
3. Assign one owning destination per concept; leave uncertain entries where they are.
4. Create only context files that immediately receive real content.
5. Move complete entries, including all language equivalents and avoided names.
6. Create or update root `CONTEXT-MAP.md` with scopes and relationships.
7. Update project-owned `AGENTS.md`, nested routes, and active documentation links.
8. Remove superseded entries and headings after all routes resolve.
9. Search for duplicate definitions, stale paths, and names that now cross the wrong boundary.
10. Review the final diff for accidental semantic edits introduced during movement.

A topology migration should preserve definitions unless a term is being deliberately repaired in the same change. Separate pure movement from semantic changes in the report even when they share one patch.

## Safe fallback

When ownership cannot yet be resolved:

- keep the term in the current or root glossary;
- record the ambiguity in the task report or owning planning source, not as a fake glossary entry;
- avoid creating a temporary context that future Agents may mistake for settled authority;
- revisit the split when new workflows, ownership, or semantic collisions provide evidence.
