---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
knowledge_manifest: "../../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

# Data asset catalog

## Data assets

| Data asset ID | Kind | Logical name | Ownership boundary | Identity/key | Lifecycle role | Read by | Written by | Retention/TTL | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| DATA-dynamodb-resource | Store/message/event/parameter/secret/other | Resource | This repo/external/Unknown | Key or Unknown | Source/state/output/reference | Behavior IDs | Behavior IDs | Value or Unknown | Confirmed/Inferred/Unknown | `path/to/file.ext:line` |

## Data ownership and consistency

Record system-of-record evidence, transaction boundaries, consistency model, concurrency controls, and ownership ambiguity. Do not infer ownership from a client or table name alone.

## Data asset gaps

List unavailable schemas, dynamic resource names, shared persistence layers, retention settings, and unresolved key structures.
