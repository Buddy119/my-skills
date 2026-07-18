---
name: eapi-behavior-reconstruction
description: "Reconstruct a human-readable repository knowledge pack from one complete EAPI microservice or AWS Lambda repository, starting with only a local path or a $eapi-behavior-reconstruction --repo invocation. Follow an expert reading workflow: index the repository, trace every executable behavior into working dossiers, synthesize repository-wide relationships and lifecycles, publish the Tech Pack, then independently reconstruct business Journeys and Scenarios for the BA Pack with many-to-many technical traceability. Use when Codex needs to reverse-engineer an undocumented repository, help developers and business analysts understand it, or prepare reliable inputs for later cross-service impact analysis."
---

# EAPI Repository Knowledge Reconstruction

Build the repository mental model before writing the final knowledge pack. Treat a behavior—not a file, class, method, or atomic claim—as the unit of understanding.

## Invocation interface

Treat this as a prompt convention for VS Code Copilot or another Skill-aware agent, not as a shell CLI.

Accept:

```text
$eapi-behavior-reconstruction \
  --repo <repository-path> \
  [--output <output-path>] \
  [--resume <analysis-state-path>]

$eapi-behavior-reconstruction --help
```

Support only:

- `--repo`: required except for `--help`; analyze the entire repository.
- `--output`: optional; default to `behavior-docs/<repository-name>/` in the working context.
- `--resume`: optional path to an existing `<output>/.work/analysis-state.yaml`; `--repo` remains required.
- `--help`: return this usage, option meanings, and examples without reading the repository, running scripts, or creating files.

Parse before starting analysis:

1. When any option is present, treat recognized option values as authoritative over surrounding prose.
2. Reject unknown options, duplicate options, missing values, `--mode`, and `--selector`. Show the short usage and do not read or write repository/output files.
3. Require quotes around values containing spaces. Resolve relative paths against the single active workspace root; when multiple roots make resolution ambiguous, request an absolute path without starting analysis.
4. If `--help` is present, show help and stop even when other arguments are present.
5. For `--resume`, require the state file to exist, derive the output root as the directory containing its `.work/` parent, and verify `analysis_mode: automatic`, repository identity, and source commit before reusing any artifact. When the repository is not a Git worktree and both commits are `unknown`, allow resume with an explicit warning.
6. When both `--resume` and `--output` are present, require their normalized output roots to match.
7. Reject a targeted state, repository mismatch, commit mismatch, or output mismatch. Preserve existing files and instruct the user to start a new full-repository run without `--resume`.

Examples:

```text
$eapi-behavior-reconstruction --repo "/repos/customer-eapi"

$eapi-behavior-reconstruction \
  --repo "/repos/customer-eapi" \
  --output "/knowledge/customer-eapi"

$eapi-behavior-reconstruction \
  --repo "/repos/customer-eapi" \
  --resume "/knowledge/customer-eapi/.work/analysis-state.yaml"
```

## Required input and natural-language compatibility

Require only the local path of one repository.

Accept an optional output directory. Analyze every discovered executable behavior; do not provide a single-behavior mode.

When no options are present, continue to accept a repository path and optional output path expressed in natural language. Discover the repository automatically. Do not ask the user to identify handlers, explain the repository, rank entry points, or select behaviors. If natural-language instructions request a single-behavior analysis, explain that this Skill analyzes the complete repository and do not silently narrow the scope.

## Non-negotiable operating rules

- Use the evidence index only to navigate. Never treat its markers or role hints as behavioral conclusions.
- Understand each behavior before drafting its Tech or BA document. Do not create a Claim Ledger or convert prose into atomic claim statements.
- Do not publish the formal pack until full-repository synthesis is complete.
- Let AI trace, interpret, synthesize, and write. Use scripts only for deterministic indexing, mechanical validation, and transactional stage control.
- Treat [assets/register-schema.json](assets/register-schema.json) as the single mechanical contract for `repository-register.md`. Do not rename, reorder, add, or remove Register table columns during an analysis. A Schema change is Skill development work and must update the Schema, Register template, Validator, Stage Executor, and tests together.
- Do not modify this Skill, its templates, references, or scripts during a repository analysis run. A writable Skill root is valid.
- Execute bundled Python scripts with the available `python3` and their absolute paths. They use only the Python standard library. If the stage executor or a required Validator cannot run, retain the Candidate and stop publication; do not patch the script, install dependencies, or advance lifecycle state manually.
- Do not access credentials, secret values, production customer data, live AWS resources, or repositories outside the supplied boundary.

## Load policies progressively

