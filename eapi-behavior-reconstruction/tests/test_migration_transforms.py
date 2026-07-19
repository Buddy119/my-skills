from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from migration_transforms import execute_transform, load_transform_registry  # noqa: E402
from register_schema import load_register_schema, validate_register_file  # noqa: E402


class MigrationTransformTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fixture = (
            SKILL_ROOT
            / "tests"
            / "fixtures"
            / "migration"
            / "repository-register-flat-http-1.md"
        )
        self.assets = SKILL_ROOT / "assets"
        self.definition = load_transform_registry().definitions[
            "repository-register-flat-http-1-to-1"
        ]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def transform(self, name: str) -> tuple[Path, dict]:
        root = self.root / name
        register = root / ".work" / "repository-register.md"
        register.parent.mkdir(parents=True)
        shutil.copy2(self.fixture, register)
        report = execute_transform(
            self.definition,
            root,
            [".work/repository-register.md"],
            [".work/repository-register.md"],
            self.assets,
        )
        return register, report

    def test_flat_register_transform_is_deterministic_and_referentially_valid(self) -> None:
        first, first_report = self.transform("first")
        second, second_report = self.transform("second")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(first_report["id_map"], second_report["id_map"])
        self.assertEqual(first_report["output_records"]["http_operations"], 1)
        self.assertEqual(first_report["output_records"]["http_usages"], 1)
        self.assertEqual(first_report["output_records"]["http_mappings"], 2)
        self.assertTrue(validate_register_file(first, load_register_schema()).valid)

    def test_transform_creates_observations_but_no_semantic_reconciliation(self) -> None:
        register, report = self.transform("semantic-boundary")
        text = register.read_text(encoding="utf-8")
        self.assertIn("DEP-OBS-004", text)
        self.assertIn("FO-003", text)
        self.assertGreaterEqual(text.count("Unresolved"), 2)
        self.assertEqual(report["output_records"]["dependency_contracts"], 0)
        self.assertEqual(report["output_records"]["failure_patterns"], 0)
        self.assertNotRegex(text, r"\|\s*DEP-\d+\s*\|")
        self.assertNotRegex(text, r"\|\s*FAIL-\d+\s*\|")

    def test_similar_method_and_target_are_not_a_mechanical_merge_key(self) -> None:
        root = self.root / "no-semantic-merge"
        register = root / ".work" / "repository-register.md"
        register.parent.mkdir(parents=True)
        text = self.fixture.read_text(encoding="utf-8")
        text = text.replace(
            "| HTTP-007 | HTTP-007-U01 |  | POST | customer-system/customers | createCustomer | fixture.create-customer | src/Client.java:42 |",
            "|  |  |  | POST | customer-system/customers | createCustomer | fixture.create-customer | src/Client.java:43 |",
            1,
        )
        register.write_text(text, encoding="utf-8")
        report = execute_transform(
            self.definition,
            root,
            [".work/repository-register.md"],
            [".work/repository-register.md"],
            self.assets,
        )
        self.assertEqual(report["output_records"]["http_operations"], 2)
        self.assertEqual(report["output_records"]["http_usages"], 2)

    def test_missing_ids_reuse_one_exact_structural_call_identity(self) -> None:
        root = self.root / "stable-structural-identity"
        register = root / ".work" / "repository-register.md"
        register.parent.mkdir(parents=True)
        text = self.fixture.read_text(encoding="utf-8")
        text = text.replace("| HTTP-007 | HTTP-007-U01 | FM-009 |", "|  |  |  |", 1)
        text = text.replace("| HTTP-007 | HTTP-007-U01 |  |", "|  |  |  |", 1)
        register.write_text(text, encoding="utf-8")
        report = execute_transform(
            self.definition,
            root,
            [".work/repository-register.md"],
            [".work/repository-register.md"],
            self.assets,
        )
        self.assertEqual(report["output_records"]["http_operations"], 1)
        self.assertEqual(report["output_records"]["http_usages"], 1)
        generated_calls = {
            value for key, value in report["id_map"].items() if key.endswith(":call")
        }
        generated_usages = {
            value for key, value in report["id_map"].items() if key.endswith(":usage")
        }
        self.assertEqual(len(generated_calls), 1)
        self.assertEqual(len(generated_usages), 1)


if __name__ == "__main__":
    unittest.main()
