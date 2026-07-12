---
name: eapi-behavior-reconstruction
description: "Automatically reconstruct a claim-first, evidence-grounded repository knowledge pack from one unfamiliar EAPI microservice or AWS Lambda repository using only its local path, remaining explicitly partial or Unknown wherever evidence is insufficient. Inventory behavior, inbound endpoints and endpoint-owned API contracts, data assets and lifecycle, state transitions, boundary fields, validation rules, internal field lineage, proven external HTTP mappings, runtime configuration, external dependency contract stubs, and a global failure taxonomy. Produce linked developer Tech Pack and business-readable BA Pack views, a canonical knowledge manifest, navigation map, and coverage report. Use when Codex needs to understand an undocumented repository, onboard BA or developers, recover implementation and business-facing knowledge, or prepare reliable impact-analysis inputs."
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

## Immutable bundled runtime

Treat the directory containing this file as `SKILL_ROOT`. During repository analysis, `SKILL.md`, `agents/`, `assets/`, `bin/`, `references/`, `scripts/`, and `integrity/runtime-lock.json` are immutable release artifacts. Never request write permission for `SKILL_ROOT`; never edit, patch, chmod, copy-and-modify, replace, or regenerate them. Write only to the selected knowledge-pack output directory.

The hash lock detects change; the host's read-only sandbox is the prevention boundary. Keep `SKILL_ROOT` outside writable workspace roots. If it is writable in the current execution environment, stop and use a read-only installed copy rather than continuing.

The bundled Python tools have no third-party dependencies. Never install packages, create a virtual environment, alter `PYTHONPATH`, or create a fallback script. Resolve `SKILL_ROOT` from the selected Skill path rather than the current working directory, and run tools only through:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" <command> ...
```

Before the first operation, run `preflight`. A validation failure means fix the generated pack, never the validator. An invocation failure means correct arguments. Any `FATAL_RUNTIME`, exit `70`, integrity mismatch, missing module, or unexpected traceback is terminal for the current run: report it and stop without repairing the Skill.

## Load policies

Read [references/runtime-integrity-policy.md](references/runtime-integrity-policy.md) completely before invoking any bundled command. Its execution and failure-handling rules are mandatory.

Read [references/evidence-policy.md](references/evidence-policy.md), [references/claim-first-policy.md](references/claim-first-policy.md), and [references/knowledge-pack-policy.md](references/knowledge-pack-policy.md) completely before analysis. The claim-first policy controls generation order and overrides presentation completeness.

Read [references/flow-perspective-policy.md](references/flow-perspective-policy.md) completely before creating any Tech or BA Behavior. Its separate-model and semantic-comparison requirements are mandatory.

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
│   ├── evidence-index.json
│   ├── claim-ledger.json
│   ├── claim-audit.json
│   └── flow-models/
│       ├── <behavior-id>.tech-flow.json
│       └── <behavior-id>.ba-flow.json
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

Run the immutable runtime preflight once before step 1:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" preflight
```

### 1. Establish boundary and evidence index

- Resolve the repository root and record `git rev-parse HEAD` when available.
- Exclude generated output, dependencies, coverage, build artifacts, and vendored code unless they define deployment behavior.
- Never access live AWS resources, credentials, secret values, or production/customer data.
- Record inaccessible, dynamic, generated, or environment-only areas.

Scaffold the complete static pack structure first:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" scaffold \
  --repo <repository-root> \
  --pack <pack-root>
```

The scaffold command populates the repository name and commit, creates all canonical static documents and dynamic output directories, and refuses to overwrite existing static documents unless `--force` is explicitly supplied. It never overwrites the claim ledger/audit or deletes dynamic behavior, contract, flow-model, or dependency-stub documents.

Then build the deterministic evidence index before manual tracing:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" index \
  --repo <repository-root> \
  --pack <pack-root>
```

Use file line counts, roles, symbols, and markers for endpoints, handlers, outbound HTTP, configuration, data access, state, events, failures, retry, tests, and assertions as search hints. Markers are not conclusions.

### 2. Discover candidates and build atomic claims

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

Process at most five behaviors per internal analysis batch. For every potential conclusion, open the exact source range before writing prose. Capture its canonical hash and ledger entry:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" show-evidence \
  --repo <repository-root> \
  --json \
  --source-kind implementation \
  --relation supports \
  --support-level direct \
  path/to/file.ext:start-end
