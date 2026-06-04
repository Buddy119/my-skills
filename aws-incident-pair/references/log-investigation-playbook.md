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

Use one of these entrypoints:

- Request workflow: require both `--request-id <request-id>` and `--xray-id <xray-trace-id>`. If region, request ID, or X-Ray trace ID is missing, ask for the missing value before starting AWS investigation.
- Alarm workflow: require one or more exact `--alarm-name <cloudwatch-alarm-name>` values. `--request-id` and `--xray-id` are not required for this workflow.

Do not guess missing required values. Do not ask for a profile; always use `--profile saml`.

## Step 3: Normalize Time Window

If the developer provides `--since`, convert it into a concrete start and end time.

For the request workflow, if no time window is provided, default to the last 60 minutes. For the alarm workflow, if no time window is provided, use the alarm's latest transition into `ALARM` plus a 5-minute backward buffer through the current time.

Always state the time window in the final chat response.

For AWS CLI compatibility:

- CloudWatch Logs `filter-log-events` uses epoch milliseconds.
- CloudWatch Logs Insights `start-query` uses epoch seconds.
- X-Ray and CloudWatch metrics accept ISO-style times.

Use simple timestamp values accepted by the detected AWS CLI version.

## Step 4: Choose The Investigation Workflow

If the developer provided `--alarm-name`, run the alarm workflow. If the developer provided request or trace IDs without alarm names, run the request workflow. If both are provided, start with the alarm workflow and use the IDs only if they exactly match discovered evidence.

## Request Workflow Step 1: Search X-Ray By Trace ID First

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
- Search exact API Gateway execution or access log events for the request ID.
- If no API Gateway execution or access log event exactly matches the request ID in the time window, state that no exact match was found and stop this fallback path. Do not use nearby API Gateway events.
- From the API Gateway log event, identify API ID, stage, resource path, HTTP method, status, integration request ID, and any integration status or latency fields present.
- If the execution log contains an X-Ray tracing value such as `Root=<xray-trace-id>`, record the X-Ray status as partial evidence even though `batch-get-traces` did not return the trace.
- Only declare no exact X-Ray evidence when neither `batch-get-traces` nor exact API Gateway execution log events contain the supplied trace ID.
- Use `aws apigateway get-rest-apis` to confirm the API ID or API name.
- Use `aws apigateway get-resources --embed methods` to map the resource path and HTTP method to the integration URI.
- Use `aws apigateway get-stages` to confirm the stage and access log configuration if needed.
- Extract the Lambda function name from the integration URI. Lambda proxy integration URIs usually contain `function:<lambda-name>` before `/invocations`.
- Discover the actual Lambda CloudWatch log group with `aws logs describe-log-groups`. Do not assume `/aws/lambda/<function-name>` exists.
- Continue the investigation in the discovered Lambda CloudWatch log group.

## Request Workflow Step 2: Search CloudWatch Logs For The Internal Log ID

In the related log group, search by available evidence in this priority order:

1. API Gateway integration request ID when it was found in execution/access logs
2. X-Ray trace ID
3. request ID
4. correlation ID
5. internal log ID if already visible in earlier evidence
6. API path if it appears in the trace or API Gateway evidence

Use `filter-log-events` for a focused search in a known log group.

Use `start-query` and `get-query-results` for Logs Insights when the query is more efficient for sorting, filtering, or correlating events in a log group.

Only exact ID matches count as evidence. Do not use nearest logs, nearby timestamps, similar IDs, adjacent request logs, or inferred matches. If a search by the provided request ID, X-Ray trace ID, or internal log ID returns no matching events, state that no matching logs were found for that exact ID and do not continue with unrelated logs.

The goal of this step is to use API Gateway evidence to identify the Lambda function, discover the actual Lambda log group, then find the internal log ID used by the application for the request. The internal log ID may be named `logId`, `log_id`, `internalLogId`, `requestLogId`, `correlationId`, or another team-specific field. State the API ID, stage, resource path, integration request ID, integration URI, Lambda function name, Lambda log group, and field name found.

This skill is used in a testing environment. Provide as much relevant raw log detail as possible. Do not truncate logs just to be brief; only omit clearly unrelated noise.

When exact log groups are unknown, use the service log group conventions reference and `describe-log-groups` before searching. State uncertainty if multiple candidate log groups exist.

## Request Workflow Step 3: Reconstruct The Whole Request Log

After finding the internal log ID, search the same related log group for the whole request sequence:

