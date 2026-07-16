# Endpoint exposure evidence policy

## Purpose

Keep application implementation, external entry declarations, environment intent, observed deployment, and external reachability separate. Apply this policy whenever evidence from any endpoint layer is found. It is technology-neutral and independent of the API field-contract L1/L2/L3 model.

## Five-layer model

1. **Application Route** — executable application code registers or implements a method, route, or handler.
2. **External Entry Declaration** — a boundary definition declares an externally addressable route and integration target.
3. **Environment Deployment Intent** — repository configuration says an entry should be enabled, bound, or deployed in an environment.
4. **Observed Runtime Deployment** — repository-local or user-supplied sanitized runtime material records an actual deployment or route observation.
5. **External Reachability Assessment** — a derived conclusion from the preceding layers, not an independent source.

One layer never proves another. In particular, an application route does not prove exposure; an external declaration does not prove a handler exists; deployment intent does not prove deployment; and deployment does not by itself prove reachability under every access condition.

## Layer statuses

Use only these statuses for all five endpoint cells:

- `Confirmed` — direct evidence establishes this layer.
- `Conflicting` — evidence inside the layer conflicts, or explicitly related layers disagree.
- `Unknown` — relevant evidence indicates the layer may exist, but its state cannot be determined.
- `Not observed` — no evidence for this layer was found inside the allowed analysis scope.

Do not use `Inferred` as a layer status. Behavioral conclusions may continue to use the general evidence statuses.

## Collect before correlating

Record every direct observation as a separate `EP-EV-nnn` register row before forming an endpoint:

- Preserve the observed method, route, handler, target, rewrite, environment, and source wording.
- Record the layer and its own evidence; do not copy another layer's evidence into the row.
- Treat schemas or route catalogs as declarations at their observed layer, not proof of application execution.
- Treat an OpenAPI route as schema-level API evidence by default. Classify it as an External Entry Declaration only when repository wiring uses that artifact to configure or publish the boundary.
- Treat repository deployment configuration as intent unless supplied runtime material proves application.
- Treat an HTTP probe, deployed-route inventory, or deployment output as runtime evidence only when its provenance, environment, and observed result are present and contain no secrets.

Do not access a live cloud account, cluster, gateway, credential, or production endpoint. If runtime material is absent, record that absence rather than trying to obtain it.

## Correlation rules

Correlate evidence only through an explicit relationship such as:

- A handler, function, controller, service, or integration target reference.
- A route/base-path rewrite or mapping definition.
- A deployment binding that names both the external entry and application target.
- Equivalent wiring whose target identity can be followed to executable application code.

Method/route equality, naming similarity, directory proximity, or shared business words identify candidates only. Do not merge them without binding evidence.

Use the existing stable endpoint ID based on the application method and application route after an application route is confirmed. Give an unmatched external-only record a stable exposure ID using `repository.external.<method>-<normalized-external-route>`; when method or route is absent, use a normalized declaration name. Add a stable suffix only for collisions.

One application endpoint may correlate to multiple external entries. Preserve every external route and mapping under the one application endpoint. An unmatched external entry remains its own Endpoint Matrix row.

## Reachability assessment

- Use `Confirmed` only when confirmed application implementation, external entry, environment binding, and observed runtime evidence form an explicit, unbroken, non-conflicting chain under the stated access conditions.
- Use `Unknown` when external exposure or deployment intent exists but one or more required links are missing.
- Use `Conflicting` when explicitly related route, target, environment, or runtime evidence disagrees and the conflict changes the chain.
- Use `Not observed` when no external-exposure evidence exists for an application route. An external-entry or environment-intent record already shows exposure intent, so incomplete correlation or deployment makes reachability `Unknown`, not `Not observed`.

Do not describe an endpoint as public, exposed, deployed, or externally reachable unless the corresponding layer is `Confirmed`. Authentication success is not required for reachability when the observed result proves the endpoint is addressable, but state the access conditions and observed response.

## Behavior and contract boundary

- Create an API behavior only from an executable application route or handler path.
- Generate a full API Contract only when the Application Route is `Confirmed` and its executable request/response path can be traced.
- Keep the contract's `method` and `route` as application identities. Record different external routes separately.
- Do not create a Behavior, API Contract, or empty contract stub for an external-only or configuration-only record.
- Keep `contract_status` about request, response, and error-contract completeness. Keep exposure statuses separate.

Keep endpoint environment intent in the endpoint register and Matrix. Add it to Runtime Config Matrix only when the same configuration also changes executable application behavior. A named external target is not an executable dependency contract unless repository code actually invokes or implements that boundary.

Publish every reconciled application endpoint and every unmatched external exposure in Endpoint Matrix. Carry detailed layer evidence in the register and concise reader-facing evidence in the Matrix and applicable Contract.

Give each Matrix detail section an explicit stable HTML anchor derived from its endpoint/exposure ID by lower-casing and replacing punctuation with hyphens. Use that exact anchor in Contract and Overview links rather than relying on renderer-generated heading anchors.
