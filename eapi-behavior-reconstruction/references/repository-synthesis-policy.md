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
11. Which endpoint observations are application behavior, meaningful external exposure, protocol support, or unresolved?
12. Which endpoint records belong in the reader-facing Matrix, which belong in its protocol-support summary, and which must be published as exceptions?
13. Which outbound HTTP usages represent the same remote operation, and which usage-specific conditions or mappings must remain distinct?

## Reconcile rather than concatenate

- Merge behavior candidates that are implementation layers of one flow.
- Split a candidate when one entry point contains independently triggered or independently observable behaviors.
- Keep multiple endpoints distinct in the Endpoint Matrix even when they share one behavior.
- Reconcile application routes, external entries, environment intent, and runtime observations only through explicit target, binding, mapping, or rewrite evidence.
- Preserve external-only entries as independent register records, then classify their operation role before deciding how they appear in the reader-facing Matrix. Do not create a behavior or API contract for them.
- Keep multiple external entries under one application endpoint when explicit mappings prove they share its implementation.
- Associate one protocol-support declaration with a normalized route group when it supports several application methods on the same path; do not duplicate it under every method.
- Summarize ordinary protocol-support records while preserving their complete evidence in the register. Publish orphaned, conflicting, environment-inconsistent, and unresolved support candidates as individual exceptions.
- Do not suppress a record solely because its method is OPTIONS or its integration is mock/static. Confirm the absence of application behavior, business payload, state access, and business dependency calls first.
- Derive external reachability only after recording each layer's own status and evidence.
- Reconcile outbound HTTP usages into one Call ID only when Method, Logical Target, and Client Operation all match. Keep every executable call site as a Usage and preserve usage-specific mappings; do not concatenate flat mapping rows into a call model.
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
- Endpoint Matrix comes from the register's reconciled publication projection: application endpoints, meaningful external exposures, exceptions, and a compact protocol-support summary. The outbound part of Field Validation and Mapping comes from reconciled Remote Operations, Executable Usages, and Field Mappings rather than the raw observation shape. Other field rules, configuration, and dependency references come from their reconciled register sections.
- Data lifecycle and failure taxonomy require cross-behavior synthesis.

Never generate the formal pack directly from evidence-index JSON, file-role metadata, or a batch of unreviewed structured facts.
