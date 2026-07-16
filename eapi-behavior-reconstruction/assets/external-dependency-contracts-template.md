---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# External dependency contracts

Describe only the boundary visible in this repository. Do not infer remote implementation.

## Dependency landscape

| Dependency | Type | Affected behaviors | Purpose at boundary | Availability impact | Status | Evidence |
|---|---|---|---|---|---|---|
| System/resource/library | HTTP/event/queue/store/lambda/library | Behavior links | Observed purpose or Unknown | Impact | Confirmed | `path/to/file.ext:line` |

## Observed operations and contracts

### Dependency or operation

- Invocation and condition:
- Observed request, event, or resource:
- Observed response or effect:
- Timeout, retry, and recovery:
- Known failure outcomes:
- Unknown remote behavior:
- Evidence:

## Shared and environment-provided dependencies

Explain layers, libraries, generated clients, environment wiring, or schemas whose implementation is unavailable and the resulting limitations.

