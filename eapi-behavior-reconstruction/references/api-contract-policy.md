# API contract policy

## Purpose and audience

Apply this policy only when a confirmed Application Route has an executable request/response path. Reconstruct the caller-visible contract enforced or emitted by the implementation at the recorded commit. Write one contract per application endpoint and link it to its Tech Behavior and Endpoint Matrix row.

Write for a developer who needs to decide how to call the endpoint. Put purpose, invocation, request fields, validation, responses, examples, confidence, and material limitations ahead of implementation evidence. Keep internal execution, deployment analysis, and downstream integration detail in their dedicated Tech documents.

Do not generate a contract for an external-entry, infrastructure, environment, or protocol-support declaration without application implementation evidence. Keep complete evidence in the repository register; publish reader-relevant exposures and exceptions in Endpoint Matrix, and represent ordinary protocol support only in its compact summary.

## Endpoint identity and links

Write each contract to:

```text
tech-pack/contracts/<endpoint-id>.api-contract.md
```

Generate a stable endpoint ID from repository name, lower-case method, and normalized route. Preserve route parameter names, replace route punctuation and slashes with hyphens, and add a stable suffix only to resolve a collision.

Keep the contract's `method` and `route` as the application method and application route. When an external path is explicitly correlated, show it separately in Quick reference. Do not imply that an application route is externally invokable when reachability is not confirmed.

Keep these frontmatter fields and meanings:

- `contract_status`: confidence and completeness of the observed request, response, and error contract, using `Confirmed|Inferred|Conflicting|Unknown`.
- `application_route_status`: `Confirmed` for a full contract.
- `external_reachability_status`: `Confirmed|Conflicting|Unknown|Not observed`.
- `behavior_document`: backlink to the related Tech Behavior.
- `endpoint_matrix`: link to the endpoint's evidence and reconciliation detail.

The Tech Behavior must list every endpoint contract in `api_contracts` with the stable destination `../contracts/<endpoint-id>.api-contract.md`. The executor may classify a missing target as a cross-stage forward reference, but Reader text must use durable labels and must not describe the Contract as planned, pending, unmaterialized, or owned by a later stage. Do not create empty Contract stubs. API Contract publication must materialize every declared target, reconcile the source Behavior and Catalog wording, and then validate the Contract filename, Behavior backlink, Catalog path, and Endpoint Matrix links strictly. Use `api_contracts: []` for non-API behaviors.

## Reader-facing structure

Organize the body in this order:

1. A one- or two-sentence statement of what the endpoint lets a caller do and its visible result.
2. `Quick reference` with method, application route, explicitly correlated external path when present, authentication, content type, contract status, external reachability, and the Matrix link.
3. `Request`, divided only into the input locations actually observed and led by required, conditionally required, and behaviorally significant fields.
4. `Responses`, covering success and caller-visible errors.
5. `Examples` when a reliable request or response example can be reconstructed.
6. `Contract completeness and limitations` only when a material Unknown, Conflict, schema/runtime gap, opaque transformation, or missing example affects use.
7. `Complete field reference` only when a large observed Schema has remaining fields that would obscure the caller-first request or response sections.
8. `Related documents` linking directly to the Behavior's
   `#implementation-sequence`, the Matrix, and only the applicable field,
   dependency, configuration, or failure references.
9. `Source notes`, containing compact evidence definitions used by the body.

Always include Quick reference, Request, Responses, Related documents, and Source notes. When no caller-supplied input exists, say so briefly under Request. Remove empty input-location subsections, empty tables, template instructions, and optional sections that add no reader value.

`assets/api-contract-structure.json` is the mechanical table contract shared by the template and Validator. Quick reference uses exactly `Property | Value`. Responses uses exactly `HTTP status | When | Body/schema | Relevant headers`. When present, Header, Path/Query, Body, Validation, and Response-field tables use the registered headers for their caller-facing role. A no-input Request may use a short sentence instead of an empty table. Do not rename columns during an analysis; changing the structure contract is Skill development and must update the JSON contract, template, Validator, Artifact version, and tests together.

For a large Schema, keep the caller-first field tables and `Complete field reference` mutually exclusive by `Location + Field path`. The complete-reference table uses the registered `Location`, field, requirement/presence, rule, and Basis columns. It lists only remaining fields and identifies `Executable`, `Schema only`, `Shared or opaque`, or `Conflict` basis. Do not mechanically require a minimum field count or force this section into a small Contract.

Generic Markdown structure validation runs before this specialized contract. If Frontmatter, headings, fences, anchors, or a table is malformed, specialized API checks are skipped for that document so one structural defect does not create a cascade of missing-section, field, or backlink errors.

## Analysis evidence versus published contract

Use these layers while reconstructing fields, but do not publish them as fixed L1/L2/L3 sections:

- **L1 — Executable evidence:** fields directly read, validated, defaulted, transformed, or written by executable implementation.
- **L2 — Schema-level evidence:** fields declared by models, OpenAPI, JSON Schema, annotations, or generated types but not directly exercised by the traced implementation.
- **L3 — Shared or opaque evidence:** fields handled through shared controllers, transformers, generated mappers, reflection, or unavailable libraries.

Reconcile the layers into one caller-facing view:

