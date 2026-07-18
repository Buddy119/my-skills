# Repository mental-model publication policy

## Purpose and sources

Turn the completed repository synthesis into a developer-facing orientation map. `repository-overview.md` must help a reader understand the repository's position, meaningful connections, and shared behavior-shaping mechanisms before opening deeper documents.

Build the view from completed dossiers plus reconciled Endpoint, Dependency, HTTP Operation, Data Lifecycle, Runtime Config, Failure Pattern, and cross-behavior models. Do not build it from Evidence Index markers, filenames, dependency names, hosts, configuration keys, or raw register rows.

## Repository connection model

Represent a logical connection by the tuple:

`external participant/resource + direction + boundary type + interaction role + configuration-selection semantics`

Use `Inbound`, `Outbound`, or `Bidirectional`. Use a repository-appropriate boundary type such as API, event/queue/stream, state resource, object/file storage, identity/key/security boundary, shared runtime service, schedule, or other observed boundary.

Classify the interaction role as one of:

- Business request/response.
- Synchronous business dependency.
- Asynchronous handoff.
- State read/write.
- Auxiliary side effect.
- Identity/security support.
- Operational support.
- Unknown.

Group several Operations into one connection when the full tuple is the same. Split the same participant when direction, role, or configuration-selection semantics differ materially. Link the grouped Operations; do not repeat their mappings or contracts.

For each connection retain:

- Supported capabilities and Behaviors.
- Business or data concepts exchanged.
- Runtime configuration that selects a target, implementation, environment variant, or optional path.
- Dependency criticality and the observed unavailability, degradation, or partial-state consequence.
- Status, conflicts, and Unknowns.
- Applicable Endpoint, Contract, Behavior, Dependency Operation, Field Mapping, Data Lifecycle, Runtime Config, and Failure Pattern links.

Use `Required`, `Degradable`, `Optional`, or `Unknown` for dependency criticality. Use `N/A` for a pure inbound trigger that is not a dependency of repository execution. Do not promote a configuration-only name, repository class, host, resource declaration, or remote-system mention into a connection without an executable boundary or explicit trigger binding.

## Context diagram and matrix

Place the repository at the center of one small Mermaid context diagram. Group only applicable nodes into Upstream, Synchronous Dependencies, State Resources, and Async Outputs/Side Effects. Use the actual control/data direction. Label each edge with the primary exchanged concept and interaction role.

Use solid edges for `Confirmed` connections. Use dashed edges for `Inferred`, `Unknown`, or `Conflicting` connections and explain the limitation in the matrix. Draw one edge per logical connection, not per call, field mapping, table operation, or Behavior.

Follow the diagram with one compact connection matrix. The matrix is an orientation and navigation surface: summarize role, capabilities, concepts, configuration, criticality, and failure/state impact, then link to detail. Do not copy Operation, Mapping, Lifecycle, Config, or Failure tables.

## Shared behavior model

Include a Shared Rule or Shared Behavior-shaping Component only when:

1. The same proven rule source, executable component, or configuration binding affects at least two Behaviors or independently exposed entry paths.
2. It materially changes validation, authorization, decisions, transformation, state, boundary interaction, output, error translation, retry, or recovery.

Separate Shared Rules from Shared Components. For a rule, explain its common semantic effect, applicability, variations, overrides, and source of truth. For a component, lead with its behavior role, then give the implementation identity, affected paths, configuration variants, change blast radius, and limitations.

Exclude ordinary logging, monitoring, generated code, framework glue, trivial wrappers, generic serializers, and utilities with no material behavior effect. Similar names or code shapes do not prove sharing. Preserve behavior-specific differences instead of publishing a false universal rule.

Link every shared item to the affected Tech Behaviors and applicable Contract, Field, Config, Lifecycle, Dependency, or Failure detail. Do not create a new repository-level document or copy the underlying detailed tables into the Overview.

## BA projection and review

Contribute only business-visible participants, interactions, shared business rules, incomplete outcomes, and recovery constraints to the independent Business Model. The Business Model—not this technical projection—decides Journey and Scenario boundaries. Do not copy the technical context diagram, connection matrix, class/module identity, or technical component table into the BA Pack.

Before publication, verify that a reader can answer direction, boundary type, interaction role, affected capabilities, exchanged concepts, configuration selection, criticality, failure impact, and the correct deep-dive destination. Reject a name-only connection list and a shared-component inventory that does not explain behavior impact.
