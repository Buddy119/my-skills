---
name: eapi-behavior-reconstruction
description: "Reconstruct a human-readable repository knowledge pack from one complete EAPI microservice or AWS Lambda repository, starting with only a local path or a $eapi-behavior-reconstruction --repo invocation. Follow an expert reading workflow: index the repository, discover every executable behavior, trace behaviors end to end into working dossiers, synthesize repository-wide relationships and data lifecycles, then publish linked developer and BA views with endpoint-level API contracts and evidence-backed technical references. Use when Codex needs to reverse-engineer an undocumented repository, help developers and business analysts understand it, or prepare reliable inputs for later cross-service impact analysis."
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
- Let AI trace, interpret, synthesize, and write. Use scripts only for deterministic indexing and mechanical validation.
- Do not modify this Skill, its templates, references, or scripts during a repository analysis run. A writable Skill root is valid.
- Execute bundled Python scripts with the available `python3` and their absolute paths. They use only the Python standard library. If a script cannot run, report the failure and perform the equivalent read-only check manually; do not patch the script or install dependencies during the run.
- Do not access credentials, secret values, production customer data, live AWS resources, or repositories outside the supplied boundary.

## Load policies progressively

Read [references/evidence-policy.md](references/evidence-policy.md) completely before reading source code.

Before tracing the first behavior, read [references/behavior-dossier-policy.md](references/behavior-dossier-policy.md) completely.

Before repository-wide synthesis, read [references/repository-synthesis-policy.md](references/repository-synthesis-policy.md) completely.

Before publishing final documents, read [references/editorial-review-policy.md](references/editorial-review-policy.md) completely.

Load these only when applicable:

- After identifying a Java repository, read [references/java-semantic-analysis-policy.md](references/java-semantic-analysis-policy.md) completely before tracing Java symbols and calls.
- After finding an application route or any endpoint-related external-entry, environment-intent, or runtime evidence, read [references/endpoint-exposure-evidence-policy.md](references/endpoint-exposure-evidence-policy.md) before correlating endpoint candidates.
- For a confirmed application API route, read [references/api-contract-policy.md](references/api-contract-policy.md).
- After proving an executable outbound HTTP call, read [references/field-mapping-policy.md](references/field-mapping-policy.md).
- Before creating BA-facing outputs, read [references/ba-pack-policy.md](references/ba-pack-policy.md).

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
│   └── repository-synthesis.md
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
    ├── behavior-catalog.md
    └── behaviors/
