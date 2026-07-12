---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../knowledge-manifest.yaml"
tech_failure_taxonomy: "../tech-pack/reliability/failure-taxonomy.md"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind each factual block to passing CLM IDs. -->

# Business exception catalog

[View technical failure taxonomy](../tech-pack/reliability/failure-taxonomy.md)

## Business-visible exceptions

| Business exception ID | Capability/behavior | Business condition | Business impact | Visible result | Recovery/next action | Status |
|---|---|---|---|---|---|---|

## Partial and delayed outcomes

| Business exception ID | Completed outcome | Incomplete/delayed outcome | Remaining business state | Recovery owner | Status |
|---|---|---|---|---|---|

## Exception gaps

List technical failures whose business-visible result, recovery expectation, or ownership cannot be established. Do not expose exception classes or infrastructure identifiers.
