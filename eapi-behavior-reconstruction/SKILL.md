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
- Let AI trace, interpret, reconcile meaning, model business behavior, and write. Use scripts for byte copying, deterministic indexing, registered schema transforms, stable structural IDs, explicit link rewrites, manifests, validation, archives, and transactional stage control. Never exchange these responsibilities.
- Treat [assets/register-schema.json](assets/register-schema.json) as the single mechanical contract for `repository-register.md`. Do not rename, reorder, add, or remove Register table columns during an analysis. A Schema change is Skill development work and must update the Schema, Register template, Validator, Stage Executor, and tests together.
- Treat [assets/lifecycle-model-schema.json](assets/lifecycle-model-schema.json) as the typed lifecycle and diagram-projection contract. Scripts may validate declared Object, State, Action, Transition, and link identities; they must not infer semantic state from words or call order.
- Treat [assets/artifact-schema.json](assets/artifact-schema.json) as the version registry for every long-lived working, Tech, BA, and operational Artifact. Do not infer a document generation from headings, directory names, old field names, or prose.
- Treat [assets/migration-transform-registry.json](assets/migration-transform-registry.json) as the only executable migration-transform registry. A mechanical transform requires an exact source schema, target schema, registered handler, and test fixture. An unknown or unversioned schema is archived and rebuilt; it is never guessed or AI-adopted inside Migration.
- Treat [assets/publication-maturity-rules.json](assets/publication-maturity-rules.json) as the mechanical contract for execution-stage residue in Reader artifacts. Explicit workflow phrases may block publication; ambiguous words remain review prompts and never become business-semantic decisions in Python.
- Treat [assets/reader-projection-schema.json](assets/reader-projection-schema.json) as the cross-stage Reader Projection contract. The executor may refresh stable identities, paths, backlinks, navigation cells, and deterministic counts; AI must review and write every affected semantic summary.
- Treat [assets/reader-presentation-schema.json](assets/reader-presentation-schema.json) as the Reader status/evidence presentation contract. Working Artifacts keep complete evidence states; Reader tables omit generic Status/Evidence columns, treat Confirmed as the baseline, preserve only exceptional qualifiers, and group Tech evidence in Source Notes.
- Treat [assets/reader-priority-schema.json](assets/reader-priority-schema.json) as the lightweight progressive-disclosure contract. It controls only the leading Reader sections and their order; it never decides Capability identity, Variant meaning, risk priority, prose length, or Schema completeness.
- Validate every local Markdown deep link against a real explicit HTML anchor or a deterministically parsed GFM heading slug. Use explicit stable anchors for Endpoint, `HTTP-*`, `DEP-*`, and `FAIL-*` identities; use heading fragments only for simple stable editorial sections. Never accept file existence alone as proof that `#fragment` is clickable.
- Do not modify this Skill, its templates, references, or scripts during a repository analysis run. A writable Skill root is valid.
- Execute bundled Python scripts with the available `python3` and their absolute paths. They use only the Python standard library. If the stage executor or a required Validator cannot run, retain the Candidate and stop publication; do not patch the script, install dependencies, or advance lifecycle state manually.
- Do not access credentials, secret values, production customer data, live AWS resources, or repositories outside the supplied boundary.

## Load policies progressively

Read [references/evidence-policy.md](references/evidence-policy.md) completely before reading source code.

Read [references/stage-execution-policy.md](references/stage-execution-policy.md) completely before initializing or resuming an output.

For `--resume`, also read [references/artifact-migration-policy.md](references/artifact-migration-policy.md) completely before running the Resume Audit.

Before tracing the first behavior, read [references/behavior-dossier-policy.md](references/behavior-dossier-policy.md) completely.

Before repository-wide synthesis, read [references/repository-synthesis-policy.md](references/repository-synthesis-policy.md) completely.

After observing any object read, write, condition, persistence, deletion, event emission, or possible state change, read [references/lifecycle-model-policy.md](references/lifecycle-model-policy.md) completely before classifying lifecycle records.

Before building the repository connection model, shared behavior model, or Repository Overview, read [references/repository-mental-model-publication-policy.md](references/repository-mental-model-publication-policy.md) completely.

Before publishing final documents, read [references/editorial-review-policy.md](references/editorial-review-policy.md) completely.

Before writing any Tech or BA Reader Artifact, read [references/reader-evidence-presentation-policy.md](references/reader-evidence-presentation-policy.md) completely.

Before writing Repository Overview, Tech Behaviors, or API Contracts, read [references/reader-priority-publication-policy.md](references/reader-priority-publication-policy.md) completely.

Before beginning `finalization`, read [references/finalization-review-policy.md](references/finalization-review-policy.md) completely.

