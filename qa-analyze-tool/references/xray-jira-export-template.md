# Xray/Jira Export Template

Use this template for `output/04-xray-jira-export.md`.

```md
# Xray/Jira Export Table

## Source
- BDD file:
- Requirement feature:

| Feature | Scenario ID | Scenario Title | Requirement Reference | Preconditions | Test Step | Expected Result | Test Data | Priority | Labels | Component | Notes |
|---------|-------------|----------------|-----------------------|---------------|-----------|-----------------|-----------|----------|--------|-----------|-------|
|  | SC-01 |  | AC-01 |  | 1. First executable action<br>2. Next executable action | 1. Expected outcome for the scenario |  | High |  |  |  |
```

Rules:

- Create one table row per BDD scenario.
- Do not include separate `Given`, `When`, or `Then` columns in the final export.
- Convert reusable `Background` and setup-only `Given` details into `Preconditions` when they describe state required before execution.
- Convert executable `Given`, `When`, and action-oriented `And` steps into `Test Step`.
- Convert `Then` steps and result-oriented `And` steps into `Expected Result`.
- Keep step and result ordering aligned by using numbered lines inside `Test Step` and `Expected Result` cells.
- Use `<br>` between numbered lines so each scenario remains a single Markdown table row.
- Preserve requirement references and priorities.
- If a field is unavailable, leave it blank or note an approved assumption. Do not invent values.
- Keep the table easy to copy into a spreadsheet or map into an import template.
