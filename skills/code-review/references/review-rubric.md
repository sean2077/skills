# Review rubric

## Severity and confidence

Rank severity by consequence and reachable scope, separately from confidence:

- **Critical:** a credible path to catastrophic loss, compromise, or outage.
- **High:** substantial correctness, security, data, or availability impact in a supported path.
- **Medium:** a bounded but meaningful failure that warrants correction.
- **Low:** a minor defect with limited impact.

Explain the actual consequence rather than relying on the label.

## Supported findings

A finding identifies the changed behavior, a reachable trigger, the resulting failure, and a precise location. Check why existing guards or tests do not eliminate the concern. Offer a correction when known; identifying a defect does not require already knowing its solution.

Use questions for unresolved intent and preferences for stylistic alternatives. State meaningful evidence gaps rather than presenting speculation as a confirmed defect.

## Risk-directed inspection

Follow relevant trust, identity, ownership, concurrency, cancellation, retry, persistence, compatibility, packaging, and rollback boundaries. Choose checks from the change's failure modes and supported environments.
