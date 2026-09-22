# Task outcome checks

Use these opt-in fixtures to test what an Agent actually changes, separately from the [routing probes](../agent-skills/README.md). This is one-task preparation, execution, and inspection, not a scheduler or a delivery workflow. No new public skill is installed.

## What is checked

| Case | Actual observations | Important limit |
|---|---|---|
| `commit-hunks` | Commit tree/parent, same-file staged hunk, another staged file, unstaged changes | A bounded Git scenario, not every commit operation |
| `spec-preservation` | Source-owned clauses, exact values, draft status, unresolved question, revised overview | Mechanical checks do not establish all semantic accuracy or reader comprehension |
| `docs-move` | Unique content and incoming/outgoing relative links and anchors | The fixture's Markdown subset, not a general Markdown validator |
| `lark-unknown-write` | Local mock calls: one send followed by same-identity readback | No network, no live CLI syntax or service certification; local logs are not tamper-proof |
| `lark-invented-syntax` | Local mock invocation log, collection observation, and correct awaiting-reply count in `answer.json`; rejects unsupported flags, identities, and IDs | Logs are writable and not tamper-proof. This bounded mock oracle does not certify live CLI syntax or model effectiveness |
| `tdd-negative-input` | Captured test tool results: missing-behavior RED at original source, then GREEN with the same tests and final hashes; independent behavior check | A final answer or an Agent-authored log cannot supply missing sequence evidence |

The invented-syntax task-only prompt states the task and points to command documentation; the brief condition adds syntax guidance separately. Correct mock use must also produce the requested result: reading help or one message is insufficient. Its local log is suitable for cooperative reference actions, not adversarial proof of execution; any model-benefit claim still needs matched observed runs and trace review.

CI runs `scripts/tests/test_task_outcomes.py` with deliberate good/bad reference actions. These are tests of the fixtures and their oracles, **not model-performance measurements**. `scripts/tests/test_release_execution.py` separately executes this repository's release shell steps with real Git and a mock publisher, including negative cases.

## Prepare a matched experiment

Use a disposable, credential-limited environment outside this checkout. Each run creates its own Git repository and refuses an existing output directory. Choose `none` (task only), `brief` (the same task plus a short instruction), or `skill` (explicitly apply a pinned, complete skill payload including its references). These compare execution, not native discovery.

```bash
python evals/tasks/runner.py prepare commit-hunks /absolute/eval/commit-none --condition none
python evals/tasks/runner.py prepare commit-hunks /absolute/eval/commit-brief --condition brief
python evals/tasks/runner.py prepare commit-hunks /absolute/eval/commit-skill --condition skill --skill-revision HEAD
```

Commit intended skill changes before using `HEAD`: payloads are exported from Git, never from uncommitted files. For old/new comparisons, use two full skill commit IDs with the same fixture and evaluator. The evaluator's content hash is recorded separately. Run order, models, effort, tool permissions, plugin/memory configuration, cache policy, and user interventions can change the result; keep them matched and record deviations. Repeated, held-out tasks are needed before claiming a stable advantage. A brief request is a legitimate alternative to the skill, not an invalid control.

Give the host only `prompt.txt`, the fixture workspace, and its named guidance when present. Do not pass `fixture.json`, evaluator source, or expected checks to the subject. Keep transcripts and result files outside the workspace. The runner and Git isolation are **not an OS sandbox**: trusted adapters and tested code can execute commands. Use your sandbox for filesystem/network/credential isolation; do not run these against production resources.

## Execute with an existing host

