---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
tech_pack: "../tech-pack/repository-overview.md"
knowledge_manifest: "../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Business repository overview

[View technical repository overview](../tech-pack/repository-overview.md)

## BA knowledge navigation

| Business question | Document |
|---|---|
| What capabilities and actors exist? | [Capability map](capability-map.md) |
| Where does business information come from and go? | [Business data lifecycle](business-data-lifecycle.md) |
| What business rules apply? | [Business rule catalog](business-rule-catalog.md) |
| What can go wrong from a business perspective? | [Business exception catalog](business-exception-catalog.md) |
| What flows can users or systems initiate? | [Behavior catalog](behavior-catalog.md) |

## Business capabilities

Summarize supported business capabilities. Separate confirmed capabilities from inferred or unknown business purpose.

## Business actors and participants

| Actor or participant | Observed role | Status |
|---|---|---|
| Person, channel, team, or system participant | Business-facing role | Confirmed/Inferred/Unknown |

## Business behavior landscape

| Capability | Behavior | Trigger | Outcome | Status | BA behavior | Tech behavior |
|---|---|---|---|---|---|---|
| Capability or Unknown | Business-readable title | Business request/event | Visible outcome | Confirmed/Inferred/Unknown | [BA](behaviors/repository.behavior-name.md) | [Tech](../tech-pack/behaviors/repository.behavior-name.md) |

## External business participants

Describe external parties or systems by their business role and the purpose of the interaction. Keep protocols and field mappings in the Tech Pack.

## Cross-behavior business rules

Record only rules that are supported across multiple behaviors. Do not promote technical validation into policy.

## Business exceptions and dependencies

Summarize recurring business-visible exceptions, incomplete outcomes, recovery constraints, and external dependencies.

## Coverage and open questions

Explain which business and integration behaviors are represented, which technical behaviors were intentionally omitted, and which business meanings remain unknown or conflicting.
