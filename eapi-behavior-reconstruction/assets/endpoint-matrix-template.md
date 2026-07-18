---
artifact_type: "endpoint-matrix"
artifact_schema_version: "1"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Endpoint matrix

This is the reader-facing projection of the complete endpoint register. Use one row per application endpoint, meaningful external exposure, and published exception. Summarize ordinary protocol-support declarations instead of publishing one row per declaration. Status cells use only `Confirmed`, `Conflicting`, `Unknown`, or `Not observed`.

## Endpoint summary

| Endpoint or Exposure ID | Operation Role | Application Route | External Entry Declaration | Environment Deployment Intent | Observed Runtime Deployment | External Reachability | Behavior | Contract |
|---|---|---|---|---|---|---|---|---|
| `repository.method-route` | application-endpoint | Confirmed — `METHOD /application-route` | Not observed | Not observed | Not observed | Not observed | [Behavior](behaviors/repository.behavior.md) | [Contract](contracts/repository.method-route.api-contract.md) |
| `repository.external.method-route` | meaningful-external-exposure | Not observed | Confirmed — `METHOD /external-route` | Unknown | Not observed | Unknown | — | — |

Do not list an ordinary `protocol-support` record here. Include a protocol-support or unresolved record only when its register disposition is `publish-as-exception`.

## Protocol-support summary

Include this section only when ordinary protocol-support observations were summarized.

| Measure | Result |
|---|---|
| Raw protocol-support declarations | Count from the reconciled register |
| Related route groups | Count and concise scope |
| Independently published exceptions | Count and Endpoint/Exposure IDs, or None |
| Sources and environments | Concise source and scope summary |

Keep the full per-observation evidence in the [repository register](../.work/repository-register.md#endpoint-evidence-records). Explain the shared configuration or route-group relationship that justified aggregation. Do not repeat one line for every preflight declaration.

## Evidence and reconciliation notes

<a id="repository-method-route"></a>

### `repository.method-route`

| Layer | Observed value | Status | Evidence |
|---|---|---|---|
| Application Route | `METHOD /application-route` → handler | Confirmed | `path/to/file.ext:line` |
| External Entry Declaration | None observed | Not observed | Repository scope reviewed |
| Environment Deployment Intent | None observed | Not observed | Repository scope reviewed |
| Observed Runtime Deployment | None supplied | Not observed | Analysis boundary |
| External Reachability Assessment | No external exposure evidence | Not observed | Derived from the preceding rows |

Explain explicit target, binding, route rewrite, or mapping evidence. Include the operation-role and publication basis when it affects why a record appears in the Matrix. When multiple external entries share this application route, list every external identity here. For published unmatched records, explain why they were not attached to an application behavior or contract. Do not create detail sections for ordinary summarized protocol-support records.

Create one explicit HTML anchor before every endpoint/exposure detail heading. Derive it from the ID by lower-casing and replacing punctuation with hyphens so Contract and Overview links remain stable.

## Unknowns and conflicts

Record unresolved correlation, authentication, deployment, route, target, environment, and reachability questions without upgrading missing layers.
