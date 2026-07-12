---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
tech_pack: "../tech-pack/repository-overview.md"
coverage_status: "complete|partial|blocked"
---

# Business behavior overview

[View technical repository overview](../tech-pack/repository-overview.md)

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
