# Lifecycle model policy

## Purpose

Model object condition, repository processing, and data movement as related but distinct facts. A coherent execution sequence is not automatically an object lifecycle.

## Three typed models

### Object State Model

A State describes a condition of one `OBJ-*` object or resource that can be defined before and after processing.

- `Explicit`: a declared field, enum, status value, or state resource.
- `Observable`: existence, deletion, durable record condition, or another directly observable object condition.
- `Derived`: an executable predicate or combination of facts. Always publish it as `Inferred` and record the derivation.

Do not use a source location, store, destination, system name, method, or action as a State. Pipeline execution can be a State only when the modeled object is itself a persisted or observable Job/Workflow.

### Processing Model

Use `ACT-*` records for Read, Observe, Validate, Transform, Map, Persist, Delete, Invoke, Emit, Route, and Other processing. Persist and Delete may cause a State Transition, but the action is not itself the resulting State. Emit does not change the source object's State unless separate evidence proves that change.

### Data Movement Model

Describe origin, store, repository boundary, representation, destination, and handoff. Movement between locations is not a State Transition. An event may be modeled as its own object, while emitting it remains an Action.

## Observation and reconciliation

Add raw executable observations as `LIFE-OBS-*` while tracing. During synthesis:

1. Reconcile object/resource identity into `OBJ-*`.
2. Define supported `STATE-*` conditions with basis, observability, status, and evidence.
3. Reconcile executable processing into `ACT-*`.
4. Create `TRANS-*` only when From and To conditions belong to the same Object and the executable change point is supported.
5. Map every Observation to typed records or retain it as `Unresolved`.

Call order, neighboring methods, names, comments, source/destination similarity, and Mermaid layout never prove a Transition. Unknown or Conflicting candidates remain outside the established diagram.

## Reader projection

Organize `data-lifecycle.md` by Object. Use:

- `stateDiagram-v2` only for registered States and Confirmed/Inferred Transitions.
- `flowchart` for Actions, resources, and boundaries.
- The exact no-transition sentence from the lifecycle schema when an Object has processing or movement but no established Transition.

Keep the `lifecycle-state-diagram` and `lifecycle-processing-diagram` tags. In a State Diagram, declare each State using its stable ID and label every edge with its `TRANS-*` ID plus status. In a Processing Diagram, use `ACT-*` identities for action nodes and never present `STATE-*` as processing steps.

The mechanical Validator checks declared types, references, and diagram projection. AI remains responsible for deciding whether a State definition and Transition meaning are supported by code.

## BA boundary

Only business-visible object conditions and outcomes may shape BA object progression. Technical Actions, stores, endpoints, retries, transformations, and emitted messages do not become business States or Journey stages unless their business-visible meaning is independently supported. Keep working traceability to the typed lifecycle model without exposing technical IDs in BA prose.