- Treat directly observed executable behavior as the current implementation contract.
- Include schema-only fields when useful to the caller, but label them `Schema only`; do not imply runtime enforcement.
- Put code/schema disagreements beside the affected field or outcome and summarize material conflicts in Contract completeness and limitations.
- Describe only the known caller-visible effect of an opaque transformation. Move component and call-chain analysis to the Tech Behavior or field document.
- Use a Confidence or Basis column only when rows differ materially. Do not add a status column whose every value is `Confirmed`.

## Request contract

Create subsections only for observed Headers, Path parameters, Query parameters, and Body. Use concise tables with:

- Exact field path.
- Type and format.
- Requiredness, including conditional requiredness.
- Nullability when known.
- Default or fallback behavior.
- Caller-visible validation, normalization, and allowed values.

Distinguish missing, null, blank, zero, and false when the implementation treats them differently. Put field-local rules in the field row. Add a separate Validation rules subsection only for request-level constraints such as content type, payload size, mutual exclusion, cross-field conditions, or conditional groups; do not restate field rows.

Keep outbound propagation out of request field rows. Do not describe that an inbound field is forwarded, renamed, percent-encoded for a dependency, or copied into a downstream header/body unless that transformation itself changes how the caller must form the request. State only the caller-visible consequence and link to Field Validation and Mapping for the boundary transformation.

Authentication belongs in Quick reference and the relevant Header table when an actual header or token contract is known. Absence of application security code does not prove that an upstream boundary requires no authentication; use `Unknown` when the caller requirement cannot be established.

## Response contract

Lead with a response-outcomes table containing:

- HTTP status.
- Caller-visible triggering condition.
- Body shape or schema.
- Relevant headers.
- Material uncertainty.

Add response field tables only when they make the body easier to use. Record field path, type/format, presence, nullability, and caller-visible output rule in one place. Do not repeat those facts in an Output Rules table.

For a small flat response whose exact fields and literals are already clear in the outcomes table or a supported example, omit a separate response-fields table unless it adds material type, nullability, conditional-presence, or formatting information. Do not render the same small response in an outcome row, field-by-field restatement, and example without distinct caller value.

Keep caller-visible error statuses, codes, messages, and bodies in the contract. Put internal exception propagation, retry, compensation, partial success, and repository-wide failure classification in Tech Behavior or Failure Taxonomy.

When a dependency outcome selects a caller-visible response, describe the condition at the observed service boundary, such as “the preference dependency rejects the request.” Keep client-library properties, transport checks, downstream status/body loss, and response-field mappings in External Dependency Contracts or Field Validation and Mapping.

Do not invent framework-generated error fields. If the status or wire body cannot be established, say `Unknown` and identify the missing evidence without copying framework internals into the main contract.

## Examples

Generate examples when source code, schema/model declarations, or tests support the displayed structure and values:

- Prefer a compact HTTP-style request using the application route. If a different external invocation path is explicitly correlated, label it separately rather than replacing the application identity.
- When method and application route are known, make the primary request example complete enough to show the method, path, observed required headers, and body when applicable. A body-only JSON sample may accompany that request but must not be the only invocation example.
- Include only observed headers. Do not invent a host, authentication token, trace header, or media type.
- Use values observed in tests or schemas when available. Otherwise use clearly illustrative placeholder values that satisfy confirmed types and rules; quote placeholders inside JSON so the example remains valid JSON.
- Use only confirmed fields, statuses, error codes, enums, and constants. Do not add conventional envelope fields.
- Put the observed HTTP status in each response-example heading instead of repeating a synthetic HTTP response block when the JSON body is the useful example.
- Emit a wire-format response example only when serialization or response assertions support that wire shape. A logical Java or internal object is not automatically a JSON response contract.
- Omit an unsafe example and record the reason in Contract completeness and limitations. Do not fill the template for appearance.

Every fenced block labelled `json` must parse as JSON.

## Evidence presentation

Use compact body markers such as `[E1](#e1)` and define them under Source notes:

```markdown
<a id="e1"></a> **E1** — `src/path/File.ext:10-18` establishes the route, required field, and success response.
```

Attach a marker to a meaningful field row, response outcome, rule, example, or paragraph. One note may support several related facts. Do not require one marker per sentence or field, and do not repeat the same source explanation throughout the body.

Prefer executable code plus assertion-level tests for statuses, validation failures, and response bodies. Use schema evidence for names, types, requiredness, and enum values. Preserve Unknown and Conflicting conclusions where evidence does not settle the caller-visible contract.

## Document ownership

- API Contract owns endpoint-specific caller-visible request, response, validation, and error details.
- Tech Behavior owns internal orchestration, decisions, state changes, side effects, and call sequence.
- Endpoint Matrix owns the five endpoint evidence layers and detailed reachability reconciliation. The Contract shows only a concise status and link.
- Field Validation and Mapping owns non-API field rules, shared technical transformations, and proven outbound HTTP mappings. It may index API contracts but must not copy their full request/response tables.
- Failure Taxonomy owns internal and repository-wide failure classification. It may link to caller-visible outcomes without duplicating error payload tables.
- External Dependency Contracts owns downstream boundary detail. The API Contract links to it only when relevant.

Do not place Controller, Service, Repository, Java class, database, downstream
client, or internal exception-propagation sequences in a Contract. A separate
`Protocol sequence` is allowed only when the caller must follow a supported
multi-step protocol such as polling after `202`, callback acknowledgement, or
challenge/response. Protocol Sequence participants and messages are
caller-visible; internal runtime participants remain in Tech Behavior.
