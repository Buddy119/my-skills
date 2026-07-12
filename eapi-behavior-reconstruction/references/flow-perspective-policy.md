# Tech and BA perspective separation policy

## Non-negotiable separation

Never render Tech Behavior and BA Behavior from one shared flow, caption, node list, or generic behavior-view object. Create two independent flow models before rendering either document:

- `.work/flow-models/<behavior-id>.tech-flow.json`
- `.work/flow-models/<behavior-id>.ba-flow.json`

The Tech model answers **how the implementation executes**. The BA model answers **what business event, decision, action, outcome, and exception a participant experiences**.

Do not create the BA model by copying the Tech nodes and replacing implementation nouns. Derive it separately from confirmed or qualified business facts: actors, capability, business information, business rules, state meaning, outcomes, and visible exceptions.

If temporary generation code is used, its data model and renderers must preserve this separation:

- Store the Tech diagram caption, nodes, and edges only in the Tech model; store the BA diagram caption, nodes, and edges only in the BA model.
- The Tech renderer may load only `*.tech-flow.json`; the BA renderer may load only `*.ba-flow.json`.
- Do not implement a fallback from a missing BA model to `meta["flow"]`, the Tech model, or the rendered Tech Mermaid.
- Do not pass one `meta` object containing generic summary or flow fields to both renderers.
- Fail generation when a required perspective model is missing. A shorter BA flow containing an explicit `Unknown` is valid; silently reusing Tech content is not.
- Keep each model at the canonical `.work/flow-models/<behavior-id>.(tech|ba)-flow.json` path. Manifest, document frontmatter, and resolved file path must agree; never load a model outside the pack.

## Tech view model

Build the Tech model directly from executable and configuration evidence. Its diagram caption and nodes may describe trigger adapters, parsing, authorization, validation implementation, orchestration, data reads/writes, state mutation, dependency calls, event publication, response mapping, exceptions, retries, compensation, and partial success.

Each Tech node must have a `T`-prefixed node ID, technical semantic type, implementation-focused label, and source evidence. The Mermaid diagram must render the Tech model's node labels rather than a separate ad hoc flow.

Bind the Tech diagram caption and every node to passing Claim IDs. A node's raw evidence ranges must belong to its bound Claims; flow metadata cannot establish a new fact.

Bind every Tech edge to passing Claim IDs that establish the rendered order or branch. Source-code line order may support a narrowly stated execution-order claim, but two individually valid node claims do not by themselves prove their relationship.

The rendered Mermaid must exactly match every model edge's source, target, and condition—not merely the edge count.

## BA view model

Build the BA model only for business or integration behaviors. Its diagram caption and nodes describe business actors or participants, business events, preconditions, decisions, actions, business state changes, outcomes, business-visible exceptions, recovery, and external business participants.

Each BA node must have a `B`-prefixed node ID, business semantic type, business-language label, and evidence status. Do not put source citations, class/method names, AWS resources, protocols, status codes, database operations, retry mechanisms, or exception types in the BA model or Mermaid flow.

Bind the BA diagram caption and every node to passing Claim IDs. Never strengthen the status of a source Claim during BA projection.

Bind every BA edge to a passing relationship Claim. An edge asserts sequence, causality, or dependency and must not be inferred from the mere existence of two business facts. Unknown-only nodes remain disconnected unless a separate passing claim proves their relationship. A single Unknown node is valid when no business sequence can be established.

When business meaning is unavailable, use fewer BA nodes and label the meaning `Unknown`. Never fill the gap by mirroring the Tech flow.

## Summary separation

Treat flow captions and document summaries as different artifacts. Keep `diagram_caption` and `diagram_claim_ids` inside each flow model. Write Tech and BA document summaries independently during editorial synthesis from their respective passing fact sets.

- Tech summary: implementation responsibility and observable execution.
- BA summary: business trigger, business action/decision, and visible outcome.

Do not copy one summary into the other or produce the BA summary by deleting component names. Shared domain vocabulary or moderate lexical similarity is acceptable when each summary answers its own reader question.

## Final semantic comparison

Before delivery, compare the linked Tech and BA documents and models:

- Reject identical Mermaid source, identical normalized node labels, or identical node sets.
- Warn on near-identical node wording and use semantic review to decide whether it indicates mechanical rewriting.
- Reject byte-identical or directly reused summaries; warn on near similarity for human review.
- Warn on technical terminology in the BA narrative; reject raw source citations, secrets, customer data, or a technical flow presented as a BA flow.
- Require implementation semantics in the Tech flow.
- Prefer more than one BA semantic category when evidence supports it; allow one concise Unknown or single supported business concept when evidence is sparse.
- Warn when BA preserves the full Tech node/edge structure with high lexical overlap or becomes more implementation-detailed than Tech.

After the deterministic validator passes, perform an explicit semantic review of every pair. Read both diagrams side by side and answer these two different questions: “Can a developer follow the implementation execution?” and “Can a BA explain the business event, decision, and visible outcome without discussing implementation?” If either answer is no—or the BA diagram is recognizably the Tech diagram with renamed nouns—rewrite the relevant model and rerun validation. Do not treat validator success alone as perspective-quality approval.

Validator success means structural and semantic separation checks passed; it does not prove that unknown business intent was recovered.
