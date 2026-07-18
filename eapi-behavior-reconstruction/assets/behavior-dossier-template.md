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

## Semantic symbol and call trace

Use this working section for Java behaviors; remove it for non-Java behaviors.

- **Language and project model:** Java version/build modules/source sets relevant to this behavior.
- **Semantic-navigation status:** `used|degraded|unavailable`, including project-import readiness and the available capability.
- **Exact entry symbol:** Fully qualified type, method signature, and entry definition.
- **Confirmed definitions and outgoing calls:** Exact symbols for critical calls, with source locations used to confirm them.
- **Incoming callers or framework entry:** Production callers, test-only references, or route/listener/Lambda/configuration evidence when no Java caller exists.
- **Interfaces, overrides, and implementation candidates:** Exact interface method, overrides, and all relevant candidates.
- **Runtime implementation binding:** Constructor/field/parameter injection and `@Bean`, `@Qualifier`, `@Primary`, `@Profile`, component-scan, test, or runtime-config evidence. Keep selection unresolved when evidence does not choose one candidate.
- **Dynamic, generated, or unresolved edges:** Proxy/AOP, reflection, annotation callbacks, event dispatch, Lombok, MapStruct, Spring Data, generated code, or incomplete semantic results.
- **Effect on behavior conclusions:** What remains `Inferred` or `Unknown`, and whether the limitation affects the main flow.

## Endpoint exposure evidence

Use this working section for API behaviors; remove it for non-API behaviors. Do not merge observations before repository synthesis.

| Layer | Observed identity or value | Status | Evidence/register IDs | Limitation |
|---|---|---|---|---|
| Application Route | Application method, route, and handler | Confirmed | `path/to/file.ext:line`; `EP-EV-001` | None or limitation |
| External Entry Declaration | External method, path, target, or None | Confirmed/Conflicting/Unknown/Not observed | Evidence or `EP-EV-nnn` | Mapping or missing evidence |
| Environment Deployment Intent | Environment and declared binding or None | Confirmed/Conflicting/Unknown/Not observed | Evidence or `EP-EV-nnn` | Limitation |
| Observed Runtime Deployment | Sanitized observation or None | Confirmed/Conflicting/Unknown/Not observed | Evidence or `EP-EV-nnn` | Limitation |
| External Reachability Assessment | Derived result and observed access conditions | Confirmed/Conflicting/Unknown/Not observed | Related `EP-EV-nnn` rows | Reasoning and missing link |

List explicit target, binding, rewrite, or mapping evidence used to correlate layers. Method/route similarity alone is not a correlation.

## Input handling and validation

Record parsing, normalization, required information, authorization, and conditions that stop or redirect processing.

## Decisions and rules

Explain decisions that materially change the path, result, state, external interaction, or visible failure. Attach evidence to the meaningful rule or paragraph.

## Main successful path

Describe the ordered happy path and its observable outcome.

## Data, business objects, and state

Record reads, writes, affected objects, state transitions, transaction boundaries, and unresolved consistency questions.

## Boundaries, outputs, and side effects

Record responses, events, messages, external calls, resources, and other effects. Add each executable external boundary as a `DEP-OBS-nnn` observation in the repository register. Keep remote internals unknown unless separately available in this repository; do not create a Dependency Contract while tracing one Behavior.

## Failures, retry, and partial success

Explain important failure conditions, propagation, visible results, state outcomes, retries, DLQs, compensation, idempotency, and partial completion where observed. Add each material path as an `FO-nnn` observation in the repository register. Do not assign repository-wide Failure Patterns until synthesis.

## Runtime configuration and IaC

Record only wiring or configuration that affects triggering, branching, dependencies, timeouts, retry, recovery, or outcomes.

## Test observations

Record one or two concrete assertions when relevant tests exist, prioritizing a material failure path. State when tests were not found or do not exercise the path.

## Evidence anchors

- `path/to/file.ext:line` — what this location helps establish

## Unknowns, conflicts, and limitations

Explain unanswered questions, conflicting artifacts, unavailable shared code, dynamic behavior, and the impact on understanding.

## Repository register contributions

List the endpoint, data/state, field rule, outbound HTTP operation/usage/mapping, configuration, Dependency Observation, Failure Observation, and cross-behavior records added to `repository-register.md`. Omit categories not observed.

## Understanding gate

- [ ] The complete flow can be retold coherently.
- [ ] Main success and material decision paths were checked.
- [ ] Data, state, boundaries, outputs, and failures were checked.
- [ ] Tests, configuration, and IaC were inspected or their absence recorded.
- [ ] Repository-external internals remain qualified.
- [ ] Key evidence and unresolved questions are recorded.
- [ ] Applicable repository-register sections were updated.
- [ ] For Java, semantic tracing was completed or the degraded/unavailable investigation and its impact were recorded.
- [ ] For an API behavior, endpoint evidence layers were recorded separately and only explicitly bound external entries were attached.

Set `understanding_status: understood` only after this reasoning review passes.
