---
name: ba-analyze-tool
description: Convert business requirements, optional reference documentation, current implementation or design materials, and optional previous BA analysis into an evidence-based BA gap analysis, open-question list, traceability matrix, change log, and versioned audit record. Use when the user invokes `/ba-analyze-tool`, asks for BA analysis, business/current/reference comparison, GAP analysis, open questions, traceability, or versioned BA lifecycle artifacts.
compatibility: GitHub Copilot agent skill.
allowed-tools: shell
---

# BA Analyze Tool

This skill helps Business Analysts turn raw stakeholder requirements, optional reference documentation, and current implementation or design materials into a defensible BA analysis package.

The core principle is: do not guess the final design. Identify what is confirmed, what is missing, what conflicts, what changed, and what decision is required.

## Usage

```bash
/ba-analyze-tool --business <path> --current <path> [--reference <path>] [--previous <path>] [--version <label>] [--output <path>]
```

Arguments:

- `--business <path>`: Required. Raw stakeholder requirements, PPT exports, Confluence exports, Excel scenario lists, Jira ticket lists, backstories, in-scope scenarios, or acceptance criteria.
- `--current <path>`: Required. Current implementation design, previous Confluence analysis, TDA discussion, existing API design, architecture notes, existing Jira tickets, or known system behavior.
- `--reference <path>`: Optional. Standards, RFCs, GitHub documentation, vendor guides, regulatory documents, API specifications, or external specifications.
- `--previous <path>`: Optional. Previous `final-ba-analysis.md` used for version comparison.
- `--version <label>`: Optional. Version label for this analysis run.
- `--output <path>`: Optional. Explicit project root for generated analysis artifacts and lifecycle registers.

Examples:

```bash
/ba-analyze-tool --business ./business --reference ./reference --current ./current
/ba-analyze-tool --business ./business --current ./current
/ba-analyze-tool --business ./business --reference ./reference --current ./current --version v1.1
/ba-analyze-tool --business ./business --reference ./reference --current ./current --previous ./previous/final-ba-analysis.md --version v1.1
/ba-analyze-tool --business ./business --reference ./reference --current ./current --output ./analysis
```

## Analysis Modes

### Full Mode

Triggered when `--business`, `--reference`, and `--current` are provided.

Generate:

- Business requirement extraction
- Reference rule extraction
- Current implementation summary
- Standard compliance gaps
- Business-to-current gaps
- Open questions
- Risks and design implications
- Traceability matrix
- Version metadata and audit record
- Change log when `--previous` is provided

### Business + Current Mode

Triggered when `--business` and `--current` are provided but `--reference` is omitted.

Generate:

- Business requirement extraction
- Current implementation summary
- Business-to-current gaps
- Open questions
- Risks and design implications
- Traceability matrix
- Version metadata and audit record
- Change log when `--previous` is provided

The report must explicitly state:

```md
Reference Input: Not provided

This analysis is based only on business requirement sources and current implementation/design sources.
Reference-based standard compliance gaps are not assessed in this run.
```

Do not infer external standard, RFC, vendor, or regulatory compliance gaps unless such requirements are explicitly present in the business or current implementation sources.

## Output Layout

If `--output` is provided, treat it as the explicit project root and write versioned artifacts under:

```text
<output>/ba-analysis-output/<version>/
```

If `--output` is omitted, create or reuse a BA Analyze Tool workspace under the user's home directory:

```text
~/ba-analyze-tool/<project-folder>/ba-analysis-output/<version>/
```

The `<project-folder>` must be a short, meaningful, filesystem-safe slug derived from the business input. Prefer, in order:

1. A clear project or feature name found in the business source title or first major heading.
2. The business objective, shortened to a readable slug.
3. The business input file or folder basename.
4. A fallback slug: `ba-analysis-YYYY-MM-DD`.

Use lowercase letters, numbers, and hyphens. Avoid spaces, punctuation, and generic names such as `business`, `requirements`, `current`, or `docs` unless no better signal exists. If the chosen project folder already exists and appears to represent the same business input, reuse it. If it exists for unrelated content, append a short differentiator such as a source basename or numeric suffix.

The project root is:

- `<output>/` when `--output` is provided.
- `~/ba-analyze-tool/<project-folder>/` when `--output` is omitted.

Each project root must keep project-level lifecycle files:

