# BA Pack policy

## Purpose and evidence boundary

The BA Pack translates verified observable behavior from the Tech Pack into business-readable documentation. It does not reconstruct an unproven historical requirement, business intention, product promise, or policy rationale.

- Generate the BA Pack only after full-repository synthesis is complete and the related Tech documents exist at the same repository commit.
- Derive each BA behavior from its completed dossier, repository synthesis, and verified Tech Behavior; do not use a shared metadata flow as the source for both views.
- Preserve `Confirmed`, `Inferred`, `Conflicting`, and `Unknown` exactly; do not upgrade confidence during translation.
- Link to the Tech Behavior for implementation details and source evidence. Do not place raw source citations in BA documents.
- Exclude purely technical behaviors unless they materially change a business-visible outcome. Describe that relevance in the affected BA behavior instead of creating a technical BA behavior.

## Audience and language

Write for a business analyst who understands the banking domain but may not know the repository, framework, AWS service, class structure, or code terminology.

Prefer business actors, business objects, decisions, events, rules, and outcomes:

- Write “The customer update request is checked for required information” rather than “The handler validates the DTO.”
- Write “The customer record is updated” rather than “The service writes to DynamoDB.”
- Write “The external customer system is asked to update the profile” rather than “The Lambda makes a POST request.”
- Write “The request is rejected and the caller is informed” rather than naming an exception class or HTTP adapter.

Do not repeat class names, handler names, method names, AWS resource names, source paths, field-level mapping tables, retry implementation, or full API schemas. Use the linked Tech Pack for those details.

## Translation rules

Translate only what is supported:

| Technical observation | BA representation |
|---|---|
| API, handler, event, queue, or schedule trigger | A business request, business event, operational event, or timed business activity |
| Validation branch | A business precondition or rule only when its business meaning is supported; otherwise a request-quality condition |
| Database write | A business state change, when the affected business object is known |
| Outbound HTTP call | An external business interaction and the business information exchanged conceptually |
| Published message or event | A business notification or event when its meaning is known |
| Retry, dead-letter queue, or technical exception | A BA exception only when it changes timing, completion, visibility, or recovery from a business perspective |

Do not turn null checks, serialization constraints, framework behavior, or infrastructure wiring into business rules unless the business meaning is evident from code, tests, schema names, or other repository evidence.

## BA behavior contents

Each BA behavior must state:

- The business capability it supports, or `Unknown`.
- Actors or system participants and their roles.
- The business trigger and preconditions.
- An ordered business flow with decisions and visible outcomes.
- Confirmed or qualified business rules.
- Conceptual business inputs and outputs, without API schema tables.
- Successful outcomes and business-visible side effects.
- Business exceptions, including the visible effect and recovery when known.
- External business interactions, without HTTP mechanics or field-level mappings.
- Open questions and a link to the corresponding Tech Behavior.

The Mermaid flow must use actor, action, decision, affected business object, and outcome labels. Create it independently from the synthesized business model. Do not copy the Tech Mermaid, mechanically rename its nodes, or reproduce internal call chains.

## Traceability and links

- Tech Behavior path: `tech-pack/behaviors/<behavior-id>.md`.
- BA Behavior path: `ba-pack/behaviors/<behavior-id>.md`.
- From a Tech Behavior, link to `../../ba-pack/behaviors/<behavior-id>.md`.
- From a BA Behavior, link to `../../tech-pack/behaviors/<behavior-id>.md`.
- The two documents must have the same `behavior_id`, `repository`, and `source_commit`.
- BA overview and catalog entries must link to both views.
- Before delivery, compare Tech and BA Mermaid content. Identical diagrams are a defect; similar topology is acceptable only when the labels and surrounding explanation answer different audience questions.
