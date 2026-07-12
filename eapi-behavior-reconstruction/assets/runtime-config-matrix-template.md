---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction. Bind each configuration row, exact key/default, and runtime effect to passing CLM IDs; Reference prose may summarize naturally. -->

# Runtime configuration matrix

## Application configuration

| Config ID | Key/reference | Category | Defined by | Read/used by | Type/allowed values | Required | Default | Affects IDs | Missing/invalid result | Environment variance | Sensitive | Status | Evidence |
|---|---|---|---|---|---|---:|---|---|---|---|---:|---|---|

## AWS Lambda and trigger runtime

| Config ID | Function/trigger | Setting | Value/default | Behavior effect | Failure/retry effect | Status | Evidence |
|---|---|---|---|---|---|---|---|

## Configuration conflicts and gaps

| Config ID/key | Code observation | IaC/config observation | Runtime impact | Status | Evidence needed |
|---|---|---|---|---|---|

Never reproduce secret or parameter values. Record only names, wiring, and behaviorally relevant use.
