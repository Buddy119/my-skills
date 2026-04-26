# Postman v2.1 to Insomnia v11 Mapping

Use this mapping after source validation and before resource emission. Keep structure deterministic; use script rewriting only for script bodies.

## Collection and Tree

| Postman v2.1 | Insomnia target |
| --- | --- |
| `info.name` | workspace `name` |
| `info.description` | workspace `description` when supported |
| root `item[]` request | request resource with workspace parent |
| root `item[]` folder | folder resource with workspace parent |
| folder `item[]` | nested folder and request resources |
| `item.name` | folder/request `name` |
| `item.description` | folder/request `description` |
| request `method` | request `method` |
| request `url.raw` | request `url` |
| request `url.query[]` | preserve in URL query and report disabled query params |
| request `header[]` | request `headers[]`, excluding disabled headers |
| request `body.mode = raw` | request `body` with `mimeType` and `text` |
| request `body.mode = urlencoded` | request `body` with `mimeType = application/x-www-form-urlencoded` and `params[]` |
| request `body.mode = formdata` | request `body` with `mimeType = multipart/form-data` and `params[]`; file params are warned |
| request `body.mode = file` | preserve file path in `body.fileName` and warn |
| request `auth` | request `authentication` when mapped, otherwise warning |
| collection/folder/request `event.listen = prerequest` | inherited request `preRequestScript` |
| collection/folder/request `event.listen = test` | inherited request `afterResponseScript` |
| collection `variable[]` | base environment `data` |
| Postman environment `values[]` | named Insomnia environment resource |
| Postman globals `values[]` | merge into base environment when no collision; warn always |
| Postman examples/responses | response resources attached to converted request |

## Auth Mapping

| Postman auth type | Migration behavior |
| --- | --- |
| `noauth` | emit empty authentication object |
| `basic` | map `username` and `password` |
| `bearer` | map `token` and optional `prefix` |
| `apikey` | map key/value/addTo when present; warn to manually validate header/query placement |
| `digest` | map common username/password/realm/nonce values; warn |
| `oauth1` | preserve common attributes in authentication object; warn |
| `oauth2` | preserve token/config attributes; warn that helper behavior is not equivalent |
| `awsv4` | preserve AWS attributes; warn |
| `ntlm` | preserve common attributes; warn |
| `edgegrid` | preserve attributes; warn unsupported helper behavior |
| `hawk` | preserve attributes; warn unsupported helper behavior |
| unknown | preserve raw attributes under `disabledReason` report only; do not invent fields |

## Variable Rules

- Skip disabled variables in emitted environment data and report their names.
- Preserve Postman `{{name}}` template syntax, which is compatible with Insomnia references.
- Warn on dynamic variables such as `{{$randomUUID}}`, `{{$timestamp}}`, and `{{$guid}}`.
- On name collisions between collection variables, environments, and globals, keep the narrower scope and report the collision.

## Counting Rules

Semantic validation must compare source and target counts:

- request count before equals request count after
- folder count before equals folder count after
- enabled environment variable count should match generated environment data, excluding disabled variables
- every enabled Postman script event appears in an emitted request script, directly or through inherited flattening
