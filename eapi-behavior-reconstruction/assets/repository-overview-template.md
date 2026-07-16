---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
analysis_mode: "automatic"
behavior_catalog: "behavior-catalog.yaml"
coverage_status: "complete|partial|blocked"
---

# Repository knowledge overview

## Observable responsibility

Summarize what the repository appears to do from executable evidence. Separate confirmed responsibilities from inferred business purpose.

## Technology and deployment

| Area | Observed value | Status | Evidence |
|---|---|---|---|
| Runtime/framework/IaC | Value | Confirmed | `path/to/file.ext:line` |

## Entry-point inventory

| Entry point | Trigger | Behavior ID | Classification | Status | Evidence |
|---|---|---|---|---|---|
| Handler or route | API/event/queue/schedule | repository.behavior | Business/integration/technical | Documented | `path/to/file.ext:line` |

## Behavior summary

| Behavior ID | Summary | Inputs | Outputs and side effects | Tech behavior | BA behavior | API contracts |
|---|---|---|---|---|---|---|
| repository.behavior | Observable behavior | Boundary | Boundary | [Tech](behaviors/repository.behavior.md) | [BA](../ba-pack/behaviors/repository.behavior.md) or N/A | Endpoint contract links or N/A |

## Knowledge pack index

| Knowledge area | Document | Availability | What it explains |
|---|---|---|---|
| Endpoints | [Endpoint matrix](endpoint-matrix.md) | Available/Not observed/Not applicable | Runtime routes and endpoint-level contracts |
| Data and state | [Data lifecycle](data-lifecycle.md) | Available/Not observed | Object movement and state transitions |
| Fields | [Field validation and mapping](field-validation-and-mapping.md) | Available/Not observed | Field rules and proven outbound HTTP mappings |
| Runtime configuration | [Runtime configuration matrix](runtime-config-matrix.md) | Available/Not observed | Configuration that changes behavior |
| External dependencies | [Dependency contracts](external-dependency-contracts.md) | Available/Not observed | Observed repository boundaries |
| Failures | [Failure taxonomy](failure-taxonomy.md) | Available/Not observed | Cross-behavior failure and recovery patterns |

Remove links for documents that are not generated; keep their availability so absence is explicit.

## External connections

List upstream triggers, downstream calls, emitted events, queues, topics, streams, tables, shared libraries, and unresolved external dependencies.

## Shared rules and components

Record validation, authorization, mapping, persistence, error-handling, and utility components reused by multiple behaviors.

## Coverage and limitations

Account for excluded, duplicate, generated, dynamic, unreadable, and blocked entry points. Do not claim complete coverage unless every discovered executable entry point has a catalog disposition.

## Repository-level open questions

List unknown responsibilities, conflicting wiring, missing schemas, environment-defined dependencies, and behavior that may live outside the repository.
