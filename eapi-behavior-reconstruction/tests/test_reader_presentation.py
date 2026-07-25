from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from artifact_schema import load_registry  # noqa: E402
from reader_presentation import (  # noqa: E402
    load_reader_presentation_schema,
    validate_bundled_reader_contract,
    validate_reader_document,
)


class ReaderPresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "pack"
        self.repo = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        source = self.repo / "src" / "Service.java"
        source.parent.mkdir(parents=True)
        source.write_text("\n".join(f"line {number}" for number in range(1, 21)) + "\n")
        self.schema = load_reader_presentation_schema()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, body: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def tech_document(self, table: str, source_notes: str | None = None) -> str:
        notes = source_notes or (
            "## Source notes\n\n"
            '<a id="e1"></a> **E1** — `src/Service.java:2-8` supports the grouped rows.\n'
        )
        return (
            "---\n"
            'artifact_type: "runtime-config-matrix"\n'
            'artifact_schema_version: "3"\n'
            'repository: "repository"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Runtime configuration matrix\n\n"
            "The grouped configuration facts are supported by [E1](#e1).\n\n"
            + table
            + "\n\n"
            + notes
        )

    def issues(self, path: Path):
        _artifact_type, issues = validate_reader_document(
            path,
            root=self.root,
            repo=self.repo,
            schema=self.schema,
        )
        return issues

    def test_bundled_contract_matches_registry_and_templates(self) -> None:
        schema = validate_bundled_reader_contract(
            load_registry(SKILL_ROOT / "assets" / "artifact-schema.json"),
            assets_root=SKILL_ROOT / "assets",
        )
        self.assertEqual(schema["reader_presentation_schema_version"], "2")
        review_schema = json.loads(
            (SKILL_ROOT / "assets" / "finalization-review-schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn(
            "evidence-qualification-projection",
            review_schema["reviews"]["semantic-fact"]["categories"],
        )
        self.assertIn(
            "status-and-evidence-density",
            review_schema["reviews"]["reader"]["categories"],
        )

    def test_confirmed_rows_need_no_status_or_evidence_column(self) -> None:
        path = self.write(
            "tech-pack/runtime-config-matrix.md",
            self.tech_document(
                "| Configuration | Behavioral effect |\n"
                "|---|---|\n"
                "| customer.mode | Selects customer behavior [E1](#e1) |"
            ),
        )
        self.assertEqual(self.issues(path), [])

    def test_generic_status_and_evidence_headers_are_rejected(self) -> None:
        path = self.write(
            "tech-pack/runtime-config-matrix.md",
            self.tech_document(
                "| Configuration | Status | Evidence |\n"
                "|---|---|---|\n"
                "| customer.mode | Confirmed | [E1](#e1) |"
            ),
        )
        codes = {issue.code for issue in self.issues(path)}
        self.assertIn("READER-GENERIC-COLUMN", codes)

    def test_only_exceptional_qualifiers_use_the_exact_public_form(self) -> None:
        valid = self.write(
            "tech-pack/runtime-config-matrix.md",
            self.tech_document(
                "| Configuration | Behavioral effect |\n"
                "|---|---|\n"
                "| customer.mode *(Unknown)* | External value changes behavior [E1](#e1) |"
            ),
        )
        self.assertEqual(self.issues(valid), [])

        confirmed = self.tech_document(
            "| Configuration | Behavioral effect |\n"
            "|---|---|\n"
            "| customer.mode *(Confirmed)* | Selects behavior [E1](#e1) |"
        )
        valid.write_text(confirmed, encoding="utf-8")
        self.assertIn("READER-CONFIRMED-QUALIFIER", {item.code for item in self.issues(valid)})

        wrong_case = confirmed.replace("*(Confirmed)*", "*(unknown)*")
        valid.write_text(wrong_case, encoding="utf-8")
        self.assertIn("READER-QUALIFIER-FORM", {item.code for item in self.issues(valid)})

        unsupported = confirmed.replace("*(Confirmed)*", "*(Likely)*")
        valid.write_text(unsupported, encoding="utf-8")
        self.assertIn("READER-QUALIFIER-VALUE", {item.code for item in self.issues(valid)})

    def test_one_source_note_can_support_multiple_rows(self) -> None:
        path = self.write(
            "tech-pack/runtime-config-matrix.md",
            self.tech_document(
                "| Configuration | Behavioral effect |\n"
                "|---|---|\n"
                "| customer.mode | Selects behavior [E1](#e1) |\n"
                "| customer.target *(Inferred)* | Selects dependency [E1](#e1) |"
            ),
        )
        self.assertEqual(self.issues(path), [])

    def test_raw_source_citation_is_kept_out_of_reader_body(self) -> None:
        path = self.write(
            "tech-pack/runtime-config-matrix.md",
            self.tech_document(
                "| Configuration | Behavioral effect |\n"
                "|---|---|\n"
                "| customer.mode | Selects behavior [E1](#e1) `src/Service.java:2` |"
            ),
        )
        self.assertIn(
            "READER-INLINE-SOURCE-CITATION",
            {item.code for item in self.issues(path)},
        )

    def test_marker_definition_and_source_bounds_are_checked(self) -> None:
        path = self.write(
            "tech-pack/runtime-config-matrix.md",
            self.tech_document(
                "| Configuration | Behavioral effect |\n"
                "|---|---|\n"
                "| customer.mode | Selects behavior [E2](#e2) |"
            ),
        )
        self.assertIn("READER-SOURCE-UNDEFINED", {item.code for item in self.issues(path)})

        path.write_text(
            self.tech_document(
                "| Configuration | Behavioral effect |\n"
                "|---|---|\n"
                "| customer.mode | Selects behavior [E1](#e1) |",
                "## Source notes\n\n"
                '<a id="e1"></a> **E1** — `src/Service.java:2-99` supports the row.\n',
            ),
            encoding="utf-8",
        )
        self.assertIn("READER-SOURCE-BOUNDS", {item.code for item in self.issues(path)})

    def test_ba_reader_rejects_source_paths_but_keeps_tech_traceability(self) -> None:
        path = self.write(
            "ba-pack/scenarios/repository.scenario.customer.md",
            "---\n"
            'artifact_type: "ba-scenario"\n'
            'artifact_schema_version: "2"\n'
            'repository: "repository"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Customer scenario\n\n"
            "The visible outcome is supported by `src/Service.java:2-8`.\n\n"
            "## Traceability\n\n"
            "[Technical behavior](../../tech-pack/behaviors/repository.customer.md)\n",
        )
        self.assertIn("READER-BA-SOURCE-CITATION", {item.code for item in self.issues(path)})

    def test_status_sensitive_endpoint_matrix_is_exempt(self) -> None:
        path = self.write(
            "tech-pack/endpoint-matrix.md",
            "---\n"
            'artifact_type: "endpoint-matrix"\n'
            'artifact_schema_version: "1"\n'
            "---\n\n"
            "# Endpoint matrix\n\n"
            "| Layer | Status | Evidence |\n"
            "|---|---|---|\n"
            "| Application Route | Confirmed | source |\n",
        )
        self.assertEqual(self.issues(path), [])


if __name__ == "__main__":
    unittest.main()
