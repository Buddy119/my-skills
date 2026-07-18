---
artifact_type: "repository-register"
artifact_schema_version: "1"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
register_status: "working|reconciled"
---

# Repository working register

Maintain this register while tracing behaviors. It is a shared notebook, not a Claim Ledger and not a final reader document. Add only observed items and reconcile duplicates during synthesis.

## Java semantic analysis context

Use this section once for a Java repository; remove it for non-Java repositories. Summarize the environment, not a language-server operation log.

- **Java project model:** Build system, modules, source sets, and relevant generated-source roots.
- **Semantic-navigation status:** `used|degraded|unavailable`.
- **Project import/readiness:** What was successfully modeled and what was not.
- **Available capabilities used:** Symbol/definition, references, call hierarchy, type hierarchy, implementations/overrides, or other existing capabilities.
- **Fallback investigation:** Exact signatures, imports, annotations, injection, build/configuration, and tests used when semantic navigation was incomplete.
- **Repository-wide limitations:** Dynamic/generated boundaries and conclusions whose call graph or implementation binding remains uncertain.

## Endpoint evidence records

Record direct observations separately before correlating endpoints. Use only `application-route`, `external-entry`, `environment-intent`, and `runtime-deployment` as evidence layers; reachability is derived later.

| Evidence ID | Evidence layer | Observed method/route/handler/target | Environment or scope | Related candidate | Status | Evidence |
|---|---|---|---|---|---|---|
| `EP-EV-001` | application-route | `METHOD /route` → handler | Application source | Candidate name or None | Confirmed | `path/to/file.ext:line` |

## Endpoint reconciliation

Populate this section during repository synthesis. Preserve unmatched external entries instead of forcing them into an application endpoint, then classify their operation role before deciding how they appear in the reader-facing Matrix.

Use `application-endpoint`, `meaningful-external-exposure`, `protocol-support`, or `unresolved` for Operation Role. Use `publish`, `summarize`, or `publish-as-exception` for Publication Disposition. Ordinary protocol-support records require evidence that they have no application handler, business payload, state access, or business dependency call; method or mock/static integration alone is insufficient.

| Endpoint or Exposure ID | Operation Role | Publication Disposition | Related Route Group | Application Route | External Entry Declaration | Environment Deployment Intent | Observed Runtime Deployment | External Reachability | Behavior | Contract | Classification basis | Correlation, conflict, or gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `repository.method-route` | application-endpoint | publish | `repository.route-group.normalized-route` | Confirmed — `METHOD /route` | Not observed | Not observed | Not observed | Not observed | `repository.behavior` | Planned application contract | Executable handler implements the application route | No external evidence observed |

When one protocol-support operation covers several methods on the same normalized route, use `repository.route-group.<normalized-path>` without an HTTP method and use `summarize` rather than duplicating it under every method. For one shared configuration spanning unrelated paths, use `repository.protocol-group.<normalized-config-identity>` and state its covered scope. Use `publish-as-exception` for orphaned, conflicting, environment-inconsistent, or unresolved support records. Keep every underlying `EP-EV-nnn` observation in Endpoint evidence records regardless of publication disposition.

## Business objects, data resources, and state changes

| Object or resource | Behavior ID | Operation | From state/source | To state/destination | Condition | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Object/resource | `repository.behavior` | Read/Create/Update/Delete | Source/state | Destination/state | Condition | Confirmed | `path/to/file.ext:line` |

## Field validation and internal transformation observations

| Boundary or model | Field(s) | Behavior ID | Rule or transformation | Result when violated | Status | Evidence |
|---|---|---|---|---|---|---|
| API/event/model | `field.path` | `repository.behavior` | Required/default/format/computation | Result | Confirmed | `path/to/file.ext:line` |

## Outbound HTTP operation records

Only use these three outbound HTTP sections after locating an executable HTTP/HTTPS invocation. Keep operation identity separate from call-site usage and field mapping.

Merge usages only when Method, Logical Target, and Client Operation all match. When legacy Call IDs are merged, retain the lexicographically first ID as canonical and list the others under Aliases.

| Call ID | Method | Logical Target | Client Operation | Observable Purpose | Related Behaviors | Aliases | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| HTTP-001 | POST | External service/path | Client operation | Boundary purpose | `repository.behavior` | None | Confirmed | `path/to/file.ext:line` |

## Outbound HTTP operation usages

Record every executable call site. The same Call ID may have multiple usages and behaviors.

| Usage ID | Call ID | Behavior ID | Executable Call Site | Invocation Condition or Config | Status | Evidence |
|---|---|---|---|---|---|---|
| HTTP-001-U01 | HTTP-001 | `repository.behavior` | Exact client invocation | Condition/configuration | Confirmed | `path/to/file.ext:line` |

## External HTTP field mapping records

Use `all` only when a mapping applies identically to every registered usage of its Call ID. Otherwise list the applicable Usage IDs. Do not repeat Method, Target, Client Operation, or Behavior in mapping rows.

