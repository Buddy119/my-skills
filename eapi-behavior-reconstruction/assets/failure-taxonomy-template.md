---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Failure taxonomy

## Failure landscape

Explain the repository's recurring failure patterns and distinguish business rejection, dependency failure, data consistency risk, and unhandled runtime failure.

| Category | Condition | Affected behaviors | Handling and visible result | Retry/recovery | Partial-state risk | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Validation/business/data/dependency/runtime | Condition | Behavior links | Result | Mechanism or Unknown | Risk or None observed | Confirmed | `path/to/file.ext:line` |

## Error translation and consistency

Explain where different implementation failures become the same outward error, or similar failures are handled differently across behaviors.

## Retry, idempotency, and partial success

Summarize cross-behavior retry, duplicate-delivery, compensation, transaction, and partial-completion patterns.

## Operational and business-visible gaps

Record unhandled cases, missing DLQs or retries, unknown recovery ownership, and other limitations supported by the repository evidence.
