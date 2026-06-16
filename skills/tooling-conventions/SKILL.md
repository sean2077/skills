---
name: tooling-conventions
description: Govern a project's tools/ or scripts/ directory at scale. Classify each script by surface (public / installed / helper / break-glass / paused / legacy / package / native / template / vendor), aggregate commands by failure-domain rather than noun-domain, place new scripts via a decision tree, enforce a script contract (-h/--help + exit codes, secrets hygiene, atomic + idempotent writes), and keep a machine-readable surface manifest in sync via a reconciliation check. Use when adding, moving, or removing a tool/CLI script, auditing tooling sprawl, or setting up tooling governance for a large or growing repo. Ships manifest-check.sh and a lean manifest schema.
allowed-tools: Read, Edit, Write, Grep, Glob, Bash(git:*)
---

# Tooling Conventions

Keep a project's `tools/` (or `scripts/`, `bin/`) directory from rotting into a pile of top-level scripts nobody can route. The goal is **a gate on every increment**, not a one-time cleanup: each new or moved script gets classified, placed, contracted, and registered. Battle-tested on a large embedded codebase; the principles are general.

Deep tables, the full script contract, and worked examples live in `reference.md`. A generic reconciliation checker (`manifest-check.sh`) and a lean manifest schema (`manifest.schema.md`) ship alongside.

## When To Use

Use this skill when the user wants to:

- add a new tool/CLI script and decide where it goes
- move, rename, split, or delete a tool script
- audit tooling sprawl ("too many scripts at the top level", "what is all this")
- set up or tighten tooling governance for a large/growing repo

Do not use it for application source layout (that is normal architecture), for documentation systems (use `project-docs-organizer`), or for one-off throwaway scripts that will not be committed.

## The one meta-rule

Keep the spec short. A few hard rules that are actually followed beat thirty that nobody reads. Everything below is either **Mandatory** (worth a gate/audit) or **judgment**. Resist adding more.

## 1. Classify by surface (not just "who calls it")

Every committed script gets exactly one **surface** label — chosen by what it *is*: who runs it, what state it mutates, the failure/hazard model, whether it emits a deliverable, and how success is verified.

| surface | one-liner | lives where |
|---|---|---|
| `public` | stable entry humans / other skills / docs invoke directly | domain **headline** at top level; other public commands under `<domain>/` |
| `installed` | shipped into an artifact / run by a service / on a target's PATH — **its path is an external contract** | top level or domain dir (moving it = changing the contract) |
| `helper` | only called by one public/installed entry; users should not run it directly | `internal/` or a domain subdir |
| `break-glass` | rare, no daily caller, but a **real recovery / one-off migration** that must stay discoverable | top level, with a `trigger` note |
| `paused` | built but not yet enabled | with an `activation_gate` note |
| `legacy` | superseded, kept for archaeology | `internal/` or `<domain>/legacy/`, with a `replacement` note |
| `package` / `native` / `template` / `vendor` | multi-file impl package / compiled-target source / render template / controlled third-party binary | see `reference.md` |

`break-glass`, `paused`, and `legacy` are **three different "non-daily" meanings** — never dump them into one `internal/` bucket. Full table + placement detail: `reference.md`.

**Top level holds only:** each domain's headline entry, genuinely high-frequency dev tools, and break-glass scripts. Everything else sinks into `<domain>/`.

## 2. Aggregate by failure-domain, not noun-domain

"One workflow class → one authoritative entry (+ subcommands)" — but a *noun* like `provision` usually spans several jobs at different altitudes. Collapse commands into one entry **only when all three axes match**:

1. **audience** — same kind of operator (dev / ci / operator / release / end-user / runtime).
2. **target-state ⊕ artifact** — mutates the same class of state ∧ produces the same class of output.
3. **hazard ⊕ verification** — same failure/rollback model ∧ the same smoke/gate proves success.

Any axis differs → **keep them separate** and sink shared logic into a lib. A noun-domain whose jobs differ in altitude stays a **multi-command toolkit**, not a mega-CLI — folding low-level recovery / batch / ledger paths under one high-level happy-path entry *hides* them. (Example in `reference.md`.)

## 3. Placement decision tree (where a new script goes)

