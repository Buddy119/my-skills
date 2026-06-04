# Forbidden AWS CLI Commands

This skill is investigation-only. Do not run AWS CLI commands that mutate state, invoke business behavior, expose secrets, decrypt data, deploy code, modify security settings, send commands, start jobs, or delete data.

If a forbidden command seems useful, explain why it may help and ask the developer to perform it manually outside the skill workflow.

## Business Invocation

Forbidden:

```bash
aws lambda invoke
```

`aws lambda invoke` is forbidden by default because it may trigger real business side effects in the target environment.

## Lambda Mutation

Forbidden:

```bash
aws lambda update-function-code
aws lambda update-function-configuration
```

## Service Remediation

Forbidden:

```bash
aws ecs update-service
aws cloudformation deploy
aws cloudformation update-stack
aws ssm send-command
```

## API Gateway Mutation

Forbidden:

```bash
aws apigateway create-*
aws apigateway update-*
aws apigateway delete-*
aws apigateway put-*
aws apigatewayv2 create-*
aws apigatewayv2 update-*
aws apigatewayv2 delete-*
aws apigatewayv2 import-*
```

## Secrets, Decryption, And Security-Sensitive Access

Forbidden:

```bash
aws secretsmanager get-secret-value
aws kms decrypt
aws iam *
```

Do not read secrets, decrypt protected values, inspect or modify IAM policy as part of this skill, or expose sensitive environment data in chat.

## Data Writes And Deletes

Forbidden:

```bash
aws dynamodb put-item
aws dynamodb update-item
aws dynamodb delete-item
aws s3 rm
```

## CloudWatch Logs Mutation

Forbidden:

```bash
aws logs delete-*
aws logs put-*
```

## AWS CLI Authentication Or Setup Commands

Forbidden:

```bash
aws configure sso
aws sso login
```

Authentication and setup commands are outside the investigation workflow. If AWS CLI access is unavailable, read the login guide and explain the relevant manual login steps to the developer instead of running setup or login commands automatically.