- Query or filter by the internal log ID.
- Sort events by timestamp ascending.
- Include the full relevant request sequence whenever practical: request start, key downstream calls, retries, warnings, errors, and final response or failure.
- If the useful error is from a downstream HTTP call, preserve the related HTTP request and response logs in chat when available.
- For downstream HTTP logs, keep method, URL/path, status code, latency, headers, request body fields, response body fields, and downstream error code/message when useful.
- Do not redact testing-environment logs by default. Avoid repeating raw AWS credentials, private keys, passwords, or production secrets if they appear in logs; mention their presence instead.

If the internal log ID appears in multiple related log groups, repeat the search in those groups and merge the timeline by timestamp.

## Request Workflow Step 4: Compare Directional Success When Requested

Run this step only when `--compare-last-success` or `--compare-first-success` is enabled.

- Use the failing request's API Gateway evidence as the comparison key: API ID, stage, resource path, and HTTP method.
- Success means HTTP `2xx` or `3xx`.
- The successful request must exactly match the same API ID, stage, resource path, and HTTP method. Do not use nearest routes, adjacent paths, similar methods, or guessed successful requests.
- Keep the error investigation window unchanged. It remains based on `--since` or the default 60 minutes.
- For `--compare-last-success`, find the latest prior successful API Gateway request before the failing request timestamp. Start with the portion of the error window before the failure. If no exact success is found, expand backward to 6 hours, then 24 hours before the failing request timestamp.
- For `--compare-first-success`, find the first later successful API Gateway request after the failing request timestamp. Start with the portion of the error window after the failure. If no exact success is found, expand forward to 6 hours, then 24 hours after the failing request timestamp. Do not search beyond the current time.
- If both flags are provided, run both comparisons and report both.
- If no exact success is found after the 24-hour bounded expansion in a requested direction, state that directly and skip that comparison.
- Reconstruct the successful request's Lambda logs by API Gateway integration request ID first, then by success request ID or success internal log ID.
- Compare failing and successful flows across API Gateway fields, Lambda log sequence, downstream HTTP calls, status, latency, request/response payloads, and post-response behavior.
- Report each comparison's search window, whether the window was expanded, matched request ID, integration request ID, and first meaningful divergence. Separate confirmed differences from hypotheses.

## Request Workflow Step 5: Detect The Useful Error

From the whole request log, identify the useful error:

- Prefer the first meaningful internal error over later propagated or wrapper errors.
- Prefer errors closest to the deepest failing dependency.
- For downstream HTTP failures, preserve the request/response evidence that proves the downstream behavior, including raw log lines when available.
- Downgrade post-response errors to secondary symptoms unless they appear before response generation or are proven to have caused the response status/body.
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

## Alarm Workflow Step 1: Resolve Exact Alarms

Describe the exact alarm names:

```bash
aws cloudwatch describe-alarms --profile saml --region <aws-region> --alarm-names "<alarm-name-1>" "<alarm-name-2>"
```

Rules:

- Match exact names only. Do not use prefix, substring, nearest, or guessed alarm matches.
- If an alarm name is not returned, report that exact missing name.
- For metric alarms, record namespace, metric name, dimensions, comparison operator, threshold, period, evaluation periods, state value, and latest state transition timestamp.
- For composite alarms, report them as unresolved unless the referenced metric alarm names are also provided and returned by `describe-alarms`.

## Alarm Workflow Step 2: Resolve API Gateway Context

Use the alarm metric namespace and dimensions first. Common API Gateway namespaces include `AWS/ApiGateway`. CloudWatch dimensions may identify API name, API ID, stage, method, resource, route, or route key depending on gateway type and alarm configuration.

Support these gateway types:

- REST API Gateway: route identity is API ID or name, stage, resource path, and HTTP method.
- HTTP API Gateway: route identity is API ID or name, stage, route key, HTTP method, and path when available.
- WebSocket API Gateway: route identity is API ID or name, stage, and route key.

Use read-only metadata to confirm identity and find stage log settings:

```bash
aws apigateway get-rest-apis --profile saml --region <aws-region>
aws apigateway get-resources --profile saml --region <aws-region> --rest-api-id "<rest-api-id>" --embed methods
aws apigateway get-stages --profile saml --region <aws-region> --rest-api-id "<rest-api-id>"
aws apigatewayv2 get-apis --profile saml --region <aws-region>
aws apigatewayv2 get-routes --profile saml --region <aws-region> --api-id "<api-id>"
aws apigatewayv2 get-stages --profile saml --region <aws-region> --api-id "<api-id>"
aws apigatewayv2 get-integrations --profile saml --region <aws-region> --api-id "<api-id>"
```

If alarm dimensions cannot be resolved to API Gateway, report the alarm as unresolved. Do not infer the API from the alarm name alone.

## Alarm Workflow Step 3: Normalize The Discovery Window

