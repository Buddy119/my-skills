---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Field lineage

## Internal field transformations

| Lineage ID | Source boundary and field ID(s) | Target boundary and field ID(s) | Transformation | Condition/default | Lossy | Behavior | Status | Evidence |
|---|---|---|---|---|---:|---|---|---|
| LINEAGE-resource-id | FIELD- source | FIELD- target | Copy/rename/normalize/calculate/persist/emit | Condition or None | Yes/No/Unknown | Behavior ID | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Unmapped, dropped, and generated fields

| Boundary and field | Treatment | Resulting boundary/field | Reason or rule | Status | Evidence |
|---|---|---|---|---|---|
| FIELD- ID | Dropped/ignored/generated/unresolved | FIELD- ID or None | Rule or Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Lineage gaps

List opaque mappers, reflection, shared serializers, unavailable models, and dynamic field bags. This document describes internal lineage, not upstream/downstream mapping.
