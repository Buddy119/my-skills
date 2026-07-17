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

<!-- TEMPLATE: Replace this comment with a one- or two-sentence caller-visible purpose and result, supported by a compact evidence marker. -->

## Quick reference

| Property | Value |
|---|---|
| Method and application route | `METHOD /normalized/path` [E1](#e1) |
| External invocation path | TEMPLATE: Include only when explicitly correlated; otherwise remove this row [E2](#e2) |
| Authentication | Scheme and requirement, or `Unknown` [E3](#e3) |
| Content type | Observed media type, or `Unknown` [E3](#e3) |
| Contract confidence | TEMPLATE: `Confirmed|Inferred|Conflicting|Unknown` — one short coverage explanation |
| External reachability | [`Confirmed|Conflicting|Unknown|Not observed`](../endpoint-matrix.md#repository-method-route) — concise limitation if needed |

## Request

<!-- TEMPLATE: Keep only observed input-location subsections. When there is no caller-supplied input, replace all tables with one short sentence. -->
<!-- TEMPLATE: Keep rules caller-visible. Move outbound forwarding, renaming, encoding, and downstream header/body mapping to Field Validation and Mapping. -->

### Headers

| Header | Type/format | Required | Nullable | Default | Rules |
|---|---|---:|---:|---|---|
| `Header-Name` | Type/format | Yes/No/Conditional | Yes/No/Unknown | None/value | Caller-visible rule [E3](#e3) |

### Path parameters

| Field | Type/format | Required | Nullable | Default | Rules |
|---|---|---:|---:|---|---|
| `parameter` | Type/format | Yes/No/Conditional | Yes/No/Unknown | None/value | Caller-visible rule [E4](#e4) |

### Query parameters

| Field | Type/format | Required | Nullable | Default | Rules |
|---|---|---:|---:|---|---|
| `parameter` | Type/format | Yes/No/Conditional | Yes/No/Unknown | None/value | Caller-visible rule [E4](#e4) |

### Body

| Field path | Type/format | Required | Nullable | Default | Rules |
|---|---|---:|---:|---|---|
| `field.path` | Type/format | Yes/No/Conditional | Yes/No/Unknown | None/value | Validation, normalization, allowed values, and schema-only/conflict note when applicable [E4](#e4) |

### Validation rules

<!-- TEMPLATE: Keep only for request-level, cross-field, conditional-group, mutual-exclusion, content-type, or payload rules that are not already stated in field rows. -->

| Condition | Caller-visible result |
|---|---|
| Request-level or cross-field condition [E5](#e5) | Status/error or rejection behavior [E5](#e5) |

## Responses

| HTTP status | When | Body/schema | Relevant headers |
|---:|---|---|---|
| 2xx/4xx/5xx | Caller-visible condition | Observed body/schema or `Unknown` [E6](#e6) | Observed header or None |

<!-- TEMPLATE: Add response field tables only when they make the body easier to use. Do not add a separate Output Rules table. -->

### Response fields

| Field path | Type/format | Present when | Nullable | Rules |
|---|---|---|---:|---|
| `field.path` | Type/format | Outcome/condition | Yes/No/Unknown | Caller-visible inclusion, format, enum, or default rule [E6](#e6) |

## Examples

<!-- TEMPLATE: Remove this section when code, schema, or tests do not support a reliable example. Do not invent a host, token, header, status, field, or wire shape. -->

### Request example

```http
METHOD /normalized/path HTTP/1.1
Content-Type: application/json
```

```json
{
  "field": "supported-or-clearly-illustrative-value"
}
```

### TEMPLATE: 2xx success response example

```json
{
  "field": "supported-value"
}
```

### TEMPLATE: 4xx/5xx error response example

```json
{
  "code": "SUPPORTED_ERROR_CODE"
}
```

<!-- TEMPLATE: Replace with a short explanation of which Source note supports the examples. -->

## Contract completeness and limitations

<!-- TEMPLATE: Remove this section when no material Unknown, Conflict, schema/runtime gap, opaque transformation, authentication gap, or omitted example affects callers. -->

- TEMPLATE: Explain the caller impact of a material limitation and what evidence would resolve it. [E8](#e8)

## Related documents

- [Tech Behavior](../behaviors/repository.behavior-name.md)
- [Endpoint Matrix](../endpoint-matrix.md#repository-method-route)
<!-- TEMPLATE: Add links to Field Validation and Mapping, External Dependency Contracts, Runtime Config Matrix, or Failure Taxonomy only when relevant. -->

## Source notes

<a id="e1"></a> **E1** — `path/to/file.ext:line` establishes the endpoint purpose, method, and application route.

<a id="e2"></a> **E2** — `path/to/config.ext:line` establishes the explicit external-path correlation; remove this note when no external path is shown.

<a id="e3"></a> **E3** — `path/to/file.ext:line` establishes authentication, headers, or content handling, or documents why they remain Unknown.

<a id="e4"></a> **E4** — `path/to/file.ext:line` establishes the displayed request fields and field-local rules.

<a id="e5"></a> **E5** — `path/to/file.ext:line` establishes a request-level or cross-field rule; remove when not applicable.

<a id="e6"></a> **E6** — `path/to/file.ext:line` establishes the displayed response outcome and fields.

<a id="e7"></a> **E7** — `path/to/test-or-schema.ext:line` supports the displayed example; remove when no example is published.

<a id="e8"></a> **E8** — `path/to/file.ext:line` establishes a material limitation or conflict; use the analysis boundary when the missing artifact itself is the limitation.
