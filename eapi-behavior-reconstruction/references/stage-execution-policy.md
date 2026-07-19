# Stage Execution Policy

Use the bundled stage executor for every analysis. It is the sole owner of workflow lifecycle fields, Checkpoint Ledgers, Working Generations, archives, promotion, Receipts, and recovery. AI remains responsible for semantic understanding and readable prose.

## Lifecycle authority

Workflow Schema 4 uses `current_stage` as the only stage fact. Never add, restore, or consult `phase`. The executor alone updates:

- `current_stage` and `stage_status`.
- `current_checkpoint` and `checkpoint_status`.
- `active_transaction`.
- `working_generation_id` and `published_generation_id`.
- `publication_status` and `formal_drift_status`.
- Synthesis, Business Model, and publication lifecycle results.

Natural-language status, a subagent response, a file count, or a partially populated directory never advances lifecycle state.

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

- A current Workflow 4 Pack with a valid Artifact Manifest resumes its explicit `current_stage`.
- Any version mismatch or missing/invalid Manifest produces `.work/migration-plan.yaml` plus a Migration Planning Receipt without modifying State, Register, Synthesis, Reader Packs, or Archive.

For a planned migration, begin the conditional stage before any normal stage:

```bash
python3 <skill-root>/scripts/stage_executor.py begin \
  --output <output-dir> \
  --stage migration \
  --plan <output-dir>/.work/migration-plan.yaml \
  --json
```

Migration and publication never share a transaction. The executor generates and seals the Migration Candidate from the Plan; AI must not edit it. Read the Artifact Migration Policy before inspecting or committing any migration result.

Begin the exact `current_stage` reported by status:

```bash
python3 <skill-root>/scripts/stage_executor.py begin \
  --output <output-dir> \
  --stage <current-stage> \
  --json
```

The response includes a transaction ID, Candidate root, Generation information when applicable, and the stage Checkpoint Ledger. Perform every write for that stage under the returned Candidate. Do not write the corresponding files directly under the formal output root.

## Checkpoint protocol

Every stage has a fixed ordered Checkpoint contract. For normal semantic stages, after completing and reviewing one item, record it through:

```bash
python3 <skill-root>/scripts/stage_executor.py checkpoint \
  --output <output-dir> \
  --transaction <transaction-id> \
  --checkpoint <checkpoint-id> \
  --status complete \
  --json
```

Allowed statuses are `in-progress`, `complete`, `skipped`, `blocked`, and `failed`. `skipped`, `blocked`, and `failed` require `--reason`. Update checkpoints in order. A commit is rejected while a necessary checkpoint is `pending`, `in-progress`, or `failed`. A stage-level `--skip` marks that stage's checkpoints skipped using the stage reason.

Checkpoint Ledgers are operational progress records, not business evidence. They do not judge whether a Dependency, Failure Pattern, Journey, or prose conclusion is semantically correct.

Migration is the exception: its four checkpoints are completed only by the executor while it creates the deterministic Candidate and Mechanical Output Manifest. Do not call `checkpoint` for Migration.

Fixed Checkpoints:

| Stage | Ordered checkpoints |
|---|---|
| `migration` | `plan-verification`, `evidence-preservation`, `artifact-migration`, `migration-validation` |
| `inventory` | `project-detection`, `entrypoint-inventory`, `evidence-index` |
| `tracing` | `behavior-tracing`, `coverage-review` |
| `synthesis` | `endpoint-reconciliation`, `outbound-http-reconciliation`, `dependency-reconciliation`, `failure-reconciliation`, `lifecycle-config-reconciliation`, `connection-shared-model`, `synthesis-review` |
| `tech-publication` | `tech-behaviors`, `repository-overview`, `repository-reference-docs`, `tech-cross-links`, `tech-validation` |
| `api-contract-publication` | `endpoint-matrix`, `api-contracts`, `api-backlinks`, `api-validation` |
| `business-model` | `capability-object-model`, `journey-scenario-model`, `tech-coverage`, `business-model-review` |
| `ba-publication` | `journeys`, `scenarios`, `ba-overview-catalog`, `ba-backlinks`, `ba-validation` |
| `finalization` | `mechanical-review`, `fact-sampling`, `readability-review`, `release-readiness` |

For a normal stage, commit only after semantic work, checkpoints, and review are complete:

```bash
python3 <skill-root>/scripts/stage_executor.py commit \
  --output <output-dir> \
  --transaction <transaction-id> \
  --json
```

Use `--semantic-result complete` for Synthesis. Use `--semantic-result complete|partial|blocked` for the Business Model. Skip only the API Contract stage when no Contract files, API Behaviors, or declared `api_contracts` exist, or skip the BA publication stage when the Business Model is blocked:

```bash
python3 <skill-root>/scripts/stage_executor.py commit \
  --output <output-dir> \
  --transaction <transaction-id> \
  --skip \
  --reason "Evidence-based reason" \
  --json
```

## Working Generation and formal publication

Inventory and Tracing commit their working navigation and Behavior artifacts normally. Beginning with Synthesis, the executor creates one Working Generation:

```text
.work/execution/generations/<generation-id>/
├── candidate-root/
├── generation-manifest.json
└── stage-history.json
```

Synthesis, Tech Publication, API Contract Publication, Business Model, and BA Publication each start from the current Generation and atomically replace only the Generation snapshot on commit. They do not replace the previously published `.work` knowledge artifacts, `tech-pack/`, or `ba-pack/`. On a first run, formal Reader Packs may remain absent until Finalization.

Each transaction records an immutable `baseline-manifest.json` and necessary baseline snapshot. Except for executor-owned State, lock, Receipt, journal, plan, and Manifest paths, the formal output is immutable while a Generation is in progress. If an agent bypasses Candidate and changes formal knowledge artifacts, commit:

