---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
analysis_mode: "automatic|targeted"
behavior_catalog: "behavior-catalog.yaml"
knowledge_manifest: "../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Technical repository overview

## Observable responsibility

Summarize what the repository appears to do from executable evidence. Separate confirmed responsibilities from inferred business purpose.

## Knowledge pack navigation

| Area | Document |
|---|---|
| Endpoints and API contracts | [Endpoint matrix](endpoints/endpoint-matrix.md) |
| Data assets and lifecycle | [Data catalog](data/data-asset-catalog.md), [lineage](data/data-lineage.md), [state transitions](data/state-transition-matrix.md) |
| Fields, validation, and mappings | [Field catalog](fields/field-catalog.md), [validation rules](fields/validation-rule-matrix.md), [external mappings](fields/external-http-mapping-matrix.md) |
| Runtime configuration | [Runtime matrix](runtime/runtime-config-matrix.md) |
| External dependencies | [Dependency matrix](dependencies/dependency-matrix.md) |
| Failures | [Failure taxonomy](reliability/failure-taxonomy.md) |

## Technology and deployment

| Area | Observed value | Status | Evidence |
|---|---|---|---|
| Runtime/framework/IaC | Value | Confirmed | `path/to/file.ext:line` |

## Entry-point inventory

| Entry point | Trigger | Behavior ID | Classification | Status | Evidence |
|---|---|---|---|---|---|
| Handler or route | API/event/queue/schedule | repository.behavior | Business/integration/technical | Documented | `path/to/file.ext:line` |

## Behavior summary

| Behavior ID | Summary | Inputs | Outputs and side effects | Tech behavior | BA behavior | Endpoint IDs |
|---|---|---|---|---|---|---|
| repository.behavior | Observable behavior | Boundary | Boundary | [Tech](behaviors/repository.behavior.md) | [BA](../ba-pack/behaviors/repository.behavior.md) or N/A | EP- IDs or N/A |

## External connections

List upstream triggers, downstream calls, emitted events, queues, topics, streams, tables, shared libraries, and unresolved external dependencies.

## Shared rules and components

Record validation, authorization, mapping, persistence, error-handling, and utility components reused by multiple behaviors.

## Coverage and limitations

Account for excluded, duplicate, generated, dynamic, unreadable, and blocked entry points. Do not claim complete coverage unless every discovered executable entry point has a catalog disposition.

## Repository-level open questions

List unknown responsibilities, conflicting wiring, missing schemas, environment-defined dependencies, and behavior that may live outside the repository.
