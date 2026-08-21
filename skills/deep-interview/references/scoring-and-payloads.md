# Scoring and payloads

Read this only when preparing the first topology/score submission, handling ontology or challenge behavior, or responding to payload rejection.

## Topology payload

```json
{
  "schema": "agent-interview-topology/2",
  "components": [
    {
      "id": "api",
      "name": "API",
      "description": "public request behavior",
      "status": "active",
      "evidence": ["[from-user] an API is required"]
    },
    {
      "id": "later-ui",
      "name": "UI",
      "description": "future interface",
      "status": "deferred",
      "evidence": ["[from-user] explicitly deferred"]
    }
  ],
  "deferrals": [
    {"component_id": "later-ui", "reason": "outside this decision"}
  ]
}
```

IDs are unique lowercase slug-like values. Use one to six components and at least one active component. Deferrals must cover exactly the deferred IDs.

## Dimensions and ambiguity

Each active component receives every dimension from `0.0` to `1.0`:

- `0.0`: absent or contradictory;
- `0.25`: hinted, with decision-bearing ambiguity;
- `0.5`: usable direction with material gaps;
- `0.75`: specific/testable with minor gaps;
- `1.0`: explicit, evidenced, and internally consistent.

Greenfield dimensions are `goal`, `constraints`, and `criteria`. Brownfield adds `context`.

For each dimension, the runtime takes the minimum score across active components. It then computes:

```text
greenfield ambiguity = 1 - (goal×0.40 + constraints×0.30 + criteria×0.30)
brownfield ambiguity = 1 - (goal×0.35 + constraints×0.25 + criteria×0.25 + context×0.15)
```

The weakest target is the lowest component × dimension pair. Exact ties rotate away from the last targeted component when possible, then use stable component/dimension order.

## Question routing and cadence

Inspect safe code, configuration, documentation, and bounded research before asking the user for discoverable facts. Ask a `[from-user]` question only when its answer can change a CRITICAL axis: scope boundary, acceptance criterion, rollback contract, lane assignment, or handoff target. Otherwise record a conservative default plus its revisit trigger in the answer.

For each user-owned question, offer 2–4 concrete choices plus free text. Mark exactly one `Recommended` only when inspected evidence favors it and cite that evidence briefly; otherwise state `No reliable default`. A casual “yes”, “ok”, or “proceed” answers only the current question and does not approve the final specification.

After two consecutive rounds whose answers do not contain `[from-user]`, the runtime sets `metrics.cadence_user_required` and refuses another non-user round. Ask the decision nearest the current weakest target rather than inventing a low-value question.

## Round payload

```json
{
  "schema": "agent-interview-round/2",
  "round": 1,
  "question": "Which failure must this API prevent first?",
  "answer": "[from-user] Requests must retain order.",
  "pressure_pass": true,
  "component_scores": {
    "api": {
      "goal": 0.75,
      "constraints": 0.50,
      "criteria": 0.50
    }
  },
  "ontology": {
    "entities": [
      {
        "name": "Request",
        "type": "entity",
        "fields": ["id", "sequence"],
        "relationships": ["processed by API"]
      }
    ]
  }
}
```

Round numbers are contiguous. Scores must cover every active component and exactly the dimensions for the chosen interview type. `pressure_pass` records that the answer was challenged for counterexamples, boundary conditions, or a concrete acceptance example rather than accepted at face value.

## Ontology stability

Each round snapshots up to 50 named/type entities with bounded fields and relationships. The runtime records the matching explanation and a stability ratio. Exact name/type matches are stable; same-type entities with more than 50% field overlap are changed; unmatched entities are new/removed. The first snapshot has no ratio.

Use ontology drift to expose term renames, implicit entities, contradictory ownership, or unstable boundaries. It informs questions; it does not independently pass the ambiguity gate.

## Challenge modes and stall

The runtime suggests each mode at most once under normal progress:

- `contrarian` from round 4;
- `simplifier` from round 6;
- `ontologist` from round 8 while ambiguity remains above `0.30`.

Submit the adopted suggestion as `"challenge_mode_used": "<mode>"`. When the last three ambiguity values span no more than `0.05` and remain above threshold, stall escalation requires `ontologist` on the next round. The ontologist stance may repeat while that stall remains; its usage history stays deduplicated.

## Gate and spec content

`gate` returns exit `4` while ambiguity exceeds threshold. `waive` is a deliberate user-accepted exception, not an automatic escape from the 20-round cap.

`crystallize` accepts only an existing regular UTF-8 file inside the bound worktree/root, rejects symlink traversal, and validates these non-empty headings (English or supported Chinese aliases): Goal, Topology, Constraints, Non-goals, Decision Boundaries, Acceptance Criteria, Ontology, and Open Assumptions. Decision Boundaries must name an owner and revisit/trigger condition. A waived run also needs Remaining Gaps or Remaining Risks.

The file must contain `pending approval` (or the supported Chinese marker). `approve` records explicit evidence separately. `complete` re-reads the file and rejects a changed digest; re-run `crystallize`, obtain fresh approval, and then complete.
