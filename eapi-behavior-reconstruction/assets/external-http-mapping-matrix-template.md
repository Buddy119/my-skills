---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# External HTTP mapping matrix

## Proven outbound HTTP calls

| Call ID | Dependency ID | Client operation | Method | Target | Behavior IDs | Config IDs | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| HTTP-external-resource-create | DEP- ID | Client operation | POST | External target | Behavior IDs | CFG- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Request and consumed-response mappings

| Mapping ID | Call ID | Direction | Source boundary and field ID(s) | Target boundary and field path(s) | Transformation | Condition/default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---:|---|---|
| MAP-external-resource-create-eapi-to-external-id | HTTP- ID | eapi-to-external/external-to-eapi | FIELD- IDs | External path(s) | Copy/rename/convert/compute | Condition/default | Yes/No/Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Unmapped and unresolved external fields

| Call ID and field | Observed treatment | Contract impact | Status | Evidence needed |
|---|---|---|---|---|
| HTTP- ID field | Dropped/ignored/unresolved | Impact | Unknown/Conflicting | Schema, code, test, or owner |

When no real outbound HTTP call exists, write `None observed` and keep manifest `external_http_calls` and `field_mappings` empty.
