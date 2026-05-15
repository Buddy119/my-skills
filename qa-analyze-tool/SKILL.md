---
name: qa-analyze-tool
description: Collect Jira or Confluence requirements as Markdown, or convert a requirement document or user story into clarified requirements, a QA strategy pack, BDD-style test cases, and an Xray/Jira-oriented export table. Use when the user asks to collect requirements from Jira or Confluence, analyze a requirement, clarify requirement gaps, generate a test approach, produce BDD test cases, or prepare upload-ready QA artifacts with `/qa-analyze-tool` in `collect`, `preview`, `strategy`, `test_case`, or `final` mode.
compatibility: GitHub Copilot agent skill. Jira and Confluence CLI tools are required only for collect mode when remote Jira or Confluence sources are requested.

allowed-tools: shell
---

# QA Analyze Tool

This skill turns a raw requirement into a staged QA artifact set with a persistent workspace and audit trail.

## Usage

```bash
/qa-analyze-tool [--mode collect|preview|strategy|test_case|final] [--requirement <requirement_path>] [--jira <issue_or_url>[,<issue_or_url>...]] [--confluence <page_id_or_url>[,<page_id_or_url>...]]
```

- `--mode` is required.
- `--requirement` may point to a file or a folder.
- `--jira` accepts one or more comma-separated Jira issue keys or Jira issue URLs.
- `--confluence` accepts one or more comma-separated Confluence page IDs or page URLs.
- For non-`collect` modes, if `--requirement` is omitted, use the pasted requirement text from the conversation and materialize it into the workspace before doing any mode work.
- In `collect` mode, at least one of `--jira` or `--confluence` is required.
- Do not combine `--requirement` with `--jira` or `--confluence`.

## Operating Rules

- Always inspect the existing workspace state before doing new work.
- Never overwrite the user's original local requirement file or folder.
- Keep exactly one canonical source copy and one canonical output set per raw requirement.
- Overwrite canonical output files in place when regenerating them.
- Record every invocation in a new audit file under `audit/`.
- Treat inferred behavior as an assumption, never as a confirmed requirement.
- `collect` is read-only source collection only; it must not update Jira or Confluence and must not run `preview` automatically.
- `strategy` must always run the `preview` workflow first.

## Workspace Layout

Create one persistent artifact root per requirement:

| Source type | Artifact root |
|-------------|---------------|
| File `/path/login.md` | `/path/login/` |
| Folder `/path/login-spec/` | `/path/login-spec/` |
| Pasted text | `qa-artifacts/{slug}/` |
| Remote Jira/Confluence collection | `qa-artifacts/collect-{slug}/` |

Inside the artifact root keep:

```text
latest-status.md
source/
  00-materialized-requirement.md
output/
  00-pending-blockers.md
  01-clarified-requirement.md
  02-strategy.md
  03-bdd-test-cases.md
  04-xray-jira-export.md
audit/
  YYYYMMDD-HHMMSS-<mode>.md
```

## Step 0: Inspect Existing State First

Before every invocation:

1. Read `latest-status.md` if it exists.
2. Read the newest audit files in `audit/` if they exist.
3. Read `output/00-pending-blockers.md` if it exists.
4. Determine:
   - latest completed mode
   - whether unresolved blockers exist
   - which blocker must be replayed first
   - which output artifacts are currently valid
   - what the next required step is
5. Only then decide whether to reuse existing outputs or regenerate them.

If unresolved blockers exist in `output/00-pending-blockers.md`, replay them first and do not continue to fresh blocker discovery or downstream generation until they are cleared.

When the user asks for a later mode, continue from the latest valid upstream artifact only if the source has not changed and no unresolved blockers remain.

In `collect` mode, perform required Jira/Confluence CLI preflight before creating or updating workspace artifacts.

## Step 0.5: Pending-Blocker Queue

`output/00-pending-blockers.md` is the working queue of unresolved blockers only.

- Create or update it when a responder cannot answer a blocker now.
- Replay unresolved blockers from it on the next invocation before anything else.
- Remove a blocker from it as soon as that blocker is answered or explicitly converted into an approved assumption.
- When all pending blockers are cleared, remove the file or leave it empty and mark the workflow clear to continue in `latest-status.md`.

Use this structure for each pending blocker:

