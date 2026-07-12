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

<!-- SCAFFOLD_ONLY: Replace every instruction with repository-specific prose. Use claim_ids as the material fact set; do not write one sentence per Claim or leave this comment. Keep the opening orientation and the flow, but rename, reorder, merge, or omit every other section when that produces a clearer explanation. State each material Unknown once instead of filling empty sections. -->

# Behavior title

## At a glance

Orient a developer in natural prose: explain when this behavior starts, its observable implementation responsibility, and the result it produces or attempts. Mention an evidence limitation here only when it materially changes that orientation. Choose the paragraph length that reads well. Do not copy Claim statements or the BA summary.

## API contracts

Include this section whenever `endpoint_ids` is nonempty; it is mandatory for `entry_type: api`. List every endpoint that invokes or routes into this behavior and link to its endpoint-owned contract:

- `EP-POST-resource` — [View API contract](../endpoints/contracts/EP-POST-resource.api-contract.md)

## Business view

Include this section only for `behavior_category: business|integration`:

[View business behavior](../../ba-pack/behaviors/repository.behavior-name.md)

## Execution story

```mermaid
flowchart TD
```

Render the exact nodes and topology from the separate Tech flow model. Follow the diagram with a coherent execution narrative that explains important branches and where execution stops, continues, or crosses a repository boundary. Do not restate every node as a separate bullet.

## Important decisions and rules

Explain the validations, conditions, defaults, and branch decisions that materially change the path. Link API-field detail to the endpoint contract and field pack rather than reproducing it.

## Data and external interactions

Explain inputs, significant transformations, reads, writes, local mutations, supported state changes, dependency calls, and emitted results as one data journey. Distinguish an attempted opaque call from a proven external outcome. When outbound HTTP mappings exist, name the relevant `HTTP-` and `MAP-` IDs, summarize their purpose, and link to the [External HTTP mapping matrix](../fields/external-http-mapping-matrix.md).

## Outputs, failures, and recovery

Describe outputs and important failure paths in context, including retry, DLQ, rollback, compensation, or partial success only when supported. Link canonical `FAIL-` and dependency records instead of copying their full tables.

## Runtime and operational considerations

Include only configuration or runtime wiring that changes this behavior. Omit this section when it adds no useful understanding.

## Unknowns and change risks

Explain the few unresolved facts that materially affect understanding or future change analysis. Do not fill this section with every missing detail.

## Detailed references

Link only the relevant canonical views. Delete every item that does not apply to this Behavior:

- [Endpoint matrix](../endpoints/endpoint-matrix.md)
- [Data assets](../data/data-asset-catalog.md), [data lineage](../data/data-lineage.md), and [state transitions](../data/state-transition-matrix.md)
- [Field catalog](../fields/field-catalog.md), [validation rules](../fields/validation-rule-matrix.md), and [field lineage](../fields/field-lineage.md)
- [Runtime configuration](../runtime/runtime-config-matrix.md)
- [External dependencies](../dependencies/dependency-matrix.md)
- [Failure taxonomy](../reliability/failure-taxonomy.md)

## Technical traceability

Keep concise source ranges for the material behavior facts here. Do not interrupt the main narrative with Evidence columns.
