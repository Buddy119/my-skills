# Script Compatibility Rules

Postman scripts must be rewritten conservatively. Prefer direct AST rewrites for known-safe APIs and preserve original logic when uncertain.

## Inheritance

For each request:

```text
finalPreRequestScript =
  collection prerequest
  + parent folder prerequest(s)
  + request prerequest

finalAfterResponseScript =
  collection test
  + parent folder test(s)
  + request test
```

Do not drop inherited scripts.

## Known API Rewrites

| Postman API | Insomnia API |
| --- | --- |
| `pm.environment.get("x")` | `insomnia.environment.get("x")` |
| `pm.environment.set("x", v)` | `insomnia.environment.set("x", v)` |
| `pm.environment.unset("x")` | `insomnia.environment.unset("x")` |
| `pm.collectionVariables.get("x")` | `insomnia.collectionVariables.get("x")` |
| `pm.collectionVariables.set("x", v)` | `insomnia.collectionVariables.set("x", v)` |
| `pm.globals.get("x")` | `insomnia.globals.get("x")` plus warning |
| `pm.globals.set("x", v)` | `insomnia.globals.set("x", v)` plus warning |
| `pm.variables.get("x")` | `insomnia.variables.get("x")` |
| `pm.variables.set("x", v)` | `insomnia.variables.set("x", v)` |
| `pm.response.json()` | `insomnia.response.json()` |
| `pm.response.text()` | `insomnia.response.text()` |
| `pm.response.code` | `insomnia.response.status` |
| `pm.test("name", fn)` | `insomnia.test("name", fn)` |
| `pm.expect(...)` | `insomnia.expect(...)` |
| `pm.sendRequest(...)` | `insomnia.sendRequest(...)` plus manual-validation warning |

## AST Rewrite Requirements

1. Parse JavaScript with Babel where possible.
2. Identify `MemberExpression` chains, including simple aliases such as `const env = pm.environment`.
3. Rewrite known-safe APIs.
4. Preserve unknown code.
5. Insert TODO comments for unsupported APIs.
6. Never delete assertions.
7. Never change business logic unless required by runtime compatibility.

## Compatibility Shim

Use the Postman compatibility shim only when parsing or safe rewriting fails. The shim keeps original Postman-style code runnable where Insomnia exposes equivalent APIs. Always report that shim fallback was used.