Before materializing API Contracts or BA Journeys/Scenarios, read [references/reader-projection-policy.md](references/reader-projection-policy.md) completely.

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
│   ├── artifact-manifest.json
│   ├── migration-plan.yaml                 # only when a version migration is required
│   ├── legacy-artifacts/                   # verified raw-artifact preservation by Plan ID
│   └── execution/
│       ├── generations/                    # unpublished repository-wide working generations
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
4. For `--resume`, run `stage_executor.py resume --repo <repository-root> --state <analysis-state-path> --json`. If the current Artifact versions and Manifest are valid, resume the existing stage. Otherwise this command performs a read-only audit of knowledge Artifacts and creates only `.work/migration-plan.yaml` plus a Migration Planning Receipt.
5. When Resume returns `migration-planned`, read the complete plan, then automatically run `stage_executor.py begin --stage migration --plan <output>/.work/migration-plan.yaml`. The executor performs every declared mechanical transform, archive/reinitialization, ID/link rewrite, and check; it then seals the Candidate and returns a Mechanical Output Manifest. Do not edit that Candidate. Inspect the plan and report, then commit the unchanged Migration before beginning any semantic or publication stage. Do not ask for a second user confirmation.
6. When Resume returns `revalidation-required`, begin `finalization` directly. The executor creates a new transactional Working Generation from the published Pack; revise only stale Reader publication wording, deep links, or Reader Projections named by the revalidation reasons, then validate and publish it. Do not create a Migration Plan or rebuild Dossiers, Register, Synthesis, or Business Model.
7. When the plan is `blocked`, preserve the output and report its `blocked_reasons`; do not edit State or Knowledge Artifacts.
8. Run `stage_executor.py status --output <output-dir> --json`, then begin the reported normal stage. Treat its returned Candidate as the only writable output root for that stage.

Resume and migration decisions come only from explicit `artifact_type`, `artifact_schema_version`, `workflow_schema_version`, the Artifact Manifest, file existence, hashes, and registered migration chains. Missing versions are `unknown`; never guess a historical generation from headings, table labels, directories, Frontmatter field names, or body text.

The generated Migration Plan is the complete scope contract. It uses only `preserve`, `mechanical-migrate`, `archive-and-rebuild`, and `block`, and records the earliest safe recovery stage. Every mechanical step declares its Transform ID, exact source/target identity, paths, ID/link rules, expected counts, Manifest policy, and referential checks. There is no `review-and-adopt` action. Do not add an undeclared migration because a document "looks old". Old BA directories, stale Contracts, and other incompatible reader files are archived only by the Migration transaction, never as a side effect of `business-model` or another publication stage.

Migration may produce structural shells and unresolved Observation rows, but never a Dependency identity, Failure Pattern, Connection Model, Shared Behavior Model, Journey, Scenario, Criticality/Risk judgment, or reader-facing prose. Build those only in Tracing, Synthesis, Business Model, and Publication from source evidence and dossiers. A mechanical ID is a reference handle, not a semantic conclusion.

Keep only progress and paths in `analysis-state.yaml`. Store behavioral knowledge in dossiers and the repository register. Never edit lifecycle fields directly; only the stage executor may update them.

After `begin`, create each new template-backed Artifact through the executor instead of copying a Skill template manually:

```bash
python3 <skill-root>/scripts/stage_executor.py scaffold \
  --output <output-dir> \
  --transaction <transaction-id> \
  --artifact-type <artifact-type> \
  [--identity <key>=<value>] \
  --json
```

Use one call per Artifact. Supply only the semantic identity already chosen by the analysis, such as `behavior_id`, `endpoint_id`, `journey_id`, or `scenario_id`; the executor writes the registered type/version, repository, commit, identity tokens, and deterministic Candidate path. It never chooses an ID or writes knowledge content. `already-exists` preserves the existing file byte-for-byte and does not mean the document is complete. Never edit the executor-owned type, version, repository, commit, or primary identity after scaffolding. Do not create optional reference documents that are not applicable.

`current_stage` is the only stage fact. Do not add or consult a `phase` field. Each `begin` creates a versioned Checkpoint Ledger. Complete the returned checkpoints in order through the executor after performing and reviewing the named work:

```bash
python3 <skill-root>/scripts/stage_executor.py checkpoint \
  --output <output-dir> \
  --transaction <transaction-id> \
  --checkpoint <checkpoint-id> \
  --status complete \
  --json
```

Use `skipped`, `blocked`, or `failed` only with `--reason`. A stage cannot commit while a required checkpoint is `pending`, `in-progress`, or `failed`. Checkpoints record progress and gates; they never replace semantic review and never publish files.

Do not call `checkpoint` for Migration. Its executor-owned mechanical checkpoints are completed while `begin --stage migration` builds and seals the Candidate. All later stages keep the normal main-agent checkpoint protocol.

Before every stage commit, run the executor's read-only compact validation command:

