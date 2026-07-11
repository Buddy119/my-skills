---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# State transition matrix

## Confirmed and inferred transitions

| Transition ID | Data object/asset | State field | From state | Triggering behavior | Rule/condition | To state | Persisted/emitted effect | Failure/partial state | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| STATE-resource-created | DATA- ID | `status` or Unknown | Absent/Any/Unknown | Behavior ID | VR- ID or condition | New state | Write/event | FAIL- ID or None | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Transition guards and concurrency

| Transition ID | Idempotency | Duplicate handling | Concurrency/version rule | Transaction/rollback | Status | Evidence |
|---|---|---|---|---|---|---|
| STATE-resource-created | Mechanism or Unknown | Outcome or Unknown | Rule or Unknown | Boundary or Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## No-state and unresolved cases

Record persistence changes with unknown business state, stateless behaviors, missing prior-state reads, and unavailable transaction evidence. Write `None observed` when the repository exposes no state transition.