```text
latest-status.md
source-fingerprint-register.md
audit/
ba-analysis-output/
  <version>/
    ...
```

These project-level files are used to detect reruns for the same requirement, source changes, and historical audit review. Prior open questions are read from the latest previous `final-ba-analysis.md`, not from a separate register file.

Every invocation must create one immutable audit file under:

```text
<project-root>/audit/YYYYMMDD-HHMMSS-<version>-<run-status>.md
```

Use `completed`, `blocked-alignment`, `blocked-input`, `blocked-interaction`, or `stopped` as the run status. Do not overwrite prior audit files.

If `--version` is omitted, generate a label using the run date and a three-digit sequence:

```text
vYYYY-MM-DD-001
```

If an output folder for that generated label already exists, increment the suffix to the next available value.

Each version folder must contain:

```text
00-run-metadata.md
01-source-inventory.md
02-business-requirements.md
03-reference-rules.md
04-current-state.md
05-gap-analysis.md
06-open-questions.md
07-traceability-matrix.md
08-change-log.md
09-open-question-status-check.md
final-ba-analysis.md
```

Always create `03-reference-rules.md`. If no reference input was provided, it must say:

```md
No reference input was provided for this analysis version.
```

Use [references/artifact-templates.md](references/artifact-templates.md) for per-artifact formats and [references/ba-report-template.md](references/ba-report-template.md) for the final report format.

## Workflow

1. Validate arguments:
   - Require `--business`.
   - Require `--current`.
   - Allow `--reference`, `--previous`, `--version`, and `--output` to be omitted.
   - Stop with a clear error if any provided path does not exist or cannot be read.
2. Determine analysis mode:
   - Full Mode when `--reference` is present.
   - Business + Current Mode when `--reference` is absent.
3. Determine output root, project folder, and version folder.
   - If `--output` is provided, use `<output>/ba-analysis-output/<version>/`.
   - If `--output` is omitted, use `~/ba-analyze-tool/<project-folder>/ba-analysis-output/<version>/`.
   - Derive `<project-folder>` from the business source title, objective, or path basename.
4. Run the rerun preflight for the project root.
   - Read `latest-status.md` if it exists.
   - Read `source-fingerprint-register.md` if it exists.
   - Inspect the newest audit files in `audit/` if they exist.
   - Determine the last run status from `latest-status.md` and the newest audit file.
   - If the last run status was not `completed`, treat this invocation as a completion/resume run and continue from the last blocked or stopped point before doing new comparison work.
   - Identify the latest previous version for the same project.
   - If `--previous` is omitted but the project root has prior versions, use the latest previous version as comparison context.
   - Read prior open questions from the previous `final-ba-analysis.md` and, when useful, previous `06-open-questions.md`.
5. Load source files:
   - Accept a file or folder for each input path.
   - For folders, read supported text-like files in lexical path order.
   - Preserve source provenance by recording source path, input type, role, and whether it was used.
   - Compute a stable fingerprint for each source file when possible, for example with SHA-256 or the platform's available checksum tool.
6. Check whether requirements changed.
   - Compare current business-source fingerprints against `source-fingerprint-register.md`.
   - If fingerprints changed, classify the change as source added, source removed, or source changed.
   - If fingerprints are unavailable, compare source file paths, modified times, and extracted business requirement records.
   - Record the result in `01-source-inventory.md`, `08-change-log.md`, and `source-fingerprint-register.md`.
7. Check prior open question status with the user.
   - Extract prior open questions from the previous `final-ba-analysis.md`.
   - Present the prior open question IDs and concise questions to the user in a popup window.
   - Ask whether any prior open questions have been answered since the last run by popup window.
   - If the user says no, mark the status check as completed with no answered prior questions.
   - If the user says yes, ask by popup window for the answered question IDs and the answer or decision for each one.
   - Preserve the same `OQ-*` ID for each prior question.
   - Mark answered questions as `Answered` or `Closed` only when the answer or decision is explicit.
   - Keep unanswered questions open with their prior status.
   - Record the status check in `09-open-question-status-check.md`, `08-change-log.md`, and the new `final-ba-analysis.md`.
