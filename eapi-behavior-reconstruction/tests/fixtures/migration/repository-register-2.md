---
artifact_type: "repository-register"
artifact_schema_version: "2"
repository: "fixture"
source_commit: "abc123"
register_status: "reconciled"
---

# Repository register

## Runtime configuration effects

| Configuration key or selector | Behavior ID | Read or wiring location | Default or value source | Observed execution effect | Scope or condition | Status | Evidence |
|---|---|---|---|---|---|---|---|
| `client.timeout` | `fixture.get-customer` | `src/ClientConfig.java:12` | `30s` default | Changes the outbound timeout | All calls | Confirmed | `src/ClientConfig.java:12` |
| `profile` | `fixture.get-customer` | `src/Wiring.java:20` | Runtime profile | Selects one client implementation | Profile-specific | Inferred | `src/Wiring.java:20` |

## Failure observations

| Observation ID | Failure category | Behavior ID | Trigger or source | Handling and propagation | Caller-visible result | State outcome | Retry or recovery | Status | Evidence | Reconciliation |
|---|---|---|---|---|---|---|---|---|---|---|
| `FO-003` | dependency | `fixture.get-customer` | Client timeout | Translated by boundary handler | Explicit error | Unchanged | Unknown | Confirmed | `src/Handler.java:30` | `FAIL-002` |

## Field validation and internal transformation observations

| Boundary or model | Field(s) | Behavior ID | Rule or transformation | Result when violated | Status | Evidence |
|---|---|---|---|---|---|---|
| API | `customerId` | `fixture.get-customer` | Required | Rejected | Confirmed | `src/Handler.java:10` |
