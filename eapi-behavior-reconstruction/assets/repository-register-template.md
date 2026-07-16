---
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

Populate this section during repository synthesis. Preserve unmatched external entries instead of forcing them into an application endpoint.

| Endpoint or Exposure ID | Application Route | External Entry Declaration | Environment Deployment Intent | Observed Runtime Deployment | External Reachability | Behavior | Contract | Correlation, conflict, or gap |
|---|---|---|---|---|---|---|---|---|
| `repository.method-route` | Confirmed — `METHOD /route` | Not observed | Not observed | Not observed | Not observed | `repository.behavior` | Planned application contract | No external evidence observed |

## Business objects, data resources, and state changes

| Object or resource | Behavior ID | Operation | From state/source | To state/destination | Condition | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Object/resource | `repository.behavior` | Read/Create/Update/Delete | Source/state | Destination/state | Condition | Confirmed | `path/to/file.ext:line` |

## Field validation and internal transformation observations

| Boundary or model | Field(s) | Behavior ID | Rule or transformation | Result when violated | Status | Evidence |
|---|---|---|---|---|---|---|
| API/event/model | `field.path` | `repository.behavior` | Required/default/format/computation | Result | Confirmed | `path/to/file.ext:line` |

## Proven outbound HTTP calls and mappings

Only use this section after locating an executable outbound HTTP invocation.

| Call ID | Behavior ID | Method and target | Direction | Source field(s) | Target field(s) | Transformation/condition | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| HTTP-001 | `repository.behavior` | `POST external/path` | EAPI→external or external→EAPI | `source.path` | `target.path` | Rename/default/conversion | Confirmed | `path/to/file.ext:line` |

## Runtime configuration effects

| Config | Behavior ID | Read/wiring location | Effective value or source | Behavioral effect | Scope/condition | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Config name | `repository.behavior` | Location | Default/environment/unknown | How execution changes | Condition | Confirmed | `path/to/file.ext:line` |

## External dependencies

| Dependency | Behavior ID | Boundary/operation | Observed request or resource | Observed response/effect | Failure impact | Status | Evidence |
|---|---|---|---|---|---|---|---|
| System/library/resource | `repository.behavior` | Operation | Contract fragment | Contract fragment | Impact or Unknown | Confirmed | `path/to/file.ext:line` |

## Failure observations

| Failure category | Behavior ID | Trigger or condition | Handling and visible result | Retry/recovery/partial state | Status | Evidence |
|---|---|---|---|---|---|---|
| Validation/business/data/dependency/runtime | `repository.behavior` | Condition | Result | Mechanism or Unknown | Confirmed | `path/to/file.ext:line` |

## Cross-behavior relationships

| Source behavior | Relationship | Target behavior | Connecting object/event/state | Status | Evidence |
|---|---|---|---|---|---|
| `repository.behavior-a` | Produces/enables/shares/consumes | `repository.behavior-b` | Object/event/state | Confirmed/Inferred | `path/to/file.ext:line` |

## Register conflicts and unresolved items

| Item | Affected behaviors | Conflict or unknown | Why it matters | Evidence needed |
|---|---|---|---|---|
| Item | Behavior IDs | Explanation | Impact | Artifact or owner |