A host can work directly in the prepared `workspace/`. For Claude Code, the following is a manual recording example based on its [CLI reference](https://code.claude.com/docs/en/cli-reference) and [programmatic mode](https://code.claude.com/docs/en/headless), reviewed 2026-09-22. It requires an authenticated CLI supporting the named flags; this is documentation review, not live-host certification. Bare mode excludes ambient skills/hooks/memory; do not silently remove it to make an unsupported version run.

```bash
# Run in a disposable sandbox. Bash permission permits commands; it is not a sandbox.
: "${CLAUDE_MODEL_ID:?Set an exact model ID, not a moving alias}"
run=/absolute/eval/commit-skill
claude --version > "$run/host-version.txt"
start=$(python -c 'import time; print(time.monotonic())')
status=0
(
  cd "$run/workspace"
  claude --bare -p --model "$CLAUDE_MODEL_ID" --no-session-persistence \
    --permission-mode dontAsk --tools "Bash,Read,Edit,Write" \
    --allowedTools "Bash,Read,Edit,Write" --output-format stream-json --verbose \
    < "$run/prompt.txt" > "$run/session.jsonl"
) || status=$?
elapsed=$(python -c 'import sys,time; print(time.monotonic()-float(sys.argv[1]))' "$start")
python evals/tasks/import_claude.py "$run/session.jsonl" "$run/driver.json" \
  --version-file "$run/host-version.txt" --model "$CLAUDE_MODEL_ID" \
  --configuration bare-local-tools --cache-condition recorded-cold \
  --elapsed-seconds "$elapsed" --exit-code "$status"
python evals/tasks/runner.py verify "$run" --driver-result "$run/driver.json" > "$run/result.json"
```

Record the **actual** cache condition instead of copying the example label. Inspect session initialization for unexpected configuration and tools. The importer pairs CLI tool-use/tool-result IDs and reads host usage; it does not turn the assistant's final success statement into evidence. Missing accounting is `null`, not zero. Interrupted, malformed, mixed-model, or incomplete streams cannot supply a completed comparison. Keep raw transcripts locally and redact before sharing: they may contain sensitive text.

Without a supported transcript, `runner.py verify /absolute/eval/run` still inspects final artifacts. It reports manual execution and unknown usage; TDD sequence remains a failed check without captured tool results. This cannot be used as a measured host comparison. Cold-reader review remains a separate, optional human/independent-reader check for document quality and meaning, not another mandatory approval gate.

## Existing adapter integration

For a trusted local adapter, `run` reuses the existing `skill-eval` process timeout, bounded output, reduced environment, and process-tree termination. A repository-local JSON file supplies an argv array (no shell interpolation):

```json
{"command": ["{python}", "{repo}/path/to/project_owned_driver.py"]}
```

Invoke `runner.py run <prepared-directory> --driver-json <config.json> --model <exact-id> --allow-execution`. One attempt is recorded; retries require a fresh directory. The adapter receives `prompt`, `workspace`, and `model` on stdin, then returns one JSON object:

```json
{
  "status": "completed",
  "host": {"name": "host", "version": "observed-version", "model": "exact-id", "configuration": "matched-settings", "cache": "observed-policy"},
  "metrics": {"input_tokens": null, "output_tokens": null, "tool_calls": null, "wall_time_seconds": null},
  "trace": [{"tool": "Bash", "command": "python check.py", "output": "captured stdout/stderr"}]
}
```

The adapter must capture the host, not ask the model to invent this envelope. Usage is token volume including cache reads/creation, not a dollar estimate. Unknown metrics remain null; elapsed time is bounded below by the runner's observation. The reduced environment does not forward API secrets: use a separately configured, sandboxed host/wrapper with its own authorized authentication. Tools may not alter prepared controls/guidance or the source repository. Failure retains the attempted directory and cannot become a passing cost comparison.

```bash
python evals/tasks/runner.py compare /absolute/eval/commit-none/result.json /absolute/eval/commit-skill/result.json
```

Comparison requires completed runs with matching fixture, evaluator, platform, Python, host/version/model/configuration and cache labels. It reports correctness and metric differences, retaining null for unknown usage. A failed task in a valid control is useful evidence; a failed host execution is not a valid control. Configuration labels and logs are supplied by the experiment operator, not cryptographic attestation. The comparison checks result consistency; it does not authenticate edited result files or independently prove the host's confinement.

## Remaining catalog coverage

Use existing executable tests rather than duplicating them in another runtime:

| Skills | Present evidence / next useful observation |
|---|---|
| `agent-scaffold` | Core/workspace/E2E tests cover files, profiles, rename paths and simulated host payloads; authenticated discovery/hooks need separate host/version runs |
| `conventional-commit`, `spec-writing`, `project-docs-organizer`, `lark-cli`, `tdd` | Outcome fixtures above; route/decision probes remain separate |
| `semver-release` | Planner/extractor tests plus execution of real release shell steps with a mock publisher; real publication is never an evaluation side effect |
| `deep-interview`, `ralph`, `work-protocol` | Existing revision, digest approval, loop, lease, recovery, scope and evidence tests; not proof of task quality |
| `domain-modeling` | Concrete contextual examples and routing probes; review definitions and migrated consumers before a live efficacy claim |
| `best-practice-research`, `tooling-conventions` | Routing probes and inventory tests where applicable; compare real recommendations/commands with a brief-request control before further pruning |

Task JSON artifacts and captured result records reject duplicate keys and non-finite constants,
just like the runner's control files. A later duplicate value cannot erase a contradictory answer.

This fixture set does not certify any host or establish gains for all 13 skills.
