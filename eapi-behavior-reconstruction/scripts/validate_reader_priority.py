#!/usr/bin/env python3
"""Validate progressive-disclosure structure in Reader artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reader_priority import (
    READER_PRIORITY_VALIDATION_VERSION,
    ReaderPriorityError,
    load_reader_priority_schema,
    validate_reader_priority_root,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        schema = load_reader_priority_schema()
        documents = validate_reader_priority_root(args.root.resolve(), schema)
    except ReaderPriorityError as exc:
        payload = {
            "reader_priority_validation_version": READER_PRIORITY_VALIDATION_VERSION,
            "documents": [],
            "errors": {"READER-PRIORITY-SCHEMA": [str(exc)]},
        }
        print(json.dumps(payload, indent=2) if args.json else f"ERROR [READER-PRIORITY-SCHEMA]: {exc}")
        return 2
    issue_count = sum(len(document["issues"]) for document in documents)
    payload = {
        "reader_priority_validation_version": READER_PRIORITY_VALIDATION_VERSION,
        "checked_documents": len(documents),
        "primary_errors": issue_count,
        "documents": documents,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for document in documents:
            for issue in document["issues"]:
                print(
                    f"ERROR [{issue['code']}] {document['path']}:{issue['line']}: {issue['message']}"
                )
        if not issue_count:
            print(f"OK: checked {len(documents)} Reader document(s)")
    return 1 if issue_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
