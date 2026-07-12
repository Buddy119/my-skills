# External dependency contract policy

## Boundary

Treat anything behaviorally material outside the repository as an external dependency stub: HTTP services, invoked Lambdas, queues, topics, event buses, streams, databases, object stores, shared layers, or libraries whose unavailable implementation controls observable behavior.

Do not infer the dependency's internal behavior. Document only the request, event, resource, response, error, and operational semantics visible from this repository.

For an opaque call, distinguish payload or argument construction, invocation attempt, returned value observed by this repository, and remote side effect. Words such as `save`, `send`, `publish`, or `update` do not prove persistence, delivery, receipt, retry, or downstream processing.

## Dependency matrix and stubs

List all dependencies in `dependency-matrix.md` and mark each `Material: Yes|No`. Create one stub for every material dependency whose contract, availability, or failure can affect a repository outcome. A non-material build or utility dependency may omit a stub when its disposition and reason are recorded.

Each stub records:

- Stable dependency ID, name, type, owner when known, and direction.
- Protocol or AWS interaction and target identity.
- Calling endpoints/behaviors.
- Request/response/event/resource contract visible here.
- Authentication mechanism without credentials.
- Runtime configuration IDs.
- Timeout, retry, backoff, circuit breaker, idempotency, and concurrency when observed.
- Error translation and related failure IDs.
- External HTTP call/mapping IDs when applicable.
- Unknown remote behavior and evidence needed.

## Non-HTTP integrations

For queues, topics, streams, events, and storage, describe message/resource shape and delivery semantics. Do not create external HTTP field mappings for them; use Field Lineage and the dependency stub.

## Completeness

Every external call, publish, enqueue, storage access, or unavailable behaviorally material shared component must have a dependency disposition: documented, duplicate, excluded with reason, or unknown.