Read [references/evidence-policy.md](references/evidence-policy.md) completely before reading source code.

Read [references/stage-execution-policy.md](references/stage-execution-policy.md) completely before initializing or resuming an output.

Before tracing the first behavior, read [references/behavior-dossier-policy.md](references/behavior-dossier-policy.md) completely.

Before repository-wide synthesis, read [references/repository-synthesis-policy.md](references/repository-synthesis-policy.md) completely.

Before building the repository connection model, shared behavior model, or Repository Overview, read [references/repository-mental-model-publication-policy.md](references/repository-mental-model-publication-policy.md) completely.

Before publishing final documents, read [references/editorial-review-policy.md](references/editorial-review-policy.md) completely.

Load these only when applicable:

- After identifying a Java repository, read [references/java-semantic-analysis-policy.md](references/java-semantic-analysis-policy.md) completely before tracing Java symbols and calls.
- After finding an application route or any endpoint-related external-entry, environment-intent, or runtime evidence, read [references/endpoint-exposure-evidence-policy.md](references/endpoint-exposure-evidence-policy.md) before correlating endpoint candidates.
- For a confirmed application API route, read [references/api-contract-policy.md](references/api-contract-policy.md).
- After proving an executable outbound HTTP call, read [references/field-mapping-policy.md](references/field-mapping-policy.md).
- After observing any executable external service, database, event, storage, or runtime-provided boundary, read [references/external-dependency-synthesis-policy.md](references/external-dependency-synthesis-policy.md) before dependency reconciliation or publication.
- After recording any material failure path, read [references/failure-taxonomy-synthesis-policy.md](references/failure-taxonomy-synthesis-policy.md) before failure-pattern reconciliation or publication.
- Before creating the independent Business Model or any BA-facing output, read [references/ba-pack-policy.md](references/ba-pack-policy.md).

## Output layout

Use this layout for every analysis:

```text
behavior-docs/<repository-name>/
├── .work/
│   ├── evidence-index.json
│   ├── analysis-state.yaml
│   ├── behavior-catalog.yaml
│   ├── behavior-dossiers/
│   ├── repository-register.md
│   ├── repository-synthesis.md
│   ├── business-model.md
│   └── execution/
│       ├── transactions/
│       ├── receipts/
│       └── archive/
├── tech-pack/
│   ├── repository-overview.md
│   ├── behavior-catalog.yaml
│   ├── endpoint-matrix.md                  # when any endpoint-layer evidence exists
│   ├── behaviors/
│   ├── contracts/
│   ├── data-lifecycle.md                   # only when data/state behavior exists
│   ├── field-validation-and-mapping.md     # only when field rules or HTTP mappings exist
│   ├── runtime-config-matrix.md            # only when config changes behavior
│   ├── external-dependency-contracts.md    # only when external boundaries exist
│   └── failure-taxonomy.md                 # only when material failures exist
└── ba-pack/
    ├── business-overview.md
    ├── business-catalog.md
    ├── journeys/
    └── scenarios/
```

Do not create empty reference documents to satisfy this tree. Record absent or inapplicable modules in `repository-overview.md` as `Not observed` or `Not applicable`.

## Workflow

### 1. Establish the boundary and analysis state

1. Confirm the repository root and record `git rev-parse HEAD` when available.
2. Exclude generated artifacts, vendored dependencies, build output, coverage output, and lockfiles unless they define runtime behavior.
3. For a new output, run `stage_executor.py init --repo <repository-root> --output <output-dir> --json`. Do not copy or edit lifecycle templates manually.
4. For `--resume`, run `stage_executor.py resume --repo <repository-root> --state <analysis-state-path> --json`. If its commit differs, preserve the existing output and initialize a sibling output directory suffixed with the new short commit; never reuse old dossiers as current facts.
5. Run `stage_executor.py status --output <output-dir> --json`, then begin the reported stage. Treat its returned Candidate as the only writable output root for that stage.

When resuming a same-commit analysis whose Register has no supported `register_schema_version`, preserve Dossiers and raw evidence but resume from `synthesis`. Archive and rebuild the Register through the stage transaction using the current template. Do not guess legacy columns by position or silently convert them into the current model.

When resuming a same-commit analysis whose register lacks both `Endpoint evidence records` and `Endpoint reconciliation`, keep completed behavior dossiers but treat endpoint inventory and synthesis as stale. Rebuild the layered endpoint register, reset synthesis/publication to pending, regenerate affected formal documents, and do not publish the legacy flattened endpoint conclusions.

