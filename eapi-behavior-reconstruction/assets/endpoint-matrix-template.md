---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Endpoint matrix

## Inbound endpoint inventory

| Endpoint ID | Method | Route | Consumer | Entry point | AuthN/AuthZ | Primary behavior | API contract | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| EP-POST-resource | POST | `/resource` | Caller or Unknown | Handler | Scheme or Unknown | repository.behavior-name | [Contract](contracts/EP-POST-resource.api-contract.md) | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Shared handlers and aliases

| Endpoint ID | Shares implementation with | Contract alias of | Difference | Status | Evidence |
|---|---|---|---|---|---|
| EP-POST-resource | Endpoint/handler or None | Endpoint ID or None | Route/auth/schema difference | Confirmed/Unknown | `path/to/file.ext:line` |

## Endpoint coverage gaps

List dynamic routes, unavailable gateway mappings, environment-dependent base paths, shared authorizers, generated APIs, and conflicting deployment definitions.
