---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every example and instruction. Bind each factual block to passing CLM IDs. -->

# State transition matrix

## Confirmed and inferred transitions

| Transition ID | Data object/asset | State field | From state | Triggering behavior | Rule/condition | To state | Persisted/emitted effect | Failure/partial state | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|

## Transition guards and concurrency

| Transition ID | Idempotency | Duplicate handling | Concurrency/version rule | Transaction/rollback | Status | Evidence |
|---|---|---|---|---|---|---|

## No-state and unresolved cases

Record persistence changes with unknown business state, stateless behaviors, missing prior-state reads, and unavailable transaction evidence. Write `None observed` when the repository exposes no state transition.