When resuming a same-commit analysis whose Endpoint reconciliation lacks `Operation Role` or `Publication Disposition`, preserve completed dossiers and raw endpoint evidence but treat endpoint reconciliation, repository synthesis, and Endpoint Matrix as stale. Reclassify operation roles, rebuild route-group associations and publication dispositions, and republish the Matrix. Preserve application contracts whose endpoint identity and caller-visible contract remain unchanged, then revalidate their Matrix links.

When resuming a same-commit analysis whose published API Contracts still use the legacy `Exposure and reachability` plus fixed input/output L1/L2/L3 body structure, keep the completed dossiers, register, synthesis, endpoint identities, and catalog. Treat only those formal Contracts and their related field-document index as stale, then republish them with the consumer-first format. Do not retrace behaviors unless the source commit changed or the working artifacts cannot support the caller-visible contract.

When resuming a same-commit analysis whose register still combines outbound Call identity and field Mapping in `Proven outbound HTTP calls and mappings`, preserve dossiers and cited call/mapping evidence but treat outbound-operation reconciliation, `field-validation-and-mapping.md`, and Tech Behaviors that reference those calls as stale. Split the evidence into Remote Operation, Executable Usage, and Field Mapping records. Preserve API Contracts, Endpoint Matrix, BA Pack, and unrelated behaviors. When several legacy Call IDs prove the same Method, Logical Target, and Client Operation, retain the lexicographically first ID as canonical and record the others as aliases; keep unresolved identities separate.

When resuming a same-commit analysis whose register still uses the flattened `External dependencies` table or lacks `Dependency contract records`, preserve dossiers and all cited dependency observations. Convert each legacy row into a stable `DEP-OBS-nnn` observation, then rebuild Dependency Contract and Operation reconciliation, the dependency section of repository synthesis, and `external-dependency-contracts.md`. Keep identities unresolved when the old evidence cannot prove grouping; do not retrace unrelated Behaviors or regenerate Endpoint, API Contract, or Field Mapping documents.

When resuming a same-commit analysis whose Failure observations lack stable IDs/reconciliation or whose register lacks `Failure pattern reconciliation`, preserve dossiers and every cited failure path. Assign stable `FO-nnn` observations, rebuild Failure Patterns, the failure section of repository synthesis, and `failure-taxonomy.md`. Republish only affected repository summaries, Tech links, and business-visible BA exception text. Do not infer retry, rollback, compensation, or state outcomes missing from the retained evidence.

When resuming a same-commit analysis whose synthesis lacks `Repository connection model` or `Shared behavior model`, or whose Repository Overview still reduces connections or shared behavior to a name list, preserve completed dossiers, register reconciliation, and existing Endpoint, API, Field, Lifecycle, Config, Dependency, and Failure documents. Rebuild only those synthesis models and `tech-pack/repository-overview.md`. Update BA documents only when the rebuilt models change a business-visible participant, interaction, shared business rule, outcome, or limitation.

When resuming a same-commit analysis whose state lacks `business_model_status`, whose BA Pack still uses `ba-pack/behaviors/`, shares Tech `behavior_id` values, or whose Tech documents use `ba_behavior_document`, preserve dossiers, the register, repository synthesis, and all established Tech facts. Let the resume audit select `business-model`; the transaction will archive legacy BA files under `.work/legacy-ba-pack/`, create a new independent Business Model, and rebuild the complete BA Pack as Journeys and Scenarios. Replace Tech and catalog BA links with `ba_scenarios` lists and update Repository Overview. Do not retrace understood Behaviors, generate old-path redirect stubs, or reuse legacy BA prose as business-model facts.

Keep only progress and paths in `analysis-state.yaml`. Store behavioral knowledge in dossiers and the repository register. Never edit lifecycle fields directly; only the stage executor may update them.

### 2. Build a navigation index and inventory entry points

Begin `inventory` through the stage executor and use its Candidate root for every path below.

Run:

```bash
python3 <skill-root>/scripts/build_evidence_index.py \
  --repo <repository-root> \
  --output <output-dir>/.work/evidence-index.json
```

Use line counts, role hints, symbols, endpoint markers, outbound HTTP markers, tests, and assertions to plan reads. Confirm every important marker by reading executable code.

Identify a Java project when the repository contains Java source or a Java build model such as Maven or Gradle. For Java repositories:

1. Load the Java semantic-analysis policy.
2. Check whether the current agent environment already exposes a usable Java language service (LSP) and whether it imported the relevant project/module successfully.
3. Record the Java project model and semantic-navigation status once in `repository-register.md`.
4. Use available semantic navigation before text matching to establish source symbols and candidate call relationships. Do not install an extension, JDK, build dependency, or language server, and do not modify the repository to make semantic tooling work.

