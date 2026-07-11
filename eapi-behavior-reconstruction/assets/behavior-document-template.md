---
behavior_id: "repository.behavior-name"
title: "Human-readable behavior title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
entry_type: "api|sqs|sns|eventbridge|schedule|stream|step-function|other"
entry_point: "handler-or-route"
overall_status: "Confirmed|Inferred|Conflicting|Unknown"
consumes:
  - type: "http-api|event|queue|topic|stream|schedule|other"
    name: "stable connection name"
produces:
  - type: "http-response|event|queue|topic|other"
    name: "stable connection name"
reads:
  - type: "dynamodb|rds|s3|parameter|secret|other"
    name: "resource or logical name"
writes:
  - type: "dynamodb|rds|s3|other"
    name: "resource or logical name"
external_dependencies:
  - type: "service|lambda|api|library|layer|other"
    name: "dependency name"
field_mappings:
  - mapping_id: "FM-001"
    direction: "upstream-to-eapi|eapi-internal|eapi-to-downstream"
    source_boundary: "stable source boundary"
    source_fields:
      - path: "customer.address.postCode"
        type: "string"
    target_boundary: "stable target boundary"
    target_fields:
      - path: "customer.address.postalCode"
        type: "string"
    transformation: "direct copy|rename|format conversion|enum mapping|derived|other"
    condition: "always or exact condition"
    default_value: "none|value|Unknown"
    lossy: "false|true|Unknown"
    status: "Confirmed|Inferred|Conflicting|Unknown"
analysis_limitations:
  - "Describe an excluded or unavailable area"
---

# Behavior title

## Summary

Describe the observable behavior in two or three sentences. Do not claim that this is the original historical requirement.

## Trigger and entry point

- Trigger:
- Entry point:
- Runtime wiring:
- Status:
- Evidence:
  - `path/to/file.ext:line`

## Inputs and mapping

| Input | Source | Required | Mapping/default | Status | Evidence |
|---|---|---:|---|---|---|
| Example | Request field | Yes | Domain field | Confirmed | `path/to/file.ext:line` |

## Field mappings

| ID | Direction | Source boundary and field(s) | Target boundary and field(s) | Transformation | Condition/default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| FM-001 | upstream-to-eapi | Boundary: `field.path` | Boundary: `field.path` | Rename | Always; no default | No | Confirmed | `path/to/file.ext:line` |

### Unmapped, dropped, or unresolved fields

| Boundary and field | Observed treatment | Status | Evidence or evidence needed |
|---|---|---|---|
| Boundary: `field.path` | Dropped/ignored/unresolved | Unknown | `path/to/file.ext:line` or required artifact |

## Preconditions and business rules

### BR-001 — Rule title

- Behavior:
- Status: Confirmed
- Evidence:
  - `path/to/file.ext:line`
  - `path/to/test.ext:line`
- Notes:

## Happy path

1. Describe the ordered executable steps.
2. Cite important transitions inline or directly below the step.

## Data access and state changes

| Operation | Resource | Key/record | State change | Status | Evidence |
|---|---|---|---|---|---|
| Read/Write | Resource | Identifier | Description | Confirmed | `path/to/file.ext:line` |

## Outputs and side effects

| Output | Destination | Contract/resource | Condition | Status | Evidence |
|---|---|---|---|---|---|
| Event/response/call | Destination | Name | Condition | Confirmed | `path/to/file.ext:line` |

## Failures, retries, and partial success

| Failure | Handling | Retry/DLQ/rollback | Status | Evidence |
|---|---|---|---|---|
| Failure condition | Observed behavior | Mechanism or Unknown | Confirmed | `path/to/file.ext:line` |

## Security, privacy, and audit

Describe authorization, sensitive-data handling, logging, and audit behavior. Use `Unknown` when evidence is absent.

## External dependency stubs

For each dependency outside this repository, record the request/event/resource name, invocation evidence, observed contract, and unknown internal behavior.

## Test coverage

| Scenario | Test | Coverage assessment | Evidence |
|---|---|---|---|
| Scenario | Test name | Covered/Partial/Missing | `path/to/test.ext:line` |

## Open questions and conflicts

| Question or conflict | Why it matters | Status | Evidence needed |
|---|---|---|---|
| Item | Risk or impact | Unknown/Conflicting | Artifact or owner |

## Evidence index

- `path/to/file.ext:line` — what this location proves
