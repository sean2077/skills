# Skills Repository Language

This file is the canonical glossary for repository-specific concepts. It defines language, not implementation, workflow, or architecture; follow the owning sources for those details.

## Canonical term languages

- `en`

## Language

### Skill catalog

**Catalog skill**:
An independently installable Agent Skill that belongs to this repository's published catalog and is maintained under `skills/<name>/`.
_Avoid_: public skill, bundled skill, project skill

**Project skill**:
A repository-local Agent Skill consumed through this repository's own harness and excluded from the published catalog; project skills live under `.agents/skills/<name>/`.
_Avoid_: private catalog skill, internal catalog skill

### Harness ownership

**Agent harness**:
The repository-local Claude Code and Codex support system whose authoritative project assets live under `.agents/` and whose host-facing surfaces live under `.claude/` and `.codex/`. "Harness" is acceptable after the scope is clear.
_Avoid_: framework, agent runtime

**Source**:
An authoritative project file that is edited directly.
_Avoid_: original, master copy

**Projection**:
A host-facing symlink or generated file derived from a **Source** and not edited directly.
_Avoid_: copy, mirror

**Scaffold runtime**:
Runtime files installed and refreshed by **agent-scaffold** rather than edited in the target repository.
_Avoid_: project tooling, harness source

### Agent authority

**Authority document**:
An `AGENTS.md` file whose instructions govern Agent work for its repository scope; the root file is the repository-level contract and nested files define local differences.
_Avoid_: prompt, readme, context file

**Managed block**:
The marker-bounded section of `AGENTS.md` owned and refreshed by **agent-scaffold**, while surrounding project prose remains project-owned.
_Avoid_: generated AGENTS.md, scaffold-owned AGENTS.md