```bash
python3 <skill-root>/scripts/stage_executor.py validate \
  --output <output-dir> \
  --transaction <transaction-id> \
  --json
```

Fix `semantic_or_document_errors` in the Candidate and resolve every `blocking_errors` item before committing. Treat `expected_candidate_manifest_drift` and `cross_stage_forward_references` as explicitly classified non-blocking state; do not edit the Manifest or create premature API/BA stubs. Use `status --json` for lifecycle, Generation, Receipt, archive, and recovery inspection, not as the primary document-error report. Validation is read-only and never completes checkpoints, refreshes a Manifest, writes a Receipt, or advances lifecycle state.

From `synthesis` onward, the executor creates or resumes one Working Generation under `.work/execution/generations/<generation-id>/candidate-root/`. Synthesis, Tech, API, Business Model, and BA stage commits update that Generation only. The previously published Register and Reader Packs remain byte-for-byte unchanged until `finalization`; on a first run they may be absent. Never bypass the Candidate to update the formal `.work` knowledge files, `tech-pack/`, or `ba-pack/`. The executor detects formal drift, restores the immutable baseline, and rejects the transaction.

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

Complete `project-detection`, `entrypoint-inventory`, and `evidence-index` in order. Commit the inventory transaction only after the evidence index is valid and every discovered entry point has a catalog disposition. Then begin `tracing` and continue in its new Candidate.

### 3. Trace behaviors into working dossiers

Order work by signal:

1. Application API routes and synchronous request handlers.
2. Event, queue, stream, and scheduled consumers.
3. Shared orchestration referenced by multiple entry points.
4. Technical behaviors.

Process at most five behaviors per internal batch. For each behavior:

1. Use `stage_executor.py mark-behavior` to set its Candidate state to `tracing`; do not edit lifecycle fields directly.
2. Scaffold `behavior-dossier` with `--identity behavior_id=<behavior-id>`; then write the working analysis into the returned Candidate path.
3. For a Java behavior, complete the dossier's `Semantic symbol and call trace` before relying on the apparent call chain. Use exact symbols, definitions, call hierarchy, references, type hierarchy, overrides, and implementations when the environment exposes them. Then confirm critical edges and runtime implementation selection in source, DI/configuration, annotations, and tests. If semantic tooling is unavailable or incomplete, perform and record the policy's degraded investigation instead.
4. For an API behavior, complete the dossier's `Endpoint exposure evidence` section and add every direct layer observation to the register without prematurely correlating it.
5. Follow the executable path from trigger through input handling, validation, decisions, data access, external boundaries, outputs, and material failures. Record raw `LIFE-OBS-*` facts, then keep object conditions, processing actions, and data movement in separate dossier sections. Do not call an action or location a State.
6. Inspect tests alongside implementation. When relevant tests exist, record one or two concrete assertions that prove a core outcome, prioritizing a failure path. Distinguish test-only references from production callers.
7. Inspect IaC and configuration for trigger filters, timeouts, retries, DLQs, permissions, resources, and behavior-changing environment values.
8. Stop at repository boundaries and describe remote internals as unknown.
9. Update the relevant sections of `.work/repository-register.md` while the evidence is in context. Record each lifecycle fact first as an Observation; do not create a Transition without supported From/To object conditions and a real change point. Record each executable external boundary as a Dependency Observation and each material failure path as a Failure Observation; do not create reader-facing Dependency Contracts or Failure Patterns while tracing one Behavior.
10. Apply the behavior-understanding gate from the dossier policy. After main-agent review, use `mark-behavior` to record `understood`; otherwise continue tracing or record `blocked` with the exact limitation. A subagent may deliver a dossier file but may not change global state or commit the stage.

Do not write formal Tech documents, the Business Model, Journeys, or Scenarios during this phase.

