# Runtime configuration policy

## Scope

Record configuration that changes wiring, availability, routing, validation, data access, external communication, failure handling, or runtime behavior.

Include:

- Environment variables and property/config keys.
- Feature flags and mode switches.
- Endpoint, queue, topic, table, bucket, and secret/parameter references.
- Lambda runtime, memory, timeout, ephemeral storage, reserved concurrency, and architecture when defined.
- Trigger filters, batching, maximum concurrency, retry policy, visibility timeout, retention, and DLQ.
- Environment or stage substitutions and defaults.

## Matrix fields

For every configuration record include stable ID, key/resource, category, definition source, read/use location, type/allowed values, requiredness, default, affected endpoints/behaviors/dependencies/failures, behavior when absent or invalid, environment variance, status, and evidence.

Separate a code default from a deployment default. Record conflicts between code, IaC, tests, and examples.

## Safety

Record secret and parameter names only. Never access live stores or reproduce values, tokens, customer identifiers, account numbers, or credentials. Mark a value `Sensitive: Yes` only when evidence supports the classification.

## Completeness

Account for direct and indirect configuration reads, IaC substitutions, and configuration passed into shared libraries. Mark dynamic or deployment-only values `Unknown` and describe the missing environment artifact.
