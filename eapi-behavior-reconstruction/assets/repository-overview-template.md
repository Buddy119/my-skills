---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
analysis_mode: "automatic|targeted"
behavior_catalog: "behavior-catalog.yaml"
knowledge_manifest: "../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind each factual block to passing CLM IDs. -->

# Technical repository overview

## Observable responsibility

Summarize what the repository appears to do from executable evidence. Separate confirmed responsibilities from inferred business purpose.

## Knowledge pack navigation

| Area | Document |
|---|---|

## Technology and deployment

| Area | Observed value | Status | Evidence |
|---|---|---|---|

## Entry-point inventory

| Entry point | Trigger | Behavior ID | Classification | Status | Evidence |
|---|---|---|---|---|---|

## Behavior summary

| Behavior ID | Summary | Inputs | Outputs and side effects | Tech behavior | BA behavior | Endpoint IDs |
|---|---|---|---|---|---|---|

## External connections

List upstream triggers, downstream calls, emitted events, queues, topics, streams, tables, shared libraries, and unresolved external dependencies.

## Shared rules and components

Record validation, authorization, mapping, persistence, error-handling, and utility components reused by multiple behaviors.

## Coverage and limitations

Account for excluded, duplicate, generated, dynamic, unreadable, and blocked entry points. Do not claim complete coverage unless every discovered executable entry point has a catalog disposition.

## Repository-level open questions

List unknown responsibilities, conflicting wiring, missing schemas, environment-defined dependencies, and behavior that may live outside the repository.
