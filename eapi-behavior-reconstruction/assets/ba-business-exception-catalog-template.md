---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../knowledge-manifest.yaml"
tech_failure_taxonomy: "../tech-pack/reliability/failure-taxonomy.md"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction with a business-readable exception view. Use claim_ids for material conclusions; do not leave this comment. -->

# Business exception catalog

[View technical failure taxonomy](../tech-pack/reliability/failure-taxonomy.md)

## Business-visible exceptions

Group exceptions by scenario. Explain the business condition, visible impact, result, and recovery or next action when supported. Do not expose exception classes or infrastructure identifiers.

## Partial and delayed outcomes

Explain partial or delayed results as short scenarios. Distinguish what completed, what remains uncertain, and who owns recovery only when known.

## Exception gaps

List technical failures whose business-visible result, recovery expectation, or ownership cannot be established. Do not expose exception classes or infrastructure identifiers.
