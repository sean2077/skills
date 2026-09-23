# Project specification conventions

Use when `specs` is selected for full setup or maintenance. Establish durable project guidance,
not a requirement to write a PRD for every task. Adopt existing RFC/PRD/design homes, languages,
numbering, templates, external owners and source/generated relationships. Keep guidance
reachable from the project entry point without requiring this skill later.

Record only useful gaps: what a specification owns, how the project distinguishes draft,
approved intent and implemented behavior, and where acceptance is defined. A recent edit,
merged file or answer to one question is not automatically approval of the whole design.
Do not invent approval states or require a new approval system.

When writing/revising project specs, preserve exact identifiers, values, units, compatibility
windows, and normative strength (must/should/may). Keep material assumptions and open decisions
visible; do not resolve product questions through editorial wording. Reuse settled decisions
and explain a consequential change rather than silently broadening scope.

Describe the main behavior and responsibilities, including important failure/recovery paths
and observable acceptance. Make decision-bearing requirements traceable to their behavior and
verification using the project's own format; a small change may need only a sentence, not a
traceability matrix. Define concepts once and route to their owner. Summarize executable/schema
contracts rather than copying another authority, retaining exact details the spec itself owns.

Separate audiences or lifecycles only when needed. Keep working transcripts, test output and
historical debates out of the current reader narrative. A cold read with realistic implementation
or acceptance questions can expose missing context; it is optional and not another approval gate.

Initialize with supported project facts and a few concrete examples, not speculative product
designs or empty templates. During upgrades use the current successor of renamed/merged guides,
preserve equivalent rules, and fix verified drift within scope. Routine spec work then follows
the project guidance directly; it does not rerun scaffold or automatically start an interview.
