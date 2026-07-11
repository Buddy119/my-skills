---
endpoint_id: "EP-POST-resource"
primary_behavior_id: "repository.behavior-name"
title: "Human-readable API operation title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
entry_point: "handler-or-route"
operation_id: "operationName-or-unknown"
method: "GET|POST|PUT|PATCH|DELETE|other"
route: "/normalized/route"
contract_status: "Confirmed|Inferred|Conflicting|Unknown"
contract_coverage: "complete|partial|blocked"
behavior_document: "../../behaviors/repository.behavior-name.md"
endpoint_matrix: "../endpoint-matrix.md"
openapi_document: null
---

# API operation title

[← Back to technical behavior](../../behaviors/repository.behavior-name.md) · [Endpoint matrix](../endpoint-matrix.md)

> This document describes the API contract observable at the recorded repository commit. It does not claim to be the original published specification. Items that cannot be proved are marked `Inferred`, `Conflicting`, or `Unknown`.

## Endpoint summary

| Property | Contract value | Status |
|---|---|---|
| Purpose | What the operation allows a consumer to do | Confirmed/Inferred/Unknown |
| Method and route | `POST /resource/{resourceId}` | Confirmed |
| Operation ID | `operationName` or Unknown | Confirmed/Unknown |
| Consumer | Known calling system/channel or Unknown | Confirmed/Inferred/Unknown |
| Authentication | Bearer token, mTLS, API key, IAM, None, or Unknown | Confirmed/Unknown |
| Authorization | Required role/scope/policy or Unknown | Confirmed/Unknown |
| Request content type | `application/json` or Unknown | Confirmed/Unknown |
| Response content type | `application/json` or Unknown | Confirmed/Unknown |
| Idempotency | Supported/not supported/conditional/Unknown | Confirmed/Inferred/Unknown |

## API input contract

### Headers

| Name | Type/format | Required | Example | Rules and meaning | Status |
|---|---|---:|---|---|---|
| `Authorization` | `string` | Yes/No/Unknown | `Bearer …` | Authentication scheme or Unknown | Confirmed/Unknown |
| `X-Correlation-Id` | `string` | Yes/No/Unknown | `550e8400-e29b-41d4-a716-446655440000` | Correlation rule or Unknown | Confirmed/Unknown |

Write `None observed` when no headers are read or enforced.

### Path parameters

| Name | Type/format | Required | Example | Validation and meaning | Status |
|---|---|---:|---|---|---|
| `resourceId` | `string` / identifier format | Yes | `123456` | Length, pattern, normalization, or Unknown | Confirmed/Inferred/Unknown |

Write `None` when the route has no path parameters.

### Query parameters

| Name | Type/format | Required | Default | Allowed values | Meaning and rules | Status |
|---|---|---:|---|---|---|---|
| `includeDetails` | `boolean` | No | `false` | `true`, `false` | Controls optional response information | Confirmed/Inferred/Unknown |

Write `None observed` when no query parameters are consumed.

### Request body schema

| Field path | Type/format | Required | Nullable | Allowed values or constraints | Default | Description | Status |
|---|---|---:|---:|---|---|---|---|
| `customer` | `object` | Yes | No | — | None | Customer information | Confirmed/Inferred/Unknown |
| `customer.id` | `string` | Yes | No | Length/pattern or Unknown | None | Customer identifier | Confirmed/Inferred/Unknown |
| `customer.type` | `string` / enum | Conditional | No | `PERSON`, `ORGANISATION` | None | Customer type | Confirmed/Inferred/Unknown |
| `items[]` | `array<object>` | No | No | Min/max items or Unknown | `[]` or None | Repeating business items | Confirmed/Inferred/Unknown |
| `items[].code` | `string` | Conditional | No | Enum/pattern or Unknown | None | Item code | Confirmed/Inferred/Unknown |

Use exact dotted paths. Use `[]` for array elements. Distinguish missing, `null`, blank, zero, and `false` whenever behavior differs.

