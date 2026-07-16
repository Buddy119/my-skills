---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Endpoint matrix

Use one row per runtime API endpoint, including endpoints that share a behavior.

| Endpoint ID | Method | Route | Authentication | Behavior | Entry point | Contract | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| `repository.method-route` | METHOD | `/route` | Scheme or Unknown | [Behavior](behaviors/repository.behavior.md) | Handler/route | [Contract](contracts/repository.method-route.api-contract.md) | Confirmed | `path/to/file.ext:line` |

## Shared implementation and routing notes

Explain endpoints that share one behavior, differ by version or route parameters, or are conditionally wired.

## Unknowns and conflicts

Record unresolved authentication, deployment, route, or contract questions.

