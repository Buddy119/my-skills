# Immutable Runtime Policy

This policy applies whenever the Skill analyzes a repository or generates, updates, or validates a knowledge pack. It does not apply to a separate maintenance task in which the user explicitly asks to change this Skill itself.

## Release boundary

Treat the directory containing `SKILL.md` as `SKILL_ROOT`. The following are immutable release artifacts during a repository-analysis run:

- `SKILL.md`
- `agents/`
- `assets/`
- `bin/`
- `references/`
- `scripts/`
- `integrity/runtime-lock.json`

Do not request write permission for `SKILL_ROOT`. Do not edit, patch, rewrite, rename, delete, copy-and-modify, chmod, replace, or regenerate any release artifact. Do not create fallback scripts or modified validator copies. Only the user-selected knowledge-pack output directory may be written.

The SHA-256 lock detects accidental release changes; it is not an external signature and cannot prevent an actor that can rewrite both artifacts and the lock. Actual prevention comes from the host sandbox or a read-only installed release. Keep `SKILL_ROOT` outside writable workspace roots and never grant it write access during analysis. If the execution environment exposes `SKILL_ROOT` as writable, stop and use a read-only installed copy rather than relying on the lock alone.

The runtime contains no third-party Python dependencies. Never run `pip`, create a virtual environment, change `PYTHONPATH`, or install a package to make a bundled command work.

## Mandatory invocation

Resolve `SKILL_ROOT` from the selected Skill location, never from the current working directory. Invoke bundled tooling only through:

```bash
python3 -E -S -B -X utf8 "$SKILL_ROOT/bin/eapi-pack" <command> ...
```

Run `preflight` before the first operation. The launcher verifies Python 3.9+, isolated UTF-8 interpreter flags, absence of compiled Python artifacts, the allowlisted command, fixed pack output locations, and the SHA-256 of every release artifact. It verifies integrity again after every child command. Direct execution of `scripts/*.py` is unsupported; even isolated direct execution remains subject to the runtime guard and write boundaries.

Do not bypass a launcher rejection by calling a script directly, copying it elsewhere, suppressing an exit code, changing permissions, or regenerating the lock.

## Failure handling

| Signal | Meaning | Permitted response |
|---|---|---|
| Exit `0` | Command succeeded | Continue. |
| `VALIDATION_FAILED` or safe refusal / exit `1` | Generated pack artifacts are invalid, or a non-destructive operation refused existing/incomplete pack state | Fix only the knowledge-pack artifacts or invocation state, then run through the launcher again. |
| `INVOCATION_ERROR` / exit `2` | Repository, pack, document, or command arguments are wrong | Correct only the invocation or output-directory permission. |
| `FATAL_RUNTIME` / exit `70` | Python contract, integrity, import, permission boundary, or bundled runtime failed | Stop the run and report the exact failure. Do not repair it during analysis. |
| Unexpected traceback or missing module | Skill defect or incompatible runtime | Stop and report it. Do not install dependencies or patch a script. |

An output-directory permission error may justify requesting write access only to that output directory. It never justifies requesting write access to `SKILL_ROOT`.

## Maintenance boundary

Changing release artifacts and regenerating `integrity/runtime-lock.json` is allowed only in a separately scoped Skill-maintenance task explicitly requested by the user. Keep lock-generation tooling outside the installed release so normal analysis cannot invoke it. After edits are final, trusted maintenance tooling creates a candidate lock; then run the full regression suite, `preflight`, tamper tests, link-boundary tests, and a forward pack. If any release artifact changes, discard the candidate and repeat. Seal or reinstall the verified release as read-only. Normal repository analysis must never transition itself into maintenance mode.
