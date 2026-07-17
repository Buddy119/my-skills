# Field mapping policy

## When to create mappings

Create mappings only after locating a real outbound HTTP/HTTPS call in executable code. Examples include:

- An HTTP client invocation.
- A generated REST client operation.
- An SDK or repository wrapper whose implementation performs an external HTTP request.
- A framework adapter that invokes an external HTTP endpoint.

Record the confirmed remote operation, every executable usage, and its field mappings separately in the behavior dossier and repository register. Then publish a call-centric view in `tech-pack/field-validation-and-mapping.md`; keep only one behavior-relevant summary row per remote operation in each Tech Behavior.

Treat each endpoint-level API Contract as the authoritative published location for its caller-visible request and response fields. In `field-validation-and-mapping.md`, index those API contracts without copying their complete field tables. Keep detailed non-API field rules, shared technical transformations, and proven outbound HTTP mappings in the field document. When a shared rule affects several API contracts, state the caller-facing consequence briefly in each contract and keep the implementation detail in the field document.

Keep only applicable field-document sections. Include the API contract index only when API contracts exist, non-API rules only when observed, shared technical transformations only when they materially aid understanding, and HTTP call/mapping sections only after proving an executable outbound HTTP call.

Do not create mappings for:

- The repository's inbound API request or API response.
- EventBridge, SQS, SNS, Kinesis, DynamoDB Stream, or other messages/events.
- Database or persistence representations.
- DTO-to-domain, repository-model, or utility-object conversions.
- A configured URL with no executable HTTP call path.

Keep both `external_http_calls: []` and `field_mappings: []`, and omit the behavior mapping section and outbound-operation portion of the field document, when no outbound HTTP call is proven.

## Remote operation identity and executable usages

Treat a remote HTTP operation, its executable usages, and its field mappings as different records:

- **Remote operation (`HTTP-nnn`)** — the repository-observed external operation identity.
- **Executable usage (`HTTP-nnn-U<n>`)** — one executable call site and behavior context that invokes the operation.
- **Field mapping (`FM-nnn`)** — one reconciled request or response transformation associated with the operation and applicable usages.

Merge usages under one Call ID only when method, logical target, and client operation all match. Method and target equality alone is insufficient. Keep different client operations as different Call IDs even when they reach the same path.

When a target URL varies by environment, use the stable logical dependency and client-operation identity from code. Record environment-specific values and conditions on the usage or runtime-configuration record; do not split the operation solely because configuration values differ.

When several legacy Call IDs reconcile to one operation, retain the lexicographically first existing ID as the canonical Call ID, list the others as aliases in the register, and update affected usages, mappings, and Tech Behavior references. Do not merge when the evidence cannot establish the complete identity tuple.

Record one usage for every executable call site with:

- Usage ID, parent Call ID, and Behavior ID.
- Executable call location.
- Invocation condition and behavior-changing configuration.
- Status and call-site evidence.

The same Call ID may appear in several Tech Behaviors, but each behavior lists only its own Usage IDs.

## Mapping boundary

Name both sides of every mapping with stable identifiers. Prefer:

- `<external-client>.<operation> request|response`
- `HTTP <METHOD> <external-host-or-service> <path> request|response`
- Fully qualified EAPI model name as the EAPI side

Do not use vague labels such as `input`, `output`, `request DTO`, or `downstream` when the code exposes a more stable name.

## Mapping record

Record each mapping with:

- A repository-wide stable ID reused consistently in dossiers, Tech metadata, the repository register, and the field document, such as `FM-001`.
- The related remote-operation Call ID, such as `HTTP-001`.
- Applicable Usage IDs, or `all` only when the same mapping applies to every registered usage of the Call ID.
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

Do not repeat the operation method, target, client operation, or Behavior identity in every mapping record. Resolve those through Call ID and Usage ID.

When all usages share the same source, target, condition, and transformation, record one mapping with `all`. When any of those differ, create separate Mapping IDs and list the applicable Usage IDs. Similar field names are not evidence that mappings are identical.

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

## Behavior metadata

For a Tech Behavior that uses an outbound operation, use structured metadata equivalent to:

```yaml
external_http_calls:
  - call_id: "HTTP-001"
    usage_ids:
      - "HTTP-001-U01"
field_mappings:
  - mapping_id: "FM-001"
    call_id: "HTTP-001"
    applicable_usage_ids:
      - "HTTP-001-U01"
    direction: "eapi-to-external"
```

Include only usages and mappings applicable to that behavior. Shared Call IDs and Mapping IDs remain identical across documents.

## Published field-document model

Start with one operation index row per Call ID. Then create one anchored `## HTTP-nnn — Operation name` section per operation containing:

1. Call Overview, with identity, purpose, related behaviors, status, and call-level evidence once.
2. Executable Usages when multiple usages exist or usage-specific conditions matter.
3. Request Mappings.
4. Response Mappings.
5. Unmapped, lossy, opaque, or unresolved details when material.

Do not copy the register tables directly into the final document. Mapping tables live inside their parent Call section and omit method, target, client operation, and Behavior columns. A single simple usage may be summarized in Call Overview instead of receiving an otherwise redundant Usage table.

Keep detailed downstream response behavior, retry, timeout, recovery, and dependency failure semantics in External Dependency Contracts. The field document carries only the operation identity needed to understand its field transformations and links to the dependency document when applicable.

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
