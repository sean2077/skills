---
name: ralph
description: Use when a verifiable goal needs bounded iterative attempts with mechanical pass, stall, plateau, exhaustion, and resume judgment.
---

# ralph

Iterate toward a verifiable goal under a fixed budget. The agent performs work and runs verifiers; the bundled runtime owns rounds, revisions, signatures, scores, stop conditions, binding, and terminal state. It never executes verifier commands.

Set `RALPH="python <skill-dir>/scripts/ralph_state.py"` using this installed skill directory.

## Start or resume

Probe with `$RALPH status --id <slug>`. Exit `3` means no run. Start a binary verifier loop with:

```bash
$RALPH start --id <slug> --goal "<verifiable goal>" --max-rounds 10 --stall-window 3
```

Use `--keep-policy score-improvement --plateau-window <n>` and submit `--score 0..1` when partial progress is meaningful. Select `--profile research` or `--profile adversarial-qa` only when the matching reference applies.

## Each round

1. Run `next --expected-revision <n>`. It opens exactly one pending round; exit `4` reports a terminal run.
2. Make one bounded attempt. Run the real verifier yourself with safe timeouts and capture its actual exit code.
3. Submit `check --round <n> --verifier-exit <code> --signature <stable failure>`. For score-improvement loops, also pass `--score <0..1>`.
4. Reload status and obey its judgment:
   - `passed`: verifier exited zero;
   - `stalled`: the same non-empty failure signature repeated through the stall window;
   - `plateaued`: score failed to improve through the plateau window;
   - `exhausted`: the round budget ended;
   - `active`: another round is allowed.

A signature describes the stable failure mechanism, not a timestamp or full noisy log. A changed error caused by the same root condition keeps the same signature.

## Completion report

Report goal, terminal state, rounds used, verifier commands run by the agent, best score when used, final signature, changes attempted, and remaining risks. Never translate a non-passing terminal state into “done”.

## Hard rules

- Never fake an exit code, score, or signature and never ask the runtime to execute a command.
- Use the latest revision on every mutation; one pending round accepts one result.
- Stop immediately on terminal state, binding mismatch, revision conflict, unsafe action, or user interruption.
- Change strategy after evidence of stall/plateau; do not spend a new run repeating the same approach without authorization.
- Nested ralph loops are forbidden.

## On-demand references

- Read [profiles](references/profiles.md) only when running a research optimization or adversarial end-to-end QA loop.
- Read [resume and recovery](references/resume-and-recovery.md) only when status reports interruption, mismatch, conflict, lock, or state corruption.