### Request-level rules

| Rule ID | Rule | Applies to | Rejection result | Status |
|---|---|---|---|---|
| API-IN-001 | Describe conditional requiredness or a cross-field rule | `fieldA`, `fieldB` | HTTP status and error code | Confirmed/Inferred/Unknown |

### Request example

Include only fields supported by evidence. Annotate the example as partial when complete shape is unavailable.

```json
{
  "customer": {
    "id": "123456",
    "type": "PERSON"
  }
}
```

Example status: `Confirmed|Inferred|Partial|Unknown`

## API output contract

### Response outcomes

| Scenario | HTTP status | Response body | Relevant headers | Retryable by consumer | Status |
|---|---:|---|---|---:|---|
| Successful completion | `200` | Success schema below | Correlation header or None | No | Confirmed/Inferred/Unknown |
| Invalid request | `400` | Standard error schema or Unknown | None/Unknown | No | Confirmed/Inferred/Unknown |
| Not authenticated | `401` | Standard error schema or Unknown | None/Unknown | No | Confirmed/Inferred/Unknown |
| Not authorized | `403` | Standard error schema or Unknown | None/Unknown | No | Confirmed/Inferred/Unknown |
| Resource not found | `404` | Standard error schema or Unknown | None/Unknown | No | Confirmed/Inferred/Unknown |
| Conflict | `409` | Standard error schema or Unknown | None/Unknown | Conditional | Confirmed/Inferred/Unknown |
| Dependency or internal failure | `500/502/503` | Standard error schema or Unknown | Retry header or Unknown | Yes/Unknown | Confirmed/Inferred/Unknown |

Remove unobserved outcomes rather than presenting them as supported. Add an `Unknown` row when framework or gateway behavior is unavailable.

### Success response body schema

| Field path | Type/format | Presence | Nullable | Source/default | Allowed values or output rules | Description | Status |
|---|---|---|---:|---|---|---|---|
| `result` | `object` | Always | No | Computed/mapped | — | Operation result | Confirmed/Inferred/Unknown |
| `result.id` | `string` | Always/Conditional | No/Unknown | Source field | Format or masking rule | Result identifier | Confirmed/Inferred/Unknown |
| `result.status` | `string` / enum | Always | No | Constant/mapped | Known enum values or Unknown | Result status | Confirmed/Inferred/Unknown |

### Success response example

```json
{
  "result": {
    "id": "123456",
    "status": "ACCEPTED"
  }
}
```

Example status: `Confirmed|Inferred|Partial|Unknown`

### Error response schema

| Field path | Type/format | Presence | Nullable | Description | Status |
|---|---|---|---:|---|---|
| `code` | `string` | Always/Unknown | No/Unknown | Stable machine-readable error code | Confirmed/Inferred/Unknown |
| `message` | `string` | Always/Unknown | No/Unknown | Consumer-readable error description | Confirmed/Inferred/Unknown |
| `details[]` | `array<object>` | Conditional/Unknown | No/Unknown | Field or rule-specific errors | Confirmed/Inferred/Unknown |
| `correlationId` | `string` | Conditional/Unknown | No/Unknown | Trace identifier | Confirmed/Inferred/Unknown |

If error serialization is owned by an unavailable framework or shared library, write `Body shape: Unknown` instead of inventing a standard envelope.

### Error catalogue

| HTTP status | Error code | Triggering condition | Message rule | Consumer action | Status |
|---:|---|---|---|---|---|
| `400` | `CUSTOMER_ID_REQUIRED` or Unknown | Customer identifier is missing | Constant/dynamic/Unknown | Correct the request | Confirmed/Inferred/Unknown |
| `409` | Code or Unknown | Business conflict | Constant/dynamic/Unknown | Refresh or resolve the conflict | Confirmed/Inferred/Unknown |
| `503` | Code or Unknown | Required dependency is unavailable | Constant/dynamic/Unknown | Retry according to policy or Unknown | Confirmed/Inferred/Unknown |

