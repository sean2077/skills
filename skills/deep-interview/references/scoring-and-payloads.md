# Scoring and payloads

Read this only when preparing the first topology/score submission or after the runtime rejects a payload.

## Topology payload

```json
{
  "schema": "agent-interview-topology/1",
  "components": [
    {"id": "api", "name": "API", "description": "public behavior", "status": "active", "evidence": ["user requested an API"]},
    {"id": "worker", "name": "Worker", "description": "background behavior", "status": "active", "evidence": ["user requested processing"]},
    {"id": "later-ui", "name": "UI", "description": "future surface", "status": "deferred", "evidence": []}
  ],
  "deferrals": [{"component_id": "later-ui", "reason": "user-confirmed deferral"}]
}
```

IDs are lowercase slug-like values, unique, and stable. There must be at least one active component. Every deferred component needs exactly one deferral reason; active components must not appear in deferrals.

## Required dimensions

Greenfield: `problem`, `users`, `scope`, `behavior`, `acceptance`, `constraints`, `risks`. Brownfield adds `context`.

Score each required dimension for every active component from `0.0` to `1.0`:

- `0.0`: absent or contradictory;
- `0.25`: hinted but decision-bearing ambiguity remains;
- `0.5`: usable direction with material gaps;
- `0.75`: specific and testable with minor gaps;
- `1.0`: explicit, evidenced, and internally consistent.

## Round payload

```json
{
  "schema": "agent-interview-round/1",
  "round": 1,
  "target": {"component": "api", "dimension": "problem"},
  "question": "Which user-visible problem must this solve first?",
  "answer": "[from-user] ...",
  "component_scores": {
    "api": {"problem": 0.75, "users": 0.5, "scope": 0.25, "behavior": 0.25, "acceptance": 0.0, "constraints": 0.25, "risks": 0.0},
    "worker": {"problem": 0.75, "users": 0.5, "scope": 0.25, "behavior": 0.25, "acceptance": 0.0, "constraints": 0.25, "risks": 0.0}
  },
  "evidence": {
    "api": {"problem": ["user answer"], "users": ["initial brief"], "scope": ["confirmed boundary"], "behavior": ["confirmed flow"], "acceptance": ["acceptance example"], "constraints": ["repository constraint"], "risks": ["named risk"]},
    "worker": {"problem": ["user answer"], "users": ["initial brief"], "scope": ["confirmed boundary"], "behavior": ["confirmed flow"], "acceptance": ["acceptance example"], "constraints": ["repository constraint"], "risks": ["named risk"]}
  }
}
```

Round numbers are contiguous. `target` is the `{component, dimension}` pair reported by status `next_target`. Submit every required dimension for every active component; deferred components are excluded. Every changed component/dimension score needs at least one non-empty evidence item.

## Mechanical formula

The runtime computes per-dimension minima across active components, then `ambiguity = 0.6 × (1 - mean(dimension minima)) + 0.4 × (1 - min(dimension minima))`, rounded to four decimals. The gate passes when ambiguity is at or below the resolved threshold and every dimension minimum is at least `0.5`. Tied weakest `{component, dimension}` pairs rotate by least-recently targeted, then stable component and dimension order.
