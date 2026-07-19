# Editorial and review policy

## Purpose

Publish evidence-grounded documentation that people can read and retell. Evidence constrains the explanation; it does not determine the prose format.

## Write from understanding

- Start with what the behavior or repository does, then explain how it reaches that result.
- Organize around trigger, decisions, state changes, boundaries, outcomes, and failures.
- Use paragraphs for connected explanation and tables for exact repeated fields or mappings.
- Cite a paragraph, rule, flow explanation, or table row at the level that supports it. Do not convert every sentence into a status-bearing claim.
- Keep `Confirmed`, `Inferred`, `Conflicting`, and `Unknown` for material conclusions and uncertainties.
- Remove unused optional sections instead of filling them with template language.

## Tech and BA views

Write each Tech Behavior from its dossier and repository synthesis. Include implementation structure only when it helps a developer follow the executable path.

Build the BA view from the independent Business Model, not from a Tech Behavior loop:

- Organize business goals as Journeys and discrete business situations as Scenarios.
- Use independent Journey/Scenario IDs and many-to-many Scenario/Tech traceability.
- Use actors, business context, decisions, business objects, handoffs, outcomes, and business-visible exceptions.
- Do not reuse Tech flow data, mechanically rename Tech Mermaid nodes, or use Tech document count as a BA document target.
- Do not expose class names, AWS resource identifiers, source paths, field tables, dependency operations, or failure mechanics.
- Preserve uncertainty and link each Scenario to all supporting Tech Behaviors.

## Three review passes

These passes produce three distinct trust conclusions. Mechanical success does not imply factual correctness or reader value. Record the sampled objects, questions, conclusions, findings, corrections, and evidence through the Finalization Review protocol; do not complete a pass using only a Checkpoint status or a zero-error Validator report.

### Mechanical review

Run the generic Markdown structure Validator across every formal Tech and BA Markdown document before Artifact/frontmatter, specialized document, or cross-link validation. It checks Frontmatter boundaries, one H1, heading order, closed code fences, unique explicit and generated anchors, and structurally valid pipe tables while ignoring fenced content and honoring escaped or inline-code pipes.

When one document is structurally invalid, report that root cause and mark its specialized checks `SKIPPED`. Do not interpret a malformed table as an empty field, Endpoint, Dependency, Failure, Journey, or Scenario index. Continue independent documents and domains, but do not claim complete mechanical validation while a necessary group is skipped.

After structure is trustworthy, use scripts for Artifact identity, state transitions, endpoint identity, links, commit consistency, JSON examples, citation bounds, and placeholders. For every local Markdown `#fragment`, require an exact explicit-anchor match or a supported GFM heading slug after URL decoding. Check same-document links as well as cross-document links. Prefer explicit anchors for long-lived domain IDs and use heading fragments only for simple stable headings; do not use case-insensitive or fuzzy matching. Fix mechanical errors without changing prose that is already accurate and readable. Do not repair a Candidate by modifying a Skill Validator or relaxing the Markdown contract during an analysis run.

### Fact review

Sample at least these high-risk facts back to source when present:

- A core rule and its failure outcome.
- An Object State definition, including its Explicit, Observable, or Derived basis.
- A State Transition, including same-Object From/To conditions, causing Action, observable or persisted result, and evidence.
- A Processing Action that correctly remains outside the Object State model.
- An outbound HTTP operation, one executable usage, and one mapping that proves both field boundaries.
- A configuration-dependent branch.
- A retry, partial-success, or dependency-failure path.
- For Java, a critical caller/callee edge and any interface-to-implementation selection that affects behavior.
- For API evidence, one application route, its external-entry correlation if any, and the resulting reachability assessment.
- For an aggregated protocol-support group, one representative declaration and its classification basis; prioritize any orphaned or conflicting exception.
- One synthesized Dependency, an Operation beneath it, the evidence that proves their shared identity, and one Required/Degradable/Optional/Unknown availability consequence.
- One Failure Pattern, including its source, propagation, caller visibility, state outcome, retry/recovery semantics, and the evidence supporting its risk-attention label.
- One Repository Overview connection, including its executable or trigger boundary, direction, interaction role, exchanged concept, configuration selection when present, availability/state impact, and deep links.
- One Shared Rule or Shared Behavior-shaping Component across two affected Behavior paths, including any difference, override, or unresolved scope.
- One Business Scenario supported by one or more Tech Behaviors, including the evidence that its business context, decision meaning, and outcomes are not merely renamed technical nodes.
- One Tech Behavior with `business-visible-support`, `no-business-visible-role`, or `unknown` disposition, confirming that the Business Model did not force a Scenario.

For each sampled item, verify that the cited code proves the meaning expressed, not merely that the named file exists.

For sampled Java call relationships, verify the exact signatures rather than names alone, distinguish production callers from tests, and inspect the relevant constructor/injection point plus `@Bean`, `@Qualifier`, `@Primary`, `@Profile`, or component-scan evidence. If runtime binding remains ambiguous, ensure the document says so. Do not publish raw language-server operation logs; retain only limitations that affect the reader's understanding or the confidence of a conclusion.

