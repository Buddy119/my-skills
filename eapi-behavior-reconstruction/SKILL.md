---
name: eapi-behavior-reconstruction
description: "Automatically discover and reconstruct observable business and integration behaviors from a single EAPI microservice or AWS Lambda repository, starting with only a local path. Build a deterministic evidence index, then produce two linked outputs: a developer-oriented Tech Pack with source-backed behavior documents, API contracts, external HTTP mappings, and failure details; and a BA Pack that translates the same verified behavior into business capabilities, actors, triggers, rules, outcomes, and exceptions without inventing intent. Use when Codex needs to understand an unfamiliar EAPI repository, reverse-engineer undocumented behavior, create technical and business-readable documentation, or prepare evidence for later cross-service impact analysis."
---

# EAPI Behavior Reconstruction

Discover and reconstruct a repository's observable current behaviors without requiring the user to understand its handlers or architecture. Keep every material conclusion traceable to code, tests, configuration, or infrastructure definitions.

## Required inputs

Require only the local path of one repository.

Accept these optional inputs when supplied:

- A behavior selector to restrict analysis to one Lambda handler, API route, event consumer, scheduled job, or named behavior.
- An output directory; otherwise default to `behavior-docs/<repository-name>/` beside the working context.

When only the repository path is supplied, enter repository auto-discovery mode. Do not ask the user to identify handlers, choose behaviors, explain the repository, or rank entry points. Perform those tasks from source evidence.

## Load the evidence policy

Read [references/evidence-policy.md](references/evidence-policy.md) completely before analyzing source code. Apply its status and citation rules to every output.

When executable code makes an outbound HTTP call to an external system, also read [references/field-mapping-policy.md](references/field-mapping-policy.md) completely and apply it. Do not load or apply field-mapping requirements to inbound APIs, events, queues, streams, persistence, or purely internal transformations.

For an API behavior, read [references/api-contract-policy.md](references/api-contract-policy.md) completely and apply it to a separate API contract document.

Before creating BA-facing outputs, read [references/ba-pack-policy.md](references/ba-pack-policy.md) completely and apply its translation and terminology rules.

## Workflow

### 1. Establish the analysis boundary

- Confirm the repository root and record the current Git commit with `git rev-parse HEAD` when available.
- Treat generated artifacts, vendored dependencies, build output, coverage output, and lockfiles as secondary evidence unless they define deployment behavior.
- Do not access credentials, secret values, production customer data, or live AWS resources.
- State excluded or unreadable areas in the final document.

### 2. Inventory the repository

Create a temporary deterministic evidence index before manually tracing files:

```bash
python3 scripts/build_evidence_index.py \
  --repo <repository-root> \
  --output <output-dir>/.work/evidence-index.json
```

Use its file line counts, role hints, symbols, endpoint markers, outbound HTTP markers, test declarations, and assertion locations to plan source reads. Treat markers as search hints, not as conclusions.

Then search with `rg` and `rg --files` as needed. Detect:

- Languages, runtimes, frameworks, build files, and module boundaries.
- Lambda handlers and runtime registration.
- API Gateway, SAM, CDK, Serverless, Terraform, or CloudFormation definitions.
- SQS, SNS, EventBridge, DynamoDB Stream, Kinesis, S3, and schedule triggers.
- Step Functions tasks.
- Tests, fixtures, schemas, and deployment configuration.
- Data stores, outbound clients, shared libraries, Lambda Layers, and environment-controlled dependencies.

Group related trigger, handler, and orchestration code into distinct behaviors. Avoid counting the API route, Lambda handler, and service method as three behaviors when they implement one flow. Keep health checks, framework glue, migrations, and deployment-only utilities in the catalog but classify them as technical behaviors.

Create:

```text
behavior-docs/<repository-name>/
├── .work/
│   └── evidence-index.json
├── tech-pack/
│   ├── repository-overview.md
│   ├── behavior-catalog.yaml
│   ├── behaviors/
│   └── contracts/
└── ba-pack/
    ├── business-overview.md
    ├── behavior-catalog.md
    └── behaviors/
```

Copy [assets/repository-overview-template.md](assets/repository-overview-template.md) and [assets/behavior-catalog-template.yaml](assets/behavior-catalog-template.yaml) into `tech-pack/`. Populate every discovered behavior with a stable ID, trigger, entry point, category, evidence, and analysis status.

If a behavior selector was supplied, use the inventory only to locate that behavior and analyze it in targeted mode. Otherwise continue automatically through every discovered business and integration behavior.

### 3. Plan internal analysis batches

Order behaviors by dependency and signal:

1. Public API and synchronous request handlers.
2. Event, queue, stream, and scheduled consumers.
3. Shared orchestration behaviors referenced by multiple entry points.
4. Technical behaviors.

