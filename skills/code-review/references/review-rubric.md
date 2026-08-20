# Review rubric

Read this only when calibrating severity, reviewing a high-risk boundary, or deciding whether a concern is actionable rather than stylistic.

## Severity

- **Critical:** plausible data loss, secret exposure, remote compromise, broad authorization bypass, or unrecoverable production impact.
- **High:** incorrect behavior on an important path, durable corruption, tenant/user isolation failure, or release-blocking regression.
- **Medium:** bounded functional defect, reliability degradation, compatibility break, or maintenance trap likely to cause defects.
- **Low:** real but narrow defect with limited impact. Do not use Low for preference-only feedback.

Severity combines impact and reach, not reviewer confidence. State confidence separately.

## Actionability gate

A finding survives only when the review can name: changed or newly exposed behavior; triggering condition; consequence; supporting code path; and a bounded correction direction. Otherwise present it as an open question or residual risk.

## Boundary checklist

Check trust transitions, authorization, serialization, retries/idempotency, partial writes, concurrency, cancellation, migration order, version negotiation, resource cleanup, observability, and rollback only where the change touches those concerns.
