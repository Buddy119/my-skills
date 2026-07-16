---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Runtime configuration matrix

Include only configuration that changes triggering, branching, dependencies, timing, retry, recovery, data selection, or observable outcomes.

| Configuration | Source/default | Read or wiring location | Affected behaviors | Behavioral effect | Scope/condition | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Name | Environment/IaC/default/Unknown | Location | Behavior links | Effect | Condition | Confirmed | `path/to/file.ext:line` |

## Configuration interactions

Explain combinations or precedence only when the repository provides evidence.

## Deployment-dependent unknowns

Record values supplied outside the repository and the behavior questions they leave unresolved without reproducing secret values.

