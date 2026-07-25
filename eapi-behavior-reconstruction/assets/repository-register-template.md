---
artifact_type: "repository-register"
artifact_schema_version: "3"
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

## Lifecycle observations

Record what executable code shows before assigning semantic Object, State, Action, or Transition identities. One observation may reconcile to several typed records. Keep it `Unresolved` when the evidence cannot safely distinguish action, movement, and state change.

| Observation ID | Candidate object or resource | Behavior ID | Observed action, condition, or change | Before condition or source | After condition or destination | Persistence or observability | Status | Evidence | Reconciliation |
|---|---|---|---|---|---|---|---|---|---|
| `LIFE-OBS-001` | Candidate object/resource | `repository.behavior` | Exact observed operation or change | Before/source as observed | After/destination as observed | Stored, returned, emitted, derived, or Unknown | Confirmed | `path/to/file.ext:line` | `OBJ-001`, `ACT-001`, `TRANS-001`, or `Unresolved` |

## Business object and resource records

Create these records during synthesis. A resource location is not an Object State.

| Object ID | Logical identity | Type | Source, ownership, and storage boundary | Related behaviors | Observation IDs | Status | Unknowns or conflicts |
|---|---|---|---|---|---|---|---|
| `OBJ-001` | Stable object/resource identity | business-object/record/event/job/resource/other | Origin, owner, store, and repository boundary | `repository.behavior` | `LIFE-OBS-001` | Confirmed | None observed or limitation |

## Object state records

Use `Explicit` for declared status values, `Observable` for directly observable existence or durable conditions, and `Derived` only for a condition computed by an executable rule. A Derived State cannot be `Confirmed`.

| State ID | Object ID | State name | Basis | Definition or derivation | Persistence or observability | Status | Evidence |
|---|---|---|---|---|---|---|---|
| `STATE-001` | `OBJ-001` | Human-readable object condition | Explicit/Observable/Derived | Exact meaning or derivation rule | Field, record existence, predicate, or observation | Confirmed/Inferred/Conflicting/Unknown | `path/to/file.ext:line` |

## Processing action records

Read, Observe, Validate, Transform, Map, Persist, Delete, Invoke, Emit, and Route are actions. Persist or Delete may cause a Transition, but the action is not itself a State.

| Action ID | Object ID(s) | Behavior ID | Action role | Input or source | Output or destination | Related Transition(s) | Condition | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `ACT-001` | `OBJ-001` | `repository.behavior` | Read/Observe/Validate/Transform/Map/Persist/Delete/Invoke/Emit/Route/Other | Input, source, or boundary | Output, destination, or effect | `TRANS-001` or None | Invocation or branch condition | Confirmed | `path/to/file.ext:line` |

## State transition records

Create a Transition only when the repository supports both object conditions and the change point. Call order, similar names, data movement, or an emitted event alone does not prove a Transition.

| Transition ID | Object ID | From State ID | To State ID | Behavior ID | Causing Action ID(s) | Condition | Observable or persisted result | Transaction, side effect, or consistency impact | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `TRANS-001` | `OBJ-001` | `STATE-001` | `STATE-002` | `repository.behavior` | `ACT-001` | Change condition | Stored or externally observable result | Transaction boundary, side effect, partial state, or None observed | Confirmed/Inferred/Conflicting/Unknown | `path/to/file.ext:line` |

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

## Runtime configuration observations

Record executable reads and wiring before assigning one logical Config identity. Endpoint impact remains a candidate until synthesis confirms the Config → Behavior → Endpoint chain.

| Observation ID | Candidate configuration | Behavior ID | Read/wiring location | Effective value or source | Observed execution effect | Scope/condition | Status | Evidence | Reconciliation |
|---|---|---|---|---|---|---|---|---|---|
| `CFG-OBS-001` | Configuration key or wiring identity | `repository.behavior` | Exact location | Default/environment/Unknown | Observed availability, validation, branch, dependency, timing, result, state, or side-effect change | Condition | Confirmed | `path/to/file.ext:line` | `CFG-001` or `Unresolved` |