### Error response example

```json
{
  "code": "CUSTOMER_ID_REQUIRED",
  "message": "Customer identifier is required"
}
```

Example status: `Confirmed|Inferred|Partial|Unknown`

## Contract semantics

Include only semantics relevant to this operation.

| Concern | Observed contract | Status |
|---|---|---|
| Idempotency | Idempotency key, natural key, not supported, or Unknown | Confirmed/Inferred/Unknown |
| Duplicate requests | Result of replaying the same request | Confirmed/Inferred/Unknown |
| Concurrency | Version/precondition rule or Unknown | Confirmed/Inferred/Unknown |
| Pagination | Cursor/page/limit behavior or N/A | Confirmed/Inferred/Unknown |
| Date and time | Accepted/emitted format and timezone | Confirmed/Inferred/Unknown |
| Empty collections | `[]`, omitted, `null`, or Unknown | Confirmed/Inferred/Unknown |
| Unknown fields | Rejected, ignored, retained, or Unknown | Confirmed/Inferred/Unknown |
| Timeout/async result | Consumer-visible completion behavior | Confirmed/Inferred/Unknown |

## Open questions and conflicts

| Question or conflict | Contract impact | Status | Evidence needed |
|---|---|---|---|
| Unresolved item | What a consumer cannot safely assume | Unknown/Conflicting | Source, schema, test, gateway configuration, shared library, or owner |

## Evidence appendix

The sections above are the consumer-facing contract. This appendix explains how confidently each part was reconstructed.

### Evidence coverage summary

| Contract area | L1 executable evidence | L2 schema evidence | L3 shared/opaque evidence | Final coverage |
|---|---|---|---|---|
| Headers | Present/None observed | Present/None observed | Present/None observed | Complete/Partial/Unknown |
| Path parameters | Present/None observed | Present/None observed | Present/None observed | Complete/Partial/Unknown |
| Query parameters | Present/None observed | Present/None observed | Present/None observed | Complete/Partial/Unknown |
| Request body | Present/None observed | Present/None observed | Present/None observed | Complete/Partial/Unknown |
| Success response | Present/None observed | Present/None observed | Present/None observed | Complete/Partial/Unknown |
| Error responses | Present/None observed | Present/None observed | Present/None observed | Complete/Partial/Unknown |

### L1 — Executable evidence

| Contract item | Observed behavior | Status | Evidence |
|---|---|---|---|
| `request.body.customer.id` | Directly read and rejected when missing | Confirmed | `path/to/file.ext:line` |
| `response.200.result.status` | Written as a constant or mapped value | Confirmed | `path/to/file.ext:line` |

### L2 — Schema-level evidence

| Model/schema | Contract item | Declaration | Runtime use observed | Status | Evidence |
|---|---|---|---:|---|---|
| Request/response model | `request.body.customer.type` | Type, requiredness, enum, or constraint | Yes/No | Schema-level | `path/to/schema.ext:line` |

### L3 — Shared or opaque evidence

| Shared component | Contract area | What is known | Limitation | Status | Evidence |
|---|---|---|---|---|---|
| Shared transformer/error handler | Error body | Known fields or None observed | Implementation unavailable or dynamic | Inferred/Unknown | `path/to/file.ext:line` |

### Evidence conflicts

| Contract item | Executable observation | Schema/published observation | Resolution | Status |
|---|---|---|---|---|
| Field, response, or rule | What runtime code does | What schema/configuration declares | Runtime wins/unresolved | Conflicting |

## Evidence index

- `path/to/file.ext:line` — proves method, route, or runtime wiring.
- `path/to/file.ext:line` — proves request validation or normalization.
- `path/to/file.ext:line` — proves success response status or body.
- `path/to/test.ext:line` — proves failure status, error body, or conditional field.
- `path/to/schema.ext:line` — provides schema-level fields and constraints.
