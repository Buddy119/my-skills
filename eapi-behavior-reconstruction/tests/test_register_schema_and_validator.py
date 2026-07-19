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
            'artifact_type: "repository-register"',
            f'artifact_schema_version: "{self.schema["register_schema_version"]}"',
            'repository: "fixture"',
            'source_commit: "unknown"',
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

    def validate(
        self, validation_profile: str = "complete"
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                str(self.root),
                "--json",
                "--validation-profile",
                validation_profile,
            ],
            capture_output=True,
            text=True,
        )
        self.assertTrue(result.stdout, result.stderr)
        return result, json.loads(result.stdout)

    def write_markdown(self, relative: str, body: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            'artifact_type: "test-reader"\n'
            'artifact_schema_version: "1"\n'
            "---\n\n"
            + body,
            encoding="utf-8",
        )
        return path

    def add_dependency_and_failure_records(self, fixture: RegisterFixture) -> None:
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

    def add_http_records(self, fixture: RegisterFixture) -> None:
        fixture.add(
            "http_operations",
            "HTTP-001",
            "POST",
            "customer-system/profile",
            "updateProfile",
            "send profile update",
            "fixture.behavior",
            "None",
            "Confirmed",
            "source.java:3",
        )
        fixture.add(
            "http_usages",
            "HTTP-001-U01",
            "HTTP-001",
            "fixture.behavior",
            "CustomerClient.updateProfile",
            "always",
            "Confirmed",
            "source.java:3",
        )
        fixture.add(
            "http_mappings",
            "FM-001",
            "HTTP-001",
            "all",
            "eapi-to-external",
            "customerId",
            "customer_id",
            "rename",
            "None",
            "No",
            "Confirmed",
            "source.java:3",
        )

    def write_dependency_document(
        self,
        criticality: str = "Required",
        status: str = "Confirmed",
        boundary_reference: str = "customer table",
    ) -> None:
        qualifier = "" if status == "Confirmed" else f" *({status})*"
        path = self.root / "tech-pack" / "external-dependency-contracts.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nartifact_type: \"external-dependency-contracts\"\n"
            "artifact_schema_version: \"2\"\n---\n\n"
            "# External dependency contracts\n\n"
            "## Dependency landscape\n\n"
            "| Dependency | Type and repository-observed role | Dependent capabilities | Criticality | Availability impact | Details |\n"
            "|---|---|---|---|---|---|\n"
            f"| `DEP-001`{qualifier} | database / state persistence | customer profile | {criticality} | request fails before completion | [Details](#dep-001) |\n\n"
            '<a id="dep-001"></a>\n'
            "## `DEP-001` — Customer store\n\n"
            "| Operation | Boundary reference | Purpose and condition | Concepts sent, consumed, read, or written | Affected capabilities/behaviors |\n"
            "|---|---|---|---|---|\n"
            f"| `DEP-001-OP01` | {boundary_reference} | write customer | customer state | `fixture.behavior` |\n",
            encoding="utf-8",
        )

    def write_field_document(self) -> None:
        path = self.root / "tech-pack" / "field-validation-and-mapping.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nartifact_type: \"field-validation-and-mapping\"\n"
            "artifact_schema_version: \"2\"\n---\n\n"
            "# Field validation and mapping\n\n"
            "## Outbound HTTP operation index\n\n"
            "| Call ID | Method and Logical Target | Client Operation | Observable Purpose | Related Behaviors | Details |\n"
            "|---|---|---|---|---|---|\n"
            "| HTTP-001 | `POST customer-system/profile` | `updateProfile` | send profile update | [Behavior](behaviors/fixture.md) | [Details](#http-001) |\n\n"
            '<a id="http-001"></a>\n'
            "## HTTP-001 — Update customer profile\n\n"
            "### Call overview\n\n"
            "| Method | Logical Target | Client Operation | Observable Purpose | Related Behaviors | Usage Summary |\n"
            "|---|---|---|---|---|---|\n"
            "| POST | customer-system/profile | updateProfile | send profile update | [Behavior](behaviors/fixture.md) | `HTTP-001-U01` — one usage |\n\n"
            "### Request mappings\n\n"
            "| Mapping ID | Applies to Usage(s) | Source Field(s) | Target Field(s) | Transformation | Condition/Default | Lossy |\n"
            "|---|---|---|---|---|---|---|\n"
            "| FM-001 | all | `customerId` | `customer_id` | rename | None | No |\n",
            encoding="utf-8",
        )

    def write_failure_document(
        self,
        caller_visibility: str = "Explicit error",
        state_outcome: str = "Unchanged",
        retry_safety: str = "Safe",
        risk_attention: str = "Low",
    ) -> None:
        path = self.root / "tech-pack" / "failure-taxonomy.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\nartifact_type: \"failure-taxonomy\"\n"
            "artifact_schema_version: \"1\"\n---\n\n"
            "# Failure taxonomy\n\n"
            "## Failure pattern index\n\n"
            "| Failure pattern | Category | Affected capabilities | Caller visibility | State outcome | Retry safety | Risk attention | Details |\n"
            "|---|---|---|---|---|---|---|---|\n"
            f"| `FAIL-001` | data | customer profile | {caller_visibility} | {state_outcome} | {retry_safety} | {risk_attention} | [Details](#fail-001) |\n\n"
            '<a id="fail-001"></a>\n'
            "## `FAIL-001` — Write failure\n\n"
            "The write fails before state changes.\n",
            encoding="utf-8",
        )

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
            {
                "dependency": "valid",
                "failure": "valid",
                "http": "valid",
                "lifecycle": "valid",
                "markdown-fragment": "valid",
            },
        )

    def test_reader_catalog_template_instruction_is_rejected(self) -> None:
        RegisterFixture(self.root).write()
        catalog = self.root / "tech-pack" / "behavior-catalog.yaml"
        catalog.parent.mkdir(parents=True)
        catalog.write_text(
            'repository: "fixture"\n# TEMPLATE: remove this publication instruction\nbehaviors: []\n',
            encoding="utf-8",
        )
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("CATALOG-DOCUMENT", payload["errors"])
        self.assertEqual(payload["primary_errors"], 1)

    def test_tech_profile_defers_only_future_api_and_ba_targets(self) -> None:
        RegisterFixture(self.root).write()
        reader = self.root / "tech-pack" / "behaviors" / "fixture.md"
        reader.parent.mkdir(parents=True)
        reader.write_text(
            "# Fixture behavior\n\n"
            "[Contract](../contracts/fixture.get-customer.api-contract.md)\n\n"
            "[Endpoint matrix](../endpoint-matrix.md)\n\n"
            "[BA scenario](../../ba-pack/scenarios/fixture.scenario.customer.md)\n",
            encoding="utf-8",
        )

        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["validation_profile"], "tech-publication")
        self.assertEqual(
            payload["deferred_checks"],
            ["api-materialization", "ba-traceability"],
        )
        self.assertEqual(payload["deferred_link_count"], 3)
        self.assertEqual(payload["deferred_links_suppressed"], 0)
        self.assertEqual(
            {item["check"] for item in payload["deferred_links"]},
            {"api-materialization", "ba-traceability"},
        )
        self.assertTrue(
            all(item["source"] == "tech-pack/behaviors/fixture.md" for item in payload["deferred_links"])
        )
        self.assertEqual(payload["primary_errors"], 0)
        self.assertEqual(payload["skipped_validation_groups"], 0)

        complete_result, complete_payload = self.validate()
        self.assertEqual(complete_result.returncode, 1)
        self.assertEqual(complete_payload["validation_profile"], "complete")
        self.assertEqual(complete_payload["deferred_checks"], [])
        self.assertEqual(complete_payload["deferred_link_count"], 0)
        self.assertIn("MARKDOWN-LINK", complete_payload["errors"])

    def test_tech_profile_keeps_ordinary_missing_and_escaping_links_strict(self) -> None:
        RegisterFixture(self.root).write()
        reader = self.root / "tech-pack" / "reader.md"
        reader.parent.mkdir(parents=True)
        reader.write_text(
            "# Reader\n\n"
            "[Missing Tech detail](missing-tech-detail.md)\n\n"
            "[Escaping link](../../outside.md)\n",
            encoding="utf-8",
        )
        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 1)
        errors = payload["errors"]["MARKDOWN-LINK"]
        self.assertTrue(any("broken local link" in message for message in errors))
        self.assertTrue(any("escapes pack root" in message for message in errors))

    def test_local_fragments_resolve_explicit_heading_duplicate_and_encoded_targets(self) -> None:
        RegisterFixture(self.root).write()
        self.write_markdown(
            "tech-pack/target.md",
            "# Target\n\n"
            '<a id="stable-entry"></a>\n\n'
            "## Protocol support summary\n\n"
            "## 重复 标题\n\n"
            "## 重复 标题\n",
        )
        self.write_markdown(
            "tech-pack/source.md",
            "# Source\n\n"
            "## Local section\n\n"
            "[same](#local-section)\n"
            "[explicit](target.md#stable-entry)\n"
            "[heading](target.md?view=reader#protocol-support-summary)\n"
            "[duplicate](target.md#%E9%87%8D%E5%A4%8D-%E6%A0%87%E9%A2%98-1)\n",
        )
        result, payload = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["markdown_fragment_validation_version"], "1")
        self.assertEqual(payload["checked_fragments"], 4)
        self.assertEqual(payload["fragment_target_documents"], 2)
        self.assertEqual(payload["fragment_error_count"], 0)
        self.assertEqual(payload["fragment_skipped_group_count"], 0)

    def test_existing_file_with_missing_fragment_is_rejected_at_source_line(self) -> None:
        RegisterFixture(self.root).write()
        self.write_markdown("tech-pack/target.md", "# Target\n")
        self.write_markdown(
            "tech-pack/source.md",
            "# Source\n\n[Broken](target.md#missing-section)\n",
        )
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["fragment_error_count"], 1)
        errors = payload["errors"]["MARKDOWN-FRAGMENT"]
        self.assertEqual(len(errors), 1)
        self.assertIn("tech-pack/source.md:8", errors[0])
        self.assertIn("target.md#missing-section", errors[0])

    def test_invalid_fragment_target_suppresses_incoming_error_cascade(self) -> None:
        RegisterFixture(self.root).write()
        target = self.root / "tech-pack" / "invalid.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# No frontmatter\n", encoding="utf-8")
        links = "\n".join(
            f"[Link {index}](invalid.md#missing-{index})" for index in range(25)
        )
        self.write_markdown("tech-pack/source.md", f"# Source\n\n{links}\n")
        result, payload = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("MARKDOWN-FRAGMENT", payload["errors"])
        self.assertEqual(payload["fragment_error_count"], 0)
        self.assertEqual(payload["fragment_skipped_group_count"], 1)
        self.assertIn("MARKDOWN-FRAGMENT:tech-pack/invalid.md", payload["skipped"])

    def test_non_markdown_fragment_warns_and_external_fragment_is_ignored(self) -> None:
        RegisterFixture(self.root).write()
        data = self.root / "tech-pack" / "data.json"
        data.parent.mkdir(parents=True, exist_ok=True)
        data.write_text("{}\n", encoding="utf-8")
        self.write_markdown(
            "tech-pack/source.md",
            "# Source\n\n"
            "[Local data](data.json#value)\n"
            "[External](https://example.test/docs#value)\n",
        )
        result, payload = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["checked_fragments"], 0)
        self.assertEqual(payload["warnings"], 1)
        self.assertIn("MARKDOWN-FRAGMENT-UNVERIFIED", payload["warning_messages"][0])

    def test_links_inside_fenced_and_inline_code_are_not_validated(self) -> None:
        RegisterFixture(self.root).write()
        self.write_markdown(
            "tech-pack/source.md",
            "# Source\n\n"
            "```md\n[Example](missing.md#missing)\n```\n\n"
            "`[Inline example](also-missing.md#missing)`\n",
        )
        result, payload = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["checked_links"], 0)
        self.assertEqual(payload["checked_fragments"], 0)

    def test_tech_profile_defers_fragment_until_contract_is_materialized(self) -> None:
        RegisterFixture(self.root).write()
        self.write_markdown(
            "tech-pack/behaviors/fixture.md",
            "# Fixture\n\n"
            "[Contract](../contracts/fixture.get.api-contract.md#quick-reference)\n",
        )
        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["deferred_link_count"], 1)
        self.assertEqual(payload["checked_fragments"], 0)

        self.write_markdown(
            "tech-pack/contracts/fixture.get.api-contract.md",
            "# Contract\n\n## Request\n",
        )
        materialized, materialized_payload = self.validate("tech-publication")
        self.assertEqual(materialized.returncode, 1)
        self.assertIn("MARKDOWN-FRAGMENT", materialized_payload["errors"])

    def test_tech_profile_accepts_reader_models_with_contract_deferred(self) -> None:
        fixture = RegisterFixture(self.root)
        self.add_http_records(fixture)
        self.add_dependency_and_failure_records(fixture)
        fixture.rows["dependency_operations"][0][2] = "HTTP-001"
        fixture.write()
        self.write_field_document()
        self.write_dependency_document(
            boundary_reference="[HTTP-001](field-validation-and-mapping.md#http-001)"
        )
        self.write_failure_document()
        behavior = self.root / "tech-pack" / "behaviors" / "fixture.md"
        behavior.parent.mkdir(parents=True, exist_ok=True)
        behavior.write_text(
            "---\n"
            'behavior_id: "fixture.behavior"\n'
            "external_http_calls:\n"
            "  - call_id: HTTP-001\n"
            "external_dependencies:\n"
            "  - dependency_id: DEP-001\n"
            "failure_patterns:\n"
            "  - pattern_id: FAIL-001\n"
            "---\n\n"
            "# Fixture behavior\n\n"
            "[Contract](../contracts/fixture.post-profile.api-contract.md)\n\n"
            "[HTTP](../field-validation-and-mapping.md#http-001)\n\n"
            "[Dependency](../external-dependency-contracts.md#dep-001)\n\n"
            "[Failure](../failure-taxonomy.md#fail-001)\n",
            encoding="utf-8",
        )

        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["primary_errors"], 0)
        self.assertEqual(payload["skipped_validation_groups"], 0)
        self.assertEqual(payload["deferred_link_count"], 1)
        self.assertEqual(
            payload["domain_statuses"],
            {
                "dependency": "valid",
                "failure": "valid",
                "http": "valid",
                "lifecycle": "valid",
                "markdown-fragment": "valid",
            },
        )

    def test_tech_profile_rejects_dependency_reader_enum_error(self) -> None:
        fixture = RegisterFixture(self.root)
        self.add_dependency_and_failure_records(fixture)
        fixture.write()
        self.write_failure_document()
        for kwargs, expected in (
            ({"criticality": "Mandatory"}, "Criticality"),
            ({"status": "Inferred"}, "Confirmed"),
        ):
            with self.subTest(expected=expected):
                self.write_dependency_document(**kwargs)
                result, payload = self.validate("tech-publication")
                self.assertEqual(result.returncode, 1)
                self.assertIn("DEP-DOCUMENT", payload["errors"])
                self.assertTrue(
                    any(
                        expected in message
                        for message in payload["errors"]["DEP-DOCUMENT"]
                    )
                )
                self.assertNotIn("FAIL-DOCUMENT", payload["errors"])

    def test_http_and_dependency_non_confirmed_status_requires_reader_qualifier(self) -> None:
        fixture = RegisterFixture(self.root)
        self.add_http_records(fixture)
        self.add_dependency_and_failure_records(fixture)
        fixture.rows["http_operations"][0][7] = "Unknown"
        fixture.rows["dependency_contracts"][0][9] = "Inferred"
        fixture.write()
        self.write_field_document()
        self.write_dependency_document()
        self.write_failure_document()

        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any("*(Unknown)*" in item for item in payload["errors"]["HTTP-DOCUMENT"])
        )
        self.assertTrue(
            any("*(Inferred)*" in item for item in payload["errors"]["DEP-DOCUMENT"])
        )

        field = self.root / "tech-pack" / "field-validation-and-mapping.md"
        field.write_text(
            field.read_text(encoding="utf-8").replace(
                "| HTTP-001 |", "| HTTP-001 *(Unknown)* |", 1
            ),
            encoding="utf-8",
        )
        self.write_dependency_document(status="Inferred")
        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("HTTP-DOCUMENT", payload["errors"])
        self.assertNotIn("DEP-DOCUMENT", payload["errors"])

    def test_tech_profile_rejects_failure_reader_enum_error(self) -> None:
        fixture = RegisterFixture(self.root)
        self.add_dependency_and_failure_records(fixture)
        fixture.write()
        self.write_dependency_document()
        for kwargs, expected in (
            ({"caller_visibility": "Hidden"}, "Caller visibility"),
            ({"state_outcome": "Maybe changed"}, "State outcome"),
            ({"retry_safety": "Probably safe"}, "Retry safety"),
            ({"risk_attention": "Severe"}, "Risk attention"),
        ):
            with self.subTest(expected=expected):
                self.write_failure_document(**kwargs)
                result, payload = self.validate("tech-publication")
                self.assertEqual(result.returncode, 1)
                self.assertIn("FAIL-DOCUMENT", payload["errors"])
                self.assertTrue(
                    any(
                        expected in message
                        for message in payload["errors"]["FAIL-DOCUMENT"]
                    )
                )
                self.assertNotIn("DEP-DOCUMENT", payload["errors"])

    def test_tech_profile_rejects_dependency_reference_to_unknown_http_call(self) -> None:
        fixture = RegisterFixture(self.root)
        self.add_dependency_and_failure_records(fixture)
        fixture.rows["dependency_operations"][0][2] = "HTTP-999"
        fixture.write()
        self.write_dependency_document()
        self.write_failure_document()

        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 1)
        self.assertIn("REG-DEP-ROW", payload["errors"])
        self.assertTrue(
            any(
                "unknown outbound Call ID: HTTP-999" in message
                for message in payload["errors"]["REG-DEP-ROW"]
            )
        )

    def test_tech_profile_rejects_unknown_behavior_repository_backlinks(self) -> None:
        fixture = RegisterFixture(self.root)
        self.add_dependency_and_failure_records(fixture)
        fixture.write()
        self.write_dependency_document()
        self.write_failure_document()
        behavior = self.root / "tech-pack" / "behaviors" / "fixture.md"
        behavior.parent.mkdir(parents=True)
        behavior.write_text(
            "---\n"
            'behavior_id: "fixture.behavior"\n'
            "external_http_calls:\n"
            "  - call_id: HTTP-999\n"
            "external_dependencies:\n"
            "  - dependency_id: DEP-999\n"
            "failure_patterns:\n"
            "  - pattern_id: FAIL-999\n"
            "---\n\n"
            "# Fixture behavior\n\n"
            "[HTTP](../field-validation-and-mapping.md#http-999)\n\n"
            "[Dependency](../external-dependency-contracts.md#dep-999)\n\n"
            "[Failure](../failure-taxonomy.md#fail-999)\n",
            encoding="utf-8",
        )

        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 1)
        self.assertIn("BEHAVIOR-HTTP-BACKLINK", payload["errors"])
        self.assertIn("BEHAVIOR-REPOSITORY-BACKLINK", payload["errors"])
        repository_errors = payload["errors"]["BEHAVIOR-REPOSITORY-BACKLINK"]
        self.assertTrue(any("unknown Dependency" in message for message in repository_errors))
        self.assertTrue(
            any("unknown Failure Pattern" in message for message in repository_errors)
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
        result, payload = self.validate("tech-publication")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(payload["errors"]), ["REG-FAIL-SCHEMA"])
        self.assertEqual(payload["validation_profile"], "tech-publication")
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
