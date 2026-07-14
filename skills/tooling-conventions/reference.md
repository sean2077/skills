# tooling-conventions — reference

On-demand depth for the resident `SKILL.md`: the full surface taxonomy, the failure-domain aggregation deep-dive, the complete script contract, the move checklist, and the verification set.

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

**Package + commands coexist.** A domain dir can hold both a package namespace and command scripts. Represent it with a directory-level `package` row (covering the package's internal modules — don't register them one by one) plus file-level rows for the actual commands. Identify commands as **`.sh` scripts (by suffix, so a missing `chmod` can't smuggle one past the audit) + executable `.py` CLIs**; non-executable package modules are covered by the package row.

## Failure-domain aggregation — worked example

The three-axis test (audience / target-state⊕artifact / hazard⊕verification) decides whether commands merge into one entry + subcommands or stay separate.

- ✅ **aggregate** — a board-ops entry with `wifi` / `sn` / `power-mode` / `logs` subcommands: all the same operator doing the same class of on-device maintenance (same audience, state, hazard). Collapsing 5+ scattered scripts into subcommands is the win.
- ✅ **toolkit, do NOT aggregate** — a "provision" noun-domain that is really several jobs at different altitudes: a high-level *fresh-board → usable* orchestrator, a low-level *single-board recovery* tool, a *batch + ledger* dispatcher, a *read-only re-probe/audit*, a *pure host codec/validator*. Docs teach operators to run each directly ⇒ each is its own public entry. Forcing them under one mega-CLI would bury the recovery/batch/ledger paths beneath a happy-path entry.
- ↔ **split** — two commands that both "touch a board from a dev machine" but differ in target-state (one provisions identity, the other deploys a build) and hazard (one is low-risk, the other rides an auto-rollback upgrade) → separate, even though the noun overlaps.

Keep the four sub-signals (`target_state`, `artifact`, `hazard`, `verify`) as distinct manifest fields even though the decision tree folds them into two axes — they are the evidence for re-reviewing a boundary case later.

## Complete script contract

### Mandatory (gate/audit these)

- **`--help` + exit-code contract** — public/installed entries: `-h/--help` → exit 0; usage / unknown flag → exit 2; runtime/preflight failure → nonzero and **do not proceed** with the dangerous action. Unknown args must never fall through to the default action.
- **Unified resolver** — if a script selects one of {build preset, profile, config path, target path, install path} from a platform/environment, it `source`s a single shared resolver (one precedence definition: explicit flag > env var > inferred-from-context > default), instead of re-implementing `--platform`/`--env` parsing or hardcoding one value.
- **Authoritative path for dangerous actions** — deploying code, mutating production/device state (config / service / identity / credentials), or producing a release deliverable goes through the project's blessed upgrade/install/desired-state/image/release path. A temporary escape hatch is allowed only as an **explicit flag + a logged risk warning + never a QA/customer path**.
- **Secrets** — never commit keys; never print secret values; no `set -x` that would leak them; temp files `0600`; `trap '…' EXIT` to shred/cleanup; deliverables pass a secrets/leak gate before shipping.
- **Atomic + idempotent** — state-file writes: `.tmp` + fsync/close + atomic rename. Install / desired-state / config-migration steps are idempotent (no ledger needed; re-running converges).
- **Logging** — multi-step scripts use a stable bracketed prefix; errors go to stderr.
- **Manifest registration** — adding/moving/removing any public/installed/break-glass/paused/legacy command surface updates the manifest (and its human view) in the same commit, or the reconciliation audit fails. New scripts default to "enforced".

### Recommended (judgment, not gated)

- `shellcheck` when available; `cmd_<verb>` subcommand dispatch; JSON output only when something automated consumes it.
- A header contract on public/installed shell entries: ① one-line purpose ② 2–3 *real* usage lines ③ surface + audience ④ hazard / dry-run note. Native sources, package modules, and templates don't need the same header — register them in the domain/target docs instead.
- Prefer `--dry-run` over `--yes`. Keep a deprecation shim for external/QA surfaces for at least one release; internal surfaces can move without a shim.

## Move / rename / delete checklist

A move is a contract change — sync every mechanical reference surface in the **same commit**:

- [ ] project manual / agent docs that name the path
- [ ] sibling skills that invoke it
- [ ] service/unit files bound to it (change the unit/install contract first, or leave a shim)
- [ ] build files, install scripts, image/packaging scripts, and any other callers
- [ ] the manifest row + its human-readable view
- [ ] decide on a deprecation shim (external/QA: keep ≥1 release; internal: drop)
- [ ] re-check the moved script's own `REPO_ROOT`/`HERE` derivation and sibling-file references (a relocated script often needs one extra `..`)

External state (a wiki, an issue tracker, agent memory) is not a commit-blocking file surface, but list any that affect the current workflow in the change summary.

## Verification — minimal set

```bash
bash -n <script.sh>                 # shell syntax
python -m py_compile <script.py>   # python syntax
<script> --help                     # exit 0 + usage
<script> --dry-run ...              # dangerous scripts: prove the no-op path
bash manifest-check.sh <manifest>   # reconcile manifest vs disk (this skill's checker)
rg -n '<old-path>' <docs> <skills> <units>   # after a move: no stale active references
# plus any domain test the project already has
```

Scripts whose effect can't be fully verified on a dev host (anything that drives real hardware, a device GUI, or a flashing/loader path) still need a real-target smoke before they're trusted.