8. Determine rerun reason when needed.
   - If the last run was `completed`, no requirement source changed, and no prior open question was answered, ask the user by popup window why they are rerunning.
   - Include whether the rerun is because the user is not satisfied with the prior result, wants a different emphasis, wants a formatting/output change, wants to add context not present in source files, or has another reason.
   - Record the user's reason in the audit file, `00-run-metadata.md`, `08-change-log.md`, and `final-ba-analysis.md`.
   - If no reason is provided through popup, stop with run status `blocked-interaction`.
9. Classify sources:
   - Business input answers: what does the business want to achieve?
   - Reference input answers: what must the solution comply with?
   - Current input answers: what do we already have today?
10. Generate source inventory.
11. Draft the business understanding:
   - Business objective
   - User roles and actors
   - In-scope scenarios
   - Out-of-scope scenarios
   - User journey
   - Business rules
   - Data requirements
   - Acceptance criteria
   - Priority
   - Assumptions
   - Ambiguities
12. Run the mandatory Business Understanding Alignment Gate.
13. Extract reference rules only when `--reference` is provided:
   - Mandatory rules: MUST or SHALL
   - Recommended rules: SHOULD
   - Optional rules: MAY
   - Data format rules
   - API behavior
   - Security requirements
   - Consent requirements
   - Error handling rules
   - Compatibility requirements
   - Required edge cases
14. Extract current implementation state:
   - Implemented behavior
   - Supported scenarios
   - Unsupported scenarios
   - Existing APIs
   - Existing data model
   - Known limitations
   - Technical constraints
   - Confirmed design decisions
   - Existing assumptions
   - Workarounds
15. Normalize requirements and rules into structured records with stable IDs and evidence.
16. Compare confirmed business requirements, optional reference rules, and current implementation.
17. Identify gaps.
18. Generate open questions.
19. Generate risks and design implications.
20. Build the traceability matrix.
21. Generate run metadata and an audit record.
22. Generate the change log using explicit `--previous` input or the latest project version from the rerun preflight.
23. Update project-level `latest-status.md` and `source-fingerprint-register.md`.
24. Produce the final BA analysis report.
25. Finalize the audit file with run status, artifacts generated, decisions made, rerun reason, blockers, and next action.

## Business Understanding Alignment Gate

This gate is mandatory for every run. The LLM must align its interpretation of the business intent with a human before downstream analysis starts.

Allowed work before human alignment:

- Validate command arguments.
- Determine the project root and latest prior version.
- Run rerun preflight.
- Load source files.
- Compute source fingerprints and detect source changes.
- Check prior open-question status from the previous final report.
- Classify sources.
- Generate source inventory.
- Draft a concise business understanding summary.

Blocked work before human alignment:

- Do not extract final reference rules.
- Do not extract final current-state records.
- Do not compare business, reference, and current sources.
- Do not identify gaps.
- Do not generate new downstream open questions, risks, design implications, traceability, final change log, or final report.

The alignment summary must include:

- Business objective
- Primary actors and roles
- In-scope scenarios
- Out-of-scope or unclear scope
- User journey summary
- Key business rules
- Data requirements
- Acceptance criteria
- Priority signals
- Assumptions
- Ambiguities
- LLM interpretation notes that need human confirmation

Ask the human to confirm or correct the summary by popup window before continuing. If the human corrects the summary, update the business understanding and ask for confirmation again by popup window if the correction changes scope, priority, actors, business rules, acceptance criteria, or gap classification.

Do not continue to gap analysis or final artifact generation until the human has explicitly confirmed the aligned business understanding.

If confirmation is not yet available, stop and return only the Business Understanding Alignment Summary for human review. Do not create the final BA report, gap analysis, downstream open-question list, risk analysis, traceability matrix, or change log while confirmation is pending.

Even when stopping at the alignment gate, create an audit file with status `blocked-alignment` and record the alignment summary delivered to the user.

Record the confirmation in `02-business-requirements.md` and `final-ba-analysis.md`:

- Confirmation status
- Confirmed by
- Confirmed role
- Confirmation date
- Summary of corrections made before confirmation

Business requirement records must include an `Alignment Status` value:

- Confirmed
- Corrected and Confirmed
- Needs Clarification
- Conflicting

Only `Confirmed` and `Corrected and Confirmed` business requirements may be used as required behavior for gap classification. `Needs Clarification` and `Conflicting` items must become open questions, not hard gaps.

## Mandatory Popup Interaction

All user-interactive actions must use a popup window. Do not collect required answers through normal chat, inline assumptions, or silent defaults.

Popup is mandatory for:

