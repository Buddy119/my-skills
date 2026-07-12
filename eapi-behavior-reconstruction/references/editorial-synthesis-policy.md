# Editorial synthesis policy

## Purpose

Turn passing repository facts into documents that BA and developers can read as explanations rather than audits. Keep the fact boundary strict and the prose flexible.

Claims define what is materially supportable. They do not define sentence wording, paragraph length, heading names, or document rhythm.

## Materiality boundary

A conclusion is material when changing it would change the reader's understanding of a trigger, decision, validation outcome, data or state change, external interaction, visible result, failure, API contract, or business meaning.

Keep these facts precise:

- API method, route, field, rule, status, example, mapping, configuration, and state literal.
- Money, currency, precision, authorization, persistence, transaction, rollback, idempotency, retry/DLQ, concurrency, encryption, retention, sensitivity/PII classification, and consumer-visible failure.
- Whether an external call was attempted versus whether the remote operation completed.
- Whether a mutation is local versus persisted or business-visible.

Allow free editorial treatment for wording, transition, framing, terminology explanation, paragraph structure, and concise summaries when the material meaning remains unchanged.

## Document profiles

Use three profiles:

- **Narrative**: `knowledge-map.md`, Tech/BA overviews, Tech Behaviors, BA Behaviors, `ba-pack/behavior-catalog.md`, capability map, business data lifecycle, business rule catalog, and business exception catalog. Organize around reader questions and use document- or section-level Claim groups. Do not attach Claim markers to every sentence.
- **Reference**: API contracts; `coverage-report.md`; endpoint, field, data, configuration, dependency, failure, state, validation, lineage, and mapping Markdown; and dependency contract stubs. Keep exact rows, cells, examples, and machine values Claim-backed.
- **Machine/Audit**: `evidence-index.json`, Claim ledger/audit, `knowledge-manifest.yaml`, `tech-pack/behavior-catalog.yaml`, and flow models. Optimize for determinism and traceability, not prose.

Classify by these exact output families, not by a filename containing words such as `catalog` or `matrix`.

## Narrative writing

Start with the reader's likely question, then explain the relevant facts in a useful order. Combine related Claims into coherent paragraphs. Use pronouns, synonyms, connective language, and short explanations when they help comprehension.

Do not iterate through the Claim ledger and render each statement. Do not repeat detailed contracts or matrices inside a Behavior; summarize and link instead.

For a Tech Behavior, help a developer understand:

- why and how execution starts;
- the end-to-end implementation story and important branches;
- data access, local mutation, supported state changes, and external calls;
- configuration and dependency effects;
- failure, recovery, partial-success behavior, and important unknowns.

For a BA Behavior, help a BA understand:

- the business or operational event;
- participants and information involved, when known;
- decisions, meaningful rules, and visible outcomes;
- business-visible exceptions and external participants;
- which business meaning cannot be established from this repository.

When evidence is sparse, write a short, clear document. Narrative template headings are prompts rather than a required outline: rename, reorder, merge, or omit sections when that helps the intended reader. Do not manufacture empty tables, repeated Unknown rows, actors, purposes, or outcomes to satisfy a template. Keep each material Unknown in the one place where it best explains the limitation.

## Tech and BA independence

Build Tech and BA flow models independently and never fall back from one to the other. Write their summaries independently as well. A similar phrase or shared domain term is not itself an error; direct reuse of one flow, generic metadata object, or rendered narrative is.

Use similarity, jargon density, table density, and short-paragraph streaks only as editorial diagnostics. Let a reader review decide whether rewriting is necessary.

## Grounding review

After drafting, review the document at section or document level:

1. Identify its material conclusions.
2. Confirm that compatible passing Claims support them and that confidence was not upgraded.
3. Remove or qualify any new causal guarantee, remote outcome, persistence result, security property, business purpose, or consumer-visible effect.
4. Ignore ordinary changes in wording that do not alter material meaning.
5. Read the result without the Claim ledger and revise anything that still sounds like a Claim dump or template projection.

An optional Composition Model may group Claims by reader question for complex documents. It is an authoring aid, not a mandatory schema and not a source of facts.

## Reader review

Before delivery, check that a developer can explain the repository's responsibility, main execution paths, data/dependencies, failures, and limitations from the Tech Pack. Check that a BA can explain the supported scenario, decisions, information, outcomes, exceptions, and unknown business meaning from the BA Pack.

Treat automated readability findings as prompts for review, not automatic proof that prose is good or bad.
