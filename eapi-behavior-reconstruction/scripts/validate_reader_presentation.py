#!/usr/bin/env python3
"""Validate Reader Pack status and evidence presentation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reader_presentation import (
    READER_PRESENTATION_VALIDATION_VERSION,
    ReaderPresentationError,
    load_reader_presentation_schema,
    reader_files,
    validate_reader_document,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        schema = load_reader_presentation_schema()
    except ReaderPresentationError as exc:
        print(f"ERROR [READER-PRESENTATION-SCHEMA] {exc}")
        return 2

    documents: list[dict[str, object]] = []
    invalid = 0
    for path in reader_files(args.root):
        artifact_type, issues = validate_reader_document(
            path,
            root=args.root,
            repo=args.repo,
            schema=schema,
        )
        if issues:
            invalid += 1
        documents.append(
            {
                "path": path.relative_to(args.root).as_posix(),
                "artifact_type": artifact_type,
                "status": "invalid" if issues else "valid",
                "issues": [issue.as_dict() for issue in issues],
            }
        )

    payload = {
        "reader_presentation_validation_version": READER_PRESENTATION_VALIDATION_VERSION,
        "result": "failed" if invalid else "ok",
        "domain_statuses": {"reader-presentation": "invalid" if invalid else "valid"},
        "primary_errors": invalid,
        "skipped_validation_groups": 0,
        "suppressed_row_errors": 0,
        "checked_documents": len(documents),
        "invalid_documents": invalid,
        "documents": documents,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for document in documents:
            for issue in document["issues"]:
                print(
                    f"ERROR [{issue['code']}] {document['path']}:{issue['line']} "
                    f"{issue['message']}"
                )
        if invalid:
            print(f"FAILED: {invalid} Reader presentation document(s)")
        else:
            print(f"OK: {len(documents)} Reader presentation document(s)")
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
