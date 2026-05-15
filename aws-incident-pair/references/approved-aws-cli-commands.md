# Approved AWS CLI Commands

These commands are approved for this skill when used in a read-only incident investigation. They use broadly supported AWS CLI operations and must be run with the detected installed AWS CLI version. They must rely on the terminal's existing AWS access.

Do not add explicit environment flags in the MVP workflow. The developer must provide `--region <aws-region>`. Company laptops require the AWS CLI profile `saml`, so every AWS service command in the investigation must use the same `--profile saml --region <aws-region>` pair. Do not expose profile as a skill-level input. Do not require jq, Python, shell scripts, or extra local dependencies.

Before any investigation command, run:

```bash
aws --version
```

Interpret the output:

- `aws-cli/1.x`: use command behavior supported by AWS CLI v1.
- `aws-cli/2.x`: use AWS CLI v2 command behavior, while staying within the approved read-only command categories.

Do not require a different AWS CLI version for the MVP. Use the installed `aws` command unless the developer explicitly says otherwise.

If command compatibility is uncertain, inspect local AWS CLI help first:

```bash
aws <service> <operation> help
```

If no region is provided, ask the developer for the AWS region before running AWS service commands. Do not guess the region. Do not ask the developer for a profile; always use `--profile saml`.

## AWS CLI Version

```bash
aws --version
```

## CloudWatch Logs

Approved operations:

- `aws logs describe-log-groups`
- `aws logs describe-log-streams`
- `aws logs filter-log-events`
- `aws logs start-query`
- `aws logs get-query-results`
- `aws logs stop-query`

Discover Lambda log groups:

```bash
aws logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/lambda/"
```

Discover service-specific log groups:

```bash
aws logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/lambda/<service-name>"
```

Discover the actual Lambda log group for a function name:

```bash
aws logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/lambda/<function-name>"
```

Use the returned log group name. Do not assume `/aws/lambda/<function-name>` exists unless it appears in the `describe-log-groups` result.

List recent streams for a known log group:

```bash
aws logs describe-log-streams --profile saml --region <aws-region> --log-group-name "<log-group-name>" --order-by LastEventTime --descending --limit 20
```

Search a known log group by request ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<request-id>\"" --limit 500
```

Search a known log group by X-Ray trace ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<xray-trace-id>\"" --limit 500
```

Search a known log group by internal log ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<internal-log-id>\"" --limit 1000
```

Search a Lambda log group by API Gateway integration request ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<lambda-log-group-name>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<integration-request-id>\"" --limit 1000
```

Run a focused CloudWatch Logs Insights query to find a request or trace:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-seconds-start> --end-time <epoch-seconds-end> --query-string "fields @timestamp, @message | filter @message like /<request-id-or-trace-id>/ | sort @timestamp asc | limit 500"
```

Run a focused CloudWatch Logs Insights query to reconstruct the whole request by internal log ID:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-seconds-start> --end-time <epoch-seconds-end> --query-string "fields @timestamp, @message | filter @message like /<internal-log-id>/ | sort @timestamp asc | limit 1000"
```

