# API contract policy

## Scope

Apply this policy to every discovered inbound endpoint. Reconstruct the consumer-visible contract actually enforced or emitted by the implementation at the recorded commit. Write one endpoint-owned contract at `tech-pack/endpoints/contracts/<endpoint-id>.api-contract.md`. Link it to the endpoint matrix and its primary Tech Behavior. Do not rely on DTO names alone or claim to recover the original published specification.

## Contract-first organization

Organize the document for an API consumer, not by source-evidence type:

1. Endpoint identity, purpose, consumer, security, media types, and idempotency.
2. Request headers, path parameters, query parameters, body schema, validation rules, and example.
3. Response outcomes by HTTP status, success schema, error schema/catalogue, and examples.
4. Consumer-visible semantics such as duplicate requests, concurrency, pagination, timestamps, empty collections, unknown fields, and asynchronous completion when applicable.
5. Open questions and conflicts.
6. An Evidence Appendix containing L1, L2, and L3 evidence.

Remove example rows and irrelevant optional sections from the generated document. Do not present common but unobserved status codes, headers, fields, or error envelopes as supported. Write `None observed`, `N/A`, or `Unknown` where absence or uncertainty matters.

## Input contract

Enumerate every observed input location separately:

- Authentication and behaviorally relevant headers.
- Path parameters.
- Query parameters.
- Request body fields, including nested objects and arrays.

For each field record the exact dotted path, type/format, requiredness, nullability, allowed values or constraints, default, meaning, and status. Use `[]` for array members. Distinguish missing, null, blank, zero, and false when behavior differs.

Record request-level rules such as content type, conditional requiredness, mutual exclusion, cross-field conditions, normalization, and conversion. Include a JSON request example only from supported fields and label it `Partial` when the complete shape is unavailable.

## Output contract

Create a response outcome matrix from observed behavior. For every outcome record:

- Triggering condition or scenario.
- HTTP status.
- Body/schema.
- Relevant headers.
- Consumer retryability when it can be supported.
- Evidence status.

For success fields record exact dotted path, type/format, presence, nullability, source/default, allowed values or output rules, meaning, and status.

Document error body fields and an error catalogue only when the error shape, code, message, or serialization behavior is observable. If an unavailable framework or shared library owns serialization, write `Body shape: Unknown`; never invent a standard error envelope. Include JSON examples only from evidence-supported shapes.

## Consumer-visible semantics

Document idempotency, duplicate request handling, optimistic concurrency, pagination, date/time format and timezone, empty collection representation, unknown field treatment, and timeout/asynchronous completion only when relevant. Mark unavailable semantics `Unknown` rather than deriving them from industry convention.

## Evidence appendix

Keep evidence confidence separate from the consumer-facing contract:

- **L1 — Executable evidence:** Fields or outcomes directly read, validated, defaulted, transformed, written, or returned by executable implementation. This is the strongest evidence.
- **L2 — Schema-level evidence:** Fields declared by request/response models, OpenAPI, JSON Schema, annotations, or generated types without observed runtime use. Label them `Schema-level`.
- **L3 — Shared or opaque evidence:** Fields or errors passing through shared controllers, transformers, generated mappers, reflection, frameworks, or unavailable libraries. Mark exact details `Inferred` or `Unknown` unless inspected.

Provide one coverage table across headers, path, query, request body, success responses, and error responses. Then provide separate L1, L2, and L3 tables. Record executable/schema conflicts explicitly. Do not repeat three evidence layers inside every request and response subsection.

## Evidence and completeness

- Prefer handler/controller, validation, serializer, schema, gateway mapping, and assertion-level test evidence together.
- Treat API Gateway or Lambda integration mappings as part of the contract when present.
- Mark `contract_coverage: partial` when generated models, dynamic schemas, shared libraries, framework errors, or gateway mappings are unavailable.
- Use `contract_status` for conclusion confidence and `contract_coverage` for analyzed surface completeness.
- Keep source citations in the Evidence Appendix and Evidence Index; consumer-facing tables use statuses so they remain readable.
- When multiple endpoints share a handler or behavior, preserve separate endpoint rows. Use `contract_alias_of` only when their complete observable contracts are equivalent; do not collapse endpoints merely because implementation is shared.
