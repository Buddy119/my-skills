# Failure taxonomy policy

## Goal

Create one repository-wide failure registry. Behavior documents reference stable failure IDs; they do not define independent copies that can drift.

## Categories

Use the narrowest supported category:

- Validation
- Authentication
- Authorization
- Business rejection
- Not found
- Conflict
- Dependency rejection
- Dependency unavailable
- Timeout
- Throttling
- Persistence
- Serialization
- Infrastructure
- Poison message
- Partial success
- Compensation failure
- Unknown/unclassified

## Failure record

For each failure record stable ID, category, origin, trigger, affected endpoint/behavior/dependency, observable result, HTTP/error/event/DLQ representation, retry owner, retryability, retry/backoff/DLQ mechanism, state or partial-success impact, rollback/compensation, configuration IDs, status, and evidence.

Distinguish:

- A thrown exception from the consumer-visible response.
- Application retry from AWS/framework retry.
- Retryable cause from an actually configured retry.
- Full rollback from partial state.
- A business rejection from a technical failure.

Do not split a generic `catch` or rethrow region into confirmed lookup, persistence, delivery, or remote failures unless dependency contracts, explicit branches, or tests establish those failure modes. Confirm the observed catch boundary and keep candidate origins inferred or unknown.

A local result containing `statusCode`, `code`, `error`, or a similar literal is not automatically a failure, rejection, HTTP outcome, or business exception. Without deployment/framework integration or a consumer contract, document only the local returned value. Every `FAIL-` manifest entity must bind to a passing `claim_type: failure`; an `output` or `validation` claim alone cannot create a failure entity.

## BA projection

Project only business-visible failures into `ba-pack/business-exception-catalog.md`. Translate them into business condition, impact, visible result, and recovery. Do not expose exception classes, stack details, AWS resource IDs, or unsupported operational intent.

## Completeness

Account for explicit errors, caught exceptions, fallback branches, timeout/retry configuration, DLQs, test assertions, and partial-success paths. Keep framework-generated or opaque errors `Unknown` rather than inventing a status or error envelope.
