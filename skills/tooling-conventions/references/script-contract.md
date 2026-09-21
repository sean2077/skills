# Command Contracts

Design a command around its actual invokers, effects, and the project's established CLI conventions.

## Input and authority

Validate input before dangerous actions. Preserve established flags, exit meanings, installed paths, service bindings, and machine-readable output while consumers depend on them. Route consequential effects through the authorized deploy, release, credential, or device workflow.

Handle secrets with the platform's permissions, redaction, temporary-storage, and cleanup mechanisms. Keep credentials out of committed files and logs.

## Context and state

Where several entries resolve the same target, environment, preset, or path, share the owning precedence logic. Derive it from project policy and callers.

Choose transactions, atomic replacement, rollback, checkpoints, or idempotency according to the state owner's guarantees and the command's failure and retry model. Preserve independent recovery when aggregation would obscure it.

## Output and preview

Provide diagnostics that help the real consumer interpret success, partial failure, and recovery. Keep machine output and exit semantics stable.

For a preview or dry-run mode, verify that it uses the real selection logic and avoids the effects it claims to suppress. Follow the project's confirmation and non-interactive policies.

## Inventory and verification

Update an existing inventory and its project-specific policy when affected entries or metadata change. Select checks that exercise the command's actual contract; see [verification](verification.md) and [path migrations](path-migrations.md).
