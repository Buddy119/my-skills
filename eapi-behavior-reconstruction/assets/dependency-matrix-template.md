---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# External dependency matrix

## Dependency inventory

| Dependency ID | Name | Type | Material | Direction | Target/resource | Used by | Contract stub | Config IDs | Failure IDs | Status | Evidence |
|---|---|---|---:|---|---|---|---|---|---|---|---|
| DEP-external-resource-system | Dependency | HTTP/Lambda/queue/topic/event/store/library/layer/other | Yes/No | Inbound/outbound/bidirectional | Identity | Endpoint/behavior IDs | [Stub](stubs/DEP-external-resource-system.contract-stub.md) or N/A | CFG- IDs | FAIL- IDs | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Interaction and availability summary

| Dependency ID | Request/event/resource contract | Response/result | Timeout/retry/DLQ | Error translation | Business/technical impact | Status |
|---|---|---|---|---|---|---|
| DEP- ID | Summary | Summary | Mechanism or Unknown | FAIL- IDs | Impact | Confirmed/Inferred/Unknown |

## Dependency coverage gaps

List dynamic endpoints, environment-only resources, unavailable shared components, missing remote schemas, and dependencies with unknown ownership.
