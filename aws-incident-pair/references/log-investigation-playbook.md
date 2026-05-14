# Log Investigation Playbook

Use this default flow for AWS backend incident investigation. Present findings directly in chat. Do not create reports, templates, scripts, or investigation output files.

## Step 1: Confirm AWS CLI Version

Run:

```bash
aws --version
```

Confirm that the command works and identify whether the active `aws` command is AWS CLI v1 or v2. Use the detected installed version for the investigation. The terminal is assumed to already have AWS access, so do not perform identity or configuration checks by default.

If a command or option may differ between AWS CLI v1 and v2, run `aws <service> <operation> help` and use the form supported by the detected version.

## Step 2: Confirm Required Inputs

Require `--region <aws-region>` before running AWS service commands. Use `--profile saml` internally and the same region value on every AWS service command in the investigation.

Require both `--request-id <request-id>` and `--xray-id <xray-trace-id>`. If region, request ID, or X-Ray trace ID is missing, ask for the missing value before starting AWS investigation. Do not guess. Do not ask for a profile; always use `--profile saml`.

## Step 3: Normalize Time Window

If the developer provides `--since`, convert it into a concrete start and end time.

If no time window is provided, default to the last 60 minutes.

Always state the time window in the final chat response.

For AWS CLI compatibility:

- CloudWatch Logs `filter-log-events` uses epoch milliseconds.
- CloudWatch Logs Insights `start-query` uses epoch seconds.
- X-Ray and CloudWatch metrics accept ISO-style times.

Use simple timestamp values accepted by the detected AWS CLI version.

## Step 4: Search X-Ray By Trace ID First

Start with X-Ray using the required trace ID:

```bash
aws xray batch-get-traces --profile saml --region <aws-region> --trace-ids "<xray-trace-id>"
```

If the trace is found:

- Identify the error group from the X-Ray output when present.
- Extract service nodes, errors, faults, downstream calls, status codes, latency, and trace annotations if present.
- Identify the likely related CloudWatch log groups from Lambda names, service names, or node names in the trace.
- If multiple components are involved, start investigation from the deepest downstream failing component first, then move outward toward callers.
- If all obvious log groups appear clean, search only log groups connected to the trace evidence, still starting from the deepest downstream component.

If the trace ID cannot be found:

- Pivot through API Gateway evidence using the required request ID.
- Search API Gateway access logs for the request ID.
- If no API Gateway access log event exactly matches the request ID in the time window, state that no exact match was found and stop this fallback path. Do not use nearby API Gateway events.
- From the API Gateway access log event, identify API ID, stage, resource path, HTTP method, status, and any integration status or latency fields present.
- Use `aws apigateway get-rest-apis` to confirm the API ID or API name.
- Use `aws apigateway get-resources --embed methods` to map the resource path and HTTP method to the integration URI.
- Use `aws apigateway get-stages` to confirm the stage and access log configuration if needed.
- Extract the Lambda function name from the integration URI. Lambda proxy integration URIs usually contain `function:<lambda-name>` before `/invocations`.
- Continue the investigation in the related Lambda CloudWatch log group.

## Step 5: Search CloudWatch Logs For The Internal Log ID

In the related log group, search by available evidence in this priority order:

1. X-Ray trace ID
2. request ID
3. correlation ID
4. internal log ID if already visible in earlier evidence
5. API path if it appears in the trace or API Gateway evidence

Use `filter-log-events` for a focused search in a known log group.

Use `start-query` and `get-query-results` for Logs Insights when the query is more efficient for sorting, filtering, or correlating events in a log group.

Only exact ID matches count as evidence. Do not use nearest logs, nearby timestamps, similar IDs, adjacent request logs, or inferred matches. If a search by the provided request ID, X-Ray trace ID, or internal log ID returns no matching events, state that no matching logs were found for that exact ID and do not continue with unrelated logs.

The goal of this step is to use API Gateway evidence to identify the Lambda function, then find the internal log ID used by the application for the request. The internal log ID may be named `logId`, `log_id`, `internalLogId`, `requestLogId`, `correlationId`, or another team-specific field. State the API ID, stage, resource path, integration URI, Lambda function name, Lambda log group, and field name found.

This skill is used in a testing environment. Provide as much relevant raw log detail as possible. Do not truncate logs just to be brief; only omit clearly unrelated noise.

When exact log groups are unknown, use the service log group conventions reference and `describe-log-groups` before searching. State uncertainty if multiple candidate log groups exist.

## Step 6: Reconstruct The Whole Request Log

After finding the internal log ID, search the same related log group for the whole request sequence:

- Query or filter by the internal log ID.
- Sort events by timestamp ascending.
- Include the full relevant request sequence whenever practical: request start, key downstream calls, retries, warnings, errors, and final response or failure.
- If the useful error is from a downstream HTTP call, preserve the related HTTP request and response logs in chat when available.
- For downstream HTTP logs, keep method, URL/path, status code, latency, headers, request body fields, response body fields, and downstream error code/message when useful.
- Do not redact testing-environment logs by default. Avoid repeating raw AWS credentials, private keys, passwords, or production secrets if they appear in logs; mention their presence instead.

If the internal log ID appears in multiple related log groups, repeat the search in those groups and merge the timeline by timestamp.

## Step 7: Detect The Useful Error

From the whole request log, identify the useful error:

- Prefer the first meaningful internal error over later propagated or wrapper errors.
- Prefer errors closest to the deepest failing dependency.
- For downstream HTTP failures, preserve the request/response evidence that proves the downstream behavior, including raw log lines when available.
- Distinguish business validation failures from infrastructure/runtime failures.
- Treat generic timeout, 500, or gateway errors as symptoms unless the underlying failing call cannot be found.

Build a concise incident timeline containing:

- first observed error
- upstream caller
- failing component
- downstream dependency
- final user-facing error
- retry behavior if visible
- latency spike if visible
- status code changes

Identify the first meaningful error in the chain, not just the final propagated error.

## Step 8: Present Findings In Chat

Do not create an output file.

Present findings directly in the Copilot chat window with:

1. investigation context
2. relevant raw logs
3. evidence timeline
4. first meaningful error
5. suspected root cause
6. impact
7. recommended next safe checks
8. commands used
9. missing evidence

Separate confirmed facts from hypotheses. Never claim root cause is confirmed unless logs or traces prove it.
