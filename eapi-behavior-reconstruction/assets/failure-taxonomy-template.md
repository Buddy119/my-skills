---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Failure taxonomy

Explain the repository's failure model as recurring patterns. Preserve observation-level evidence in the working register; do not publish a row-by-row failure inventory.

## Repository failure model

Summarize the dominant rejection, dependency, data-consistency, configuration, asynchronous, and unexpected-runtime failure themes. Distinguish recurring patterns from behavior-specific exceptions.

## Highest-attention risks

Lead with supported `High` risks and material `Unknown` risks. Explain why they matter in terms of caller visibility, partial or committed state, unsafe repetition, lost outcomes, or missing recovery. Do not invent business severity unavailable from the repository.

## Failure pattern index

Use one row per Failure Pattern. Order High and Unknown attention first, without hiding Medium or Low patterns.

| Failure pattern | Category | Affected capabilities | Caller visibility | State outcome | Retry safety | Risk attention | Details |
|---|---|---|---|---|---|---|---|
| `FAIL-001` — Pattern name | Normalized category | Capability/Behavior links | Explicit error/Degraded result/Success with loss/Swallowed/Async only/Unknown | Unchanged/Rolled back/Partial/Committed before failure/Unknown | Safe/Conditional/Unsafe/Unknown | High/Medium/Low/Unknown | [Details](#fail-001) |

<a id="fail-001"></a>
## `FAIL-001` — Failure pattern name

### Trigger and affected capabilities

Explain the common failure source or condition and the capabilities and behaviors in which this pattern occurs.

### Propagation and caller-visible result

Describe whether the failure is rejected, translated, propagated, swallowed, degraded, or visible only asynchronously. Link caller-facing API errors to their API Contracts rather than repeating status and response tables.

### State outcome

Explain whether state is unchanged, rolled back, partial, already committed, or Unknown. Link detailed object transitions to [data lifecycle](data-lifecycle.md).

### Retry, rollback, compensation, and recovery

State whether repeating the operation is Safe, Conditional, Unsafe, or Unknown, and describe only observed automatic retry, rollback, compensation, manual recovery, or absence of recovery.

### Variations across behaviors

Explain material implementation or outcome variations that remain inside this Pattern. Split the Pattern when caller visibility, state outcome, or recovery semantics are not materially equivalent.

### Related dependencies and documents

Link related [dependency contracts](external-dependency-contracts.md), Tech Behaviors, API Contracts, configuration, and lifecycle details without copying them.

### Unknowns and source notes

- Unknowns or conflicts:
- Source notes:
  - `path/to/file.ext:line` — what the source establishes about this failure pattern

Repeat one anchored `## FAIL-nnn` section for each synthesized Pattern. Remove optional subsections that add no reader value.

## Cross-pattern inconsistencies and recovery gaps

Summarize similar failures that are translated differently, inconsistent state outcomes, unsafe or unknown retry behavior, missing compensation, swallowed failures, false-success paths, and recovery ownership gaps.