Process at most five behaviors in one internal batch to keep evidence focused. Persist completed documents and update `behavior-catalog.yaml`, then continue with the next batch without asking the user to select it. Stop early only when the repository is inaccessible, required permissions are unavailable, or source ambiguity makes further claims unsafe; record the exact blocker and partial coverage.

### 4. Trace each behavior

Follow the executable path from entry point to observable outcomes:

1. Parse and map the input.
2. Apply validation and authorization.
3. Execute domain or orchestration logic.
4. Read and write data.
5. Call external services.
6. Publish events or enqueue messages.
7. Map the response.
8. Handle failures, retries, idempotency, compensation, and partial success.

Inspect tests alongside implementation. For each behavior, when relevant tests exist, trace at least one or two concrete assertions that prove core rules or outcomes; prioritize a failure-path assertion. Cite the assertion or expectation lines and their setup/trigger when needed. A test filename, test class, or test method declaration alone is not behavioral evidence.

Inspect IaC and configuration for runtime facts such as trigger filters, timeouts, retries, DLQs, permissions, resource names, and environment-dependent wiring.

Stop at repository boundaries. Represent calls or events owned elsewhere as external dependency stubs; do not infer the other repository's internal behavior.

Create a Mermaid `flowchart` for every behavior. Show the trigger, major internal steps, decisions, data access, external calls, emitted events, success result, and material failure branches. Keep the diagram at behavior level rather than reproducing every method call. Mark inferred nodes with `(Inferred)` and explain their evidence status in the surrounding prose.

### 5. Trace external HTTP field mappings when applicable

First locate a real outbound HTTP/HTTPS invocation in executable code, such as an HTTP client, SDK wrapper that performs HTTP, generated REST client, or framework HTTP adapter. Record it in `external_http_calls` with its client/operation, method, target, and source evidence.

Only after confirming that call, generate mappings for:

- EAPI fields to the external HTTP request path, query, header, or body.
- External HTTP response fields back to EAPI fields when the response is consumed.

Do not create `field_mappings` for the repository's inbound API request/response, EventBridge, SQS, SNS, streams, DTO-to-domain, domain-to-persistence, or other internal conversions. Document inbound APIs in the API contract and non-HTTP integrations in inputs, outputs, side effects, and dependency stubs.

For applicable external mappings, record direct copies, renames, nested-path changes, type/format conversions, enum translations, defaults, constants, conditional mappings, computed fields, one-to-many or many-to-one transformations, masking, truncation, and intentionally dropped fields. Cite both the source-field read and target-field write when they occur at different locations.

Use stable boundary names that can later connect documents. Do not manufacture an upstream or downstream field name that is unavailable in this repository; create an `Unknown` mapping endpoint or an open question instead.

### 6. Separate observations from interpretation

- Describe what the implementation currently does.
- Do not claim to recover the original requirement or design rationale.
- Label each material statement as `Confirmed`, `Inferred`, `Conflicting`, or `Unknown` according to the evidence policy.
- Record contradictions rather than choosing the most convenient source.
- Record unanswered transactional, retry, contract, or data-consistency questions explicitly.

### 7. Create the Tech Pack

Copy and complete [assets/behavior-document-template.md](assets/behavior-document-template.md). Preserve the YAML keys even when a list is empty so future aggregation remains deterministic. This is the technical source of truth.

Write each document to `tech-pack/behaviors/<behavior-id>.md`. After validation, update the corresponding catalog entry from `discovered` to `documented` or `blocked`.

For each API behavior:

1. Copy and complete [assets/api-contract-document-template.md](assets/api-contract-document-template.md) as `tech-pack/contracts/<behavior-id>.api-contract.md`.
2. Keep L1 executable, L2 schema-level, and L3 shared/opaque-transformer evidence separate in that contract.
3. Set the behavior document's `api_contract_document` to `../contracts/<behavior-id>.api-contract.md`.
4. Add a short `API contract` section containing a relative Markdown link to the contract; do not duplicate contract tables in the behavior document.
5. Set the contract's `behavior_document` to `../behaviors/<behavior-id>.md` and include a visible return link.

For non-API behaviors, keep `api_contract_document: null` and omit the `API contract` section.

Classify each behavior as `business`, `integration`, or `technical`. For business and integration behaviors, reserve `ba_behavior_document` for `../../ba-pack/behaviors/<behavior-id>.md` and add a short `BA view` link section. For purely technical behaviors, set `ba_behavior_document: null` and omit that section.

Before deriving the BA document, pre-validate each business or integration Tech Behavior while allowing only the not-yet-created BA target file:

