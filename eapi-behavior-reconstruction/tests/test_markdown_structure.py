from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from markdown_structure import (  # noqa: E402
    github_heading_slug,
    load_api_contract_structure,
    parse_markdown,
    validate_api_contract_tables,
)


def document(body: str) -> str:
    return '---\nartifact_type: "test"\nartifact_schema_version: "1"\n---\n\n' + body


class MarkdownStructureTests(unittest.TestCase):
    def test_valid_table_supports_escaped_and_inline_code_pipes(self) -> None:
        value = document(
            "# Title\n\n## Data\n\n"
            "| Key | Value |\n|---|---|\n"
            "| escaped | alpha\\|beta |\n"
            "| inline | `left|right` |\n"
            "\n```json\n{\"pipe\": \"a|b\"}\n```\n"
        )
        self.assertEqual(parse_markdown(value).issues, ())

    def test_missing_delimiter_and_ragged_rows_are_rejected(self) -> None:
        missing = parse_markdown(document("# Title\n\n| A | B |\n| one | two |\n"))
        self.assertIn("MD-TABLE-DELIMITER", {item.code for item in missing.issues})
        ragged = parse_markdown(
            document("# Title\n\n| A | B |\n|---|---|\n| one | two | three |\n")
        )
        self.assertIn("MD-TABLE-WIDTH", {item.code for item in ragged.issues})

        missing_edge_pipe = parse_markdown(
            document("# Title\n\n| A | B\n|---|---|\n| one | two |\n")
        )
        self.assertEqual(missing_edge_pipe.issues, ())

        gfm_without_edge_pipes = parse_markdown(
            document("# Title\n\nA | B\n--- | ---\none | two\n")
        )
        self.assertEqual(gfm_without_edge_pipes.issues, ())

    def test_unclosed_fence_duplicate_anchor_and_heading_jump_are_rejected(self) -> None:
        parsed = parse_markdown(
            document(
                "# Title\n\n### Jump\n\n<a id=\"same\"></a>\n<a id=\"same\"></a>\n\n```mermaid\ngraph TD\n"
            )
        )
        codes = {item.code for item in parsed.issues}
        self.assertEqual(
            {"MD-HEADING-JUMP", "MD-ANCHOR-DUPLICATE", "MD-FENCE-UNCLOSED"} - codes,
            set(),
        )

    def test_fragment_index_contains_explicit_and_gfm_heading_anchors(self) -> None:
        parsed = parse_markdown(
            document(
                "# API *Guide*\n\n"
                '<a id="stable-entry"></a>\n\n'
                "## `POST /customers` &amp; rules\n\n"
                "## 重复 标题\n\n"
                "## 重复 标题\n"
            )
        )
        self.assertEqual(parsed.issues, ())
        self.assertEqual(
            parsed.fragment_ids,
            {
                "api-guide",
                "stable-entry",
                "post-customers--rules",
                "重复-标题",
                "重复-标题-1",
            },
        )
        self.assertEqual(github_heading_slug("Status: `READY`!"), "status-ready")
        self.assertEqual(github_heading_slug("Shared_rules"), "shared_rules")
        self.assertEqual(github_heading_slug("_Visible_ rule"), "visible-rule")

    def test_explicit_anchor_collision_with_generated_heading_is_rejected(self) -> None:
        parsed = parse_markdown(
            document('<a id="details"></a>\n\n# Details\n')
        )
        self.assertIn("MD-ANCHOR-DUPLICATE", {item.code for item in parsed.issues})

    def test_code_fence_headings_and_anchors_do_not_enter_fragment_index(self) -> None:
        parsed = parse_markdown(
            document(
                "# Visible\n\n"
                "```md\n## Hidden\n<a id=\"hidden\"></a>\n```\n"
            )
        )
        self.assertEqual(parsed.issues, ())
        self.assertEqual(parsed.fragment_ids, {"visible"})

    def test_unsupported_complex_heading_requires_explicit_anchor(self) -> None:
        parsed = parse_markdown(
            document("# [Nested](docs/(preview))\n")
        )
        self.assertEqual(parsed.issues, ())
        self.assertEqual(parsed.fragment_ids, set())

    def test_api_contract_structure_schema_detects_wrong_required_headers(self) -> None:
        value = document(
            "# API\n\n## Quick reference\n\n"
            "| Wrong | Value |\n|---|---|\n| Method | GET |\n\n"
            "## Request\n\nNo caller input.\n\n"
            "## Responses\n\n| HTTP status | When | Body/schema | Relevant headers |\n"
            "|---|---|---|---|\n| 200 | Success | None | None |\n\n"
            "## Related documents\n\n- None\n\n## Source notes\n\nNone.\n"
        )
        structure = parse_markdown(value)
        schema = load_api_contract_structure(SKILL_ROOT / "assets" / "api-contract-structure.json")
        issues = validate_api_contract_tables(structure, schema)
        self.assertIn("API-TABLE-MISSING", {item.code for item in issues})

    def test_contract_validator_stops_after_markdown_root_cause(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            contract = root / "broken.api-contract.md"
            contract.write_text(
                document("# API\n\n| A | B |\n| value | value |\n"),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_api_contract.py"),
                    str(contract),
                    "--repo",
                    str(repo),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("MD-TABLE-DELIMITER", result.stdout)
            self.assertIn("SKIPPED [API-CONTRACT-SEMANTICS]", result.stdout)
            self.assertNotIn("missing YAML keys", result.stdout)

    def test_pack_validator_checks_all_formal_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tech = root / "tech-pack"
            ba = root / "ba-pack"
            tech.mkdir()
            ba.mkdir()
            (tech / "valid.md").write_text(document("# Valid\n"), encoding="utf-8")
            (ba / "invalid.md").write_text(
                document("# Invalid\n\n| A | B |\n| one | two |\n"),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_markdown_structure.py"),
                    str(root),
                    "--json",
                ],
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(payload["checked_documents"], 2)
            self.assertEqual(payload["invalid_documents"], 1)
            self.assertEqual(payload["primary_errors"], 1)
            self.assertEqual(payload["skipped_validation_groups"], 1)
            self.assertIn("MARKDOWN-DOCUMENT:ba-pack/invalid.md", payload["skipped"])


if __name__ == "__main__":
    unittest.main()