Complete `behavior-tracing` and `coverage-review`. Commit `tracing` only when status reports no undiscovered or tracing Behavior. Natural-language progress reports do not satisfy this gate.

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
2. Reconcile observations inside the existing versioned Register tables. Preserve `artifact_type: "repository-register"`, its registry-backed `artifact_schema_version`, and every table header exactly as defined by `assets/register-schema.json`; change rows, not the mechanical contract.
3. Read all behavior dossiers and the repository register.
4. Scaffold `repository-synthesis`; then write the repository mental model into the returned Candidate path.
5. Reconcile lifecycle Observations into `OBJ-*`, `STATE-*`, `ACT-*`, and `TRANS-*`. Build separate Object State, Processing, and Data Movement models. Review every Transition against its From/To conditions, causing Action, observable or persisted result, and evidence; keep unsupported relationships in Unproven lifecycle relationships.
6. Reconcile endpoint evidence only through explicit target, binding, mapping, or rewrite evidence. Populate `Endpoint reconciliation` with separate layer statuses and derive external reachability without upgrading missing layers.
7. Classify each reconciled endpoint record as `application-endpoint`, `meaningful-external-exposure`, `protocol-support`, or `unresolved`; record `publish`, `summarize`, or `publish-as-exception`, the classification basis, and any normalized route-group association. Ordinary protocol support requires proof that it has no application handler, business payload, state access, or business dependency call. Method or mock/static integration alone is insufficient.
8. Associate a shared protocol-support operation with one normalized route group instead of copying it under every application method. Summarize ordinary support records; publish orphaned, conflicting, environment-inconsistent, and unresolved records as exceptions.
9. Reconcile outbound HTTP observations into Remote Operations, Executable Usages, and Field Mappings. Merge Call IDs only from a complete Method + Logical Target + Client Operation match; preserve usage-specific conditions and transformations.
10. Reconcile every `DEP-OBS-nnn` into a logical `DEP-nnn` Dependency or mark it `Unresolved`. Group only with executable binding, configuration, DI/wiring, or resource-identity evidence. Create `DEP-nnn-OPnn` Operations beneath each Dependency, link existing HTTP Call IDs instead of copying mappings, record dependent capabilities, and classify availability impact as `Required`, `Degradable`, `Optional`, or `Unknown` at Operation or Behavior usage level.
11. Reconcile every `FO-nnn` into a `FAIL-nnn` Pattern or mark it `Unresolved`. Merge only when trigger/source, propagation, caller visibility, state outcome, retry safety, and recovery semantics are materially equivalent. Record recurring behaviors, dependency relationships, recovery gaps, and evidence-supported `High`, `Medium`, `Low`, or `Unknown` risk attention.
12. Merge, split, or rename behaviors when the combined evidence requires it; update the working catalog, state, dossiers, and register together.
13. Build the `Capability path model`. Combine Behaviors by supported repository capability and describe each capability's goal, trigger, normal successful path, principal decisions, result, and deep links. Do not create one Capability per Behavior or call a path default without selection evidence.
14. Build the `Variant model`. Include Market, Country, Tenant, Channel, Profile, Environment, Feature Flag, or another axis only when a proven selector changes rules, validation, Dependency choice, Mapping, state, output, failure, retry, or recovery. Record the absence of a repository-proven baseline instead of choosing one.
15. Build the `Risk hotspot model` from existing High and materially Unknown Failure, Dependency, and Lifecycle conclusions. Do not create a second risk score or copy the Failure Pattern index.
16. Build the `Repository connection model` from reconciled endpoint, dependency, lifecycle, configuration, and failure models. Group only when participant/resource, direction, boundary type, interaction role, and configuration-selection semantics are equivalent. Include only executable crossings or explicit trigger bindings; a class, host, resource, or configuration name alone is not a connection.
17. Build the `Shared behavior model`. Include a rule or behavior-shaping component only when the same proven source is reused by at least two Behaviors or independent entry paths and materially changes validation, decisions, authorization, transformation, state, boundaries, output, error handling, or recovery. Preserve behavior-specific differences and overrides. Exclude logging, ordinary monitoring, generated code, framework glue, simple wrappers, and single-Behavior helpers.
18. Explain blocked coverage, conflicts, and unknowns instead of filling gaps with intent.
19. Complete the synthesis checkpoints in their executor-provided order: Endpoint, Outbound HTTP, Dependency, Failure, Lifecycle/Config, Connection/Shared Model, and synthesis review. Commit with `--semantic-result complete` only after every Lifecycle, Dependency, and Failure Observation is reconciled or explicitly unresolved, every Transition received semantic review, the Capability, Variant, Risk, Dependency, Failure, Connection, and Shared Behavior models are complete and reviewed. This commit advances only the Working Generation; it does not replace the formal Pack.

### 6. Publish the Tech Pack

Begin `tech-publication` and write in its Candidate for a developer who needs to understand the repository, not for an auditor trying to count claims.

