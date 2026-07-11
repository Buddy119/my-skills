---
dependency_id: "DEP-external-resource-system"
title: "External dependency contract stub"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
dependency_type: "http-api|lambda|queue|topic|event-bus|stream|database|object-store|library|layer|other"
overall_status: "Confirmed|Inferred|Conflicting|Unknown"
dependency_matrix: "../dependency-matrix.md"
---

# External dependency contract stub

[← Back to dependency matrix](../dependency-matrix.md)

## Boundary summary

| Property | Observed value | Status | Evidence |
|---|---|---|---|
| Dependency ID/name | DEP- ID / name | Confirmed | `path/to/file.ext:line` |
| Direction and protocol | Outbound/inbound, HTTP/event/resource | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |
| Target identity | Endpoint/resource/logical name | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |
| Owner | Team/system or Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Consumers in this repository

| Endpoint/behavior ID | Purpose | Invocation condition | Status | Evidence |
|---|---|---|---|---|
| ID | Observable purpose | Condition | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Visible contract

Describe the request, response, event, message, resource, or unavailable shared behavior visible from this repository. Link HTTP mappings to [the external mapping matrix](../../fields/external-http-mapping-matrix.md); use Field Lineage for non-HTTP boundaries.

## Operational semantics

| Concern | Observed behavior | Config/failure IDs | Status | Evidence |
|---|---|---|---|---|
| Authentication | Mechanism without credentials | CFG- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |
| Timeout | Value/behavior or Unknown | CFG-/FAIL- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |
| Retry/backoff/DLQ | Mechanism or None/Unknown | CFG-/FAIL- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |
| Idempotency/concurrency | Mechanism or Unknown | IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Errors and translation

| Remote/resource condition | Local handling/result | Failure ID | Retry owner | Status | Evidence |
|---|---|---|---|---|---|
| Condition | Handling | FAIL- ID | Caller/application/AWS/Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Unknown remote behavior

List internal behavior that this repository cannot establish and the external artifact or owner needed. Do not infer it.

## Evidence index

- `path/to/file.ext:line` — what the repository proves about this dependency.
