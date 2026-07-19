# Reader priority and progressive-disclosure policy

## Purpose

Keep complete repository knowledge without forcing every reader through the complete model. Working Artifacts preserve all facts, statuses, schemas, relationships, and evidence. Reader Artifacts prioritize the questions a developer must answer before choosing a deep-dive document.

## Three reading layers

1. Repository orientation: responsibility, Capability paths, behavior-changing Variants, and highest-attention risks.
2. Behavior and endpoint use: one executable Behavior story and one caller-visible API Contract.
3. Specialist reference: Lifecycle, Mapping, Runtime Config, Dependency, Failure, Endpoint exposure, and full Schema detail.

Do not copy a lower-layer table into an upper layer merely to make the upper document look complete. Link to it once with enough context for the reader to decide whether to follow the link.

## Capability paths

Build Capability paths from completed dossiers and Repository Synthesis, not by iterating the Behavior Catalog. One Capability may use several Behaviors; one Behavior may support several Capabilities.

For each Capability explain the observable goal, supported trigger, principal decisions, normal result, state or side-effect outcome, and relevant deep links. Use one small diagram only when it makes the path easier to retell. Do not present a class or service call chain as the Capability path.

Call a path normal, default, or primary only when executable selection, configuration, or tests establish that choice. When several supported paths exist and the repository does not prove a default, present them as alternatives.

## Behavior-changing Variants

Use a general Variant model for Market, Country, Tenant, Channel, Profile, Environment, Feature Flag, or another supported selection axis. A name or configuration value alone is not a Variant.

Include a Variant only when it changes a rule, validation, Dependency, Mapping, state transition, output, error, retry, recovery, or other observable path. Record the selection source, scope, baseline or lack of a proven default, alternative behavior, affected Capabilities/Behaviors, and the appropriate Runtime Config or specialist links.

## Risk hotspots

Reuse Failure risk attention, Dependency criticality, and Lifecycle consistency conclusions. Promote only supported High attention and materially Unknown partial-state, false-success, unsafe-retry, caller-visibility, or recovery concerns. Do not create a second risk score or repeat the full Failure Pattern index.

## Behavior publication

Lead with Summary, Main Path, and a retellable Behavior Flow. Put material Variants and risks next. Keep input details, rules, Actions, Transitions, HTTP Calls, Dependencies, Failures, and outputs under Implementation Reference and omit inapplicable subsections.

API caller fields belong in the endpoint Contract. A Behavior may explain why a field changes an internal path, but it must not copy caller field tables.

## API field layering

Request and Responses lead with required, conditionally required, and behaviorally significant fields. When the observed Schema is large, place remaining fields in `Complete field reference` after outcomes and limitations.

The caller-first and complete-reference sections are disjoint. Together they describe the observed field surface. Label Schema-only, shared/opaque, and conflicting bases without implying runtime enforcement. Omit the complete-reference section for a small Contract.

## Review boundary

Mechanical validation may require the orientation sections, their order, registered field-reference headers, and non-duplicated field identities. It must not use word counts, table-row counts, Schema-field counts, Capability counts, or risk counts as a quality proxy.

Reader Review decides whether the selected Capability paths, Variants, risks, and core API fields are useful and factually prioritized. A structurally valid priority section with unhelpful prose is not a completed Reader Review.