Use `rg` and `rg --files` to find:

- Runtimes, frameworks, build files, and module boundaries.
- Lambda, API, queue, event, stream, schedule, and Step Functions entry points.
- IaC and runtime wiring.
- Services, repositories, outbound clients, models, schemas, tests, and configuration.

When API-related evidence exists, inventory these sources independently before forming endpoint identities:

- Executable application routes and handlers.
- External boundary declarations in proxy, ingress, gateway, routing, or infrastructure definitions.
- Environment-specific deployment intent and bindings.
- Repository-local or user-supplied sanitized runtime observations.

Add each observation to `Endpoint evidence records` in the repository register. Do not let an application route prove exposure, let a declaration prove deployment, or correlate layers from method/route similarity alone. Do not make reader-facing publication decisions during inventory; a confirmed observation may later be summarized rather than promoted to a Matrix row. An external-only candidate is not an executable behavior and must not be added to the behavior catalog.

For Java executable call relationships, use `rg` as discovery support and as the documented fallback when semantic navigation is unavailable or incomplete. A filename, method-name match, import, or subagent observation identifies a candidate; it does not by itself establish the called symbol or runtime implementation.

Group trigger, handler, controller, service, and orchestration code into one behavior when they implement one end-to-end flow. Catalog framework glue, health checks, migrations, and deployment-only utilities as technical, duplicate, or excluded rather than promoting them to business behaviors.

Create stable behavior IDs and catalog every executable application or framework entry point. Keep external-only and configuration-only endpoint candidates out of the behavior catalog and in the endpoint register. Mirror active behaviors in `analysis-state.yaml` with status `discovered`.

Commit the inventory transaction only after the evidence index is valid and every discovered entry point has a catalog disposition. Then begin `tracing` and continue in its new Candidate.

### 3. Trace behaviors into working dossiers

Order work by signal:

1. Application API routes and synchronous request handlers.
2. Event, queue, stream, and scheduled consumers.
3. Shared orchestration referenced by multiple entry points.
4. Technical behaviors.

Process at most five behaviors per internal batch. For each behavior:

1. Use `stage_executor.py mark-behavior` to set its Candidate state to `tracing`; do not edit lifecycle fields directly.
2. Copy [assets/behavior-dossier-template.md](assets/behavior-dossier-template.md) to `.work/behavior-dossiers/<behavior-id>.md`.
3. For a Java behavior, complete the dossier's `Semantic symbol and call trace` before relying on the apparent call chain. Use exact symbols, definitions, call hierarchy, references, type hierarchy, overrides, and implementations when the environment exposes them. Then confirm critical edges and runtime implementation selection in source, DI/configuration, annotations, and tests. If semantic tooling is unavailable or incomplete, perform and record the policy's degraded investigation instead.
4. For an API behavior, complete the dossier's `Endpoint exposure evidence` section and add every direct layer observation to the register without prematurely correlating it.
5. Follow the executable path from trigger through input handling, validation, decisions, data access, external boundaries, outputs, and material failures.
6. Inspect tests alongside implementation. When relevant tests exist, record one or two concrete assertions that prove a core outcome, prioritizing a failure path. Distinguish test-only references from production callers.
7. Inspect IaC and configuration for trigger filters, timeouts, retries, DLQs, permissions, resources, and behavior-changing environment values.
8. Stop at repository boundaries and describe remote internals as unknown.
9. Update the relevant sections of `.work/repository-register.md` while the evidence is in context. Record each executable external boundary as a Dependency Observation and each material failure path as a Failure Observation; do not create reader-facing Dependency Contracts or Failure Patterns while tracing one Behavior.
10. Apply the behavior-understanding gate from the dossier policy. After main-agent review, use `mark-behavior` to record `understood`; otherwise continue tracing or record `blocked` with the exact limitation. A subagent may deliver a dossier file but may not change global state or commit the stage.

Do not write formal Tech documents, the Business Model, Journeys, or Scenarios during this phase.

Commit `tracing` only when status reports no undiscovered or tracing Behavior. Natural-language progress reports do not satisfy this gate.

### 4. Record external HTTP mappings only when proven

First locate every executable outbound HTTP/HTTPS invocation. Record it as an Executable Usage with its call site, Behavior ID, invocation condition, configuration, status, and evidence.

Reconcile usages into Remote Operations only when Method, Logical Target, and Client Operation all match. Assign one Call ID such as `HTTP-001` to the operation and one Usage ID such as `HTTP-001-U01` to each executable call site. Do not merge from Method/Target similarity alone or split one logical operation solely because environment-provided target values differ.

