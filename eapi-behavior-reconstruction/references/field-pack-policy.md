# Field Pack policy

## Scope

Create a repository-wide field catalog for boundary-visible or behaviorally significant fields. Include fields that are read, validated, normalized, defaulted, persisted, emitted, returned, or used in a proven external HTTP mapping. Exclude incidental local variables with no contract, rule, state, or boundary significance.

Identify a field by boundary plus exact path, not by its bare name. Use dotted paths and `[]` for array elements.

Classify every manifest field with `boundary_kind` and `observation_kind`. Use `local-lookup` plus `local-lookup-key` when code merely evaluates `.get("x")`, `obj["x"]`, or an equivalent lookup on an opaque value. That proves the local literal key and result propagation only; it does not prove that an external response contains the field, that the field is required, or that it belongs to a remote schema. A Confirmed `outbound-http-response` field requires direct schema evidence and a `declared-contract-field` or `schema-field` observation.

## Field catalog

For each field record its stable field ID, boundary ID, boundary kind, observation kind, path, semantic meaning, type/format, requiredness, nullability, source/default, sensitivity classification only when directly established, related validation rules, related lineage/mapping IDs, status, and evidence.

Do not infer that two same-named fields have the same meaning. Do not reproduce customer data or secret values.

## Validation rules

Create independent validation-rule records for requiredness, missing/null/blank distinctions, type/format conversion, length/range/pattern, enum, conditional requiredness, mutual exclusion, cross-field rules, authorization-dependent rules, and rejection outcomes.

Link every rule to field IDs, endpoint/behavior IDs, failure IDs, and assertion-level tests when available. Distinguish schema declaration from executable enforcement.

## Field lineage

Use field lineage for internal reads, renames, normalization, calculation, persistence, and event/response propagation. Record source and target boundary IDs, transformation, condition/default, lossiness, status, and evidence.

Field lineage may describe API-to-domain, domain-to-storage, or event transformations, but must not call them upstream/downstream mappings.

## External HTTP mappings

Apply the separate field-mapping policy. Create an external HTTP mapping only after a real outbound HTTP call is proven. Store mappings in `external-http-mapping-matrix.md`; behavior documents reference mapping IDs rather than duplicate the full rows.

## Completeness

Coverage may be complete only when relevant boundary schemas or models have been enumerated. When only executable field reads are visible, mark the pack partial and identify missing schemas or opaque transformers.
