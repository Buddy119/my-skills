---
name: postman2insomnia
description: Convert Postman Collection v2.1 JSON files and Postman environment or globals JSON files into Insomnia v11-compatible import/export resource bundles. Use when the user invokes `/postman2insomnia`, asks to migrate Postman collections to Insomnia, or needs Postman scripts, variables, folders, requests, auth, and environments converted with validation and migration reports.
compatibility: GitHub Copilot agent skill. Converter scripts require Node.js and npm; dependencies are installed by the bundled preflight script when missing.

allowed-tools: shell
---

# Postman v2.1 to Insomnia v11 Migration

## Usage

```bash
/postman2insomnia --source <folder-path-to-postman> [--output <folder>] [--strict]
```

This skill performs schema-guided conversion. Do not convert directly from Postman JSON to Insomnia JSON in one LLM pass.

## Required Preflight

Before every conversion:

1. Check Node.js:

```bash
node --version
```

If Node.js is unavailable, stop immediately and ask the user to install Node.js first.

2. From this skill folder, run:

```bash
npm run preflight
```

The preflight checks for `ajv`, `ajv-draft-04`, `@babel/parser`, `@babel/traverse`, `@babel/generator`, and `@babel/types`. If any dependency is missing, it runs `npm install --no-audit --no-fund` automatically, then verifies imports. If installation fails, report the exact command and stop without converting.

## Converter Command

After preflight succeeds:

```bash
node scripts/postman2insomnia.mjs --source <folder-path-to-postman> [--output <folder>] [--strict]
```

Default output folder is `<source>/insomnia-migration/`. Never modify source Postman files.

If `--output <folder>` is provided, write every generated Insomnia JSON file and report to that folder instead of the default source-local folder. Create the destination folder if it does not already exist.

## Required Reading

Read these files before adapting or extending migration behavior:

- [schemas/postman-collection-v2.1.schema.json](schemas/postman-collection-v2.1.schema.json)
- [schemas/insomnia-v11-import.schema.json](schemas/insomnia-v11-import.schema.json)
- [knowledge/postman-v2.1-to-insomnia-v11-mapping.md](knowledge/postman-v2.1-to-insomnia-v11-mapping.md)
- [knowledge/script-compatibility-rules.md](knowledge/script-compatibility-rules.md)

For feature-specific questions, also read:

- [knowledge/insomnia-resource-model.md](knowledge/insomnia-resource-model.md)
- [knowledge/unsupported-features.md](knowledge/unsupported-features.md)

## Workflow

1. Validate source JSON and classify collection, environment, globals, and unknown files.
2. Validate Postman collections against the bundled Postman v2.1 schema.
3. Build a normalized migration AST for collection, folders, requests, variables, auth, bodies, and scripts.
4. Preserve script inheritance order: collection to folder ancestry to request.
5. Rewrite known-safe Postman script APIs to Insomnia script APIs using JavaScript AST rewriting.
6. Preserve unknown logic, add TODO comments for unsupported APIs, and use a compatibility shim only when safe rewriting fails.
7. Generate Insomnia export/import resources using the target schema and fixtures.
8. Validate the generated Insomnia bundle and parent relationships.
9. Produce an Insomnia JSON file, migration report, and script compatibility report.

## Non-Negotiable Rules

- Never generate an Insomnia field unless it exists in the target Insomnia schema or bundled expected fixture exports.
- Do not assume the Insomnia app version is the same as the import schema version. Use the bundled Insomnia schema and fixtures to determine resource shape and `__export_format`.
- Never silently drop data. Preserve the closest equivalent and add a warning when mapping is lossy.
- Never delete assertions or business logic from scripts.
- Treat unsupported collection-runner behavior as a migration warning, not as successfully converted behavior.
- If `--strict` is used, fail the conversion when validation warnings or unsupported feature warnings are present.
