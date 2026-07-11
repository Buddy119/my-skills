# API contract policy

## Scope

Apply this policy when `entry_type` is `api`. Reconstruct the contract actually enforced or emitted by the implementation at the recorded commit. Write it as a separate API contract document, not inline in the behavior document. Link both documents to each other using relative Markdown links. Do not rely on DTO names alone.

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
- Treat API Gateway or Lambda integration mappings as part of the contract when present.
- Cite assertion-level tests when they prove a validation failure, status code, error body, or conditional response field.
