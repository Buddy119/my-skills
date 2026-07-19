#!/usr/bin/env python3
"""Validate typed lifecycle Register and reader projections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lifecycle_model import (
    LIFECYCLE_MODEL_VALIDATION_VERSION,
    LifecycleSchemaError,
    load_lifecycle_schema,
    validate_behavior_lifecycle_projection,
    validate_lifecycle_document,
    validate_lifecycle_register,
)
from register_schema import RegisterSchemaError, load_register_schema, validate_register_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_root", type=Path)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.pack_root.resolve()
    repo = args.repo.resolve() if args.repo else None
    errors: list[str] = []
    skipped: dict[str, str] = {}
    status = "invalid"
    try:
        register_schema = load_register_schema()
        lifecycle_schema = load_lifecycle_schema()
    except (RegisterSchemaError, LifecycleSchemaError) as exc:
        errors.append(str(exc))
    else:
        register = root / ".work" / "repository-register.md"
        contract = validate_register_file(register, register_schema)
        lifecycle_header_errors = contract.domain_errors.get("lifecycle", ())
        if contract.errors or lifecycle_header_errors:
            errors.extend(contract.errors)
            errors.extend(lifecycle_header_errors)
            skipped["LIFECYCLE-DOCUMENT"] = "prerequisite Lifecycle Register schema is invalid"
        else:
            result = validate_lifecycle_register(register, register_schema, lifecycle_schema)
            status = result.status
            errors.extend(result.errors)
            if result.status == "valid":
                errors.extend(
                    validate_lifecycle_document(
                        root / "tech-pack" / "data-lifecycle.md",
                        result,
                        repo,
                        lifecycle_schema,
                    )
                )
                errors.extend(validate_behavior_lifecycle_projection(root, result))
            else:
                skipped["LIFECYCLE-DOCUMENT"] = f"prerequisite Lifecycle Register is {result.status}"
    payload = {
        "result": "failed" if errors or skipped else "ok",
        "lifecycle_model_validation_version": LIFECYCLE_MODEL_VALIDATION_VERSION,
        "domain_status": status,
        "primary_errors": len(errors),
        "skipped_validation_groups": len(skipped),
        "errors": {"LIFECYCLE-MODEL": errors[:10]} if errors else {},
        "suppressed_by_group": {"LIFECYCLE-MODEL": max(0, len(errors) - 10)} if len(errors) > 10 else {},
        "skipped": skipped,
        "warnings": 0,
        "warning_messages": [],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for error in errors[:10]:
            print(f"ERROR [LIFECYCLE-MODEL] {error}")
        for code, reason in skipped.items():
            print(f"SKIPPED [{code}] {reason}")
    return 1 if errors or skipped else 0


if __name__ == "__main__":
    sys.exit(main())
