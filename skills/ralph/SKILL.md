---
name: ralph
description: Use when a verifiable goal needs bounded iterative attempts with mechanical pass, stall, plateau, exhaustion, and resume judgment.
---

# ralph

Iterate toward one verifiable goal under a fixed budget. The agent changes the system and runs the verifier; the bundled standard-library runtime owns rounds, revisions, stable signatures, optional scores, binding, and stop conditions. It never executes verifier commands.

Invoke the quoted script path directly:

```bash
python3 "<installed-skill-dir>/scripts/ralph_state.py" status
```

Use `python` when that is the host's Python 3 command, or `py -3` on Windows. Python 3.8+ is required; no third-party package is required.

## Start or resume

Exit `3` from `status` means the default run does not exist:

```bash
python3 "<installed-skill-dir>/scripts/ralph_state.py" start \
  --goal "<verifiable goal>" --max-rounds 10 --stall-window 3
```

Use `--id <slug>` for parallel runs. Session isolation, newest-first `list --all-sessions --limit 20`, `--latest`, compact output, `--full`, and bounded `history --tail <1..20>` follow the same runtime contract as the other deterministic workflow skills.

Use `--keep-policy score-improvement --plateau-window <n>` with `--score 0..1` only when partial quality has a real rubric. Select `--profile research` or `--profile adversarial-qa` only when the matching reference applies.

## Each round

1. Run `next --expected-revision <n>`. It opens exactly one pending round.
2. Make one bounded, materially different attempt. Run the real verifier yourself with safe timeouts.
3. Submit the observed result with `check --round <n> --verifier-exit <code> --signature <stable-failure>`. A failing verifier requires a non-empty, noise-free root-cause signature. Score-improvement loops also require `--score <0..1>`.
4. Obey the compact result:
   - `active`: another round is allowed;
   - `passed`: verifier exited zero;
   - `stalled`: one failure mechanism filled the stall window;
   - `plateaued`: score failed to improve through the plateau window;
   - `exhausted`: the round budget ended;
   - `aborted`: the run was explicitly stopped.

A successful transition into a terminal status returns success because the result was recorded. A later mutation attempt returns terminal exit `4`. One pending round accepts exactly one `check`.

## Completion report

Report goal, terminal status, rounds used, verifier commands actually run, best score/round when applicable, final signature, changes attempted, and remaining risks. Never translate a non-passing terminal into “done”.

## Hard rules

- Never fake an exit code, score, signature, or verifier run.
- Use the latest revision for every mutation.
- Stop on terminal status, binding mismatch, revision conflict, unsafe action, or user interruption.
- Change strategy after stall/plateau evidence; do not buy a new run merely to repeat an exhausted approach.
- Nested ralph loops are forbidden.

## On-demand references

- Read [profiles](references/profiles.md) only for research optimization or adversarial end-to-end QA.
- Read [resume and recovery](references/resume-and-recovery.md) only for pending-round resume, discovery, mismatch, conflict, lock, corruption, or non-Git roots.
