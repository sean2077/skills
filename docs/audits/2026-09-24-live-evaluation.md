# Live model evaluation — 2026-09-24

Historical record. The numbers below describe the revisions, host, gateway and models named here; they are not a standing certification. Current measurement procedure lives in [routing probes](../../evals/agent-skills/README.md) and [task outcomes](../../evals/tasks/README.md).

## Setup

| Item | Value |
|---|---|
| Host | Claude Code 2.1.280, Windows 11, Git Bash |
| Models | `claude-opus-5-5` and `deepseek-v4.1-flash`, each pinned with `SKILL_EVAL_MODEL` / `--model`; every result records the model that actually served it |
| Gateway | Third-party Anthropic-compatible gateway configured in user settings. Its default model is not Claude, so an unpinned run silently evaluates another model. Prompt-cache accounting through it is uncontrolled |
| Routing probes | `skill_eval.py run` over all three `evals/agent-skills/*/suite.json`, per-call cap `SKILL_EVAL_MAX_BUDGET_USD=0.50` |
| Task outcomes | `runner.py prepare` plus `claude --bare -p`, following the task README. Bare mode loaded only bundled host skills, not the catalog |

Evidence is in [`2026-09-24-live-evaluation/`](2026-09-24-live-evaluation/). Folders are named by model and the revision each run evaluated. `routing/rechecks/` holds targeted reruns; `122c13b` was an experimental lark wording change that was discarded after these reruns. `tasks/summary.json` re-scores every task run with the final evaluator and counts `Bash` calls. Session transcripts were retained locally and are not committed.

## Routing probes

A case passes when both runs complete, the treatment's selection and expected behavior match, scope holds, and the baseline/treatment cost comparison stays inside the suite budget. A baseline's workflow label is reported but does not fail a case.

Treatment decisions correct at each revision:

| Suite | Opus `442fac5` | Opus `c28c1b7` | deepseek `d8bda75` | Opus final `86fcf5c` | deepseek final `86fcf5c` |
|---|---|---|---|---|---|
| agent-scaffold (29) | 23 | 28 | 27 | 27 → 28¹ | 28 → 29¹ |
| deep-interview (12) | 5 | 12 | 7 | 12 | 11 |
| lark-cli (17) | 17 | 17 | 15 | 17 | 15 |

¹ After `00e360e` corrected the `decision_artifact` observation; see the rechecks.

Remaining final failures:

| Model | Case | Nature |
|---|---|---|
| Opus | agent-scaffold `positive-recorded-none` | Correct reuse of an empty selection, but it omits the `project_guidance_writes` observation |
| deepseek | deep-interview `positive-adaptive-material-edit` | Reports `persistent_state: true` for a conversational interview despite the clarified meaning |
| deepseek | lark-cli `positive-file-containment` | Reports `file_access_outside_cwd: true`. Asked directly with the same `SKILL.md` (original wording, three times; clarified wording, three times), it refused the `../` path and proposed running from the file's directory every time. This is how it reads the observation label, not its decision |
| deepseek | lark-cli `positive-identity-permission-boundary` | Chooses the `analysis` workflow label instead of `lark` |

Other failing cases failed only cost budgets. Baseline `input_tokens` ranged from about 3.5k to 21k, and treatment from about 4k to 24k, in every suite and for both models. That spread comes from cache reads and cache creation being counted, and from the gateway sometimes reporting the cached host prompt and sometimes not. The fixed `max_additive` of 2,000 input tokens is smaller than that noise, so input-budget failures here are not evidence of skill cost. Treatment outputs are longer mainly because selected runs report many more observation keys.

### What the probes found

- **agent-scaffold: pending selection (fixed in `c28c1b7`).** Without an answer to the one-time domain question, both models planned to record the selection and write project guidance while asking. Opus also asked during a read-only preview. The rules existed only in `references/onboarding-selection.md`, which the probe does not load. The entry point now states them. deepseek still planned the writes until the probe said that write decisions describe what happens before the user answers.
- **deep-interview: byte-exact reapproval (fixed in `af3cd91`).** deepseek judged that a whitespace-only edit to an approved runtime specification needed no reapproval. The exact-bytes rule lived only in the runtime reference. The entry point now states it, and the case passes for both models.
- **deep-interview: stale probe labels (fixed in `c28c1b7`).** Opus made every substantive decision correctly but failed on the retired runtime's labels (`mode: adaptive`, `question_batch_policy: adaptive`, `external_research: conditional`), which the current skill no longer teaches. The suite now asserts `persistent_state` and the stated research need.
- **Probe vocabulary (fixed in `c28c1b7` and later).** Both models guessed between neighboring workflow labels, read boolean observations as properties of the request rather than their own action, and read `persistent_state` as "the conversation continues". The adapter now defines four workflow labels, says that booleans describe the agent's own action, and defines `persistent_state`. Making the boolean rule explicit briefly turned `decision_artifact`, which expects a record name, into `true` for both models. `00e360e` removed it from the boolean list.

