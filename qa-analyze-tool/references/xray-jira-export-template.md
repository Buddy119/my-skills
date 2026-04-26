# Xray/Jira Export Template

Use this template for `output/04-xray-jira-export.md`.

```md
# Xray/Jira Export Table

## Source
- BDD file:
- Requirement feature:

| Feature | Scenario ID | Scenario Title | Requirement Reference | Preconditions | Given | When | Then | Test Data | Priority | Labels | Component | Notes |
|---------|-------------|----------------|-----------------------|---------------|-------|------|------|-----------|----------|--------|-----------|-------|
|  | SC-01 |  | AC-01 |  |  |  |  |  | High |  |  |  |
```

Rules:

- Create one table row per BDD scenario.
- Preserve requirement references and priorities.
- If a field is unavailable, leave it blank or note an approved assumption. Do not invent values.
- Keep the table easy to copy into a spreadsheet or map into an import template.
