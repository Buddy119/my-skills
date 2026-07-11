---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Validation rule matrix

## Executable and schema rules

| Rule ID | Field IDs | Endpoint/behavior IDs | Rule | Missing/null/blank behavior | Normalization/default | Rejection result | Failure ID | Evidence layer | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| VR-resource-id-required | FIELD- ID | EP-/behavior IDs | Required/range/pattern/enum/cross-field rule | Distinction | Transformation or None | Status/error/event | FAIL- ID | L1/L2/L3 | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Cross-field and conditional rules

| Rule ID | Inputs | Condition | Required/forbidden effect | Output/failure | Status | Evidence |
|---|---|---|---|---|---|---|
| VR-conditional-rule | FIELD- IDs | Condition | Effect | FAIL- ID/result | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Assertion evidence

| Rule ID | Success assertion | Failure assertion | Coverage note |
|---|---|---|---|
| VR-resource-id-required | `path/to/test.ext:line` or None | `path/to/test.ext:line` or None | What is and is not proved |

## Validation gaps

List schema-only rules, shared validators, framework behavior, and untested branches. Do not claim runtime enforcement from a declaration alone.
