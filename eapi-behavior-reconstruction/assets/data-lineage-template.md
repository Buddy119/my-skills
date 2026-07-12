---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction. Bind each structured lineage row, relationship, and exact value to passing CLM IDs; Reference prose may summarize naturally. -->

# Data lineage

## Repository data flow

Place a `<!-- claims: CLM-... -->` marker immediately before or after the diagram. Its passing Claims must support every rendered relationship; split the graph when one Claim set cannot support the whole diagram.

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
