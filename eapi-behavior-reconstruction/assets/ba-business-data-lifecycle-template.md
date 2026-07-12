---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../knowledge-manifest.yaml"
tech_data_lineage: "../tech-pack/data/data-lineage.md"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction with a business-readable information journey. Use claim_ids for material conclusions; do not leave this comment. -->

# Business data lifecycle

[View technical data lineage](../tech-pack/data/data-lineage.md)

## Business information journey

```mermaid
flowchart TD
```

Explain where material business information originates when known, which decisions or actions use it, how its meaning/state changes, and where it goes. Do not reproduce field paths or storage mechanics.

## Important business information

Describe significant information objects in short, readable entries. Use a compact table only when it makes comparison easier.

## Business-visible changes

Explain supported before/after meanings and their visible results. Do not turn local assignments or opaque save calls into business state changes.

## Lifecycle gaps

Summarize material unknown ownership, upstream origin, downstream use, or state meaning. Keep database, field-path, retention implementation, and AWS details in the Tech Pack.
