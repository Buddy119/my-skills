---
dependency_id: "DEP-external-resource-system"
title: "External dependency contract stub"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
dependency_type: "http-api|lambda|queue|topic|event-bus|stream|database|object-store|library|layer|other"
overall_status: "Confirmed|Inferred|Conflicting|Unknown"
dependency_matrix: "../dependency-matrix.md"
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind any dynamic H1 and each single-sentence factual block to passing CLM IDs. -->

# External dependency contract stub

[← Back to dependency matrix](../dependency-matrix.md)

## Boundary summary

| Property | Observed value | Status | Evidence |
|---|---|---|---|

## Consumers in this repository

| Endpoint/behavior ID | Purpose | Invocation condition | Status | Evidence |
|---|---|---|---|---|

## Visible contract

Describe the request, response, event, message, resource, or unavailable shared behavior visible from this repository. Link HTTP mappings to [the external mapping matrix](../../fields/external-http-mapping-matrix.md); use Field Lineage for non-HTTP boundaries.

## Operational semantics

| Concern | Observed behavior | Config/failure IDs | Status | Evidence |
|---|---|---|---|---|

## Errors and translation

| Remote/resource condition | Local handling/result | Failure ID | Retry owner | Status | Evidence |
|---|---|---|---|---|---|

## Unknown remote behavior

List internal behavior that this repository cannot establish and the external artifact or owner needed. Do not infer it.

## Evidence index

- `path/to/file.ext:line` — what the repository proves about this dependency.