```md
# Pending Blockers

## Q-01
- Status: open
- Why blocking:
- Source reference:
- Last asked:
- Responder Name:
- Responder Role:
- Expected answer type:
- Question:
- Answer:
```

Keep only unresolved blockers in this file. Do not keep historical resolved blockers here.

## Step 0.6: Responder Identity

Before asking the first blocker question in a blocker-resolution invocation, capture:

- `Responder Name`
- `Responder Role`

Use that identity for every blocker answer captured in the same invocation. Later modes do not need responder identity unless they re-enter blocker resolution through `preview`.

## Step 1: Materialize The Source

Always materialize the requirement into `source/00-materialized-requirement.md`.

For `collect` mode, run the CLI preflight first. Do not create or update workspace artifacts if a required CLI is missing.

### File Input

- Copy the file contents into `source/00-materialized-requirement.md`.
- Preserve headings, lists, tables, and code blocks as Markdown.
- Do not modify the original file.

### Folder Input

- Read every `.md` and `.txt` file under the folder.
- Exclude the tool-managed workspace items from the merge set:
  - `source/`
  - `output/`
  - `audit/`
  - `latest-status.md`
- Merge them into one canonical Markdown document in lexical path order.
- Before each file's contents, add a short separator heading with its relative path so provenance is preserved.
- Save the merged result to `source/00-materialized-requirement.md`.

### Pasted Text

- Create `qa-artifacts/{slug}/` if needed.
- Save the pasted requirement text to `source/00-materialized-requirement.md`.

### Remote Jira And Confluence Input

- Remote input is supported only through `collect` mode.
- For remote collection, create the artifact root under `qa-artifacts/`.
- For multiple remote sources, derive a short human-readable slug from the fetched Markdown content, for example `qa-artifacts/collect-payment-refund-flow/`.
- If a reliable summary slug cannot be derived, fall back to a compact ID-based slug, for example `qa-artifacts/collect-PROJ-1-PROJ-2-123456789/`.
- Materialize all collected remote content into `source/00-materialized-requirement.md`.
- Add provenance before each collected source section:
  - source type: `jira` or `confluence`
  - source ID or URL
  - collection timestamp
  - CLI command used
- Remote content must be fetched and saved as Markdown.

### Source Change Detection

After materializing the latest raw source:

- Compare it to the previous `source/00-materialized-requirement.md` if one existed.
- If the source changed, mark downstream outputs stale in `latest-status.md`.
- Note the source change in the new audit file.

Staleness rules:

- If `source/00-materialized-requirement.md` changes, `00` through `04` are stale.
- If remote collection changes `source/00-materialized-requirement.md`, review stale pending blockers before reusing them because they may no longer match the current requirement.
- If `output/01-clarified-requirement.md` changes, `02` through `04` are stale.
- If `output/02-strategy.md` changes, `03` and `04` are stale.
- If `output/03-bdd-test-cases.md` changes, `04` is stale.

## Mode Flow

### `collect`

Purpose: fetch raw requirement content from Jira and/or Confluence, materialize it as Markdown, update status and audit, then stop.

Validation:

1. Require at least one of `--jira` or `--confluence`.
2. Reject `--requirement` when either remote flag is present.
3. Parse comma-separated `--jira` and `--confluence` values by trimming whitespace and preserving user-provided order.
4. Allow mixed Jira and Confluence sources in the same invocation.

CLI preflight:

1. If `--jira` is provided, read [references/jira_SKILL.md](references/jira_SKILL.md), then verify Jira CLI is installed:

```bash
jira --help
```

2. If `--confluence` is provided, read [references/confluence_SKILL.md](references/confluence_SKILL.md), then verify Confluence CLI is installed:

```bash
confluence --version
```

3. If any required CLI is missing or unavailable:
   - stop immediately
   - do not create or update requirement artifacts
   - show install and configuration guidance from the relevant reference file
   - include package install command, verification command, required environment variables or config command, and a reminder that collection is read-only

Install guidance summary:

```bash
# Jira
npm install -g @pchuri/jira-cli
jira --help

# Confluence
npm install -g confluence-cli
confluence --version
```

Collection workflow:

1. Fetch each Jira issue as Markdown:

```bash
jira --no-color issue view <issue> --format markdown
```

2. Fetch each Confluence page as Markdown:

