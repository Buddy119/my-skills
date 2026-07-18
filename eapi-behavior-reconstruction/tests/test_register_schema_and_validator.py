from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "assets" / "register-schema.json"
TEMPLATE_PATH = SKILL_ROOT / "assets" / "repository-register-template.md"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_pack_links.py"
EXECUTOR = SKILL_ROOT / "scripts" / "stage_executor.py"


class RegisterFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.rows: dict[str, list[list[str]]] = {
            key: [] for key in self.schema["tables"]
        }

    def add(self, table: str, *cells: str) -> None:
        self.rows[table].append(list(cells))

    def write(self, header_override: dict[str, list[str]] | None = None) -> Path:
        header_override = header_override or {}
        parts = [
            "---",
            'repository: "fixture"',
            'source_commit: "unknown"',
            'register_schema_version: "1"',
            'register_status: "reconciled"',
            "---",
            "",
            "# Repository working register",
        ]
        for key, table in self.schema["tables"].items():
            headers = header_override.get(key, table["headers"])
            parts.extend(
                [
                    "",
                    f"## {table['section']}",
                    "",
                    "| " + " | ".join(headers) + " |",
                    "|" + "|".join("---" for _ in headers) + "|",
                ]
            )
            for row in self.rows[key]:
                parts.append("| " + " | ".join(row) + " |")
        path = self.root / ".work" / "repository-register.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(parts) + "\n", encoding="utf-8")
        return path


class RegisterSchemaAndValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "pack"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.root), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertTrue(result.stdout, result.stderr)
        return result, json.loads(result.stdout)

    def test_template_and_schema_are_exactly_synchronized(self) -> None:
        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        try:
            from register_schema import validate_bundled_contract

            result = validate_bundled_contract(TEMPLATE_PATH)
        finally:
            sys.path.pop(0)
        self.assertTrue(result.valid, (result.errors, result.domain_errors))

    def test_empty_current_schema_fixture_passes_without_skips(self) -> None:
        RegisterFixture(self.root).write()
        result, payload = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["primary_errors"], 0)
        self.assertEqual(payload["skipped_validation_groups"], 0)
        self.assertEqual(
            payload["domain_statuses"],
            {"dependency": "valid", "failure": "valid", "http": "valid"},
        )

    def test_dependency_header_error_is_one_root_without_cascade(self) -> None:
        fixture = RegisterFixture(self.root)
        bad_headers = fixture.schema["tables"]["dependency_contracts"]["headers"][:-1]
        fixture.write({"dependency_contracts": bad_headers})
        behaviors = self.root / "tech-pack" / "behaviors"
        behaviors.mkdir(parents=True)
        for index in range(300):
            (behaviors / f"b-{index}.md").write_text(
                "---\n"
                f'behavior_id: "fixture.b-{index}"\n'
                "external_dependencies:\n"
                "  - dependency_id: DEP-999\n"
                "failure_patterns: []\n"
                "---\n\n"
                "Behavior body.\n",
                encoding="utf-8",
            )
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(payload["errors"]), ["REG-DEP-SCHEMA"])
        self.assertEqual(len(payload["errors"]["REG-DEP-SCHEMA"]), 1)
        rendered = result.stdout.lower()
        self.assertNotIn("unknown dependency", rendered)
        self.assertNotIn("broken backlink", rendered)
        self.assertEqual(payload["domain_statuses"]["dependency"], "invalid")
        self.assertEqual(payload["domain_statuses"]["http"], "valid")
        self.assertEqual(payload["domain_statuses"]["failure"], "valid")
        self.assertLess(len(result.stdout.splitlines()), 90)

    def test_failure_header_error_skips_taxonomy_and_backlinks(self) -> None:
        fixture = RegisterFixture(self.root)
        bad_headers = fixture.schema["tables"]["failure_patterns"]["headers"][:-1]
        fixture.write({"failure_patterns": bad_headers})
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(payload["errors"]), ["REG-FAIL-SCHEMA"])
        self.assertEqual(payload["domain_statuses"]["failure"], "invalid")
        self.assertIn("FAIL-DOCUMENT", payload["skipped"])
        self.assertIn("BEHAVIOR-FAIL-BACKLINK", payload["skipped"])

    def test_dependency_invalid_does_not_stop_unrelated_link_check(self) -> None:
        fixture = RegisterFixture(self.root)
        bad_headers = fixture.schema["tables"]["dependency_contracts"]["headers"][:-1]
        fixture.write({"dependency_contracts": bad_headers})
        (self.root / "reader.md").write_text("[missing](missing.md)\n", encoding="utf-8")
        _result, payload = self.validate()
        self.assertIn("REG-DEP-SCHEMA", payload["errors"])
        self.assertIn("MARKDOWN-LINK", payload["errors"])
        self.assertEqual(payload["domain_statuses"]["http"], "valid")

    def test_true_unknown_dependency_is_reported_when_indexes_are_valid(self) -> None:
        fixture = RegisterFixture(self.root)
        fixture.add(
            "failure_observations",
            "FO-001",
            "dependency",
            "fixture.behavior",
            "downstream rejection",
            "propagate",
            "Explicit error",
            "Unchanged",
            "None observed",
            "Confirmed",
            "source.java:1",
            "FAIL-001",
        )
        fixture.add(
            "failure_patterns",
            "FAIL-001",
            "dependency",
            "downstream rejection",
            "FO-001",
            "fixture.behavior",
            "DEP-999",
            "Explicit error",
            "Unchanged",
            "Safe",
            "None observed",
            "Low",
            "None observed",
            "source.java:1",
        )
        fixture.write()
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        messages = payload["errors"]["REG-FAIL-ROW"]
        self.assertTrue(any("unknown Dependency: DEP-999" in message for message in messages))
        self.assertNotIn("FAIL-DEP-XREF", payload["skipped"])

    def test_latest_dependency_and_failure_tables_parse_as_trusted_domains(self) -> None:
        fixture = RegisterFixture(self.root)
        fixture.add(
            "dependency_observations",
            "DEP-OBS-001",
            "customer system",
            "database",
            "fixture.behavior",
            "customer table",
            "customer state",
            "Unknown",
            "Confirmed",
            "source.java:1",
            "DEP-001",
        )
        fixture.add(
            "dependency_contracts",
            "DEP-001",
            "customer store",
            "database",
            "state persistence",
            "DEP-001-OP01",
            "fixture.behavior",
            "fixture.behavior: Required",
            "DEP-OBS-001",
            "None",
            "Confirmed",
            "None observed",
        )
        fixture.add(
            "dependency_operations",
            "DEP-001-OP01",
            "DEP-001",
            "customer table",
            "write customer",
            "customer state",
            "fixture.behavior",
            "fixture.behavior: Required",
            "request fails before completion",
            "Confirmed",
            "source.java:1",
        )
        fixture.add(
            "failure_observations",
            "FO-001",
            "data",
            "fixture.behavior",
            "write failure",
            "propagate",
            "Explicit error",
            "Unchanged",
            "None observed",
            "Confirmed",
            "source.java:2",
            "FAIL-001",
        )
        fixture.add(
            "failure_patterns",
            "FAIL-001",
            "data",
            "write failure",
            "FO-001",
            "fixture.behavior",
            "DEP-001",
            "Explicit error",
            "Unchanged",
            "Safe",
            "None observed",
            "Low",
            "None observed",
            "source.java:2",
        )
        fixture.write()
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["domain_statuses"]["dependency"], "valid")
        self.assertEqual(payload["domain_statuses"]["failure"], "valid")
        self.assertNotIn("REG-DEP-ROW", payload["errors"])
        self.assertNotIn("REG-FAIL-ROW", payload["errors"])
        self.assertNotIn("FAIL-DEP-XREF", payload["skipped"])
        self.assertIn("DEP-DOCUMENT", payload["errors"])
        self.assertIn("FAIL-DOCUMENT", payload["errors"])

    def test_row_error_budget_shows_ten_and_suppresses_the_rest(self) -> None:
        fixture = RegisterFixture(self.root)
        for index in range(25):
            fixture.add(
                "dependency_operations",
                f"BAD-{index}",
                "DEP-001",
                "resource",
                "invoke",
                "concept",
                "fixture.behavior",
                "fixture.behavior: Required",
                "Unknown",
                "Confirmed",
                "source.java:1",
            )
        fixture.write()
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["primary_errors"], 25)
        self.assertEqual(len(payload["errors"]["REG-DEP-ROW"]), 10)
        self.assertEqual(payload["suppressed_by_group"]["REG-DEP-ROW"], 15)
        self.assertEqual(payload["domain_statuses"]["dependency"], "partial")

    def test_init_rejects_schema_template_drift_before_creating_output(self) -> None:
        copied = Path(self.temporary.name) / "skill-copy"
        shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        template = copied / "assets" / "repository-register-template.md"
        template.write_text(
            template.read_text(encoding="utf-8").replace(
                "| Dependency ID | Logical identity |",
                "| Dependency Identifier | Logical identity |",
                1,
            ),
            encoding="utf-8",
        )
        repo = Path(self.temporary.name) / "repo"
        output = Path(self.temporary.name) / "output"
        repo.mkdir()
        result = subprocess.run(
            [
                sys.executable,
                str(copied / "scripts" / "stage_executor.py"),
                "init",
                "--repo",
                str(repo),
                "--output",
                str(output),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("out of sync", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
