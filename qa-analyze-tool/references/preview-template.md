# Preview Template

Use this template for `output/01-clarified-requirement.md`.

```md
# Clarified Requirement

## Source Summary
- Source type:
- Source path or identifier:
- Materialized source:
- Preview date:

## Requirement Overview
- Feature or story name:
- Primary objective:
- Primary actors:
- Business value:

## In-Scope Behavior
- 

## Out-Of-Scope Behavior
- 

## Clarified Functional Rules
- Rule ID:
  - Description:
  - Source basis:

## Data And Validation Rules
- Rule ID:
  - Description:
  - Constraints:
  - Source basis:

## Permissions And Role Rules
- Rule ID:
  - Description:
  - Source basis:

## Integration And Dependency Notes
- 

## Error Handling Expectations
- 

## Acceptance Criteria
- AC-01:
- AC-02:

## Assumptions Approved By User
- A-01:

## Responder Identity For This Preview Invocation
- Responder Name:
- Responder Role:

## Open Non-Blocking Notes
- 

## Blocking Questions Resolved In This Preview
- Q-01:
  - Question:
  - Responder Name:
  - Responder Role:
  - User answer:
  - Resolution:

## Pending Blockers Deferred
- Q-02:
  - Why blocking:
  - Source reference:
  - Last asked:
  - Responder Name:
  - Responder Role:
  - Answer: [left blank]

## Traceability Notes
- Requirement references used:
- Files merged, if folder input:
```

Rules:

- Rewrite the requirement into a normalized structure.
- Do not copy raw ambiguity forward without either resolving it or marking it as an approved assumption.
- If blockers are deferred, keep them in `output/00-pending-blockers.md` as the unresolved queue and reflect them here only as preview context.
- Only keep non-blocking open notes at the end.
