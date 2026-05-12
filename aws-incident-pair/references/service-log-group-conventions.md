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
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/"
```

For a likely service prefix:

```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/<service-name>"
```

## Guidance

- Do not guess log groups blindly.
- Use `describe-log-groups` first if the service-to-log-group mapping is unknown.
- Prefer environment-specific names when the naming convention makes the target clear.
- State uncertainty if multiple candidate log groups exist.
- If there are several candidates, search the most likely candidate first and explain why it was selected.