Only then record:

- EAPI fields mapped to the external request path, query, header, or body.
- External response fields mapped back into EAPI fields when consumed.

Give every mapping a stable `FM-nnn` ID, its Call ID, and either the applicable Usage IDs or `all` when it applies identically to every registered usage. Do not repeat Method, Target, Client Operation, or Behavior in each mapping row.

Do not classify inbound API contracts, event payloads, queue messages, persistence mappings, or internal DTO/domain conversions as cross-boundary HTTP field mappings.

### 5. Synthesize the repository mental model

Begin only after every active behavior is `understood` or explicitly `blocked`, every executable entry point has a catalog disposition, and endpoint evidence candidates are registered.

1. Begin the `synthesis` transaction and work only in its Candidate.
2. Reconcile observations inside the existing versioned Register tables. Preserve `register_schema_version: "1"` and every table header exactly as defined by `assets/register-schema.json`; change rows, not the mechanical contract.
3. Read all behavior dossiers and the repository register.
4. Copy [assets/repository-synthesis-template.md](assets/repository-synthesis-template.md) to `.work/repository-synthesis.md`.
5. Reconcile behavior boundaries, business objects, state transitions, data lifecycles, dependencies, configuration effects, and failure categories.
6. Reconcile endpoint evidence only through explicit target, binding, mapping, or rewrite evidence. Populate `Endpoint reconciliation` with separate layer statuses and derive external reachability without upgrading missing layers.
7. Classify each reconciled endpoint record as `application-endpoint`, `meaningful-external-exposure`, `protocol-support`, or `unresolved`; record `publish`, `summarize`, or `publish-as-exception`, the classification basis, and any normalized route-group association. Ordinary protocol support requires proof that it has no application handler, business payload, state access, or business dependency call. Method or mock/static integration alone is insufficient.
8. Associate a shared protocol-support operation with one normalized route group instead of copying it under every application method. Summarize ordinary support records; publish orphaned, conflicting, environment-inconsistent, and unresolved records as exceptions.
9. Reconcile outbound HTTP observations into Remote Operations, Executable Usages, and Field Mappings. Merge Call IDs only from a complete Method + Logical Target + Client Operation match; preserve usage-specific conditions and transformations.
10. Reconcile every `DEP-OBS-nnn` into a logical `DEP-nnn` Dependency or mark it `Unresolved`. Group only with executable binding, configuration, DI/wiring, or resource-identity evidence. Create `DEP-nnn-OPnn` Operations beneath each Dependency, link existing HTTP Call IDs instead of copying mappings, record dependent capabilities, and classify availability impact as `Required`, `Degradable`, `Optional`, or `Unknown` at Operation or Behavior usage level.
11. Reconcile every `FO-nnn` into a `FAIL-nnn` Pattern or mark it `Unresolved`. Merge only when trigger/source, propagation, caller visibility, state outcome, retry safety, and recovery semantics are materially equivalent. Record recurring behaviors, dependency relationships, recovery gaps, and evidence-supported `High`, `Medium`, `Low`, or `Unknown` risk attention.
12. Merge, split, or rename behaviors when the combined evidence requires it; update the working catalog, state, dossiers, and register together.
13. Build the `Repository connection model` from reconciled endpoint, dependency, lifecycle, configuration, and failure models. Group only when participant/resource, direction, boundary type, interaction role, and configuration-selection semantics are equivalent. Include only executable crossings or explicit trigger bindings; a class, host, resource, or configuration name alone is not a connection.
14. Build the `Shared behavior model`. Include a rule or behavior-shaping component only when the same proven source is reused by at least two Behaviors or independent entry paths and materially changes validation, decisions, authorization, transformation, state, boundaries, output, error handling, or recovery. Preserve behavior-specific differences and overrides. Exclude logging, ordinary monitoring, generated code, framework glue, simple wrappers, and single-Behavior helpers.
15. Explain blocked coverage, conflicts, and unknowns instead of filling gaps with intent.
16. Commit with `--semantic-result complete` only after every Dependency and Failure Observation is reconciled or explicitly unresolved, the repository-wide dependency and failure models are complete, and the Connection and Shared Behavior models have been reviewed. The executor runs the mechanical publishability gate before promotion.

### 6. Publish the Tech Pack

Begin `tech-publication` and write in its Candidate for a developer who needs to understand the repository, not for an auditor trying to count claims.

