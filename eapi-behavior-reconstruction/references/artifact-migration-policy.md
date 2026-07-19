# Artifact Versioning and Migration Policy

Load this policy only for `--resume`.

## Contents

- Trust boundaries and ownership matrix
- Explicit identity and registered transforms
- Resume Audit and Migration transaction
- Transform semantics
- Unknown legacy Packs
- Receipts and completion

## Trust boundaries

Migration and semantic reconstruction are different transactions, Receipts, and claims of trust:

```text
Resume Audit
→ deterministic Migration Transaction
→ Tracing / Synthesis / Business Model / Publication
```

- Resume Audit may create only `.work/migration-plan.yaml` and a Migration Planning Receipt.
- Migration may copy bytes, execute a registered deterministic schema transform, preserve explicit IDs, generate deterministic structural IDs, rewrite links declared by an ID map, archive incompatible files, create an empty current-schema working shell, invalidate derived Artifacts, and update lifecycle state.
- Migration must not reconcile dependencies, group failures, construct repository connections/shared behavior, model Journeys/Scenarios, judge Criticality/Risk/Caller Visibility/state meaning, or write reader prose.
- Semantic reconstruction begins only after a committed Migration Receipt.

## Ownership matrix

| Work | Owner | Allowed during Migration |
|---|---|---|
| Byte copy, checksum, count, archive, staging swap | Stage Executor | Yes |
| Frontmatter and lifecycle-envelope migration | Registered transform | Yes |
| Stable ID preservation or deterministic ID generation from one explicit source record | Registered transform | Yes |
| Link rewrite explicitly determined by an ID Map | Registered transform | Yes |
| Table split defined by an exact source schema | Registered transform | Yes |
| Legacy lifecycle row preservation as an unresolved Observation | Registered transform | Yes |
| Referential integrity and Manifest checks | Validator / Stage Executor | Yes |
| Dependency identity reconciliation | AI in Synthesis | No |
| Failure Pattern grouping and risk meaning | AI in Synthesis | No |
| Connection and Shared Behavior models | AI in Synthesis | No |
| Capability, Journey, and Scenario modeling | AI in Business Model | No |
| Reader-facing Tech/BA prose | AI in Publication | No |

Do not ask AI to perform copying or archival work. Do not ask a script to decide whether two dependencies, failures, operations, rules, or business scenarios mean the same thing.

## Explicit identity and registered transforms

Every long-lived Artifact declares:

```yaml
artifact_type: "registered-type"
artifact_schema_version: "registered-version"
```

JSON operational Artifacts carry the same keys. `workflow_schema_version` describes executor lifecycle semantics; it is not a document-format version. The Repository Register's Artifact version is resolved through `artifact-schema.json`, which references `register-schema.json`.

Use only explicit identity/version, Manifest entries, file existence, checksums, repository identity, source commit, and registry migration chains. Never select a migration from headings, directories, table labels, L1/L2/L3 text, old Frontmatter fields, or body prose. A missing version is `unknown` even when the file resembles a current template.

`assets/migration-transform-registry.json` is the only transform registry. A `mechanical-migrate` step is executable only when it has:

- Exact source Artifact type and schema version.
- Exact target Artifact type and schema version.
- Registered `transform_id` and handler.
- Source and target Schema declarations.
- A committed test fixture for the source schema.
- Input/output paths, ID rule, link rule, expected record/file counts, Manifest policy, and referential checks.

Do not register a Version `0`, `unknown`, or unversioned transform by guessing a historical format.

## Resume Audit

Run:

```bash
python3 <skill-root>/scripts/stage_executor.py resume \
  --repo <repository-root> \
  --state <output>/.work/analysis-state.yaml \
  --json
```

For a current Workflow 4 Pack with a complete valid Artifact Manifest, resume its explicit `current_stage` and do not create a Migration Plan.

Otherwise inspect `.work/migration-plan.yaml`. Confirm its Plan ID, repository, commit, source snapshot, target versions, steps, invalidated types, expected archives, blocked reasons, and recovery stage. The current release targets Workflow Schema `4`, Artifact Registry `6`, Migration Plan Schema `2`, Analysis State Artifact Schema `2`, Repository Synthesis Artifact Schema `3`, Repository Overview Artifact Schema `3`, Tech Behavior Artifact Schema `4`, API Contract Artifact Schema `3`, Artifact Manifest Schema `2`, and Stage Receipt Schema `2`.

Each mechanical step must visibly declare the Transform ID and its expected mechanical results. The plan is JSON-compatible YAML so the standard-library executor parses it deterministically. It must not contain repository knowledge conclusions.

If the plan is blocked, stop. If the Pack changes after planning, rerun Resume Audit; the snapshot-bound plan is no longer executable.

## Migration transaction

Begin automatically after a non-blocked plan:

