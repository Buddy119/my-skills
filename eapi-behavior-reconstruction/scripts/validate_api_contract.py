#!/usr/bin/env python3
"""Validate a standalone API contract, its evidence, and its behavior backlink."""

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
    "entry_point",
    "method",
    "route",
    "contract_status",
    "behavior_document",
}

REQUIRED_HEADINGS = {
    "Endpoint summary",
    "API input contract",
    "API output contract",
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
    return {
        match.group(1)
        for line in frontmatter.splitlines()
        if line and not line[0].isspace()
        if (match := re.match(r"([A-Za-z_][A-Za-z0-9_-]*):", line))
    }


def scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def section_value(body: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<content>.*?)(?=^##\s+|\Z)",
        body,
        re.M | re.S,
    )
    return match.group("content") if match else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
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

    status = scalar_value(frontmatter, "contract_status")
    if status not in ALLOWED_STATUSES:
        errors.append("contract_status must be Confirmed, Inferred, Conflicting, or Unknown")

    headings = set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))
    missing_headings = sorted(REQUIRED_HEADINGS - headings)
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))

    for heading in ("API input contract", "API output contract"):
        section = section_value(body, heading)
        missing_layers = [layer for layer in ("L1", "L2", "L3") if layer not in section]
        if missing_layers:
            errors.append(f"{heading} is missing evidence layer(s): " + ", ".join(missing_layers))

    behavior_document = scalar_value(frontmatter, "behavior_document")
    if not behavior_document or behavior_document.lower() in {"null", "none"}:
        errors.append("behavior_document must point to the related behavior document")
    else:
        behavior_path = (args.document.parent / behavior_document).resolve()
        if not behavior_path.is_file():
            errors.append(f"linked behavior document does not exist: {behavior_document}")
        if not re.search(rf"\]\({re.escape(behavior_document)}\)", body):
            errors.append("contract body must contain a Markdown link matching behavior_document")

    citations = list(EVIDENCE_RE.finditer(body))
    if not citations:
        errors.append("no source citations found; use `relative/path.ext:line`")

    checked: set[tuple[str, int, int | None]] = set()
    for match in citations:
        relative = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end")) if match.group("end") else None
        key = (relative, start, end)
        if key in checked:
            continue
        checked.add(key)
        source = args.repo / relative
        if not source.is_file():
            errors.append(f"cited file does not exist: {relative}")
            continue
        if end is not None and end < start:
            errors.append(f"invalid line range: {relative}:{start}-{end}")
            continue
        try:
            line_count = sum(1 for _ in source.open(encoding="utf-8", errors="replace"))
        except OSError as exc:
            errors.append(f"cannot read cited file {relative}: {exc}")
            continue
        final_line = end or start
        if start < 1 or final_line > line_count:
            errors.append(
                f"citation outside file bounds: {relative}:{start}" + (f"-{end}" if end else "")
            )

    if "TODO" in text or "path/to/" in text or "repository.behavior-name" in text:
        errors.append("template placeholders remain in the document")

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print(f"OK: {len(citations)} citation occurrence(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

