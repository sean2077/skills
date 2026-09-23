# Project specification conventions

Use when `specs` is selected for full setup or maintenance. Establish durable project guidance,
not a requirement to write a PRD for every task. Adopt existing RFC/PRD/design homes, languages,
numbering, templates, external owners and source/generated relationships. Keep guidance
reachable from the project entry point without requiring this skill later.

The installed [specification guide](../assets/conventions/specs.md)
(`.agents/conventions/specs.md`, routed from the managed block) carries the generic daily rules:
status versus approval versus implementation, semantic preservation of identifiers, values and
normative strength, visible open decisions, observable acceptance, single concept owners and
retiring implemented plans. Do not restate them in project docs.

Record only useful project gaps: where specifications and design records live, what each owns,
how this project marks draft, approved intent and implemented behavior, where acceptance is
defined, and the threshold for needing a specification at all. A recent edit, merged file or
answer to one question is not automatically approval of the whole design. Do not invent
approval states or require a new approval system.

Initialize with supported project facts and a few concrete examples, not speculative product
designs or empty templates. During upgrades use the current successor of renamed/merged guides,
preserve equivalent rules, and fix verified drift within scope. Routine spec work then follows
the project guidance and the installed guide directly; it does not rerun scaffold or
automatically start an interview.
