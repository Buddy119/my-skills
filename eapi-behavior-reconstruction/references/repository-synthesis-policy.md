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
14. Which external-boundary observations belong to the same logical Dependency, what role does it play, which Operations and capabilities share it, and how does unavailability affect each usage?
15. Which failure observations share materially equivalent trigger, propagation, visibility, state, retry, and recovery semantics, and which represent distinct repository-wide Patterns?
16. Which dependency and failure conclusions are High-attention or materially Unknown, and what repository evidence supports that reader priority?
17. Which reconciled Operations form one reader-meaningful logical connection, and where do direction, boundary, interaction role, or configuration selection require separate connections for the same participant?
18. Which shared rules and behavior-shaping components materially affect at least two Behaviors or independent entry paths, where do their effects differ, and what would change if their source changed?

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
- Reconcile Dependency Observations into one Dependency only when code, configuration, DI/wiring, resource definitions, or explicit operation bindings establish the same logical external participant or resource boundary. Keep distinct Operations beneath one Dependency and keep ambiguous candidates unresolved; names, hosts, paths, and resource types alone are not grouping evidence.
- Reconcile Failure Observations into one Pattern only when trigger/source, handling/propagation, caller visibility, state outcome, retry safety, and recovery are materially equivalent. Do not group from exception names, error codes, statuses, or text alone.
- Assign every Dependency and Failure Observation to a reconciled object or mark it `Unresolved`; do not discard observations that do not fit a clean reader model.
- Preserve operation- or behavior-level Dependency criticality when one Dependency is Required for one capability but Degradable, Optional, or Unknown for another.
- Use Failure risk attention to prioritize reading, not to manufacture a business risk score. Keep decisive missing state, retry, or recovery evidence as `Unknown`.
- Reconcile repository connections from executable boundaries and explicit trigger bindings after Endpoint, Dependency, Lifecycle, Config, and Failure reconciliation. Group only when participant/resource, direction, boundary type, interaction role, and configuration-selection semantics match. Split one participant when it plays materially different roles or directions.
- Do not create a connection from a host, resource, class, client, configuration, or participant name alone. Preserve missing role, exchanged-concept, target-selection, availability, or state-impact evidence as `Unknown` rather than filling the Overview with name associations.
- Reconcile a Shared Rule or Shared Behavior-shaping Component only when one proven rule source, implementation, or configuration binding affects at least two Behaviors or independent entry paths and changes observable validation, decisions, authorization, transformation, state, boundaries, output, error handling, or recovery. Similar names are not shared identity evidence.
- Exclude logging, ordinary monitoring, generated code, framework glue, simple wrappers, behavior-neutral utilities, and single-Behavior helpers from the Shared Behavior model.
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

- Repository Overview comes from the synthesized Repository Connection and Shared Behavior models. The independent Business Model uses repository synthesis and the completed Tech facts to reconstruct business-visible Capabilities, Journeys, Scenarios, actors, objects, rules, outcomes, and limitations before any BA document is published.
- Behavior documents come from their dossiers, informed by synthesis.
- Endpoint Matrix comes from the register's reconciled publication projection: application endpoints, meaningful external exposures, exceptions, and a compact protocol-support summary. The outbound part of Field Validation and Mapping comes from reconciled Remote Operations, Executable Usages, and Field Mappings rather than the raw observation shape. Other field rules, configuration, and dependency references come from their reconciled register sections.
- External Dependency Contracts come from reconciled `DEP-nnn` participants/resources and their `DEP-nnn-OPnn` Operations, not the Dependency Observation rows.
- Failure Taxonomy comes from reconciled `FAIL-nnn` Patterns and cross-pattern risk analysis, not the Failure Observation rows.
- Data lifecycle, Dependency Contracts, and Failure Taxonomy require cross-behavior synthesis even when a resulting Pattern or Dependency is observed in only one Behavior.

Never generate the formal pack directly from evidence-index JSON, file-role metadata, or a batch of unreviewed structured facts.

Never derive the BA Pack by iterating the Tech Behavior catalog. Tech Behaviors are supporting evidence inputs; they are not the BA document identity or cardinality model.
