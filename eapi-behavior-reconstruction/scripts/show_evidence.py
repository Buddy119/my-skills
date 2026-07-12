#!/usr/bin/env python3
"""Validate citation bounds and print exact numbered source ranges before drafting."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from runtime_guard import run_guarded


REFERENCE_RE = re.compile(r"^(?P<path>.+):(?P<start>\d+)(?:-(?P<end>\d+))?$")


def resolve_inside(repo: Path, relative: str) -> Path:
    candidate = (repo / relative).resolve()
    try:
        candidate.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {relative}") from exc
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("references", nargs="+")
    parser.add_argument("--max-lines", type=int, default=120)
    parser.add_argument("--json", action="store_true", help="emit claim-ledger evidence objects")
    parser.add_argument(
        "--source-kind",
        choices=("implementation", "test", "schema", "configuration", "iac", "comment", "naming"),
    )
    parser.add_argument("--relation", choices=("supports", "contradicts", "context"))
    parser.add_argument("--support-level", choices=("direct", "indirect", "context"))
    args = parser.parse_args()

    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"ERROR: repository directory does not exist: {repo}", file=sys.stderr)
        return 2

    errors: list[str] = []
    rendered: list[str] = []
    evidence_objects: list[dict[str, str]] = []
    if args.json and not all((args.source_kind, args.relation, args.support_level)):
        print(
            "ERROR: --json requires --source-kind, --relation, and --support-level",
            file=sys.stderr,
        )
        return 2

    for reference in args.references:
        match = REFERENCE_RE.match(reference)
        if not match:
            errors.append(f"invalid reference: {reference}; expected path:line or path:start-end")
            continue

        relative = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        if start < 1 or end < start:
            errors.append(f"invalid line range: {reference}")
            continue
        if end - start + 1 > args.max_lines:
            errors.append(f"range exceeds --max-lines ({args.max_lines}): {reference}")
            continue

        try:
            source = resolve_inside(repo, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not source.is_file():
            errors.append(f"file does not exist: {relative}")
            continue

        try:
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            errors.append(f"cannot read {relative}: {exc}")
            continue
        if end > len(lines):
            errors.append(f"range outside file bounds ({len(lines)} lines): {reference}")
            continue

        normalized_reference = f"{relative}:{start}" + (f"-{end}" if end != start else "")
        excerpt = "\n".join(lines[start - 1 : end]) + "\n"
        evidence_objects.append(
            {
                "source": normalized_reference,
                "source_kind": args.source_kind or "",
                "relation": args.relation or "",
                "support_level": args.support_level or "",
                "excerpt_sha256": "sha256:" + hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                "rationale": "REPLACE_WITH_EXACT_EVIDENCE_TO_CLAIM_REASONING",
            }
        )
        rendered.append(f"### {normalized_reference}")
        for line_number in range(start, end + 1):
            rendered.append(f"{line_number:6} | {lines[line_number - 1]}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(evidence_objects, indent=2, ensure_ascii=False))
    else:
        print("\n".join(rendered))
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