- Business Understanding Alignment Gate confirmation or correction.
- Prior open-question answered/not-answered check.
- Details for answered prior open questions.
- Rerun reason when last run completed and no requirement change or answered open question is detected.
- Any other clarification that blocks analysis or changes output status.

Rules:

- Do not skip an interactive step without showing a popup window.
- Do not use chat fallback for required answers.
- If a popup window cannot be shown, stop the run with status `blocked-interaction`.
- Record the missed popup interaction and blocked reason in the audit file.
- Only continue after the popup answer is captured and recorded.

## Audit Mechanism

Every invocation for a project must write one audit file under `<project-root>/audit/`.

Audit filename:

```text
YYYYMMDD-HHMMSS-<version>-<run-status>.md
```

Run statuses:

- `completed`: final BA analysis report and versioned artifacts were generated.
- `blocked-alignment`: the run stopped at the Business Understanding Alignment Gate.
- `blocked-input`: required arguments or input paths were missing or unreadable.
- `blocked-interaction`: a required popup interaction could not be shown or completed.
- `stopped`: the run stopped for any other explicit reason.

Audit files are append-only historical records. Do not edit or overwrite earlier audit files. If a correction is needed, create a new audit file in the next run and reference the previous audit filename.

Each audit file must record:

- Invocation command and arguments.
- Run timestamp.
- Run status.
- Project root and version folder.
- Previous baseline selected, including whether it came from `--previous` or automatic latest-version detection.
- Input paths and readability result.
- Source fingerprint summary and requirement-change result.
- Prior open-question review result and user-provided answers, if any.
- Last run status and rerun path selected.
- Rerun reason when captured from the user.
- Popup interactions shown, answers captured, and any popup interaction failure.
- Business understanding alignment status.
- Human confirmer name and role, if confirmed.
- Files generated, updated, skipped, or not generated.
- Gap, open-question, and change-log count summary when available.
- Blockers or stop reason.
- Next recommended action.

The versioned `00-run-metadata.md` should summarize the same run at a high level. The audit file is the detailed lifecycle record of what happened during that invocation.

## Rerun And Prior Open Question Rules

When the tool runs for an existing project root, treat it as a lifecycle continuation, not a fresh one-off analysis.

Before drafting new analysis, always check the latest project status:

1. Last run status.
2. Whether the requirement sources changed.
3. Whether the user has answers or decisions for any previously open questions from the last report.
4. If nothing changed and no questions were answered, why the user is rerunning.

### Last Run Status Routing

Use `latest-status.md` and the newest audit file to determine the last run status.

If the last run status is not `completed`:

- Treat the new invocation as a completion/resume run for the same project.
- Resume from the last blocked or stopped point.
- Do not ask for rerun reason yet.
- If the prior run stopped at `blocked-alignment`, show the Business Understanding Alignment popup again and continue only after confirmation.
- If the prior run stopped at `blocked-input`, validate the newly provided paths and continue only if required inputs are readable.
- If the prior run stopped at `blocked-interaction`, retry the required popup interaction.
- Record the previous status and resumed action in the new audit file.

If the last run status is `completed`:

- Check requirement source changes.
- Ask by popup whether prior open questions were answered.
- If no requirement changed and no prior open question was answered, ask by popup why the user is rerunning.
- Record all detected reasons and user-provided reasons in the audit file.

Valid rerun reasons include:

- Requirement changed.
- Prior open question answered.
- User not satisfied with prior result.
- User wants different analysis emphasis.
- User wants formatting or output structure changes.
- User has additional context not present in source files.
- User wants regeneration for review/audit purposes.
- Other user-provided reason.

If last run was `completed`, nothing changed, no open question was answered, and the user does not provide a rerun reason through popup, stop with status `blocked-interaction`.

### Requirement Change Detection

Use `source-fingerprint-register.md` to compare current inputs with the latest known project state.

For each source, record:

- Source ID
- File path
- Input type
- Last modified time when available
- Fingerprint or checksum when available
- Prior fingerprint
- Change status: `Unchanged`, `Added`, `Removed`, `Changed`, or `Unknown`
- Notes

If business source content changed, rerun the Business Understanding Alignment Gate because the human's prior confirmation may no longer apply.

If only reference or current implementation sources changed, keep the confirmed business understanding but record the source change and reassess related gaps, questions, risks, and traceability.

### Prior Open Question Review