```

Populate [assets/claim-ledger-template.json](assets/claim-ledger-template.json) at `.work/claim-ledger.json`. Keep each claim atomic and single-sentence. Split observed local mutation, opaque method invocation, external outcome, and business meaning into separate claims; never promote the latter three from a method name or template. For Confirmed/Inferred technical claims, choose non-generic verification tokens that occur in both the statement and the supporting source excerpt.

Validate the draft ledger, then re-read every cited range in a separate semantic audit and populate [assets/claim-audit-template.json](assets/claim-audit-template.json):

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-claims \
  --repo <repository-root> \
  --pack <pack-root> \
  --draft

python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" prepare-audit \
  --repo <repository-root> \
  --pack <pack-root>

python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-claims \
  --repo <repository-root> \
  --pack <pack-root>
```

Only audit verdict `Pass` may feed the manifest, flow models, or documents. Persist completed claim batches and continue automatically.

Before accepting the audit, replace `review.mode`, `author_id`, and `reviewer_id`. The reviewer must be a different agent/context from the claim author. Reviewer metadata is an accountability control, not proof by itself; retain the separate semantic-review pass.

### 3. Create the canonical inventory from passing claims

Populate the scaffolded [assets/knowledge-manifest-template.yaml](assets/knowledge-manifest-template.yaml), [assets/knowledge-map-template.md](assets/knowledge-map-template.md), and [assets/coverage-report-template.md](assets/coverage-report-template.md).

Assign stable IDs to behaviors, endpoints, data assets, fields, rules, dependencies, configurations, failures, proven outbound HTTP calls, and mappings. Use the ID conventions in the knowledge-pack policy; never use discovery-order numbering.

Treat the manifest as a relationship registry, never as evidence. Every entity must reference passing `claim_ids`, and each referenced claim must list that entity in `subject_ids`. The entity must also have a compatible claim type: for example, `FAIL-` requires `claim_type: failure`, an endpoint requires `endpoint-contract`, and a field mapping requires `mapping`. Build relationships from claims rather than turning behavior metadata into facts.

Bind machine-readable values, not only entity IDs: endpoint method/route, field path, configuration key, concrete dependency type, failure category, and mapping direction must occur in the bound Claim statement, verification tokens, or render terms. Keep `tech-pack/behavior-catalog.yaml` an exact manifest projection for repository/commit, analysis mode, behavior identity/status/paths/relationships/claims, and summary counts.

Replace every scaffold example, instruction, and `SCAFFOLD_ONLY` sentinel. For an empty entity set, use `section: []`. A statement such as `None observed` requires a scoped `absence` or `coverage-gap` claim; never infer global absence from an empty metadata list.

### 4. Build endpoint-owned API contracts

Complete the scaffolded [assets/endpoint-matrix-template.md](assets/endpoint-matrix-template.md) at `tech-pack/endpoints/endpoint-matrix.md`.

For every inbound endpoint, copy [assets/api-contract-document-template.md](assets/api-contract-document-template.md) to `tech-pack/endpoints/contracts/<endpoint-id>.api-contract.md`.

- Organize the contract for the API consumer: endpoint/security, request, response outcomes, errors, examples, and applicable semantics.
- Put L1 executable, L2 schema, and L3 shared/opaque evidence in the Evidence Appendix.
- Link the contract to the endpoint matrix and its primary Tech Behavior.
- Link every API entry behavior and shared behavior reached from an endpoint to each relevant endpoint and contract.
- Keep unobserved route, gateway, authorization, status, or error behavior `Unknown`; do not fill industry-standard defaults.
- Bind every contract row, paragraph, and example to passing Claim IDs. Contract frontmatter values such as method, route, operation ID, and status are facts too and must be covered by those claims.

### 5. Build the Tech Behavior view

Complete the scaffolded [assets/repository-overview-template.md](assets/repository-overview-template.md) and [assets/behavior-catalog-template.yaml](assets/behavior-catalog-template.yaml). Copy [assets/behavior-document-template.md](assets/behavior-document-template.md) for each behavior.

Before writing a Tech Behavior, copy [assets/tech-flow-model-template.json](assets/tech-flow-model-template.json) to `.work/flow-models/<behavior-id>.tech-flow.json`. Populate `summary_claim_ids`, every node's `claim_ids`, and every edge's `claim_ids` from passing claims. An edge needs a claim that proves its sequence/branch relationship; node claims alone are insufficient. Raw evidence on a Tech node must belong to those claims.

Write behaviors to `tech-pack/behaviors/<behavior-id>.md`. Render the Tech summary and Mermaid node labels from that Tech model. Bind every other factual paragraph, list item, table row, and example to passing claims with `<!-- claims: CLM-... -->` markers.