```bash
confluence read <pageIdOrUrl> --format markdown
```

3. Combine all fetched Markdown into `source/00-materialized-requirement.md`.
4. Use clear section headings, for example:
   - `# Collected Requirement`
   - `## Source Summary`
   - `## Jira: PROJ-123`
   - `## Confluence: 123456789`
5. Do not include Jira comments, linked issues, subtasks, Confluence child pages, or attachments in v1 unless the user explicitly provides those items as direct source IDs.
6. If any source fetch fails, stop and do not create a misleading complete collected requirement.
7. Compare the collected source to the previous materialized source.
8. If the collected source changed, mark `output/00-pending-blockers.md` and outputs `01` through `04` stale.
9. Update `latest-status.md`:
   - latest completed mode: `collect`
   - materialized source: `valid`
   - pending blockers and downstream outputs: `stale` if the collected source changed
   - next required action: `preview`
10. Write `audit/YYYYMMDD-HHMMSS-collect.md`.
11. Stop. Do not automatically run `preview`.

The collect audit file must record:

- Jira values requested
- Confluence values requested
- CLI preflight result
- CLI commands used
- whether each fetch succeeded
- whether Markdown output was obtained
- whether the materialized source changed
- which artifacts were marked stale

### `preview`

Purpose: review the raw requirement, identify blocking ambiguity, ask clarification questions, and produce a normalized clarified requirement.

Workflow:

1. Read `output/00-pending-blockers.md` first if it exists.
2. If unresolved blockers exist:
   - capture `Responder Name` and `Responder Role` for this invocation
   - re-ask unresolved blockers from the pending file before analyzing new blockers
   - use popup UI as the first-choice channel
   - if popup does not complete cleanly, allow chat fallback with:

```text
Responder Name: Alice
Responder Role: Product Owner
Q-01: <answer>
```

3. If a replayed blocker is answered:
   - fold the answer into the clarified requirement
   - record the answer in the audit file
   - remove that blocker from `output/00-pending-blockers.md`
4. If a replayed blocker is still unanswered:
   - keep it in `output/00-pending-blockers.md`
   - stop the workflow
5. Only when the pending-blocker file has no unresolved blockers may fresh blocker discovery begin.
6. Inspect `source/00-materialized-requirement.md`.
7. Look for blockers across:
   - actors and roles
   - scope boundaries
   - entry triggers
   - business rules
   - validations and edge conditions
   - permissions and access rules
   - integrations and dependencies
   - error handling
   - acceptance criteria
   - data rules and field constraints
8. Ask only blocking questions.
9. Before asking the first newly discovered blocker in this invocation, capture `Responder Name` and `Responder Role` if not already captured.
10. Ask one blocker question at a time.
11. If answers arrive, fold them into a normalized clarified requirement document.
12. If the responder cannot answer a blocker now:
    - write or update `output/00-pending-blockers.md` with a blank answer field for that blocker
    - record the blocker in `latest-status.md`
    - stop the workflow
13. If the user explicitly approves an assumption instead of providing an answer:
    - record the assumption in the clarified requirement
    - record it in the audit file
    - remove the blocker from `output/00-pending-blockers.md` if it was already there
14. Save the result to `output/01-clarified-requirement.md`.
15. Update `latest-status.md`.
16. Create a new audit file for the invocation.

The clarified requirement format must follow [references/preview-template.md](references/preview-template.md).

### `strategy`

Purpose: create the QA pack from a clarified requirement.

Workflow:

1. Always run the `preview` workflow first.
2. If `output/00-pending-blockers.md` exists and contains unresolved blockers, stop after replaying them.
3. Read `output/01-clarified-requirement.md`.
4. Generate the QA pack.
5. Save it to `output/02-strategy.md`.
6. Update `latest-status.md`.
7. Record the invocation in `audit/`.

The QA pack format must follow [references/strategy-template.md](references/strategy-template.md).

### `test_case`

Purpose: create BDD-style Markdown test cases from the current strategy output.

Workflow:

1. Read `latest-status.md` and confirm `output/02-strategy.md` is valid.
2. If `output/00-pending-blockers.md` exists and contains unresolved blockers, stop and replay them through `preview` first.
3. If `output/02-strategy.md` is missing or stale, generate the missing prerequisite first.
4. Read `output/02-strategy.md`.
5. Convert the strategy scenarios into BDD-style test cases.
6. Save the result to `output/03-bdd-test-cases.md`.
7. Update `latest-status.md`.
8. Record the invocation in `audit/`.

