---
name: eapi-behavior-reconstruction
description: "Automatically reconstruct a complete, evidence-grounded repository knowledge pack from one unfamiliar EAPI microservice or AWS Lambda repository using only its local path. Inventory behavior, inbound endpoints and endpoint-owned API contracts, data assets and lifecycle, state transitions, boundary fields, validation rules, internal field lineage, proven external HTTP mappings, runtime configuration, external dependency contract stubs, and a global failure taxonomy. Produce linked developer Tech Pack and business-readable BA Pack views, a canonical knowledge manifest, navigation map, and coverage report. Use when Codex needs to understand an undocumented repository, onboard BA or developers, recover implementation and business-facing knowledge, or prepare reliable impact-analysis inputs."
---

# EAPI Repository Knowledge Pack

Build the maximum defensible understanding of one repository at one recorded commit. Treat behavior as the navigation spine, not as the container for all repository knowledge. Keep every material conclusion traceable to code, tests, configuration, IaC, or schema evidence.

## Required input

Require only the local repository path.

Accept an optional analysis selector and output directory. A selector may target one endpoint, handler, event consumer, scheduled job, or behavior, but targeted output must be marked `partial`. Without a selector, discover and document the repository automatically; do not ask the user to explain the repository or choose entry points.

Default output:

```text
repository-knowledge-pack/<repository-name>/
```

## Load policies

Read [references/evidence-policy.md](references/evidence-policy.md) and [references/knowledge-pack-policy.md](references/knowledge-pack-policy.md) completely before analysis.

Read these policies when building their corresponding canonical pack:

- [references/api-contract-policy.md](references/api-contract-policy.md) for inbound endpoints.
- [references/data-lifecycle-policy.md](references/data-lifecycle-policy.md) for data assets, lineage, and state transitions.
- [references/field-pack-policy.md](references/field-pack-policy.md) for fields, validation, and internal lineage.
- [references/runtime-config-policy.md](references/runtime-config-policy.md) for environment, IaC, Lambda, and trigger configuration.
- [references/dependency-contract-policy.md](references/dependency-contract-policy.md) for repository-external dependencies.
- [references/failure-taxonomy-policy.md](references/failure-taxonomy-policy.md) for global failures.
- [references/ba-pack-policy.md](references/ba-pack-policy.md) before creating BA views.

Read [references/field-mapping-policy.md](references/field-mapping-policy.md) only after executable code proves an outbound HTTP/HTTPS call. Never create external mappings for inbound APIs, events, queues, streams, persistence, or internal object conversions.

## Output structure

Create:

```text
repository-knowledge-pack/<repository-name>/
├── knowledge-manifest.yaml
├── knowledge-map.md
├── coverage-report.md
├── .work/
│   └── evidence-index.json
├── tech-pack/
│   ├── repository-overview.md
│   ├── behavior-catalog.yaml
│   ├── behaviors/
│   ├── endpoints/
│   │   ├── endpoint-matrix.md
│   │   └── contracts/
│   ├── data/
│   │   ├── data-asset-catalog.md
│   │   ├── data-lineage.md
│   │   └── state-transition-matrix.md
│   ├── fields/
│   │   ├── field-catalog.md
│   │   ├── validation-rule-matrix.md
│   │   ├── field-lineage.md
│   │   └── external-http-mapping-matrix.md
│   ├── runtime/
│   │   └── runtime-config-matrix.md
│   ├── dependencies/
│   │   ├── dependency-matrix.md
│   │   └── stubs/
│   └── reliability/
│       └── failure-taxonomy.md
└── ba-pack/
    ├── business-overview.md
    ├── capability-map.md
    ├── business-data-lifecycle.md
    ├── business-rule-catalog.md
    ├── business-exception-catalog.md
    ├── behavior-catalog.md
    └── behaviors/
```

Keep `knowledge-manifest.yaml` as the canonical relationship registry and `knowledge-map.md` as the human landing page.

## Workflow

### 1. Establish boundary and evidence index

- Resolve the repository root and record `git rev-parse HEAD` when available.
- Exclude generated output, dependencies, coverage, build artifacts, and vendored code unless they define deployment behavior.
- Never access live AWS resources, credentials, secret values, or production/customer data.
- Record inaccessible, dynamic, generated, or environment-only areas.

Scaffold the complete static pack structure first:

```bash
python3 scripts/scaffold_knowledge_pack.py \
  --repo <repository-root> \
  --output <pack-root>
```

The scaffold command populates the repository name and commit, creates all canonical static documents and dynamic output directories, and refuses to overwrite existing static documents unless `--force` is explicitly supplied. It never deletes dynamic behavior, contract, or dependency-stub documents.

Then build the deterministic evidence index before manual tracing:

```bash
python3 scripts/build_evidence_index.py \
  --repo <repository-root> \
  --output <pack-root>/.work/evidence-index.json
```

