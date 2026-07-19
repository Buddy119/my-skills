from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from artifact_schema import load_registry  # noqa: E402
from markdown_structure import parse_markdown  # noqa: E402
from reader_priority import (  # noqa: E402
    load_reader_priority_schema,
    validate_bundled_reader_priority_contract,
    validate_reader_priority_document,
)
from validate_api_contract import validate_progressive_field_reference  # noqa: E402


def reader_document(artifact_type: str, version: str, body: str) -> str:
    return (
        "---\n"
        f'artifact_type: "{artifact_type}"\n'
        f'artifact_schema_version: "{version}"\n'
        'repository: "repo"\n'
        'source_commit: "abc"\n'
        "---\n\n"
        + body
    )


class ReaderPriorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_reader_priority_schema(
            SKILL_ROOT / "assets" / "reader-priority-schema.json"
        )

    def validate(self, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reader.md"
            path.write_text(text, encoding="utf-8")
            _artifact_type, issues = validate_reader_priority_document(path, self.schema)
            return [issue.code for issue in issues]

    def test_bundled_templates_registry_and_priority_contract_are_synchronized(self) -> None:
        registry = load_registry(SKILL_ROOT / "assets" / "artifact-schema.json")
        self.assertEqual(registry.registry_version, "6")
        self.assertEqual(
            registry.definitions["business-model"].dependencies,
            ("behavior-dossier",),
        )
        self.assertEqual(
            registry.definitions["ba-scenario"].dependencies,
            ("business-model",),
        )
        self.assertEqual(
            validate_bundled_reader_priority_contract(
                assets_root=SKILL_ROOT / "assets",
                registry_versions={
                    artifact_type: definition.current_version
                    for artifact_type, definition in registry.definitions.items()
                },
            ),
            [],
        )

    def test_simple_behavior_needs_no_empty_reference_sections(self) -> None:
        text = reader_document(
            "tech-behavior",
            "4",
            "# Behavior\n\n"
            "## Summary\n\nExplains the outcome.\n\n"
            "## Main path\n\n1. Accept the trigger.\n2. Return the result.\n\n"
            "## Behavior flow\n\n```mermaid\nflowchart LR\n A --> B\n```\n\n"
            "## Source notes\n\nNo source note is needed by this structure fixture.\n",
        )
        self.assertEqual(self.validate(text), [])

    def test_overview_rejects_inventory_before_reader_orientation(self) -> None:
        text = reader_document(
            "repository-overview",
            "3",
            "# Overview\n\n"
            "## Technical reference\n\nReference.\n\n"
            "## Repository in 5 minutes\n\nOrientation.\n\n"
            "## Capability paths\n\nPath.\n\n"
            "## Behavior variants\n\nVariants.\n\n"
            "## Risk hotspots\n\nRisks.\n\n"
            "## System context and shared behavior\n\nContext.\n\n"
            "## Coverage and unknowns\n\nCoverage.\n\n"
            "## Source notes\n\nNotes.\n",
        )
        self.assertIn("READER-PRIORITY-ORDER", self.validate(text))

    def test_api_complete_reference_is_optional_but_ordered_when_present(self) -> None:
        text = reader_document(
            "api-contract",
            "3",
            "# API\n\n"
            "## Quick reference\n\nQuick.\n\n"
            "## Request\n\nRequest.\n\n"
            "## Responses\n\nResponses.\n\n"
            "## Complete field reference\n\nRemaining fields.\n\n"
            "## Related documents\n\nLinks.\n\n"
            "## Source notes\n\nNotes.\n",
        )
        self.assertEqual(self.validate(text), [])


class ProgressiveApiFieldReferenceTests(unittest.TestCase):
    def contract(self, complete_rows: str = "", *, include_complete: bool = True) -> object:
        complete = ""
        if include_complete:
            complete = (
                "## Complete field reference\n\n"
                "| Location | Field path | Type/format | Required or present when | Nullable | Default | Rules | Basis |\n"
                "|---|---|---|---|---|---|---|---|\n"
                + complete_rows
                + "\n"
            )
        return parse_markdown(
            "---\nartifact_type: \"api-contract\"\nartifact_schema_version: \"3\"\n---\n\n"
            "# API\n\n"
            "## Quick reference\n\nQuick.\n\n"
            "## Request\n\n"
            "### Path parameters\n\n"
            "| Field | Type/format | Required | Nullable | Rules |\n"
            "|---|---|---|---|---|\n"
            "| `id` | string | Yes | No | Non-empty |\n\n"
            "## Responses\n\n"
            "| HTTP status | When | Body/schema | Relevant headers |\n"
            "|---|---|---|---|\n"
            "| 200 | Success | Result | None |\n\n"
            + complete
            + "## Related documents\n\nLinks.\n\n"
            "## Source notes\n\nNotes.\n"
        )

    def test_simple_api_does_not_require_complete_field_reference(self) -> None:
        self.assertEqual(
            validate_progressive_field_reference(
                self.contract(include_complete=False)
            ),
            [],
        )

    def test_core_and_complete_reference_cannot_repeat_field_identity(self) -> None:
        errors = validate_progressive_field_reference(
            self.contract(
                "| Path | `id` | string | Always | No | None | Non-empty | Executable |"
            )
        )
        self.assertTrue(any("duplicate field identity" in error for error in errors))

    def test_remaining_schema_field_can_be_published_once(self) -> None:
        errors = validate_progressive_field_reference(
            self.contract(
                "| Body | `metadata.note` | string | When metadata is supplied | Yes | None | Descriptive note | Schema only |"
            )
        )
        self.assertEqual(errors, [])

    def test_complete_reference_rejects_unknown_location_and_basis(self) -> None:
        errors = validate_progressive_field_reference(
            self.contract(
                "| Internal | `trace` | string | Always | No | None | Identifier | Guessed |"
            )
        )
        self.assertTrue(any("invalid Location" in error for error in errors))
        self.assertTrue(any("invalid Basis" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
