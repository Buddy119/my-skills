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

One application endpoint may correlate to multiple external entries. Preserve every external route and mapping under the one application endpoint. Keep an unmatched external entry as its own register record until its operation role and reader-facing publication disposition are reconciled; being unmatched does not automatically make it a Matrix row.

When one protocol-support operation applies to several application methods on the same normalized path, associate it with one route group rather than duplicating it under each method. Use `repository.route-group.<normalized-path>` for a path group and omit the HTTP method. When a single shared protocol configuration spans unrelated paths, use `repository.protocol-group.<normalized-config-identity>` and list the covered paths or scopes in the classification basis.

## Operation role and publication projection

Classify reconciled records separately from their five-layer evidence statuses. Use only these operation roles:

- `application-endpoint` — executable application code implements the request path.
- `meaningful-external-exposure` — an external-only entry has independent caller or operational meaning even though no application implementation is observed in this repository.
- `protocol-support` — a declaration supplies transport- or protocol-level support without implementing an application behavior.
- `unresolved` — the available evidence cannot safely determine the role.

Then assign one publication disposition:

- `publish` — include the record in the reader-facing Matrix summary.
- `summarize` — keep complete register evidence and represent it only in the Matrix protocol-support summary.
- `publish-as-exception` — include an otherwise supporting or unresolved record because a gap or conflict needs reader attention.

Treat an operation as ordinary `protocol-support` only when all of these are established:

1. It is an OPTIONS operation or another protocol-support operation.
2. No executable application handler or business-processing path is present.
3. Its response is static, mock, or automatically generated.
4. Its observable result is limited to preflight, CORS, transport, or protocol headers/status rather than a business payload.
5. It does not read or change business state, invoke a business dependency, or implement independent authentication/query behavior.
6. It is explicitly related to an application route group or to a shared protocol-support configuration.

Do not classify from method, integration type, name, or same-path similarity alone. If any criterion is unresolved, use `unresolved`. A mock health/version response, a static business response, or a mock that invokes meaningful logic remains `meaningful-external-exposure` or `unresolved`, not ordinary protocol support.

Publish every `application-endpoint` and `meaningful-external-exposure`. Summarize ordinary `protocol-support` records instead of publishing one row per declaration. Publish protocol-support records individually as exceptions when they are orphaned, conflicting, environment-inconsistent, or cannot be safely related to an application route group. Publish every `unresolved` record until the uncertainty is resolved.

Operation role and publication disposition do not change evidence status. A protocol-support declaration may be `Confirmed` at its observed layer while still being summarized rather than promoted to a reader-facing endpoint.

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

Carry complete layer evidence, operation role, route-group association, classification basis, and publication disposition in the register. Publish only reader-relevant endpoints, meaningful external exposures, and exceptions in the Matrix summary. Add a compact protocol-support summary that reports ordinary supporting declarations and links once to the complete register evidence. Runtime evidence for a protocol-support operation remains evidence of that operation; it does not create a business endpoint.

In an API Contract, show only the application identity, any explicitly correlated external path, the external-reachability status, a material limitation when needed, and a link to the Matrix. Do not repeat the five-layer table or protocol-support inventory in the Contract.

Give each Matrix detail section an explicit stable HTML anchor derived from its endpoint/exposure ID by lower-casing and replacing punctuation with hyphens. Use that exact anchor in Contract and Overview links rather than relying on renderer-generated heading anchors.