```bash
python3 scripts/validate_behavior_doc.py \
  <tech-behavior-document.md> \
  --repo <repository-root> \
  --allow-missing-ba
```

The BA metadata and visible Markdown link are still required in this mode. Do not use this option for final validation.

Use stable connection names when the code provides them:

- HTTP method plus normalized route.
- Event source plus event/detail type or schema name.
- Queue, topic, event bus, table, state machine, and Lambda logical names.
- Fully qualified external client or operation names when resource names are indirect.

Before writing each citation, preview and range-check it:

```bash
python3 scripts/show_evidence.py \
  --repo <repository-root> \
  path/to/file.ext:start-end
```

Use the displayed line numbers to narrow the citation to the smallest range that proves the claim. Never draft a range from memory or search-output offsets. Use repository-relative POSIX citations as `path/to/file.ext:line` or `path/to/file.ext:start-end`.

### 8. Derive the BA Pack

Generate the BA Pack only after the related Tech Pack documents pass pre-validation and any applicable API contract passes full validation.

1. Copy [assets/ba-overview-template.md](assets/ba-overview-template.md) to `ba-pack/business-overview.md`.
2. Copy [assets/ba-behavior-catalog-template.md](assets/ba-behavior-catalog-template.md) to `ba-pack/behavior-catalog.md`.
3. For every `business` or `integration` behavior, copy [assets/ba-behavior-document-template.md](assets/ba-behavior-document-template.md) to `ba-pack/behaviors/<behavior-id>.md`.
4. Translate the verified behavior into business language: business capability, actors, trigger, preconditions, rules, business flow, inputs/outputs, outcomes, exceptions, and external business interactions.
5. Do not repeat classes, handlers, methods, AWS resources, source paths, field-level mappings, retry implementation, or API schemas in the BA narrative. Link to the Tech Behavior for those details.
6. Preserve `Confirmed`, `Inferred`, `Conflicting`, and `Unknown`. Never convert a technical inference into a confirmed business purpose.
7. Link BA documents back to `../../tech-pack/behaviors/<behavior-id>.md` and ensure the Tech Behavior links to the BA document.
8. Exclude purely technical behaviors from BA behavior documents, but summarize their business relevance only when they materially affect a business outcome.

### 9. Validate both packs

Run:

```bash
python3 scripts/validate_behavior_doc.py <behavior-document.md> --repo <repository-root>
```

For API behaviors, also run:

```bash
python3 scripts/validate_api_contract.py <api-contract.md> --repo <repository-root>
```

For each BA behavior, run:

```bash
python3 scripts/validate_ba_behavior.py <ba-behavior.md>
```

Resolve validation errors before delivering. Treat warnings as review items and mention any warning that remains intentional.

### 10. Deliver

Report:

- The Tech Pack and BA Pack directories, generated behavior paths, and API contract paths.
- The analyzed repository and commit.
- The number of discovered, documented, technical, and blocked behaviors.
- The strongest confirmed findings.
- The important inferred, conflicting, or unknown items.
- Validation results for every behavior document.

Do not modify application source code unless the user separately requests an implementation change.

## Quality bar

Before completing, verify that:

- The document covers the happy path and failure paths.
- The `Behavior flow` section contains a readable Mermaid flowchart with decisions and material failure branches.
- Business rules cite source or test evidence.
- Matching tests contribute one or two assertion-level citations per behavior when available, with failure paths prioritized.
- Data reads, writes, events, and external calls appear in both YAML metadata and prose.
- `external_http_calls` and `field_mappings` are empty when no outbound HTTP call exists in executable code.
- When an outbound HTTP call exists, record it in `external_http_calls`; include `field_mappings` only for its request and consumed response fields.
- Every external HTTP mapping appears in metadata and the `External HTTP field mappings` section with call ID, transformation, condition, default, lossiness, confidence, and evidence.
- Every API behavior document links to a separate API contract, and the contract links back to the behavior document.
- Every API contract separates L1 executable, L2 schema-level, and L3 shared/opaque-transformer evidence for both input and output; absent layers are explicitly marked as not observed.
- Every business or integration Tech Behavior links to one BA Behavior, and every BA Behavior links back.
- BA documents use business actors, events, rules, outcomes, and exceptions; technical identifiers remain behind Tech Pack links.
- BA documents contain no raw source citations and derive from a Tech Behavior at the same repository commit.
- AWS behavior comes from IaC/configuration evidence when available.
- External dependencies are named but not over-interpreted.
- The document records the Git commit and analysis limitations.
- No secret value or customer data is reproduced.
- The catalog accounts for every discovered executable entry point as documented, technical, duplicate, excluded, or blocked.
- Every citation was previewed with `show_evidence.py` before drafting and passes final validation.