```

Do not create empty reference documents to satisfy this tree. Record absent or inapplicable modules in `repository-overview.md` as `Not observed` or `Not applicable`.

## Workflow

### 1. Establish the boundary and analysis state

1. Confirm the repository root and record `git rev-parse HEAD` when available.
2. Exclude generated artifacts, vendored dependencies, build output, coverage output, and lockfiles unless they define runtime behavior.
3. Copy [assets/analysis-state-template.yaml](assets/analysis-state-template.yaml), [assets/behavior-catalog-template.yaml](assets/behavior-catalog-template.yaml), and [assets/repository-register-template.md](assets/repository-register-template.md) into `.work/`.
4. Set `analysis_mode: automatic`, and move `phase` through `inventory`, `tracing`, `synthesis`, `publishing`, and `completed` as work advances.
5. If an existing `.work/analysis-state.yaml` has the same repository and commit, resume it. If its commit differs, preserve the existing output and start a sibling output directory suffixed with the new short commit; never reuse old dossiers as current facts.

When resuming a same-commit analysis whose register lacks both `Endpoint evidence records` and `Endpoint reconciliation`, keep completed behavior dossiers but treat endpoint inventory and synthesis as stale. Rebuild the layered endpoint register, reset synthesis/publication to pending, regenerate affected formal documents, and do not publish the legacy flattened endpoint conclusions.

Keep only progress and paths in `analysis-state.yaml`. Store behavioral knowledge in dossiers and the repository register.

### 2. Build a navigation index and inventory entry points

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

Add each observation to `Endpoint evidence records` in the repository register. Do not let an application route prove exposure, let a declaration prove deployment, or correlate layers from method/route similarity alone. An external-only candidate is not an executable behavior and must not be added to the behavior catalog.

For Java executable call relationships, use `rg` as discovery support and as the documented fallback when semantic navigation is unavailable or incomplete. A filename, method-name match, import, or subagent observation identifies a candidate; it does not by itself establish the called symbol or runtime implementation.

Group trigger, handler, controller, service, and orchestration code into one behavior when they implement one end-to-end flow. Catalog framework glue, health checks, migrations, and deployment-only utilities as technical, duplicate, or excluded rather than promoting them to business behaviors.

Create stable behavior IDs and catalog every executable application or framework entry point. Keep external-only and configuration-only endpoint candidates out of the behavior catalog and in the endpoint register. Mirror active behaviors in `analysis-state.yaml` with status `discovered`.

### 3. Trace behaviors into working dossiers

Order work by signal:

1. Application API routes and synchronous request handlers.
2. Event, queue, stream, and scheduled consumers.
3. Shared orchestration referenced by multiple entry points.
4. Technical behaviors.

Process at most five behaviors per internal batch. For each behavior:

1. Set its state to `tracing`.
2. Copy [assets/behavior-dossier-template.md](assets/behavior-dossier-template.md) to `.work/behavior-dossiers/<behavior-id>.md`.
3. For a Java behavior, complete the dossier's `Semantic symbol and call trace` before relying on the apparent call chain. Use exact symbols, definitions, call hierarchy, references, type hierarchy, overrides, and implementations when the environment exposes them. Then confirm critical edges and runtime implementation selection in source, DI/configuration, annotations, and tests. If semantic tooling is unavailable or incomplete, perform and record the policy's degraded investigation instead.
4. For an API behavior, complete the dossier's `Endpoint exposure evidence` section and add every direct layer observation to the register without prematurely correlating it.
5. Follow the executable path from trigger through input handling, validation, decisions, data access, external boundaries, outputs, and material failures.
6. Inspect tests alongside implementation. When relevant tests exist, record one or two concrete assertions that prove a core outcome, prioritizing a failure path. Distinguish test-only references from production callers.
7. Inspect IaC and configuration for trigger filters, timeouts, retries, DLQs, permissions, resources, and behavior-changing environment values.
8. Stop at repository boundaries and describe remote internals as unknown.
9. Update the relevant sections of `.work/repository-register.md` while the evidence is in context.
10. Apply the behavior-understanding gate from the dossier policy. Mark the behavior `understood` only after it passes; otherwise continue tracing or mark it `blocked` with the exact limitation.

Do not write final Tech or BA behavior documents during this phase.

### 4. Record external HTTP mappings only when proven

First locate an executable outbound HTTP/HTTPS invocation. Record the call, method, target, client operation, behavior ID, and evidence in the dossier and repository register.

Only then record:

- EAPI fields mapped to the external request path, query, header, or body.
- External response fields mapped back into EAPI fields when consumed.

Do not classify inbound API contracts, event payloads, queue messages, persistence mappings, or internal DTO/domain conversions as cross-boundary HTTP field mappings.

### 5. Synthesize the repository mental model

Begin only after every active behavior is `understood` or explicitly `blocked`, every executable entry point has a catalog disposition, and endpoint evidence candidates are registered.

1. Set `phase: synthesis`.
2. Read all behavior dossiers and the repository register.
3. Copy [assets/repository-synthesis-template.md](assets/repository-synthesis-template.md) to `.work/repository-synthesis.md`.
4. Reconcile behavior boundaries, shared rules, business objects, state transitions, data lifecycles, dependencies, configuration effects, and failure categories.
5. Reconcile endpoint evidence only through explicit target, binding, mapping, or rewrite evidence. Populate `Endpoint reconciliation` with separate layer statuses, preserve unmatched external entries, and derive external reachability without upgrading missing layers.
6. Merge, split, or rename behaviors when the combined evidence requires it; update the working catalog, state, dossiers, and register together.
7. Explain blocked coverage, conflicts, and unknowns instead of filling gaps with intent.
8. Set `synthesis_status: complete` after the synthesis work is complete. Coverage may still be `partial` when explicitly blocked areas are accounted for.

Run the mechanical state check before publishing:

```bash
python3 <skill-root>/scripts/validate_analysis_state.py \
  <output-dir>/.work/analysis-state.yaml \
  --repo <repository-root> \
  --catalog <output-dir>/.work/behavior-catalog.yaml \
  --dossiers-dir <output-dir>/.work/behavior-dossiers \
  --require-publishable
