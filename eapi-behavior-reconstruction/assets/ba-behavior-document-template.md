---
behavior_id: "repository.behavior-name"
title: "Business-readable behavior title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
business_capability: "Business capability or Unknown"
behavior_type: "business|integration"
overall_status: "Confirmed|Inferred|Conflicting|Unknown"
actors:
  - "Business actor or system participant"
business_data_object_ids: []
business_rule_ids: []
business_exception_ids: []
tech_behavior_document: "../../tech-pack/behaviors/repository.behavior-name.md"
---

# Business-readable behavior title

[View technical behavior](../../tech-pack/behaviors/repository.behavior-name.md)

## Related BA knowledge

- [Capability map](../capability-map.md)
- [Business data lifecycle](../business-data-lifecycle.md)
- [Business rule catalog](../business-rule-catalog.md)
- [Business exception catalog](../business-exception-catalog.md)

## Business summary

Explain the business event, action, and visible outcome in two or three sentences. Do not describe the code structure or invent the original requirement.

## Business trigger and actors

| Actor or participant | Trigger or role | Status |
|---|---|---|
| Business actor | Starts, receives, or supports the behavior | Confirmed/Inferred/Unknown |

## Business flow

```mermaid
flowchart TD
    A[Business request or event] --> B[Check required business information]
    B --> C{Business conditions satisfied?}
    C -- No --> D[Inform the initiating participant of the exception]
    C -- Yes --> E[Perform the business action]
    E --> F[Business outcome]
```

Describe the important business decisions and outcomes. Mark inferred nodes with `(Inferred)`.

## Business preconditions

| Preconditions | Business meaning | Status |
|---|---|---|
| Condition | Why the behavior can or cannot proceed | Confirmed/Inferred/Unknown |

## Business rules

### BR-001 — Business-readable rule title

- Rule:
- Business effect:
- Status: Confirmed/Inferred/Conflicting/Unknown

## Business inputs and outputs

Describe concepts, not API fields or schemas.

| Direction | Business information | Business meaning or rule | Status |
|---|---|---|---|
| Input/Output | Information concept | Meaning, condition, or limitation | Confirmed/Inferred/Unknown |

## Business outcomes

| Outcome | Who or what is affected | When it occurs | Status |
|---|---|---|---|
| Successful or alternative outcome | Actor or business object | Condition | Confirmed/Inferred/Unknown |

## Business exceptions

| Exception condition | Business impact | Visible result or recovery | Status |
|---|---|---|---|
| Condition | What does not complete or changes | What the participant observes; Unknown if unavailable | Confirmed/Inferred/Unknown |

## External business interactions

| External participant | Business purpose | Information exchanged | Business dependency | Status |
|---|---|---|---|---|
| External system or party | Purpose or Unknown | Conceptual information | Effect if unavailable or Unknown | Confirmed/Inferred/Unknown |

## Open questions

| Question | Business importance | Status |
|---|---|---|
| Unresolved item | Decision or impact it affects | Unknown/Conflicting |

## Traceability

- [Technical behavior](../../tech-pack/behaviors/repository.behavior-name.md)
- Repository commit: `git-commit-or-unknown`
- Technical implementation and source evidence remain in the linked Tech Pack.
