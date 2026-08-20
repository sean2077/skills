# Evidence and synthesis

Read this only when an analysis spans several boundaries, sources conflict, or the conclusion needs explicit confidence calibration.

## Evidence order

Prefer, in order: observed runtime/test output; executable behavior and invariants; configuration actually loaded; caller/callee contracts; focused tests; current documentation; comments; history; naming alone.

A lower-ranked source may still win when it is the only source addressing the exact condition. Say why.

## Claim ledger

For every load-bearing claim record:

- the claim;
- path plus symbol, section, or focused line range;
- `fact`, `inference`, or `unknown`;
- evidence for and against;
- confidence and the observation that would change it.

Merge claims that describe the same mechanism. Keep distinct claims separate when they imply different behavior or probes.

## Synthesis discipline

Lead with the answer, not the browsing history. Explain the minimum causal or ownership chain needed for the reader to understand the result. Mention files because they support a claim, not as an inventory dump.
