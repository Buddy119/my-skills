---
behavior_id: "repository.behavior-name"
working_title: "Human-readable working title"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
understanding_status: "tracing|understood|blocked"
entry_type: "api|sqs|sns|eventbridge|schedule|stream|step-function|other"
entry_points:
  - "repository-relative-file:line"
---

# Behavior working dossier

This file is a private analysis artifact. Write connected working explanations rather than final documentation or atomic claims.

## Working purpose and boundary

Explain the observable purpose currently suggested by the executable path, what starts the behavior, where the repository's responsibility ends, and which business meaning remains uncertain.

## End-to-end executable narrative

Retell the flow from trigger to observable result in natural language. Include the major calls and decisions needed to understand the behavior without listing every method.

## Input handling and validation

Record parsing, normalization, required information, authorization, and conditions that stop or redirect processing.

## Decisions and rules

Explain decisions that materially change the path, result, state, external interaction, or visible failure. Attach evidence to the meaningful rule or paragraph.

## Main successful path

Describe the ordered happy path and its observable outcome.

## Data, business objects, and state

Record reads, writes, affected objects, state transitions, transaction boundaries, and unresolved consistency questions.

## Boundaries, outputs, and side effects

Record responses, events, messages, external calls, and other effects. Keep remote internals unknown unless separately available in this repository.

## Failures, retry, and partial success

Explain important failure conditions, visible results, retries, DLQs, compensation, idempotency, and partial completion where observed.

## Runtime configuration and IaC

Record only wiring or configuration that affects triggering, branching, dependencies, timeouts, retry, recovery, or outcomes.

## Test observations

Record one or two concrete assertions when relevant tests exist, prioritizing a material failure path. State when tests were not found or do not exercise the path.

## Evidence anchors

- `path/to/file.ext:line` — what this location helps establish

## Unknowns, conflicts, and limitations

Explain unanswered questions, conflicting artifacts, unavailable shared code, dynamic behavior, and the impact on understanding.

## Repository register contributions

List the endpoint, data/state, field rule, outbound HTTP mapping, configuration, dependency, failure, and cross-behavior observations added to `repository-register.md`. Omit categories not observed.

## Understanding gate

- [ ] The complete flow can be retold coherently.
- [ ] Main success and material decision paths were checked.
- [ ] Data, state, boundaries, outputs, and failures were checked.
- [ ] Tests, configuration, and IaC were inspected or their absence recorded.
- [ ] Repository-external internals remain qualified.
- [ ] Key evidence and unresolved questions are recorded.
- [ ] Applicable repository-register sections were updated.

Set `understanding_status: understood` only after this reasoning review passes.

