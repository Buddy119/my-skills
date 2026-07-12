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

<!-- SCAFFOLD_ONLY: Replace every instruction with business-readable prose. Use claim_ids as the material fact set; do not translate Tech prose sentence by sentence or leave this comment. Keep the scenario orientation and the flow, but rename, reorder, merge, or omit every other section when that produces a clearer explanation. State each material Unknown once instead of filling empty sections. -->

# Business-readable behavior title

[View technical behavior](../../tech-pack/behaviors/repository.behavior-name.md)

## Scenario at a glance

Explain the supported business or operational event, the meaningful action or decision, and the visible outcome in natural language. Write this independently from the Tech summary. If the repository does not establish the capability, actor, purpose, or outcome, state that limitation once and keep the document concise.

## Participants and starting point

Describe known participants, their supported roles, the starting event, and relevant preconditions. Omit unsupported actors instead of inferring them from component names.

## Business journey

```mermaid
flowchart TD
```

Render the exact nodes and topology from the independent BA flow model. Explain the journey using business events, decisions, actions, information, outcomes, and visible exceptions. Do not copy or rename the internal Tech call sequence.

## Decisions and business rules

Explain only rules with supported business meaning. Keep transport checks and framework validation in the Tech Pack.

## Information and outcomes

Describe business information conceptually, where it comes from when known, how it is used, and what visible result follows. Do not reproduce API schemas or field mappings.

## Exceptions and external participants

Explain business-visible exceptions, incomplete or delayed results, recovery when known, and material external participants. Omit low-level HTTP, queue, database, and exception-class names. When asynchronous delivery, timing, duplication, or recovery changes what a participant can observe, preserve that business meaning without exposing unnecessary infrastructure mechanics.

## Open business questions

List only unanswered questions that would materially change requirements, impact analysis, ownership, or the interpretation of the outcome.

## Related knowledge

- [Capability map](../capability-map.md)
- [Business data lifecycle](../business-data-lifecycle.md)
- [Business rule catalog](../business-rule-catalog.md)
- [Business exception catalog](../business-exception-catalog.md)
- [Technical behavior](../../tech-pack/behaviors/repository.behavior-name.md)

Technical implementation and source evidence remain in the linked Tech Pack.
