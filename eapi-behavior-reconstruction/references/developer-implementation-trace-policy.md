# Developer implementation trace policy

## Purpose

Give developers two peer views of every executable Behavior without turning the
Tech Pack into either a business-only flow or a repository-wide call graph.

## Two independent Behavior models

Build both models while tracing:

- **Behavior Flow** explains the trigger, result-changing decisions, supported
  alternatives, evidence-backed object-state changes, important side effects,
  and final observable results.
- **Implementation Sequence** explains runtime participants, framework dispatch,
  ordered calls and returns, persistence and external boundaries, transaction
  position, asynchronous handoff, and exception propagation.

Do not derive one model by relabeling the other. Behavior Flow must not use Java
classes or methods as its primary nodes. Implementation Sequence may contain
more technical detail, but it must remain a selective executable story rather
than a complete call graph. A dynamic or generated edge stays an explicit
Unknown boundary.

Every published Tech Behavior contains one `flowchart` under `Behavior flow`
and one `sequenceDiagram` under `Implementation sequence`. When a minimum
credible call order cannot be established, keep the Behavior blocked instead
of drawing a plausible sequence.

## Exception handling trace

Follow material failures from their origin through local catches, global advice,
framework handlers, translation, propagation, swallowing, degradation, retry,
and the caller-visible or asynchronous result. Record state and side effects at
the failure point plus observed rollback, compensation, retry, or manual
recovery. Connect the Behavior-specific trace to `FO-*`, reconciled `FAIL-*`,
Dependency, Lifecycle, and API Contract detail without copying the repository
Failure Taxonomy.

The sequence diagram shows where an exception occurs and how it propagates.
The Exception table owns detailed local handling semantics. API Contracts show
only caller-visible errors.

## Java implementation slices

For a Java repository, reconcile only production types that participate in an
executable Behavior:

- `JTYPE-*` identifies a type and its runtime role.
- `JEDGE-*` represents `calls`, `injects`, `implements`, `extends`, `creates`,
  `framework-dispatch`, or `generated-delegate`.
- `JIMPL-*` binds Endpoint or trigger → Behavior → exact entry symbol → types
  and edges → runtime selection evidence.

Use the Java semantic-analysis policy. A symbol relationship and a runtime DI
selection are separate facts. Multiple implementations without binding evidence
remain candidates. Shared types are defined once. Tests are evidence, not
production nodes. AOP, reflection, generated repositories/mappers, and
framework callbacks remain explicit dynamic boundaries.

Publish `java-implementation-map.md` only for Java repositories with reconciled
implementation records. Do not inventory unrelated classes.

## Configuration-to-Endpoint impacts

Separate:

- `CFG-OBS-*`: a read or wiring observation and its executable effect.
- `CFG-*`: a reconciled logical configuration identity.
- `CFG-*-I*`: a specific impact on a Behavior and, when applicable, Endpoint.

An Endpoint relationship requires a proven configuration read/wiring, a
concrete executable Behavior effect, and an established Behavior/Endpoint
relationship. A similar configuration name and route is never enough.

Use these impact types exactly:

`application availability`, `authentication/authorization`, `validation`,
`branch/variant`, `implementation selection`, `dependency target`,
`timeout/retry/recovery`, `output/status`, `state/side effect`, or `other`.

Runtime Config owns application execution differences and its Endpoint reverse
index. Endpoint Matrix owns exposure, environment intent, observed deployment,
and external reachability. Neither document may promote the other model's
evidence.

## API Contract boundary

API Contracts remain caller-first. They do not contain internal participant,
class, method, database, downstream-client, or exception-propagation sequences.
Link each Contract directly to the related Behavior's
`#implementation-sequence`.

An API Contract may contain a separate Protocol Sequence only when the caller
must perform a supported multi-call protocol such as polling after `202`,
callback acknowledgement, challenge/response, or another explicit externally
observable interaction. That diagram contains caller-visible exchanges only.