1. Build each Tech Behavior from its completed dossier. Use [assets/behavior-document-template.md](assets/behavior-document-template.md).
2. Build `repository-overview.md` from the completed Connection and Shared Behavior models in `repository-synthesis.md` using [assets/repository-overview-template.md](assets/repository-overview-template.md), not directly from the evidence index, dependency names, configuration names, or file roles. Publish one grouped system-context Mermaid diagram and a compact connection matrix; then publish separate Shared Rules and Shared Behavior-shaping Components tables. Link to detailed models instead of copying their Operation, Mapping, Lifecycle, Config, or Failure tables. Leave BA Scenario links empty until the independent Business Model is complete.
3. Copy the reconciled working catalog to `tech-pack/behavior-catalog.yaml` and replace working dossier paths with final document links.
4. Generate applicable repository references from the corresponding reconciled register records and repository-synthesis models:
   - [assets/endpoint-matrix-template.md](assets/endpoint-matrix-template.md)
   - [assets/data-lifecycle-template.md](assets/data-lifecycle-template.md)
   - [assets/field-validation-and-mapping-template.md](assets/field-validation-and-mapping-template.md)
   - [assets/runtime-config-matrix-template.md](assets/runtime-config-matrix-template.md)
   - [assets/external-dependency-contracts-template.md](assets/external-dependency-contracts-template.md)
   - [assets/failure-taxonomy-template.md](assets/failure-taxonomy-template.md)
5. Build the outbound portion of `field-validation-and-mapping.md` as one index row and one anchored section per Remote Operation. Put call identity once in Call Overview, list multiple or materially different Executable Usages, and nest request/response mappings under that Call. Do not copy the register tables or repeat call metadata in mapping rows.
6. In each affected Tech Behavior, add one call-summary row per Remote Operation, link its Call ID directly to the operation anchor, and list only that behavior's Usage IDs. Do not create one behavior row per Mapping ID.
7. Build `external-dependency-contracts.md` as one landscape row and one anchored section per `DEP-nnn`. Nest Operations beneath their Dependency, explain role, shared capabilities, availability, degradation, state implications, and remote Unknowns, and link Field Mapping and Failure details instead of repeating them. Never publish the Dependency Observation table.
8. Build `failure-taxonomy.md` as one index row and one anchored section per `FAIL-nnn`. Lead with repository-wide High and Unknown attention, then explain trigger, caller visibility, state outcome, retry/recovery, and cross-Behavior variations. Link API errors, lifecycle changes, Dependency Contracts, and Tech flows instead of repeating them. Never publish the Failure Observation table.
9. Link each behavior only to relevant repository references. Use stable `dependency_id` entries and `failure_patterns` IDs in affected Tech frontmatter, with one concise usage-specific row linking each repository-level anchor. Do not duplicate detailed contracts or repository-wide tables inside every behavior.

Keep prose natural. Attach evidence to a paragraph, meaningful rule, flow explanation, or table row; do not label every sentence.

Commit `tech-publication` only after its Behavior and repository-document gates pass.

### 7. Publish endpoint evidence and application API contracts

Begin `api-contract-publication` and use its Candidate.

First generate `endpoint-matrix.md` whenever the register contains evidence from any endpoint layer. Treat it as a reader-facing projection rather than a dump of every register row:

- Publish every reconciled `application-endpoint` and `meaningful-external-exposure`.
- Publish every `unresolved` record and every orphaned, conflicting, or environment-inconsistent protocol-support record as an exception.
- Summarize ordinary `protocol-support` declarations in one compact section with raw declaration count, related route groups, exception count, source/scope summary, and one link to the complete repository register.
- Do not publish one Matrix row per ordinary preflight/CORS declaration. Do not hide a real handler, business response, health/version capability, authentication/query behavior, state access, or dependency-backed operation merely because it uses OPTIONS or mock/static integration.
- Keep all five endpoint-layer statuses independent from operation role and publication disposition.

For every confirmed application endpoint:

1. Generate a stable endpoint ID from repository, lower-case method, and normalized route. Replace slashes and route punctuation with hyphens; retain parameter names. Add a stable disambiguating suffix only for a collision.
2. Copy [assets/api-contract-document-template.md](assets/api-contract-document-template.md) to `tech-pack/contracts/<endpoint-id>.api-contract.md`.
3. Use L1 executable, L2 schema-level, and L3 shared/opaque evidence to reconcile fields before writing, but publish one caller-facing request and response view rather than fixed evidence-layer sections.
4. Lead with purpose, invocation, authentication, caller inputs, validation, responses, supported examples, confidence, and material limitations. Omit empty input locations and optional sections.
5. Keep `method` and `route` as application identities. Show only a concise external-path/reachability summary and the Endpoint Matrix link; do not copy the five-layer table into the Contract.
6. Keep internal flow in Tech Behavior, detailed endpoint exposure in Endpoint Matrix, outbound HTTP mappings in Field Validation and Mapping, downstream boundaries in External Dependency Contracts, and internal/repository-wide failures in Failure Taxonomy.
7. Use compact `[E#]` markers and grouped Source notes. Do not expose a repeated Evidence column or one citation per sentence when a meaningful row or paragraph can share support.
8. Generate request and response examples only when code, schema, or tests support their fields, statuses, and wire shapes. Omit unsafe examples and record the caller impact instead of inventing values or serialization.
9. Set the contract's `behavior_document` backlink.
10. Add every related application endpoint to the Tech Behavior's `api_contracts` list and visible `API contracts` links. Use `api_contracts: []` for non-API behaviors.

