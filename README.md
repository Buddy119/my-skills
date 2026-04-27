# Buddy Skills

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
| [qa-analyze-tool](qa-analyze-tool/) | Turn requirements, Jira issues, or Confluence pages into clarified QA artifacts and test exports. | `/qa-analyze-tool --mode <mode> ...` |
| [postman2insomnia](postman2insomnia/) | Convert Postman collection, environment, and globals JSON exports into Insomnia import files. | `/postman2insomnia --source <folder-path-to-postman>` |

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