```
What are you adding?
├─ a subcommand/flag of an existing domain headline?  → add it there (no new script)
├─ called only by one public entry?                   → helper: internal/ or <domain>/
├─ same noun-domain, independent operator job?         → new public command in <domain>/
├─ the domain's new daily-use main entry?              → headline at top level
├─ multi-file package / render template?               → <domain>/ (package / template)
├─ compiled/native target source?                      → <target>/ (dir name = command)
├─ rare but sole production recovery/migration?        → break-glass (top level + trigger)
├─ third-party binary?                                 → vendor/ (record source/version/checksum)
└─ one-off spike?                                       → internal/<name>/ or don't commit
```

Ask first: *"Is this a subcommand of an existing headline?"* (yes → add it there) and *"Is this a new headline or a domain-public command?"* (default → `<domain>/`; only a domain's daily main entry earns a top-level headline).

## 4. Script contract — Mandatory

These are worth auditing (see §5):

- **`--help` + exit codes**: public/installed entries support `-h/--help` (exit 0); usage / unknown flag → exit 2; preflight failure → nonzero **and stop before the dangerous action**. Never let an unknown arg fall through to the default action.
- **One shared resolver**: scripts that pick an environment/platform/config/target must `source` a single shared resolver, not each re-parse `--platform`/`--env` or hardcode a default.
- **Dangerous actions go through the authoritative path**: anything that deploys, mutates production/device state, or builds a deliverable uses the project's blessed upgrade/install/release path. Any escape hatch is an **explicit flag + a logged warning + never a customer/QA path**.
- **Secrets hygiene**: never commit/print secrets; no `set -x` leaking them; temp files `0600`; `trap ... EXIT` to shred/cleanup.
- **Atomic + idempotent**: state writes use `.tmp` + fsync + rename; install/migration steps are idempotent (re-running is a no-op).
- **Stable logs**: multi-step scripts use a stable prefix (e.g. `[deploy]`); errors to stderr.
- **Manifest registration**: adding/moving/removing any public/installed/break-glass/paused/legacy command surface updates the manifest in the **same commit** (§5).

Recommended (not gated): `shellcheck`; `cmd_<verb>` subcommand style; a 3–4 line header contract (purpose / 2–3 real usages / surface + audience / hazard + dry-run); prefer `--dry-run` over `--yes`; keep a deprecation shim for external surfaces for ≥1 release. Details: `reference.md`.

## 5. Surface manifest = source of truth

For a repo past a handful of scripts, keep a **machine-readable manifest** (one row per command surface) plus a human view, and a reconciliation check so the two never drift from reality.

- Schema (lean, copy-paste): `manifest.schema.md` — core columns `path, surface, domain, audience, entry_for, hazard, verify, notes` (+ a few optional ones for installed/legacy/paused/break-glass/vendor).
- Rule: a `public` tool must own an independent `entry_for` job; **no independent job ⇒ it is a helper**, not a public command. This keeps the manifest a governance tool, not a "once mentioned, public forever" snapshot.
- Check: `bash manifest-check.sh [path/to/manifest.tsv]` reconciles the manifest against the scripts on disk — flags manifest rows pointing at missing files, command files on disk with no row, shell/python syntax errors, and public/installed entries lacking a `--help` handler. Wire it into CI / pre-commit.

Small projects can skip the manifest and just apply §1–§4 by judgment; adopt the manifest when the script count or contributor count makes drift likely.

## 6. Move = contract change

Moving/renaming/deleting a script syncs every mechanical reference **in the same commit**: docs, sibling skills, service/unit files, build files + other callers, the manifest + its human view, and a decision on whether to leave a deprecation shim (external/QA surfaces: keep one for ≥1 release; internal: move freely). Re-check the script's own `REPO_ROOT`/path derivation after a move. Checklist + verification commands: `reference.md`.

## Workflow

1. Identify the job: **add**, **move/rename/delete**, or **audit**.
2. **Add** → classify the surface (§1), run the placement tree (§3), apply the Mandatory contract (§4), and register it in the manifest (§5).
3. **Move/delete** → run the move checklist (§6) and update the manifest in the same commit.
4. **Audit** → run `manifest-check.sh`; for sprawl, report each top-level script's surface and whether it should sink into a domain dir or merge into an existing headline (§2–§3). Report candidates; don't mass-move without confirmation.
5. Verify with the minimal set (`bash -n` / `py_compile` / `--help` / `--dry-run` / domain tests / `manifest-check.sh` / grep for stale references) — see `reference.md`.
