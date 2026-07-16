---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Field validation and mapping

## How to read this document

Separate executable field rules from schema declarations and from unknown shared transformations. Cross-boundary mappings in this document require a proven executable outbound HTTP call.

## Input and output field rules

| Boundary | Field(s) | Behavior/endpoint | Rule, default, or normalization | Failure/output effect | Evidence level | Status | Evidence |
|---|---|---|---|---|---|---|---|
| API/event/model | `field.path` | Behavior or Endpoint link | Rule | Effect | L1/L2/L3 | Confirmed | `path/to/file.ext:line` |

## Proven external HTTP calls

| Call ID | Behavior | Method and target | Client operation | Status | Evidence |
|---|---|---|---|---|---|
| HTTP-001 | [Behavior](behaviors/repository.behavior.md) | `POST external/path` | Client operation | Confirmed | `path/to/file.ext:line` |

## External HTTP field mappings

| Mapping ID | Call ID | Direction | Source field(s) | Target field(s) | Transformation | Condition/default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| FM-001 | HTTP-001 | EAPI→external | `source.path` | `target.path` | Rename/conversion | Condition | No/Yes | Confirmed | `path/to/file.ext:line` |

## Unmapped, dropped, opaque, or unresolved fields

Explain intentionally dropped values, fields hidden in unavailable shared transformers, and mappings that cannot be proven.

