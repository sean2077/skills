---
name: prototype
description: Use when uncertainty should be reduced with a disposable, time-bounded experiment rather than production-ready implementation.
---

# prototype

Build the smallest disposable experiment that resolves a named uncertainty. Optimize for learning, not production completeness, while keeping safety, observability, and cleanup explicit.

## Workflow

1. State the uncertainty as a falsifiable question and the decision the result will inform.
2. Define success, failure, and inconclusive signals before building.
3. Identify what may be faked and what must be real for the experiment to answer the question.
4. Set scope, time/effort bound, data/environment safety, and disposal plan.
5. Build the thinnest end-to-end path that exercises the uncertain seam.
6. Run the experiment and capture inputs, environment, commands, observations, and anomalies.
7. Conclude `supported`, `refuted`, or `inconclusive`; explain what the prototype does not prove.
8. Dispose of or clearly quarantine prototype artifacts unless the user authorizes hardening.

## Output contract

- hypothesis and decision;
- experiment boundary and shortcuts;
- observed evidence;
- conclusion and confidence;
- production gaps and next decision;
- cleanup/quarantine status.

## Hard rules

- Do not silently ship prototype code as production implementation.
- Never use production secrets, destructive data, or unbounded load to gain evidence.
- A demo is not evidence unless its observation discriminates between plausible outcomes.
- Keep one primary uncertainty per prototype; split unrelated questions.
- Do not polish architecture, broad compatibility, or exhaustive tests beyond what the experiment needs.

## On-demand references

- Read [experiment design](references/experiment-design.md) only when choosing a seam, a fake/real boundary, or interpreting an inconclusive result.
