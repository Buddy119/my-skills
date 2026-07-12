---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction. Bind each structured field transformation and exact source/target value to passing CLM IDs. -->

# Field lineage

## Internal field transformations

| Lineage ID | Source boundary and field ID(s) | Target boundary and field ID(s) | Transformation | Condition/default | Lossy | Behavior | Status | Evidence |
|---|---|---|---|---|---:|---|---|---|

## Unmapped, dropped, and generated fields

| Boundary and field | Treatment | Resulting boundary/field | Reason or rule | Status | Evidence |
|---|---|---|---|---|---|

## Lineage gaps

List opaque mappers, reflection, shared serializers, unavailable models, and dynamic field bags. This document describes internal lineage, not upstream/downstream mapping.
