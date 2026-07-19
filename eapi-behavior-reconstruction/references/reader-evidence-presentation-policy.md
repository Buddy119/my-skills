# Reader evidence presentation policy

Load this policy when publishing or reviewing Tech/BA Reader artifacts.

## Working facts and Reader projection

Keep complete `Confirmed|Inferred|Conflicting|Unknown` status and source evidence in Dossiers, the Repository Register, Repository Synthesis, and Business Model. Reader documents are projections, not copies of those tables.

Treat `Confirmed` as the Reader baseline. Do not publish a generic `Status`, `Evidence`, `Evidence level`, or `Status and limitation` column in an affected Reader table. Do not repeat `Confirmed` beside every item.

For a non-Confirmed item, append exactly one qualifier to its primary label or stable identity:

```markdown
`STATE-002` *(Inferred)*
[Dependency](#dep-002) *(Unknown)*
Business outcome *(Conflicting)*
```

Use only `*(Inferred)*`, `*(Unknown)*`, and `*(Conflicting)*`. Explain the reason in the nearest limitation, Unknown, conflict, or boundary text. Never use a qualifier to replace that explanation.

## Grouped Tech source notes

Attach a small number of evidence markers to coherent prose, one rule, or a group of table rows:

```markdown
The rules and mappings in this section are supported by [E1](#e1) and [E2](#e2).

## Source notes

<a id="e1"></a> **E1** — `src/main/...:10-24` supports validation and mapping.
<a id="e2"></a> **E2** — `src/test/...:40-55` verifies rejection behavior.
```

One note may support several related rows. Do not require one marker per row or sentence. Every used marker must have one definition, every definition must be used, and every definition must contain at least one valid repository citation.

BA documents must not contain source paths or Source Notes. Preserve their factual traceability through Journey–Scenario–Tech Behavior links and use qualifiers only for material uncertainty.

## Status-sensitive exceptions

Do not apply the generic-column rule to:

- Endpoint Matrix layer Status/Evidence, because comparing independent evidence layers is its purpose.
- API Contract completeness, Application Route, and reachability status.
- Failure Taxonomy Caller Visibility, State Outcome, Retry Safety, Recovery, and Risk Attention.
- Artifact Frontmatter and operational lifecycle State.

Controlled criticality, state basis, operation role, publication disposition, and failure semantics are domain information, not generic evidence labels; retain them when they help the reader distinguish outcomes.

## Review boundary

Mechanical checks may validate table headers, allowed qualifier spelling, marker/definition relationships, citation bounds, and projection of Register status onto stable Reader identities. They must not count `Confirmed`, require a fixed number of notes, require evidence on every row, or decide from prose whether an item deserves a particular status.
