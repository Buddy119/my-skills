# API contract policy

## Scope

Apply this policy only when a confirmed Application Route has an executable request/response path. Reconstruct the contract actually enforced or emitted by the implementation at the recorded commit. Write one separate API contract per application endpoint, not one contract per grouped behavior and not inline in the behavior document. Link every contract to its behavior and Endpoint Matrix row. Do not rely on DTO names alone.

Do not generate a contract for an external-entry, infrastructure, or environment declaration without application implementation evidence. Keep those records in Endpoint Matrix under the endpoint-exposure policy.

## Endpoint identity and links

Write each contract to:

```text
tech-pack/contracts/<endpoint-id>.api-contract.md
```

Generate a stable endpoint ID from repository name, lower-case method, and normalized route. Preserve route parameter names, replace route punctuation and slashes with hyphens, and add a stable suffix only to resolve a collision.

Include both `behavior_id` and `endpoint_id` in contract frontmatter. The behavior document must list every endpoint contract in `api_contracts` and link to it using `../contracts/<endpoint-id>.api-contract.md`. Use `api_contracts: []` for non-API behaviors. Each contract must link back using `../behaviors/<behavior-id>.md`.

Add one `endpoint-matrix.md` row per reconciled application endpoint. Keep unmatched external exposures as their own Matrix rows without contracts or behavior links.

Keep the contract's `method` and `route` as the application method and application route. When one or more external paths map to it, record them in `Exposure and reachability` and Endpoint Matrix without replacing the application identity.

## Contract versus exposure confidence

`contract_status` describes the completeness and consistency of executable request, response, and error behavior. It does not describe deployment or external availability.

Record these separately:

- `application_route_status`, which must be `Confirmed` for a full contract.
- `external_reachability_status`, using `Confirmed|Conflicting|Unknown|Not observed`.
- `endpoint_matrix`, linking to the corresponding endpoint evidence and reconciliation section.

In `Exposure and reachability`, summarize all five endpoint layers with their own status and evidence. The API field-contract L1/L2/L3 sections remain independent.

## Evidence layers

Keep these layers separate in both input and output contracts:

- **L1 — Executable evidence:** Fields directly read, validated, defaulted, transformed, or written by executable implementation. This is the strongest contract evidence.
- **L2 — Schema-level evidence:** Fields declared by request/response models, OpenAPI, JSON Schema, annotations, or generated types but not directly exercised by the traced implementation. Label them `schema-level`; do not imply runtime enforcement without L1 evidence.
- **L3 — Shared or opaque transformer evidence:** Fields produced or consumed through shared controllers, common transformers, generated mappers, reflection, or unavailable libraries. Mark exact fields `Inferred` or `Unknown` unless the transformer implementation is inspected.

Do not merge fields from weaker layers into L1. If a layer has no evidence, write `None observed` rather than omitting the layer.

## Input contract

Enumerate every observed input location:

- Authentication and relevant headers.
- Path parameters.
- Query parameters.
- Request body fields, including nested objects and arrays.

For each field record:

- Exact dotted path and location.
- Type and format.
- Requiredness and nullability.
- Default or fallback behavior.
- Normalization or conversion.
- Validation rules, including ranges, lengths, patterns, enum values, and cross-field conditions.
- Evidence status and source/test/schema citations.

Distinguish missing, null, blank, zero, and false when the code treats them differently. Record request-level rules such as content type, payload size, mutual exclusion, and conditional requiredness.

## Output contract

Record every observed response outcome:

- HTTP status code.
- Triggering condition.
- Response schema or body shape.
- Headers when behaviorally relevant.
- Error code and message rules.

For each success response field record:

- Exact dotted path.
- Type, format, presence, and nullability.
- Source, computed rule, default, or constant.
- Conditional inclusion, masking, rounding, date/time, and enum rules.
- Evidence status and citations.

Do not invent fields for opaque framework-generated errors. Mark the body `Unknown` and identify the missing framework or integration evidence.

## Evidence and completeness

- Prefer handler/controller, validation, serializer, schema, and test evidence together.
- Record conflicts between published schemas and executable code.
- Mark contract coverage partial when dynamic schemas, generated models, shared libraries, or infrastructure response mappings are unavailable.
- Treat boundary and integration mappings as endpoint-exposure evidence. Include request/response transformation in the application contract only when executable or declarative mapping evidence defines contract behavior, while keeping deployment and reachability conclusions separate.
- Cite assertion-level tests when they prove a validation failure, status code, error body, or conditional response field.
