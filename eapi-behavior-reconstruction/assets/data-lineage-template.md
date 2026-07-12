---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind each factual block to passing CLM IDs. -->

# Data lineage

## Repository data flow

```mermaid
flowchart TD
```

Use boundary, behavior, data asset, field, and dependency IDs in node labels where practical.

## Object-level lineage

| Lineage ID | Source boundary/asset | Behavior | Transformation | Target boundary/asset | Condition/default | Lossy | Related field/rule IDs | Status | Evidence |
|---|---|---|---|---|---|---:|---|---|---|

## Transaction and partial-success boundaries

| Behavior | Ordered writes/calls/events | Transaction boundary | Failure point | Remaining state or side effect | Status | Evidence |
|---|---|---|---|---|---|---|

## Lineage gaps

List opaque mappers, generated schemas, unavailable shared libraries, dynamic serializers, and external state ownership that prevents complete lineage.
