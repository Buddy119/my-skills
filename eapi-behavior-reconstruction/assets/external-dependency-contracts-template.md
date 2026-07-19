---
artifact_type: "external-dependency-contracts"
artifact_schema_version: "2"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# External dependency contracts

Explain the external participants and resources this repository actually depends on. Synthesize observations into dependency contracts; do not copy the working-register rows or infer remote implementation.

## Dependency landscape

Use one row per Dependency ID. `Criticality` is the highest supported usage-level classification; call out mixed or Unknown usages in the detail section.

| Dependency | Type and repository-observed role | Dependent capabilities | Criticality | Availability impact | Details |
|---|---|---|---|---|---|
| `DEP-001` — Dependency name | Type — concise boundary role | Capability/Behavior links | Required/Degradable/Optional/Unknown | Concise visible impact | [Details](#dep-001) |

<a id="dep-001"></a>
## `DEP-001` — Dependency name

### Role and boundary

Explain what this external participant or resource enables, which boundary is observable in this repository, and where repository responsibility ends.

### Dependent capabilities and behaviors

Describe the shared business or technical capabilities that depend on it. Link the relevant Tech Behaviors without repeating their internal flows.

### Observed operations and exchanged concepts

List each operation once beneath this Dependency. Describe exchanged concepts rather than repeating field-level mappings.

| Operation | Boundary reference | Purpose and condition | Concepts sent, consumed, read, or written | Affected capabilities/behaviors |
|---|---|---|---|---|
| `DEP-001-OP01` *(Inferred)* | [HTTP-001](field-validation-and-mapping.md#http-001), event, or resource | Observable operation purpose and invocation condition | Business/data concepts | Behavior links [E1](#e1) |

### Availability impact and criticality

Explain Required, Degradable, Optional, or Unknown classifications at the operation or behavior level. State what stops, continues, becomes delayed, or remains incomplete when the dependency is unavailable.

### Fallback, degradation, and state implications

Describe only observed alternative paths, retries, partial success, state inconsistency, compensation, or manual recovery. Link relevant [failure patterns](failure-taxonomy.md) and [data lifecycle](data-lifecycle.md) sections instead of reproducing them.

### Known local contract and unknown remote behavior

Separate what this repository sends, consumes, or assumes from remote SLA, persistence, idempotency, error semantics, and implementation that remain Unknown.

### Related documents and source notes

- Related Tech Behaviors:
- Field mappings or resource details:
- Failure patterns:
<a id="e1"></a> **E1** — `path/to/dependency-boundary.ext:18-64` supports the grouped role, operations, and observed availability impact.

Repeat one anchored `## DEP-nnn` section for each synthesized Dependency. Remove optional subsections that add no reader value.
