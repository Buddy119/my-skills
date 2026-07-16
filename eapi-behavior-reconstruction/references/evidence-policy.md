# Evidence policy

## Purpose

Describe observable implementation behavior without presenting reconstructed intent as historical fact.

## Evidence statuses

### Confirmed

Use `Confirmed` when direct evidence supports the statement. Prefer two independent sources for high-risk rules, such as implementation plus test or implementation plus IaC.

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

## Scope rules

- Treat other repositories as black boxes until separately analyzed.
- Describe an outbound request or emitted event, but do not assert what the remote service does internally.
- Distinguish source-defined behavior from environment-specific deployment behavior.
- Record missing IaC, indirect environment variables, reflection, dynamic loading, and generated code as limitations.

## Required functional review flags

Raise an explicit open question when evidence is incomplete for:

- Idempotency, duplicate delivery, and concurrency.
- Transaction boundaries and partial failure.
- Retry, timeout, DLQ, and compensation behavior.
- Monetary precision, currency, date, time zone, and ordering.
- Backward compatibility of API or event contracts.