1. Scaffold one `tech-behavior` per completed dossier with `--identity behavior_id=<behavior-id>`, then write the developer-facing Behavior. Lead with Summary, Main Path, and a retellable Behavior Flow. Put material Variants and risks next; keep only applicable implementation subsections and omit empty State, HTTP, Dependency, and Failure sections.
2. Scaffold `repository-overview` and build it from the completed Capability Path, Variant, Risk Hotspot, Connection, and Shared Behavior models in `repository-synthesis.md`, not directly from evidence, catalogs, or raw register rows. Lead with `Repository in 5 minutes`, one path per principal Capability, behavior-changing Variants, and High or materially Unknown risks. Put system context and Technical Reference later. Link detailed Endpoint, Schema, Mapping, Lifecycle, Config, Dependency, and Failure models instead of copying their tables. Leave BA Scenario semantics for the independent Business Model.
3. Scaffold `tech-behavior-catalog`, populate it from the reconciled working catalog, and replace working dossier paths with final document links. Do not copy the Working Catalog's Artifact identity into the Tech Catalog. For every API Behavior, declare each stable Endpoint ID and Contract destination in both the Behavior and Catalog. Use `../contracts/<endpoint-id>.api-contract.md` in the Behavior and `contracts/<endpoint-id>.api-contract.md` in the Catalog. The executor treats a missing target as a cross-stage forward reference, but Reader text must use durable labels such as “API Contract” and must not mention planning, pending materialization, generation order, or a later stage. Do not create empty Contract stubs or an Endpoint Matrix during Tech publication. Use `api_contracts: []` for non-API Behaviors.
4. Scaffold only applicable repository references and populate them from the corresponding reconciled register records and repository-synthesis models:
   - [assets/data-lifecycle-template.md](assets/data-lifecycle-template.md)
   - [assets/field-validation-and-mapping-template.md](assets/field-validation-and-mapping-template.md)
   - [assets/runtime-config-matrix-template.md](assets/runtime-config-matrix-template.md)
   - [assets/external-dependency-contracts-template.md](assets/external-dependency-contracts-template.md)
   - [assets/failure-taxonomy-template.md](assets/failure-taxonomy-template.md)
   Build `data-lifecycle.md` by Object. Use a State Diagram only for registered States and established Transitions; use a separate Processing/Data Movement flow for `ACT-*`, resources, and boundaries. When no Transition is established, omit the State Diagram and use the exact no-transition statement from the lifecycle schema.
5. Build the outbound portion of `field-validation-and-mapping.md` as one index row and one anchored section per Remote Operation. Put call identity once in Call Overview, list multiple or materially different Executable Usages, and nest request/response mappings under that Call. Do not copy the register tables or repeat call metadata in mapping rows.
6. In each affected Tech Behavior, add one call-summary row per Remote Operation, link its Call ID directly to the operation anchor, and list only that behavior's Usage IDs. Do not create one behavior row per Mapping ID.
7. Build `external-dependency-contracts.md` as one landscape row and one anchored section per `DEP-nnn`. Nest Operations beneath their Dependency, explain role, shared capabilities, availability, degradation, state implications, and remote Unknowns, and link Field Mapping and Failure details instead of repeating them. Never publish the Dependency Observation table.
8. Build `failure-taxonomy.md` as one index row and one anchored section per `FAIL-nnn`. Lead with repository-wide High and Unknown attention, then explain trigger, caller visibility, state outcome, retry/recovery, and cross-Behavior variations. Link API errors, lifecycle changes, Dependency Contracts, and Tech flows instead of repeating them. Never publish the Failure Observation table.
9. Link each behavior only to relevant repository references. Use stable `dependency_id` entries and `failure_patterns` IDs in affected Tech frontmatter, with one concise usage-specific row linking each repository-level anchor. Do not duplicate detailed contracts or repository-wide tables inside every behavior.

Keep prose natural. In Reader artifacts, do not add generic Status/Evidence columns or repeat `Confirmed`. Put `*(Inferred)*`, `*(Unknown)*`, or `*(Conflicting)*` beside the affected primary label, and support coherent Tech sections with grouped `[E#]` Source Notes rather than one citation per row. BA documents expose no source citations and trace through Scenario-to-Tech relationships.

Complete all Tech publication checkpoints through the executor. Commit `tech-publication` only after its Behavior checks, publication-maturity check, and the `tech-publication` Pack validation profile pass. That profile fully validates the HTTP Call/Usage/Mapping model, Dependency Contracts, Failure Taxonomy, their Register relationships, Tech Behavior backlinks, ordinary Tech links, and Artifact integrity. It records missing future API materialization and BA traceability as `deferred`, never as a successful `SKIPPED` check. Only missing Contract files, Endpoint Matrix, and future `ba-pack/` targets are deferred; identity, stable destination, visible links, path containment, publication-neutral prose, and all current Tech artifacts remain strict. This commit advances only the Working Generation.

### 7. Publish endpoint evidence and application API contracts

Begin `api-contract-publication` and use its Candidate.

First scaffold `endpoint-matrix` whenever the register contains evidence from any endpoint layer, then write it as a reader-facing projection rather than a dump of every register row:

- Publish every reconciled `application-endpoint` and `meaningful-external-exposure`.
- Publish every `unresolved` record and every orphaned, conflicting, or environment-inconsistent protocol-support record as an exception.
- Summarize ordinary `protocol-support` declarations in one compact section with raw declaration count, related route groups, exception count, source/scope summary, and one link to the complete repository register.
- Do not publish one Matrix row per ordinary preflight/CORS declaration. Do not hide a real handler, business response, health/version capability, authentication/query behavior, state access, or dependency-backed operation merely because it uses OPTIONS or mock/static integration.
- Keep all five endpoint-layer statuses independent from operation role and publication disposition.

For every confirmed application endpoint:

1. Generate a stable endpoint ID from repository, lower-case method, and normalized route. Replace slashes and route punctuation with hyphens; retain parameter names. Add a stable disambiguating suffix only for a collision.
2. Scaffold `api-contract` with both `--identity endpoint_id=<endpoint-id>` and `--identity behavior_id=<behavior-id>`, then write the caller-facing Contract into the returned path.
3. Use L1 executable, L2 schema-level, and L3 shared/opaque evidence to reconcile fields before writing, but publish one caller-facing request and response view rather than fixed evidence-layer sections.
4. Lead with purpose, invocation, authentication, required/conditional/high-impact caller inputs, validation, responses, supported examples, confidence, and material limitations. For a large Schema, put remaining non-duplicated fields in the optional `Complete field reference`; omit that section for a small Contract.
5. Keep `method` and `route` as application identities. Show only a concise external-path/reachability summary and the Endpoint Matrix link; do not copy the five-layer table into the Contract.
6. Keep internal flow in Tech Behavior, detailed endpoint exposure in Endpoint Matrix, outbound HTTP mappings in Field Validation and Mapping, downstream boundaries in External Dependency Contracts, and internal/repository-wide failures in Failure Taxonomy.
7. Use compact `[E#]` markers and grouped Source notes. Do not expose a repeated Evidence column or one citation per sentence when a meaningful row or paragraph can share support.
8. Generate request and response examples only when code, schema, or tests support their fields, statuses, and wire shapes. Omit unsafe examples and record the caller impact instead of inventing values or serialization.
9. Set the contract's `behavior_document` backlink.
10. Materialize every Contract declared by the Tech Behavior and Catalog. Verify the Endpoint ID, Contract filename, Behavior backlink, visible link, Catalog path, and Matrix links as one relationship. Correct endpoint relationships only when reconciliation requires it; do not leave any declared Contract target missing when this stage commits.
11. After every Contract and Matrix record is present, run `refresh-projections`. Read its plan, revise every semantic API Projection, then record each review with `mark-projection`. During `api-backlinks`, confirm the refreshed Behavior, Catalog, Repository Overview, optional Field Pack index, and affected Failure summaries describe the materialized API view and contain no generation-order wording.

Do not generate a contract or behavior for an external-only, configuration-only, or ordinary protocol-support record. Multiple external entries mapped to one application endpoint share its one application contract.

Validate each endpoint contract and its backlink before continuing.

Complete the Endpoint Matrix, Contract, Reader Projection, backlink, and validation checkpoints. Commit this stage only when API Reader Projection status is `current`. Use `--skip` only when there are no Contract files, no API Behaviors, and no declared `api_contracts` in the Tech Behavior or Catalog; do not create empty Contracts. Either result advances only the Working Generation.

### 8. Build an independent Business Model and publish the BA Pack

Begin only after repository synthesis and the related Tech documents are complete.

1. Begin `business-model`, read the BA Pack policy, scaffold `business-model`, and write the independent business synthesis into the returned Candidate path.
2. Reconstruct Capabilities, actors, business objects, Journeys, Scenarios, shared business rules, business-visible exceptions, and Journey–Scenario relationships across all completed Tech facts. Do not iterate through Tech Behaviors and generate one BA document per row.
3. Account for every active Tech Behavior in the Business Model as `scenario-support`, `business-visible-support`, `no-business-visible-role`, or `unknown`. An Entry Point, technical branch, validation, Dependency, or exception does not automatically become a Scenario, business decision, rule, participant, or exception.
4. Assign semantic Journey and Scenario IDs from supported business goals and contexts. Merge and split by actor goal, business context, decision meaning, business-object lifecycle, and visible outcome—not by endpoint, handler, event, or Behavior identity.
5. Complete the Capability/Object, Journey/Scenario, Tech Coverage, and Business Model review checkpoints. Review the Business Model semantically and commit `business-model` with `--semantic-result complete`, `partial`, or `blocked`. Only the executor updates `business_model_status`; the commit advances only the Working Generation.
6. When status is `complete` or `partial`, begin `ba-publication`; scaffold `ba-overview` and `ba-catalog`, one `ba-journey` with `journey_id` per Journey, and one `ba-scenario` with `scenario_id` per Scenario. Then write the BA content into those returned Candidate paths.
7. Author direct many-to-many Scenario/Tech and Journey/Scenario relationships. After every Journey and Scenario exists, run `refresh-projections` to generate the inverse Tech Behavior, Catalog, Journey-derived, and Repository Overview navigation. Revise every semantic BA Projection and record it with `mark-projection`. A Journey links its Scenarios and their supporting Tech Behaviors, but Tech documents do not maintain Journey backlinks. `ba_scenarios: []` is valid for Behaviors with no direct Scenario.
   During `ba-backlinks`, confirm the refreshed Tech and BA documents describe the complete current business model and contain no wording that treats Journeys or Scenarios as pending a later publication step.
