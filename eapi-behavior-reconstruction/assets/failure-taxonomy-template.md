---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind each factual block to passing CLM IDs. -->

# Failure taxonomy

## Failure registry

| Failure ID | Category | Origin | Trigger | Affected endpoint/behavior/dependency | Observable result | Retry owner | Retryable | Retry/DLQ/rollback | State/partial-success impact | Config IDs | Status | Evidence |
|---|---|---|---|---|---|---|---:|---|---|---|---|---|

## Failure category summary

| Category | Failure IDs | Common observable effect | Recovery owner | Coverage gap |
|---|---|---|---|---|

## Partial success and compensation

| Failure ID | Completed operations | Incomplete operation | Remaining state/side effect | Compensation | Status | Evidence |
|---|---|---|---|---|---|---|

## Failure coverage gaps

List opaque framework errors, untested branches, unavailable DLQ/retry settings, dynamic error serialization, and unknown remote failures.
