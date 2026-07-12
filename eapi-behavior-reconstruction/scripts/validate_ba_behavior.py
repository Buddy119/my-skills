#!/usr/bin/env python3
"""Validate a BA behavior and its bidirectional Tech Pack traceability."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from runtime_guard import run_guarded
from validate_claim_ledger import find_pack_root, pack_format_version, validate_single_document
from validate_flow_separation import validate_pair


REQUIRED_KEYS = {
    "behavior_id",
    "title",
    "repository",
    "source_commit",
    "claim_ids",
    "business_capability",
    "behavior_type",
    "overall_status",
    "flow_perspective",
    "summary_perspective",
    "ba_flow_model",
    "actors",
    "business_data_object_ids",
    "business_rule_ids",
    "business_exception_ids",
    "tech_behavior_document",
}
REQUIRED_HEADINGS = {
    "Business summary",
    "Related BA knowledge",
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
    r"(?<![A-Za-z0-9_./-])(?P<path>(?!https?://)(?:[A-Za-z0-9_.-]+/)*"
    r"[A-Za-z0-9_.-]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?"
)
OBVIOUS_SECRET_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|"
    r"\baws_secret_access_key\s*[:=]\s*[\"'][A-Za-z0-9/+=]{32,}[\"']",
    re.I,
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
    pack = find_pack_root(args.document.resolve())
    version = pack_format_version(pack) if pack is not None else 1

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
    if version >= 2:
        if "Scenario at a glance" not in headings:
            warnings.append("preferred Scenario at a glance heading is absent; review whether the opening still orients a BA")
        if "Business journey" not in headings:
            warnings.append("preferred Business journey heading is absent; Mermaid flow and business explanation are still required")
        recommended = {
            "Participants and starting point",
            "Decisions and business rules",
            "Information and outcomes",
            "Exceptions and external participants",
            "Open business questions",
            "Related knowledge",
        }
        missing_recommended = sorted(recommended - headings)
        if missing_recommended:
            warnings.append("reader-oriented section(s) absent: " + ", ".join(missing_recommended))
    else:
        missing_headings = sorted(REQUIRED_HEADINGS - headings)
        if missing_headings:
            errors.append("missing sections: " + ", ".join(missing_headings))

    if not re.search(r"```mermaid\s*\n\s*(?:flowchart|graph)\b", body, re.I):
        errors.append("Business flow must contain a Mermaid flowchart or graph")

    if RAW_CITATION_RE.search(body):
        errors.append("BA behavior must not contain raw source citations; link to the Tech behavior")
    if OBVIOUS_SECRET_RE.search(body):
        errors.append("BA behavior contains an obvious secret literal; remove the value")

    related_documents = (
        "../capability-map.md",
        "../business-data-lifecycle.md",
        "../business-rule-catalog.md",
        "../business-exception-catalog.md",
    )
    for related in related_documents:
        if not (args.document.parent / related).resolve().is_file():
            errors.append(f"linked BA knowledge document does not exist: {related}")
        if not re.search(rf"\]\({re.escape(related)}\)", body):
            errors.append(f"BA behavior must link related knowledge document: {related}")

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
                flow_errors, flow_warnings, _metrics = validate_pair(tech_path, args.document.resolve())
                errors.extend(flow_errors)
                warnings.extend(flow_warnings)
        if not re.search(rf"\]\({re.escape(tech_document)}\)", body):
            errors.append("BA behavior body must contain a Markdown link matching tech_behavior_document")

    jargon = sorted({match.group(0) for match in TECH_JARGON_RE.finditer(body)}, key=str.lower)
    if jargon:
        warnings.append("developer terminology found in BA narrative: " + ", ".join(jargon))

    if "Unknown" not in body and "Conflicting" not in body:
        warnings.append("document contains no Unknown or Conflicting review items")
    if "TODO" in text or "path/to/" in text or "repository.behavior-name" in text:
        errors.append("template placeholders remain in the document")

    claim_errors, claim_warnings = validate_single_document(args.document.resolve(), args.repo.resolve())
    errors.extend("claim provenance: " + error for error in claim_errors)
    warnings.extend("claim provenance: " + warning for warning in claim_warnings)

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
    sys.exit(run_guarded(main))
