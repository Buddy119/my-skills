---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../knowledge-manifest.yaml"
tech_validation_rules: "../tech-pack/fields/validation-rule-matrix.md"
coverage_status: "complete|partial|blocked"
---

# Business rule catalog

[View technical validation rules](../tech-pack/fields/validation-rule-matrix.md)

## Business-meaningful rules

| Business rule ID | Capability/behavior | Rule | Business information | Condition | Business outcome or exception | Status |
|---|---|---|---|---|---|---|
| BR-resource-eligibility | Capability/behavior | Business-readable rule | Information concept | Condition | Outcome/exception | Confirmed/Inferred/Unknown |

## Rule interactions

| Business rule ID | Depends on | Conflicts with | Ordering or precedence | Status |
|---|---|---|---|---|
| BR- ID | BR- ID or None | BR- ID or None | Rule or Unknown | Confirmed/Inferred/Unknown |

## Excluded technical validation

Summarize categories intentionally omitted because they only concern serialization, null safety, transport shape, framework behavior, or infrastructure rather than a supported business meaning.

## Rule gaps

List rules whose business rationale, ownership, precedence, or completeness remains unknown or conflicting.
