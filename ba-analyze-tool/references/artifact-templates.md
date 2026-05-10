# Artifact Templates

Use these templates for the versioned artifact folder:

```text
<output>/ba-analysis-output/<version>/
```

When `--output` is omitted, the default versioned artifact folder is:

```text
~/ba-analyze-tool/<project-folder>/ba-analysis-output/<version>/
```

Each project root also keeps lifecycle files outside the version folder:

```text
latest-status.md
source-fingerprint-register.md
audit/
```

## Project-Level `latest-status.md`

```md
# Latest Status

| Field | Value |
|-------|-------|
| Project Folder |  |
| Latest Version |  |
| Latest Run Date |  |
| Latest Run Status | completed / blocked-alignment / blocked-input / blocked-interaction / stopped |
| Latest Analysis Mode |  |
| Business Understanding Confirmation Status | Confirmed / Pending |
| Requirement Change Status | Unchanged / Changed / Unknown |
| Prior Open Question Review | Completed / Skipped / Pending |
| Rerun Path | Fresh run / Completion resume / Requirement changed / Prior question answered / User-requested rerun |
| Latest Rerun Reason |  |
| Open Questions Total |  |
| Open Questions Open |  |
| Open Questions Answered This Run |  |
| Open Questions Closed This Run |  |
| Latest Output Folder |  |

## Next Recommended Action

- 
```

## Project-Level `source-fingerprint-register.md`

```md
# Source Fingerprint Register

| Source ID | File | Input Type | Last Modified | Fingerprint | First Seen Version | Last Seen Version | Current Status | Notes |
|-----------|------|------------|---------------|-------------|--------------------|-------------------|----------------|-------|
| SRC-001 |  | Business / Reference / Current / Previous |  |  |  |  | Active / Removed |  |
```

## Project-Level `audit/YYYYMMDD-HHMMSS-<version>-<run-status>.md`

Create one audit file for every invocation. Do not overwrite previous audit files.

```md
# BA Analyze Tool Run Audit

| Field | Value |
|-------|-------|
| Audit File |  |
| Run Timestamp |  |
| Run Status | completed / blocked-alignment / blocked-input / blocked-interaction / stopped |
| Analysis Version |  |
| Project Root |  |
| Version Folder |  |
| Invocation |  |
| Last Run Status |  |
| Rerun Path | Fresh run / Completion resume / Requirement changed / Prior question answered / User-requested rerun |
| Rerun Reason |  |
| Previous Baseline |  |
| Previous Baseline Selection | Provided by `--previous` / Automatic latest version / None |

## Input Validation

| Input | Path | Required? | Readable? | Notes |
|-------|------|-----------|-----------|-------|
| Business |  | Yes | Yes / No |  |
| Current |  | Yes | Yes / No |  |
| Reference |  | No | Yes / No / Not provided |  |
| Previous |  | No | Yes / No / Not provided |  |

## Source Change Check

| Source ID | File | Input Type | Previous Fingerprint | Current Fingerprint | Change Status | Notes |
|-----------|------|------------|----------------------|---------------------|---------------|-------|
| SRC-001 |  | Business / Reference / Current |  |  | Unchanged / Added / Removed / Changed / Unknown |  |

## Prior Open Question Review

| Question ID | Previous Status | User Provided Answer? | Current Status | Answer / Decision | Evidence |
|-------------|-----------------|-----------------------|----------------|-------------------|----------|
| OQ-001 |  | Yes / No |  |  |  |

## Rerun Reason Check

| Field | Value |
|-------|-------|
| Requirement Changed? | Yes / No / Unknown |
| Prior Open Question Answered? | Yes / No / Not applicable |
| Popup Rerun Reason Required? | Yes / No |
| User Rerun Reason |  |
| Rerun Reason Evidence | Popup response |

## Popup Interactions

| Interaction ID | Purpose | Popup Shown? | Completed? | Response Summary | Failure / Blocker |
|----------------|---------|--------------|------------|------------------|-------------------|
| POP-001 | Business alignment / Prior open question review / Rerun reason / Other | Yes / No | Yes / No |  |  |

## Business Understanding Alignment

| Field | Value |
|-------|-------|
| Alignment Status | Confirmed / Pending / Not reached |
| Confirmed By |  |
| Confirmed Role |  |
| Confirmation Date |  |
| Corrections Before Confirmation |  |

## Generated Or Updated Files

| File | Action | Notes |
|------|--------|-------|
| 00-run-metadata.md | Created / Updated / Skipped |  |

## Summary Counts

| Item | Count |
|------|-------|
| Business Requirements |  |
| Reference Rules |  |
| Current-State Records |  |
| Gaps |  |
| Open Questions |  |
| Changes |  |

## Blockers Or Stop Reason

- 

## Next Recommended Action

- 
```

