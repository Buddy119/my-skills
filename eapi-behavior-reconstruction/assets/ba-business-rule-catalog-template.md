---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../knowledge-manifest.yaml"
tech_validation_rules: "../tech-pack/fields/validation-rule-matrix.md"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction with a business-readable rule view. Use claim_ids for material conclusions; do not leave this comment. -->

# Business rule catalog

[View technical validation rules](../tech-pack/fields/validation-rule-matrix.md)

## Business-meaningful rules

Group supported rules by capability or scenario. Explain the condition, affected business information, and outcome or exception in natural language. Use a table only when readers need to compare several rules.

## Rule interactions

Explain supported dependencies, conflicts, ordering, or precedence. Omit this section when the repository establishes none.

## Excluded technical validation

Briefly identify categories intentionally omitted because they concern serialization, null safety, transport shape, framework behavior, or infrastructure rather than a supported business meaning.

## Rule gaps

List rules whose business rationale, ownership, precedence, or completeness remains unknown or conflicting.
