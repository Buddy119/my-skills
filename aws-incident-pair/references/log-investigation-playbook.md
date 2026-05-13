# Log Investigation Playbook

Use this default flow for AWS backend incident investigation. Present findings directly in chat. Do not create reports, templates, scripts, or investigation output files.

## Step 1: Confirm AWS CLI Version

Run:

```bash
aws --version
```

Confirm that the command works and identify whether the active `aws` command is AWS CLI v1 or v2. Use the detected installed version for the investigation. The terminal is assumed to already have AWS access, so do not perform identity or configuration checks by default.

If a command or option may differ between AWS CLI v1 and v2, run `aws <service> <operation> help` and use the form supported by the detected version.

## Step 2: Confirm Region

Require `--region <aws-region>` before running AWS service commands. Use `--profile saml` internally and the same region value on every AWS service command in the investigation.

If the developer does not provide a region, ask for it. Do not guess. Do not ask for a profile; always use `--profile saml`.

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

If a trace ID is available, start with X-Ray:

```bash
aws xray batch-get-traces --profile saml --region <aws-region> --trace-ids "<xray-trace-id>"
```

If the trace is found:

- Identify the error group from the X-Ray output when present.
- Extract service nodes, errors, faults, downstream calls, status codes, latency, and trace annotations if present.
- Identify the likely related CloudWatch log groups from Lambda names, service names, or node names in the trace.
- If multiple components are involved, start investigation from the deepest downstream failing component first, then move outward toward callers.
- If all obvious log groups appear clean, search the candidate log groups one by one, still starting from the deepest downstream component.

If the trace ID cannot be found:

- Do not guess blindly across many log groups.
- Ask the developer which Lambda log group they want to search.
- If the developer gives a service name rather than a log group, use the service log group conventions reference to discover candidates and ask the developer to choose when multiple candidates remain.

## Step 5: Search CloudWatch Logs For The Internal Log ID

In the related log group, search by available evidence in this priority order:

1. X-Ray trace ID
2. request ID
3. correlation ID
4. internal log ID if already visible in earlier evidence
5. API path if it appears in the trace or request evidence

Use `filter-log-events` for a focused search in a known log group.

Use `start-query` and `get-query-results` for Logs Insights when the query is more efficient for sorting, filtering, or correlating events in a log group.

The goal of this step is to find the internal log ID used by the application for the request. This may be named `logId`, `log_id`, `internalLogId`, `requestLogId`, `correlationId`, or another team-specific field. State the exact field name found.

Do not dump huge raw logs into chat. Show only the most useful raw snippets and summarize the rest into timeline events.

When exact log groups are unknown, use the service log group conventions reference and `describe-log-groups` before searching. State uncertainty if multiple candidate log groups exist.

## Step 6: Reconstruct The Whole Request Log

After finding the internal log ID, search the same related log group for the whole request sequence:

- Query or filter by the internal log ID.
- Sort events by timestamp ascending.
- Include enough context to show request start, key downstream calls, retries, warnings, errors, and final response or failure.
- If the useful error is from a downstream HTTP call, preserve the related HTTP request and response log snippets in chat when available.
- For downstream HTTP snippets, keep method, URL/path, status code, latency, sanitized headers, sanitized request body fields, sanitized response body fields, and downstream error code/message when useful.
- Keep raw snippets short and redact sensitive values.

If the internal log ID appears in multiple related log groups, repeat the search in those groups and merge the timeline by timestamp.

## Step 7: Detect The Useful Error

From the whole request log, identify the useful error:

- Prefer the first meaningful internal error over later propagated or wrapper errors.
- Prefer errors closest to the deepest failing dependency.
- For downstream HTTP failures, preserve the request/response evidence that proves the downstream behavior.
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
2. useful raw log snippets
3. evidence timeline
4. first meaningful error
5. suspected root cause
6. impact
7. recommended next safe checks
8. commands used
9. missing evidence

Separate confirmed facts from hypotheses. Never claim root cause is confirmed unless logs or traces prove it.
