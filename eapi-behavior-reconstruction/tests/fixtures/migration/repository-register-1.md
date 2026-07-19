---
artifact_type: "repository-register"
artifact_schema_version: "1"
repository: "fixture-repository"
source_commit: "unknown"
register_status: "reconciled"
---

# Repository working register

## Business objects, data resources, and state changes

| Object or resource | Behavior ID | Operation | From state/source | To state/destination | Condition | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Customer record | fixture.update-customer | Read | customer table | service | always | Confirmed | src/Service.java:10 |
| Customer record | fixture.update-customer | Update | existing record | persisted record | request is valid | Confirmed | src/Service.java:20-24 |

## Unrelated preserved section

This text must remain byte-for-byte unchanged by the lifecycle structural migration.
