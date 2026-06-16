# Deep Init — Reference

On-demand detail for the `deepinit` skill: the annotated template, a worked example, the regeneration algorithm, and validation snippets. The resident `SKILL.md` is enough for small trees; read this before generating a large one or merging a non-trivial update.

## Annotated template

```markdown
<!-- Parent: ../AGENTS.md -->
```
First line on every non-root file. The path is relative to **this file's own directory**; a file one level below the root points at `../AGENTS.md`, one two levels down also points at `../AGENTS.md` (its parent is one directory up). The root file omits this line entirely.

```markdown
# {Directory name}
```
The directory's own name, not the repo's.

```markdown
## Purpose
```
One paragraph an agent can read in five seconds: what lives here and why. State the role in the system, not a file listing — the table below is the listing.

```markdown
## Key Files
```
Only the files an agent would actually open or edit. Skip lockfiles, snapshots, and generated output. Each row says what the file does **and** the situation in which an agent touches it ("the only place routes are registered", "edit this when adding a migration").

```markdown
## Subdirectories
```
One row per child directory, each ending with `(see \`child/AGENTS.md\`)` so the link to descend is explicit. Omit the section when there are no child directories.

```markdown
## For Agents
```
The highest-value section: the conventions, constraints, and gotchas specific to this directory, plus how to test changes here. This is where a directory earns its file — generic advice that applies repo-wide belongs in the root, not repeated in every leaf.

```markdown
## Dependencies
```
**Internal:** other parts of the repo this directory leans on (so an agent knows what it might break). **External:** the few third-party packages that matter here, not the whole manifest.

```markdown
<!-- MANUAL: notes below this line are preserved on regeneration -->
```
Everything after this marker is author-owned. Regeneration must copy it through byte-for-byte.

## Worked example

Root `AGENTS.md`:

```markdown
# acme-web

## Purpose
A task-management web app with real-time collaboration. React + TypeScript front end, a thin Node API, Postgres.

## Key Files
| File | Description |
|------|-------------|
| `package.json` | Scripts and dependencies; `pnpm dev` runs the app |
| `tsconfig.json` | Strict TypeScript config shared by all packages |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `src/` | Application source (see `src/AGENTS.md`) |
| `docs/` | Human documentation (see `docs/AGENTS.md`) |

## For Agents
- Strict mode is on; do not introduce `any`.
- Run `pnpm test` and `pnpm typecheck` before claiming a change works.

## Dependencies
- **External:** React 18, Vite, Prisma.

<!-- MANUAL: release runbook lives in NOTION, not here -->
```

Nested `src/api/AGENTS.md`:

```markdown
<!-- Parent: ../AGENTS.md -->

# api

## Purpose
HTTP layer: route handlers, request validation, and the Prisma client wiring. No business rules — those live in `src/domain/`.

## Key Files
| File | Description |
|------|-------------|
| `router.ts` | The only place routes are registered; add new endpoints here |
| `validate.ts` | Zod schemas; every handler validates input through these |

## For Agents
- Handlers stay thin: validate, call a domain function, serialize. Push logic into `src/domain/`.
- Integration tests in `__tests__/` hit a throwaway Postgres; run `pnpm test:api`.

## Dependencies
- **Internal:** `src/domain/` (business logic), `src/db/` (Prisma client).
- **External:** `zod`, `express`.

<!-- MANUAL: -->
```

## Regeneration (update mode)

When an `AGENTS.md` already exists, never overwrite blind:

1. **Read** the existing file.
2. **Split** at `<!-- MANUAL: -->`: the auto region (above) and the manual region (the marker line and everything below).
3. **Recompute** the auto region from the directory's current state — refresh `Key Files`, `Subdirectories`, and any moved-file references.
4. **Reattach** the manual region verbatim. If the old file had no marker, append a fresh `<!-- MANUAL: -->` line so future runs have a seam.
5. **Fix the parent tag** if the file moved to a new depth.
6. **Leave unchanged files alone** — if the directory's contents and structure are identical to what the file already describes, skip the rewrite so diffs stay meaningful.

## Validation snippets

Locate every file and check that parent references exist:

```bash
find . -name AGENTS.md -not -path '*/node_modules/*' -not -path '*/.git/*'
grep -rL '<!-- Parent:' --include=AGENTS.md . | grep -v '^\./AGENTS.md$'   # non-root files missing a parent tag
```

For each `<!-- Parent: ../AGENTS.md -->`, confirm the referenced file resolves from that file's directory, and that no `AGENTS.md` lingers in a directory that has since been deleted.
