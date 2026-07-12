# Repository knowledge pack policy

## Goal and boundary

Build the maximum defensible understanding of one repository at one recorded commit. The pack must help developers and business analysts navigate behavior, endpoints, data lifecycle, fields, runtime configuration, dependencies, and failures without claiming knowledge that lives only in another repository, deployed environment, unavailable shared layer, or historical requirement.

Use `Confirmed`, `Inferred`, `Conflicting`, and `Unknown` from the evidence policy. Use `complete`, `partial`, and `blocked` only for coverage.

## Canonical manifest

Create and audit `.work/claim-ledger.json` before populating `knowledge-manifest.yaml` or drafting final documents. Treat the claim ledger as the repository-fact registry and the manifest as the canonical relationship registry, never as evidence. Every entity must have one stable ID, one status, and one or more passing `claim_ids` that bind the entity to supported facts or scoped uncertainty.

At least one bound claim must have an entity-compatible type. In particular, endpoints require `endpoint-contract`, failures require `failure`, configurations require `configuration`, and external mappings require `mapping`. A field also records `boundary_kind` and `observation_kind`; keep local lookup keys separate from declared external fields.

Machine-readable values are facts too. Endpoint `method`/`route`, field `path`, configuration `key`, concrete dependency `type`, failure `category`, and mapping `direction` must be present in the statement, verification tokens, or render terms of their bound claims. Two generated files that repeat the same unsupported value do not corroborate one another.

The behavior catalog may temporarily use `discovered` and its `pending` count during analysis. Before final pack validation, resolve every manifest behavior to `documented`, `technical`, `duplicate`, `excluded`, or `blocked`.

Use these ID conventions:

- Behavior: `<repository>.<semantic-behavior-slug>`; preserve existing behavior IDs.
- Endpoint: `EP-<METHOD>-<normalized-route-slug>`.
- Data asset: `DATA-<kind>-<semantic-name>`.
- Field: `FIELD-<boundary-id>-<normalized-field-path>`.
- Validation rule: `VR-<semantic-rule-slug>`.
- External dependency: `DEP-<semantic-name>`.
- Runtime configuration: `CFG-<normalized-key-or-resource>`.
- Failure: `FAIL-<semantic-failure-slug>`.
- Outbound HTTP call: `HTTP-<dependency-or-operation-slug>`.
- External HTTP mapping: `MAP-<call-slug>-<direction>-<field-slug>`.

Prefer semantic IDs that survive discovery-order changes. Never renumber existing IDs merely because another entity is discovered.

## Canonical ownership

- Endpoint contracts are owned by endpoints, not behaviors.
- Behaviors link to every endpoint and contract that invokes them.
- Field definitions and validation rules are owned by the Field Pack.
- External HTTP mappings are owned by the Field Pack and reference a proven HTTP call and dependency.
- Data assets, lineage, and state transitions are owned by the Data Pack.
- Runtime configuration is owned by the Runtime Pack.
- External dependency details are owned by dependency stubs.
- Failures are owned by the global failure taxonomy; behavior tables reference failure IDs.
- Tech and BA flows are owned by separate `.work/flow-models/*.tech-flow.json` and `*.ba-flow.json` models. Their diagram captions are model-backed; their human document summaries are written independently. Never store one generic flow for both views.
- Flow models, behavior metadata, catalogs, and manifest relationships must reference passing claims. Every flow edge needs its own relationship `claim_ids`. They may organize facts but cannot create them.
- `tech-pack/behavior-catalog.yaml` is a strict projection of manifest behavior identity, status, paths, relationships, claims, repository/commit, analysis mode, and counts; it may not drift independently.

Behavior documents summarize and link to these canonical records. Do not duplicate full contracts, mappings, configuration matrices, dependency stubs, or failure definitions inside behaviors.

## Required navigation and coverage

Create `knowledge-map.md` as a Narrative human entry point and `coverage-report.md` as a Reference completeness statement. Let the Knowledge Map synthesize repository responsibility, reading paths, major behaviors, and important limitations from its document-level Claim set without per-sentence markers. The coverage report must account for discovered, documented, excluded, blocked, and unknown items across behaviors, endpoints, data assets, fields, validation rules, dependencies, configurations, failures, HTTP calls, and mappings. Bind exact inventory counts and coverage conclusions to the entity, absence, or coverage-gap Claims that justify them.

Targeted analysis is always `partial` unless a prior complete manifest is being refreshed. Complete coverage requires every discovered executable entry point and every indexed repository signal to have an explicit disposition.

## Cross-document consistency

- All documents use the same repository and source commit.
- Every required manifest document path exists. A duplicate, excluded, or blocked behavior may omit its individual document when the catalog records its disposition and reason. A non-material dependency may omit a stub; every material dependency must have one.
- Every manifest ID appears in its canonical matrix or catalog.
- All local Markdown links resolve inside the pack.
- Every endpoint points to a contract and at least one behavior.
- Every external dependency with a material contract has a stub.
- Every behavior failure references a failure ID from the taxonomy.
- Unknown and conflicting relationships remain explicit.