If the developer provided `--since`, convert it into a concrete start time and use now as the end time unless the developer gave an explicit end.

If no `--since` is provided, use the alarm's latest transition into `ALARM` as the anchor. Add a 5-minute backward buffer before that transition, then search through the current time. State the concrete start and end time in chat.

## Alarm Workflow Step 4: Discover API Gateway Logs

Find access or execution log groups from:

- stage access log settings returned by API Gateway metadata
- REST execution log naming, such as `API-Gateway-Execution-Logs_<api-id>/<stage>`
- `/aws/apigateway/` log group prefixes
- team-maintained service log group conventions

If multiple candidate API Gateway log groups exist, inspect raw shape with a small Logs Insights sample before selecting specific queries. State uncertainty and all candidate log groups checked.

## Alarm Workflow Step 5: Find Failed API Events

Search the selected API Gateway log groups in the discovery window for API Gateway events with HTTP status `4xx` or `5xx`.

Preferred behavior:

- If logs have structured fields, filter by the actual status field and route fields.
- If logs are unstructured, use message filters carefully and inspect sample events to identify where status, request ID, route, method, integration request ID, and X-Ray root appear.
- If no failed API Gateway log events are found, report that no failed API logs were found for the exact alarm, log groups, and window.

Do not count Lambda-only errors as failed API requests unless they are correlated to an API Gateway response with HTTP `4xx` or `5xx`.

## Alarm Workflow Step 6: Group Failed APIs And Count Impact

Group failed events by exact route identity:

- REST: API ID or name, stage, resource path, HTTP method.
- HTTP API: API ID or name, stage, route key, HTTP method, path when available.
- WebSocket: API ID or name, stage, route key.

For each failed route:

- identify the first failed request timestamp
- from the first failed request timestamp through now, count total API requests for the exact route
- count failed API requests for the exact route where status is `4xx` or `5xx`
- determine whether at least one successful API request exists for the exact route where status is `2xx` or `3xx`

If logs lack one or more route identity fields, state which fields are missing and avoid merging distinct routes silently.

## Alarm Workflow Step 7: Pick Representative Failed Requests

For each failed route, choose the earliest failed request as the representative failed request for later log investigation. Extract:

- request ID
- integration request ID when present
- timestamp
- status and integration status when present
- API ID or name
- gateway type and stage
- resource path, method, route key, or WebSocket route
- latency fields when present
- X-Ray root value such as `Root=<xray-trace-id>` when present

Use only exact extracted IDs in later log searches. At this stage, do not run Lambda or backend log investigation yet.

## Alarm Workflow Step 8: Present Calculation Report And Ask For Route Selection

After grouping failed routes and extracting representative request IDs, present the alarm calculation report before deeper log investigation. Include:

- alarm investigation summary
- failed API route table
- total request count from first failed request through now
- failed request count from first failed request through now
- whether success was observed for each failed route
- representative failed request ID and status for each failed route
- commands used and missing evidence so far

Number each failed API route row. Ask the developer which failed API route number or route identity they want to continue investigating. Do not continue into Lambda or backend logs until the developer selects one or more routes.

## Alarm Workflow Step 9: Investigate Selected Representative Requests

After the developer selects one or more failed API routes, continue the existing request-level API Gateway to Lambda correlation for only the selected routes:

- map route to integration with REST or API Gateway v2 metadata
- extract the Lambda function name from the integration URI when the integration is Lambda-backed
- discover the actual Lambda CloudWatch log group with `describe-log-groups`
- search Lambda logs by API Gateway integration request ID first, then X-Ray trace ID, request ID, correlation ID, or internal log ID
- reconstruct the whole request log sequence
- identify the first meaningful error

If X-Ray root is not present, continue without X-Ray and state missing exact X-Ray evidence. If the route integration is not Lambda-backed, report the integration type and use only approved read-only evidence for that backend.

## Step 10: Present Findings In Chat

Do not create an output file.

Present findings directly in the Copilot chat window with:

1. executive summary
2. suspected root cause
3. first meaningful error
4. alarm investigation summary when the alarm workflow is used
5. failed APIs table when the alarm workflow is used
6. route selection question when the alarm calculation report has been presented but no route has been selected yet
7. last successful request comparison when `--compare-last-success` is enabled
8. first successful request comparison when `--compare-first-success` is enabled
9. impact
10. recommended next safe checks
11. evidence timeline
12. investigation context
13. relevant raw logs
14. commands used
15. missing evidence

Order the response from most important to least important. Put conclusions and decision-making evidence first, then detailed context, raw logs, command inventory, and gaps.

Separate confirmed facts from hypotheses. Never claim root cause is confirmed unless logs or traces prove it.
