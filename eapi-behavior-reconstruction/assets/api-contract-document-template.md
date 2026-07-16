---
behavior_id: "repository.behavior-name"
endpoint_id: "repository.method-route"
title: "Human-readable API contract title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
entry_point: "handler-or-route"
method: "GET|POST|PUT|PATCH|DELETE|other"
route: "/normalized/route"
contract_status: "Confirmed|Inferred|Conflicting|Unknown"
application_route_status: "Confirmed"
external_reachability_status: "Confirmed|Conflicting|Unknown|Not observed"
behavior_document: "../behaviors/repository.behavior-name.md"
endpoint_matrix: "../endpoint-matrix.md#repository-method-route"
---

# API contract title

[← Back to behavior](../behaviors/repository.behavior-name.md)

## Endpoint summary

| Property | Observed value | Status | Evidence |
|---|---|---|---|
| Endpoint ID | `repository.method-route` | Confirmed | `path/to/file.ext:line` |
| Method and route | `METHOD /normalized/path` | Confirmed | `path/to/file.ext:line` |
| Authentication | Scheme or Unknown | Confirmed/Unknown | `path/to/file.ext:line` |
| Content type | Value or Unknown | Confirmed/Unknown | `path/to/file.ext:line` |

`contract_status` above describes the request/response/error contract, not deployment or reachability.

## Exposure and reachability

[View this endpoint in the Endpoint Matrix](../endpoint-matrix.md#repository-method-route)

| Layer | Observed value | Status | Evidence |
|---|---|---|---|
| Application Route | `METHOD /normalized/path` → executable handler | Confirmed | `path/to/file.ext:line` |
| External Entry Declaration | External route/target or None observed | Confirmed/Conflicting/Unknown/Not observed | `path/to/config.ext:line` or analysis boundary |
| Environment Deployment Intent | Environment binding or None observed | Confirmed/Conflicting/Unknown/Not observed | `path/to/config.ext:line` or analysis boundary |
| Observed Runtime Deployment | Sanitized runtime observation or None supplied | Confirmed/Conflicting/Unknown/Not observed | `path/to/runtime-evidence.ext:line` or analysis boundary |
| External Reachability Assessment | Derived result under stated access conditions | Confirmed/Conflicting/Unknown/Not observed | Evidence rows above |

When external and application paths differ, state the explicit rewrite or integration mapping. Do not replace the application `method` or `route` in frontmatter.

## API input contract

### L1 — Executable input evidence

| Location | Field path | Type/format | Required | Nullable | Default | Validation and normalization rules | Status | Evidence |
|---|---|---|---:|---:|---|---|---|---|
| Header/path/query/body | `field.path` | Type | Yes/No/Conditional | Yes/No/Unknown | None/value | Length, range, pattern, enum, conversion, or cross-field rule | Confirmed | `path/to/file.ext:line` |

### L2 — Schema-level input evidence

| Model/schema | Field path | Type/format | Declared constraints | Runtime use observed | Status | Evidence |
|---|---|---|---|---:|---|---|
| Model or schema | `field.path` | Type | Required/nullable/enum/etc. | Yes/No | Schema-level | `path/to/schema.ext:line` |

### L3 — Shared or opaque input transformation

| Shared component | Known input/output | Confidence | Limitation | Evidence |
|---|---|---|---|---|
| Transformer/controller/mapper | Known fields or None observed | Inferred/Unknown | Unavailable or dynamic implementation | `path/to/file.ext:line` |

### Request-level rules

| Rule ID | Rule | Failure result | Status | Evidence |
|---|---|---|---|---|
| API-IN-001 | Content, conditional, or cross-field rule | Status/error | Confirmed | `path/to/file.ext:line` |

## API output contract

### Response outcomes

| Condition | HTTP status | Body/schema | Relevant headers | Status | Evidence |
|---|---:|---|---|---|---|
| Success or failure condition | 200/400/etc. | Schema or Unknown | Header or None | Confirmed | `path/to/file.ext:line` |

### L1 — Executable output evidence

| Field path | Type/format | Present when | Nullable | Source/default | Output rules | Status | Evidence |
|---|---|---|---:|---|---|---|---|
| `field.path` | Type | Always/condition | Yes/No/Unknown | Source, constant, or computed | Masking, formatting, enum, rounding, or inclusion rule | Confirmed | `path/to/file.ext:line` |

### L2 — Schema-level output evidence

| Model/schema | Field path | Type/format | Declared constraints | Runtime write observed | Status | Evidence |
|---|---|---|---|---:|---|---|
| Model or schema | `field.path` | Type | Nullable/enum/etc. | Yes/No | Schema-level | `path/to/schema.ext:line` |

### L3 — Shared or opaque output transformation

| Shared component | Known output | Confidence | Limitation | Evidence |
|---|---|---|---|---|
| Transformer/controller/mapper | Known fields or None observed | Inferred/Unknown | Unavailable or dynamic implementation | `path/to/file.ext:line` |

### Output and error rules

| Rule ID | Rule | Applies to | Status | Evidence |
|---|---|---|---|---|
| API-OUT-001 | Response or error rule | Status/field | Confirmed | `path/to/file.ext:line` |

## Open questions and conflicts

| Question or conflict | Why it matters | Status | Evidence needed |
|---|---|---|---|
| Item | Contract impact | Unknown/Conflicting | Artifact or owner |

## Evidence index

- `path/to/file.ext:line` — what this location proves
