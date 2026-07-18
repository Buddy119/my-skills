#!/usr/bin/env python3
"""Validate Markdown mechanics for formal Tech and BA documents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from markdown_structure import parse_markdown


def markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in (root / "tech-pack", root / "ba-pack"):
        if directory.is_dir():
            files.extend(path for path in directory.rglob("*.md") if path.is_file())
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    invalid = 0
    for path in markdown_files(args.root):
        structure = parse_markdown(path.read_text(encoding="utf-8"))
        relative = path.relative_to(args.root).as_posix()
        issues = [issue.as_dict() for issue in structure.issues]
        if issues:
            invalid += 1
        results.append({"path": relative, "status": "invalid" if issues else "valid", "issues": issues})

    payload = {
        "result": "failed" if invalid else "ok",
        "domain_statuses": {"markdown": "invalid" if invalid else "valid"},
        "primary_errors": invalid,
        "skipped_validation_groups": invalid,
        "suppressed_row_errors": 0,
        "checked_documents": len(results),
        "invalid_documents": invalid,
        "skipped": {
            f"MARKDOWN-DOCUMENT:{result['path']}":
            "specialized validation skipped because Markdown structure is invalid"
            for result in results
            if result["status"] == "invalid"
        },
        "documents": results,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for result in results:
            for issue in result["issues"]:
                print(f"ERROR [{issue['code']}] {result['path']}:{issue['line']} {issue['message']}")
            if result["status"] == "invalid":
                print(
                    f"SKIPPED [MARKDOWN-DOCUMENT:{result['path']}] "
                    "specialized validation prerequisite is invalid"
                )
        if invalid:
            print(f"FAILED: {invalid} structurally invalid Markdown document(s)")
        else:
            print(f"OK: {len(results)} Markdown document(s)")
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
