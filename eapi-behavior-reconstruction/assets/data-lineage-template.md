---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Data lineage

## Repository data flow

```mermaid
flowchart LR
    A[Inbound boundary] --> B[Validation and normalization]
    B --> C[Behavior]
    C --> D[(Data asset)]
    C --> E[Response, event, or dependency]
```

Use boundary, behavior, data asset, field, and dependency IDs in node labels where practical.

## Object-level lineage

| Lineage ID | Source boundary/asset | Behavior | Transformation | Target boundary/asset | Condition/default | Lossy | Related field/rule IDs | Status | Evidence |
|---|---|---|---|---|---|---:|---|---|---|
| LINEAGE-resource | Source ID | Behavior ID | Parse/normalize/calculate/persist/emit | Target ID | Condition or None | Yes/No/Unknown | FIELD-/VR- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Transaction and partial-success boundaries

| Behavior | Ordered writes/calls/events | Transaction boundary | Failure point | Remaining state or side effect | Status | Evidence |
|---|---|---|---|---|---|---|
| Behavior ID | Operations | Transaction/none/Unknown | Failure ID | Rollback/partial/Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Lineage gaps

List opaque mappers, generated schemas, unavailable shared libraries, dynamic serializers, and external state ownership that prevents complete lineage.
