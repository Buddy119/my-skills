# External dependency synthesis policy

## Purpose and boundary

Turn executable boundary observations into a reader model of the external participants and resources on which the repository depends. Keep raw observations in the repository register and publish one contract per reconciled logical Dependency.

Include an item only when executable behavior crosses the repository or process boundary to a service, database, event resource, storage resource, runtime-provided component, or other externally controlled resource. Do not list every ordinary in-process library. Include an opaque shared library or generated client only when its unavailable implementation materially limits the observed boundary contract.

## Three-level working model

Maintain:

1. `DEP-OBS-nnn` Dependency Observations: one evidence-bearing invocation, resource access, event interaction, availability branch, or externally provided behavior.
2. `DEP-nnn` Dependency Contracts: one logical external participant or resource boundary.
3. `DEP-nnn-OPnn` Dependency Operations: distinct calls, events, resources, or operations beneath the Dependency.

Assign every Observation to one Dependency or mark it `Unresolved`. Preserve the earliest stable ID when reconciliation merges existing candidates and record retired IDs as aliases.

## Dependency identity and grouping

Merge observations only when executable code, configuration, DI/wiring, resource definitions, or an explicit operation binding establishes the same logical external participant or resource boundary.

- Keep several HTTP calls, resource operations, tables, events, or topics as distinct Operations beneath one Dependency when their common boundary is proven.
- Keep the same logical Dependency across environment-specific target values when one configuration identity selects those values.
- Keep candidates separate when identity, ownership, client contract, or binding remains ambiguous.
- Do not merge from a shared name, host, URL fragment, resource type, schema shape, or field name alone.
- Do not infer the remote system's internal workflow, persistence, SLA, authentication enforcement, retry, idempotency, or error behavior from a local client name.

For an outbound HTTP operation, link the Dependency Operation to its existing `HTTP-nnn` Call ID and Field Pack anchor. Do not duplicate Method/Target identity, Usage rows, or request/response mappings. For database, event, storage, or other boundaries, retain the stable resource or operation identity available in the repository.

## Role, exchanged concepts, and impact

For each Dependency, synthesize:

- The role observable at this repository boundary.
- The capabilities and behaviors that share it.
- Its Operations and the concepts sent, consumed, read, written, or affected.
- Invocation conditions and behavior-changing configuration.
- What the repository does when the Dependency is unavailable.
- Alternative paths, degradation, partial success, state inconsistency, compensation, and recovery only when observed.
- Local assumptions and remote behavior that remains `Unknown` or `Conflicting`.

Classify criticality at Operation or Behavior usage level:

- `Required`: the required outcome cannot complete when the Dependency is unavailable.
- `Degradable`: processing can complete with a reduced, delayed, queued, or partial result.
- `Optional`: an optional branch is skipped without changing the required outcome.
- `Unknown`: repository evidence cannot establish the consequence.

When usages differ, preserve every classification. In the landscape, show the highest supported classification and call out mixed or Unknown usages; never hide a known limitation behind one overall label.

## Reader publication

Publish `external-dependency-contracts.md` from reconciled Dependency Contracts, not directly from observations.

- Use one landscape row and one anchored detail section per `DEP-nnn`.
- State Call, target, resource, and Dependency identity once.
- Nest Operations beneath their Dependency and link deeper field, lifecycle, configuration, failure, and behavior documents.
- Use natural-language role and impact explanations before source notes.
- Keep evidence compact in grouped Source Notes under the Dependency section; do not reproduce the observation table, a generic Status column, or repeated Confirmed labels. Put any Inferred, Unknown, or Conflicting qualifier beside the Dependency or Operation identity.
- Omit the document when no executable external boundary is observed and record `Not observed` in Repository Overview.

Project Dependency Operations into Repository Overview only through the synthesized Repository Connection model. Combine same-role Operations into one logical connection when direction, boundary, interaction role, and configuration-selection semantics match; split materially different roles. The Overview links back to the Dependency Contract and does not redefine or copy its Operation inventory.

## Completion and review gate

Before publication, confirm:

- Every Dependency Observation is assigned or explicitly unresolved.
- Every Operation belongs to an existing Dependency.
- Grouping has binding evidence beyond name or target similarity.
- All affected Behaviors and capabilities are represented without repeating one Dependency per Behavior.
- Criticality and availability consequences are evidence-supported or `Unknown`.
- Remote internals and guarantees remain qualified.
- Field mappings and failure patterns are linked rather than copied.
