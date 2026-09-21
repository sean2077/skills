# Documentation maintenance

Documentation serves consumers, repository Agents, maintainers, and installed skill users. Keep facts in their authoritative home and maintain the routes readers use to find them.

## Ownership

| Source | Responsibility |
|---|---|
| `README.md` | Consumer orientation, catalog, installation, and navigation |
| `AGENTS.md` / linked `CLAUDE.md` | Frequently needed repository instructions |
| `docs/skill-composition.md` | Choosing and combining catalog routes |
| `docs/architecture.md` | Product surfaces and source/generated ownership |
| `docs/development.md` | Maintainer commands, checks, generation, and releases |
| `docs/compatibility.md` | Dated installer, host, platform, and verification claims |
| `docs/harness-constraint-policy.md` | Design and validation principles |
| `docs/audits/*.md` | Historical review evidence and decisions |
| `CONTEXT.md` | Repository terminology |
| `CHANGELOG.md` | Pending changes and release history |
| `skills/<name>/SKILL.md` and references | Installed skill guidance and operational detail |
| Scaffold assets and runtime source | Generated/installed content; ownership map in architecture |

## Editing and reorganization

Choose organization from reader tasks and existing conventions. Keep authoritative facts together and use navigation for additional views. Scale inventories and planning to the change; preserve useful unique content when consolidating or removing pages.

Update changed guidance and its readers together: links, backlinks, templates, generated projections, manifests, and command examples. Run the affected catalog, link, generation, and behavior checks from the [development guide](development.md). Record user- or maintainer-visible changes under Unreleased.

## Evidence and freshness

Derive repository facts from the inspected revision, especially paths, generators, pins, counts, and commands. Cite first-party sources for external product contracts and bind changing claims to a review date or tested version. A pinned CI dependency is a tested pin, not a claim to be upstream latest.

Distinguish format validation, installer tests, host wiring, and observed host behavior. Keep historical findings tied to their date; record corrections in current guidance and Unreleased rather than rewriting past release history.

Use metadata when status or freshness helps readers interpret a document. Follow the project's convention; flat `status` and `updated` are useful starting fields. Interpret them alongside content, repository evidence, and user intent. See [document metadata](../skills/project-docs-organizer/references/document-metadata.md).

## Executable examples

Check working directory, scope, quoting, identity, effects, confirmation, and expected result. Quote shell globs such as `'*'`; prefix local installer paths with `./`. Keep preview, authorization, mutation, and verification clear for consequential writes.
