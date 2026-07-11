## API input contract

### Endpoint

| Property | Observed value | Status | Evidence |
|---|---|---|---|
| Method and route | `METHOD /normalized/path` | Confirmed | `path/to/file.ext:line` |
| Authentication | Scheme or Unknown | Confirmed/Unknown | `path/to/file.ext:line` |
| Content type | Value or Unknown | Confirmed/Unknown | `path/to/file.ext:line` |

### Input fields

| Location | Field path | Type/format | Required | Nullable | Default | Validation and normalization rules | Status | Evidence |
|---|---|---|---:|---:|---|---|---|---|
| Header/path/query/body | `field.path` | Type | Yes/No/Conditional | Yes/No/Unknown | None/value | Length, range, pattern, enum, conversion, or cross-field rule | Confirmed | `path/to/file.ext:line` |

### Request-level rules

| Rule ID | Rule | Failure result | Status | Evidence |
|---|---|---|---|---|
| API-IN-001 | Content, conditional, or cross-field rule | Status/error | Confirmed | `path/to/file.ext:line` |

## API output contract

### Response outcomes

| Condition | HTTP status | Body/schema | Relevant headers | Status | Evidence |
|---|---:|---|---|---|---|
| Success or failure condition | 200/400/etc. | Schema or Unknown | Header or None | Confirmed | `path/to/file.ext:line` |

### Success response fields

| Field path | Type/format | Present when | Nullable | Source/default | Output rules | Status | Evidence |
|---|---|---|---:|---|---|---|---|
| `field.path` | Type | Always/condition | Yes/No/Unknown | Source, constant, or computed | Masking, formatting, enum, rounding, or inclusion rule | Confirmed | `path/to/file.ext:line` |

### Output and error rules

| Rule ID | Rule | Applies to | Status | Evidence |
|---|---|---|---|---|
| API-OUT-001 | Response or error rule | Status/field | Confirmed | `path/to/file.ext:line` |

