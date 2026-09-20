---
name: prototype
description: "Use for a disposable experiment with a falsifiable question and bounded scope. Not for production delivery, an already settled implementation, or unbounded exploration."
---

# prototype

Resolve one material uncertainty with the smallest disposable experiment. Define the question, decision it informs, and success/failure/inconclusive signals before choosing the implementation. Avoid production completeness that does not improve the observation.

## Experiment boundaries

- Bound time or attempts, cost, data, and permitted effects. Reuse project tools and an isolated temporary workspace; inspect unfamiliar commands before execution.
- Distinguish simulated, mocked, and real integrations. Choose an independent oracle: a passing mock of your own assumption is not evidence that the real boundary works.
- Capture enough inputs, environment, and observations to reproduce the result. Adapt only when evidence justifies the next probe; stop once the decision is resolved or the agreed budget is exhausted.
- Keep exploratory work out of production code unless separately authorized. Do not access production, publish, deploy, or mutate shared state merely to make an experiment realistic.
- Remove disposable artifacts you own or identify anything retained with its reason. Do not delete others' work or hide evidence needed for the conclusion.

Report **supported**, **refuted**, or **inconclusive** with the observations, limits, and any next decision. A successful prototype proves only what was actually tested, not production readiness. No separate experiment document or fixed report sections are needed unless the task requires them.

## On-demand references

- Read [experiment design](references/experiment-design.md) when selecting an oracle, isolation boundary, or a probe that separates competing explanations.