## `00-run-metadata.md`

```md
# Run Metadata

| Field | Value |
|-------|-------|
| Analysis Version |  |
| Run Date |  |
| Analysis Mode | Business + Reference + Current / Business + Current |
| Business Input Path |  |
| Reference Input Path |  |
| Current Input Path |  |
| Previous Analysis |  |
| Output Root Source | Provided by `--output` / Default home workspace |
| Project Folder |  |
| Output Folder |  |
| Audit File |  |
| Last Run Status |  |
| Rerun Path | Fresh run / Completion resume / Requirement changed / Prior question answered / User-requested rerun |
| Rerun Reason |  |
| Business Understanding Confirmation Status | Confirmed / Pending |
| Business Understanding Confirmed By |  |
| Business Understanding Confirmed Role |  |
| Business Understanding Confirmation Date |  |
| Generated By | BA Analyze Tool Copilot Skill |

## Audit Notes

- Invocation:
- Version selection:
- Project folder selection:
- Audit file:
- Previous analysis handling:
- Reference handling:
- Business understanding alignment:
- Files generated:
```

## `01-source-inventory.md`

```md
# Source Inventory

| Source ID | File | Input Type | Last Modified | Fingerprint | Previous Fingerprint | Change Status | Role in Analysis | Used / Ignored | Notes |
|-----------|------|------------|---------------|-------------|----------------------|---------------|------------------|----------------|-------|
| SRC-001 |  | Business / Reference / Current / Previous |  |  |  | Unchanged / Added / Removed / Changed / Unknown |  | Used / Ignored |  |

## Source Handling Notes

- Business sources:
- Reference sources:
- Current implementation/design sources:
- Previous analysis:
- Requirement change status:
- Ignored sources and reasons:
```

## `02-business-requirements.md`

```md
# Business Requirements

## Business Context

- Business understanding confirmation status: Confirmed / Pending
- Confirmed by:
- Confirmed role:
- Confirmation date:
- Corrections made before confirmation:
- Business objective:
- Primary actors:
- Business value:
- User journey summary:
- LLM interpretation notes confirmed by human:

## Business Understanding Alignment Summary

| Item | LLM Draft Understanding | Human Correction / Confirmation | Final Aligned Understanding |
|------|-------------------------|---------------------------------|-----------------------------|
| Business objective |  |  |  |
| Actors and roles |  |  |  |
| In-scope scenarios |  |  |  |
| Out-of-scope or unclear scope |  |  |  |
| User journey |  |  |  |
| Business rules |  |  |  |
| Data requirements |  |  |  |
| Acceptance criteria |  |  |  |
| Priority signals |  |  |  |
| Assumptions and ambiguities |  |  |  |

## In-Scope Scenarios

| Scenario ID | Scenario | Actor | Priority | Evidence |
|-------------|----------|-------|----------|----------|
| SC-001 |  |  |  |  |

## Out-of-Scope / Unclear Scope

| Item ID | Scope Item | Status | Evidence | Notes |
|---------|------------|--------|----------|-------|
| SCOPE-001 |  | Out of Scope / Unclear |  |  |

## Requirement Records

| Requirement ID | Status | Alignment Status | Requirement | Type | Priority | Assumptions / Ambiguities | Evidence |
|----------------|--------|------------------|-------------|------|----------|---------------------------|----------|
| BR-001 | New / Existing / Updated / Removed | Confirmed / Corrected and Confirmed / Needs Clarification / Conflicting |  | Functional / Data / Journey / Rule / Non-Functional |  |  |  |

## Acceptance Criteria

| AC ID | Acceptance Criterion | Related Requirement | Evidence |
|-------|----------------------|---------------------|----------|
| AC-001 |  | BR-001 |  |
```

## `03-reference-rules.md`

```md
# Reference Rules

## Reference Input Status

Reference Input: Provided / Not provided

If no reference input was provided, write:

No reference input was provided for this analysis version.

This analysis does not assess standard, RFC, vendor, or regulatory compliance unless such requirements are explicitly present in the business or current implementation sources.

## Reference Rule Records

| Rule ID | Status | Requirement Level | Rule | Category | Evidence |
|---------|--------|-------------------|------|----------|----------|
| RR-001 | New / Existing / Updated / Removed | MUST / SHALL / SHOULD / MAY |  | Data / API / Security / Consent / Error Handling / Compatibility / Edge Case |  |
```

## `04-current-state.md`

