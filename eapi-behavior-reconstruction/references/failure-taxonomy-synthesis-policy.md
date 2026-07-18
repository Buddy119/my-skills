# Failure taxonomy synthesis policy

## Purpose

Turn behavior-level failure observations into a repository-wide failure model that explains recurring patterns, caller visibility, state consequences, retry safety, and recovery. Keep every `FO-nnn` observation in the repository register; publish one section per reconciled `FAIL-nnn` Pattern.

## Observation and Pattern model

Record each material failure path as a Failure Observation with its Behavior, trigger/source, handling/propagation, caller-visible result, state outcome, retry/recovery, status, and evidence. Assign every Observation to one Pattern or mark it `Unresolved`.

Create or merge a Failure Pattern only when these dimensions are materially equivalent:

1. Failure source or triggering condition.
2. Propagation, translation, swallowing, or degradation behavior.
3. Caller-visible or asynchronously visible result.
4. Data and business-state outcome.
5. Retry safety, rollback, compensation, and recovery semantics.

An exception class, error code, response status, log text, or dependency name alone is not a Pattern identity. Split observations when one path returns an error but another swallows it, when one rolls back but another leaves committed state, or when retry safety differs materially. Keep minor behavior-specific variations inside one Pattern only when the five identity dimensions remain equivalent.

## Normalized dimensions

Use:

- Caller Visibility: `Explicit error`, `Degraded result`, `Success with loss`, `Swallowed`, `Async only`, or `Unknown`.
- State Outcome: `Unchanged`, `Rolled back`, `Partial`, `Committed before failure`, or `Unknown`.
- Retry Safety: `Safe`, `Conditional`, `Unsafe`, or `Unknown`.
- Recovery: one or more of `Automatic retry`, `Rollback`, `Compensation`, `Manual`, `None observed`, or `Unknown`.

Do not equate an exception catch with recovery, a transaction annotation with proven rollback for every side effect, an infrastructure retry setting with safe repetition, or absence of a retry definition with proof that retries never occur.

## Risk attention

Use an evidence-grounded reader-attention label, not a formal enterprise risk score:

- `High`: partial or committed state may remain; the repository can report success while losing a required outcome; repetition is unsafe and may duplicate or corrupt results; or a required outcome fails without reliable recovery.
- `Medium`: a required outcome fails or degrades, but the failure is visible and state is controlled, or recovery is conditional or manual.
- `Low`: the operation is rejected before material side effects, state remains unchanged or is reliably rolled back, the result is clear, and repetition is safe.
- `Unknown`: evidence cannot establish the decisive visibility, state, retry, or recovery dimensions.

Assign `Low` only when all relevant dimensions support it. Prefer `Unknown` to a reassuring label when decisive evidence is missing. Describe business impact separately and do not invent severity unavailable from the repository.

## Repository synthesis

Use the reconciled Patterns to identify:

- Recurring failures shared by several Behaviors or capabilities.
- Similar failures translated differently across entry points.
- Dependency failures that produce different state or caller outcomes.
- Partial, committed, swallowed, degraded, and false-success paths.
- Safe, conditional, unsafe, and unknown repetition.
- Automatic retry, rollback, compensation, manual recovery, missing recovery, and unclear ownership.
- Highest-attention and materially Unknown consistency or business-outcome risks.

Do not claim recurrence when only one Observation exists. A single material Pattern still belongs in the taxonomy when it helps explain repository risk.

## Reader publication and document boundaries

Publish `failure-taxonomy.md` from reconciled Patterns, not from the raw observations.

- Use one index row and one anchored detail section per `FAIL-nnn`.
- Lead with the repository failure model and High/Unknown attention items.
- Link caller-visible response shapes to API Contracts.
- Link internal behavior paths to Tech Behaviors.
- Link state transitions to Data Lifecycle and dependency availability to External Dependency Contracts.
- Keep observation evidence in compact Source notes rather than a global failure inventory.
- Omit the document when no material failure is observed and record `Not observed` in Repository Overview.

## Completion and review gate

Before publication, confirm:

- Every Failure Observation is assigned or explicitly unresolved.
- Pattern grouping considers all five identity dimensions.
- Swallowed, degraded, false-success, partial-state, and committed-before-failure paths have not been hidden inside generic categories.
- Retry safety and recovery are supported or `Unknown`.
- High attention can be traced to evidence and Low is not used when decisive evidence is missing.
- Cross-behavior inconsistencies and recovery gaps are summarized without copying API, Behavior, lifecycle, or Dependency detail.
