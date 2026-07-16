# Behavior dossier policy

## Purpose

A behavior dossier is a private working model of one end-to-end behavior. Build it while reading code, tests, configuration, and infrastructure. Use it to preserve understanding across batches; do not publish it as reader documentation.

The dossier is not a Claim Ledger. Write connected explanations, working tables, and evidence notes. Do not assign IDs to ordinary observations or label every sentence with an evidence status.

## Trace one behavior as a whole

Follow the executable path from trigger to observable result. Combine route, handler, controller, service, repository, client, and transformer code when they implement one flow.

Answer these questions before declaring the behavior understood:

1. What triggers the behavior, and how is the entry point wired at runtime?
2. What input is parsed, normalized, or rejected?
3. Which decisions materially change the path or result?
4. What happens on the main successful path?
5. What data is read, created, updated, or deleted?
6. What state transitions occur, and under which conditions?
7. Which external boundaries are crossed, and what observable contract is used?
8. What output, event, message, or other side effect is produced?
9. What important failures, retries, compensation, or partial-success outcomes exist?

Explain unknown answers rather than creating plausible behavior.

## Evidence while reading

- Capture small source ranges when a code path, rule, mapping, or outcome becomes clear.
- Prefer a coherent paragraph supported by several evidence anchors over a list of atomic claims.
- Inspect one or two concrete test assertions per behavior when relevant tests exist. Prioritize a material failure assertion.
- Record test absence or inaccessible shared code as a limitation.
- Treat names and comments as supporting context, not proof of business purpose.

## Repository register contribution

Before leaving the behavior, add applicable observations to the repository register:

- Endpoint identity and owning behavior.
- Data resources, business objects, and state transitions.
- Input or output field rules.
- Proven outbound HTTP calls and mappings.
- Behavior-changing runtime configuration.
- External dependencies.
- Material failures.
- Relationships to other behaviors.

Do not create empty entries for categories that are not observed.

## Understanding gate

Move a behavior from `tracing` to `understood` only when:

- The dossier contains a natural-language end-to-end narrative.
- The main path and material decisions are clear.
- Data, state, boundaries, outputs, and failures were checked.
- Tests, IaC, and configuration were inspected or explicitly unavailable.
- Repository-external internals remain qualified as unknown.
- Key evidence and unresolved questions are recorded.
- Applicable repository-register sections were updated.

This is a reasoning gate. Do not delegate it to a structural validator. If the gate cannot be met, keep tracing or mark the behavior `blocked` with the precise missing evidence and impact.

## Batch discipline

Work on at most five behaviors before persisting dossiers, updating the register and state file, and reviewing behavior boundaries. Do not keep many incomplete behavior models only in conversation context.

