# Unsupported and Risky Features

Always report these items when detected. Do not silently rewrite them as fully supported behavior.

## High Risk

- `pm.execution.setNextRequest()`
- `postman.setNextRequest()`
- callback-heavy `pm.sendRequest()` flows
- dynamic variables such as `{{$randomUUID}}`, `{{$timestamp}}`, and `{{$guid}}`
- `pm.visualizer`
- `pm.cookies`
- `pm.request` mutation
- external package usage through `require()`
- crypto/hash helper usage
- file upload references
- OAuth token helper behavior
- collection runner branching and looping

## Fallback Behavior

- Preserve the closest equivalent when possible.
- Add a TODO comment to scripts where runtime behavior may differ.
- Put exact details in both the migration report and script compatibility report.
- In `--strict` mode, fail if any high-risk feature is detected.
