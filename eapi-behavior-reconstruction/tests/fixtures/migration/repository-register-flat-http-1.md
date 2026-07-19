---
artifact_type: "repository-register"
artifact_schema_version: "flat-http-1"
repository: "fixture-repository"
source_commit: "unknown"
---

# Legacy repository register

## Legacy outbound HTTP field mappings

| Call ID | Usage ID | Mapping ID | Method | Logical Target | Client Operation | Behavior ID | Executable Call Site | Invocation Condition or Config | Observable Purpose | Direction | Source Field(s) | Target Field(s) | Transformation | Condition/Default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HTTP-007 | HTTP-007-U01 | FM-009 | POST | customer-system/customers | createCustomer | fixture.create-customer | src/Client.java:42 | enabled | Create customer | eapi-to-external | request.name | payload.customerName | rename | None | No | Confirmed | src/Client.java:40-44 |
| HTTP-007 | HTTP-007-U01 |  | POST | customer-system/customers | createCustomer | fixture.create-customer | src/Client.java:42 | enabled | Create customer | external-to-eapi | response.id | customerId | rename | None | No | Confirmed | src/Client.java:45-47 |

## Legacy external dependency rows

| Observation ID | Candidate dependency | Boundary type | Behavior ID | Operation or resource | Exchanged concept or observed effect | Availability observation | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| DEP-OBS-004 | Customer system | HTTP | fixture.create-customer | HTTP-007 | Customer creation | Failure is propagated | Confirmed | src/Client.java:40-50 |

## Legacy failure rows

| Observation ID | Failure category | Behavior ID | Trigger or source | Handling and propagation | Caller-visible result | State outcome | Retry or recovery | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| FO-003 | dependency | fixture.create-customer | Customer system error | propagated | Explicit error | Unchanged | Unknown | Confirmed | src/Service.java:30-36 |
