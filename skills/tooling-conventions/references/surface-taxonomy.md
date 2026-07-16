# Tool Surface Taxonomy

Read this when classifying committed command surfaces or deciding whether related commands share a failure domain.

## Full surface taxonomy

| surface | meaning | where it goes |
|---|---|---|
| `public` | a stable entry that humans / skills / docs invoke directly | the domain **headline** stays at top level (`tools/<name>.sh`); the domain's *other* public commands sink to `tools/<domain>/<name>.sh` |
| `installed` | shipped into an image / invoked by a service / placed on a target's PATH — **the path is an external contract** | top level or domain dir; moving it = changing a contract (update the service/install side too) |
| `helper` | only ever called by one public/installed entry; a user should never run it directly | `tools/internal/` or a domain subdir |
| `break-glass` | rare, no daily caller, but a **real production-recovery / one-off migration** capability that must stay discoverable | top level, carrying a `trigger` note ("reach for this when …") |
| `paused` | designed/built but not yet enabled | top level or domain dir, carrying an `activation_gate` note (what unblocks it) |
| `legacy` | superseded, kept only for archaeology | `tools/internal/` or `tools/<domain>/legacy/`, carrying a `replacement` note |
| `package` | a multi-file implementation package (e.g. a Python package, a template set) | `tools/<domain>/`; register the dir once, not each internal module |
| `native` | source dir for a compiled host tool (CMake/Make target) | `tools/<target>/` with the dir name = the command name |
| `template` | a render template, not an executable entry | `tools/<domain>/` |
| `vendor` | a controlled third-party binary | `tools/vendor/`, recording source + version + checksum; large ones may be gitignored + lockfile-verified |

**Headline vs domain-public.** "public" is a surface; "headline" is a *placement role* derived from path + docs (it is not a manifest field). Each domain usually has one headline — its daily main entry, where docs tell an operator to start. When a domain splits by platform, a platform sibling headline is fine (don't fabricate a wrapper). Every other public command in the domain sinks under `tools/<domain>/` and still has `surface=public`, just with a domain-prefixed path. `internal/`-resident public entries (an active backend that happens to live in `internal/`) are a documented path-exception; domain-subdir public entries are normal placement, not exceptions.

**Package + commands coexist.** A domain dir can hold both a package namespace and command scripts. Represent it with a directory-level `package` row (covering the package's internal modules — don't register them one by one) plus file-level rows for the actual commands. Identify commands as **`.sh` scripts (by suffix, so a missing `chmod` can't smuggle one past the audit) + executable `.py` CLIs**; for tracked Python files the checker reads Git mode `100755` instead of trusting `[ -x ]`, which is unreliable with Windows `core.filemode=false`. Non-executable package modules are covered by the package row.

## Failure-domain aggregation — worked example

The three-axis test (audience / target-state⊕artifact / hazard⊕verification) decides whether commands merge into one entry + subcommands or stay separate.

- ✅ **aggregate** — a board-ops entry with `wifi` / `sn` / `power-mode` / `logs` subcommands: all the same operator doing the same class of on-device maintenance (same audience, state, hazard). Collapsing 5+ scattered scripts into subcommands is the win.
- ✅ **toolkit, do NOT aggregate** — a "provision" noun-domain that is really several jobs at different altitudes: a high-level *fresh-board → usable* orchestrator, a low-level *single-board recovery* tool, a *batch + ledger* dispatcher, a *read-only re-probe/audit*, a *pure host codec/validator*. Docs teach operators to run each directly ⇒ each is its own public entry. Forcing them under one mega-CLI would bury the recovery/batch/ledger paths beneath a happy-path entry.
- ↔ **split** — two commands that both "touch a board from a dev machine" but differ in target-state (one provisions identity, the other deploys a build) and hazard (one is low-risk, the other rides an auto-rollback upgrade) → separate, even though the noun overlaps.

Keep the four sub-signals (`target_state`, `artifact`, `hazard`, `verify`) as distinct manifest fields even though the decision tree folds them into two axes — they are the evidence for re-reviewing a boundary case later.
