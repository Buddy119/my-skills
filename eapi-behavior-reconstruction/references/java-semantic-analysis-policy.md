# Java semantic analysis policy

## Purpose and scope

Use an available Java language service (LSP) to reduce mistakes caused by matching filenames or method names. Apply this policy only after Java source or a Java Maven/Gradle project model is detected. It changes how call relationships are discovered; it does not replace source, dependency-injection, runtime configuration, or test evidence.

Do not build a repository-wide call graph for its own sake. Trace the symbols and edges needed to understand each executable behavior.

## Semantic-first tracing order

When the current environment already exposes a usable Java language service and the relevant project/module is imported:

1. Locate the exact entry type, symbol, method signature, and method structure.
2. Go to each critical definition rather than selecting a same-name text match.
3. Inspect outgoing calls from orchestration, decision, data-access, and external-boundary methods.
4. Inspect incoming callers for shared methods and distinguish production source sets from tests.
5. Find references where call hierarchy is incomplete, again separating production and test references.
6. Trace interface implementations, overrides, and type hierarchy for each behavior-affecting abstraction.
7. Inspect constructor, field, and parameter types at injection points.

Use `rg` and direct file reads for repository inventory, configuration, annotations, framework wiring, generated/dynamic boundaries, and as fallback. Treat a name or text hit as a candidate until an exact signature and source relationship are confirmed.

## Confirm critical call edges twice

For a call edge that affects the behavior's route, decision, state, external interaction, output, or failure:

- Use semantic navigation to confirm the static caller, callee, definition, or implementation candidates when possible.
- Read the executable call site and target definition.
- When an abstraction is injected, inspect the binding evidence that selects a runtime implementation.
- Use tests as corroboration, not as proof that a production path is wired identically.

Record source locations rather than screenshots or raw language-server output. A language-service result is a navigation aid; formal evidence remains the repository source at the analyzed commit.

## Spring and dependency-injection selection

Inspect the complete injection path before choosing an implementation:

- Constructor, field, and method-parameter injection types.
- `@Bean` factories and configuration imports.
- `@Qualifier` values at both injection and bean-definition sites.
- `@Primary` precedence.
- `@Profile`, conditional beans, and behavior-changing runtime properties.
- Component scanning and exclusions.
- Test-specific replacements, mocks, and profiles.

An implementation list proves candidates, not selection. If multiple candidates remain and no binding evidence chooses one, list them and mark the selected implementation `Inferred` or `Unknown`. Do not let class names or apparent business fit break the tie.

## Framework entries and semantic blind spots

No incoming Java caller does not mean an entry is unreachable. Confirm controllers, listeners, scheduled methods, Lambda handlers, lifecycle callbacks, and event consumers through annotations, configuration, registration code, or IaC.

Explicitly record edges that static navigation may not resolve:

- Spring proxies and AOP advice.
- Reflection and dynamic class loading.
- Annotation callbacks and framework dispatch.
- Application events and messaging frameworks.
- Lombok-generated members.
- MapStruct and other generated mappers.
- Spring Data derived or generated repository methods.
- Generated sources absent from the workspace or project model.

Do not invent a direct caller/callee relationship across these boundaries. Describe the observed dispatch or generation mechanism and its limit.

## Degraded and unavailable operation

Use `degraded` when some semantic capability works but project import, modules, generated sources, or results are incomplete. Use `unavailable` when no usable Java semantic capability is exposed.

In either case:

1. Do not install extensions, a JDK, build dependencies, or a language server.
2. Do not edit build files, source, generated code, workspace settings, or Skill scripts.
3. Trace exact fully qualified types and complete method signatures through imports, call sites, annotations, constructor injection, bean/configuration definitions, build files, and tests.
4. Compare parameter and return types to avoid joining overloads or unrelated same-name methods.
5. Separate production callers from test-only references.
6. Record unresolved callers, implementations, and dynamic edges, and lower the affected conclusion to `Inferred` or `Unknown`.

Mark a behavior `blocked` only when the missing semantic relationship prevents a safe account of its main flow. Otherwise complete the dossier with the limitation visible.

## Recording requirements

Record the environment once in the repository register and the behavior-specific trace in every Java dossier. Include status, exact entry signature, critical definitions and outgoing calls, callers or framework-entry evidence, implementation candidates, binding evidence, blind spots, and impact.

Formal Tech documents should not reproduce the operation log. Carry forward only unresolved call, implementation, or coverage limits that affect what a developer may conclude. BA documents should contain no LSP terminology unless a technical uncertainty materially prevents a business conclusion; describe the business uncertainty instead.

During synthesis, translate the reviewed trace into the Java implementation
model rather than a raw LSP log:

- one `JTYPE-*` per executable production type;
- one `JEDGE-*` per supported `calls`, `injects`, `implements`, `extends`,
  `creates`, `framework-dispatch`, or `generated-delegate` relationship;
- one `JIMPL-*` slice connecting an Endpoint or non-API trigger to its Behavior,
  exact entry symbol, relevant types, edges, and runtime selection.

Define a shared type once even when several Behaviors use it. Do not include
test classes as implementation nodes or unrelated production classes as an
inventory. Link each Behavior's Implementation Sequence to its `JIMPL-*` slice.