```md
# Current Implementation Summary

## Current State Overview

- Confirmed implemented behavior:
- Supported scenarios:
- Unsupported scenarios:
- Existing assumptions:
- Known workarounds:

## Current State Records

| Current State ID | Status | Area | Current Behavior / Design | Supported Scenarios | Known Limitations | Evidence |
|------------------|--------|------|---------------------------|---------------------|-------------------|----------|
| CS-001 | New / Existing / Updated / Removed |  |  |  |  |  |

## Technical Constraints

| Constraint ID | Constraint | Impact | Evidence |
|---------------|------------|--------|----------|
| CON-001 |  |  |  |
```

## `05-gap-analysis.md`

```md
# Gap Analysis

## Gap Summary

- Total gaps:
- High severity:
- Medium severity:
- Low severity:
- Closed or not applicable:

## Gap Records

| Gap ID | Status | Category | Required Behavior | Current State | Gap Description | Impact | Severity | Recommendation | Design Implication | Evidence |
|--------|--------|----------|-------------------|---------------|-----------------|--------|----------|----------------|--------------------|----------|
| GAP-001 | New / Existing / Updated / Closed / Deferred / Not Applicable | Functional / Scenario / Data / API / UX / Security / Standard Compliance / Error Handling / Non-Functional / Operational / Test Coverage / Documentation |  |  |  |  | High / Medium / Low |  |  |  |
```

## `06-open-questions.md`

```md
# Open Questions

## Open Question Summary

- Total questions:
- Blocking:
- Non-blocking:
- Answered or closed:

## Open Question Records

| Question ID | Status | Topic | Question | Why It Matters | Options / Possible Answers | Owner | Blocking Level | Related Gap | Evidence |
|-------------|--------|-------|----------|----------------|----------------------------|-------|----------------|-------------|----------|
| OQ-001 | New / Existing / Updated / Answered / Closed / Deferred / Escalated |  |  |  |  |  | Blocking / Non-Blocking |  |  |

## Prior Question Status Carryover

| Question ID | Previous Status | User Provided Answer? | Current Status | Status Reason | Answer / Decision Evidence | Related Artifact Updates |
|-------------|-----------------|-----------------------|----------------|---------------|----------------------------|--------------------------|
| OQ-001 |  | Yes / No |  |  |  |  |
```

## `07-traceability-matrix.md`

```md
# Traceability Matrix

| Business Requirement | Reference Rule | Current State | Gap ID | Open Question ID | Evidence |
|----------------------|----------------|---------------|--------|------------------|----------|
| BR-001 | RR-001 / Not assessed / Not applicable | CS-001 | GAP-001 | OQ-001 |  |

## Traceability Notes

- Requirements without current-state coverage:
- Reference rules without current-state coverage:
- Gaps blocked by open questions:
- Requirements with no identified gap:
```

## `08-change-log.md`

```md
# Change Log

## Previous Analysis Status

Previous Analysis: Provided / Not provided

If no previous analysis was provided, write:

No previous analysis was provided. Change log is not applicable for this run.

## Change Records

| Change ID | Type | Previous Version | Current Version | Description | Impact |
|-----------|------|------------------|-----------------|-------------|--------|
| CHG-001 | Source Added / Source Removed / Source Changed / New Requirement / Changed Requirement / Removed Requirement / New Gap / Changed Gap / Closed Gap / New Open Question / Changed Open Question / Resolved Open Question / New Assumption / Changed Assumption |  |  |  |  |
```

## `09-open-question-status-check.md`

```md
# Prior Open Question Status Check

## Status Check Summary

- Previous baseline:
- Current version:
- Source of prior questions: Previous `final-ba-analysis.md`
- User confirmed whether any prior questions were answered: Yes / No
- Questions reviewed:
- Questions newly answered:
- Questions closed:
- Questions still open:
- Questions newly created:

## User Response

- Did the user report answered prior questions? Yes / No
- User response summary:

## Prior Question Review

| Question ID | Previous Status | User Provided Answer? | Current Status | Question | Answer / Decision | Evidence | Downstream Impact |
|-------------|-----------------|-----------------------|----------------|----------|-------------------|----------|-------------------|
| OQ-001 | Existing | Yes / No | Answered / Closed / Existing / Updated / Deferred / Escalated |  |  |  |  |

## New Questions

| Question ID | Status | Question | Why It Matters | Evidence |
|-------------|--------|----------|----------------|----------|
| OQ-002 | New |  |  |  |

## Register Updates Applied

No separate open-question register is maintained. Prior-question status is carried forward from the previous final report into the current final report.
```

## `final-ba-analysis.md`

Use [ba-report-template.md](ba-report-template.md).

## Evidence Rules

- Evidence must point to a provided source.
- Evidence should include source ID and, when available, file path, heading, row, ticket ID, page section, or a short quoted phrase.
- If evidence is weak, classify the item as an assumption or open question instead of a confirmed requirement or gap.
- If sources conflict, create an open question and cite both conflicting sources.
