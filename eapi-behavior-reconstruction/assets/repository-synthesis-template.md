---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
synthesis_status: "complete|partial|blocked"
coverage_status: "complete|partial|blocked"
---

# Repository synthesis

This is the internal repository mental model produced after behavior tracing. Reconcile the dossiers and register; do not concatenate them.

## Observable repository responsibility

Explain what the repository demonstrably does and distinguish supported responsibility from inferred business purpose.

## Capability and behavior model

Describe how behaviors combine into capabilities. Include a behavior-level Mermaid map when relationships materially aid understanding.

## Behavior relationships

Explain trigger chains, shared orchestration, shared rules, common components, and independently exposed behaviors.

## Business objects and data lifecycle

Describe where important objects originate, how behaviors read or change them, state transitions, external movement, and terminal or unknown states.

## Endpoint and contract model

Reconcile application routes, external entries, environment intent, and runtime observations without collapsing their evidence. Explain explicit bindings and rewrites, unmatched external entries, multiple exposures sharing one implementation, conflicts, external reachability, and which confirmed application routes receive contracts.

Classify every reconciled record as `application-endpoint`, `meaningful-external-exposure`, `protocol-support`, or `unresolved`. Record its `publish`, `summarize`, or `publish-as-exception` disposition, its classification basis, and any normalized route-group relationship. Summarize ordinary protocol support while keeping orphaned, conflicting, environment-inconsistent, and unresolved candidates visible as publication exceptions.

## Outbound HTTP operation and mapping model

Reconcile executable call sites into Remote Operations only when Method, Logical Target, and Client Operation all match. Describe shared Call IDs, their Usage IDs and related behaviors, usage-specific conditions/configuration, request and response mapping sets, aliases from merged legacy IDs, and unresolved identity or transformation conflicts. This section drives the call-centric Field Validation and Mapping document.

## Runtime configuration effects

Synthesize how configuration changes execution, outcomes, dependency selection, timing, or recovery.

## Dependency contract model

Reconcile dependency observations into logical external participants or resource boundaries. Explain the evidence used to group operations, the role each Dependency plays, dependent capabilities, operation- or behavior-level criticality, unavailability impact, fallback or degradation, state implications, and remote behavior that remains Unknown. Keep ambiguous candidates unresolved instead of merging from names, hosts, paths, or types alone.

Record the publication projection: one reader-facing Dependency section per reconciled `DEP-nnn`, with its `DEP-nnn-OPnn` operations and links to existing HTTP Call, field mapping, lifecycle, and failure knowledge rather than copied detail.

## Repository-wide failure pattern model

Reconcile failure observations into `FAIL-nnn` Patterns only when trigger/source, propagation, caller visibility, state outcome, retry safety, and recovery semantics are materially equivalent. Explain affected capabilities, recurring cross-behavior handling, behavior-specific variations, dependency relationships, error-translation inconsistencies, partial or committed state, swallowed or false-success outcomes, and recovery gaps.

Assign evidence-supported `High`, `Medium`, `Low`, or `Unknown` risk attention without inventing business severity. Record the publication projection as one reader-facing section per Pattern, not one row per observation.

## Repository connection model

Create a repository-level projection from the reconciled endpoint, Behavior, Dependency, data-lifecycle, configuration, and failure models. Include only executable boundaries or explicit trigger bindings; a name, Host, class, configuration key, or resource declaration alone is not a connection.

Group by external participant/resource, direction, boundary type, interaction role, and configuration-selection semantics. Combine multiple Operations only when that complete identity is equivalent; split one participant when it plays materially different roles.

| External participant or resource | Direction | Boundary type | Interaction role | Capabilities and Behaviors | Exchanged concepts | Config or variants | Criticality | Failure and state impact | Status or limitation | Deep-dive models |
|---|---|---|---|---|---|---|---|---|---|---|
| Participant/resource | Inbound/Outbound/Bidirectional | API/event/state/storage/identity/shared-service/schedule/other | Business request/response, Synchronous business dependency, Asynchronous handoff, State read/write, Auxiliary side effect, Identity/security support, Operational support, or Unknown | Capability and Behavior IDs | Business/data concepts | Target, implementation, environment, optional path, or None observed | Required/Degradable/Optional/Unknown/N/A | Blocking, degradation, partial state, or Unknown | Confirmed/Inferred/Conflicting/Unknown | Endpoint/Contract/Behavior/Dependency Operation/Mapping/Lifecycle/Config/Failure references |

Record how this model should be projected into one context diagram and one compact Overview matrix. Do not copy detailed child tables.

## Shared behavior model

Include only rules and components proven to affect at least two Behaviors or independently exposed entry paths and to change observable validation, decisions, authorization, transformation, state, boundaries, outputs, error handling, retry, or recovery.

### Shared rules

| Shared rule | Common semantic effect | Capabilities and Behaviors | Variations or overrides | Configuration or source of truth | Status and limitations | Deep-dive models |
|---|---|---|---|---|---|---|
| Human-readable rule | Observable shared effect | Capability and Behavior IDs | Behavior-specific difference or None observed | Executable rule/configuration source | Confirmed/Inferred/Conflicting/Unknown | Behavior/Contract/Field/Config/Failure references |

### Shared behavior-shaping components

| Component and behavior role | Capabilities and Behaviors | Observable behavior impact | Configuration or implementation variants | Change blast radius and limitations | Status | Deep-dive models |
|---|---|---|---|---|---|---|
| Role first; implementation identity second | Capability and Behavior IDs | Path/result/state/boundary/failure effect | Binding, profile, target, or None observed | Affected outcomes and Unknowns | Confirmed/Inferred/Conflicting/Unknown | Behavior/Field/Config/Lifecycle/Dependency/Failure references |

Exclude logging, ordinary monitoring, generated code, framework glue, trivial wrappers, generic serializers, and utilities that do not materially shape behavior. If no item qualifies, record `Not observed` rather than producing an inventory.

## Coverage, conflicts, and unknowns

Account for every entry point and explain blocked code, missing tests/IaC/schemas, dynamic behavior, external boundaries, and conflicting artifacts.

## Publication decisions

List applicable final Tech Pack reference documents, omitted documents and why, the Repository Overview connection/shared projections, BA-visible capabilities, and any warnings that must accompany delivery.
