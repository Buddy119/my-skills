---
name: eapi-behavior-reconstruction
description: Reconstruct one observable business or integration behavior from a single EAPI microservice or AWS Lambda code repository and produce a standardized Markdown behavior document with source evidence, confidence labels, upstream/internal/downstream field mappings, rules, side effects, failures, tests, and external dependency stubs. Use when Codex needs to reverse-engineer undocumented behavior from code, explain what a Lambda/API/event consumer currently does, document API or event field transformations, document one repository incrementally, or create behavior documents that can later be connected for cross-service impact analysis.
---

# EAPI Behavior Reconstruction

Reconstruct the system's observable current behavior without inventing the missing historical intent. Analyze one behavior at a time and keep every material conclusion traceable to code, tests, configuration, or infrastructure definitions.

## Required inputs

Obtain:

- The local path of one repository.
- A behavior selector: Lambda handler, API route, event consumer, scheduled job, or a concise behavior name.
- An output directory, or default to `behavior-docs/<repository-name>/` beside the working context.

If no behavior selector is supplied, inventory candidate entry points and present up to five concise candidates. Recommend the smallest representative behavior, then ask the user to choose before performing deep reconstruction.

## Load the evidence policy

Read [references/evidence-policy.md](references/evidence-policy.md) completely before analyzing source code. Apply its status and citation rules to every output.

When the behavior receives, transforms, or emits structured data, also read [references/field-mapping-policy.md](references/field-mapping-policy.md) completely and apply it to the field mapping metadata and prose.

## Workflow

### 1. Establish the analysis boundary

- Confirm the repository root and record the current Git commit with `git rev-parse HEAD` when available.
- Treat generated artifacts, vendored dependencies, build output, coverage output, and lockfiles as secondary evidence unless they define deployment behavior.
- Do not access credentials, secret values, production customer data, or live AWS resources.
- State excluded or unreadable areas in the final document.

### 2. Locate the entry point

Search with `rg` and `rg --files` first. Look for the selector in:

- Lambda handlers and runtime registration.
- API Gateway, SAM, CDK, Serverless, Terraform, or CloudFormation definitions.
- SQS, SNS, EventBridge, DynamoDB Stream, Kinesis, S3, and schedule triggers.
- Step Functions tasks.
- Tests, fixtures, schemas, and deployment configuration.

Record the concrete trigger and entry-point evidence before tracing deeper.

### 3. Trace the behavior

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

### 4. Trace field mappings

Trace mappings at every visible boundary:

- Upstream request or event to EAPI transport/domain model.
- EAPI model to persistence representation.
- EAPI model to downstream request, command, response, or event.

Record direct copies, renames, nested-path changes, type/format conversions, enum translations, defaults, constants, conditional mappings, computed fields, one-to-many or many-to-one transformations, masking, truncation, and intentionally dropped fields. Cite both the source-field read and target-field write when they occur at different locations.

Use stable boundary names that can later connect documents. Do not manufacture an upstream or downstream field name that is unavailable in this repository; create an `Unknown` mapping endpoint or an open question instead.

### 5. Separate observations from interpretation

- Describe what the implementation currently does.
- Do not claim to recover the original requirement or design rationale.
- Label each material statement as `Confirmed`, `Inferred`, `Conflicting`, or `Unknown` according to the evidence policy.
- Record contradictions rather than choosing the most convenient source.
- Record unanswered transactional, retry, security, or data-consistency questions explicitly.

### 6. Create the behavior document

Copy and complete [assets/behavior-document-template.md](assets/behavior-document-template.md). Preserve the YAML keys even when a list is empty so future aggregation remains deterministic.

Use stable connection names when the code provides them:

- HTTP method plus normalized route.
- Event source plus event/detail type or schema name.
- Queue, topic, event bus, table, state machine, and Lambda logical names.
- Fully qualified external client or operation names when resource names are indirect.

Use repository-relative POSIX paths in evidence citations. Cite as `path/to/file.ext:line` or `path/to/file.ext:start-end`.

### 7. Validate

Run:

```bash
python3 scripts/validate_behavior_doc.py <behavior-document.md> --repo <repository-root>
```

Resolve validation errors before delivering. Treat warnings as review items and mention any warning that remains intentional.

### 8. Deliver

Report:

- The behavior document path.
- The analyzed repository and commit.
- The behavior entry point.
- The strongest confirmed findings.
- The important inferred, conflicting, or unknown items.
- The validation result.

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