Run a focused CloudWatch Logs Insights query to reconstruct a successful request by API Gateway integration request ID:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<lambda-log-group-name>" --start-time <epoch-seconds-start> --end-time <epoch-seconds-end> --query-string "fields @timestamp, @message | filter @message like /<success-integration-request-id>/ | sort @timestamp asc | limit 1000"
```

Retrieve CloudWatch Logs Insights results:

```bash
aws logs get-query-results --profile saml --region <aws-region> --query-id "<query-id>"
```

Stop a long-running or no-longer-needed Logs Insights query:

```bash
aws logs stop-query --profile saml --region <aws-region> --query-id "<query-id>"
```

## X-Ray

Approved operations:

- `aws xray get-trace-summaries`
- `aws xray batch-get-traces`
- `aws xray get-service-graph`

Find trace summaries in a time window:

```bash
aws xray get-trace-summaries --profile saml --region <aws-region> --start-time "<iso-start-time>" --end-time "<iso-end-time>"
```

Find traces with faults:

```bash
aws xray get-trace-summaries --profile saml --region <aws-region> --start-time "<iso-start-time>" --end-time "<iso-end-time>" --filter-expression "fault = true"
```

Find traces with errors:

```bash
aws xray get-trace-summaries --profile saml --region <aws-region> --start-time "<iso-start-time>" --end-time "<iso-end-time>" --filter-expression "error = true"
```

Get full trace details by trace ID:

```bash
aws xray batch-get-traces --profile saml --region <aws-region> --trace-ids "<xray-trace-id>"
```

Inspect service graph in the incident time window:

```bash
aws xray get-service-graph --profile saml --region <aws-region> --start-time "<iso-start-time>" --end-time "<iso-end-time>"
```

## Lambda Read-Only Metadata

Approved operations:

- `aws lambda list-functions`
- `aws lambda get-function`
- `aws lambda get-function-configuration`

List Lambda functions:

```bash
aws lambda list-functions --profile saml --region <aws-region>
```

Get Lambda function metadata:

```bash
aws lambda get-function --profile saml --region <aws-region> --function-name "<function-name>"
```

Get Lambda runtime configuration:

```bash
aws lambda get-function-configuration --profile saml --region <aws-region> --function-name "<function-name>"
```

Use Lambda metadata to confirm runtime, timeout, memory, last modified time, environment variable names, and tracing mode. Do not expose sensitive environment variable values in chat.

## CloudWatch Metrics

Approved operations:

- `aws cloudwatch get-metric-data`
- `aws cloudwatch get-metric-statistics`
- `aws cloudwatch describe-alarms`

Describe alarms:

```bash
aws cloudwatch describe-alarms --profile saml --region <aws-region>
```

Get Lambda error statistics:

```bash
aws cloudwatch get-metric-statistics --profile saml --region <aws-region> --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=<function-name> --start-time "<iso-start-time>" --end-time "<iso-end-time>" --period 60 --statistics Sum
```

Get Lambda duration statistics:

```bash
aws cloudwatch get-metric-statistics --profile saml --region <aws-region> --namespace AWS/Lambda --metric-name Duration --dimensions Name=FunctionName,Value=<function-name> --start-time "<iso-start-time>" --end-time "<iso-end-time>" --period 60 --statistics Average Maximum
```

Get Lambda throttle statistics:

```bash
aws cloudwatch get-metric-statistics --profile saml --region <aws-region> --namespace AWS/Lambda --metric-name Throttles --dimensions Name=FunctionName,Value=<function-name> --start-time "<iso-start-time>" --end-time "<iso-end-time>" --period 60 --statistics Sum
```

Run a metric data query when supported by the detected AWS CLI version:

```bash
aws cloudwatch get-metric-data --profile saml --region <aws-region> --metric-data-queries '<metric-data-queries-json>' --start-time "<iso-start-time>" --end-time "<iso-end-time>"
```

If unsure about the JSON shape for `get-metric-data`, inspect local help before using it.

## API Gateway Read-Only Metadata

Approved operations:

- `aws apigateway get-rest-apis`
- `aws apigateway get-resources`
- `aws apigateway get-stages`

List REST APIs:

```bash
aws apigateway get-rest-apis --profile saml --region <aws-region>
```

List resources for an API:

```bash
aws apigateway get-resources --profile saml --region <aws-region> --rest-api-id "<rest-api-id>" --embed methods
```

List stages for an API:

```bash
aws apigateway get-stages --profile saml --region <aws-region> --rest-api-id "<rest-api-id>"
```

Use API Gateway metadata only to map an incoming API path or stage to backend components. Do not update deployment, stage, method, integration, authorizer, or gateway configuration.

Search a known API Gateway access log group by request ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<api-gateway-access-log-group>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<request-id>\"" --limit 500
```

Search a known API Gateway execution log group by request ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<api-gateway-execution-log-group>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<request-id>\"" --limit 500
```

Run a Logs Insights query against API Gateway access or execution logs by request ID:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<api-gateway-log-group>" --start-time <epoch-seconds-start> --end-time <epoch-seconds-end> --query-string "fields @timestamp, @message | filter @message like /<request-id>/ | sort @timestamp asc | limit 500"
```

Find the latest prior successful API Gateway request for the same route:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<api-gateway-log-group>" --start-time <success-search-start-epoch-seconds> --end-time <error-epoch-seconds> --query-string "fields @timestamp, @message | filter @message like /<api-id>/ and @message like /<stage>/ and @message like /<resource-path>/ and @message like /<http-method>/ | filter (@message like / 2[0-9][0-9] / or @message like / 3[0-9][0-9] /) | sort @timestamp desc | limit 1"
```

Use this only after the failing request has identified the exact API ID, stage, resource path, HTTP method, and error timestamp. Search only before the failing request timestamp. Start with the portion of the error investigation window before the failure, then expand `success-search-start-epoch-seconds` backward to 6 hours and 24 hours before the failure if no exact success is found.

Find the first later successful API Gateway request for the same route:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<api-gateway-log-group>" --start-time <error-epoch-seconds> --end-time <success-search-end-epoch-seconds> --query-string "fields @timestamp, @message | filter @message like /<api-id>/ and @message like /<stage>/ and @message like /<resource-path>/ and @message like /<http-method>/ | filter (@message like / 2[0-9][0-9] / or @message like / 3[0-9][0-9] /) | sort @timestamp asc | limit 1"
```

Use this only after the failing request has identified the exact API ID, stage, resource path, HTTP method, and error timestamp. Search only after the failing request timestamp and never beyond the current time. Start with the portion of the error investigation window after the failure, then expand `success-search-end-epoch-seconds` forward to 6 hours and 24 hours after the failure if no exact success is found.

API Gateway log formats vary, so adapt the field names or message filters to the actual access/execution log shape. The successful request must exactly match the same API ID, stage, resource path, and HTTP method. Do not compare against nearest, adjacent, similar, or guessed success logs.

Use API Gateway access or execution logs to identify API ID, stage, resource path, HTTP method, status, integration request ID, integration status, latency, and X-Ray root values such as `Root=<xray-trace-id>` when these fields are present. Access and execution log formats vary by team, so inspect the raw event fields before deciding which API Gateway metadata command to run next.