```bash
python3 <skill-root>/scripts/stage_executor.py begin \
  --output <output> \
  --stage migration \
  --plan <output>/.work/migration-plan.yaml \
  --json
```

The executor automatically applies the plan and completes these mechanical checkpoints: plan verification, evidence preservation, Artifact migration, and migration validation. It writes transaction-local `mechanical-output-manifest.json` with Candidate hashes, Transform reports, input/output counts, ID Maps, archives/reinitializations, and referential-check results.

Actions mean:

- `preserve`: keep the exact source checksum.
- `mechanical-migrate`: execute the named registered transform and nothing else.
- `archive-and-rebuild`: checksum-archive the source, invalidate it, and defer its meaning to the named later stage. The executor may create an empty current-schema shell for State, Catalog, or Register so that the later stage has a safe structural target.
- `block`: no safe preservation or recovery path exists; Migration cannot begin.

There is no `review-and-adopt` action. The Candidate returned by `begin --stage migration` is executor-generated and sealed. AI may read the plan and Mechanical Output Manifest but must not edit, copy into, organize, or enrich the Candidate. Migration checkpoints are executor-owned and cannot be updated manually.

Commit the unchanged Candidate:

```bash
python3 <skill-root>/scripts/stage_executor.py commit \
  --output <output> \
  --transaction <migration-transaction-id> \
  --json
```

Commit recomputes every Candidate hash and rejects any manual or AI change before archive or promotion. Do not pass `--semantic-result` or `--skip`.

The Migration Receipt records Transform IDs, source/output hashes and counts, ID Maps, referential checks, archive manifests, invalidated Artifact types, and recovery stage. It must not contain Dependency identities, Failure Patterns, Journeys, Scenarios, or publication claims.

## Transform semantics

A registered transform may:

- Preserve a valid explicit ID.
- Generate a repeatable ID from one normalized explicit source record and retain its ID Map.
- Split an exact legacy flat HTTP row into Operation, Usage, and Mapping rows when the source schema exposes the necessary identity and call-site fields.
- Move legacy dependency and failure rows into Observation tables with `Reconciliation: Unresolved`.
- Move a Register Schema 1 lifecycle row into one stable `LIFE-OBS-*` record with `Reconciliation: Unresolved`, while preserving its original action, Before/Source, After/Destination, persistence, status, and evidence cells.
- Rewrite only links whose old/new identity is explicit in the ID Map.

A transform must not:

- Merge records from name, Host, URL, method/target similarity, field names, or prose.
- Generate `DEP-nnn`, `FAIL-nnn`, Connection/Shared models, Journeys, or Scenarios.
- Generate `OBJ-*`, `STATE-*`, `ACT-*`, or `TRANS-*`, or infer that an old lifecycle verb represented an object State or a Transition.
- Decide Criticality, Risk, Caller Visibility, State Outcome, business meaning, or remote behavior.
- Generate Repository Synthesis or Reader documents.

If an explicit old ID has conflicting structural rows, or the source lacks safe split fields, fail the registered transform or use `archive-and-rebuild`. Never repair the ambiguity semantically inside Migration.

Reader-first changes to Repository Synthesis, Tech Behaviors, or API Contracts do not by themselves mechanically invalidate a current Business Model or BA Pack. Preserve those business artifacts, then revalidate Scenario-to-Tech traceability and business-visible Variant differences against the rebuilt Tech Generation. Rebuild only the affected business artifacts when that semantic review finds a changed business fact or outcome.

## Unknown legacy Packs

An unknown or unversioned Artifact has no registered transform:

1. Preserve its exact bytes under `.work/legacy-artifacts/<plan-id>/`.
2. Invalidate the old Artifact and every derived Artifact declared by the Registry dependency graph.
3. Create only safe empty structural shells when required.
4. Resume from the earliest necessary `inventory`, `tracing`, or `synthesis` stage.

Unknown Evidence Index or Catalog normally returns to Inventory. Unknown or unusable Dossiers return to Tracing or Inventory. An unknown Register returns to Synthesis only when current Evidence and Dossiers remain sufficient; otherwise use the earlier stage. Old Reader Packs are archived and republished later. Never infer a historical schema from its text.

## Receipts and completion

- Migration Planning, Migration, Synthesis, Tech/API Publication, Business Model, BA Publication, and Finalization have distinct Receipts.
- A Migration Receipt must not claim Reader documents were published.
- A pre-Finalization Publication Receipt has `promotion_scope: generation` and does not publish the formal Pack.
- A Finalization Receipt has `promotion_scope: formal-pack` and `formal_pack_published: true` only after post-promotion validation succeeds.
- `completed` requires a committed Finalization Receipt and no unresolved invalidated Artifact type.
- A current `completed` State without its Finalization Receipt is an integrity failure; never rewrite State to manufacture a recovery point.