Use file line counts, roles, symbols, and markers for endpoints, handlers, outbound HTTP, configuration, data access, state, events, failures, retry, tests, and assertions as search hints. Markers are not conclusions.

### 2. Create the canonical inventory

Populate the scaffolded [assets/knowledge-manifest-template.yaml](assets/knowledge-manifest-template.yaml), [assets/knowledge-map-template.md](assets/knowledge-map-template.md), and [assets/coverage-report-template.md](assets/coverage-report-template.md).

Inventory and assign stable IDs to:

- Behaviors and executable entry points.
- Every distinct inbound endpoint, even when handlers are shared.
- Behaviorally relevant data assets, reads, writes, events, and state fields.
- Boundary-visible or rule-significant fields and validation rules.
- Runtime configuration and IaC settings that affect behavior.
- External dependencies and material shared/opaque components.
- Explicit, translated, configured, and partial-success failures.
- Proven outbound HTTP calls and their mappings.

Use the ID conventions in the knowledge-pack policy. Never use discovery-order numbering that changes when another entity is found.

Populate manifest relationships before writing final prose. Update it continuously as tracing discovers new entities. Preserve every top-level entity section even when empty.

Replace or remove every scaffold example row and placeholder. For an empty entity set, use `section: []` in the manifest and write `None observed` plus coverage limitations in its canonical document.

### 3. Discover behaviors and endpoints

Group trigger, handler, controller, service, and orchestration code into observable behaviors. Do not count layers in one execution path as separate behaviors. Classify health checks, framework glue, migrations, and deployment-only utilities as technical.

Build one endpoint record per distinct inbound method and route. Do not merge endpoints because they share a handler. When the same observable contract is genuinely shared, use `contract_alias_of` and explain the equivalence.

Trace each executable behavior through:

1. Input parsing and boundary mapping.
2. Authentication, authorization, validation, normalization, and defaults.
3. Domain/orchestration decisions.
4. Data reads, writes, state changes, and transaction boundaries.
5. External dependencies and emitted messages/events.
6. Response/result mapping.
7. Failures, retries, DLQs, compensation, and partial success.

Inspect relevant tests alongside implementation. Extract one or two concrete assertions for core outcomes when available; prioritize a failure path. A test name alone is not behavioral evidence.

Process at most five behaviors per internal analysis batch. Persist completed artifacts and continue automatically.

### 4. Build endpoint-owned API contracts

Complete the scaffolded [assets/endpoint-matrix-template.md](assets/endpoint-matrix-template.md) at `tech-pack/endpoints/endpoint-matrix.md`.

For every inbound endpoint, copy [assets/api-contract-document-template.md](assets/api-contract-document-template.md) to `tech-pack/endpoints/contracts/<endpoint-id>.api-contract.md`.

- Organize the contract for the API consumer: endpoint/security, request, response outcomes, errors, examples, and applicable semantics.
- Put L1 executable, L2 schema, and L3 shared/opaque evidence in the Evidence Appendix.
- Link the contract to the endpoint matrix and its primary Tech Behavior.
- Link every API entry behavior and shared behavior reached from an endpoint to each relevant endpoint and contract.
- Keep unobserved route, gateway, authorization, status, or error behavior `Unknown`; do not fill industry-standard defaults.

### 5. Build the Tech Behavior view

Complete the scaffolded [assets/repository-overview-template.md](assets/repository-overview-template.md) and [assets/behavior-catalog-template.yaml](assets/behavior-catalog-template.yaml). Copy [assets/behavior-document-template.md](assets/behavior-document-template.md) for each behavior.

Write behaviors to `tech-pack/behaviors/<behavior-id>.md`. Include a Mermaid flowchart, happy/failure paths, rule IDs, data asset IDs, dependency IDs, config IDs, failure IDs, endpoint IDs, and links to canonical Pack documents.

Behaviors summarize repository-wide knowledge; do not duplicate full API contracts, field matrices, runtime matrices, dependency stubs, or failure definitions.

For `business` and `integration` behaviors, reserve `ba_behavior_document: ../../ba-pack/behaviors/<behavior-id>.md`. Technical behaviors use `null`.

### 6. Build the Data Pack

Complete the scaffolded documents based on:

- [assets/data-asset-catalog-template.md](assets/data-asset-catalog-template.md)
- [assets/data-lineage-template.md](assets/data-lineage-template.md)
- [assets/state-transition-matrix-template.md](assets/state-transition-matrix-template.md)

Account for every behaviorally relevant read, write, response, message, event, and external call. Distinguish internal transformation, storage mutation, and supported business state transition. Record transaction, idempotency, concurrency, rollback, and partial state only when visible.

### 7. Build the Field Pack

Complete the scaffolded documents based on:

- [assets/field-catalog-template.md](assets/field-catalog-template.md)
- [assets/validation-rule-matrix-template.md](assets/validation-rule-matrix-template.md)
- [assets/field-lineage-template.md](assets/field-lineage-template.md)
- [assets/external-http-mapping-matrix-template.md](assets/external-http-mapping-matrix-template.md)

Catalog boundary-visible or behaviorally significant fields, not every local variable. Separate executable validation from schema declaration. Use Field Lineage for internal API/domain/storage/event transformations.

Only after a real outbound HTTP call is proven, register an `HTTP-` call and `MAP-` records in the manifest and external mapping matrix. Behavior documents reference those IDs.

### 8. Build Runtime, Dependency, and Failure Packs

Complete the scaffolded runtime, dependency-matrix, and failure documents; copy the dynamic dependency-stub template as needed:

- [assets/runtime-config-matrix-template.md](assets/runtime-config-matrix-template.md)
- [assets/dependency-matrix-template.md](assets/dependency-matrix-template.md)
- [assets/external-dependency-stub-template.md](assets/external-dependency-stub-template.md) for each material external dependency
- [assets/failure-taxonomy-template.md](assets/failure-taxonomy-template.md)

Record configuration definitions and reads, defaults, Lambda/trigger settings, behavior effects, and missing/invalid outcomes. Record secret names only.

Treat repository-external systems and unavailable behaviorally material components as black-box stubs. Record only the visible contract and operational semantics.

Assign every material failure one `FAIL-` ID. Behavior failure tables reference this global taxonomy. Distinguish exception, consumer-visible outcome, retry cause, configured retry, rollback, and partial success.

### 9. Derive the BA Pack

Generate BA views only from validated Tech facts at the same commit. Complete the scaffolded repository-wide BA documents and copy the dynamic behavior template as needed:

- [assets/ba-overview-template.md](assets/ba-overview-template.md)
- [assets/ba-capability-map-template.md](assets/ba-capability-map-template.md)
- [assets/ba-business-data-lifecycle-template.md](assets/ba-business-data-lifecycle-template.md)
- [assets/ba-business-rule-catalog-template.md](assets/ba-business-rule-catalog-template.md)
- [assets/ba-business-exception-catalog-template.md](assets/ba-business-exception-catalog-template.md)
- [assets/ba-behavior-catalog-template.md](assets/ba-behavior-catalog-template.md)
- [assets/ba-behavior-document-template.md](assets/ba-behavior-document-template.md) for business/integration behaviors

Use business capabilities, actors, information, decisions, outcomes, and visible exceptions. Do not include source citations, classes, methods, AWS identifiers, API field paths, configuration keys, or exception classes. Link to canonical Tech documents for details. Preserve evidence confidence.

### 10. Preview evidence and validate

Before drafting any citation, range-check it:

```bash
python3 scripts/show_evidence.py --repo <repository-root> path/to/file.ext:start-end
```

Run individual validation:

```bash
python3 scripts/validate_behavior_doc.py <tech-behavior.md> --repo <repository-root>
python3 scripts/validate_api_contract.py <endpoint-contract.md> --repo <repository-root>
python3 scripts/validate_ba_behavior.py <ba-behavior.md>
```

For a business/integration Tech Behavior whose BA target is not created yet, pre-validate with `--allow-missing-ba`; never use that flag for final validation.

Finally validate the entire relationship graph, coverage, links, IDs, commit consistency, BA citation boundary, and source citation bounds:

```bash
python3 scripts/validate_knowledge_pack.py <pack-root> --repo <repository-root>
```

Resolve all errors. Mention intentional warnings in delivery.

## Delivery

Report pack path, repository, commit, analysis mode, coverage status, entity counts, strongest confirmed findings, important unknown/conflicting/blocked areas, and validator results. Do not modify application source code unless separately requested.

## Quality bar

Before completion, verify:

- `knowledge-manifest.yaml` accounts for every discovered entity and relationship.
- `knowledge-map.md` lets BA and developers reach every canonical view.
- Every executable entry point has a documented disposition.
- Every endpoint has a matrix row, endpoint-owned contract, and linked behavior.
- Data lineage accounts for repository-visible origins, transformations, reads/writes, and destinations.
- State transitions are evidence-backed and distinguish business state from storage mutation.
- Field validation, internal lineage, and external HTTP mappings are separate canonical views.
- External HTTP mappings exist only for proven outbound HTTP calls.
- Every behaviorally relevant configuration read or IaC setting has a `CFG-` record.
- Every material external dependency has a matrix disposition and contract stub when applicable.
- Every material failure has one canonical `FAIL-` record referenced by behaviors.
- BA views contain business language, no raw source citations, and no unsupported business intent.
- All documents use the same repository commit and all relative links resolve.
- Coverage is never called complete while entry points, schemas, shared components, dynamic configuration, or repository signals remain undisposed.
- No credential, secret value, production payload, or customer data is reproduced.