## Task outcomes

Opus ran each case once, except three runs per arm for the installed-guide pair. deepseek did the same, and its host-failed run was retried once.

| Case | Condition | Opus | deepseek |
|---|---|---|---|
| lark-invented-syntax | none / skill | ✓ / ✓ | ✓ / ✓ |
| lark-stateful-update | none / skill | ✓ / ✓ | ✓ / ✓ |
| scaffold-testing-guidance | none / skill | ✓ / ✓ | ✓² / ✗³ |

² The first none run ended with a truncated host stream after the model started a background task; the retry passed.
³ The skill run merged `quality-decisions.md` into the development guide, then deleted it. The oracle protects that file. The prompt says to "consolidate" it and to "preserve … all other files", which allows either reading, so this is a fixture ambiguity rather than a clear skill defect.

With Opus, the pinned scaffold skill's single guidance run used about 7× the output tokens, 3× the tool calls and 4× the time of the task-only run, for the same verified result.

The scaffold guidance and plan-retirement prompts say not to execute commands. Opus made no `Bash` calls in any of those runs. deepseek ran commands (`ls`, `find`, `cat >`, `rm`) in 5 of its 9 such runs. The oracles cannot observe this; transcript review found it.

### v10 installed convention guide pair

`plan-retirement` and `plan-retirement-installed-guide` differ only in `.agents/conventions/docs.md` and its managed route. Both arms used condition `none`, with three runs per arm per model.

| Model / arm | Passed at run | Passed re-scored | Read the guide |
|---|---|---|---|
| Opus without guide | 1/3 | 3/3 | — |
| Opus with guide | 1/3 | 3/3 | 3/3 |
| deepseek without guide | 1/3 | 3/3 | — |
| deepseek with guide | 3/3 | 3/3 | 3/3 |

Every failure at run time was an oracle false negative. Opus runs failed because the oracle demanded the rationale sentence and the architecture owner's sentence byte for byte. deepseek runs had the earlier fixes but failed because the owner sentence's source path had become a Markdown link. The runs had preserved the rationale with light rewording, extended the owner sentence with its reason, or formatted or linked the path, which is what the guide asks. The final oracle compares prose after removing inline code, emphasis and link syntax. It still requires the rationale's decision and reason in one paragraph, the owner statement, and the dated measurement verbatim.

The route worked: every treatment run read the installed guide. On this task neither model improved measurably, because both already succeeded without the guide. The deepseek run-time difference came only from link formatting. This pair cannot show a benefit. That needs a task whose correct result depends on a rule only the guide states.

## Defects found and fixed

- **Catalog.** agent-scaffold's entry point keeps an unanswered selection pending and exempts previews. deep-interview's entry point states that any byte change to an approved runtime specification needs fresh approval.
- **Evaluation plumbing.** The runner's reduced environment dropped `SKILL_EVAL_MAX_BUDGET_USD` and `CLAUDE_BIN`, so those documented knobs never reached the adapter. `host_model` read a field the CLI does not emit. There was no way to pin a model through a remapping gateway.
- **Oracles and probes.** The plan-retirement exact-wording checks, the stale deep-interview labels, and the ambiguous probe vocabulary described above.

## Open

- The installed-guide pair needs a discriminating task.
- The `scaffold-testing-guidance` prompt should say whether the consolidated source file stays.
- Input-token budgets need an allowance that reflects cache-accounting noise, or a cache-controlled host.
- Task oracles cannot see command execution that a prompt forbids.

## Limits

This covers two models on one host and one gateway, with uncontrolled caching. Routing probes show decisions stated from the entry point alone, not native discovery or executed work. Task outcomes are one or three runs of bounded fixtures. Operator-supplied labels are not attestation.
