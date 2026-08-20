# Cleanup safety

Read this only when deciding whether an abstraction, fallback, compatibility branch, or test seam is safe to remove.

## Deletion test

Delete a layer when its removal makes complexity disappear and callers remain simpler. Keep or redesign it when removal spreads policy, state, retries, validation, or compatibility knowledge across callers.

## Fallback test

A fallback is justified only when the triggering condition is observable, the substitute behavior is intentional, and failure remains diagnosable. Remove silent defaults, broad exception swallowing, and compatibility branches with no supported caller.

## Behavior-lock hierarchy

Prefer tests through the same public interface callers use. Internal-only tests may protect a risky refactor temporarily, but reliance on private internals is an architecture signal, not permission to widen this cleanup pass.

When automation is unavailable, use a deterministic fixture, captured input/output comparison, or narrowly documented manual observation. State what the substitute cannot prove.