```

### 6. Publish the Tech Pack

Set `phase: publishing` and `publication_status: in-progress`. Write for a developer who needs to understand the repository, not for an auditor trying to count claims.

1. Build each Tech Behavior from its completed dossier. Use [assets/behavior-document-template.md](assets/behavior-document-template.md).
2. Build `repository-overview.md` from `repository-synthesis.md` using [assets/repository-overview-template.md](assets/repository-overview-template.md), not directly from the evidence index.
3. Copy the reconciled working catalog to `tech-pack/behavior-catalog.yaml` and replace working dossier paths with final document links.
4. Generate applicable repository references from the corresponding register and synthesis sections:
   - [assets/endpoint-matrix-template.md](assets/endpoint-matrix-template.md)
   - [assets/data-lifecycle-template.md](assets/data-lifecycle-template.md)
   - [assets/field-validation-and-mapping-template.md](assets/field-validation-and-mapping-template.md)
   - [assets/runtime-config-matrix-template.md](assets/runtime-config-matrix-template.md)
   - [assets/external-dependency-contracts-template.md](assets/external-dependency-contracts-template.md)
   - [assets/failure-taxonomy-template.md](assets/failure-taxonomy-template.md)
5. Link each behavior only to relevant repository references. Do not duplicate detailed contracts or repository-wide tables inside every behavior.

Keep prose natural. Attach evidence to a paragraph, meaningful rule, flow explanation, or table row; do not label every sentence.

### 7. Publish endpoint evidence and application API contracts

First generate `endpoint-matrix.md` whenever the register contains evidence from any endpoint layer. Include every reconciled application endpoint and every unmatched external, environment-intent, or runtime record, with separate statuses for all five layers.

For every confirmed application endpoint:

1. Generate a stable endpoint ID from repository, lower-case method, and normalized route. Replace slashes and route punctuation with hyphens; retain parameter names. Add a stable disambiguating suffix only for a collision.
2. Copy [assets/api-contract-document-template.md](assets/api-contract-document-template.md) to `tech-pack/contracts/<endpoint-id>.api-contract.md`.
3. Keep L1 executable, L2 schema-level, and L3 shared/opaque-transformer evidence separate from the five endpoint-exposure layers.
4. Keep `method` and `route` as application identities. Add the application-route and external-reachability statuses plus a link to the Endpoint Matrix evidence.
5. Set the contract's `behavior_document` backlink.
6. Add every related application endpoint to the Tech Behavior's `api_contracts` list and visible `API contracts` links. Use `api_contracts: []` for non-API behaviors.

Do not generate a contract or behavior for an external-only or configuration-only record. Multiple external entries mapped to one application endpoint share its one application contract.

Validate each endpoint contract and its backlink before continuing.

### 8. Derive the BA Pack after synthesis

Generate the BA Pack only after repository synthesis and related Tech documents are complete.

1. Build `business-overview.md` from the synthesized business capabilities, participants, business objects, lifecycles, shared rules, outcomes, and exceptions using [assets/ba-overview-template.md](assets/ba-overview-template.md).
2. Build `behavior-catalog.md` with [assets/ba-behavior-catalog-template.md](assets/ba-behavior-catalog-template.md), then generate `business` and `integration` behaviors with [assets/ba-behavior-document-template.md](assets/ba-behavior-document-template.md).
3. Use the dossier, repository synthesis, and Tech Behavior as inputs; do not translate the Tech Mermaid or reuse a shared flow object.
4. Model BA flow using business events, participants, decisions, business-object changes, and visible outcomes.
5. Preserve evidence confidence without exposing raw source citations. Link back to the Tech Behavior.

Purely technical behavior belongs in the BA Pack only when its effect materially changes a business-visible outcome; describe that effect in the affected BA behavior.

### 9. Review in three passes

Apply the editorial policy in this order:

1. Mechanical review: state, structure, links, endpoint identity, commit, placeholders, and citation bounds.
2. Fact review: sample important rules, state changes, mappings, configuration effects, and failure paths back to source.
3. Reader review: confirm a developer and BA can independently retell the behavior, lifecycle, outcomes, and exceptions.

Run:

```bash
python3 <skill-root>/scripts/validate_behavior_doc.py <tech-behavior.md> --repo <repository-root>
python3 <skill-root>/scripts/validate_api_contract.py <endpoint-contract.md> --repo <repository-root>
python3 <skill-root>/scripts/validate_ba_behavior.py <ba-behavior.md>
python3 <skill-root>/scripts/validate_pack_links.py <output-dir>
```

Treat warnings as review prompts, not prose-generation targets. Resolve mechanical errors without rewriting readable text into claim statements.

### 10. Deliver

Set `publication_status: complete` and `phase: completed` after final review. Report:

- Repository path and commit.
- Full-repository coverage and any blocked areas.
- Pack directories and generated documents.
- Behavior and endpoint counts, including blocked coverage.
- Important confirmed findings, unknowns, conflicts, and limitations.
- Mechanical validation results and any intentional warnings.

Do not modify application source code unless the user separately requests an implementation change.

## Completion standard

Before delivering, confirm:

- `.work` shows inventory, per-behavior understanding, repository registration, and synthesis in that order.
- Every final behavior can be retold as a coherent success-and-failure story.
- Tests contribute assertion-level evidence when available.
- Data and state changes connect across behaviors where evidence permits.
- Every confirmed application API route has its own contract; external-only records appear only in Endpoint Matrix.
- Application route, external entry, environment intent, runtime deployment, and external reachability remain separate, with no single layer proving another.
- Cross-boundary field mappings exist only for proven outbound HTTP calls.
- Runtime configuration appears only when it changes behavior.
- External systems are described at the observed boundary without invented internals.
- Every Java behavior has a completed semantic symbol/call trace or an explicit degraded/unavailable investigation; unresolved callers, dynamic edges, and implementation bindings remain qualified.
- Tech and BA flows answer different audience questions and are not copies.
- The final prose reads as documentation, not as a Claim Ledger or validator transcript.
