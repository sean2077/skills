# Evaluation contract

Read this only when authoring or debugging a `skill-eval` manifest, adapter, verifier, CI gate, or result consumer.

## Suite manifest

Paths are repository-relative. Commands are argv arrays; supported placeholders are `{python}`, `{repo}`, `{workspace}`, `{mode}`, and `{case_id}`.

```json
{
  "schema_version": 1,
  "suite_id": "tdd-behavior",
  "skill_path": "skills/tdd",
  "fixture": "evals/examples/tdd/fixture",
  "adapter": {
    "command": ["{python}", "{repo}/evals/examples/tdd/fake_adapter.py"],
    "timeout_seconds": 30,
    "max_output_bytes": 262144
  },
  "verifier": {
    "command": ["{python}", "{repo}/evals/examples/tdd/verifier.py"],
    "timeout_seconds": 30,
    "max_output_bytes": 262144
  },
  "scope": {"allow": ["src/**", "tests/**"], "deny": [".git/**", ".agents/**"]},
  "budgets": {
    "absolute": {"interventions": 0},
    "relative": {"input_tokens": {"max_ratio": 1.5, "max_additive": 0}}
  },
  "cases": [
    {"id": "positive", "kind": "positive", "prompt": "Implement with TDD."},
    {"id": "negative", "kind": "negative", "prompt": "Explain only."},
    {"id": "neighbor", "kind": "confusable", "prompt": "Review without editing."}
  ]
}
```

`kind` is `positive`, `negative`, or `confusable`. `expected_selected` defaults to true only for positive cases. An explicit repository revision may be supplied; otherwise the runtime resolves `HEAD` once before the suite. The resolved commit is materialized as a clean detached Git worktree, and every fixture, skill, adapter, and verifier path is resolved there rather than in the caller's possibly dirty worktree. When the resolved revision is current `HEAD`, the manifest itself must match the committed copy; commit suite changes before running. A manifest explicitly targeting an older commit may remain a current control file, but every repository-relative path it names must exist in that older commit.

## Adapter request and response

The adapter receives one JSON request on stdin. `mode` is `baseline` or `treatment`; `repository_root` is the absolute detached-revision root, and `skill_path` is an absolute path below it for treatment or null for baseline. It returns exactly one bounded JSON object:

```json
{
  "schema_version": 1,
  "contract": "agent-skill-eval/v1",
  "run_id": "copied exactly",
  "mode": "treatment",
  "selected": true,
  "status": "completed",
  "metrics": {
    "input_tokens": 1200,
    "output_tokens": 400,
    "tool_calls": 8,
    "wall_time_seconds": 12.5,
    "interventions": 0
  },
  "metadata": {}
}
```

All five metrics are required. Report observed values; do not omit or estimate token and tool counts when the host exposes exact accounting. The runtime clamps wall time to at least the independently measured elapsed time. Adapter metadata containing secret-like keys is rejected. The adapter may modify only the isolated workspace; mutations elsewhere in the detached repository fail with exit `20`.

Adapter and verifier commands are trusted local executables selected by the suite author. The runtime uses argv execution with `shell=False`, a reduced environment, time/output bounds, process-tree termination, detached-revision checks, and mutation detection; it is not an operating-system sandbox and does not claim to block network or arbitrary host access by a malicious command.

## Verifier response

The verifier receives the case, mode, workspace, absolute detached `repository_root`, treatment `skill_path` when applicable, adapter result, changed paths, fixture digest, revision, and repository snapshot digest. It must not mutate either the workspace or any other repository path.

```json
{
  "schema_version": 1,
  "contract": "agent-skill-eval/v1",
  "run_id": "copied exactly",
  "passed": true,
  "checks": [{"name": "tests", "passed": true, "message": "all passed"}]
}
```

Use executable tests, static checks, or exact artifact assertions. A model judgment may be an additional metric, but it must not replace the deterministic correctness gate.

## Exit classes

- `0`: validation or suite passed.
- `2`: invalid CLI usage.
- `3`: invalid manifest, path, schema, or incomparable pair, including repository snapshot drift.
- `20`: adapter start, timeout, output, exit, or protocol failure.
- `21`: verifier failure or mutation.
- `30`: a valid suite failed trigger, correctness, scope, or budget gates.

The repository includes an offline example at `evals/examples/tdd/`.

After persisting a suite result, run `skill_eval.py validate-result <result.json>` to recompute every stored baseline/treatment comparison and reject tampered comparisons or inconsistent summary counts.
