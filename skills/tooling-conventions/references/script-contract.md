# Contextual Command Contract

Read this when implementing or auditing a committed command after its Job Boundary and Contract
Profile are known. The Contract Profile decides which cards apply; this is not one mandatory CLI
or implementation template.

## Always-on safety boundaries

- Never let unknown or invalid input reach a dangerous default action. Preserve the target
  project's existing CLI grammar and exit-code convention; when a new authoritative entry has no
  governing convention, choose and document the smallest interface its real invokers need.
- Route deploys, releases, credential changes, device mutation, and other hazardous effects through
  the project's authoritative path. An escape hatch exists only when project policy names its
  trigger, warning, prohibited environments, owner, and removal condition.
- Never commit or print secrets. Use the target platform's permission, redaction, temporary-storage,
  and cleanup mechanisms; do not promise secure erasure that the storage layer cannot provide.
- Preserve installed paths, service bindings, machine-readable output, and other external command
  contracts until every active consumer moves in one coordinated change.

## Conditional contract cards

### Invocation and help

Apply when humans or automation invoke the entry directly. Preserve the project's parser, flags,
usage format, and exit meanings. Add discoverability for a new interface only when an actual
invoker needs it; do not retrofit `-h/--help`, subcommands, or a universal exit number merely to
match this skill.

### Context resolution

Apply when several entries or call sites select the same preset, profile, environment, target, or
path. Consolidate duplicated precedence into the project's language-native shared resolver or
configuration authority. Derive precedence from callers and policy rather than imposing a fixed
flag/environment/inference/default order.

### State mutation and retry

Apply when the command owns persistent state or partial failure matters. Choose the transaction,
atomic replacement, rollback, checkpoint, idempotency key, or convergence mechanism supported by
that state owner. Require idempotency only when retry or convergence is part of the observed
contract; a generic skill does not prescribe `.tmp` files, `fsync`, rename semantics, or a ledger.

### Output and observability

Apply when a human must diagnose multiple steps or a machine consumes output. Preserve structured
stdout and exit semantics, route diagnostics through the project logger or stderr as appropriate,
and use prefixes or JSON only when the consumer contract calls for them.

### Preview and confirmation

Apply when a hazardous effect can be previewed faithfully. Do not claim a dry run unless tests prove
the preview has no forbidden side effects and represents the real selection logic. Confirmation
flags, interactive prompts, and non-interactive defaults remain project-owned.

### Inventory registration, when adopted

If the target repository already owns a structural tool inventory, adding, moving, or removing an
affected command or registered directory updates it in the same commit. Update Project Tool Policy
separately when semantic metadata changes. Do not create an inventory solely to satisfy this
reference.

## Review outcome

Record the cards selected and rejected with evidence, the existing contracts preserved, failure and
recovery behavior, and the smallest verification set that proves the chosen outcomes.