## Runtime configuration records

Populate during synthesis. Merge observations only when code or wiring proves one logical configuration identity.

| Config ID | Logical identity | Source/default | Scope/environment | Related behaviors | Observation IDs | Status | Unknowns or conflicts |
|---|---|---|---|---|---|---|---|
| `CFG-001` | Stable configuration identity | Repository default/environment/runtime/Unknown | Profile, environment, tenant, or other scope | Behavior IDs | `CFG-OBS-001` | Confirmed/Inferred/Conflicting/Unknown | Missing runtime value, precedence, or None observed |

## Runtime configuration impact records

Use Endpoint IDs only after synthesis confirms the affected Behavior implements the Endpoint. Keep exposure/deployment intent in Endpoint evidence rather than representing it as application execution.

| Impact ID | Config ID | Behavior ID | Endpoint ID(s) | Impact type | Condition/value | Execution difference | Caller/state/failure effect | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `CFG-001-I01` | `CFG-001` | `repository.behavior` | `repository.method-route` or None | application availability/authentication/authorization/validation/branch/variant/implementation selection/dependency target/timeout/retry/recovery/output/status/state/side effect/other | Condition and value source | Concrete executable difference | Caller-visible, state, recovery, or Unknown | Confirmed/Inferred/Conflicting/Unknown | `path/to/file.ext:line` |

## Java type records

Use these Java-only tables after semantic tracing. Include only production types that participate in executable Behaviors.

| Type ID | Fully qualified class | Role | Source set/module | Related behaviors | Related endpoints | Status | Evidence or limitation |
|---|---|---|---|---|---|---|---|
| `JTYPE-001` | `com.example.Type` | entry/service/repository/client/mapper/config/other | Production module/source set | Behavior IDs | Endpoint IDs or None | Confirmed/Inferred/Conflicting/Unknown | `path/to/file.java:line` or limitation |

## Java dependency edge records

| Edge ID | Source Type ID | Relation | Target Type ID | Behavior ID(s) | Binding/condition | Status | Evidence or limitation |
|---|---|---|---|---|---|---|---|
| `JEDGE-001` | `JTYPE-001` | calls/injects/implements/extends/creates/framework-dispatch/generated-delegate | `JTYPE-002` | Behavior IDs | Qualifier/Profile/runtime condition or None | Confirmed/Inferred/Conflicting/Unknown | `path/to/file.java:line` or limitation |

## Behavior and endpoint Java implementation bindings

| Binding ID | Behavior ID | Endpoint ID(s) or trigger | Exact entry symbol | Type IDs | Edge IDs | Runtime implementation selection | Status | Unknowns or evidence |
|---|---|---|---|---|---|---|---|---|
| `JIMPL-001` | `repository.behavior` | Endpoint IDs or non-API trigger | `com.example.Entry#method(Type)` | `JTYPE-001`, `JTYPE-002` | `JEDGE-001` | Qualifier/Primary/Profile/framework binding or unresolved candidates | Confirmed/Inferred/Conflicting/Unknown | Evidence and dynamic/generated limits |

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

| Observation ID | Failure category | Behavior ID | Failure/exception identity | Origin or throw/failure location | Handler | Handling and propagation | Caller-visible result | State outcome | Retry or recovery | Status | Evidence | Reconciliation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `FO-001` | Validation/business/dependency/data/configuration/runtime/other | `repository.behavior` | Exception type or executable condition | Exact call, boundary, or condition | Local catch, global advice, framework handler, or None observed | Translate/propagate/swallow/degrade/retry | Observed result or Unknown | Unchanged/Rolled back/Partial/Committed before failure/Unknown | Mechanism or Unknown | Confirmed | `path/to/file.ext:line` | `FAIL-001` or `Unresolved` |

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
