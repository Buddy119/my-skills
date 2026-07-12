---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction. Bind each proven HTTP call, mapping row, direction, and exact field value to passing CLM IDs. -->

# External HTTP mapping matrix

## Proven outbound HTTP calls

| Call ID | Dependency ID | Client operation | Method | Target | Behavior IDs | Config IDs | Status | Evidence |
|---|---|---|---|---|---|---|---|---|

## Request and consumed-response mappings

| Mapping ID | Call ID | Direction | Source boundary and field ID(s) | Source type/format | Target boundary and field path(s) | Target type/format | Transformation | Condition/default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---:|---|---|

## Unmapped and unresolved external fields

| Call ID and field | Observed treatment | Contract impact | Status | Evidence needed |
|---|---|---|---|---|

When no real outbound HTTP call exists, write `None observed` and keep manifest `external_http_calls` and `field_mappings` empty.
