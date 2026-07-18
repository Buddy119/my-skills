# Stage Execution Policy

Use the bundled stage executor for every analysis. It is the sole owner of workflow lifecycle fields, transaction archives, promotion, receipts, and recovery. AI remains responsible for semantic understanding and prose.

## Core protocol

Run the executor by absolute path with the available `python3`:

```bash
python3 <skill-root>/scripts/stage_executor.py <command> ...
```

Initialize a new output:

```bash
python3 <skill-root>/scripts/stage_executor.py init \
  --repo <repository-root> \
  --output <output-dir> \
  --json
```

Resume an existing output:

```bash
python3 <skill-root>/scripts/stage_executor.py resume \
  --repo <repository-root> \
  --state <output-dir>/.work/analysis-state.yaml \
  --json
```

Resume has two outcomes:

- A current Workflow 3 Pack with a valid Artifact Manifest resumes its recorded normal stage.
- Any version mismatch or missing/invalid Manifest produces `.work/migration-plan.yaml` plus a Migration Planning Receipt without modifying State, Register, Synthesis, Pack, or Archive.

For a planned migration, begin the conditional stage before any normal stage:

```bash
python3 <skill-root>/scripts/stage_executor.py begin \
  --output <output-dir> \
  --stage migration \
  --plan <output-dir>/.work/migration-plan.yaml \
  --json
```

Migration and publication never share a transaction. Migration Candidate changes are limited by the Plan; commit it without `--semantic-result` or `--skip`. Read the Artifact Migration Policy for the full trust and adoption rules.

Begin the exact `current_stage` reported by status:

```bash
python3 <skill-root>/scripts/stage_executor.py begin \
  --output <output-dir> \
  --stage <current-stage> \
  --json
```

The command returns a transaction ID and Candidate root. Perform every write for that stage under the Candidate root. Do not write the same artifacts directly under the formal output root.

Commit only after semantic work and review are complete:

```bash
python3 <skill-root>/scripts/stage_executor.py commit \
  --output <output-dir> \
  --transaction <transaction-id> \
  --json
```

Use `--semantic-result complete` for synthesis. Use `--semantic-result complete|partial|blocked` for the Business Model. Skip only the API Contract stage when no application contracts exist or the BA publication stage when the Business Model is blocked:

```bash
python3 <skill-root>/scripts/stage_executor.py commit \
  --output <output-dir> \
  --transaction <transaction-id> \
  --skip \
  --reason "Evidence-based reason" \
  --json
```

## Behavior status ownership

During tracing, add Behavior entries to the Candidate state and catalog as part of inventory. After reviewing a dossier semantically, update its lifecycle through:

```bash
python3 <skill-root>/scripts/stage_executor.py mark-behavior \
  --output <output-dir> \
  --transaction <transaction-id> \
  --behavior-id <behavior-id> \
  --status understood \
  --dossier behavior-dossiers/<behavior-id>.md \
  --json
```

Use `blocked` only with a precise note. A subagent may write an assigned dossier but must not call `mark-behavior`, alter lifecycle fields, commit, abort, recover, archive, or write to formal Pack directories. The main agent reviews the artifact before changing its state.

## Failure and recovery

Use one status call instead of reconstructing progress manually:

```bash
python3 <skill-root>/scripts/stage_executor.py status \
  --output <output-dir> \
  --json
```

`failed` means the Candidate is retained and the formal Pack was not advanced. Correct the Candidate and retry the same transaction, or abort it:

```bash
python3 <skill-root>/scripts/stage_executor.py abort \
  --output <output-dir> \
  --transaction <transaction-id> \
  --json
```

When status reports an interrupted promotion or an inconsistent lock/journal, run:

```bash
python3 <skill-root>/scripts/stage_executor.py recover \
  --output <output-dir> \
  --json
```

Do not infer completion from an agent message. A stage is complete only when its committed Receipt exists and status has advanced. Do not modify the executor or another Skill script during analysis. If the executor or a required Validator cannot run, retain the Candidate and stop publication; do not fall back to manual lifecycle updates.

## Versioned Artifact and Register contracts

`assets/artifact-schema.json` is the registry for long-lived working, reader, and operational Artifacts. Every current Artifact declares its type and version, and `.work/artifact-manifest.json` records its path, identity, version, checksum, producing stage, invalidations, and latest transaction. `init` validates the registry against all active templates. Every successful commit atomically refreshes the Manifest.

Do not use headings, directory names, old fields, or prose to detect a legacy generation. Only explicit Artifact metadata, the Manifest, file existence, hashes, and registry migration chains may drive Resume.

`assets/register-schema.json` is the single source for the Register Schema version, sections, exact table columns, and mechanical domain prerequisites. `init` verifies that this Schema and `repository-register-template.md` are synchronized before creating output. Synthesis and later publication gates verify the Candidate Register against the same Schema.

During a repository analysis, edit Register rows only. Do not repair a validation failure by changing table headers, the Schema, a Validator, the executor, or the template. If a Skill developer intentionally changes the Register model, publish the Schema, template, Validator, executor, and contract tests as one change set.

A Repository Register declares `artifact_type: repository-register` and its registry-backed `artifact_schema_version`. A missing version is `unknown`; the Migration Plan uses `review-and-adopt`, preserves the raw Register, and resumes no later than `synthesis`. Never infer legacy fields from column positions.

Pack validation reports HTTP, Dependency, and Failure domain states as `valid`, `partial`, `invalid`, or `skipped`. A Schema failure invalidates only its domain; downstream checks that require a complete index are reported as `SKIPPED`, while unrelated validation continues. A Receipt with Primary Errors or skipped necessary groups does not represent complete validation. Receipts record Artifact Registry/Register versions, domain states, Primary Error count, skipped-group count, and suppressed-error count.

## Stage boundaries

Use this sequence without reordering:

0. `migration` (conditional Resume-only): version upgrade, raw-artifact preservation, incompatible-file archive, invalidation, and recovery-stage selection. It never publishes reader documents.

1. `inventory`: evidence index, working state, catalog, register, and entry-point inventory.
2. `tracing`: completed or explicitly blocked Behavior Dossiers and updated Register observations.
3. `synthesis`: reconciled Register and repository synthesis; commit with `--semantic-result complete`.
4. `tech-publication`: Tech Behaviors, overview, catalog, and applicable repository-level documents.
5. `api-contract-publication`: Endpoint Matrix and application API Contracts, or an evidence-based skip.
6. `business-model`: independent Business Model; commit with its reviewed semantic result.
7. `ba-publication`: BA overview, catalog, Journeys, Scenarios, and many-to-many backlinks, or a blocked-model skip.
8. `finalization`: three-pass review and complete mechanical validation.

All paths mentioned in workflow instructions are relative to the active Candidate root until the stage commits.
