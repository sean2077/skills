# Causal evidence

Establish the observed failure, expected behavior, relevant revision, inputs, and environment. A reliable reproduction strengthens causal claims; when one is unavailable, use the available traces and code while making that limitation explicit.

## Competing explanations

Focus on explanations consistent with the observations and supported by a plausible mechanism. For each leading hypothesis, identify a prediction that distinguishes it from alternatives. Consider disconfirming evidence and update confidence as results arrive.

A controlled reproduction can establish more than a plausible reading of code. Traces and state transitions can locate a failure boundary; tests describe intended contracts only to the extent their assertions and setup cover this case. Logs, history, comments, and names provide leads whose relevance must be checked.

## Discriminating probes

Prefer a safe probe whose possible outcomes change the diagnosis. Track the relevant inputs, identities, state, outputs, and timing across component boundaries. Account for retries, cancellation, concurrency, and stale state when they could explain the same symptom.

Keep read-only investigations read-only. Inspect unfamiliar commands and obtain authority for probes that mutate state or contact consequential external systems.

## Conclusion

Explain the most likely mechanism and supporting observations. Distinguish a confirmed cause from a hypothesis, and identify a useful next observation when material uncertainty remains.