1. detects the drift;
2. restores the formal baseline;
3. marks the transaction failed with `FORMAL-DRIFT-RESTORED`; and
4. retains the Candidate for correction.

If restoration cannot complete, status requires `recover`; do not continue publication or manually edit State.

Finalization starts from the complete Working Generation. It is the only normal stage that promotes repository-wide knowledge artifacts into the public `.work`, `tech-pack/`, and `ba-pack/` paths. It validates the complete Candidate, archives every replaced formal artifact with hashes, records each promotion in a Journal, validates the promoted result, and then writes the completed State and Finalization Receipt. An interruption must be recovered or rolled back from the Journal; partial directory movement is never treated as completion.

Public paths remain stable. This release protocol guarantees no persistent mixed Generation: a failed or interrupted promotion restores the complete previous published pack.

## Behavior status ownership

During Tracing, the main agent updates Behavior lifecycle only through:

```bash
python3 <skill-root>/scripts/stage_executor.py mark-behavior \
  --output <output-dir> \
  --transaction <transaction-id> \
  --behavior-id <behavior-id> \
  --status understood \
  --dossier behavior-dossiers/<behavior-id>.md \
  --json
```

Use `blocked` only with a precise note. A subagent may write an assigned Candidate file but must not call `mark-behavior`, update checkpoints, alter State, commit, abort, recover, archive, change a Generation, or write formal Pack directories. The main agent reviews the artifact before changing status.

## Status, failure, and recovery

Use one status call instead of reconstructing progress manually:

```bash
python3 <skill-root>/scripts/stage_executor.py status \
  --output <output-dir> \
  --json
```

Read at least:

- Stage, stage status, current Checkpoint, and Checkpoint summary.
- Working Generation ID/status and published Generation ID/commit.
- Formal drift status.
- Release readiness.
- Active transaction, failed Validators, and recovery requirement.
- For Migration, the sealed Mechanical Output Manifest path/hash and Transform count; do not treat an editable Candidate as valid.

`failed` means the Candidate is retained and neither the current Generation nor formal Pack was advanced. Correct the Candidate and retry the same transaction, or abort it:

```bash
python3 <skill-root>/scripts/stage_executor.py abort \
  --output <output-dir> \
  --transaction <transaction-id> \
  --json
```

When status reports an interrupted Generation swap, formal promotion, or inconsistent lock/journal, run:

```bash
python3 <skill-root>/scripts/stage_executor.py recover \
  --output <output-dir> \
  --json
```

Do not infer completion from an agent message. A stage is complete only when its committed Receipt exists and status advances. If the executor or a required Validator cannot run, retain the Candidate and stop; do not patch Skill scripts, install dependencies, or manually advance lifecycle state.

## Versioned Artifact and Register contracts

`assets/artifact-schema.json` is the registry for long-lived working, reader, and operational Artifacts. `assets/migration-transform-registry.json` is the registry for deterministic transforms and their exact source/target schemas and fixtures. Every current Artifact declares its type and version, and `.work/artifact-manifest.json` records path, identity, version, checksum, producing stage, invalidation, and latest transaction. `init` validates both Registries, the Register Schema, API Contract structure contract, and active templates as one release set.

Never use headings, directories, old fields, or prose to detect a legacy generation. Only explicit Artifact metadata, Manifest entries, file existence, hashes, and registry migration chains may drive Resume.

`assets/register-schema.json` is the only mechanical source for Register Schema version, sections, exact table columns, and domain prerequisites. During an analysis, edit Register rows only. A Schema failure invalidates only its domain; downstream checks report `SKIPPED` instead of treating an unavailable index as empty. Unrelated validation continues. Primary Errors or skipped necessary groups mean validation is incomplete.

The generic Markdown structure contract runs before frontmatter, specialized document, and cross-link validation. A malformed document reports its structural root cause and specialized checks for that document are `SKIPPED`; an invalid table must not become hundreds of missing-field or backlink errors.

## Stage sequence and trust boundary

Use this sequence without reordering:

0. `migration` (conditional Resume-only): executor-owned registered transforms, byte preservation, incompatible archive, structural reinitialization, invalidation, and recovery-stage selection. Its sealed Candidate contains no AI reconciliation or Reader document generation.
1. `inventory`: project detection, entry points, evidence index, working catalog, and Register observations.
2. `tracing`: completed or explicitly blocked Behavior Dossiers and updated observations.
3. `synthesis`: first Working Generation; reconciled Register and Repository Synthesis.
4. `tech-publication`: Tech Behaviors, Overview, Catalog, and applicable repository documents in the Generation. API Behaviors declare stable Contract forward references, but this stage creates neither Contract stubs nor Endpoint Matrix. Its Behavior validation relaxes only target-file existence; identity, exact path, uniqueness, and visible links remain mandatory.
5. `api-contract-publication`: Materialize every planned application Contract and the Endpoint Matrix in the Generation, then strictly validate Behavior, Contract, Catalog, and Matrix relationships; use an evidence-based skip only when no API publication intent exists.
6. `business-model`: independent Business Model in the Generation.
7. `ba-publication`: BA Overview, Catalog, Journeys, Scenarios, and backlinks in the Generation, or blocked-model skip.
8. `finalization`: Markdown-first mechanical validation, fact/readability review, transactional formal publication, post-promotion validation, and completion.

All workflow paths are relative to the active Candidate root. A normal stage Receipt uses `promotion_scope: generation` until Finalization. Only a successful Finalization Receipt has `promotion_scope: formal-pack` and `formal_pack_published: true`.
