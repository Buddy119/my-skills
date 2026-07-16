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
- An outbound HTTP mapping.
- A configuration-dependent branch.
- A retry, partial-success, or dependency-failure path.
- For Java, a critical caller/callee edge and any interface-to-implementation selection that affects behavior.
- For API evidence, one application route, its external-entry correlation if any, and the resulting reachability assessment.

For each sampled item, verify that the cited code proves the meaning expressed, not merely that the named file exists.

For sampled Java call relationships, verify the exact signatures rather than names alone, distinguish production callers from tests, and inspect the relevant constructor/injection point plus `@Bean`, `@Qualifier`, `@Primary`, `@Profile`, or component-scan evidence. If runtime binding remains ambiguous, ensure the document says so. Do not publish raw language-server operation logs; retain only limitations that affect the reader's understanding or the confidence of a conclusion.

For sampled endpoints, verify that each layer cites evidence of that layer, correlation uses an explicit target/mapping/binding, and the prose does not call an application route public, deployed, or reachable when only static evidence exists.

### Reader review

Read the document without using source code and ask:

- Can a developer retell the complete success and material failure paths?
- Can a BA identify the business trigger, decisions, affected object, outcome, and exceptions?
- Can either reader find deeper contract, lifecycle, mapping, configuration, dependency, or failure detail with one link?
- Does the document contain repetitive status phrases, empty tables, template instructions, or validator-oriented wording?

Revise for clarity when the answer is no, while preserving the underlying facts.

## Validator boundary

Validators may reject missing files, invalid links, inconsistent IDs, invalid line ranges, and template placeholders. They must not require Claim IDs, sentence-level citations, fixed prose length, a minimum number of table rows, or regex-defined business meaning.

Treat warnings as prompts for human-style inspection, not as a reason to add artificial Unknowns, jargon replacements, or extra Mermaid nodes.