Keep the model at the canonical `.work/flow-models/<behavior-id>.tech-flow.json` path and render its exact edge source, target, and condition topology. Do not substitute another in-pack or out-of-pack model with the same node count.

Behaviors summarize repository-wide knowledge; do not duplicate full API contracts, field matrices, runtime matrices, dependency stubs, or failure definitions.

For `business` and `integration` behaviors, reserve `ba_behavior_document: ../../ba-pack/behaviors/<behavior-id>.md`. Technical behaviors use `null`.

### 6. Build the Data Pack

Complete the scaffolded documents based on:

- [assets/data-asset-catalog-template.md](assets/data-asset-catalog-template.md)
- [assets/data-lineage-template.md](assets/data-lineage-template.md)
- [assets/state-transition-matrix-template.md](assets/state-transition-matrix-template.md)

Account for every behaviorally relevant read, write, response, message, event, and external call. Distinguish local mutation, opaque persistence invocation, proven storage mutation, and supported business state transition as separate claims. Record transaction, idempotency, concurrency, rollback, and partial state only when directly supported.

### 7. Build the Field Pack

Complete the scaffolded documents based on:

- [assets/field-catalog-template.md](assets/field-catalog-template.md)
- [assets/validation-rule-matrix-template.md](assets/validation-rule-matrix-template.md)
- [assets/field-lineage-template.md](assets/field-lineage-template.md)
- [assets/external-http-mapping-matrix-template.md](assets/external-http-mapping-matrix-template.md)

Catalog boundary-visible or behaviorally significant fields, not every local variable. Give every manifest field a `boundary_kind` and `observation_kind`. A `.get("status")` or equivalent lookup on an opaque value is a `local-lookup` / `local-lookup-key`, not a Confirmed external response field. A Confirmed outbound-HTTP response field requires direct schema evidence. Separate executable validation from schema declaration. Use Field Lineage for internal API/domain/storage/event transformations.

In the Field Catalog, bind type/format, requiredness, nullability, ownership/meaning, source/default, and sensitivity cells to claims. When a cell has no supporting claim, write `Unknown` or `—`; do not fill standard-looking values for presentation completeness.

Only after a real outbound HTTP call is proven, register an `HTTP-` call and `MAP-` records in the manifest and external mapping matrix. Behavior documents reference those IDs.

### 8. Build Runtime, Dependency, and Failure Packs

Complete the scaffolded runtime, dependency-matrix, and failure documents; copy the dynamic dependency-stub template as needed:

- [assets/runtime-config-matrix-template.md](assets/runtime-config-matrix-template.md)
- [assets/dependency-matrix-template.md](assets/dependency-matrix-template.md)
- [assets/external-dependency-stub-template.md](assets/external-dependency-stub-template.md) for each material external dependency
- [assets/failure-taxonomy-template.md](assets/failure-taxonomy-template.md)

Record configuration definitions and reads, defaults, Lambda/trigger settings, behavior effects, and missing/invalid outcomes. Record secret names only.

Treat repository-external systems and unavailable behaviorally material components as black-box stubs. A client invocation proves the attempted call and observed arguments, not remote success, delivery, persistence, receipt, or downstream behavior.

Assign every material failure one `FAIL-` ID backed by a passing `claim_type: failure`. Behavior failure tables reference this global taxonomy. A locally returned `statusCode`/`code` literal remains a local result unless deployment or consumer-contract evidence establishes failure semantics. Distinguish exception, consumer-visible outcome, retry cause, configured retry, rollback, and partial success.

### 9. Derive the BA Pack

Generate BA views only from passing claims at the same commit. BA claim status must never be stronger than the underlying Tech claim. Complete the scaffolded repository-wide BA documents and copy the dynamic behavior template as needed:

- [assets/ba-overview-template.md](assets/ba-overview-template.md)
- [assets/ba-capability-map-template.md](assets/ba-capability-map-template.md)
- [assets/ba-business-data-lifecycle-template.md](assets/ba-business-data-lifecycle-template.md)
- [assets/ba-business-rule-catalog-template.md](assets/ba-business-rule-catalog-template.md)
- [assets/ba-business-exception-catalog-template.md](assets/ba-business-exception-catalog-template.md)
- [assets/ba-behavior-catalog-template.md](assets/ba-behavior-catalog-template.md)
- [assets/ba-behavior-document-template.md](assets/ba-behavior-document-template.md) for business/integration behaviors

