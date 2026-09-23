# Task outcome checks

These opt-in fixtures inspect what an Agent actually changes, separately from [routing probes](../agent-skills/README.md). They prepare, execute, and inspect one task; they are not a scheduler, delivery workflow, or new catalog skill.

## What is checked

| Case | Observations | Limit |
|---|---|---|
| `commit-hunks` | Commit tree/parent, same-file staged hunk, another staged file, unstaged changes | One bounded Git scenario |
| `spec-preservation` | Owned clauses, exact values, draft status, unresolved question, revised overview | Not complete semantic accuracy or reader comprehension |
| `docs-move` | Unique content and incoming/outgoing relative links/anchors | The fixture's Markdown subset, not a general repository link validator |
| `lark-unknown-write` | Local mock: one send and same-identity readback | No network or live CLI/service certification; writable logs are not tamper-proof |
| `lark-invented-syntax` | Mock calls, collection observation, and correct awaiting-reply count in `answer.json`; rejects unsupported flags/identities/IDs | Cooperative mock evidence, not adversarial execution proof or model effectiveness |
| `tdd-negative-input` | Captured missing-behavior RED at original source, then GREEN with unchanged tests/final hashes and an independent behavior check | Final answers and Agent-authored logs cannot replace missing sequence evidence |

The syntax task-only prompt states the task and points to command documentation; the brief condition adds syntax guidance separately. Reading help or one message is insufficient: valid mock use must also produce the requested count.

CI's `scripts/tests/test_task_outcomes.py` exercises good/bad reference actions to test the fixtures and oracles, **not model performance**. `scripts/tests/test_release_execution.py` separately runs repository-owned release shell steps with real Git and a mock publisher; it never publishes. Task answers and captured JSON records reject duplicate keys and non-finite constants, as control files do.

## Prepare a matched experiment

Use an authorized, disposable, credential-limited environment outside this checkout. Each run creates a separate Git repository and refuses an existing output directory. Choose `none` (task only), `brief` (task plus short instruction), or `skill` (task plus a pinned complete skill payload, including references). This measures explicit application, not native discovery.

```bash
python evals/tasks/runner.py prepare commit-hunks /absolute/eval/commit-none --condition none
python evals/tasks/runner.py prepare commit-hunks /absolute/eval/commit-brief --condition brief
python evals/tasks/runner.py prepare commit-hunks /absolute/eval/commit-skill --condition skill --skill-revision HEAD
```

Run these commands from the evaluator's checkout. Commit intended skill changes before using `HEAD`: payloads come from Git, not dirty files. For old/new comparisons, use two full skill commit IDs with the same fixture/evaluator; the evaluator hash is recorded separately. Match run order, model, effort, permissions, plugin/memory configuration, cache conditions, and interventions, recording deviations. A brief request is a legitimate control. Repeated held-out tasks are needed for a stable-advantage claim.

Give the subject only `prompt.txt`, the fixture workspace, and named guidance. Keep `fixture.json`, evaluator source, expected checks, transcripts, and results out of its workspace/context. The runner, a worktree, or a separate Git repository is **not an OS sandbox**. Use effective filesystem/network/credential isolation when required; never evaluate against production resources.

## Execute with an existing host

