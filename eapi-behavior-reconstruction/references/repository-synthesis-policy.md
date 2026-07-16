# Repository synthesis policy

## Purpose

Turn completed behavior dossiers into one repository mental model before publishing the Knowledge Pack. Synthesis identifies relationships that no single handler, method, or dossier can establish alone.

## Entry conditions

Begin after:

- Every executable entry point has a catalog disposition.
- Every active business, integration, and technical behavior is `understood` or explicitly `blocked`.
- Applicable endpoint, data, mapping, configuration, dependency, failure, and relationship observations are present in the repository register.

Do not use an inventory or evidence-index marker as a substitute for a completed dossier.

## Synthesis questions

Use the dossiers and register to answer:

1. What observable responsibility does this repository perform?
2. Which behaviors form each supported capability?
3. Which behaviors trigger, enable, or consume results from other behaviors?
4. Which business or data objects cross behavior boundaries?
5. Where do those objects originate, how do they change, and where do they leave or terminate?
6. Which state transitions form a lifecycle?
7. Which rules or components are genuinely shared across behaviors?
8. Which endpoints expose the same behavior, and which endpoint contracts differ?
9. Which configuration values alter execution, outcomes, dependencies, or recovery?
10. Which dependencies and failure modes recur across the repository?

## Reconcile rather than concatenate

- Merge behavior candidates that are implementation layers of one flow.
- Split a candidate when one entry point contains independently triggered or independently observable behaviors.
- Keep multiple endpoints distinct in the Endpoint Matrix even when they share one behavior.
- Reconcile application routes, external entries, environment intent, and runtime observations only through explicit target, binding, mapping, or rewrite evidence.
- Preserve external-only entries as independent exposure records; do not create a behavior or API contract for them.
- Keep multiple external entries under one application endpoint when explicit mappings prove they share its implementation.
- Derive external reachability only after recording each layer's own status and evidence.
- Resolve duplicate register entries and preserve conflicting evidence explicitly.
- Do not infer ordering or lifecycle edges merely because two objects have similar names.
- Do not infer a remote system's internal behavior from a client method name.

Update the working catalog, analysis state, dossiers, and register together when behavior boundaries change.

## Coverage semantics

`synthesis_status: complete` means the synthesis process is complete for the accessible repository evidence. It does not imply that every business meaning is known.

Use the final pack's `coverage_status`:

- `complete` when every discovered entry point is understood or intentionally classified and no material area is unreadable.
- `partial` when blocked, unreadable, generated, dynamic, or external areas materially limit coverage.
- `blocked` when repository-wide synthesis cannot be completed safely.

## Source of final documents

- Repository overview and BA overview come from repository synthesis.
- Behavior documents come from their dossiers, informed by synthesis.
- Endpoint Matrix, field rules, configuration, and dependency references come from reconciled register sections.
- Data lifecycle and failure taxonomy require cross-behavior synthesis.

Never generate the formal pack directly from evidence-index JSON, file-role metadata, or a batch of unreviewed structured facts.
