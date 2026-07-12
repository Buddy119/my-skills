---
behavior_id: "repository.behavior-name"
title: "Business-readable behavior title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
business_capability: "Business capability or Unknown"
behavior_type: "business|integration"
overall_status: "Confirmed|Inferred|Conflicting|Unknown"
flow_perspective: "business"
summary_perspective: "business"
ba_flow_model: "../../.work/flow-models/repository.behavior-name.ba-flow.json"
actors: []
business_data_object_ids: []
business_rule_ids: []
business_exception_ids: []
tech_behavior_document: "../../tech-pack/behaviors/repository.behavior-name.md"
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind the dynamic H1 and each single-sentence factual block to passing CLM IDs. -->

# Business-readable behavior title

[View technical behavior](../../tech-pack/behaviors/repository.behavior-name.md)

## Related BA knowledge

- [Capability map](../capability-map.md)
- [Business data lifecycle](../business-data-lifecycle.md)
- [Business rule catalog](../business-rule-catalog.md)
- [Business exception catalog](../business-exception-catalog.md)

## Business summary

Render the independent BA model's business-focused `summary`. Explain the business event, decision/action, and visible outcome in two or three sentences. Do not reuse or mechanically paraphrase the Tech summary.

## Business trigger and actors

| Actor or participant | Trigger or role | Status |
|---|---|---|

## Business flow

```mermaid
flowchart TD
```

Render node labels and edges from the separate BA flow model. Describe business actors/events, decisions, actions, outcomes, and visible exceptions. Mark inferred nodes with `(Inferred)`. Do not copy or mechanically rename Tech nodes.

## Business preconditions

| Preconditions | Business meaning | Status |
|---|---|---|

## Business rules

Add only rules backed by passing `business-rule` claims. Leave the section empty when no business meaning is established.

## Business inputs and outputs

Describe concepts, not API fields or schemas.

| Direction | Business information | Business meaning or rule | Status |
|---|---|---|---|

## Business outcomes

| Outcome | Who or what is affected | When it occurs | Status |
|---|---|---|---|

## Business exceptions

| Exception condition | Business impact | Visible result or recovery | Status |
|---|---|---|---|

## External business interactions

| External participant | Business purpose | Information exchanged | Business dependency | Status |
|---|---|---|---|---|

## Open questions

| Question | Business importance | Status |
|---|---|---|

## Traceability

- [Technical behavior](../../tech-pack/behaviors/repository.behavior-name.md)
- Repository commit: `git-commit-or-unknown`
- Technical implementation and source evidence remain in the linked Tech Pack.
