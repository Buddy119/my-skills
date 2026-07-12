---
endpoint_id: "EP-POST-resource"
primary_behavior_id: "repository.behavior-name"
title: "Human-readable API operation title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
entry_point: "handler-or-route"
operation_id: "operationName-or-unknown"
method: "GET|POST|PUT|PATCH|DELETE|other"
route: "/normalized/route"
contract_status: "Confirmed|Inferred|Conflicting|Unknown"
contract_coverage: "complete|partial|blocked"
behavior_document: "../../behaviors/repository.behavior-name.md"
endpoint_matrix: "../endpoint-matrix.md"
openapi_document: null
---

<!-- SCAFFOLD_ONLY: Replace every instruction and bind the dynamic H1 and each single-sentence factual block to passing CLM IDs. The template supplies no contract facts. -->

# API operation title

[← Back to technical behavior](../../behaviors/repository.behavior-name.md) · [Endpoint matrix](../endpoint-matrix.md)

> This document describes only the contract observable at the recorded repository commit; it is not an assumed industry-standard contract.

## Endpoint summary

| Property | Contract value | Status |
|---|---|---|

Add only properties backed by passing claims. Do not use common API defaults.

## API input contract

### Headers

| Name | Type/format | Required | Example | Rules and meaning | Status |
|---|---|---:|---|---|---|

Use a scoped absence claim when no header consumption is observed.

### Path parameters

| Name | Type/format | Required | Example | Validation and meaning | Status |
|---|---|---:|---|---|---|

### Query parameters

| Name | Type/format | Required | Default | Allowed values | Meaning and rules | Status |
|---|---|---:|---|---|---|---|

### Request body schema

| Field path | Type/format | Required | Nullable | Allowed values or constraints | Default | Description | Status |
|---|---|---:|---:|---|---|---|---|

Use exact evidence-backed paths. Distinguish missing, `null`, blank, zero, and `false` only when their behavior is established.

### Request-level rules

| Rule ID | Rule | Applies to | Rejection result | Status |
|---|---|---|---|---|

### Request example

Omit this subsection when no complete or explicitly partial example is supported. Never synthesize a representative payload.

## API output contract

### Response outcomes

| Scenario | HTTP status | Response body | Relevant headers | Retryable by consumer | Status |
|---|---:|---|---|---:|---|

Add only observed outcomes. Do not infer conventional 2xx, 4xx, or 5xx responses.

### Success response body schema

| Field path | Type/format | Presence | Nullable | Source/default | Allowed values or output rules | Description | Status |
|---|---|---|---:|---|---|---|---|

### Success response example

Omit this subsection when no evidence-backed example exists.

### Error response schema

| Field path | Type/format | Presence | Nullable | Description | Status |
|---|---|---|---:|---|---|

If serialization is opaque, create an audited `Unknown` claim rather than inventing an envelope.

### Error catalogue

| HTTP status | Error code | Triggering condition | Message rule | Consumer action | Status |
|---:|---|---|---|---|---|

### Error response example

Omit this subsection when no evidence-backed example exists.

## Contract semantics

| Concern | Observed contract | Status |
|---|---|---|

Include only semantics relevant to this operation and supported by passing claims.

## Open questions and conflicts

| Question or conflict | Contract impact | Status | Evidence needed |
|---|---|---|---|

## Evidence appendix

### Evidence coverage summary

| Contract area | L1 executable evidence | L2 schema evidence | L3 shared/opaque evidence | Final coverage |
|---|---|---|---|---|

### L1 — Executable evidence

| Contract item | Observed behavior | Status | Evidence |
|---|---|---|---|

### L2 — Schema-level evidence

| Model/schema | Contract item | Declaration | Runtime use observed | Status | Evidence |
|---|---|---|---:|---|---|

### L3 — Shared or opaque evidence

| Shared component | Contract area | What is known | Limitation | Status | Evidence |
|---|---|---|---|---|---|

### Evidence conflicts

| Contract item | Executable observation | Schema/published observation | Resolution | Status |
|---|---|---|---|---|

## Evidence index

List only source ranges owned by this contract's passing claims.
