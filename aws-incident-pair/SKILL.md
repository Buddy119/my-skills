---
name: aws-incident-pair
description: Investigate AWS incidents using read-only commands with the installed AWS CLI version.
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
- Always detect the installed AWS CLI version before investigation:

```bash
aws --version
```

Company laptops may have AWS CLI v1 or v2 installed. Run `aws --version`, identify whether the active `aws` command is v1 or v2, and use the installed version for the investigation. The approved command templates use broadly supported read-only operations. If unsure whether a command or option is supported by the detected AWS CLI version, run the relevant help command first:

```bash
aws <service> <operation> help
```

## Usage

Examples:

```bash
/aws-incident-pair --region ap-southeast-1 --request-id <request-id> --xray-id <xray-trace-id> --since 60m
```

The skill does not parse parameters programmatically. Interpret the developer's request and use the provided region, required `saml` profile, request ID, X-Ray trace ID, and time window to select read-only AWS CLI commands.

`--request-id` and `--xray-id` are mandatory. If either one is missing, ask the developer to provide the missing ID before starting AWS log or trace investigation.

Do not define service name or error keyword as standard skill-level options. If the developer wants a specific service, server, Lambda, log group, or error pattern investigated, they can ask for it in follow-up chat, and Copilot should treat it as extra context for that turn.

If no time window is provided, default to the last 60 minutes and state that default in chat.

If no region is provided, ask the developer for the AWS region before running AWS service commands. Do not guess the region. Do not ask the developer for a profile; always use `--profile saml` in AWS CLI commands.

## Required References

Load these references as needed:

- [references/approved-aws-cli-commands.md](references/approved-aws-cli-commands.md): allowed AWS CLI command categories and templates for the detected installed version.
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
2. Confirm the developer provided `--region <aws-region>`, `--request-id <request-id>`, and `--xray-id <xray-trace-id>`. Ask for any missing value before starting AWS investigation. Always use `--profile saml` in AWS CLI commands.
3. Normalize the time window from `--since` or default to the last 60 minutes.
4. Search X-Ray first with `batch-get-traces --profile saml --region <aws-region>` using the provided X-Ray trace ID.
5. If the trace is found, identify the error group and likely failing log groups from the X-Ray output. Prefer the deepest downstream failing component first.
6. If X-Ray does not show an obvious failing log group, search only log groups connected to the trace evidence, deepest downstream component first.
7. If the trace ID cannot be found in X-Ray, pivot through API Gateway evidence using the required request ID.
8. Search exact API Gateway execution or access log events for the request ID to identify API ID, stage, resource path, HTTP method, status, integration request ID, and any X-Ray root value.
9. If API Gateway execution logs contain `Root=<xray-trace-id>`, record X-Ray status as partial evidence and continue API Gateway to Lambda correlation. Only declare no exact X-Ray evidence when neither X-Ray nor API Gateway execution logs contain the supplied trace ID.
10. Use `aws apigateway get-rest-apis`, `aws apigateway get-resources --embed methods`, and `aws apigateway get-stages` to map the API ID, stage, method, and resource path to the Lambda integration URI, then extract the Lambda function name.
11. Discover the actual Lambda CloudWatch log group with `aws logs describe-log-groups`; do not assume `/aws/lambda/<function-name>` exists.
12. After identifying the Lambda log group, search Lambda logs by API Gateway integration request ID first, then by X-Ray trace ID, request ID, or correlation ID to find the internal log ID for the request.
13. Use the internal log ID to find the whole log sequence for that request.
14. Detect the useful error from the whole request log. If the error comes from a downstream HTTP call, include the relevant HTTP request and response logs in chat.
15. Correlate evidence into a concise timeline and present findings directly in chat. Do not write incident output files.

## Evidence Rules

- Be concise but evidence-driven.
- Prefer timeline-based reasoning.
- Provide as much relevant raw log detail as possible because this skill is used in a testing environment.
- Prefer full request log sequences over abbreviated excerpts when the internal log ID is known.
- Preserve downstream HTTP request and response logs when they explain the failure.
- Do not truncate logs just to be brief; only omit clearly unrelated noise.
- Summarize logs into meaningful events.
- Never say root cause is confirmed unless logs or traces prove it.
- Always distinguish confirmed evidence from hypothesis.
- Match only the exact provided `--request-id`, `--xray-id`, or exact internal log ID. Do not use nearest logs, nearby timestamps, similar IDs, adjacent request logs, or inferred matches as evidence.
- If no trace, API Gateway access log, Lambda log, or internal request log is found for the exact provided IDs, say that directly and list the exact IDs, log groups, and time window searched.
- Treat errors logged after response generation as secondary symptoms unless the same error clearly appears before response generation.
- Do not redact testing-environment logs by default. If a value is clearly an AWS credential, private key, password, or production secret, call out that it was present and avoid repeating the raw secret value.
- Do not change AWS resources.
- Do not invoke business functions.
- Do not perform remediation actions.
- Do not require shell scripts, jq, Python scripts, or additional local dependencies.
- Use commands and options supported by the detected installed AWS CLI version.

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
- API Gateway API ID:
- API Gateway stage:
- API Gateway resource path:
- API Gateway status:
- API Gateway integration request ID:
- Error group:
- Error Lambda:
- Internal log ID:
- Log groups checked:
- Trace IDs checked:

### Relevant Raw Logs
Include as much of the relevant raw request log sequence as possible.

When an internal log ID is found, show the full related log sequence in timestamp order whenever practical. If the full sequence is too large for one response, include the most relevant continuous sections first and clearly say which time ranges or repeated noise were omitted.

If the useful error is from a downstream HTTP call, include the related request and response logs when available, such as method, URL/path, status code, latency, headers, request body fields, response body fields, and downstream error code/message.

Do not redact testing-environment logs by default. Avoid repeating raw AWS credentials, private keys, passwords, or production secrets if they appear in logs; mention their presence instead.

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
List AWS CLI commands used, including the region, log groups, trace IDs, request IDs, and internal log IDs used for the investigation.

### Missing Evidence
State what could not be confirmed. If the exact provided IDs produced no matching evidence, say so directly and do not substitute nearby logs.