8. Preserve evidence confidence without exposing raw source citations. Include only business-visible participants, interactions, shared rules, degradation, partial success, state risk, and recovery limitations. Do not copy the technical context diagram, connection matrix, internal components, Dependency tables, Failure tables, or Tech flows.
9. When status is `blocked`, begin `ba-publication` only to commit it with `--skip` and the blocker reason; omit invented Journey and Scenario documents and keep the supported Tech Pack complete.

Complete the Journey, Scenario, BA Overview/Catalog, Reader Projection, backlink, and validation checkpoints. Commit `ba-publication` only after both API and BA Reader Projection statuses are `current` or `not-applicable`. This commit advances only the Working Generation.

### 9. Review in three passes

Begin `finalization` from the complete Working Generation and review its Candidate snapshot. This is the only normal stage authorized to replace formal knowledge Artifacts and Reader Packs.

Apply the Editorial and Finalization Review policies in this order:

1. Mechanical review: generic Markdown structure first, then Artifact/frontmatter, specialized document structure, file and Fragment links, endpoint identity, commit, JSON examples, placeholders, and citation bounds.
2. Fact review: sample important rules, Object State definitions, State Transition evidence, Action/State separation, mappings, configuration effects, and failure paths back to source.
3. Reader review: confirm a developer can retell Tech behavior and a BA can retell independent Journeys, Scenarios, object changes, outcomes, and exceptions; verify that mapping count does not multiply Call, Target, or Behavior metadata in the Field Pack. Run the publication-maturity check across the complete Reader Pack. Rewrite every explicit execution-stage residue. Inspect warning-only words such as `planned` or `pending` in context and retain them only when they describe a real domain state.

After corrections stabilize, create one schema-complete input for each pass and run `record-review` for `mechanical`, `semantic-fact`, and `reader`. Every applicable risk category needs a high-value sample; every `not-applicable` category needs a reason. Record all displayed Validator warning decisions. A corrected sample must name a file actually changed in Finalization, and a Semantic Fact sample must cite repository evidence. Re-record all three Reviews if Candidate knowledge changes.

Before Release Readiness, confirm every applicable Reader Projection is `current`, its relationship graph matches the Candidate, and no semantic Projection item remains pending. A valid link alone does not prove that Overview, Catalog, Behavior, Field, or BA summaries are current.

During reader review, also verify that each external Dependency appears once regardless of the number of Behaviors or Operations, and that each Failure Pattern explains a repository-level trigger-to-visible-result-and-state story instead of presenting an observation inventory.

Before opening Technical Reference, verify that a developer can explain repository responsibility, retell each principal Capability path, identify code-supported Market/Country/Tenant/Channel/Profile/configuration Variants, and locate High or materially Unknown risks. For a large API Schema, verify that core caller fields precede the remaining field reference without duplicate identities; for a small Schema, reject an unnecessary completeness appendix.

For Repository Overview, verify that the context diagram and connection matrix make direction, boundary, interaction role, exchanged concepts, supported Behaviors, configuration selection, criticality, and failure/state impact understandable without the register. Confirm that same-role Operations are not repeated as connections, materially different roles are not collapsed, shared items really affect at least two Behavior paths, ordinary utilities are excluded, and every deep-dive destination is reachable with one link.

For the BA Pack, verify that Journey and Scenario counts arise from business goals, contexts, decisions, object lifecycles, and outcomes rather than Tech Behavior count. Sample one Scenario-to-Tech many-to-many mapping, one unmapped Tech Behavior disposition, one technical branch that was not promoted to a business decision, and one business-visible exception. Confirm that BA documents do not reproduce the Tech call chain with renamed nodes.

Complete `mechanical-review`, `fact-sampling`, and `readability-review` only after their current Review record exists. Complete `release-readiness` only when Mechanical is `passed`, Semantic Fact and Reader are `current`, all records bind the same Candidate Hash, no finding is unresolved, Reader Projections are current, and complete mechanical validation has zero Primary Errors and zero necessary Skipped Groups.

The finalization commit validates the complete Generation, computes a release Manifest, archives the previously published knowledge Artifacts, promotes the complete Generation under a recovery Journal, validates the result again, and only then writes the final Receipt and completed State. A result with any Primary Error or skipped necessary validation group is incomplete and cannot be reported as全面验证通过. Treat warnings as review prompts, not prose-generation targets. Resolve mechanical errors in the Candidate without rewriting readable text into claim statements.

### 10. Deliver

