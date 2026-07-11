# Data lifecycle policy

## Scope

Explain where repository-visible data originates, how it is validated and transformed, where it is read or written, what state changes, and where it leaves the repository. Separate business state from storage representation and temporary in-memory transformations.

## Data assets

Create a stable data asset for every behaviorally relevant database/table, object collection, file/bucket, cache, parameter, secret reference, inbound message, outbound event, or durable external record visible to this repository. Do not treat ordinary local variables as data assets.

For each asset record type, logical name, ownership boundary, key or identity, read/write behaviors, lifecycle role, retention/TTL when observed, and evidence status. Record secret names only; never retrieve or reproduce values.

## Data lineage

Trace repository-visible flows as:

`source boundary → validation/normalization → internal representation → read/write → emitted response/event/external call`.

Record transformation, condition, default, lossiness, affected field/rule IDs, behavior IDs, and evidence. Use `Unknown` for opaque serializers, reflection, shared layers, or unavailable schemas.

Internal lineage is not an upstream/downstream field mapping. Reserve `external HTTP mapping` for the boundary defined by the field-mapping policy.

## State transitions

Create a state transition only when code, tests, schema, or persistence logic identifies a state before and after an action. Record:

- Data object and state field.
- From state, including `Any`, `Absent`, or `Unknown` when appropriate.
- Triggering behavior and rule/condition.
- To state.
- Persistence write and emitted side effects.
- Transaction boundary, rollback, partial state, idempotency, and concurrency when visible.
- Status and evidence.

Do not turn any database update into a business state transition. When only storage mutation is known, describe it as a persistence change and leave business meaning `Unknown`.

## Completeness

Account for every read, write, emitted event, and external call found during behavior tracing. If no state machine exists, keep the state transition matrix and state `None observed`; do not invent states.
