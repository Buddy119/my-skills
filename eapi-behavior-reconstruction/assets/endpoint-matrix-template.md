---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
coverage_status: "complete|partial|blocked"
---

# Endpoint matrix

Use one row per reconciled application endpoint and one row per unmatched external exposure. Status cells use only `Confirmed`, `Conflicting`, `Unknown`, or `Not observed`.

## Endpoint summary

| Endpoint or Exposure ID | Application Route | External Entry Declaration | Environment Deployment Intent | Observed Runtime Deployment | External Reachability | Behavior | Contract |
|---|---|---|---|---|---|---|---|
| `repository.method-route` | Confirmed — `METHOD /application-route` | Not observed | Not observed | Not observed | Not observed | [Behavior](behaviors/repository.behavior.md) | [Contract](contracts/repository.method-route.api-contract.md) |
| `repository.external.method-route` | Not observed | Confirmed — `METHOD /external-route` | Unknown | Not observed | Unknown | — | — |

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

Explain explicit target, binding, route rewrite, or mapping evidence. When multiple external entries share this application route, list every external identity here. For unmatched records, explain why they were not attached to an application behavior or contract.

Create one explicit HTML anchor before every endpoint/exposure detail heading. Derive it from the ID by lower-casing and replacing punctuation with hyphens so Contract and Overview links remain stable.

## Unknowns and conflicts

Record unresolved correlation, authentication, deployment, route, target, environment, and reachability questions without upgrading missing layers.
