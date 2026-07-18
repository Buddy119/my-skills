# Artifact Versioning and Migration Policy

Load this policy only for `--resume`.

## Trust boundaries

Migration and publication are different transactions, Receipts, and claims of trust.

- Resume Audit may create only `.work/migration-plan.yaml` and a Migration Planning Receipt.
- Migration may upgrade Artifact envelopes, preserve raw evidence, adopt working material, archive incompatible files, invalidate derived Artifacts, and update lifecycle state.
- Migration must not synthesize repository conclusions, publish reader documents, construct business Journeys/Scenarios, or claim that a Tech/BA Pack is complete.
- Synthesis and publication begin only after a committed Migration Receipt.

## Explicit identity

Every long-lived Artifact declares:

```yaml
artifact_type: "registered-type"
artifact_schema_version: "registered-version"
```

JSON operational Artifacts carry the same keys. `workflow_schema_version` describes executor lifecycle semantics; it is not a document-format version. The Repository Register's Artifact version is resolved through `artifact-schema.json`, which references `register-schema.json` for its table contract.

Use only explicit identity/version, Manifest entries, file existence, checksums, repository identity, source commit, and registry migration chains. Never choose a migration from:

- Headings or section names.
- Directory names such as an old BA layout.
- L1/L2/L3 or other prose.
- Presence/absence of an old Frontmatter business field.
- A table column label found by text search.

A missing version is `unknown`, even when the body resembles the latest template.

## Resume Audit

Run:

```bash
python3 <skill-root>/scripts/stage_executor.py resume \
  --repo <repository-root> \
  --state <output>/.work/analysis-state.yaml \
  --json
```

For a current Workflow 3 pack with a complete valid Artifact Manifest, resume the recorded normal stage and do not create a plan.

Otherwise inspect `.work/migration-plan.yaml` before continuing. Confirm:

- `plan_id`, repository, source commit, and source snapshot hash.
- Target Workflow and Registry versions.
- Each planned action and path.
- Invalidated Artifact types and their responsible rebuild stages.
- Expected archives, blocked reasons, and post-migration recovery stage.

The plan is JSON-compatible YAML so the standard-library executor can parse it deterministically. The plan may not contain repository knowledge conclusions.

If the plan is blocked, stop. Do not modify knowledge Artifacts or lifecycle state. If the Pack changes after planning, discard no evidence; rerun Resume Audit to produce a new snapshot-bound plan.

## Migration transaction

Begin automatically after a non-blocked plan:

```bash
python3 <skill-root>/scripts/stage_executor.py begin \
  --output <output> \
  --stage migration \
  --plan <output>/.work/migration-plan.yaml \
  --json
```

The formal Pack and State remain unchanged while the Candidate is prepared. Work only inside the returned Candidate.

Actions mean:

- `preserve`: do not alter the file or checksum.
- `mechanical-migrate`: perform only the registry-declared deterministic envelope conversion.
- `review-and-adopt`: preserve the source under `.work/legacy-artifacts/<plan-id>/`, review the working content, convert it to the current working schema, and keep uncertainty as `Unknown`, `Unresolved`, or a blocked Dossier.
- `archive-and-rebuild`: remove the Candidate copy after verified archive; do not replace it during Migration.
- `block`: no safe migration exists; no Migration may begin.

For review-and-adopt, do not make new repository-level conclusions. Keep existing evidence and citations, normalize only what can be safely mapped, and defer reconciliation to Synthesis.

Legacy `ba-pack/behaviors/` is additionally archived as one checksum-verified tree under `.work/legacy-ba-pack/<transaction-id>/`; this archive is created only by Migration commit.

Commit only after every retained Artifact has the current explicit type/version and all changes are inside the plan:

```bash
python3 <skill-root>/scripts/stage_executor.py commit \
  --output <output> \
  --transaction <migration-transaction-id> \
  --json
```

Do not pass `--semantic-result` or `--skip`. A successful Migration Receipt records preserved/migrated/archived/invalidated files and the next normal stage. Publication remains `stale` or `pending`.

## Unknown legacy Packs

When a Pack has no Artifact Manifest or explicit versions:

- Preserve same-commit Evidence Index, Working Behavior Catalog, Dossiers, and Repository Register as raw material.
- Copy review-and-adopt sources to the verified legacy-artifacts archive.
- Mark unsafe Dossiers blocked and unsafe Register relationships Unknown/Unresolved rather than inventing conversions.
- Archive Repository Synthesis, Business Model, Tech Pack, and BA Pack; do not treat their prose as current reader truth.
- Resume from Synthesis when the evidence and necessary Dossiers remain usable, otherwise Tracing or Inventory.

Do not infer a specific historical schema version.

## Receipts and completion

- Migration Planning, Migration, Synthesis, Tech/API Publication, Business Model, BA Publication, and Finalization have distinct Receipts.
- A Migration Receipt must not claim reader documents were published.
- A Publication Receipt must not contain migration/archive decisions outside its normal file replacement archive.
- `completed` requires a committed Finalization Receipt and zero unresolved invalidated Artifact types.
- A current `completed` State without its Finalization Receipt is an integrity failure. Do not rewrite State to manufacture a recovery point.