For sampled endpoints, verify that each layer cites evidence of that layer, correlation uses an explicit target/mapping/binding, and the prose does not call an application route public, deployed, or reachable when only static evidence exists. For a summarized protocol-support item, also verify that no executable handler, business payload, state access, or business dependency call was overlooked. A method name or mock integration is not sufficient classification evidence.

### Reader review

Read the document without using source code and ask:

- Can a developer retell the complete success and material failure paths?
- Can a BA identify the business trigger, decisions, affected object, outcome, and exceptions?
- Can either reader find deeper contract, lifecycle, mapping, configuration, dependency, or failure detail with one link?
- Does the document contain repetitive status phrases, empty tables, template instructions, or validator-oriented wording?

Treat execution lifecycle and reader semantics as separate layers. Reader artifacts must describe the current published Generation, never a future Skill step. Reject explicit residue such as `forward reference`, `N/A until publication`, a planned Artifact path, or a statement that a later stage will generate or materialize a document. Review bare `planned`, `pending`, `not yet`, `temporary`, `future`, and `later` in context: rewrite them when they describe the documentation workflow, but retain them when evidence shows a real business, configuration, or runtime state. The publication-maturity Validator identifies candidates; AI performs the contextual decision.

Treat cross-stage Reader Projection as a separate completeness check. After Contracts, Journeys, or Scenarios are materialized, review the transaction Projection Plan and confirm that Overview, Catalog, Behavior, Field, Failure, and BA summaries reflect the complete current Generation. A valid target link is insufficient when an upstream index omits the new Artifact or its surrounding explanation still describes an earlier model. Review every semantic Projection item; never mark it complete merely because the executor refreshed IDs and paths.

For each API Contract, perform a caller-first review before reading its Source notes:

- Can a developer identify the endpoint purpose, application method/route, authentication, content type, required inputs, success outcomes, caller-visible errors, contract confidence, and important limitations from the opening sections?
- Are field and conditional rules stated once, in the place a caller expects them?
- Are examples supported by code, schema, or tests, and are unknown wire shapes omitted rather than invented?
- When invocation details are known, does the request example show method, path, required observed headers, and body rather than presenting a body fragment alone?
- For a small response, is each fact presented only where it adds value, rather than repeated across the outcome row, response-fields table, and example?
- Does the Contract summarize and link to Endpoint Matrix, Tech Behavior, field mappings, dependencies, and Failure Taxonomy instead of copying their detailed content?
- Do request and response rows avoid downstream target paths, field renames, propagation, encoding, client-library checks, and other boundary-mapping detail that belongs in Field Validation and Mapping or External Dependency Contracts?
- Do evidence markers stay visually secondary while still allowing a reader to reach the supporting source note?

For Endpoint Matrix, perform a reader-value review:

- Do application endpoints and meaningful external exposures dominate the main table rather than routine protocol-support declarations?
- Are ordinary protocol-support observations summarized once while complete evidence remains available in the repository register?
- Are orphaned, conflicting, environment-inconsistent, and unresolved support operations visible as exceptions?
- Has any real application handler, business response, health/version capability, or dependency-backed operation been hidden merely because it uses OPTIONS or a mock/static integration?

For Field Validation and Mapping, perform a call-centric review:

- Does each Remote Operation appear once in the operation index and once as an anchored detail section?
- Are Method, Logical Target, Client Operation, related Behaviors, and call-level evidence stated once in Call Overview rather than repeated per Mapping row?
- Does each Tech Behavior contain at most one summary row per Call ID and link directly to that Call section?
- When one operation has several behaviors or call sites, are their Usage IDs and different invocation conditions preserved?
- Are request and response mappings separated, with usage scope retained when transformations differ?
- Were operations merged only when Method, Logical Target, and Client Operation all match?

For External Dependency Contracts, perform a dependency-centric review:

- Does each logical external participant or resource appear once in the landscape and once as an anchored detail section, regardless of Behavior or Operation count?
- Do its Operations sit beneath the Dependency and link to HTTP Calls, mappings, lifecycle, and failures instead of copying those documents?
- Can a developer understand the Dependency's repository-observed role, shared capabilities, exchanged concepts, availability impact, fallback/degradation, and state implications without reading the register?
- Were observations grouped from executable binding or resource-identity evidence rather than name, host, path, or type similarity?
- Are remote implementation, SLA, persistence, idempotency, and error semantics kept Unknown when this repository cannot prove them?
- Does the final document avoid an observation-by-observation evidence inventory?

For Failure Taxonomy, perform a Pattern-centric review:

- Does each `FAIL-nnn` explain one coherent trigger-to-handling-to-visible-result-to-state story across its affected Behaviors?
- Were observations merged only when source, propagation, caller visibility, state outcome, retry safety, and recovery are materially equivalent?
- Are swallowed failures, degraded or false-success results, partial/committed state, unsafe repetition, and missing recovery visible rather than hidden in generic categories?
- Can a developer identify High and materially Unknown attention items quickly and trace the classification back to source?
- Are caller response shapes, internal flow, data lifecycle, and Dependency detail linked rather than duplicated?
- Does the final document explain repository-wide patterns and inconsistencies instead of copying the Failure Observation table?

For Repository Overview, perform a repository-mental-model review:

- Can a developer understand each important connection's direction, boundary, role, exchanged concepts, supported capabilities/Behaviors, configuration variants, criticality, and failure/state impact without reading the register?
- Does the Mermaid diagram group participants around the repository and use edge direction to express real control or data movement rather than decorative proximity?
- Are same-role Operations for one Dependency reconciled into one logical connection, while different directions, roles, or configuration-selection semantics remain distinct?
- Are name-only, host-only, resource-only, or configuration-only candidates excluded or qualified rather than presented as confirmed connections?
- Does each Shared item affect at least two Behaviors or independent entries and materially shape observable behavior?
- Are logging, ordinary monitoring, framework glue, generated code, simple wrappers, behavior-neutral utilities, and single-Behavior helpers excluded?
- Can readers reach Endpoint, Contract, Behavior, Dependency, Mapping, Lifecycle, Config, and Failure detail with one relevant link instead of seeing those details copied into the Overview?

For Data Lifecycle, perform a typed-lifecycle review:

- Does every State describe a condition of one Object rather than an action, method, system, store, source, or destination?
- Does every diagram edge map to a registered Transition with supported From/To conditions and a real change point?
- Are Read, Observe, Validate, Transform, Map, Persist, Delete, Invoke, Emit, and Route presented as Actions, with Persist/Delete linked to a Transition only when separately supported?
- Are State Diagrams and Processing/Data Movement flows visually and structurally separate?
- Are Derived States marked `Inferred` with their derivation, and are Unknown/Conflicting candidates excluded from established diagram edges?
- When no Transition is established, is the State Diagram omitted rather than filled from call order?

For the BA Pack, perform an independent-business-model review:

- Do Journey and Scenario identities arise from business goals, contexts, decisions, objects, and outcomes rather than Entry Points or Tech Behavior IDs?
- Can one Scenario link several Tech Behaviors and can one Tech Behavior link zero, one, or several Scenarios without artificial documents?
- Does each Journey describe a repository-observable goal, stages, Scenario relationships, object progression, handoffs, and boundaries rather than a service call chain?
- Does each Scenario explain a supported business situation and visible outcomes without translating technical triggers and branches node by node?
- Were technical validation, Dependencies, and exceptions included only when their business meaning or visible impact is supported?
- Does the Tech coverage map account for every active Behavior with a defensible disposition?
- Can a BA understand the Pack without knowing handlers, endpoints, clients, resources, exception classes, or internal retry mechanics?

Revise for clarity when the answer is no, while preserving the underlying facts.

## Validator boundary

Validators may reject malformed Frontmatter boundaries, missing/multiple H1 headings, illegal heading jumps, unclosed fences, duplicate anchors, malformed Markdown tables, missing files, nonexistent local Markdown Fragments, invalid links, inconsistent IDs, dangling Call/Usage/Mapping/Dependency/Failure/Journey/Scenario/Object/State/Action/Transition references, cross-Object Transitions, Derived-as-Confirmed States, typed lifecycle diagram mismatches, duplicate IDs, invalid line ranges, template placeholders, and invalid controlled status values. The API Contract structure contract may require exact caller-facing table headers when a table is present. Validators may verify declared Journey–Scenario and Scenario–Tech backlinks. They must not decide from prose whether something is semantically a State or Action, whether a Transition is factually true, how Journeys or Scenarios should be split, whether a technical concept has business meaning, whether remote operations, Dependencies, Failure Patterns, Connections, or Shared items are semantically equivalent; derive Criticality or Risk Attention from prose; require Claim IDs, sentence-level citations, fixed prose length, a minimum number of table rows, Mermaid node counts unrelated to declared lifecycle projection, a fixed aggregation ratio, or prose/method/integration regexes that pretend to determine business meaning.

Register validation must first verify the versioned Schema contract and then isolate Lifecycle, HTTP, Dependency, and Failure domains. A bad header produces one Schema root error for that domain; it must not be interpreted as an empty ID index. Skip document reconciliation, completeness, Unknown-reference, and backlink checks that require the invalid or partial index, while continuing unrelated Endpoint, API, BA, HTTP, and Markdown checks. When Dependency is unavailable, Failure may still validate its local controlled fields but must skip Related Dependency cross-references.

Cap each validation group at ten displayed independent errors, de-duplicate identical messages, and summarize additional suppressed errors. `SKIPPED` is explicit loss of validation coverage, not success. Only zero Primary Errors and zero skipped necessary groups supports the statement that full mechanical validation passed.

Treat warnings as prompts for human-style inspection, not as a reason to add artificial Unknowns, jargon replacements, or extra Mermaid nodes.
