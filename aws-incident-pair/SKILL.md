---
name: aws-incident-pair
description: Investigate AWS incidents using read-only AWS CLI v1-compatible commands.
compatibility: GitHub Copilot agent skill. Requires an already authenticated terminal that can run AWS CLI commands against the intended AWS environment.
allowed-tools: shell
---

# AWS Incident Pair

Use this skill when the developer asks Copilot to investigate an AWS backend incident from chat. This is an incident investigation pair, not an automated remediation agent.

Core principle: AWS CLI gathers facts. Copilot correlates, explains, and summarizes facts. The developer decides the action.

## Preconditions

- The current terminal already has access to the dedicated AWS environment.
- The developer must provide `--region <aws-region>` for the target AWS region.
- Company laptops require the AWS CLI profile `saml`; Copilot must use `--profile saml` on every AWS service command.
- After the region is provided, use the same `--profile saml --region <aws-region>` pair on every AWS service command in the investigation.
- Do not ask the developer to configure authentication as part of this workflow.
- Do not require or add explicit environment flags to skill usage.
- Do not run identity or AWS configuration checks by default.
- Always confirm AWS CLI compatibility before investigation:

```bash
aws --version
```

The company laptop environment uses AWS CLI v1. Do not assume AWS CLI v2 behavior. If unsure whether a command or option is supported by the installed AWS CLI v1 version, run the relevant help command first:

```bash
aws <service> <operation> help
```

## Usage

Examples:

```bash
/aws-incident-pair --region ap-southeast-1 --request-id <request-id> --since 60m
/aws-incident-pair --region ap-southeast-1 --xray-id <xray-trace-id> --since 2h
```

The skill does not parse parameters programmatically. Interpret the developer's request and use the provided region, required `saml` profile, request ID, X-Ray trace ID, and time window to select read-only AWS CLI commands.

Do not define service name or error keyword as standard skill-level options. If the developer wants a specific service, server, Lambda, log group, or error pattern investigated, they can ask for it in follow-up chat, and Copilot should treat it as extra context for that turn.

If no time window is provided, default to the last 60 minutes and state that default in chat.

If no region is provided, ask the developer for the AWS region before running AWS service commands. Do not guess the region. Do not ask the developer for a profile; always use `--profile saml` in AWS CLI commands.

## Required References

Load these references as needed:

- [references/approved-aws-cli-commands.md](references/approved-aws-cli-commands.md): allowed AWS CLI v1-compatible command categories and templates.
- [references/forbidden-aws-cli-commands.md](references/forbidden-aws-cli-commands.md): commands and command categories that must not be run.
- [references/log-investigation-playbook.md](references/log-investigation-playbook.md): default investigation workflow.
- [references/service-log-group-conventions.md](references/service-log-group-conventions.md): log group naming patterns and discovery guidance.
- [references/service-investigation-notes.md](references/service-investigation-notes.md): team-maintained service-specific investigation notes.
- [references/login-guide.md](references/login-guide.md): team-maintained AWS CLI access/login guide.

The team-maintained service investigation notes may start nearly blank. Read them when they contain relevant notes for the service, error, or log pattern being investigated.

The login guide may start blank. Do not read it during the normal investigation path. Read it only when `aws --version` is unavailable or an AWS CLI investigation command fails because the terminal lacks AWS CLI access, credentials, or authorization. If the guide has content, summarize the relevant login/access steps for the developer in chat. If the guide is blank, state that AWS CLI access appears unavailable and that the team login guide has not been filled in yet.

## Safety Boundary

Copilot may only use read-only AWS CLI commands to collect diagnostic evidence.

Do not execute commands that:

- change AWS resources
- invoke business operations
- read secrets
- decrypt data
- send messages
- start jobs
- restart services
- deploy code
- modify configuration
- delete data
- modify IAM or security settings

If an unsafe command seems useful, explain why it might help and ask the developer to perform that action manually outside this skill workflow. Do not run it.

## Approved Command Categories

Use only read-only commands from these categories:

- AWS CLI version check
- CloudWatch Logs discovery and search
- CloudWatch Logs Insights query start/result retrieval/stop
- X-Ray trace summaries, trace retrieval, and service graph
- Lambda read-only metadata
- CloudWatch metrics and alarms
- API Gateway read-only metadata

See the approved commands reference for templates.

## Forbidden Command Categories

Never run commands that mutate state, invoke production business behavior, expose secrets, decrypt protected data, modify security settings, deploy code, send commands, write records, delete data, or perform automated remediation.

See the forbidden commands reference before considering any command outside the approved categories.

## Default Workflow

1. Confirm AWS CLI version with `aws --version`.
2. Confirm the developer provided `--region <aws-region>`. Ask for it if missing. Always use `--profile saml` in AWS CLI commands.
3. Normalize the time window from `--since` or default to the last 60 minutes.
4. If a trace ID is available, search X-Ray first with `batch-get-traces --profile saml --region <aws-region>`.
5. If the trace is found, identify the error group and likely failing log groups from the X-Ray output. Prefer the deepest downstream failing component first.
6. If X-Ray does not show an obvious failing log group, search candidate log groups one by one, deepest downstream component first.
7. If the trace ID cannot be found in X-Ray, ask the developer which Lambda log group they want to inspect before continuing log search.
8. In the related CloudWatch log group, search for the trace ID, request ID, or correlation ID to find the internal log ID for the request.
9. Use the internal log ID to find the whole log sequence for that request.
10. Detect the useful error from the whole request log. If the error comes from a downstream HTTP call, preserve the relevant HTTP request and response log snippets in chat, redacting sensitive headers and payload fields.
11. Correlate evidence into a concise timeline and present findings directly in chat. Do not write incident output files.

## Evidence Rules

- Be concise but evidence-driven.
- Prefer timeline-based reasoning.
- Show only useful raw log snippets.
- Preserve useful downstream HTTP request and response snippets when they explain the failure.
- Do not dump huge raw logs.
- Summarize logs into meaningful events.
- Never say root cause is confirmed unless logs or traces prove it.
- Always distinguish confirmed evidence from hypothesis.
- Redact tokens, secrets, authorization headers, cookies, passwords, customer-sensitive payloads, and personal data.
- Do not change AWS resources.
- Do not invoke business functions.
- Do not perform remediation actions.
- Do not require shell scripts, jq, Python scripts, or additional local dependencies.
- Use AWS CLI v1-compatible commands and options only.

## Chat Response Format

Respond directly in chat using this structure:

### Investigation Context
- AWS CLI version:
- AWS profile:
- AWS region:
- Time window:
- Main evidence used:
- Affected service:
- X-Ray trace status:
- Error group:
- Internal log ID:
- Log groups checked:
- Trace IDs checked:

### Useful Raw Log Snippets
Show only the most relevant raw log snippets.

If the useful error is from a downstream HTTP call, include the relevant request and response snippets when available, such as method, URL/path, status code, latency, sanitized headers, sanitized request body fields, sanitized response body fields, and downstream error code/message.

Redact:

- tokens
- secrets
- authorization headers
- cookies
- passwords
- customer-sensitive payloads
- personal data

### Evidence Timeline
| Time | Source | Event | Evidence |
|---|---|---|---|

### First Meaningful Error
Explain the first real error found in the chain, not only the final propagated error.

### Suspected Root Cause
Confirmed:
- ...

Hypothesis:
- ...

### Impact
State what appears to be affected and what is still unknown.

### Recommended Next Safe Checks
List read-only diagnostic steps first. Do not recommend production changes unless evidence strongly supports them.

### Commands Used
List AWS CLI commands used. Redact sensitive values.

### Missing Evidence
State what could not be confirmed.
