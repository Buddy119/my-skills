# Evidence policy

## Purpose

Describe observable implementation behavior without presenting reconstructed intent as historical fact.

## Evidence statuses

### Confirmed

Use `Confirmed` when direct evidence supports the statement. Prefer two independent sources for high-risk rules, such as implementation plus test or implementation plus IaC.

Keep the complete evidence status in Dossiers, the Repository Register, Repository Synthesis, and the Business Model. In formal Reader artifacts, `Confirmed` is the unmarked baseline. Preserve `Inferred`, `Unknown`, and `Conflicting` beside the affected identity or label using the exact public qualifiers from the Reader Presentation Schema. Group Tech source support into Source Notes; do not require one citation per row. BA documents trace through Tech Behaviors instead of exposing source paths.

Examples:

- A validation branch explicitly rejects a closed customer.
- A unit test asserts the rejection.
- A deployment template connects an SQS queue to the handler.

### Inferred

Use `Inferred` when the conclusion reasonably follows from indirect evidence but is not explicitly established.

Examples:

- A class or variable name suggests business purpose.
- A client call implies an external validation whose internals are unavailable.
- An event name suggests a consumer behavior not present in this repository.

State the reasoning and what evidence would confirm it.

### Conflicting

Use `Conflicting` when code, tests, configuration, IaC, comments, or schemas disagree. Cite both sides and describe the operational uncertainty. Do not silently select one source.

### Unknown

Use `Unknown` when available material cannot answer the question. State why it matters and what artifact or owner could resolve it.

## Evidence priority

Use the following as a guide, not an automatic truth ranking:

1. Executable production path at the recorded commit.
2. Deployment/IaC and runtime configuration definitions.
3. Tests that execute the relevant path.
4. API or event schemas.
5. Comments, names, examples, and stale local documentation.

When higher-ranked evidence conflicts with lower-ranked evidence, record the conflict if the lower-ranked artifact is still expected to be authoritative, such as a published contract.

## Citation rules

- Use repository-relative POSIX paths.
- Include a line or tight line range: `src/handler.ts:42-48`.
- Cite the definition or executable branch, not only a search result or import.
- Attach citations to a coherent paragraph, meaningful rule, flow explanation, or table row. Do not turn each sentence into an atomic claim merely to attach a citation.
- Cite tests separately from production code.
- Cite concrete assertions or expectations, not only test filenames, classes, or method declarations.
- When relevant tests exist for a behavior, extract one or two assertions that prove a core outcome; prioritize a failure-path assertion.
- Do not cite generated build output when a source definition is available.
- Never reproduce secrets, tokens, customer identifiers, or production payloads.

Evidence statuses apply to material conclusions and uncertainty, not to every connective sentence in readable prose.

## Java semantic-navigation evidence

- Treat Java language-service results as navigation and cross-confirmation, not as the final citation format or proof of runtime execution.
- Cite repository source for the call site, exact method definition, implementation class, DI/configuration binding, framework entry wiring, and relevant test assertion.
- `Find References` establishes that references exist. Separate production references from test references, and do not infer that every reference runs in a deployed path.
- Incoming and outgoing call hierarchy establish static relationships the language service can resolve. They do not expose every proxy, reflection, generated, event-driven, or framework-invoked edge.
- Interface implementations and overrides identify candidates. Use injection and runtime-binding evidence before naming the implementation selected for a behavior.
- When a language service is unavailable, not ready, or incomplete, lower confidence for affected call edges and record the exact fallback evidence used. Do not convert a text-name match into `Confirmed` solely because no better tool is available.

## Scope rules

- Treat other repositories as black boxes until separately analyzed.
- Describe an outbound request or emitted event, but do not assert what the remote service does internally.
- Distinguish source-defined behavior from environment-specific deployment behavior.
- Record missing IaC, indirect environment variables, reflection, dynamic loading, and generated code as limitations.
- Record Java proxy/AOP, annotation callbacks, event dispatch, Lombok, MapStruct, Spring Data, reflection, and generated-code boundaries when they prevent static call confirmation.
- Treat application routes, external-entry declarations, environment deployment intent, observed runtime deployment, and external reachability as separate evidence layers. A source or configuration artifact proves only the layer it directly represents.
- Keep endpoint evidence collection separate from reader-facing publication. A `Confirmed` declaration remains in the register even when its reconciled operation role is protocol support and its publication disposition is summary-only.
- Keep Dependency Observations separate from Dependency Contracts. A confirmed call or resource access proves the local boundary, not that similarly named observations share one remote participant or that the remote system provides unobserved guarantees.
- Keep Failure Observations separate from Failure Patterns. A caught exception proves the observed path, not repository-wide recurrence, rollback of every side effect, safe retry, compensation, or business severity.
- Keep Lifecycle Observations separate from Object, State, Action, and Transition reconciliation. A read, validation, mapping, write call, external invocation, event emission, source, store, or destination does not by itself prove an Object State or State Transition.
- Support every State with a precise object-condition definition and an Explicit, Observable, or Derived basis. Derived States remain `Inferred` even when their predicate is executable. Support every Transition with same-Object From/To States and the executable change point; chronological order alone is not evidence.
- Treat `Required`, `Degradable`, `Optional`, and Failure risk-attention labels as synthesized conclusions that require the relevant path, state, visibility, and recovery evidence. Use `Unknown` when decisive evidence is unavailable.
- Treat a repository connection as a synthesized projection of an executable boundary or explicit trigger binding. A dependency name, host, URL, class, client, resource, configuration key, import, or file-role marker does not by itself prove that a connection exists or establish its direction and role.
- Support connection direction, boundary type, interaction role, exchanged concepts, configuration selection, criticality, and failure/state impact from the corresponding executable path and reconciled Endpoint, Dependency, Lifecycle, Config, or Failure evidence. Qualify each unresolved dimension instead of letting one known attribute prove the others.
- Treat a Shared Rule or Shared Behavior-shaping Component as proven only when the same implementation, explicit rule source, or configuration binding affects at least two Behaviors or independent entry paths. Similar naming, duplicated code shape, or a widely imported behavior-neutral utility does not establish shared behavioral semantics.
- Treat Business Journeys and Scenarios as synthesized models that require supported business context, participants, object meaning, decisions, or visible outcomes across the completed Tech facts. An Entry Point, Endpoint, event, Tech Behavior, branch, validation, Dependency, or exception proves only its technical observation; it does not automatically prove a business modeling unit.
- Require every published Business Scenario to link at least one supporting Tech Behavior, while allowing a Tech Behavior to support zero, one, or several Scenarios. Keep historical requirements, remote journey stages, policy intent, and unsupported business meaning `Unknown`.
- Accept runtime endpoint evidence only from repository-local or user-supplied sanitized artifacts with an identifiable environment and observation. Do not query live infrastructure or reproduce credentials and payloads.

## Required functional review flags

Raise an explicit open question when evidence is incomplete for:

- Idempotency, duplicate delivery, and concurrency.
- Transaction boundaries and partial failure.
- Object-state definitions, Before/After conditions, and whether a write or emission actually changes the modeled object.
- Retry, timeout, DLQ, and compensation behavior.
- Monetary precision, currency, date, time zone, and ordering.
- Backward compatibility of API or event contracts.
