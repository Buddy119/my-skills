# BDD Template

Use this template for `output/03-bdd-test-cases.md`.

```md
# BDD Test Cases

## Source
- Strategy file:
- Requirement feature:

## Coverage Map
| Scenario ID | BDD Scenario Title | Requirement Reference |
|-------------|--------------------|-----------------------|
| SC-01 |  | AC-01 |

## Feature: <feature name>

### Background
Given ...

### Scenario: <scenario title>
<!-- Scenario ID: SC-01 -->
<!-- Requirement Reference: AC-01 -->
<!-- Priority: High -->
Given ...
And ...
When ...
Then ...

### Scenario: <scenario title>
<!-- Scenario ID: SC-02 -->
<!-- Requirement Reference: AC-02 -->
<!-- Priority: Medium -->
Given ...
When ...
Then ...

### Scenario Outline: <only when repetition is justified>
<!-- Scenario ID: SC-03 -->
<!-- Requirement Reference: AC-03 -->
<!-- Priority: Medium -->
Given ...
When ...
Then ...

Examples:
| input | outcome |
|-------|---------|
|  |  |
```

Rules:

- Keep one scenario per distinct business outcome.
- Preserve scenario IDs and requirement references from the strategy output.
- Use `Scenario Outline` only when several scenarios share the same structure.
- Keep steps concrete enough for QA execution, but do not turn them into long procedural scripts.
