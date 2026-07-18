#!/usr/bin/env python3
"""Validate a BA Scenario and its many-to-many Journey/Tech traceability."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ba_validation_common import (
    ALLOWED_STATUSES,
    RAW_CITATION_RE,
    duplicate_values,
    has_mermaid,
    has_placeholders,
    headings,
    linked_entries,
    linked_entry_counts,
    markdown_link,
    resolved,
    scalar_value,
    semantic_id,
    split_frontmatter,
    top_level_keys,
)


REQUIRED_KEYS = {
    "scenario_id",
    "title",
    "repository",
    "source_commit",
    "business_capabilities",
    "overall_status",
    "actors",
    "journeys",
    "tech_behaviors",
}
REQUIRED_HEADINGS = {
    "Business purpose and context",
    "Business flow",
    "Business outcomes",
    "Traceability",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
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

    scenario_id = scalar_value(frontmatter, "scenario_id")
    if not semantic_id(scenario_id, "scenario"):
        errors.append("scenario_id must use <repository>.scenario.<semantic-slug>")
    status = scalar_value(frontmatter, "overall_status")
    if status not in ALLOWED_STATUSES:
        errors.append("overall_status must be Confirmed, Inferred, Conflicting, or Unknown")

    missing_headings = sorted(REQUIRED_HEADINGS - headings(body))
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))
    if not has_mermaid(body):
        errors.append("Business flow must contain a Mermaid flowchart or graph")
    if RAW_CITATION_RE.search(body):
        errors.append("BA Scenario must not contain raw source citations")

    relationships = (
        ("journeys", "journey_id", "journey", "scenarios", "scenario_id"),
        ("tech_behaviors", "behavior_id", "Tech behavior", "ba_scenarios", "scenario_id"),
    )
    repository = scalar_value(frontmatter, "repository")
    source_commit = scalar_value(frontmatter, "source_commit")
    for block_key, id_key, label, backlink_key, backlink_id_key in relationships:
        count_ids, count_documents = linked_entry_counts(frontmatter, block_key, id_key)
        if count_ids != count_documents:
            errors.append(f"every {block_key} entry must contain {id_key} and document")
        entries = linked_entries(frontmatter, block_key, id_key)
        if not entries:
            errors.append(f"BA Scenario must list at least one {block_key} entry")
            continue
        duplicate_ids, duplicate_documents = duplicate_values(entries)
        if duplicate_ids:
            errors.append(f"duplicate {block_key} IDs: " + ", ".join(sorted(duplicate_ids)))
        if duplicate_documents:
            errors.append(
                f"duplicate {block_key} documents: " + ", ".join(sorted(duplicate_documents))
            )

        for identifier, document in entries:
            linked_path = resolved(args.document, document)
            if not linked_path.is_file():
                errors.append(f"linked {label} does not exist: {document}")
                continue
            try:
                linked_frontmatter, _ = split_frontmatter(linked_path.read_text(encoding="utf-8"))
            except ValueError as exc:
                errors.append(f"linked {label} is invalid: {document}: {exc}")
                continue
            if scalar_value(linked_frontmatter, id_key) != identifier:
                errors.append(f"declared {id_key} does not match linked document: {identifier}")
            for key, expected in (("repository", repository), ("source_commit", source_commit)):
                if scalar_value(linked_frontmatter, key) != expected:
                    errors.append(f"Scenario and linked {label} must have the same {key}: {identifier}")
            backlinks = linked_entries(linked_frontmatter, backlink_key, backlink_id_key)
            backlink_found = any(
                backlink_id == scenario_id
                and resolved(linked_path, backlink_document) == args.document.resolve()
                for backlink_id, backlink_document in backlinks
            )
            if not backlink_found:
                errors.append(f"linked {label} lacks Scenario backlink: {identifier} -> {scenario_id}")
            if not markdown_link(body, document):
                errors.append(f"Scenario body must link {label}: {document}")

    if has_placeholders(text):
        errors.append("template placeholders remain in the document")

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("OK: BA Scenario has valid Journey and Tech Behavior traceability")
    return 0


if __name__ == "__main__":
    sys.exit(main())