A host can work in the prepared `workspace/`. This manual Claude Code example is based on its [CLI reference](https://code.claude.com/docs/en/cli-reference) and [programmatic mode](https://code.claude.com/docs/en/headless), reviewed 2026-09-22, not a live-host certification. It requires an authenticated CLI supporting these flags. Bare mode excludes ambient skills/hooks/memory; do not silently drop it to accommodate an unsupported version. A live run may incur model usage.

Run from the evaluator checkout in Bash/Git Bash after setting an exact `CLAUDE_MODEL_ID` and the actually observed `CLAUDE_CACHE_CONDITION`. Do not label a run cold merely because this is its first local attempt.

```bash
(
  set -e
  # Bash tool permission permits execution; it does not provide a sandbox.
  : "${CLAUDE_MODEL_ID:?Set an exact model ID, not a moving alias}"
  : "${CLAUDE_CACHE_CONDITION:?Describe the actual observed cache condition}"
  run=/absolute/eval/commit-skill
  test -d "$run/workspace"
  printf 'Retained task output: %s\n' "$run"
  claude --version > "$run/host-version.txt"
  start=$(python -c 'import time; print(time.monotonic())')
  status=0
  (
    cd "$run/workspace" || exit 1
    claude --bare -p --model "$CLAUDE_MODEL_ID" --no-session-persistence \
      --permission-mode dontAsk --tools "Bash,Read,Edit,Write" \
      --allowedTools "Bash,Read,Edit,Write" --output-format stream-json --verbose \
      < "$run/prompt.txt" > "$run/session.jsonl" 2> "$run/host-stderr.txt"
  ) || status=$?
  elapsed=$(python -c 'import sys,time; print(time.monotonic()-float(sys.argv[1]))' "$start")
  python evals/tasks/import_claude.py "$run/session.jsonl" "$run/driver.json" \
    --version-file "$run/host-version.txt" --model "$CLAUDE_MODEL_ID" \
    --configuration bare-local-tools --cache-condition "$CLAUDE_CACHE_CONDITION" \
    --elapsed-seconds "$elapsed" --exit-code "$status"
  python evals/tasks/runner.py verify "$run" --driver-result "$run/driver.json" > "$run/result.json"
)
```

Inspect session initialization for unexpected configuration/tools. The importer pairs tool-use/result IDs and captures host usage; it does not accept the assistant's success statement as execution evidence. Unknown accounting is `null`, not zero. Interrupted, malformed, mixed-model, or incomplete streams cannot form a completed comparison. Retain failure output and raw transcripts locally; redact sensitive content before sharing, including stderr.

Without a supported transcript, `runner.py verify /absolute/eval/run` still checks final artifacts, but reports manual execution and unknown usage. TDD sequence fails without captured tool results; this is not a measured host comparison. Cold-reader review is a separate optional check of meaning and usability, not an approval gate.

## Existing adapter integration

A trusted local adapter can use `run` with the existing process timeout, bounded output, reduced environment, and process-tree termination. A repository-local JSON configuration supplies argv, with no shell interpolation:

```json
{"command": ["{python}", "{repo}/path/to/project_owned_driver.py"]}
```

Invoke `runner.py run <prepared-directory> --driver-json <config.json> --model <exact-id> --allow-execution`. One attempt is recorded; retries need a fresh directory. The adapter receives `prompt`, `workspace`, and `model` on stdin and returns one JSON object:

```json
{
  "status": "completed",
  "host": {"name": "host", "version": "observed-version", "model": "exact-id", "configuration": "matched-settings", "cache": "observed-policy"},
  "metrics": {"input_tokens": null, "output_tokens": null, "tool_calls": null, "wall_time_seconds": null},
  "trace": [{"tool": "Bash", "command": "python check.py", "output": "captured stdout/stderr"}]
}
```

Capture the host; do not ask the model to invent this envelope. Token volume includes cache reads/creation and is not a dollar estimate. Unknown metrics stay null; the runner bounds elapsed time below by its own observation. The reduced environment does not forward API secrets; use a separately configured sandboxed host/wrapper with authorized authentication. Tools must not alter prepared controls/guidance or the source repository. Failure retains the attempt and cannot become a passing cost comparison.

```bash
python evals/tasks/runner.py compare /absolute/eval/commit-none/result.json /absolute/eval/commit-skill/result.json
```

Comparison requires completed runs matching fixture, evaluator, platform, Python, host/version/model/configuration, and cache labels. It reports correctness and metric differences, retaining null for unknown usage. A failed task in a valid control is evidence; a failed host is not a valid control. Operator-supplied labels/logs are not attestation: consistent files do not authenticate edited results or prove confinement and matched conditions.

## Remaining catalog coverage

Reuse existing checks rather than duplicating them in another runtime:

| Skills | Evidence / next useful observation |
|---|---|
| `agent-scaffold` | Core/workspace/E2E files, profiles, moves, and simulated host payloads; authenticated discovery/hooks need separate versioned runs |
| `conventional-commit`, `spec-writing`, `project-docs-organizer`, `lark-cli`, `tdd` | Outcome fixtures above; decision probes remain separate |
| `semver-release` | Planner/extractor tests and real release shell execution with a mock publisher; real publication is never an evaluation side effect |
| `deep-interview`, `work-protocol` | Revision, digest, lease, recovery, scope, and evidence tests; not proof of task quality |
| `domain-modeling` | Contextual examples and routing probes; inspect definitions and migrated consumers before efficacy claims |
| `best-practice-research`, `tooling-conventions` | Probes and applicable inventory tests; compare actual recommendations/commands with a brief control before further pruning |

This fixture set does not certify a host or establish gains for all 12 skills.
