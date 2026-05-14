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
aws logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/lambda/"
```

For a likely service prefix:

```bash
aws logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/lambda/<service-name>"
```

For API Gateway access or execution logs, common candidates include:

```bash
aws logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "API-Gateway-Execution-Logs_"
aws logs describe-log-groups --profile saml --region <aws-region> --log-group-name-prefix "/aws/apigateway/"
```

Team API Gateway access log groups may use custom names. If multiple API Gateway log groups exist, search likely API Gateway access log groups for the required request ID and use only exact matching events to identify API ID, stage, resource path, method, and status.

## Guidance

- Do not guess log groups blindly.
- Use `describe-log-groups` first if the service-to-log-group mapping is unknown.
- For X-Ray misses, prefer API Gateway access log evidence over guessing Lambda log groups.
- Prefer environment-specific names when the naming convention makes the target clear.
- State uncertainty if multiple candidate log groups exist.
- If there are several candidates, search plausible candidates by exact request ID. Do not use nearest or adjacent logs as substitutes for an exact ID match.
