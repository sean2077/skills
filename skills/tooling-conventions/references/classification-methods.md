# Contextual Tool Classification Methods

Read this when deciding whether commands aggregate, remain a toolkit, or move within a
project-owned root. These are reasoning lenses, not required categories or directory names.

## Composition rules

Use the Governance Decision Pipeline in order:

1. **Job Boundary** — identify one independently invokable job with coherent owned state or
   artifact, failure/rollback behavior, and verification.
2. **Contract Profile** — record invocation, distribution, risk, lifecycle, and provenance
   constraints without collapsing them into one label.
3. **Placement Decision** — only after the first two are stable, choose a root, grouping, path,
   and name from the target project's evidence.

Boundary lenses may propose a Job Boundary or local grouping. Constraint lenses may veto an
aggregation or constrain placement, but normally do not create peer directory axes. Select only
cards supported by evidence, state why the others do not govern, and never build a Cartesian
product of every lens.

## Boundary lenses

### Task or journey

- **Signals:** operators search by outcome, workflow stage, incident step, or repeatable sequence.
- **Ask:** what exact job is the invoker trying to complete, and what independently proves it done?
- **Fits when:** commands form a stable end-to-end workflow or several distinct operator jobs.
- **Fails when:** a journey hides durable ownership or combines incompatible failure domains.
- **Pipeline role:** proposes Job Boundaries; may suggest subcommands when the full contract aligns.
- **Micro-example:** build, sign, and publish can form one release entry only when one rollback and
  release verification govern the sequence; independent signing recovery remains separate.

### Domain capability, ownership, and language

- **Signals:** capabilities have different decision owners, lifecycles, handoffs, or meanings for
  the same term.
- **Ask:** which capability owns this job and vocabulary, and where does that ownership end?
- **Fits when:** a domain-rich project has cohesive capability boundaries that survive team moves.
- **Fails when:** it merely mirrors teams, services, or source directories without ownership facts.
- **Pipeline role:** proposes durable Job Boundaries or local grouping after behavior is understood.
- **Micro-example:** device identity recovery stays with identity ownership even if its script is
  currently beside deployment commands that touch the same board.

### Invoker or entry

- **Signals:** humans, CI, services, release automation, or target runtimes have different
  permissions, stability expectations, or interaction contracts.
- **Ask:** who or what invokes this directly, and which path or interface do they depend on?
- **Fits when:** invocation contracts genuinely separate public, automation, service, and private
  helper responsibilities.
- **Fails when:** several invokers share the same stable job and can use one authoritative entry.
- **Pipeline role:** distinguishes authoritative entries from helpers and identifies external paths.
- **Micro-example:** a service-installed executable and a developer wrapper may share a library,
  but remain separate entries when the service path is an external deployment contract.

### State or artifact

- **Signals:** commands own different desired state, credentials, ledgers, packages, images, or
  generated deliverables.
- **Ask:** what state or artifact changes, who owns it, and what invariant proves the result?
- **Fits when:** ownership and transactional boundaries are clearer than the command nouns.
- **Fails when:** artifacts are incidental outputs of one coherent job rather than separate assets.
- **Pipeline role:** separates jobs with incompatible atomicity, rollback, or verification.
- **Micro-example:** compiling an image and installing it on a device remain separate when the
  build artifact is reproducible but device rollout requires health checks and rollback.

## Constraint lenses

### Distribution contract

- **Signals:** a command is installed into an image, placed on `PATH`, invoked by a service, or
  consumed from a fixed repository path.
- **Ask:** which consumers bind to this path or interface, and can all move together?
- **Fits when:** relocation or renaming changes an external or packaged contract.
- **Fails when:** the path is private and every caller is updated atomically in the same change.
- **Pipeline role:** constrains placement and migration; it does not define a noun-domain directory.
- **Micro-example:** a target-side health command keeps its installed path while its host-side
  source may move only through the owning image/install change.

### Hazard, recovery, and verification

- **Signals:** commands differ in production impact, rollback, recovery trigger, dry-run support,
  or the evidence required to trust success.
- **Ask:** what can fail, how is damage bounded or reversed, and which check proves success?
- **Fits when:** risk or verification differences reveal independent operator jobs.
- **Fails when:** small risk differences are flags within one coherent command contract.
- **Pipeline role:** may veto aggregation and sets script-contract plus real-target verification.
- **Micro-example:** batch provisioning with a ledger stays separate from single-device recovery
  even though both manipulate identity, because rollback and proof are different.

### Lifecycle or authority

- **Signals:** active, paused, superseded, generated, or retained assets have different owners and
  trust rules.
- **Ask:** which entry is authoritative now, what activates or replaces the others, and why retain
  them?
- **Fits when:** callers might select stale, disabled, or generated commands as if they were live.
- **Fails when:** lifecycle labels become a junk drawer instead of resolving ownership.
- **Pipeline role:** annotates authority and migration; normally secondary to the live Job Boundary.
- **Micro-example:** a paused migration command carries its activation gate in project policy
  rather than moving into a universal `paused/` directory.

### Implementation form or provenance

- **Signals:** the governed asset is a script, compiled source tree, package, template, generated
  entry, or controlled third-party binary.
- **Ask:** what builds or supplies it, and which source/version/checksum owns future updates?
- **Fits when:** build, packaging, licensing, or provenance constrains where the asset can live.
- **Fails when:** implementation form is mistaken for the command's operator-facing job.
- **Pipeline role:** constrains placement and verification after Job Boundaries are stable.
- **Micro-example:** a vendored executable follows the project's vendor/checksum policy while the
  wrapper that exposes a project-owned job follows the wrapper's own command contract.

## Decision record

Before recommending or applying a change, report:

1. observed roots, callers, ownership, vocabulary, drift, and existing gates;
2. selected and rejected method cards with evidence;
3. Job Boundaries and aggregate, toolkit, or split decisions;
4. Contract Profiles, including active path consumers and verification;
5. project-owned placement and naming decisions;
6. migration/coordination impacts and the complete verification plan.

Persist this Tool Governance Decision Record only when the target project already requires a
manifest, ADR, or design page, or when the user explicitly requests one.
