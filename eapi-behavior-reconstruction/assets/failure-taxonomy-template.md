---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Failure taxonomy

## Failure registry

| Failure ID | Category | Origin | Trigger | Affected endpoint/behavior/dependency | Observable result | Retry owner | Retryable | Retry/DLQ/rollback | State/partial-success impact | Config IDs | Status | Evidence |
|---|---|---|---|---|---|---|---:|---|---|---|---|---|
| FAIL-resource-id-required | Validation | Source/component | Condition | EP-/behavior/DEP- IDs | HTTP/error/event/result | Caller/application/AWS/None/Unknown | Yes/No/Unknown | Mechanism | None/rollback/partial/Unknown | CFG- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Failure category summary

| Category | Failure IDs | Common observable effect | Recovery owner | Coverage gap |
|---|---|---|---|---|
| Validation/dependency/timeout/etc. | FAIL- IDs | Effect | Caller/application/AWS/Unknown | Gap or None |

## Partial success and compensation

| Failure ID | Completed operations | Incomplete operation | Remaining state/side effect | Compensation | Status | Evidence |
|---|---|---|---|---|---|---|
| FAIL-partial-result | Operations | Operation | State/effect | Mechanism or Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Failure coverage gaps

List opaque framework errors, untested branches, unavailable DLQ/retry settings, dynamic error serialization, and unknown remote failures.
