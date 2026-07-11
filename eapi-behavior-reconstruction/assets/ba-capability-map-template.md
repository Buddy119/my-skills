---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../knowledge-manifest.yaml"
tech_overview: "../tech-pack/repository-overview.md"
coverage_status: "complete|partial|blocked"
---

# Business capability map

## Capabilities and outcomes

| Capability | Business purpose | Actors/participants | Behavior IDs | Trigger | Business outcome | External participant | Status |
|---|---|---|---|---|---|---|---|
| Capability or Unknown | Supported purpose without invented intent | Actors | Behavior IDs | Request/event/schedule | Outcome | Participant or None | Confirmed/Inferred/Unknown |

## Capability relationships

```mermaid
flowchart LR
    A[Actor or participant] --> C[Business capability]
    C --> O[Business outcome]
    C --> X[External participant]
```

## Capability gaps

List inferred or unknown purpose, missing upstream/downstream context, and technical behaviors with no established business meaning. See the [technical overview](../tech-pack/repository-overview.md).