Do not generate a contract or behavior for an external-only, configuration-only, or ordinary protocol-support record. Multiple external entries mapped to one application endpoint share its one application contract.

Validate each endpoint contract and its backlink before continuing.

Commit this stage after the executor validates application Contracts and Matrix links. When the repository has no application API Contract, commit it with `--skip` and an evidence-based reason; do not create empty Contracts.

### 8. Build an independent Business Model and publish the BA Pack

Begin only after repository synthesis and the related Tech documents are complete.

1. Begin `business-model`, read the BA Pack policy, and copy [assets/business-model-template.md](assets/business-model-template.md) to `.work/business-model.md` in its Candidate.
2. Reconstruct Capabilities, actors, business objects, Journeys, Scenarios, shared business rules, business-visible exceptions, and Journey–Scenario relationships across all completed Tech facts. Do not iterate through Tech Behaviors and generate one BA document per row.
3. Account for every active Tech Behavior in the Business Model as `scenario-support`, `business-visible-support`, `no-business-visible-role`, or `unknown`. An Entry Point, technical branch, validation, Dependency, or exception does not automatically become a Scenario, business decision, rule, participant, or exception.
4. Assign semantic Journey and Scenario IDs from supported business goals and contexts. Merge and split by actor goal, business context, decision meaning, business-object lifecycle, and visible outcome—not by endpoint, handler, event, or Behavior identity.
5. Review the Business Model semantically and commit `business-model` with `--semantic-result complete`, `partial`, or `blocked`. Only the executor updates `business_model_status`.
6. When status is `complete` or `partial`, begin `ba-publication` and build `business-overview.md` with [assets/ba-overview-template.md](assets/ba-overview-template.md), `business-catalog.md` with [assets/ba-business-catalog-template.md](assets/ba-business-catalog-template.md), Journey documents with [assets/ba-journey-document-template.md](assets/ba-journey-document-template.md), and Scenario documents with [assets/ba-scenario-document-template.md](assets/ba-scenario-document-template.md).
7. Maintain direct many-to-many Scenario/Tech traceability: each Scenario lists all supporting Tech Behaviors; each supporting Tech Behavior and catalog entry lists the Scenario in `ba_scenarios`. A Journey links its Scenarios and their supporting Tech Behaviors, but Tech documents do not maintain Journey backlinks. `ba_scenarios: []` is valid for every Behavior category.
8. Preserve evidence confidence without exposing raw source citations. Include only business-visible participants, interactions, shared rules, degradation, partial success, state risk, and recovery limitations. Do not copy the technical context diagram, connection matrix, internal components, Dependency tables, Failure tables, or Tech flows.
9. When status is `blocked`, begin `ba-publication` only to commit it with `--skip` and the blocker reason; omit invented Journey and Scenario documents and keep the supported Tech Pack complete.

Commit `ba-publication` only after the executor verifies Journey, Scenario, backlink, and Pack-link mechanics.

### 9. Review in three passes

Begin `finalization` and review its Candidate snapshot.

Apply the editorial policy in this order:

1. Mechanical review: state, structure, links, endpoint identity, commit, placeholders, and citation bounds.
2. Fact review: sample important rules, state changes, mappings, configuration effects, and failure paths back to source.
3. Reader review: confirm a developer can retell Tech behavior and a BA can retell independent Journeys, Scenarios, object changes, outcomes, and exceptions; verify that mapping count does not multiply Call, Target, or Behavior metadata in the Field Pack.

During reader review, also verify that each external Dependency appears once regardless of the number of Behaviors or Operations, and that each Failure Pattern explains a repository-level trigger-to-visible-result-and-state story instead of presenting an observation inventory.

