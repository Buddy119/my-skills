---
behavior_id: "repository.behavior-name"
title: "Human-readable behavior title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
entry_type: "api|sqs|sns|eventbridge|schedule|stream|step-function|other"
entry_point: "handler-or-route"
behavior_category: "business|integration|technical"
overall_status: "Confirmed|Inferred|Conflicting|Unknown"
flow_perspective: "technical"
summary_perspective: "technical"
tech_flow_model: "../../.work/flow-models/repository.behavior-name.tech-flow.json"
ba_behavior_document: null
endpoint_ids: []
api_contract_documents: []
data_asset_ids: []
field_ids: []
dependency_ids: []
config_ids: []
validation_rule_ids: []
failure_ids: []
external_http_call_ids: []
external_mapping_ids: []
consumes: []
produces: []
reads: []
writes: []
analysis_limitations: []
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind the dynamic H1 and each single-sentence factual block to passing CLM IDs. -->

# Behavior title

## Summary

Render the implementation-focused `summary` from the Tech flow model in two or three sentences. Do not use the BA summary or claim that this is the original historical requirement.

## Trigger and entry point

- Trigger:
- Entry point:
- Runtime wiring:
- Status:
- Evidence:
  - `path/to/file.ext:line`

## API contracts

Include this section whenever `endpoint_ids` is nonempty; it is mandatory for `entry_type: api`. List every endpoint that invokes or routes into this behavior and link to its endpoint-owned contract:

- `EP-POST-resource` — [View API contract](../endpoints/contracts/EP-POST-resource.api-contract.md)

## BA view

Include this section only for `behavior_category: business|integration`:

[View business behavior](../../ba-pack/behaviors/repository.behavior-name.md)

## Behavior flow

```mermaid
flowchart TD
```

Render node labels and edges from the separate Tech flow model. Explain the implementation steps and branches with source evidence. Do not reuse the BA flow model.

## Inputs

Describe non-API input messages, events, records, schedules, or invocation context. API behaviors use the dedicated API contract sections.

## External HTTP field mappings

Include this section only when `external_mapping_ids` is nonempty. Summarize the interaction and link to the canonical [External HTTP mapping matrix](../fields/external-http-mapping-matrix.md). List `HTTP-` and `MAP-` IDs; do not duplicate the full mapping table.

## Related repository knowledge

- [Endpoint matrix](../endpoints/endpoint-matrix.md)
- [Data assets](../data/data-asset-catalog.md), [data lineage](../data/data-lineage.md), and [state transitions](../data/state-transition-matrix.md)
- [Field catalog](../fields/field-catalog.md), [validation rules](../fields/validation-rule-matrix.md), and [field lineage](../fields/field-lineage.md)
- [Runtime configuration](../runtime/runtime-config-matrix.md)
- [External dependencies](../dependencies/dependency-matrix.md)
- [Failure taxonomy](../reliability/failure-taxonomy.md)

## Preconditions and business rules

Add only rule IDs and behavior supported by passing claims.

## Happy path

Render only ordered steps supported by passing claims.

## Data access and state changes

| Operation | Resource | Key/record | State change | Status | Evidence |
|---|---|---|---|---|---|

## Outputs and side effects

| Output | Destination | Contract/resource | Condition | Status | Evidence |
|---|---|---|---|---|---|

## Failures, retries, and partial success

| Failure ID | Failure | Handling | Retry/DLQ/rollback | Status | Evidence |
|---|---|---|---|---|---|

## External dependency stubs

List relevant `DEP-` IDs, summarize their role, and link to their canonical stubs under `../dependencies/stubs/`. Do not reproduce the full dependency contract here.

## Open questions and conflicts

| Question or conflict | Why it matters | Status | Evidence needed |
|---|---|---|---|

## Evidence index

List only source ranges owned by this behavior's passing claims.
