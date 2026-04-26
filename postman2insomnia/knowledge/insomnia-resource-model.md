# Insomnia Resource Model

This skill targets Insomnia v11-compatible import bundles using Kong's documented Insomnia JSON v4/v5-style resource-array model.

## Bundle Shape

```json
{
  "_type": "export",
  "__export_format": 4,
  "__export_date": "2026-04-26T00:00:00.000Z",
  "__export_source": "postman2insomnia-skill",
  "resources": []
}
```

`__export_format` must come from the bundled target schema or expected fixture. Do not infer it from the Insomnia application version.

## Resource Rules

- Every resource must have `_id` and `_type`.
- Supported emitted resource types are `workspace`, `environment`, `folder`, `request`, and `response`.
- The workspace uses `_id = "__WORKSPACE_ID__"`.
- The base environment uses `_id = "__BASE_ENVIRONMENT_ID__"` and `parentId = "__WORKSPACE_ID__"`.
- Generated entities use deterministic placeholder IDs such as `__folder_1__`, `__request_1__`, and `__response_1__`.
- Every non-workspace resource must have a `parentId` that points to an existing resource.
- Folder and request resources may be parented by the workspace or a folder.
- Named environments should be parented by the base environment.

## Request Script Fields

Use request-level script fields:

- `preRequestScript`
- `afterResponseScript`

Scripts must be strings. Convert Postman `script.exec` arrays to newline-joined strings before emission.

## Schema Discipline

Never generate an Insomnia field unless it is present in:

1. `schemas/insomnia-v11-import.schema.json`, or
2. the bundled expected Insomnia fixture exports.

The bundled schema is a documented baseline. If a real Insomnia v11 export is available later, replace or tighten this schema from that export.
