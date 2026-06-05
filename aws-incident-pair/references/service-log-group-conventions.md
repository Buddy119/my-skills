# Service Log Group Conventions

Customize this file with team-specific service-to-log-group mappings over time.

## Common Lambda Log Group Patterns

```text
/aws/lambda/<service-name>-<env>
/aws/lambda/<domain>-<service-name>-<env>
```

Examples:

```text
/aws/lambda/payment-api-prod
/aws/lambda/payment-validator-prod
/aws/lambda/customer-profile-api-sit
```

## Discover Unknown Log Groups

When the exact log group is unknown, start with:

```bash
aws --no-cli-pager logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/lambda/"
```

For a likely service prefix:

```bash
aws --no-cli-pager logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/lambda/<service-name>"
```

For API Gateway access or execution logs, common candidates include:

```bash
aws --no-cli-pager logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "API-Gateway-Execution-Logs_"
aws --no-cli-pager logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/apigateway/"
```

REST API Gateway execution logs commonly use `API-Gateway-Execution-Logs_<rest-api-id>/<stage>`. Access log groups can be custom and should be read from stage settings when available.

HTTP API Gateway and WebSocket API Gateway use API Gateway v2 metadata. Their access log groups are usually configured on the stage and can use custom names. When the API ID is already known from alarm dimensions or API Gateway logs, use `aws --no-cli-pager apigatewayv2 get-stages --api-id <api-id>` to inspect stage access log settings.

Team API Gateway access log groups may use custom names. If multiple API Gateway log groups exist, search likely API Gateway access log groups for the required request ID or alarm-discovered route identity and use only exact matching events to identify API ID, stage, resource path, route key, method, and status.

## Guidance

- Do not guess log groups blindly.
- Use `describe-log-groups` first if the service-to-log-group mapping is unknown.
- Always discover actual Lambda log groups with `describe-log-groups`; do not assume `/aws/lambda/<function-name>` exists.
- For X-Ray misses, prefer exact API Gateway execution/access log evidence over guessing Lambda log groups.
- For alarm-name investigations, prefer API Gateway log groups discovered from the alarm's API Gateway dimensions and Logs Insights inspection. Use stage access log settings as confirmation when the API ID is already known. Do not infer the gateway only from the alarm name.
- Prefer environment-specific names when the naming convention makes the target clear.
- State uncertainty if multiple candidate log groups exist.
- If there are several candidates, search plausible candidates by exact request ID. Do not use nearest or adjacent logs as substitutes for an exact ID match.
