#!/usr/bin/env python3
"""Validate that Reader artifacts do not expose transient publication lifecycle wording."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from publication_maturity import PublicationMaturityError, load_rules, validate_reader_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack_root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.pack_root.expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: pack root does not exist: {root}")
        return 2
    try:
        report = validate_reader_artifacts(root, load_rules())
    except PublicationMaturityError as exc:
        if args.json:
            print(json.dumps({"result": "error", "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for item in report["blocking_residues"]:
            print(
                f"ERROR [DOC-PUBLICATION-RESIDUE] {item['path']}:{item['line']}: "
                f"{item['message']}"
            )
        for item in report["review_terms"]:
            print(
                f"WARNING [DOC-PUBLICATION-TERM] {item['path']}:{item['line']}: "
                f"{item['message']}"
            )
        print(
            f"{'FAILED' if report['blocking_count'] else 'OK'}: "
            f"{report['blocking_count']} blocking residue(s), "
            f"{report['review_count']} review term(s)"
        )
    return 1 if report["blocking_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
