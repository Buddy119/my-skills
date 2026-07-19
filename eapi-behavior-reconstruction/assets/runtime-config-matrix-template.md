---
artifact_type: "runtime-config-matrix"
artifact_schema_version: "2"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Runtime configuration matrix

Include only configuration that changes triggering, branching, dependencies, timing, retry, recovery, data selection, or observable outcomes.

| Configuration | Source/default | Read or wiring location | Affected behaviors | Behavioral effect | Scope/condition |
|---|---|---|---|---|---|
| Name *(Unknown)* | Environment/IaC/default/Unknown | Location | Behavior links | Effect | Condition [E1](#e1) |

## Configuration interactions

Explain combinations or precedence only when the repository provides evidence.

## Deployment-dependent unknowns

Record values supplied outside the repository and the behavior questions they leave unresolved without reproducing secret values.

## Source notes

<a id="e1"></a> **E1** — `path/to/config-or-wiring.ext:10-36` supports the configuration source, selection rule, and behavioral effect.
