# Field mapping policy

## When to create mappings

Create mappings only after locating a real outbound HTTP/HTTPS call in executable code. Examples include:

- An HTTP client invocation.
- A generated REST client operation.
- An SDK or repository wrapper whose implementation performs an external HTTP request.
- A framework adapter that invokes an external HTTP endpoint.

Record the confirmed call in `external_http_calls`. Then map EAPI fields to the external request and, when consumed, external response fields back to EAPI.

Do not create mappings for:

- The repository's inbound API request or API response.
- EventBridge, SQS, SNS, Kinesis, DynamoDB Stream, or other messages/events.
- Database or persistence representations.
- DTO-to-domain, repository-model, or utility-object conversions.
- A configured URL with no executable HTTP call path.

Keep both `external_http_calls: []` and `field_mappings: []`, and omit the mapping section, when no outbound HTTP call is proven.

## Mapping boundary

Name both sides of every mapping with stable identifiers. Prefer:

- `<external-client>.<operation> request|response`
- `HTTP <METHOD> <external-host-or-service> <path> request|response`
- Fully qualified EAPI model name as the EAPI side

Do not use vague labels such as `input`, `output`, `request DTO`, or `downstream` when the code exposes a more stable name.

## Mapping record

Record each mapping with:

- A stable ID local to the behavior document, such as `FM-001`.
- The related `external_http_calls.call_id`, such as `HTTP-001`.
- Direction: `eapi-to-external` or `external-to-eapi`.
- Source boundary and one or more exact source field paths.
- Target boundary and one or more exact target field paths.
- Source and target types or formats when visible.
- Transformation expression in concise implementation-neutral language.
- Condition under which the mapping applies.
- Default or constant value, without exposing secrets.
- Whether information is lost, truncated, masked, aggregated, or dropped.
- Evidence status and citations.

Use dotted paths and array markers consistently, for example `customer.addresses[].postalCode`.

## Transformation categories

Describe the observed category and details:

- Direct copy or rename.
- Nesting, flattening, or path relocation.
- Type or format conversion.
- Enum or code translation; list the observed value pairs.
- Default, fallback, or constant injection.
- Conditional mapping.
- Concatenation, split, aggregation, or derived value.
- Normalization, trimming, case conversion, rounding, or date/time conversion.
- Masking, hashing, encryption, redaction, or truncation.
- Dropped or ignored field.

For many-to-one and one-to-many cases, keep the transformation as one mapping record with multiple source or target fields rather than creating misleading independent copies.

## Evidence rules

- Cite the source field definition or read and the target field assignment or serialization.
- Cite schema definitions when they establish names, types, requiredness, or enum values.
- Cite tests when they prove an actual value conversion.
- Use `Confirmed` only when the code or test establishes both sides and the transformation.
- Use `Inferred` when one boundary is visible but the remote contract is not.
- Use `Conflicting` when code, schema, tests, or examples disagree.
- Use `Unknown` for dynamic reflection, opaque shared libraries, unavailable generated models, or environment-controlled mappings.

## Completeness checks

Inspect and record:

- Input fields that are validated but never mapped.
- Input fields silently ignored or explicitly dropped.
- Output fields created without an upstream source.
- Defaults that distinguish missing, null, blank, zero, and false.
- Optional-to-required changes across boundaries.
- Precision, currency, date, time-zone, locale, and encoding changes.
- Enum values without a known downstream equivalent.
- PII or financial fields that are masked, logged, or propagated.

Do not claim full field coverage unless the relevant schemas or models were fully enumerated. Record the limitation when only fields touched by the chosen behavior were traced.
