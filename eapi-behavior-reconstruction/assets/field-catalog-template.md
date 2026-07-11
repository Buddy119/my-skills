---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Field catalog

## Boundary and significant fields

| Field ID | Boundary ID/type | Field path | Meaning | Type/format | Required | Nullable | Source/default | Validation rule IDs | Lineage/mapping IDs | Status | Evidence |
|---|---|---|---|---|---:|---:|---|---|---|---|---|
| FIELD-EP-POST-resource-body-id | EP-POST-resource/request | `body.id` | Meaning or Unknown | Type/format | Yes/No/Conditional | Yes/No/Unknown | Source/default | VR- IDs | LINEAGE-/MAP- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Enum and code sets

| Field ID | Value | Meaning | Accepted/emitted | Mapping target | Status | Evidence |
|---|---|---|---|---|---|---|
| FIELD- ID | Code | Meaning or Unknown | Input/output/both | External value or None | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Field coverage gaps

List missing schemas, reflection, shared transformers, dynamic maps, generated models, or fields only visible at one boundary.