Commit `finalization`. Deliver only when `status --json` reports `current_stage: completed`, `stage_status: committed`, `working_generation_status: published`, matching `working_generation_id` and `published_generation_id`, `artifact_manifest_status: valid`, `markdown_fragment_validation_status: current`, `manifest_refresh_pending: none`, `formal_drift_status: clean`, `release_readiness: ready`, and a successful finalization Receipt with `formal_pack_published: true`. A Manifest reported as `stale` during an active transaction is pending deterministic commit refresh, not corruption and not completion; inspect the separate formal/Candidate status fields described in the Stage Execution Policy. Report:

- Repository path and commit.
- Full-repository coverage and any blocked areas.
- Pack directories and generated documents.
- Behavior, Journey, Scenario, and endpoint counts, separating application endpoints, meaningful external exposures, aggregated protocol-support declarations, published exceptions, and blocked coverage.
- Important confirmed findings, unknowns, conflicts, and limitations.
- Mechanical Pass, Semantic Fact Review, and Reader Review results, sampled coverage, corrections, unresolved findings, and intentional warnings. Never present Mechanical Pass alone as document quality completion.

Do not modify application source code unless the user separately requests an implementation change.

## Completion standard

Before delivering, confirm:

- `.work` shows inventory, per-behavior understanding, repository registration, repository synthesis, and independent business modeling in that order.
- Every long-lived Artifact declares the Registry-backed type/version, the final Artifact Manifest matches file hashes, and no invalidated Artifact type remains at Finalization.
- Migration Planning, Migration, and Publication have distinct Receipts; Resume decisions use explicit versions and hashes, and the Register table headers match the bundled Schema with `valid` HTTP, Dependency, Failure, and Lifecycle domains and zero skipped necessary groups.
- Every final behavior can be retold as a coherent success-and-failure story.
- Tests contribute assertion-level evidence when available.
- Data and state changes connect across behaviors where evidence permits.
- Object States describe object conditions, Processing Actions describe what code does, and Data Movement describes source/store/boundary/destination. Every published lifecycle edge has a registered Transition and evidence; unsupported relationships remain unresolved rather than being drawn.
- Every confirmed application API route has its own contract; meaningful external-only records and endpoint exceptions appear only in Endpoint Matrix, while ordinary protocol-support records remain fully evidenced in the register and appear as a compact Matrix summary.
- Every API Contract leads with caller purpose, invocation, inputs, validation, responses, confidence, and material limitations; it uses supported examples when available and links instead of copying internal flow, five-layer exposure, outbound mappings, or failure-taxonomy detail.
- Application route, external entry, environment intent, runtime deployment, and external reachability remain separate, with no single layer proving another.
- Cross-boundary field mappings exist only for proven outbound HTTP calls.
- Outbound HTTP knowledge is separated into Remote Operations, Executable Usages, and Field Mappings; each Remote Operation has one final anchored section, while usage-specific conditions and mappings remain visible.
- Runtime configuration appears only when it changes behavior.
- External systems are reconciled into Dependency Contracts with distinct Operations, dependent capabilities, availability impact, and explicit remote Unknowns; the formal document does not repeat one dependency per Behavior or copy the observation register.
- Failure observations are reconciled into repository-wide Patterns with caller visibility, state outcome, retry safety, recovery, and evidence-supported risk attention; the formal taxonomy does not copy one row per dossier failure.
- Repository Overview contains a synthesis-backed context diagram and connection matrix rather than a list of external names; logical connections preserve direction, boundary, role, exchanged concepts, configuration variants, criticality, failure/state impact, and one-click deep links without repeating every Operation.
- Repository Overview acts as the five-minute entry point: responsibility, Capability paths, behavior-changing Variants, and highest-attention risks appear before system context and Technical Reference.
- Tech Behaviors lead with a retellable Main Path and omit inapplicable implementation subsections; API Contracts layer caller-critical fields before any remaining complete Schema reference.
- Shared Rules and Shared Behavior-shaping Components include only proven cross-Behavior items that materially affect observable behavior, preserve differences and overrides, and exclude ordinary tools and framework glue.
- Every Java behavior has a completed semantic symbol/call trace or an explicit degraded/unavailable investigation; unresolved callers, dynamic edges, and implementation bindings remain qualified.
- `.work/business-model.md` accounts for every active Tech Behavior without using Behavior count as a Journey or Scenario target.
- Journey and Scenario IDs are independent from Tech Behavior IDs; Scenario/Tech traceability is many-to-many and every declared relationship has a backlink.
- BA Journeys explain business goals, stages, object progression, handoffs, outcomes, and repository boundaries; BA Scenarios explain supported business situations, decisions, information, outcomes, and exceptions.
- Technical triggers, branches, validations, Dependencies, and exceptions are not promoted to business concepts without supported business-visible meaning.
- BA flows are independently modeled business views, not copied or mechanically renamed Tech call chains.
- The final prose reads as documentation, not as a Claim Ledger or validator transcript.
- Every published local Markdown link with a non-empty Fragment resolves to an explicit anchor or supported GFM heading slug; deferred API/BA links have been materialized and rechecked.
