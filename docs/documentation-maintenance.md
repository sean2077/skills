# Documentation maintenance policy

This repository treats documentation as an executable product surface: skills route work, references carry command contracts, templates are installed into other repositories, and README examples are copied directly by users.

## Document classes and ownership

| Class | Canonical role | Change rule |
|---|---|---|
| `README.md` | Catalog orientation, safe install examples, navigation | Summarize and route; do not duplicate host or maintainer detail. |
| `AGENTS.md` / `CLAUDE.md` | Maintainer entry-point contract | Keep lean; move rationale and volatile detail into `docs/`. |
| `docs/compatibility.md` | Host, installer, trust, and verification claims | Date and source volatile external facts. |
| `docs/harness-constraint-policy.md` | Decision rule for mechanical controls | Keep model- and tool-neutral unless a boundary requires a concrete example. |
| `skills/*/SKILL.md` | Resident routing, invariants, and shortest safe workflow | Load-bearing only; link depth directly. |
| `skills/*/references/*.md` | On-demand procedures and command facts | One topic per file; update the exact recipe and its safety/verification boundary together. |
| `skills/*/assets/**` | Installed templates | Treat as product source; reconcile dogfood copies and generated projections in the same change. |
| `CHANGELOG.md` | Historical release record | Add current corrections under Unreleased; do not rewrite old behavior as though it was always true. |

## Evidence classes

1. **Repository-derived facts** — skill count, paths, generated ownership, CI pins, and command names must come from the same commit as the edit. Prefer existing validators and manifests over prose.
2. **External stable contracts** — specifications and durable path rules should cite the official specification or product documentation.
3. **External volatile facts** — current releases, flags, trust flows, host discovery, and platform limitations require an official source and a verification date. Avoid “latest” when a tested pin is the real invariant.
4. **Historical facts** — preserve release context. Correct a historical error explicitly rather than silently normalizing old entries to current behavior.

## Claim rules

- Do not infer runtime compatibility from Agent Skills format conformance, an installer target list, a plugin/catalog manifest, or successful parsing alone.
- Distinguish **validated**, **installer-tested**, **host-wired**, **behavior-tested**, and **not certified**. State the exact layer.
- Give volatile claims a date or a stable version boundary. When the installed runtime is the source of truth, document the targeted drift-recovery path instead of preflighting every request.
- Avoid universal and exhaustive wording unless a deterministic inventory or test actually proves it.
- Keep one authoritative home for each durable fact. Other documents summarize and link to it.

## Command examples

- Treat every copy-paste command as an interface. Verify option scope, quoting, working directory, identity, destructive confirmation, and expected output against current implementation or official documentation.
- Quote shell globs (`'*'`) and keep user values in data/argv positions rather than shell syntax.
- Mark version pins as pins. Do not label them latest unless release lookup is part of the same change.
- For risky writes, keep preview, confirmation, execution, and verification semantics together; do not let a shorter example bypass the surrounding safety contract.

## Change workflow

1. Fix the repository commit used as the evidence baseline.
2. Inventory all affected entry points, references, templates, dogfood copies, and command snippets.
3. Compare internal claims with manifests, scripts, tests, and workflows from that commit.
4. Verify changed external facts against primary sources and record the date/version boundary.
5. Update the canonical page first, then repair summaries and routes; remove duplicated detail.
6. Run catalog validation, targeted tests, link checks already owned by the repository, and any real CLI/host smoke test required by the changed claim.
7. Add an Unreleased changelog entry that names corrected behavior and any migration impact.
8. Report what was verified, what was intentionally unchanged, and any remaining host/user-policy boundary that cannot be asserted by repository tests.

Do not add phrase-only CI checks for prose claims. Mechanical validation should own inventories, links, schemas, generated parity, and executable behavior; source review and dated evidence own volatile external facts.
