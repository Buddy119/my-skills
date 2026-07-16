#!/usr/bin/env python3
"""Validate a BA behavior and its bidirectional Tech Pack traceability."""

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
    "business_capability",
    "behavior_type",
    "overall_status",
    "actors",
    "tech_behavior_document",
}
REQUIRED_HEADINGS = {
    "Business summary",
    "Business trigger and actors",
    "Business flow",
    "Business preconditions",
    "Business rules",
    "Business inputs and outputs",
    "Business outcomes",
    "Business exceptions",
    "External business interactions",
    "Open questions",
    "Traceability",
}
ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
ALLOWED_TYPES = {"business", "integration"}
RAW_CITATION_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?`"
)
TECH_JARGON_RE = re.compile(
    r"\b(?:Controller|Handler|DTO|Lambda|DynamoDB|EventBridge|Java|TypeScript|class|method)\b",
    re.I,
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


def mermaid_flow(body: str) -> str | None:
    match = re.search(r"```mermaid\s*\n(?P<flow>.*?)(?:\n```)", body, re.I | re.S)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group("flow")).strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if not args.document.is_file():
        print(f"ERROR: document does not exist: {args.document}")
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

    behavior_type = scalar_value(frontmatter, "behavior_type")
    if behavior_type not in ALLOWED_TYPES:
        errors.append("behavior_type must be business or integration")

    headings = set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))
    missing_headings = sorted(REQUIRED_HEADINGS - headings)
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))

    if not re.search(r"```mermaid\s*\n\s*(?:flowchart|graph)\b", body, re.I):
        errors.append("Business flow must contain a Mermaid flowchart or graph")

    if RAW_CITATION_RE.search(body):
        errors.append("BA behavior must not contain raw source citations; link to the Tech behavior")

    tech_document = scalar_value(frontmatter, "tech_behavior_document")
    tech_frontmatter = ""
    if not tech_document or tech_document.lower() in {"null", "none"}:
        errors.append("tech_behavior_document must point to the matching Tech behavior")
    else:
        tech_path = (args.document.parent / tech_document).resolve()
        if not tech_path.is_file():
            errors.append(f"linked Tech behavior does not exist: {tech_document}")
        else:
            try:
                tech_frontmatter, tech_body = split_frontmatter(tech_path.read_text(encoding="utf-8"))
            except ValueError as exc:
                errors.append(f"linked Tech behavior is invalid: {exc}")
            else:
                for key in ("behavior_id", "repository", "source_commit"):
                    if scalar_value(frontmatter, key) != scalar_value(tech_frontmatter, key):
                        errors.append(f"BA and Tech behavior must have the same {key}")
                expected_ba_link = Path("../../ba-pack/behaviors") / args.document.name
                tech_ba_document = scalar_value(tech_frontmatter, "ba_behavior_document")
                if tech_ba_document != expected_ba_link.as_posix():
                    errors.append(
                        "linked Tech behavior ba_behavior_document must point back to "
                        + expected_ba_link.as_posix()
                    )
                if not re.search(rf"\]\({re.escape(expected_ba_link.as_posix())}\)", tech_body):
                    errors.append("linked Tech behavior body must contain the return link to this BA behavior")
                tech_flow = mermaid_flow(tech_body)
                ba_flow = mermaid_flow(body)
                if tech_flow and ba_flow and tech_flow == ba_flow:
                    warnings.append(
                        "HIGH: BA and Tech Mermaid flows are identical; rebuild the BA flow from business "
                        "events, decisions, affected objects, and outcomes"
                    )
        if not re.search(rf"\]\({re.escape(tech_document)}\)", body):
            errors.append("BA behavior body must contain a Markdown link matching tech_behavior_document")

    jargon = sorted({match.group(0) for match in TECH_JARGON_RE.finditer(body)}, key=str.lower)
    if jargon:
        warnings.append("developer terminology found in BA narrative: " + ", ".join(jargon))

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
    print(f"OK: BA behavior is linked to its Tech behavior, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
