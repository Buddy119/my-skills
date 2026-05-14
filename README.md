# Skills

This folder contains self-contained open standard skill packages. Each skill lives in its own subfolder and includes its own `SKILL.md` with detailed operating rules, inputs, outputs, and workflow guidance.

## Install For GitHub Copilot

Install all skills into the default GitHub Copilot skills folder:

```bash
./install-copilot-skills.sh
```

Install one skill on macOS or Linux:

```bash
./install-copilot-skills.sh --skill postman2insomnia
```

Install all skills on Windows PowerShell:

```powershell
.\install-copilot-skills.ps1
```

Install one skill on Windows PowerShell:

```powershell
.\install-copilot-skills.ps1 -Skill postman2insomnia
```

The install target is always `~/.copilot/skills`. If the target folder does not exist, the installer creates it. If a skill already exists there, the installer asks before overwriting and backs up the old copy before replacement.

## Skills Overview

| Skill | Purpose | Main usage |
| --- | --- | --- |
| [aws-incident-pair](aws-incident-pair/) | Investigate AWS backend incidents in chat using read-only commands with the installed AWS CLI version, X-Ray traces, and CloudWatch logs. | `/aws-incident-pair --region <aws-region> --request-id <request-id> --xray-id <trace-id> ...` |
| [ba-analyze-tool](ba-analyze-tool/) | Convert business requirements, reference docs, and current implementation materials into evidence-based BA gap analysis artifacts. | `/ba-analyze-tool --business <path> --current <path> ...` |
| [qa-analyze-tool](qa-analyze-tool/) | Turn requirements, Jira issues, or Confluence pages into clarified QA artifacts and test exports. | `/qa-analyze-tool --mode <mode> ...` |
| [postman2insomnia](postman2insomnia/) | Convert Postman collection, environment, and globals JSON exports into Insomnia import files. | `/postman2insomnia --source <folder-path-to-postman>` |

## aws-incident-pair

[Skill details](aws-incident-pair/SKILL.md)

Use this skill as an AWS incident investigation pair. It detects the installed AWS CLI version, uses read-only AWS CLI commands to inspect X-Ray traces and CloudWatch logs, then summarizes evidence directly in chat. It does not remediate, invoke business functions, write report files, or generate investigation output files.

```bash
/aws-incident-pair --region <aws-region> --request-id <request-id> --xray-id <xray-trace-id> --since 60m
```

Key inputs:

- AWS region through `--region`.
- Request ID through `--request-id` is required.
- X-Ray trace ID through `--xray-id` is required.
- Optional time window through `--since`; defaults to the last 60 minutes.

Operating assumptions:

- The terminal already has AWS CLI access to the target environment.
- The company laptop profile is `saml`; the skill uses `--profile saml` internally on AWS CLI commands.
- The skill starts with `aws --version`, detects AWS CLI v1 or v2, and uses the installed version.
- If AWS CLI access is unavailable, the skill refers to `references/login-guide.md` when it has been filled in.

Primary investigation flow:

- Search X-Ray by trace ID first when available.
- Identify the error group and likely failing log group from X-Ray.
- If X-Ray cannot find the trace, ask for `x-amz-apigw-id` and use it with the original trace ID to identify the Lambda that generated the error.
- Search CloudWatch logs to find the internal log ID.
- Use the internal log ID to reconstruct the request log sequence.
- Provide as much relevant testing-environment log detail as possible, including downstream HTTP request/response logs when they explain the failure.

## ba-analyze-tool

[Skill details](ba-analyze-tool/SKILL.md)

Use this skill to turn stakeholder requirements, optional reference documentation, current implementation or design materials, and optional previous BA analysis into a versioned BA analysis package. It focuses on confirmed requirements, current-state gaps, open questions, traceability, change history, and audit records.

```bash
/ba-analyze-tool --business <path> --current <path> [--reference <path>] [--previous <path>] [--version <label>] [--output <path>]
```

Key inputs:

- Business requirements through `--business`.
- Current implementation, design, or known behavior through `--current`.
- Optional standards, API specs, vendor docs, regulatory material, or other references through `--reference`.
- Optional previous `final-ba-analysis.md` through `--previous` for lifecycle comparison.

Main modes:

- Business + Reference + Current: compares business requirements, reference rules, and current implementation.
- Business + Current: compares business requirements and current implementation without assessing external reference compliance.

Primary outputs include run metadata, source inventory, extracted business requirements, reference rules, current-state summary, gap analysis, open questions, traceability matrix, change log, open-question status check, final BA analysis report, latest status, source fingerprint register, and immutable audit records.

By default, generated files are written under `~/ba-analyze-tool/<project-folder>/ba-analysis-output/<version>/`. If `--output <path>` is provided, generated files are written under `<path>/ba-analysis-output/<version>/`.

## qa-analyze-tool

[Skill details](qa-analyze-tool/SKILL.md)

Use this skill to collect or analyze requirements and generate a staged QA artifact set. It supports requirement clarification, QA strategy, BDD-style test cases, and final Xray/Jira-oriented export tables.

```bash
/qa-analyze-tool [--mode collect|preview|strategy|test_case|final] [--requirement <requirement_path>] [--jira <issue_or_url>[,<issue_or_url>...]] [--confluence <page_id_or_url>[,<confluence_page_or_url>...]]
```

Key inputs:

- Local requirement file or folder through `--requirement`.
- Jira issue keys or URLs through `--jira`.
- Confluence page IDs or URLs through `--confluence`.

Main modes:

- `collect`: collect Jira or Confluence requirements as Markdown.
- `preview`: clarify requirements and identify blockers or assumptions.
- `strategy`: generate the QA strategy after requirement clarification.
- `test_case`: generate BDD-style test cases.
- `final`: prepare the complete output set, including an Xray/Jira-oriented export table.

Primary outputs include clarified requirements, pending blockers, QA strategy, BDD test cases, upload-ready export tables, status files, and audit records.

## postman2insomnia

[Skill details](postman2insomnia/SKILL.md)

Use this skill to convert Postman Collection v2.1 JSON files plus optional Postman environment and globals JSON files into Insomnia-compatible import/export resource bundles.

```bash
/postman2insomnia --source <folder-path-to-postman> [--output <folder>] [--strict]
```

Before conversion, the skill checks that Node.js is available and runs its dependency preflight from the skill folder:

```bash
npm run preflight
```

Key inputs:

- A folder containing one or more Postman Collection v2.1 JSON files.
- Optional Postman environment JSON files.
- Optional Postman globals JSON files.

Primary outputs:

- Insomnia import JSON files.
- Migration reports.
- Script compatibility reports.

By default, generated files are written to `<folder-path-to-postman>/insomnia-migration/`. If `--output <folder>` is provided, generated files are written to that dedicated output path instead.

The converter validates source files, builds a normalized migration model, emits Insomnia resources, rewrites known-safe Postman script APIs, and reports unsupported or risky behavior for manual review.
