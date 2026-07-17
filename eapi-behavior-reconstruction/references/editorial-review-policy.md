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

Write the Tech view from the behavior dossier and repository synthesis. Include implementation structure only when it helps a developer follow the executable path.

Write the BA view as a new audience model from the dossier, synthesis, and verified Tech facts:

- Use actors, business events, decisions, business objects, outcomes, and exceptions.
- Do not reuse the Tech flow data or mechanically rename Tech Mermaid nodes.
- Do not expose class names, AWS resource identifiers, source paths, or field tables.
- Preserve uncertainty and link to the Tech view for details.

Before delivery, compare the Tech and BA diagrams. Identical diagrams are a defect. Similar topology is acceptable only when node meanings and narrative answer the two audiences' different questions.

## Three review passes

### Mechanical review

Use scripts for file structure, state transitions, endpoint identity, links, commit consistency, citation bounds, and placeholders. Fix mechanical errors without changing prose that is already accurate and readable.

### Fact review

Sample at least these high-risk facts back to source when present:

- A core rule and its failure outcome.
- A state change or data write.
- An outbound HTTP operation, one executable usage, and one mapping that proves both field boundaries.
- A configuration-dependent branch.
- A retry, partial-success, or dependency-failure path.
- For Java, a critical caller/callee edge and any interface-to-implementation selection that affects behavior.
- For API evidence, one application route, its external-entry correlation if any, and the resulting reachability assessment.
- For an aggregated protocol-support group, one representative declaration and its classification basis; prioritize any orphaned or conflicting exception.

For each sampled item, verify that the cited code proves the meaning expressed, not merely that the named file exists.

For sampled Java call relationships, verify the exact signatures rather than names alone, distinguish production callers from tests, and inspect the relevant constructor/injection point plus `@Bean`, `@Qualifier`, `@Primary`, `@Profile`, or component-scan evidence. If runtime binding remains ambiguous, ensure the document says so. Do not publish raw language-server operation logs; retain only limitations that affect the reader's understanding or the confidence of a conclusion.

For sampled endpoints, verify that each layer cites evidence of that layer, correlation uses an explicit target/mapping/binding, and the prose does not call an application route public, deployed, or reachable when only static evidence exists. For a summarized protocol-support item, also verify that no executable handler, business payload, state access, or business dependency call was overlooked. A method name or mock integration is not sufficient classification evidence.

### Reader review

Read the document without using source code and ask:

- Can a developer retell the complete success and material failure paths?
- Can a BA identify the business trigger, decisions, affected object, outcome, and exceptions?
- Can either reader find deeper contract, lifecycle, mapping, configuration, dependency, or failure detail with one link?
- Does the document contain repetitive status phrases, empty tables, template instructions, or validator-oriented wording?

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

Revise for clarity when the answer is no, while preserving the underlying facts.

## Validator boundary

Validators may reject missing files, invalid links, inconsistent IDs, dangling Call/Usage/Mapping references, duplicate IDs, invalid anchors, invalid line ranges, template placeholders, and invalid operation-role values in a published Matrix row. They must not decide whether remote operations are semantically equivalent, require Claim IDs, sentence-level citations, fixed prose length, a minimum number of table rows, a fixed aggregation ratio, or method/integration regexes that pretend to determine business meaning.

Treat warnings as prompts for human-style inspection, not as a reason to add artificial Unknowns, jargon replacements, or extra Mermaid nodes.
