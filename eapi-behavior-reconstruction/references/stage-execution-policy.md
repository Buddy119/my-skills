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

## Versioned Register contract

`assets/register-schema.json` is the single source for the Register Schema version, sections, exact table columns, and mechanical domain prerequisites. `init` verifies that this Schema and `repository-register-template.md` are synchronized before creating output. Synthesis and later publication gates verify the Candidate Register against the same Schema.

During a repository analysis, edit Register rows only. Do not repair a validation failure by changing table headers, the Schema, a Validator, the executor, or the template. If a Skill developer intentionally changes the Register model, publish the Schema, template, Validator, executor, and contract tests as one change set.

A same-commit legacy Register with a missing or unsupported `register_schema_version` resumes from `synthesis`. Preserve Dossiers and raw evidence, archive the old Register transactionally, and rebuild the current structure. Do not infer legacy fields from their column positions.

Pack validation reports HTTP, Dependency, and Failure domain states as `valid`, `partial`, `invalid`, or `skipped`. A Schema failure invalidates only its domain; downstream checks that require a complete index are reported as `SKIPPED`, while unrelated validation continues. A Receipt with Primary Errors or skipped necessary groups does not represent complete validation. Receipts record the Register Schema version, domain states, Primary Error count, skipped-group count, and suppressed-error count.

## Stage boundaries

Use this sequence without reordering:

1. `inventory`: evidence index, working state, catalog, register, and entry-point inventory.
2. `tracing`: completed or explicitly blocked Behavior Dossiers and updated Register observations.
3. `synthesis`: reconciled Register and repository synthesis; commit with `--semantic-result complete`.
4. `tech-publication`: Tech Behaviors, overview, catalog, and applicable repository-level documents.
5. `api-contract-publication`: Endpoint Matrix and application API Contracts, or an evidence-based skip.
6. `business-model`: independent Business Model; commit with its reviewed semantic result.
7. `ba-publication`: BA overview, catalog, Journeys, Scenarios, and many-to-many backlinks, or a blocked-model skip.
8. `finalization`: three-pass review and complete mechanical validation.

All paths mentioned in workflow instructions are relative to the active Candidate root until the stage commits.
