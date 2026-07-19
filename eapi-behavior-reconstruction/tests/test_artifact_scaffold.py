from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"


def load_module(name: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.pop(0)


class ArtifactScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact_schema = load_module("artifact_schema")
        cls.scaffold = load_module("artifact_scaffold")
        cls.registry = cls.artifact_schema.load_registry()
        cls.schema = cls.scaffold.load_scaffold_schema(cls.registry)

    def test_bundled_schema_matches_registry_templates_and_paths(self) -> None:
        self.assertEqual(self.schema.version, "1")
        self.assertEqual(len(self.schema.definitions), 17)
        self.assertNotIn("analysis-state", self.schema.definitions)
        self.assertNotIn("repository-register", self.schema.definitions)
        self.assertNotIn("artifact-manifest", self.schema.definitions)
        for artifact_type, scaffold in self.schema.definitions.items():
            artifact = self.registry.definitions[artifact_type]
            self.assertIsNotNone(artifact.template)
            self.assertNotEqual(artifact.producing_stage, "finalization")
            self.assertEqual(
                "*" in artifact.paths[0],
                scaffold.path_identity_field is not None,
            )

    def test_render_singleton_uses_registry_identity_without_semantic_generation(self) -> None:
        rendered = self.scaffold.render_artifact(
            self.registry,
            self.schema,
            SKILL_ROOT / "assets",
            "repository-synthesis",
            "customer-eapi",
            "abc123",
            {},
        )
        self.assertEqual(rendered.relative_path, ".work/repository-synthesis.md")
        self.assertIn('artifact_type: "repository-synthesis"', rendered.content)
        self.assertIn(
            f'artifact_schema_version: "{self.registry.definitions["repository-synthesis"].current_version}"',
            rendered.content,
        )
        self.assertIn('repository: "customer-eapi"', rendered.content)
        self.assertIn('source_commit: "abc123"', rendered.content)
        self.assertIn('synthesis_status: "complete|partial|blocked"', rendered.content)
        self.assertIn("Explain what the repository demonstrably does", rendered.content)

    def test_render_api_contract_replaces_only_explicit_identity_tokens(self) -> None:
        identity = {
            "endpoint_id": "customer-eapi.post-customers-id",
            "behavior_id": "customer-eapi.update-customer",
        }
        rendered = self.scaffold.render_artifact(
            self.registry,
            self.schema,
            SKILL_ROOT / "assets",
            "api-contract",
            "customer-eapi",
            "abc123",
            identity,
        )
        self.assertEqual(
            rendered.relative_path,
            "tech-pack/contracts/customer-eapi.post-customers-id.api-contract.md",
        )
        self.assertIn('endpoint_id: "customer-eapi.post-customers-id"', rendered.content)
        self.assertIn('behavior_id: "customer-eapi.update-customer"', rendered.content)
        self.assertIn(
            'behavior_document: "../behaviors/customer-eapi.update-customer.md"',
            rendered.content,
        )
        self.assertIn(
            'endpoint_matrix: "../endpoint-matrix.md#customer-eapi.post-customers-id"',
            rendered.content,
        )
        self.assertIn('method: "GET|POST|PUT|PATCH|DELETE|other"', rendered.content)
        self.assertIn('route: "/normalized/route"', rendered.content)
        self.assertNotIn("repository.method-route", rendered.content)
        self.assertNotIn("repository.behavior-name", rendered.content)

    def test_identity_arguments_reject_duplicate_missing_and_nonportable_values(self) -> None:
        with self.assertRaisesRegex(self.scaffold.ArtifactScaffoldError, "key=value"):
            self.scaffold.parse_identity_arguments(["behavior_id"])
        with self.assertRaisesRegex(self.scaffold.ArtifactScaffoldError, "duplicate"):
            self.scaffold.parse_identity_arguments(
                ["behavior_id=repo.one", "behavior_id=repo.two"]
            )
        for value in ("../escape", "has space", ".", "..", "nested/path"):
            with self.subTest(value=value):
                with self.assertRaises(self.scaffold.ArtifactScaffoldError):
                    self.scaffold.parse_identity_arguments([f"behavior_id={value}"])

    def test_render_rejects_missing_or_unknown_identity(self) -> None:
        with self.assertRaisesRegex(self.scaffold.ArtifactScaffoldError, "missing"):
            self.scaffold.render_artifact(
                self.registry,
                self.schema,
                SKILL_ROOT / "assets",
                "behavior-dossier",
                "repo",
                "unknown",
                {},
            )
        with self.assertRaisesRegex(self.scaffold.ArtifactScaffoldError, "unknown"):
            self.scaffold.render_artifact(
                self.registry,
                self.schema,
                SKILL_ROOT / "assets",
                "repository-synthesis",
                "repo",
                "unknown",
                {"behavior_id": "repo.unexpected"},
            )

    def test_schema_drift_is_rejected(self) -> None:
        source = SKILL_ROOT / "assets" / "artifact-scaffold-schema.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["artifact_types"]["behavior-dossier"]["identity_fields"][
            "behavior_id"
        ] = "missing-template-token"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact-scaffold-schema.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(
                self.scaffold.ArtifactScaffoldError, "lacks identity token"
            ):
                self.scaffold.load_scaffold_schema(
                    self.registry,
                    path=path,
                    assets_root=SKILL_ROOT / "assets",
                )


if __name__ == "__main__":
    unittest.main()
