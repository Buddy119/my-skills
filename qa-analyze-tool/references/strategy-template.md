# Strategy Template

Use this template for `output/02-strategy.md`.

```md
# QA Strategy Pack

## Requirement Context
- Feature or story name:
- Based on clarified requirement:
- Version or date:

## Scope
### In Scope
- 

### Out Of Scope
- 

## Assumptions
- A-01:

## Risks
- R-01:
  - Impact:
  - Reason:

## Test Approach
- Functional coverage focus:
- Priority flows:
- Validation focus:
- Negative path focus:
- Data coverage focus:
- Integration coverage focus:
- Non-functional notes if relevant:

## Scenario Inventory
| Scenario ID | Title | Objective | Preconditions | Priority | Requirement Reference |
|-------------|-------|-----------|---------------|----------|-----------------------|
| SC-01 |  |  |  |  |  |

## Coverage Notes
- Covered boundaries:
- Known exclusions:
- Items needing later confirmation:

## Traceability Matrix
| Requirement Reference | Requirement Summary | Covered By Scenario IDs | Notes |
|-----------------------|---------------------|-------------------------|-------|
| AC-01 |  | SC-01 |  |

## Recommended Next Step
- Generate BDD test cases from the scenario inventory.
```

Rules:

- Build from the clarified requirement, not the raw source.
- Prioritize functional behavior, alternate flows, validations, and key negatives.
- Keep assumptions explicit and separated from confirmed behavior.
