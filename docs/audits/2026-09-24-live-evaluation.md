# Live model evaluation — 2026-09-24

Historical record. The numbers below describe the revisions, host, and gateway named here; they are not a standing certification. Current measurement procedure lives in [routing probes](../../evals/agent-skills/README.md) and [task outcomes](../../evals/tasks/README.md).

## Setup

| Item | Value |
|---|---|
| Host | Claude Code 2.1.280, Windows 11, Git Bash |
| Model | `claude-opus-5-5`, pinned with `SKILL_EVAL_MODEL` / `--model`; every result records it as the serving model |
| Gateway | Third-party Anthropic-compatible gateway configured in user settings. Its default model is not Claude, so an unpinned run silently evaluates another model. Prompt-cache accounting through it is uncontrolled |
| Routing probes | `skill_eval.py run` over all three `evals/agent-skills/*/suite.json`, per-call cap `SKILL_EVAL_MAX_BUDGET_USD=0.50` |
| Task outcomes | `runner.py prepare` + `claude --bare -p` as in the task README; bare mode loaded only bundled host skills, not the catalog |
| Initial revision | `442fac5` (main `8fe752b` plus the adapter fix below) |
| Final revision | `c28c1b7` (all fixes below) |

Evidence: [`2026-09-24-live-evaluation/`](2026-09-24-live-evaluation/) holds every routing result and task `result.json`. Session transcripts were retained locally and not committed.

## Routing probes

A case passes only when both runs complete, selection/trigger and the expected-behavior subset match, scope holds, and the baseline/treatment cost comparison stays inside the suite budget.

| Suite | Initial pass | Initial decisions correct | Final pass | Final decisions correct |
|---|---|---|---|---|
| agent-scaffold | 19/29 | 21/29 | 19/29 | 28/29 |
| deep-interview | 5/12 | 5/12 | 8/12 | 12/12 |
| lark-cli | 16/17 | 17/17 | 15/17 | 17/17 |

"Decisions correct" excludes cases that failed only a cost budget.

Initial decision failures:

- **agent-scaffold, real skill gap (3 cases).** Without an answer to the one-time domain question, the treatment planned to record the selection and write project guidance in the same turn (first setup and legacy upgrade), and it asked the question during a read-only preview. Both rules existed only in `references/onboarding-selection.md`, which the probe does not load. After the entry point stated them (`c28c1b7`), a targeted rerun and the final run passed all three.
- **agent-scaffold, omitted observation (1 case).** For a recorded empty selection, the treatment reused the selection correctly but did not report `project_guidance_writes`; this persists in the final run.
- **agent-scaffold, label taxonomy (4 cases).** Both arms, or the baseline alone, chose a neighboring workflow label (`analysis` for a scaffold preview or diagnosis, `implementation` for a script rename, `documentation` for a glossary rename). The probe listed 24 bare labels. It now defines the four labels whose boundaries were being guessed; the final run had no label failures.
- **deep-interview, stale expectations (7 cases).** Every substantive decision was correct: approval, persistence, first-turn question counts, and reapproval after edits. The suite still demanded the retired scoring runtime's labels (`mode: adaptive`, `question_batch_policy: adaptive`, `external_research: conditional`), which the current skill does not teach. It now asserts `persistent_state` and the stated research need.

All remaining failures are cost budgets. In the final run, baseline `input_tokens` ranged from about 3.5k to 21k and treatment from about 4k to 24k in every suite, because cache reads and creation are counted and this gateway sometimes reports the cached host prompt and sometimes does not. The fixed `max_additive` of 2,000 input tokens is below that noise, so input-budget failures here are not evidence of skill cost. Treatment outputs are longer mainly because selected runs report many more observation keys.

## Task outcomes

Single runs, except three per arm for the installed-guide pair. All passed except where the table shows the pair's original oracle result.

| Case | Condition | Pass | Input tok | Output tok | Tools | Seconds |
|---|---|---|---|---|---|---|
| lark-invented-syntax | none / skill | ✓ / ✓ | 204k / 144k | 1.8k / 1.5k | 9 / 8 | 46 / 27 |
| lark-stateful-update | none / skill | ✓ / ✓ | 141k / 117k | 0.9k / 1.3k | 6 / 6 | 31 / 24 |
| scaffold-testing-guidance | none / skill | ✓ / ✓ | 58k / 276k | 5.5k / 37.0k | 16 / 45 | 97 / 393 |

With Opus, every task passed without the catalog skill. In its single run, the pinned scaffold skill used about 7× the output tokens, 3× the tool calls and 4× the time of the task-only run for the same verified result.

### v10 installed convention guide pair

`plan-retirement` and `plan-retirement-installed-guide` differ only in `.agents/conventions/docs.md` and its managed route. Both used condition `none`.

| Arm | Run 1 | Run 2 | Run 3 | Read the guide | Mean input tok |
|---|---|---|---|---|---|
| Without guide, original oracle | ✗ | ✗ | ✓ | — | 73k |
| With guide, original oracle | ✓ | ✗ | ✗ | 3/3 | 125k |
| Without guide, corrected oracle | ✓ | ✓ | ✓ | — | |
| With guide, corrected oracle | ✓ | ✓ | ✓ | 3/3 | |

Every original failure was an oracle false negative. The oracle required the retired plan's rationale sentence byte for byte, and the architecture owner's sentence unchanged, including its closing period and no code formatting. Runs that moved the rationale into the owner with light rewording, extended the owner sentence with its reason, or wrapped a path in backticks failed although they did what the guide asks. The corrected oracle judges the rationale and owner statement by meaning after removing inline formatting, and the dated measurement remains verbatim. The retained workspaces were re-scored offline with the corrected oracle; see `tasks/summary.json`.

The route worked: every treatment read the installed guide. The guide produced no measurable improvement on this task for this model, because the baseline already succeeded. Input volume is noisy here and is not a reliable cost estimate. This is one task with three runs per arm; a weaker model or a task whose correct answer depends on a guide-only rule is needed before claiming a benefit or its absence.

## Defects found and fixed

- Evaluation plumbing: the runner's reduced environment dropped `SKILL_EVAL_MAX_BUDGET_USD` and `CLAUDE_BIN`, so those documented knobs never reached the adapter. `host_model` read a field the CLI does not emit. There was no way to pin a model through a remapping gateway.
- Oracles: the plan-retirement exact-wording checks and the stale deep-interview labels above.
- Catalog: agent-scaffold's entry point now keeps an unanswered selection pending and exempts previews.

## Limits

One model, one host, one gateway, and uncontrolled caching. Routing probes show stated decisions from the entry point alone, not native discovery or executed work. Task outcomes are single or triple runs of bounded fixtures. Operator-supplied labels are not attestation.
