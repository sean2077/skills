---
name: analyze
description: Use when a repository-local question needs read-only cross-file explanation; use trace for causal failures and direct reading for one-file facts.
---

# analyze

Answer repository questions through read-only evidence gathering. Return a ranked synthesis that separates facts, inferences, and unknowns; do not edit code or turn the answer into an implementation plan.

## Workflow

1. Restate the exact question and the decision the answer should enable.
2. Bound the search to relevant entry points, callers, data paths, configuration, tests, and history.
3. Read the smallest useful set of artifacts, expanding only when evidence crosses a boundary.
4. Build a claim ledger: claim, source path and symbol or line, confidence, and whether it is fact or inference.
5. Look for contradictory evidence and explain why it does or does not change the ranking.
6. Return the synthesis using the output contract below.

## Output contract

1. **Answer** — the direct conclusion in a few sentences.
2. **Ranked findings** — strongest first, each with repository evidence.
3. **How the parts connect** — the relevant control/data/configuration path.
4. **Uncertainties** — facts not established by the repository.
5. **Next read-only probe** — at most one, only when it could materially change the answer.

## Hard rules

- Read-only means no edits, generated files, commits, or configuration changes.
- Do not present an inference as code-proven fact.
- Prefer current code and executable tests over comments; use history only to explain intent or evolution.
- Do not use this skill for a reproducible failure that needs causal hypothesis ranking; use `trace`.
- Do not expand into generic best-practice research unless the question requires external evidence.

## On-demand references

- Read [evidence and synthesis](references/evidence-and-synthesis.md) only when evidence conflicts, the answer spans several boundaries, or confidence needs explicit calibration.
