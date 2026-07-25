from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "reader_projection.py"


def load_module():
    sys.path.insert(0, str(MODULE_PATH.parent))
    specification = importlib.util.spec_from_file_location("reader_projection", MODULE_PATH)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    try:
        sys.modules[specification.name] = module
        specification.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(specification.name, None)
        sys.path.pop(0)


def behavior_document(*, include_ba: bool = False) -> str:
    ba = (
        "ba_scenarios:\n"
        '  - scenario_id: "repo.scenario.complete"\n'
        '    document: "../../ba-pack/scenarios/repo.scenario.complete.md"\n'
        if include_ba
        else "ba_scenarios: []\n"
    )
    ba_section = (
        "### BA scenarios\n\n"
        "- [Complete request](../../ba-pack/scenarios/repo.scenario.complete.md)\n\n"
        if include_ba
        else ""
    )
    return (
        "---\n"
        'artifact_type: "tech-behavior"\n'
        'artifact_schema_version: "5"\n'
        'behavior_id: "repo.behavior"\n'
        'title: "Behavior"\n'
        'repository: "repo"\n'
        'source_commit: "abc"\n'
        'entry_type: "api"\n'
        "api_contracts:\n"
        '  - endpoint_id: "repo.get-items"\n'
        '    document: "../contracts/repo.get-items.api-contract.md"\n'
        + ba
        + "failure_patterns: []\n"
        + "java_bindings: []\n"
        + "runtime_config_impacts: []\n"
        "---\n\n"
        "# Behavior\n\n"
        "## Summary\n\nHandles an item request.\n\n"
        "## Main path\n\n1. Accept the request.\n2. Return the result.\n\n"
        "## Behavior flow\n\n```mermaid\nflowchart LR\n A --> B\n```\n\n"
        "## Implementation sequence\n\n"
        "```mermaid\nsequenceDiagram\n"
        "    participant Caller\n"
        "    participant Entry\n"
        "    Caller->>Entry: Request item\n"
        "    Entry-->>Caller: Item result\n"
        "```\n\n"
        "## Exception and failure handling\n\n"
        "No distinct exception path was observed in this projection fixture.\n\n"
        "## Related documents\n\n"
        "### API contracts\n\n"
        "- [Old label](../contracts/repo.get-items.api-contract.md)\n\n"
        + ba_section
        + "## Source notes\n\nNo source note is required by this projection fixture.\n"
    )


def catalog_document(*, include_ba: bool = False) -> str:
    ba = (
        "    ba_scenarios:\n"
        '      - scenario_id: "repo.scenario.complete"\n'
        '        document: "../ba-pack/scenarios/repo.scenario.complete.md"\n'
        if include_ba
        else "    ba_scenarios: []\n"
    )
    return (
        'artifact_type: "tech-behavior-catalog"\n'
        'artifact_schema_version: "1"\n'
        'repository: "repo"\n'
        'source_commit: "abc"\n'
        'analysis_mode: "automatic"\n'
        "behaviors:\n"
        '  - behavior_id: "repo.behavior"\n'
        '    title: "Behavior"\n'
        '    document: "behaviors/repo.behavior.md"\n'
        + ba
        + "    api_contracts: []\n"
    )


def overview_document() -> str:
    return (
        "---\n"
        'artifact_type: "repository-overview"\n'
        'artifact_schema_version: "3"\n'
        'repository: "repo"\n'
        'source_commit: "abc"\n'
        "---\n\n"
        "# Repository overview\n\n"
        "## Repository in 5 minutes\n\nThe repository handles item requests.\n\n"
        "## Capability paths\n\n### Retrieve item\n\nThe caller requests an item and receives the result.\n\n"
        "## Behavior variants\n\nNo material variant was observed.\n\n"
        "## Risk hotspots\n\nNo high-attention risk was observed.\n\n"
        "## System context and shared behavior\n\nThe API caller is the observable upstream.\n\n"
        "## Technical reference\n\n"
        "### Endpoint exposure summary\n\n"
        "| Category | Count | Interpretation | Details |\n"
        "|---|---|---|---|\n"
        "| Application endpoints | 99 | Routes | [Matrix](endpoint-matrix.md) |\n"
        "| Meaningful external exposures | 99 | Exposures | [Matrix](endpoint-matrix.md) |\n"
        "| Aggregated protocol-support declarations | 0 | Support | Not observed |\n"
        "| Unresolved or conflicting exceptions | 99 | Exceptions | [Matrix](endpoint-matrix.md) |\n\n"
        "### Knowledge pack index\n\n"
        "| Knowledge area | Document | Availability | What it explains |\n"
        "|---|---|---|---|\n"
        "| Endpoints | [Endpoint matrix](endpoint-matrix.md) | Not observed | Routes |\n\n"
        "## Coverage and unknowns\n\nRuntime deployment was not observed.\n\n"
        "## Source notes\n\nNo source note is required by this projection fixture.\n"
    )


class ReaderProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "candidate"
        self.tx = Path(self.temporary.name) / "transaction"
        (self.root / "tech-pack" / "behaviors").mkdir(parents=True)
        (self.root / "tech-pack" / "contracts").mkdir(parents=True)
        (self.root / ".work").mkdir(parents=True)
        self.tx.mkdir()
        (self.root / ".work" / "analysis-state.yaml").write_text(
            'business_model_status: "complete"\n', encoding="utf-8"
        )
        (self.root / "tech-pack" / "behaviors" / "repo.behavior.md").write_text(
            behavior_document(), encoding="utf-8"
        )
        (self.root / "tech-pack" / "behavior-catalog.yaml").write_text(
            catalog_document(), encoding="utf-8"
        )
        (self.root / "tech-pack" / "repository-overview.md").write_text(
            overview_document(), encoding="utf-8"
        )
        (self.root / "tech-pack" / "contracts" / "repo.get-items.api-contract.md").write_text(
            "---\n"
            'artifact_type: "api-contract"\n'
            'artifact_schema_version: "3"\n'
            'endpoint_id: "repo.get-items"\n'
            'behavior_id: "repo.behavior"\n'
            'title: "Get items"\n'
            'method: "GET"\n'
            'route: "/items"\n'
            'contract_status: "Confirmed"\n'
            "---\n\n# Get items\n\n"
            "## Related documents\n\n"
            "- [Implementation sequence]"
            "(../behaviors/repo.behavior.md#implementation-sequence)\n",
            encoding="utf-8",
        )
        (self.root / "tech-pack" / "endpoint-matrix.md").write_text(
            "# Endpoint matrix\n\n"
            "## Endpoint summary\n\n"
            "| Endpoint or Exposure ID | Operation Role | Contract |\n"
            "|---|---|---|\n"
            "| `repo.get-items` | application-endpoint | [Contract](contracts/repo.get-items.api-contract.md) |\n",
            encoding="utf-8",
        )
        (self.root / "tech-pack" / "field-validation-and-mapping.md").write_text(
            "# Field validation and mapping\n\n"
            "## API contract index\n\n"
            "| Endpoint | Contract |\n|---|---|\n"
            "| `GET /items` | [Contract](contracts/repo.get-items.api-contract.md) |\n",
            encoding="utf-8",
        )
        self.module = load_module()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def mark_all(self, plan: dict) -> None:
        for item in plan["semantic_items"]:
            self.module.mark_projection(
                root=self.root,
                transaction_dir=self.tx,
                transaction_id="tx-1",
                projection_id=item["projection_id"],
                status="reviewed-no-change",
                reason="The semantic summary already describes the materialized relationship.",
            )

    def test_api_projection_refreshes_navigation_and_requires_semantic_review(self) -> None:
        plan = self.module.refresh_projections(
            root=self.root,
            transaction_dir=self.tx,
            transaction_id="tx-1",
            stage="api-contract-publication",
            repository="repo",
            source_commit="abc",
        )
        self.assertEqual(plan["status"], "in-progress")
        catalog = (self.root / "tech-pack" / "behavior-catalog.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn('endpoint_id: "repo.get-items"', catalog)
        behavior = (self.root / "tech-pack" / "behaviors" / "repo.behavior.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "[Implementation sequence]"
            "(../behaviors/repo.behavior.md#implementation-sequence)",
            (
                self.root
                / "tech-pack"
                / "contracts"
                / "repo.get-items.api-contract.md"
            ).read_text(encoding="utf-8"),
        )
        overview = (self.root / "tech-pack" / "repository-overview.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("| Application endpoints | 1 |", overview)
        self.assertNotIn("contracts/repo.get-items.api-contract.md", overview)
        self.assertTrue(
            any(item["path"] == "tech-pack/repository-overview.md" for item in plan["semantic_items"])
        )

        pending = self.module.evaluate_projection(
            root=self.root,
            transaction_dir=self.tx,
            transaction_id="tx-1",
            stage="api-contract-publication",
            repository="repo",
            source_commit="abc",
        )
        self.assertEqual(pending["statuses"]["api"], "stale")
        self.assertGreater(pending["pending_count"], 0)
        with self.assertRaises(self.module.ReaderProjectionError):
            self.module.mark_projection(
                root=self.root,
                transaction_dir=self.tx,
                transaction_id="tx-1",
                projection_id=plan["semantic_items"][0]["projection_id"],
                status="reviewed-no-change",
                reason=None,
            )

        self.mark_all(plan)
        current = self.module.evaluate_projection(
            root=self.root,
            transaction_dir=self.tx,
            transaction_id="tx-1",
            stage="api-contract-publication",
            repository="repo",
            source_commit="abc",
        )
        self.assertEqual(current["statuses"], {"api": "current", "ba": "deferred"})
        self.assertEqual(current["pending_count"], 0)

        contract = self.root / "tech-pack" / "contracts" / "repo.get-items.api-contract.md"
        contract.write_text(
            contract.read_text(encoding="utf-8").replace('route: "/items"', 'route: "/items/v2"'),
            encoding="utf-8",
        )
        stale = self.module.evaluate_projection(
            root=self.root,
            transaction_dir=self.tx,
            transaction_id="tx-1",
            stage="api-contract-publication",
            repository="repo",
            source_commit="abc",
        )
        self.assertEqual(stale["statuses"]["api"], "stale")
        self.assertGreater(stale["stale_count"], 0)

    def test_relationship_conflict_is_recorded_without_reader_mutation(self) -> None:
        behavior = self.root / "tech-pack" / "behaviors" / "repo.behavior.md"
        behavior.write_text(
            behavior.read_text(encoding="utf-8").replace(
                'endpoint_id: "repo.get-items"', 'endpoint_id: "repo.other"'
            ),
            encoding="utf-8",
        )
        before = {
            path: path.read_bytes()
            for path in (
                behavior,
                self.root / "tech-pack" / "behavior-catalog.yaml",
                self.root / "tech-pack" / "repository-overview.md",
            )
        }
        plan = self.module.refresh_projections(
            root=self.root,
            transaction_dir=self.tx,
            transaction_id="tx-1",
            stage="api-contract-publication",
            repository="repo",
            source_commit="abc",
        )
        self.assertEqual(plan["status"], "invalid")
        self.assertTrue(plan["relationship_errors"])
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_ba_projection_creates_reverse_navigation(self) -> None:
        (self.root / "ba-pack" / "scenarios").mkdir(parents=True)
        (self.root / "ba-pack" / "journeys").mkdir(parents=True)
        (self.root / "ba-pack" / "scenarios" / "repo.scenario.complete.md").write_text(
            "---\n"
            'scenario_id: "repo.scenario.complete"\n'
            'title: "Complete request"\n'
            "journeys:\n"
            '  - journey_id: "repo.journey.items"\n'
            '    document: "../journeys/repo.journey.items.md"\n'
            "tech_behaviors:\n"
            '  - behavior_id: "repo.behavior"\n'
            '    document: "../../tech-pack/behaviors/repo.behavior.md"\n'
            "---\n\n# Complete request\n",
            encoding="utf-8",
        )
        (self.root / "ba-pack" / "journeys" / "repo.journey.items.md").write_text(
            "---\n"
            'journey_id: "repo.journey.items"\n'
            'title: "Manage items"\n'
            "scenarios:\n"
            '  - scenario_id: "repo.scenario.complete"\n'
            '    document: "../scenarios/repo.scenario.complete.md"\n'
            "supporting_tech_behaviors:\n"
            '  - behavior_id: "repo.behavior"\n'
            '    document: "../../tech-pack/behaviors/repo.behavior.md"\n'
            "---\n\n# Manage items\n",
            encoding="utf-8",
        )
        (self.root / "ba-pack" / "business-overview.md").write_text(
            "# Business overview\n\n## Journey landscape\n\n"
            "- [Manage items](journeys/repo.journey.items.md)\n",
            encoding="utf-8",
        )
        (self.root / "ba-pack" / "business-catalog.md").write_text(
            "# Business catalog\n\n"
            "## Journey index\n\n- [Manage items](journeys/repo.journey.items.md)\n\n"
            "## Scenario index\n\n- [Complete](scenarios/repo.scenario.complete.md)\n\n"
            "## Tech coverage map\n\n- [Behavior](../tech-pack/behaviors/repo.behavior.md)\n",
            encoding="utf-8",
        )
        plan = self.module.refresh_projections(
            root=self.root,
            transaction_dir=self.tx,
            transaction_id="tx-1",
            stage="ba-publication",
            repository="repo",
            source_commit="abc",
        )
        self.assertEqual(plan["status"], "in-progress")
        behavior = (self.root / "tech-pack" / "behaviors" / "repo.behavior.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('scenario_id: "repo.scenario.complete"', behavior)
        self.assertIn("### BA scenarios", behavior)
        catalog = (self.root / "tech-pack" / "behavior-catalog.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn('scenario_id: "repo.scenario.complete"', catalog)
        overview = (self.root / "tech-pack" / "repository-overview.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("../ba-pack/scenarios/repo.scenario.complete.md", overview)
        self.assertTrue(
            any(item["path"] == "tech-pack/repository-overview.md" for item in plan["semantic_items"])
        )

    def test_api_projection_refreshes_java_and_config_endpoint_navigation(self) -> None:
        (self.root / ".work" / "repository-register.md").write_text(
            "# Repository register\n\n"
            "## Behavior and endpoint Java implementation bindings\n\n"
            "| Binding ID | Behavior ID | Endpoint ID(s) or trigger | Exact entry symbol | Type IDs | Edge IDs | Runtime implementation selection | Status | Unknowns or evidence |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| JIMPL-001 | repo.behavior | repo.get-items | repo.Handler.getItems() | JTYPE-001 | JEDGE-001 | constructor injection | Confirmed | source |\n\n"
            "## Runtime configuration impact records\n\n"
            "| Impact ID | Config ID | Behavior ID | Endpoint ID(s) | Impact type | Condition/value | Execution difference | Caller/state/failure effect | Status | Evidence |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            "| CFG-001-I01 | CFG-001 | repo.behavior | repo.get-items | timeout/retry/recovery | configured | changes timeout | timeout result changes | Confirmed | source |\n",
            encoding="utf-8",
        )
        (self.root / "tech-pack" / "java-implementation-map.md").write_text(
            "# Java implementation map\n\n"
            "## Behavior and API implementation index\n\n"
            "| Implementation | Behavior | Endpoint or trigger | Entry symbol | Principal Java types | Details |\n"
            "|---|---|---|---|---|---|\n"
            "| old | old | old | old | old | old |\n\n"
            '<a id="jimpl-001"></a>\n\n'
            "## JIMPL-001 — Implementation slice\n",
            encoding="utf-8",
        )
        (self.root / "tech-pack" / "runtime-config-matrix.md").write_text(
            "# Runtime configuration matrix\n\n"
            "## Endpoint reverse impact index\n\n"
            "| Endpoint | Affected behavior | Config impacts | What changes | Deep dive |\n"
            "|---|---|---|---|---|\n"
            "| old | old | old | old | old |\n\n"
            '<a id="cfg-001-i01"></a>\n',
            encoding="utf-8",
        )

        plan = self.module.refresh_projections(
            root=self.root,
            transaction_dir=self.tx,
            transaction_id="tx-1",
            stage="api-contract-publication",
            repository="repo",
            source_commit="abc",
        )
        self.assertEqual(plan["status"], "in-progress")
        surfaces = {item["surface"] for item in plan["mechanical_items"]}
        self.assertIn(
            "java-implementation-map.endpoint-behavior-bindings", surfaces
        )
        self.assertIn("runtime-config-matrix.endpoint-reverse-index", surfaces)

        java_map = (
            self.root / "tech-pack" / "java-implementation-map.md"
        ).read_text(encoding="utf-8")
        self.assertIn("[repo.behavior](behaviors/repo.behavior.md)", java_map)
        self.assertIn(
            "[repo.get-items](contracts/repo.get-items.api-contract.md)", java_map
        )
        config = (
            self.root / "tech-pack" / "runtime-config-matrix.md"
        ).read_text(encoding="utf-8")
        self.assertIn("[repo.behavior](behaviors/repo.behavior.md)", config)
        self.assertIn(
            "[repo.get-items](contracts/repo.get-items.api-contract.md)", config
        )
        self.assertIn("[`CFG-001-I01`](#cfg-001-i01)", config)


if __name__ == "__main__":
    unittest.main()
