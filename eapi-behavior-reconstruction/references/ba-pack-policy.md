# BA Pack policy

## Purpose and evidence boundary

The BA Pack translates verified observable behavior from the Tech Pack into business-readable documentation. It does not reconstruct an unproven historical requirement, business intention, product promise, or policy rationale.

- Generate a BA behavior only from a validated Tech Behavior at the same repository commit.
- Build an independent BA flow/summary model under `.work/flow-models/`; never reuse or mechanically rename the Tech model's summary, nodes, or edges.
- Give every BA edge passing relationship `claim_ids`; do not connect individually valid or Unknown nodes unless evidence establishes their sequence or causality.
- Preserve `Confirmed`, `Inferred`, `Conflicting`, and `Unknown` exactly; do not upgrade confidence during translation.
- Bind every BA fact to passing Claim IDs; a BA status must never be stronger than its source claims.
- Link to the Tech Behavior for implementation details and source evidence. Do not place raw source citations in BA documents.
- Exclude purely technical behaviors unless they materially change a business-visible outcome. Describe that relevance in the affected BA behavior instead of creating a technical BA behavior.

## Audience and language

Write for a business analyst who understands the banking domain but may not know the repository, framework, AWS service, class structure, or code terminology.

Prefer business actors, business objects, decisions, events, rules, and outcomes only when those meanings are supported:

- Write “The customer update request is checked for required information” rather than “The handler validates the DTO.”
- Write “The customer record is updated” only when persistence and the business object are proven; otherwise keep the business outcome `Unknown`.
- Write “The external customer system is asked to update the profile” only when the participant and purpose are supported; an opaque call alone is insufficient.
- Write “The request is rejected and the caller is informed” only when the visible result is observable; a thrown exception alone is insufficient.

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

Do not invent actors, recipients, owners, purpose, completed outcomes, or business rules from injected collaborator names, method names, status literals, or message construction. When only implementation activity is known, omit it from BA flow or record the business meaning as an audited `Unknown` claim.

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

The Mermaid flow must use actor, action, decision, and outcome labels. Do not reproduce internal call chains.

Before delivery, run the Tech/BA flow-separation validator. Identical or near-identical summaries, Mermaid nodes, or reused model files are validation errors, not acceptable documentation variants.

## Repository-wide BA views

Derive these views from validated Tech Pack records at the same commit:

- `capability-map.md`: capabilities, actors, behaviors, outcomes, and external participants.
- `business-data-lifecycle.md`: where business information originates, how its business state changes, and where it is used or sent.
- `business-rule-catalog.md`: business-meaningful rules derived from validated field and behavior rules; exclude purely technical validation.
- `business-exception-catalog.md`: business-visible subset of the global failure taxonomy.

Do not copy endpoint schemas, field paths, configuration keys, exception classes, or source citations into these views. Link to the canonical Tech Pack documents.

## Traceability and links

- Tech Behavior path: `tech-pack/behaviors/<behavior-id>.md`.
- BA Behavior path: `ba-pack/behaviors/<behavior-id>.md`.
- From a Tech Behavior, link to `../../ba-pack/behaviors/<behavior-id>.md`.
- From a BA Behavior, link to `../../tech-pack/behaviors/<behavior-id>.md`.
- The two documents must have the same `behavior_id`, `repository`, and `source_commit`.
- BA overview and catalog entries must link to both views.
