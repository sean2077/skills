# Tool Script Contract

Read this when implementing or auditing the mandatory and recommended behavior of a committed command.

## Complete script contract

### Mandatory (gate/audit these)

- **`--help` + exit-code contract** — authoritative entries invoked directly by humans or automation: `-h/--help` → exit 0; usage / unknown flag → exit 2; runtime/preflight failure → nonzero and **do not proceed** with the dangerous action. Unknown args must never fall through to the default action.
- **Unified resolver** — if a script selects one of {build preset, profile, config path, target path, install path} from a platform/environment, it `source`s a single shared resolver (one precedence definition: explicit flag > env var > inferred-from-context > default), instead of re-implementing `--platform`/`--env` parsing or hardcoding one value.
- **Authoritative path for dangerous actions** — deploying code, mutating production/device state (config / service / identity / credentials), or producing a release deliverable goes through the project's blessed upgrade/install/desired-state/image/release path. A temporary escape hatch is allowed only as an **explicit flag + a logged risk warning + never a QA/customer path**.
- **Secrets** — never commit keys; never print secret values; no `set -x` that would leak them; temp files `0600`; `trap '…' EXIT` to shred/cleanup; deliverables pass a secrets/leak gate before shipping.
- **Atomic + idempotent** — state-file writes: `.tmp` + fsync/close + atomic rename. Install / desired-state / config-migration steps are idempotent (no ledger needed; re-running converges).
- **Logging** — multi-step scripts use a stable bracketed prefix; errors go to stderr.
- **Inventory registration, when adopted** — if the target repository already owns a structural
  tool inventory, adding, moving, or removing an affected command or registered directory updates
  it in the same commit. Update Project Tool Policy separately when semantic metadata changes.
  Do not create an inventory solely to satisfy this reference.

### Recommended (judgment, not gated)

- `shellcheck` when available; `cmd_<verb>` subcommand dispatch; JSON output only when something automated consumes it.
- A header contract on authoritative shell entries: ① one-line purpose ② 2–3 *real* usage lines
  ③ direct invokers and owned job ④ hazard / dry-run note. Supporting package modules, native
  sources, and templates do not need the same header—record their build/provenance contract in
  the project-owned location instead.
- Prefer `--dry-run` over `--yes`. Keep compatibility behavior only when the target project's
  verified active consumers require it; the generic skill does not create or retain shims.
