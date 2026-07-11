#!/usr/bin/env python3
"""Validate the minimum structure and source evidence of a behavior document."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_KEYS = {
    "behavior_id",
    "title",
    "repository",
    "source_commit",
    "entry_type",
    "entry_point",
    "overall_status",
    "consumes",
    "produces",
    "reads",
    "writes",
    "external_dependencies",
    "field_mappings",
    "analysis_limitations",
}

REQUIRED_HEADINGS = {
    "Summary",
    "Trigger and entry point",
    "Inputs and mapping",
    "Field mappings",
    "Preconditions and business rules",
    "Happy path",
    "Data access and state changes",
    "Outputs and side effects",
    "Failures, retries, and partial success",
    "Security, privacy, and audit",
    "External dependency stubs",
    "Test coverage",
    "Open questions and conflicts",
    "Evidence index",
}

ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
EVIDENCE_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?`"
)


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("YAML frontmatter is not closed with ---")
    return text[4:end], text[end + 5 :]


def top_level_keys(frontmatter: str) -> set[str]:
    keys: set[str] = set()
    for line in frontmatter.splitlines():
        if line and not line[0].isspace():
            match = re.match(r"([A-Za-z_][A-Za-z0-9_-]*):", line)
            if match:
                keys.add(match.group(1))
    return keys


def scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if not args.document.is_file():
        print(f"ERROR: document does not exist: {args.document}")
        return 2
    if not args.repo.is_dir():
        print(f"ERROR: repository directory does not exist: {args.repo}")
        return 2

    text = args.document.read_text(encoding="utf-8")
    try:
        frontmatter, body = split_frontmatter(text)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    missing_keys = sorted(REQUIRED_KEYS - top_level_keys(frontmatter))
    if missing_keys:
        errors.append("missing YAML keys: " + ", ".join(missing_keys))

    status = scalar_value(frontmatter, "overall_status")
    if status not in ALLOWED_STATUSES:
        errors.append("overall_status must be Confirmed, Inferred, Conflicting, or Unknown")

    headings = set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))
    missing_headings = sorted(REQUIRED_HEADINGS - headings)
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))

    has_structured_mappings = bool(re.search(r"^field_mappings:\s*\n\s+-\s+mapping_id:", frontmatter, re.M))
    if has_structured_mappings and not re.search(r"\bFM-\d+\b", body):
        errors.append("structured field_mappings exist but no FM-nnn mapping appears in the Field mappings section")

    citations = list(EVIDENCE_RE.finditer(body))
    if not citations:
        errors.append("no source citations found; use `relative/path.ext:line`")

    checked: set[tuple[str, int, int | None]] = set()
    for match in citations:
        rel = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end")) if match.group("end") else None
        key = (rel, start, end)
        if key in checked:
            continue
        checked.add(key)

        source = args.repo / rel
        if not source.is_file():
            errors.append(f"cited file does not exist: {rel}")
            continue
        if end is not None and end < start:
            errors.append(f"invalid line range: {rel}:{start}-{end}")
            continue
        try:
            line_count = sum(1 for _ in source.open(encoding="utf-8", errors="replace"))
        except OSError as exc:
            errors.append(f"cannot read cited file {rel}: {exc}")
            continue
        final_line = end or start
        if start < 1 or final_line > line_count:
            errors.append(f"citation outside file bounds: {rel}:{start}" + (f"-{end}" if end else ""))

    if "Unknown" not in body and "Conflicting" not in body:
        warnings.append("document contains no Unknown or Conflicting review items")
    if "TODO" in text or "path/to/" in text or "repository.behavior-name" in text:
        errors.append("template placeholders remain in the document")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {len(citations)} citation occurrence(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
