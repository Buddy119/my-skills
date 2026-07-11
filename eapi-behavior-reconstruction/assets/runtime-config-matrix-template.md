---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Runtime configuration matrix

## Application configuration

| Config ID | Key/reference | Category | Defined by | Read/used by | Type/allowed values | Required | Default | Affects IDs | Missing/invalid result | Environment variance | Sensitive | Status | Evidence |
|---|---|---|---|---|---|---:|---|---|---|---|---:|---|---|
| CFG-resource-endpoint | Key name | Environment/flag/resource/other | IaC/config/code | Location | Type/values | Yes/No/Conditional | Code/deployment default | Behavior/EP-/DEP-/FAIL- IDs | Result | Difference or Unknown | Yes/No/Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## AWS Lambda and trigger runtime

| Config ID | Function/trigger | Setting | Value/default | Behavior effect | Failure/retry effect | Status | Evidence |
|---|---|---|---|---|---|---|---|
| CFG-lambda-timeout | Function | Runtime/memory/timeout/concurrency/batch/filter/retry/DLQ | Value or Unknown | Effect | FAIL- IDs/effect | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Configuration conflicts and gaps

| Config ID/key | Code observation | IaC/config observation | Runtime impact | Status | Evidence needed |
|---|---|---|---|---|---|
| CFG- ID | Value/default | Value/default | Impact | Conflicting/Unknown | Environment artifact or owner |

Never reproduce secret or parameter values. Record only names, wiring, and behaviorally relevant use.
