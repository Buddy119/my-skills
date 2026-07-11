---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Repository knowledge coverage

## Inventory coverage

| Entity | Discovered | Documented | Excluded | Blocked | Unknown | Coverage notes |
|---|---:|---:|---:|---:|---:|---|
| Behaviors | 0 | 0 | 0 | 0 | 0 | Notes |
| Endpoints | 0 | 0 | 0 | 0 | 0 | Notes |
| Data assets | 0 | 0 | 0 | 0 | 0 | Notes |
| Fields | 0 | 0 | 0 | 0 | 0 | Notes |
| Validation rules | 0 | 0 | 0 | 0 | 0 | Notes |
| Dependencies | 0 | 0 | 0 | 0 | 0 | Notes |
| Runtime configurations | 0 | 0 | 0 | 0 | 0 | Notes |
| Failures | 0 | 0 | 0 | 0 | 0 | Notes |
| External HTTP calls and mappings | 0 | 0 | 0 | 0 | 0 | Notes |

## Entry-point disposition

| Discovered entry point | Type | Disposition | Behavior/endpoint ID | Reason | Evidence |
|---|---|---|---|---|---|
| Handler or route | API/event/queue/schedule | Documented/Technical/Duplicate/Excluded/Blocked | ID | Reason | `path/to/file.ext:line` |

## Evidence surface coverage

| Evidence surface | Availability | Used for | Limitation |
|---|---|---|---|
| Production source | Available/Partial/Missing | Behavior and rules | Limitation |
| Tests and assertions | Available/Partial/Missing | Success/failure outcomes | Limitation |
| IaC/deployment configuration | Available/Partial/Missing | Endpoint/runtime wiring | Limitation |
| Request/response/event schemas | Available/Partial/Missing | Contract and fields | Limitation |
| Shared libraries/layers | Available/Partial/Missing | Opaque behavior | Limitation |

## Unresolved coverage gaps

| Gap | Affected knowledge | Impact | Status | Evidence or owner needed |
|---|---|---|---|---|
| Missing artifact or ambiguity | IDs/documents | What cannot be safely assumed | Unknown/Conflicting/Blocked | Artifact or owner |

## Coverage conclusion

Explain why the overall status is complete, partial, or blocked. Targeted analysis must remain partial unless it refreshes an already complete manifest.
