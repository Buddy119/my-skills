# Approved AWS CLI Commands

These commands are approved for this skill when used in a read-only incident investigation. They must be compatible with AWS CLI v1 and must rely on the terminal's existing AWS access.

Do not add explicit environment flags in the MVP workflow. The developer must provide `--region <aws-region>`. Company laptops require the AWS CLI profile `saml`, so every AWS service command in the investigation must use the same `--profile saml --region <aws-region>` pair. Do not expose profile as a skill-level input. Do not require jq, Python, shell scripts, or extra local dependencies.

Before any investigation command, run:

```bash
aws --version
```

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

List recent streams for a known log group:

```bash
aws logs describe-log-streams --profile saml --region <aws-region> --log-group-name "<log-group-name>" --order-by LastEventTime --descending --limit 20
```

Search a known log group by request ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<request-id>\"" --limit 50
```

Search a known log group by X-Ray trace ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<xray-trace-id>\"" --limit 50
```

Search a known log group by internal log ID:

```bash
aws logs filter-log-events --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-ms-start> --end-time <epoch-ms-end> --filter-pattern "\"<internal-log-id>\"" --limit 100
```

Run a focused CloudWatch Logs Insights query to find a request or trace:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-seconds-start> --end-time <epoch-seconds-end> --query-string "fields @timestamp, @message | filter @message like /<request-id-or-trace-id>/ | sort @timestamp asc | limit 50"
```

Run a focused CloudWatch Logs Insights query to reconstruct the whole request by internal log ID:

```bash
aws logs start-query --profile saml --region <aws-region> --log-group-name "<log-group-name>" --start-time <epoch-seconds-start> --end-time <epoch-seconds-end> --query-string "fields @timestamp, @message | filter @message like /<internal-log-id>/ | sort @timestamp asc | limit 100"
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

Run a metric data query when supported by the local AWS CLI v1 version:

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
aws apigateway get-resources --profile saml --region <aws-region> --rest-api-id "<rest-api-id>"
```

List stages for an API:

```bash
aws apigateway get-stages --profile saml --region <aws-region> --rest-api-id "<rest-api-id>"
```

Use API Gateway metadata only to map an incoming API path or stage to backend components. Do not update deployment, stage, method, integration, authorizer, or gateway configuration.