For each business/integration behavior, copy [assets/ba-flow-model-template.json](assets/ba-flow-model-template.json) to `.work/flow-models/<behavior-id>.ba-flow.json`. Build it independently from passing business-meaning claims, and bind `summary_claim_ids`, every node's `claim_ids`, and every edge's relationship `claim_ids`. Do not infer actors, recipients, purpose, ownership, rules, or business state from component names or technical literals. Do not connect Unknown facts without a passing relationship claim. When business meaning is unavailable, produce a shorter or single-node BA flow with an audited `Unknown` claim rather than mirroring Tech.

Keep the BA model at that canonical path and render its exact edge topology and conditions; manifest, BA frontmatter, and resolved model path must agree.

If you create temporary generation code, use separate Tech and BA input types and separate render functions. The Tech renderer may load only the Tech model and the BA renderer only the BA model. Never use a common `meta["flow"]`/`meta["summary"]`, never fall back from a missing BA model to Tech content, and fail generation if the required perspective model is absent.

Render the BA summary and Mermaid labels only from the BA model. The Tech and BA models must remain separate files with different perspectives and node ID namespaces.

Use business capabilities, actors, information, decisions, outcomes, and visible exceptions. Do not include source citations, classes, methods, AWS identifiers, API field paths, configuration keys, or exception classes. Link to canonical Tech documents for details. Preserve evidence confidence.

### 10. Preview evidence and validate

Before drafting any citation, range-check it:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" show-evidence \
  --repo <repository-root> \
  path/to/file.ext:start-end
```

Run individual validation:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-tech --document <tech-behavior.md> --repo <repository-root>
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-contract --document <endpoint-contract.md> --repo <repository-root>
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-ba --document <ba-behavior.md> --repo <repository-root>
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-flow --tech <tech-behavior.md> --ba <ba-behavior.md> --repo <repository-root>
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-index --pack <pack-root> --repo <repository-root>
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-claims --pack <pack-root> --repo <repository-root>
```

For a business/integration Tech Behavior whose BA target is not created yet, pre-validate with `--allow-missing-ba`; never use that flag for final validation.

Finally validate the entire relationship graph, coverage, links, IDs, commit consistency, BA citation boundary, and source citation bounds:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" validate-pack \
  --pack <pack-root> \
  --repo <repository-root>
```

Rebuild the evidence index if any candidate repository file changed, appeared, or disappeared after indexing. Resolve all errors. Mention intentional warnings in delivery.

Validator success is necessary but not sufficient. Before delivery, read every linked Tech/BA Mermaid pair side by side and perform the semantic review required by the flow-perspective policy. Rewrite any BA flow that is still the Tech execution sequence with renamed nouns, even if lexical checks did not catch it (for example, because the two views use different languages). Also inspect every dynamic factual heading and keep each factual prose block to one claim-bound sentence; a valid Claim marker must never be used to carry an additional unsupported sentence.

## Delivery

Report pack path, repository, commit, evidence-index repository fingerprint (especially when commit is `unknown`), immutable runtime bundle fingerprint, analysis mode, coverage status, entity/claim counts, strongest confirmed findings, important unknown/conflicting/blocked areas, and validator results. Do not modify application source code unless separately requested.

## Quality bar

Before completion, verify:

- `knowledge-manifest.yaml` accounts for every discovered entity and relationship.
- Every repository assertion exists first as one atomic claim with current source-range hashes.
- Every `Confirmed`, `Inferred`, `Conflicting`, and `Unknown` claim satisfies its evidence invariant and has a passing semantic audit.
- Every manifest entity, factual Markdown block, flow summary, and flow node binds to passing claim IDs.
- No template example, evidence-index marker, manifest value, flow metadata, or temporary generator is used as evidence.
- No opaque `save`, client, queue, or publisher invocation is described as a completed external side effect without direct evidence.
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
- Every Tech Behavior renders a separate `technical` flow model; every BA Behavior renders a separate `business` flow model.
- Tech and BA summaries and Mermaid node labels are neither identical nor near-identical mechanical rewrites.
- BA flow nodes contain business semantics and no implementation terms; Tech flow nodes describe implementation execution.
- Final validation compares every linked Tech/BA pair; individual document validation alone is insufficient.
- All documents use the same repository commit and all relative links resolve.
- Coverage is never called complete while entry points, schemas, shared components, dynamic configuration, or repository signals remain undisposed.
- No credential, secret value, production payload, or customer data is reproduced.
- The final command completed through the immutable launcher, the post-command integrity check passed, and no release artifact or lock was changed during analysis.