For Repository Overview, verify that the context diagram and connection matrix make direction, boundary, interaction role, exchanged concepts, supported Behaviors, configuration selection, criticality, and failure/state impact understandable without the register. Confirm that same-role Operations are not repeated as connections, materially different roles are not collapsed, shared items really affect at least two Behavior paths, ordinary utilities are excluded, and every deep-dive destination is reachable with one link.

For the BA Pack, verify that Journey and Scenario counts arise from business goals, contexts, decisions, object lifecycles, and outcomes rather than Tech Behavior count. Sample one Scenario-to-Tech many-to-many mapping, one unmapped Tech Behavior disposition, one technical branch that was not promoted to a business decision, and one business-visible exception. Confirm that BA documents do not reproduce the Tech call chain with renamed nodes.

The finalization commit runs all applicable document, state, link, citation, and placeholder Validators and records their complete output plus Register domain status in the Receipt. A result with any Primary Error or skipped necessary validation group is incomplete and cannot be reported as全面验证通过. Treat warnings as review prompts, not prose-generation targets. Resolve mechanical errors in the Candidate without rewriting readable text into claim statements.

### 10. Deliver

Commit `finalization`. Deliver only when `status --json` reports `current_stage: completed`, `stage_status: committed`, and a successful finalization Receipt. Report:

- Repository path and commit.
- Full-repository coverage and any blocked areas.
- Pack directories and generated documents.
- Behavior, Journey, Scenario, and endpoint counts, separating application endpoints, meaningful external exposures, aggregated protocol-support declarations, published exceptions, and blocked coverage.
- Important confirmed findings, unknowns, conflicts, and limitations.
- Mechanical validation results and any intentional warnings.

Do not modify application source code unless the user separately requests an implementation change.

## Completion standard

Before delivering, confirm:

- `.work` shows inventory, per-behavior understanding, repository registration, repository synthesis, and independent business modeling in that order.
- The Register declares the supported Schema version, all table headers match the bundled Schema, and the final Receipt reports `valid` HTTP, Dependency, and Failure domains with zero skipped necessary validation groups.
- Every final behavior can be retold as a coherent success-and-failure story.
- Tests contribute assertion-level evidence when available.
- Data and state changes connect across behaviors where evidence permits.
- Every confirmed application API route has its own contract; meaningful external-only records and endpoint exceptions appear only in Endpoint Matrix, while ordinary protocol-support records remain fully evidenced in the register and appear as a compact Matrix summary.
- Every API Contract leads with caller purpose, invocation, inputs, validation, responses, confidence, and material limitations; it uses supported examples when available and links instead of copying internal flow, five-layer exposure, outbound mappings, or failure-taxonomy detail.
- Application route, external entry, environment intent, runtime deployment, and external reachability remain separate, with no single layer proving another.
- Cross-boundary field mappings exist only for proven outbound HTTP calls.
- Outbound HTTP knowledge is separated into Remote Operations, Executable Usages, and Field Mappings; each Remote Operation has one final anchored section, while usage-specific conditions and mappings remain visible.
- Runtime configuration appears only when it changes behavior.
- External systems are reconciled into Dependency Contracts with distinct Operations, dependent capabilities, availability impact, and explicit remote Unknowns; the formal document does not repeat one dependency per Behavior or copy the observation register.
- Failure observations are reconciled into repository-wide Patterns with caller visibility, state outcome, retry safety, recovery, and evidence-supported risk attention; the formal taxonomy does not copy one row per dossier failure.
- Repository Overview contains a synthesis-backed context diagram and connection matrix rather than a list of external names; logical connections preserve direction, boundary, role, exchanged concepts, configuration variants, criticality, failure/state impact, and one-click deep links without repeating every Operation.
- Shared Rules and Shared Behavior-shaping Components include only proven cross-Behavior items that materially affect observable behavior, preserve differences and overrides, and exclude ordinary tools and framework glue.
- Every Java behavior has a completed semantic symbol/call trace or an explicit degraded/unavailable investigation; unresolved callers, dynamic edges, and implementation bindings remain qualified.
- `.work/business-model.md` accounts for every active Tech Behavior without using Behavior count as a Journey or Scenario target.
- Journey and Scenario IDs are independent from Tech Behavior IDs; Scenario/Tech traceability is many-to-many and every declared relationship has a backlink.
- BA Journeys explain business goals, stages, object progression, handoffs, outcomes, and repository boundaries; BA Scenarios explain supported business situations, decisions, information, outcomes, and exceptions.
- Technical triggers, branches, validations, Dependencies, and exceptions are not promoted to business concepts without supported business-visible meaning.
- BA flows are independently modeled business views, not copied or mechanically renamed Tech call chains.
- The final prose reads as documentation, not as a Claim Ledger or validator transcript.
