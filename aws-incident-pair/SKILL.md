---
name: aws-incident-pair
description: Investigate AWS incidents, request IDs, X-Ray traces, API Gateway failures, and CloudWatch alarm-name driven API impact using read-only commands with the installed AWS CLI version.
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
- Add `--no-cli-pager` to AWS service commands by default to prevent interactive `--More--` pager prompts. If the detected AWS CLI version rejects `--no-cli-pager`, rerun the same read-only command without it and note that the installed CLI does not support the pager flag.
- Use Windows/PowerShell-safe command templates: keep AWS CLI commands on one line, avoid POSIX-only shell syntax, wrap normal scalar values in double quotes, wrap Logs Insights query strings in single quotes, and use exact CloudWatch Logs filter patterns like `--filter-pattern '"<request-id>"'`.
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
/aws-incident-pair --region ap-southeast-1 --request-id <request-id> --xray-id <xray-trace-id> --since 60m [--compare-last-success] [--compare-first-success]
/aws-incident-pair --region ap-southeast-1 --alarm-name "<cloudwatch-alarm-name>" [--alarm-name "<another-alarm-name>"] [--since 60m]
```

The skill does not parse parameters programmatically. Interpret the developer's request and use the provided region, required `saml` profile, request ID, X-Ray trace ID, alarm name, and time window to select read-only AWS CLI commands.

The skill has two investigation entrypoints:

- Request workflow: `--request-id` and `--xray-id` are mandatory. If either one is missing, ask the developer to provide the missing ID before starting AWS log or trace investigation.
- Alarm workflow: one or more `--alarm-name` values are mandatory. Match CloudWatch alarm names exactly. Do not use prefix, substring, nearest, or guessed alarm matches. `--request-id` and `--xray-id` are not required for the alarm workflow.

`--compare-last-success` is optional. When enabled, compare the error request with the latest prior successful request before the failing request timestamp for the same API Gateway API ID, stage, resource path, and HTTP method. Success means HTTP `2xx` or `3xx`.

`--compare-first-success` is optional. When enabled, compare the error request with the first later successful request after the failing request timestamp for the same API Gateway API ID, stage, resource path, and HTTP method. Success means HTTP `2xx` or `3xx`.

If both comparison flags are provided, run both comparisons and report both. The error investigation window remains based on `--since` or the default 60 minutes. Comparison lookups use separate bounded windows: start inside the error window, then expand to 6 hours and 24 hours in the requested direction if no exact success is found. Last-success lookup searches only before the failing request timestamp. First-success lookup searches only after the failing request timestamp and never beyond the current time.

In the alarm workflow, use `aws --no-cli-pager cloudwatch describe-alarms --alarm-names` to resolve the exact alarm. Prefer the alarm's latest transition into `ALARM` as the failed API discovery anchor, add a 5-minute backward buffer, and search API Gateway logs through the current time. If the developer provides `--since`, use that explicit time window instead and state the concrete start and end times. Failed API request means HTTP status `4xx` or `5xx`. Success means HTTP `2xx` or `3xx`.

When locating an API route, use CloudWatch Logs Insights against plausible API Gateway access or execution log groups before broad API Gateway metadata enumeration. Logs Insights is the fastest way to extract the actual request ID, status, method, path, stage, route key, integration request ID, and X-Ray root from observed traffic. Use API Gateway metadata after the route evidence is found to confirm integration and log settings.

For alarm workflow impact, count different failed APIs by route identity:

- REST API Gateway: API ID or name, stage, resource path, and HTTP method.
- HTTP API Gateway: API ID or name, stage, route key, HTTP method, and path when available.
- WebSocket API Gateway: API ID or name, stage, and route key.

From the first failed request timestamp through now, report for each failed route: total API request count, failed API request count, and whether at least one successful request exists for the same route identity. For each failed route, pick the earliest failed request as the representative failed request and extract request ID, integration request ID, status, timestamp, route identity, and X-Ray root if present. Present the calculation report first, then ask the developer which failed API route they want to continue investigating. Do not run the deeper request-level API Gateway to Lambda log workflow until the developer chooses a route.

Composite alarms or alarms whose metric dimensions cannot be resolved to API Gateway must be reported as unresolved unless the referenced metric alarm names are also provided. Do not infer API Gateway identity from unrelated alarm names.

Do not define service name or error keyword as standard skill-level options. If the developer wants a specific service, server, Lambda, log group, or error pattern investigated, they can ask for it in follow-up chat, and Copilot should treat it as extra context for that turn.

If no time window is provided for the request workflow, default to the last 60 minutes and state that default in chat. If no time window is provided for the alarm workflow, use the alarm transition based discovery window described above.

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
- API Gateway v2 read-only metadata

See the approved commands reference for templates.

## Forbidden Command Categories

Never run commands that mutate state, invoke production business behavior, expose secrets, decrypt protected data, modify security settings, deploy code, send commands, write records, delete data, or perform automated remediation.

See the forbidden commands reference before considering any command outside the approved categories.

## Default Workflow

Use the request workflow when the developer provides `--request-id` or `--xray-id`. Use the alarm workflow when the developer provides one or more `--alarm-name` values. If both entrypoints are provided, start with the alarm workflow and use the provided request or trace IDs only as extra context when they exactly match discovered evidence.

### Request Workflow

1. Confirm AWS CLI version with `aws --version`.
2. Confirm the developer provided `--region <aws-region>`, `--request-id <request-id>`, and `--xray-id <xray-trace-id>`. Ask for any missing value before starting AWS investigation. Always use `--profile saml` in AWS CLI commands.
3. Normalize the time window from `--since` or default to the last 60 minutes.
4. Search X-Ray first with `aws --no-cli-pager xray batch-get-traces --profile saml --region <aws-region>` using the provided X-Ray trace ID.
5. If the trace is found, identify the error group and likely failing log groups from the X-Ray output. Prefer the deepest downstream failing component first.
6. If X-Ray does not show an obvious failing log group, search only log groups connected to the trace evidence, deepest downstream component first.
7. If the trace ID cannot be found in X-Ray, pivot through API Gateway evidence using the required request ID.
8. Search exact API Gateway execution or access log events for the request ID to identify API ID, stage, resource path, HTTP method, status, integration request ID, and any X-Ray root value.
9. If API Gateway execution logs contain `Root=<xray-trace-id>`, record X-Ray status as partial evidence and continue API Gateway to Lambda correlation. Only declare no exact X-Ray evidence when neither X-Ray nor API Gateway execution logs contain the supplied trace ID.
10. Use `aws --no-cli-pager apigateway get-rest-apis`, `aws --no-cli-pager apigateway get-resources --embed methods`, and `aws --no-cli-pager apigateway get-stages` to map the API ID, stage, method, and resource path to the Lambda integration URI, then extract the Lambda function name.
11. Discover the actual Lambda CloudWatch log group with `aws --no-cli-pager logs describe-log-groups`; do not assume `/aws/lambda/<function-name>` exists.
12. After identifying the Lambda log group, search Lambda logs by API Gateway integration request ID first, then by X-Ray trace ID, request ID, or correlation ID to find the internal log ID for the request.
13. Use the internal log ID to find the whole log sequence for that request.
14. If `--compare-last-success` or `--compare-first-success` is enabled, find the requested exact successful API Gateway request for the same API ID, stage, resource path, and HTTP method. For `--compare-last-success`, search only before the failing request timestamp and choose the latest prior `2xx` or `3xx`. For `--compare-first-success`, search only after the failing request timestamp and choose the first later `2xx` or `3xx`. Start inside the error investigation window, then expand the comparison lookup to 6 hours and 24 hours in the requested direction if no exact success is found.
15. Detect the useful error from the whole request log. If the error comes from a downstream HTTP call, include the relevant HTTP request and response logs in chat.
16. If comparison is enabled and an exact success is found, reconstruct each success request's Lambda logs using integration request ID first, then request ID or internal log ID. Compare error and success flows across API Gateway fields, Lambda log sequence, downstream calls, status, latency, request/response payloads, and first meaningful divergence.
17. Correlate evidence into a concise timeline and present findings directly in chat. Do not write incident output files.

### Alarm Workflow

1. Confirm AWS CLI version with `aws --version`.
2. Confirm the developer provided `--region <aws-region>` and at least one exact `--alarm-name`. Ask only for missing region or missing alarm name. Always use `--profile saml` in AWS CLI commands.
3. Describe the exact alarm names with `aws --no-cli-pager cloudwatch describe-alarms --alarm-names`. If an alarm is missing, say the exact name was not found and do not substitute similar names.
4. For each alarm, identify whether it is a metric alarm or composite alarm. For composite alarms, report it as unresolved unless its referenced metric alarm names were also provided and found.
5. From metric alarm namespace, metric name, dimensions, and alarm configuration, resolve the likely API Gateway context and candidate log groups. Support REST API Gateway, HTTP API Gateway, and WebSocket API Gateway.
6. Normalize the discovery window. If `--since` is provided, use it. Otherwise use the alarm's latest transition into `ALARM` with a 5-minute backward buffer through the current time. State the concrete window.
7. Discover the relevant API Gateway access or execution log groups from alarm dimensions, execution log naming conventions, `/aws/apigateway/` prefixes, and known team log prefixes. If multiple candidate log groups exist, inspect only plausible API Gateway log groups and state uncertainty.
8. Use Logs Insights first to inspect API Gateway log shape and find failed events in the discovery window before running broad API Gateway metadata commands. Failed means HTTP status `4xx` or `5xx`. If no failed API Gateway log events are found, report that directly with the alarm, log groups, and window searched.
9. Group failed events by route identity. REST route identity is API ID or name, stage, resource path, and method. HTTP API route identity is API ID or name, stage, route key, method, and path when available. WebSocket route identity is API ID or name, stage, and route key.
10. For every failed route, find the first failed request timestamp. From that timestamp through now, calculate total request count, failed request count, and whether at least one `2xx` or `3xx` success exists for that exact route identity.
11. For each failed route, choose the earliest failed request as the representative failed request. Extract request ID, integration request ID when present, status, timestamp, API ID/name, stage, route/resource, method or route key, integration status, latency, and X-Ray root when present.
12. Present the alarm investigation summary and failed API route table directly in chat before deeper log investigation. Include enough route labels or row numbers for the developer to choose one or more failed APIs.
13. Ask the developer which failed API route they want to continue investigating. Do not continue into Lambda or backend logs until the developer selects a route.
14. After the developer selects a failed API route, use that route's representative failed request and continue the existing request-level API Gateway to Lambda workflow: use API Gateway metadata to confirm the selected route's integration, discover the Lambda log group, search Lambda logs by integration request ID first, then X-Ray trace ID, request ID, correlation ID, or internal log ID, reconstruct the whole request log, and identify the first meaningful error. If no X-Ray ID is present, continue through API Gateway and Lambda correlation and state that exact X-Ray evidence is missing.

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
- Match only exact provided `--alarm-name` values. Do not use nearest, prefix, substring, or inferred alarm matches.
- In alarm workflow, failed API means HTTP status `4xx` or `5xx`; successful API means HTTP status `2xx` or `3xx`.
- In alarm workflow, failed API route counts must match exact route identity. Do not merge different methods, stages, resources, route keys, or API IDs unless the log format lacks those fields; if fields are missing, state the limitation instead of inventing them.
- If no trace, API Gateway access log, Lambda log, or internal request log is found for the exact provided IDs, say that directly and list the exact IDs, log groups, and time window searched.
- For `--compare-last-success` and `--compare-first-success`, match successful requests exactly by API ID, stage, resource path, and HTTP method. Do not compare against nearest, adjacent, similar, or guessed success logs.
- `--compare-last-success` may only use successful requests before the failing request timestamp. `--compare-first-success` may only use successful requests after the failing request timestamp and never beyond the current time.
- Treat errors logged after response generation as secondary symptoms unless the same error clearly appears before response generation.
- Do not redact testing-environment logs by default. If a value is clearly an AWS credential, private key, password, or production secret, call out that it was present and avoid repeating the raw secret value.
- Do not change AWS resources.
- Do not invoke business functions.
- Do not perform remediation actions.
- Do not require shell scripts, jq, Python scripts, or additional local dependencies.
- Use commands and options supported by the detected installed AWS CLI version.

## Chat Response Format

Respond directly in chat using this structure. Put the summary, likely cause, and important decision-making evidence first. Put raw logs, command inventory, and missing evidence after the main conclusion.

### Executive Summary
- Status:
- Most likely failing component:
- First meaningful error:
- Suspected root cause:
- User-facing impact:
- Confidence:
- Immediate safe next check:

Keep this section short and useful. Lead with what the developer most needs to know.

### Suspected Root Cause
Confirmed:
- ...

Hypothesis:
- ...

### First Meaningful Error
Explain the first real error found in the chain, not only the final propagated error.

### Alarm Investigation Summary
Include this section only when the alarm workflow is used.

- Alarm names:
- Alarm state:
- Alarm metric and dimensions:
- Gateway type:
- Discovery window:
- API Gateway API ID/name:
- API Gateway stage:
- First failed request time:
- Total request count from first failure to now:
- Failed request count from first failure to now:
- Failed route count:

### Failed APIs
Include this section only when the alarm workflow is used.

| # | Route identity | First failed time | Total requests | Failed requests | Success observed | Representative request ID | Representative status |
|---:|---|---:|---:|---:|---|---|---|

After this table, ask the developer which failed API route number or route identity they want to continue investigating. Do not include representative request log reconstruction until the developer selects a route.

### Last Successful Request Comparison
Include this section only when `--compare-last-success` is enabled.

- Success request ID:
- Success integration request ID:
- Success timestamp:
- Success status:
- Comparison basis:
- Success search window:
- Window expanded:
- First meaningful divergence:

Compare the error request and last successful request across API Gateway fields, Lambda log sequence, downstream HTTP calls, status, latency, request/response payloads, and post-response behavior. Search only before the failing request timestamp. If no exact prior `2xx` or `3xx` success is found for the same API ID, stage, resource path, and HTTP method after the bounded 24-hour backward expansion, say that directly and skip this comparison.

### First Successful Request Comparison
Include this section only when `--compare-first-success` is enabled.

- Success request ID:
- Success integration request ID:
- Success timestamp:
- Success status:
- Comparison basis:
- Success search window:
- Window expanded:
- First meaningful divergence:

Compare the error request and first successful request across API Gateway fields, Lambda log sequence, downstream HTTP calls, status, latency, request/response payloads, and post-response behavior. Search only after the failing request timestamp and never beyond the current time. If no exact later `2xx` or `3xx` success is found for the same API ID, stage, resource path, and HTTP method after the bounded 24-hour forward expansion, say that directly and skip this comparison.

### Impact
State what appears to be affected and what is still unknown.

### Recommended Next Safe Checks
List read-only diagnostic steps first. Do not recommend production changes unless evidence strongly supports them.

### Evidence Timeline
| Time | Source | Event | Evidence |
|---|---|---|---|

### Investigation Context
- AWS CLI version:
- AWS profile:
- AWS region:
- Time window:
- Main evidence used:
- Alarm names checked:
- Affected service:
- X-Ray trace status:
- API Gateway type:
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

### Commands Used
List AWS CLI commands used, including the region, log groups, trace IDs, request IDs, and internal log IDs used for the investigation.

### Missing Evidence
State what could not be confirmed. If the exact provided IDs produced no matching evidence, say so directly and do not substitute nearby logs.