| Mapping ID | Call ID | Applies to Usage(s) | Direction | Source Field(s) | Target Field(s) | Transformation | Condition/Default | Lossy | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| FM-001 | HTTP-001 | all | eapi-to-external | `source.path` | `target.path` | Rename/conversion | Condition/default | No | Confirmed | `path/to/file.ext:line` |

## Runtime configuration effects

| Config | Behavior ID | Read/wiring location | Effective value or source | Behavioral effect | Scope/condition | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Config name | `repository.behavior` | Location | Default/environment/unknown | How execution changes | Condition | Confirmed | `path/to/file.ext:line` |

## External dependency observations

Record each executable boundary observation before grouping dependencies. A dependency observation is evidence, not a reader-facing contract. Use `Unresolved` when the observation cannot yet be assigned safely.

| Observation ID | Candidate dependency | Boundary type | Behavior ID | Operation or resource | Exchanged concept or observed effect | Availability observation | Status | Evidence | Reconciliation |
|---|---|---|---|---|---|---|---|---|---|
| `DEP-OBS-001` | System/resource candidate | HTTP/event/queue/store/runtime-boundary/other | `repository.behavior` | Call, resource, event, or operation | Concept sent, consumed, read, written, or affected | Failure/fallback/state observation or Unknown | Confirmed | `path/to/file.ext:line` | `DEP-001` or `Unresolved` |

## Dependency contract records

Populate during repository synthesis. Create one record per proven logical external participant or resource boundary, not one per Behavior or call site. `Criticality by usage` may retain different classifications for different operations or behaviors.

| Dependency ID | Logical identity | Type | Repository-observed role | Related operations | Related behaviors or capabilities | Criticality by usage | Observation IDs | Aliases | Status | Unknowns or conflicts |
|---|---|---|---|---|---|---|---|---|---|---|
| `DEP-001` | Stable logical dependency identity | service/database/event-resource/storage/runtime-boundary/other | What this dependency enables at the repository boundary | `DEP-001-OP01` | Behavior/capability IDs | `repository.behavior`: Required/Degradable/Optional/Unknown | `DEP-OBS-001` | None | Confirmed | Remote internals, conflicts, or None observed |

## Dependency operation records

Keep operations beneath their parent Dependency. Link an existing `HTTP-nnn` Call ID when the operation is an outbound HTTP boundary; do not copy its field mappings here.

| Operation ID | Dependency ID | Boundary reference | Invocation or resource | Exchanged concepts | Behaviors or capabilities | Criticality by usage | Unavailability, fallback, and state impact | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `DEP-001-OP01` | `DEP-001` | `HTTP-001` or stable event/resource identity | Executable invocation, event, or resource | Conceptual input/output/effect | Behavior/capability IDs | `repository.behavior`: Required/Degradable/Optional/Unknown | Visible failure, degradation, alternative path, partial state, or Unknown | Confirmed | `path/to/file.ext:line` |

## Failure observations

Record the observed failure path before assigning a repository-wide Pattern. Keep handling, visibility, state, retry, and recovery separate so failures with different outcomes are not merged from a shared exception name.

| Observation ID | Failure category | Behavior ID | Trigger or source | Handling and propagation | Caller-visible result | State outcome | Retry or recovery | Status | Evidence | Reconciliation |
|---|---|---|---|---|---|---|---|---|---|---|
| `FO-001` | Validation/business/dependency/data/configuration/runtime/other | `repository.behavior` | Condition or failure source | Catch/translate/propagate/swallow/degrade | Observed result or Unknown | Unchanged/Rolled back/Partial/Committed before failure/Unknown | Mechanism or Unknown | Confirmed | `path/to/file.ext:line` | `FAIL-001` or `Unresolved` |

## Failure pattern reconciliation

Populate during repository synthesis. Group observations only when their trigger, propagation, caller visibility, state outcome, and retry/recovery semantics are materially equivalent.

| Pattern ID | Category | Trigger or source | Observation IDs | Behaviors or capabilities | Related dependencies | Caller visibility | State outcome | Retry safety | Recovery | Risk attention | Conflicts or unknowns | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `FAIL-001` | Normalized repository failure category | Shared trigger/source description | `FO-001` | Behavior/capability IDs | `DEP-001` or None | Explicit error/Degraded result/Success with loss/Swallowed/Async only/Unknown | Unchanged/Rolled back/Partial/Committed before failure/Unknown | Safe/Conditional/Unsafe/Unknown | Automatic retry/Rollback/Compensation/Manual/None observed/Unknown | High/Medium/Low/Unknown | Material variation or None observed | `path/to/file.ext:line` |

## Cross-behavior relationships

| Source behavior | Relationship | Target behavior | Connecting object/event/state | Status | Evidence |
|---|---|---|---|---|---|
| `repository.behavior-a` | Produces/enables/shares/consumes | `repository.behavior-b` | Object/event/state | Confirmed/Inferred | `path/to/file.ext:line` |

## Register conflicts and unresolved items

| Item | Affected behaviors | Conflict or unknown | Why it matters | Evidence needed |
|---|---|---|---|---|
| Item | Behavior IDs | Explanation | Impact | Artifact or owner |
