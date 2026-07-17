---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Field validation and mapping

<!-- TEMPLATE: Keep only applicable sections. Remove sample rows and do not create empty tables merely to mirror this template. -->

## API contract index

Caller-visible API request and response fields are authoritative in the linked endpoint contracts. Use this table for repository-wide navigation rather than copying their field tables.

| Endpoint | Contract | Input locations | Response statuses | Contract confidence or limitation |
|---|---|---|---|---|
| `METHOD /route` | [API Contract](contracts/repository.method-route.api-contract.md) | Header/path/query/body as observed | Statuses as observed | Confirmed/Unknown/short limitation |

## Non-API field rules

Use this section for event, message, persistence-boundary, shared technical, or other non-API rules that help explain repository behavior. Do not label them cross-boundary HTTP mappings.

| Boundary | Field(s) | Behavior | Rule, default, or normalization | Failure/output effect | Evidence level | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Event/message/shared model | `field.path` | [Behavior](behaviors/repository.behavior.md) | Rule | Effect | L1/L2/L3 | Confirmed | `path/to/file.ext:line` |

## Shared technical transformations

Record reusable implementation transformations when their detail would clutter individual API contracts or behaviors. Keep each contract's caller-visible consequence in that contract.

| Transformation | Used by | Known input/output | Caller-visible effect | Status | Evidence |
|---|---|---|---|---|---|
| Shared mapper/transformer | Behavior or Contract links | Known fields | Effect or limitation | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Outbound HTTP operation index

Include this section only after proving an executable outbound HTTP/HTTPS call. Use one row per reconciled remote operation, not one row per field mapping.

| Call ID | Method and Logical Target | Client Operation | Observable Purpose | Related Behaviors | Status | Details |
|---|---|---|---|---|---|---|
| HTTP-001 | `POST external-service/path` | Client operation | Boundary purpose | [Behavior](behaviors/repository.behavior.md) | Confirmed | [View operation](#http-001) |

<a id="http-001"></a>

## HTTP-001 — Operation name

### Call overview

State the operation identity once. Keep full downstream failure, retry, timeout, and recovery semantics in External Dependency Contracts.

| Method | Logical Target | Client Operation | Observable Purpose | Related Behaviors | Usage Summary | Status | Evidence |
|---|---|---|---|---|---|---|---|
| POST | External service/path | Client operation | Boundary purpose | [Behavior](behaviors/repository.behavior.md) | One executable usage, or concise count | Confirmed | `path/to/file.ext:line` |

### Executable usages

Include this table when multiple usages exist or their conditions/configuration differ. A single simple usage may remain summarized in Call Overview.

| Usage ID | Behavior | Executable Call Site | Invocation Condition or Config | Status | Evidence |
|---|---|---|---|---|---|
| HTTP-001-U01 | [Behavior](behaviors/repository.behavior.md) | Exact client invocation | Condition/configuration | Confirmed | `path/to/file.ext:line` |

### Request mappings

Omit this section when no request-side mapping is observed. Method, Target, Client Operation, and Behavior belong in Call Overview or Executable Usages and must not be repeated here.

| Mapping ID | Applies to Usage(s) | Source Field(s) | Target Field(s) | Transformation | Condition/Default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| FM-001 | all | `source.path` | `target.path` | Rename/conversion | Condition/default | No | Confirmed | `path/to/file.ext:line` |

### Response mappings

Use the same mapping-table shape for `external-to-eapi` mappings. Omit the section when no response field is consumed.

| Mapping ID | Applies to Usage(s) | Source Field(s) | Target Field(s) | Transformation | Condition/Default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| FM-002 | HTTP-001-U01 | `external.path` | `eapi.path` | Rename/conversion | Condition/default | No | Confirmed | `path/to/file.ext:line` |

### Unmapped, lossy, opaque, or unresolved

Explain intentionally dropped values, information loss, unavailable shared transformers, and mappings that cannot be proven. Omit this subsection and any other optional subsection that has no applicable content.
