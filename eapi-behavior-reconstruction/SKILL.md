---
name: eapi-behavior-reconstruction
description: Automatically discover and reconstruct observable business and integration behaviors from a single EAPI microservice or AWS Lambda code repository, starting with only a local repository path. Produce a repository overview, behavior catalog, and standardized evidence-backed behavior documents with upstream/internal/downstream field mappings, rules, side effects, failures, tests, and external dependency stubs. Use when Codex needs to determine what an unfamiliar repository does, reverse-engineer undocumented code, explain Lambda/API/event-consumer behavior, document field transformations, or create behavior documents for later cross-service impact analysis.
---

# EAPI Behavior Reconstruction

Discover and reconstruct a repository's observable current behaviors without requiring the user to understand its handlers or architecture. Keep every material conclusion traceable to code, tests, configuration, or infrastructure definitions.

## Required inputs

Require only the local path of one repository.

Accept these optional inputs when supplied:

- A behavior selector to restrict analysis to one Lambda handler, API route, event consumer, scheduled job, or named behavior.
- An output directory; otherwise default to `behavior-docs/<repository-name>/` beside the working context.

When only the repository path is supplied, enter repository auto-discovery mode. Do not ask the user to identify handlers, choose behaviors, explain the repository, or rank entry points. Perform those tasks from source evidence.

## Load the evidence policy

Read [references/evidence-policy.md](references/evidence-policy.md) completely before analyzing source code. Apply its status and citation rules to every output.

When the behavior receives, transforms, or emits structured data, also read [references/field-mapping-policy.md](references/field-mapping-policy.md) completely and apply it to the field mapping metadata and prose.

## Workflow

### 1. Establish the analysis boundary

- Confirm the repository root and record the current Git commit with `git rev-parse HEAD` when available.
- Treat generated artifacts, vendored dependencies, build output, coverage output, and lockfiles as secondary evidence unless they define deployment behavior.
- Do not access credentials, secret values, production customer data, or live AWS resources.
- State excluded or unreadable areas in the final document.

### 2. Inventory the repository

Search with `rg` and `rg --files` first. Detect:

- Languages, runtimes, frameworks, build files, and module boundaries.
- Lambda handlers and runtime registration.
- API Gateway, SAM, CDK, Serverless, Terraform, or CloudFormation definitions.
- SQS, SNS, EventBridge, DynamoDB Stream, Kinesis, S3, and schedule triggers.
- Step Functions tasks.
- Tests, fixtures, schemas, and deployment configuration.
- Data stores, outbound clients, shared libraries, Lambda Layers, and environment-controlled dependencies.

Group related trigger, handler, and orchestration code into distinct behaviors. Avoid counting the API route, Lambda handler, and service method as three behaviors when they implement one flow. Keep health checks, framework glue, migrations, and deployment-only utilities in the catalog but classify them as technical behaviors.

Create:

```text
behavior-docs/<repository-name>/
├── repository-overview.md
├── behavior-catalog.yaml
└── behaviors/
```

Copy [assets/repository-overview-template.md](assets/repository-overview-template.md) and [assets/behavior-catalog-template.yaml](assets/behavior-catalog-template.yaml). Populate every discovered behavior with a stable ID, trigger, entry point, category, evidence, and analysis status.

If a behavior selector was supplied, use the inventory only to locate that behavior and analyze it in targeted mode. Otherwise continue automatically through every discovered business and integration behavior.

### 3. Plan internal analysis batches

Order behaviors by dependency and signal:

1. Public API and synchronous request handlers.
2. Event, queue, stream, and scheduled consumers.
3. Shared orchestration behaviors referenced by multiple entry points.
4. Technical behaviors.

Process at most five behaviors in one internal batch to keep evidence focused. Persist completed documents and update `behavior-catalog.yaml`, then continue with the next batch without asking the user to select it. Stop early only when the repository is inaccessible, required permissions are unavailable, or source ambiguity makes further claims unsafe; record the exact blocker and partial coverage.

### 4. Trace each behavior

Follow the executable path from entry point to observable outcomes:

1. Parse and map the input.
2. Apply validation and authorization.
3. Execute domain or orchestration logic.
4. Read and write data.
5. Call external services.
6. Publish events or enqueue messages.
7. Map the response.
8. Handle failures, retries, idempotency, compensation, and partial success.

Inspect tests alongside implementation. Inspect IaC and configuration for runtime facts such as trigger filters, timeouts, retries, DLQs, permissions, resource names, and environment-dependent wiring.

Stop at repository boundaries. Represent calls or events owned elsewhere as external dependency stubs; do not infer the other repository's internal behavior.

### 5. Trace field mappings

Trace mappings at every visible boundary:

- Upstream request or event to EAPI transport/domain model.
- EAPI model to persistence representation.
- EAPI model to downstream request, command, response, or event.

Record direct copies, renames, nested-path changes, type/format conversions, enum translations, defaults, constants, conditional mappings, computed fields, one-to-many or many-to-one transformations, masking, truncation, and intentionally dropped fields. Cite both the source-field read and target-field write when they occur at different locations.

Use stable boundary names that can later connect documents. Do not manufacture an upstream or downstream field name that is unavailable in this repository; create an `Unknown` mapping endpoint or an open question instead.

### 6. Separate observations from interpretation

- Describe what the implementation currently does.
- Do not claim to recover the original requirement or design rationale.
- Label each material statement as `Confirmed`, `Inferred`, `Conflicting`, or `Unknown` according to the evidence policy.
- Record contradictions rather than choosing the most convenient source.
- Record unanswered transactional, retry, security, or data-consistency questions explicitly.

### 7. Create each behavior document

Copy and complete [assets/behavior-document-template.md](assets/behavior-document-template.md). Preserve the YAML keys even when a list is empty so future aggregation remains deterministic.

Write each document to `behaviors/<behavior-id>.md`. After validation, update the corresponding catalog entry from `discovered` to `documented` or `blocked`.

Use stable connection names when the code provides them:

- HTTP method plus normalized route.
- Event source plus event/detail type or schema name.
- Queue, topic, event bus, table, state machine, and Lambda logical names.
- Fully qualified external client or operation names when resource names are indirect.

Use repository-relative POSIX paths in evidence citations. Cite as `path/to/file.ext:line` or `path/to/file.ext:start-end`.

### 8. Validate

Run:

```bash
python3 scripts/validate_behavior_doc.py <behavior-document.md> --repo <repository-root>
```

Resolve validation errors before delivering. Treat warnings as review items and mention any warning that remains intentional.

### 9. Deliver

Report:

- The repository overview, behavior catalog, and generated behavior document paths.
- The analyzed repository and commit.
- The number of discovered, documented, technical, and blocked behaviors.
- The strongest confirmed findings.
- The important inferred, conflicting, or unknown items.
- Validation results for every behavior document.

Do not modify application source code unless the user separately requests an implementation change.

## Quality bar

Before completing, verify that:

- The document covers the happy path and failure paths.
- Business rules cite source or test evidence.
- Data reads, writes, events, and external calls appear in both YAML metadata and prose.
- Every observed cross-boundary field mapping appears in `field_mappings` metadata and the `Field mappings` section.
- Each mapping records transformation, condition, default, lossiness, confidence, and evidence; use explicit empty or `Unknown` values when unresolved.
- AWS behavior comes from IaC/configuration evidence when available.
- External dependencies are named but not over-interpreted.
- The document records the Git commit and analysis limitations.
- No secret value or customer data is reproduced.
- The catalog accounts for every discovered executable entry point as documented, technical, duplicate, excluded, or blocked.
