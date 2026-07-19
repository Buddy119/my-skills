# BA Pack policy

## Contents

- Purpose and evidence boundary
- Independent business-model stage
- Business modeling units
- Prevent technical-to-business relabeling
- Many-to-many traceability
- Reader document responsibilities
- Completion and review gate

## Purpose and evidence boundary

Reconstruct an independent business model from the completed repository synthesis and Tech facts. Do not translate one Tech Behavior into one BA document.

- Generate the Business Model only after repository synthesis and the related Tech documents are complete at the same commit.
- Generate the BA Pack only after the Business Model receives a semantic review and has status `complete` or `partial`.
- Describe only the repository-observable portion of a business journey. Keep upstream, downstream, historical intent, policy rationale, and remote behavior `Unknown` when this repository cannot establish them.
- Preserve `Confirmed`, `Inferred`, `Conflicting`, and `Unknown` in the Business Model; do not upgrade confidence during business modeling. In BA Reader documents, Confirmed is the unmarked baseline and only Inferred, Unknown, or Conflicting is shown beside the affected business label.
- Keep raw source citations in the Tech Pack. Use Journey and Scenario traceability links to reach supporting Tech Behaviors.

## Independent business-model stage

Create `.work/business-model.md` from the completed dossiers, repository synthesis, Tech Behaviors, API Contracts, lifecycle, dependencies, failures, and configuration effects. The Business Model is a natural-language working synthesis, not a Claim Ledger or a translated Tech catalog.

Account for every active Tech Behavior with one BA disposition:

- `scenario-support`: directly supports one or more Business Scenarios.
- `business-visible-support`: changes a business-visible result but is represented inside another Scenario rather than as a standalone Scenario.
- `no-business-visible-role`: has no supported business-visible role in this repository.
- `unknown`: available facts cannot establish its business relevance.

Do not use the Tech Behavior count as a target for Journey or Scenario count.

## Business modeling units

### Business Journey

A Journey is the repository-observable sequence through which an actor or participant pursues a business goal and reaches an outcome. It organizes one or more Scenarios into meaningful stages, handoffs, business-object changes, and visible outcomes.

- A simple repository may have one Journey containing one Scenario.
- Reuse a Scenario in several Journeys when the same supported business situation contributes to different goals.
- Do not invent stages outside the repository. Show an unknown upstream or downstream boundary when it matters.
- Use a semantic ID: `<repository>.journey.<business-goal-slug>`.

### Business Scenario

A Scenario is a discrete business situation with a supported context or trigger, actors, relevant preconditions, decisions, affected business information or objects, and visible outcomes.

- A Scenario may be supported by several Tech Behaviors.
- One Tech Behavior may support several Scenarios when its business contexts or outcomes materially differ.
- A Tech Behavior may support no Scenario.
- Use a semantic ID: `<repository>.scenario.<business-context-outcome-slug>`.

Merge technical paths into one Scenario when they achieve the same business goal under materially equivalent context, decisions, and outcomes. Split only when actor goal, business context, decision meaning, affected object lifecycle, or visible result materially differs.

## Prevent technical-to-business relabeling

- An Entry Point, Endpoint, Event, Handler, or Tech Behavior does not automatically create a Scenario.
- A technical branch becomes a business decision only when it changes a supported business condition or visible business result.
- A validation becomes a Business Rule only when its business meaning is supported. Otherwise keep it as a request-quality or information precondition.
- A technical dependency becomes an External Business Participant only when its role or unavailability changes a business interaction or result.
- A technical exception becomes a Business Exception only when it changes completion, caller-visible outcome, recovery, timing, or business-object state.
- Do not model internal retries, transformations, framework calls, mapping steps, or fully recovered technical failures as standalone business stages.
- Consume only business-visible Object States and outcomes from the typed lifecycle model. A technical Action, source, store, destination, or event emission cannot become a BA State or Journey stage without independently supported business-visible meaning. Derived States retain their `Inferred` confidence.
- Do not reproduce endpoint exposure layers, class names, methods, AWS resources, protocols, field mappings, storage identities, or Failure Pattern mechanics in BA documents.

## Many-to-many traceability

Maintain direct Scenario-to-Tech traceability:

- Each Scenario lists every directly supporting Tech Behavior.
- Each supporting Tech Behavior lists the Scenario ID and document in `ba_scenarios`.
- A Journey lists its Scenarios and the union of their supporting Tech Behaviors for navigation, but Tech Behaviors do not maintain Journey backlinks.
- Journey and Scenario IDs are independent of Tech Behavior IDs and filenames.
- `ba_scenarios: []` is valid for every Tech Behavior category.

The Business Model's Tech coverage map is the completeness control. Mechanical validators check declared links and backlinks, not whether a Behavior should have been mapped.

## Reader document responsibilities

`business-overview.md` explains capabilities, actors, important objects, Journey landscape, shared business rules, business-visible participants, outcomes, and limitations. It does not repeat Scenario details.

`business-catalog.md` contains a Journey index, a Scenario index, and a Tech coverage map.

A Journey document explains:

- Business goal and repository-observable scope.
- Actors and start/end conditions.
- Ordered stages and linked Scenarios.
- Business-object changes and handoffs.
- Business-visible exceptions, degradation, recovery constraints, and Unknown boundaries.
- Scenario links and supporting Tech Behavior links.

A Scenario document explains:

- Business purpose and context.
- Actors, business trigger, and relevant preconditions.
- An independently modeled business flow.
- Business decisions and information concepts.
- Successful, alternative, and failed visible outcomes.
- Business-visible external interactions.
- Related Journeys and supporting Tech Behaviors.

Remove optional sections that add no reader value. Do not fill simple Scenarios with empty tables.

## Completion and review gate

Set `business_model_status`:

- `complete`: all Tech Behaviors have a disposition and the observable Journey/Scenario model has been reviewed; Unknowns may remain.
- `partial`: supported Journeys and Scenarios can be published, but blocked or unreadable evidence materially limits business coverage.
- `blocked`: a safe Journey/Scenario model cannot be established; do not publish invented BA documents.
- `pending`: business modeling has not completed.

Before publication, verify:

- Journey and Scenario counts arose from business meaning rather than Tech document count.
- Every Scenario has at least one supporting Tech Behavior.
- Every Journey has at least one Scenario.
- Every active Tech Behavior has a BA disposition.
- Business rules, participants, and exceptions satisfy the evidence boundary above.
- A BA reader can retell business goals, situations, object changes, outcomes, and limitations without following the Tech call chain.
