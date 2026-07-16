---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Data and state lifecycle

## Lifecycle overview

Explain where important business objects or records originate, how they move through repository behaviors, and where they leave or terminate. Use a Mermaid state or flow diagram when it clarifies the lifecycle.

## Objects, stores, and ownership boundary

| Object or record | Source | Repository/store | Owning or observing behaviors | Destination | Status | Evidence |
|---|---|---|---|---|---|---|
| Object | Source | Store/resource | Behavior links | Destination | Confirmed | `path/to/file.ext:line` |

## State transitions

| Object | From | To | Triggering behavior | Condition | Side effects | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Object | State/source | State/destination | [Behavior](behaviors/repository.behavior.md) | Condition | Effect | Confirmed | `path/to/file.ext:line` |

## Consistency, transaction, and retention questions

Explain transaction boundaries, concurrent updates, partial writes, retention, ordering, and unresolved ownership only where the repository provides evidence or a meaningful gap.

