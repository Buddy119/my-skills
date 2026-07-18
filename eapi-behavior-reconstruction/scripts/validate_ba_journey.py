#!/usr/bin/env python3
"""Validate a BA Journey, its Scenarios, and derived Tech navigation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from markdown_structure import parse_markdown

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
    "journey_id",
    "title",
    "repository",
    "source_commit",
    "business_capabilities",
    "overall_status",
    "actors",
    "scenarios",
    "supporting_tech_behaviors",
}
REQUIRED_HEADINGS = {
    "Business goal and scope",
    "Journey map",
    "Stages and scenarios",
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
    structure = parse_markdown(text)
    if structure.issues:
        for issue in structure.issues:
            print(f"ERROR [{issue.code}] line {issue.line}: {issue.message}")
        print("SKIPPED [BA-JOURNEY-SEMANTICS] prerequisite Markdown structure is invalid")
        return 1
    try:
        frontmatter, body = split_frontmatter(text)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    missing_keys = sorted(REQUIRED_KEYS - top_level_keys(frontmatter))
    if missing_keys:
        errors.append("missing YAML keys: " + ", ".join(missing_keys))

    journey_id = scalar_value(frontmatter, "journey_id")
    if not semantic_id(journey_id, "journey"):
        errors.append("journey_id must use <repository>.journey.<semantic-slug>")
    status = scalar_value(frontmatter, "overall_status")
    if status not in ALLOWED_STATUSES:
        errors.append("overall_status must be Confirmed, Inferred, Conflicting, or Unknown")

    missing_headings = sorted(REQUIRED_HEADINGS - headings(body))
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))
    if not has_mermaid(body):
        errors.append("Journey map must contain a Mermaid flowchart or graph")
    if RAW_CITATION_RE.search(body):
        errors.append("BA Journey must not contain raw source citations")

    scenario_count, scenario_document_count = linked_entry_counts(
        frontmatter, "scenarios", "scenario_id"
    )
    if scenario_count != scenario_document_count:
        errors.append("every scenarios entry must contain scenario_id and document")
    scenarios = linked_entries(frontmatter, "scenarios", "scenario_id")
    if not scenarios:
        errors.append("BA Journey must list at least one Scenario")
    duplicate_ids, duplicate_documents = duplicate_values(scenarios)
    if duplicate_ids:
        errors.append("duplicate Scenario IDs: " + ", ".join(sorted(duplicate_ids)))
    if duplicate_documents:
        errors.append("duplicate Scenario documents: " + ", ".join(sorted(duplicate_documents)))

    repository = scalar_value(frontmatter, "repository")
    source_commit = scalar_value(frontmatter, "source_commit")
    derived_tech: dict[str, Path] = {}
    for scenario_id, document in scenarios:
        scenario_path = resolved(args.document, document)
        if not scenario_path.is_file():
            errors.append(f"linked Scenario does not exist: {document}")
            continue
        try:
            scenario_frontmatter, _ = split_frontmatter(
                scenario_path.read_text(encoding="utf-8")
            )
        except ValueError as exc:
            errors.append(f"linked Scenario is invalid: {document}: {exc}")
            continue
        if scalar_value(scenario_frontmatter, "scenario_id") != scenario_id:
            errors.append(f"declared scenario_id does not match linked Scenario: {scenario_id}")
        for key, expected in (("repository", repository), ("source_commit", source_commit)):
            if scalar_value(scenario_frontmatter, key) != expected:
                errors.append(f"Journey and linked Scenario must have the same {key}: {scenario_id}")
        backlinks = linked_entries(scenario_frontmatter, "journeys", "journey_id")
        if not any(
            backlink_id == journey_id
            and resolved(scenario_path, backlink_document) == args.document.resolve()
            for backlink_id, backlink_document in backlinks
        ):
            errors.append(f"linked Scenario lacks Journey backlink: {scenario_id} -> {journey_id}")
        if not markdown_link(body, document):
            errors.append(f"Journey body must link Scenario: {document}")
        for behavior_id, behavior_document in linked_entries(
            scenario_frontmatter, "tech_behaviors", "behavior_id"
        ):
            derived_tech[behavior_id] = resolved(scenario_path, behavior_document)

    tech_count, tech_document_count = linked_entry_counts(
        frontmatter, "supporting_tech_behaviors", "behavior_id"
    )
    if tech_count != tech_document_count:
        errors.append(
            "every supporting_tech_behaviors entry must contain behavior_id and document"
        )
    supporting_tech = linked_entries(
        frontmatter, "supporting_tech_behaviors", "behavior_id"
    )
    if not supporting_tech:
        errors.append("BA Journey must list derived supporting Tech Behaviors")
    duplicate_ids, duplicate_documents = duplicate_values(supporting_tech)
    if duplicate_ids:
        errors.append("duplicate supporting Tech Behavior IDs: " + ", ".join(sorted(duplicate_ids)))
    if duplicate_documents:
        errors.append(
            "duplicate supporting Tech Behavior documents: "
            + ", ".join(sorted(duplicate_documents))
        )

    declared_tech: dict[str, Path] = {}
    for behavior_id, document in supporting_tech:
        tech_path = resolved(args.document, document)
        declared_tech[behavior_id] = tech_path
        if not tech_path.is_file():
            errors.append(f"linked Tech behavior does not exist: {document}")
            continue
        try:
            tech_frontmatter, _ = split_frontmatter(tech_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"linked Tech behavior is invalid: {document}: {exc}")
            continue
        if scalar_value(tech_frontmatter, "behavior_id") != behavior_id:
            errors.append(f"declared behavior_id does not match linked Tech behavior: {behavior_id}")
        for key, expected in (("repository", repository), ("source_commit", source_commit)):
            if scalar_value(tech_frontmatter, key) != expected:
                errors.append(f"Journey and linked Tech behavior must have the same {key}: {behavior_id}")
        if not markdown_link(body, document):
            errors.append(f"Journey body must link supporting Tech behavior: {document}")

    if set(declared_tech) != set(derived_tech):
        missing = sorted(set(derived_tech) - set(declared_tech))
        extra = sorted(set(declared_tech) - set(derived_tech))
        if missing:
            errors.append("Journey omits Tech Behaviors derived from Scenarios: " + ", ".join(missing))
        if extra:
            errors.append("Journey lists Tech Behaviors not used by its Scenarios: " + ", ".join(extra))
    for behavior_id in sorted(set(declared_tech) & set(derived_tech)):
        if declared_tech[behavior_id] != derived_tech[behavior_id]:
            errors.append(f"Journey and Scenario resolve Tech behavior differently: {behavior_id}")

    if has_placeholders(text):
        errors.append("template placeholders remain in the document")

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print("OK: BA Journey has valid Scenario links and derived Tech navigation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