The previous `final-ba-analysis.md` is the source of truth for prior open questions. Do not maintain a separate project-level open-question register.

On a rerun with a previous baseline:

1. Extract prior questions from the previous report's `Open Questions` section and `Open Question Register Summary`.
2. Show the user a concise list of still-open prior question IDs and questions.
3. Ask: "Have any of these open questions been answered since the last run?"
4. If the user says no, skip prior-question resolution and continue with source-change checks and analysis.
5. If the user says yes, ask for the answered `OQ-*` IDs and the answer or decision for each.
6. Treat user-provided answers as human response evidence and record them in `09-open-question-status-check.md`, `08-change-log.md`, and the new `final-ba-analysis.md`.

Use these status rules for prior questions:

- `Existing`: still open and materially unchanged from the prior report.
- `Updated`: still open but wording, scope, owner, blocking level, or related gap changed.
- `Answered`: explicit answer exists, but downstream impact still needs to be reflected in requirements, gaps, or recommendations.
- `Closed`: explicit answer or decision exists and downstream artifacts have been updated.
- `Deferred`: the question is intentionally postponed.
- `Escalated`: the question requires decision from another owner or governance path.

Only mark a prior question `Answered` or `Closed` when the user provides an explicit answer or an explicit answer is present in newly provided sources. Do not infer an answer from silence, missing text, or the absence of a prior problem statement.

When a prior question is answered:

- Preserve the same `OQ-*` ID.
- Record the answer or decision, evidence, owner if known, and version.
- Reassess related gaps.
- Close, update, or create gaps as needed.
- Add a `Resolved Open Question` or `Changed Open Question` row to the change log.

When requirements changed:

- Preserve stable IDs where the underlying item is the same.
- Mark affected requirements, gaps, and open questions as `Updated`.
- Create new IDs only for genuinely new items.
- Close or mark obsolete items only when evidence shows they no longer apply.

## Analysis Rules

1. `--business` and `--current` are mandatory.
2. `--reference` is optional.
3. If `--reference` is missing, do not infer external standard compliance gaps.
4. Human-confirmed business understanding is mandatory before downstream analysis.
5. Do not treat the LLM's interpretation of business intent as confirmed until a human confirms or corrects it.
6. Every gap must be evidence-based and based on confirmed or corrected-and-confirmed business understanding.
7. Every open question must be tied to missing, ambiguous, or conflicting information.
8. Do not invent requirements not supported by the provided sources.
9. Preserve stable IDs across versions when `--previous` is provided.
10. Track lifecycle status for gaps and open questions.
11. On every rerun for an existing project, check requirement changes and open-question status before new analysis.
12. Use the previous `final-ba-analysis.md` as the prior open-question source; do not create a separate open-question register file.
13. Generate run metadata for every analysis.
14. Generate a change log when previous analysis is provided or when the project root has previous versions.
15. Clearly distinguish confirmed requirements, inferred requirements, assumptions, gaps, and open questions.
16. If source files conflict, create an open question instead of silently choosing one.
17. If a source is ignored, record the reason in the source inventory.
18. Do not treat stakeholder desire, reference rule, and current implementation as the same type of evidence.
19. Do not produce generic BA questions. Questions must be specific, decision-oriented, and tied to evidence.

## Gap Rules

A gap is required or expected behavior that current implementation does not satisfy.

Gap categories:

- Functional Gap
- Scenario Gap
- Data Gap
- API Gap
- UX / Journey Gap
- Security / Consent Gap
- Standard Compliance Gap
- Error Handling Gap
- Non-Functional Gap
- Operational / Monitoring Gap
- Test Coverage Gap
- Documentation Gap

Gap lifecycle statuses:

- New
- Existing
- Updated
- Closed
- Deferred
- Not Applicable

Required gap columns:

| Gap ID | Status | Category | Required Behavior | Current State | Gap Description | Impact | Severity | Recommendation | Proposal Solution | Design Implication | Evidence |
|--------|--------|----------|-------------------|---------------|-----------------|--------|----------|----------------|-------------------|--------------------|----------|

Evidence must cite the source ID, source path or file, and a concise quote or paraphrased location.

### Proposal Solution Rules

For each gap, provide a `Proposal Solution` for BA reference when enough evidence exists to suggest a practical resolution path.

The proposal solution must:

- Be based on confirmed business understanding, reference rules when provided, and current implementation evidence.
- Explain what could be changed or added to close the gap.
- Be concise and implementation-oriented enough for discussion with Product, Architecture, Engineering, QA, or Compliance.
- Stay clearly marked as a proposal for BA review, not an approved final design.
- Avoid inventing new requirements, business scope, or compliance obligations.
- Identify dependency on an open question when the solution cannot be chosen without a decision.

If there is not enough evidence to propose a solution, write:

```text
Pending decision: see OQ-xxx.
```

or:

```text
Insufficient evidence to propose a solution.
```

Do not use `Proposal Solution` to bypass open questions. If multiple reasonable approaches exist, summarize the main options briefly and point to the decision needed.

## Open Question Rules

An open question is missing, ambiguous, conflicting, or decision-blocking information that prevents a final design decision.

Generate open questions only when:

- Information is missing
- Information is ambiguous
- Sources conflict
- Scope is unclear
- A design decision is required
- Ownership is unclear

Do not generate generic questions. Every question must explain why it matters and what decision it blocks.

Open question lifecycle statuses:

- New
- Existing
- Updated
- Answered
- Closed
- Deferred
- Escalated

Required open question columns:

| Question ID | Status | Topic | Question | Why It Matters | Options / Possible Answers | Owner | Blocking Level | Related Gap | Evidence |
|-------------|--------|-------|----------|----------------|----------------------------|-------|----------------|-------------|----------|

## Versioning And Change Log

When `--previous` is provided, use that report as the previous baseline.

When `--previous` is omitted but the project root already contains prior versions, use the latest prior version in `ba-analysis-output/` as the previous baseline and record that automatic baseline selection in `00-run-metadata.md` and `08-change-log.md`.

When a previous baseline exists:

- Read the previous report, previous `06-open-questions.md`, previous `08-change-log.md`, and previous `09-open-question-status-check.md` if it exists before assigning current IDs.
- Preserve stable IDs for requirements, gaps, and questions that represent the same underlying item.
- If an existing item materially changes, keep the same ID and mark it `Updated`.
- If a gap is resolved, keep the same ID and mark it `Closed`.
- If an open question is answered, keep the same ID and mark it `Answered` or `Closed`.
- If an item no longer applies, keep the same ID and mark it `Not Applicable`, `Closed`, or `Deferred` as appropriate.
- If an item is new, assign a new ID.

Supported change types:

- Source Added
- Source Removed
- Source Changed
- New Requirement
- Changed Requirement
- Removed Requirement
- New Gap
- Changed Gap
- Closed Gap
- New Open Question
- Changed Open Question
- Resolved Open Question
- New Assumption
- Changed Assumption

Required change log columns:

| Change ID | Type | Previous Version | Current Version | Description | Impact |
|-----------|------|------------------|-----------------|-------------|--------|

The change log must explicitly include:

- Requirement source changes from the fingerprint check.
- Open questions answered since the previous version.
- Open questions still unresolved.
- Gaps changed because an open question was answered.

## Traceability Rules

The traceability matrix must connect business requirements, reference rules, current implementation, gaps, open questions, and evidence.

Required columns:

| Business Requirement | Reference Rule | Current State | Gap ID | Open Question ID | Evidence |
|----------------------|----------------|---------------|--------|------------------|----------|

In Business + Current Mode, use `Not assessed` or `Not applicable` for `Reference Rule` unless a standard-like requirement is explicitly present in the business or current implementation sources.

## Output Quality

- Keep terminology consistent across all artifacts.
- Preserve evidence and source provenance.
- Prefer concise BA language suitable for Confluence.
- Separate confirmed facts from assumptions and inferred implications.
- Do not collapse gaps and open questions into the same item.
- Use stable IDs:
  - Business requirements: `BR-001`
  - Reference rules: `RR-001`
  - Current-state records: `CS-001`
  - Gaps: `GAP-001`
  - Open questions: `OQ-001`
  - Risks: `RISK-001`
  - Changes: `CHG-001`

## Trigger Hints

Use this skill when the user asks to:

- run `/ba-analyze-tool`
- analyze BA requirements
- compare business requirements to current implementation
- compare business, reference, and current implementation sources
- generate a BA gap analysis
- generate BA open questions
- generate a traceability matrix
- create a versioned BA analysis report
- compare a new BA analysis with a previous BA analysis
