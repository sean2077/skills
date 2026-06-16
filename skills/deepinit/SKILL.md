---
name: deepinit
description: Generate or refresh a tree of hierarchical AGENTS.md files across a codebase — one per significant directory, each tagged with a parent reference so the files form a navigable hierarchy — documenting what each directory contains, how it relates to the rest, and how an agent should work in it. Preserves hand-written sections on regeneration. Use when bootstrapping agent docs for a repo, mapping a codebase for AI agents, or refreshing stale AGENTS.md after the structure changes. Not for human-facing README/docs trees (use project-docs-organizer) or a single standalone CLAUDE.md.
allowed-tools: Read, Edit, Write, Grep, Glob
---

# Deep Init

Lay down a tree of `AGENTS.md` files — one per significant directory — so any agent dropped into the repo can answer "what is this directory, how does it relate to the rest, and how do I work in it" without re-deriving the whole codebase each time. `AGENTS.md` is the cross-agent convention (Claude Code, Codex, and others read it), so this map is portable rather than tied to one tool.

The full annotated template, a worked example, and the regeneration algorithm live in [`reference.md`](reference.md) — read it before generating a large tree or when an update merge is non-trivial.

## When To Use

Use this skill when the user wants to:

- bootstrap agent docs for a repo ("生成 AGENTS.md / init agent docs / map this codebase for AI agents")
- refresh stale `AGENTS.md` after files move, directories are added, or structure changes
- give agents a navigable, per-directory map of a medium-to-large codebase

Do not use it for:

- human-facing documentation systems — README and `docs/` trees (use `project-docs-organizer`)
- a single root `AGENTS.md`/`CLAUDE.md` with no hierarchy (just write that file directly)
- throwaway, generated, or vendored directories (see the skip list below)

## Core Concept: the parent-linked hierarchy

Every `AGENTS.md` except the repo root carries a parent reference as its first line:

```markdown
<!-- Parent: ../AGENTS.md -->
```

That single tag turns scattered files into one walkable tree, so an agent can climb from any directory up to the root for wider context:

```text
AGENTS.md                       ← root (no parent tag)
├── src/AGENTS.md               ← <!-- Parent: ../AGENTS.md -->
│   ├── src/api/AGENTS.md        ← <!-- Parent: ../AGENTS.md -->
│   └── src/utils/AGENTS.md      ← <!-- Parent: ../AGENTS.md -->
└── docs/AGENTS.md              ← <!-- Parent: ../AGENTS.md -->
```

The path is always relative to the file's own directory, so a child one level down points at `../AGENTS.md`. Generate **parents before children** so every reference resolves the moment it is written.

## Template

Keep each file to this shape. Drop sections a directory genuinely has nothing to say for; never pad with boilerplate.

```markdown
<!-- Parent: ../AGENTS.md -->        # omit this line on the repo-root AGENTS.md

# {Directory name}

## Purpose
One paragraph: what this directory holds and its role in the system.

## Key Files
| File | Description |
|------|-------------|
| `name.ext` | What it does and when an agent touches it |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `sub/` | What it holds (see `sub/AGENTS.md`) |

## For Agents
- Conventions, constraints, and gotchas to respect when editing here.
- How to test changes made in this directory.

## Dependencies
- **Internal:** other parts of the repo this relies on.
- **External:** key third-party packages.

<!-- MANUAL: notes below this line are preserved on regeneration -->
```

Anything below the `<!-- MANUAL: -->` marker is author-owned and must survive every regeneration untouched.

## Workflow

1. **Map the tree.** Walk the directory structure, skipping noise: `node_modules`, `.git`, `dist`, `build`, `out`, `target`, `.venv`, `__pycache__`, `coverage`, `.next`, `.nuxt`, `vendor`, and other generated or dependency directories.
2. **Pick the directories worth documenting.** A directory earns an `AGENTS.md` when it holds source, config, or assets an agent would read or edit. Apply the edge-case rules below to the rest.
3. **Order by depth.** List the survivors level by level (root, then level 1, then level 2, …).
4. **Generate parent-first.** For each directory, top-down: read its files, then write `AGENTS.md` filling the template from real content — accurate file roles, real subdirectory purposes, the conventions an agent must follow here, and actual dependencies. Add the parent tag (omit on the root). Independent directories at the same depth can be done in parallel if your host supports subagents; otherwise do them sequentially — but never a child before its parent.
5. **Update, don't clobber.** If an `AGENTS.md` already exists, read it first, preserve everything below `<!-- MANUAL: -->` verbatim, refresh the auto-generated sections to match the current files and subdirectories, and fix the parent path if the file moved.
6. **Validate the tree.** See the acceptance checks; fix orphans, broken parent paths, and gaps before reporting done.

## Edge Cases

| Directory | Action |
|-----------|--------|
| Empty | Skip — no `AGENTS.md`. |
| Only subdirectories, no files | Minimal file: `Purpose` + `Subdirectories` only. |
| Only generated / minified / vendored files | Skip. |
| Only config files | Short file describing what the config governs. |

## Acceptance Checks

Before claiming completion:

- A root `AGENTS.md` exists and has **no** parent tag.
- Every other `AGENTS.md` starts with a `<!-- Parent: -->` tag whose path resolves, and the tags chain to a single root (no orphans, no cycles).
- Every significant directory is covered; every skipped directory falls under the skip list or edge-case rules.
- Hand-written content below `<!-- MANUAL: -->` is preserved across regeneration.
- No `AGENTS.md` survives in a directory that no longer exists.
- Descriptions name real files and real responsibilities — no generic filler.