The BDD format must follow [references/bdd-template.md](references/bdd-template.md).

### `final`

Purpose: convert the current BDD Markdown into an Xray/Jira-oriented, Excel-ready Markdown table with executable `Test Step` and `Expected Result` columns.

Workflow:

1. Read `latest-status.md` and confirm `output/03-bdd-test-cases.md` is valid.
2. If `output/00-pending-blockers.md` exists and contains unresolved blockers, stop and replay them through `preview` first.
3. If `output/03-bdd-test-cases.md` is missing or stale, generate the missing prerequisite first.
4. Read `output/03-bdd-test-cases.md`.
5. Convert the scenarios into the upload-oriented table. Do not preserve separate `Given`, `When`, or `Then` export columns.
6. Save the result to `output/04-xray-jira-export.md`.
7. Update `latest-status.md`.
8. Record the invocation in `audit/`.

The export format must follow [references/xray-jira-export-template.md](references/xray-jira-export-template.md).

## Clarification Policy

This skill is strict about requirement clarity.

- Do not silently invent missing requirement behavior.
- Do not continue past `preview` when blockers remain unresolved.
- Do not perform fresh blocker discovery while replayed blockers remain unresolved in `output/00-pending-blockers.md`.
- Do not allow `strategy` to generate `output/02-strategy.md` while `output/00-pending-blockers.md` contains unresolved blockers.
- Do not allow `test_case` or `final` to bypass unresolved blockers in `output/00-pending-blockers.md`.
- If the user explicitly accepts an assumption, record it in:
  - `output/01-clarified-requirement.md`
  - the current audit file
  - `latest-status.md`

Use assumptions sparingly. If a missing point changes test scope, permissions, business logic, user flow, or expected outcomes, treat it as blocking.

## Audit Files

Each invocation creates one audit file named:

```text
audit/YYYYMMDD-HHMMSS-<mode>.md
```

Each audit file must record:

- invocation mode
- original source path, folder path, or pasted-text identifier
- Jira values requested, if any
- Confluence values requested, if any
- CLI preflight result, if `collect` mode
- CLI commands used, if `collect` mode
- whether each remote fetch succeeded, if `collect` mode
- whether Markdown output was obtained, if `collect` mode
- whether the source changed
- what status was found before work began
- responder name
- responder role
- which artifacts were reused
- which artifacts were regenerated
- blockers replayed from `output/00-pending-blockers.md`
- questions asked to the user
- user answers
- blockers answered in this invocation
- assumptions accepted by the user
- blockers that remain open
- whether `output/00-pending-blockers.md` was updated, reduced, cleared, or left unchanged
- files updated in `output/`
- next recommended step

## `latest-status.md`

Keep `latest-status.md` compact and current. It must summarize:

- artifact root
- latest completed mode
- materialized source validity
- whether `output/00-pending-blockers.md` exists
- unresolved blocker count
- current blocker ID being asked
- current validity of:
  - `output/00-pending-blockers.md`
  - `output/01-clarified-requirement.md`
  - `output/02-strategy.md`
  - `output/03-bdd-test-cases.md`
  - `output/04-xray-jira-export.md`
- whether blocking questions remain open
- whether the workflow is blocked from continuing
- whether the source changed since the prior completed step
- latest audit file
- next required action

Use simple status labels such as `valid`, `stale`, `missing`, or `blocked`.

## Output Quality Rules

- Keep terminology consistent across all artifacts.
- Preserve traceability from requirement to strategy to BDD to export rows.
- Prefer concise, concrete wording.
- Avoid duplicate scenarios.
- Use `Scenario Outline` only when repeated scenarios truly share the same structure.
- Keep Markdown readable and structured.

## Trigger Hints

Use this skill when the user asks to:

- analyze a requirement or user story for QA
- collect requirements directly from Jira or Confluence
- clarify requirement gaps before testing
- generate a test approach or QA strategy
- convert strategy output into BDD test cases
- prepare upload-ready QA tables for Xray or Jira
- use `/qa-analyze-tool` with any supported mode
