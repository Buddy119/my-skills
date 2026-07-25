from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
BEHAVIOR_VALIDATOR = SCRIPTS / "validate_behavior_doc.py"
API_VALIDATOR = SCRIPTS / "validate_api_contract.py"
EXECUTOR = SCRIPTS / "stage_executor.py"


def load_executor_module():
    sys.path.insert(0, str(SCRIPTS))
    specification = importlib.util.spec_from_file_location("stage_executor_api_order", EXECUTOR)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    try:
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def behavior_document(
    contracts: list[tuple[str, str]],
    *,
    entry_type: str = "api",
    linked_documents: set[str] | None = None,
) -> str:
    if contracts:
        contract_yaml = "api_contracts:\n" + "".join(
            f'  - endpoint_id: "{endpoint_id}"\n    document: "{document}"\n'
            for endpoint_id, document in contracts
        )
    else:
        contract_yaml = "api_contracts: []\n"
    links = contracts if linked_documents is None else [
        (endpoint_id, document)
        for endpoint_id, document in contracts
        if document in linked_documents
    ]
    api_section = ""
    if entry_type == "api":
        api_section = "## API contracts\n\n" + "".join(
            f"- [{endpoint_id}]({document})\n" for endpoint_id, document in links
        ) + "\n"
    return (
        "---\n"
        'artifact_type: "tech-behavior"\n'
        'artifact_schema_version: "5"\n'
        'behavior_id: "sample-repo.get-customer"\n'
        'title: "Get customer"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        f'entry_type: "{entry_type}"\n'
        'entry_point: "GET /customers/{id}"\n'
        'behavior_category: "business"\n'
        'overall_status: "Confirmed"\n'
        + contract_yaml
        + "ba_scenarios: []\n"
        "consumes: []\n"
        "produces: []\n"
        "reads: []\n"
        "writes: []\n"
        "external_dependencies: []\n"
        "external_http_calls: []\n"
        "field_mappings: []\n"
        "failure_patterns: []\n"
        "java_bindings: []\n"
        "runtime_config_impacts: []\n"
        "analysis_limitations: []\n"
        "---\n\n"
        "# Get customer\n\n"
        "## Summary\n\nReturns the observed customer result. [E1](#e1)\n\n"
        "## Trigger and entry point\n\nThe application route invokes the handler.\n\n"
        + api_section
        + "## Main path\n\n1. Accept the request.\n2. Return the result.\n\n"
        + "## Behavior flow\n\n```mermaid\nflowchart TD\n    A[Request] --> B[Response]\n```\n\n"
        "## Implementation sequence\n\n```mermaid\nsequenceDiagram\n"
        "    participant Caller\n    participant Handler\n"
        "    Caller->>Handler: Request\n    Handler-->>Caller: Response\n```\n\n"
        "## Exception and failure handling\n\nNo material exception was observed.\n\n"
        "## Inputs\n\nThe caller input is defined in the API Contract.\n\n"
        "## Preconditions and business rules\n\nNo additional rule was observed.\n\n"
        "## Happy path\n\n1. Accept the request.\n2. Return the result.\n\n"
        "## Data access and processing\n\nNo processing action was observed.\n\n"
        "## Object state transitions\n\nNo object state transition was observed.\n\n"
        "## Outputs and side effects\n\nReturns the caller-visible response.\n\n"
        "## Open questions and conflicts\n\nExternal deployment remains Unknown.\n\n"
        "## Source notes\n\n"
        '<a id="e1"></a> **E1** — `src/Handler.java:1` supports the behavior summary.\n'
    )


class ApiPublicationOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "sample-repo"
        source = self.repo / "src" / "Handler.java"
        source.parent.mkdir(parents=True)
        source.write_text("class Handler {}\n", encoding="utf-8")
        self.behaviors = self.root / "pack" / "tech-pack" / "behaviors"
        self.behaviors.mkdir(parents=True)
        self.document = self.behaviors / "sample-repo.get-customer.md"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_validator(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BEHAVIOR_VALIDATOR),
                str(self.document),
                "--repo",
                str(self.repo),
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    def test_tech_profile_allows_only_missing_contract_target(self) -> None:
        contract = "../contracts/sample-repo.get-customer.api-contract.md"
        self.document.write_text(
            behavior_document([("sample-repo.get-customer", contract)]),
            encoding="utf-8",
        )

        strict = self.run_validator()
        self.assertEqual(strict.returncode, 1)
        self.assertIn("linked API contract does not exist", strict.stdout)

        tech = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(tech.returncode, 0, tech.stdout + tech.stderr)

    def test_forward_reference_requires_exact_identity_path_and_body_link(self) -> None:
        wrong = "../contracts/different.api-contract.md"
        self.document.write_text(
            behavior_document([("sample-repo.get-customer", wrong)]),
            encoding="utf-8",
        )
        result = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(result.returncode, 1)
        self.assertIn("document must match its Endpoint ID", result.stdout)

        expected = "../contracts/sample-repo.get-customer.api-contract.md"
        self.document.write_text(
            behavior_document(
                [("sample-repo.get-customer", expected)], linked_documents=set()
            ),
            encoding="utf-8",
        )
        result = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(result.returncode, 1)
        self.assertIn("body must link endpoint", result.stdout)

    def test_forward_reference_rejects_duplicate_ids_and_documents(self) -> None:
        expected = "../contracts/sample-repo.get-customer.api-contract.md"
        self.document.write_text(
            behavior_document(
                [
                    ("sample-repo.get-customer", expected),
                    ("sample-repo.get-customer", expected),
                ]
            ),
            encoding="utf-8",
        )
        result = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate Endpoint IDs", result.stdout)
        self.assertIn("duplicate documents", result.stdout)

    def test_multiple_endpoint_forward_references_are_allowed(self) -> None:
        contracts = [
            (
                "sample-repo.get-customer",
                "../contracts/sample-repo.get-customer.api-contract.md",
            ),
            (
                "sample-repo.put-customer",
                "../contracts/sample-repo.put-customer.api-contract.md",
            ),
        ]
        self.document.write_text(behavior_document(contracts), encoding="utf-8")
        result = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_behavior_requires_independent_flowchart_and_sequence_diagram(self) -> None:
        document = behavior_document([])
        self.document.write_text(
            document.replace("sequenceDiagram", "flowchart TD", 1),
            encoding="utf-8",
        )
        result = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Implementation sequence must contain exactly one Mermaid sequenceDiagram",
            result.stdout,
        )

        self.document.write_text(
            document.replace("flowchart TD", "sequenceDiagram", 1),
            encoding="utf-8",
        )
        result = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Behavior flow must contain exactly one Mermaid flowchart or graph",
            result.stdout,
        )

    def test_contract_requires_direct_implementation_sequence_navigation(self) -> None:
        endpoint_id = "sample-repo.get-customer"
        relative_contract = f"../contracts/{endpoint_id}.api-contract.md"
        self.document.write_text(
            behavior_document([(endpoint_id, relative_contract)]),
            encoding="utf-8",
        )
        contracts = self.root / "pack" / "tech-pack" / "contracts"
        contracts.mkdir(parents=True)
        matrix = self.root / "pack" / "tech-pack" / "endpoint-matrix.md"
        matrix.write_text(
            "# Endpoint matrix\n\n"
            "## Endpoint summary\n\n"
            "| Endpoint or Exposure ID | Operation Role | Application Route | External Entry Declaration | Environment Deployment Intent | Observed Runtime Deployment | External Reachability | Behavior | Contract |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            f"| `{endpoint_id}` | application-endpoint | Confirmed — `GET /customers/{{id}}` | Not observed | Not observed | Not observed | Not observed | [Behavior](behaviors/{endpoint_id}.md) | [Contract](contracts/{endpoint_id}.api-contract.md) |\n\n"
            f'<a id="{endpoint_id.replace(".", "-")}"></a>\n\n'
            f"## `{endpoint_id}`\n",
            encoding="utf-8",
        )
        contract = contracts / f"{endpoint_id}.api-contract.md"
        base = (
            "---\n"
            'artifact_type: "api-contract"\n'
            'artifact_schema_version: "3"\n'
            f'behavior_id: "{endpoint_id}"\n'
            f'endpoint_id: "{endpoint_id}"\n'
            'title: "Get customer"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            'entry_point: "GET /customers/{id}"\n'
            'method: "GET"\n'
            'route: "/customers/{id}"\n'
            'contract_status: "Confirmed"\n'
            'application_route_status: "Confirmed"\n'
            'external_reachability_status: "Not observed"\n'
            f'behavior_document: "../behaviors/{endpoint_id}.md"\n'
            f'endpoint_matrix: "../endpoint-matrix.md#{endpoint_id.replace(".", "-")}"\n'
            "---\n\n"
            "# Get customer\n\nPurpose. [E1](#e1)\n\n"
            "## Quick reference\n\n"
            "| Property | Value |\n|---|---|\n"
            "| Method and application route | `GET /customers/{id}` |\n"
            "| Authentication | Unknown |\n"
            "| Content type | Unknown |\n"
            "| Contract confidence | Confirmed |\n"
            f"| External reachability | [Not observed](../endpoint-matrix.md#{endpoint_id.replace('.', '-')}) |\n\n"
            "## Request\n\nThe path identifies the customer.\n\n"
            "## Responses\n\n"
            "| HTTP status | When | Body/schema | Relevant headers |\n"
            "|---|---|---|---|\n"
            "| 200 | Request succeeds | Customer | None observed |\n\n"
            "## Related documents\n\n"
            f"- [Tech Behavior](../behaviors/{endpoint_id}.md)\n"
            f"- [Endpoint Matrix](../endpoint-matrix.md#{endpoint_id.replace('.', '-')})\n"
            "__SEQUENCE_LINK__"
            "\n## Source notes\n\n"
            '<a id="e1"></a> **E1** — `src/Handler.java:1` supports the route.\n'
        )
        contract.write_text(base.replace("__SEQUENCE_LINK__", ""), encoding="utf-8")
        missing = subprocess.run(
            [
                sys.executable,
                str(API_VALIDATOR),
                str(contract),
                "--repo",
                str(self.repo),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(missing.returncode, 1)
        self.assertIn("must link directly", missing.stdout)

        sequence_link = (
            f"- [Implementation sequence]"
            f"(../behaviors/{endpoint_id}.md#implementation-sequence)\n"
        )
        contract.write_text(
            base.replace("__SEQUENCE_LINK__", sequence_link), encoding="utf-8"
        )
        valid = subprocess.run(
            [
                sys.executable,
                str(API_VALIDATOR),
                str(contract),
                "--repo",
                str(self.repo),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

    def test_non_api_behavior_cannot_declare_contracts(self) -> None:
        contract = "../contracts/sample-repo.get-customer.api-contract.md"
        self.document.write_text(
            behavior_document(
                [("sample-repo.get-customer", contract)], entry_type="sqs"
            ),
            encoding="utf-8",
        )
        result = self.run_validator("--allow-missing-api-contracts")
        self.assertEqual(result.returncode, 1)
        self.assertIn("non-API behavior must set api_contracts: []", result.stdout)

    def test_executor_uses_forward_reference_mode_only_for_tech_stage(self) -> None:
        self.document.write_text(behavior_document([]), encoding="utf-8")
        executor = load_executor_module()
        candidate = self.root / "pack"
        (candidate / ".work").mkdir(exist_ok=True)
        (candidate / ".work" / "analysis-state.yaml").write_text("", encoding="utf-8")
        (candidate / ".work" / "behavior-catalog.yaml").write_text("", encoding="utf-8")
        (candidate / ".work" / "behavior-dossiers").mkdir()

        tech_commands = executor.validator_commands("tech-publication", candidate, self.repo)
        api_commands = executor.validator_commands(
            "api-contract-publication", candidate, self.repo
        )
        diagnostic_commands = executor.validator_commands(
            "tech-publication",
            candidate,
            self.repo,
            diagnostic_manifest=True,
        )
        ba_commands = executor.validator_commands("ba-publication", candidate, self.repo)
        final_commands = executor.validator_commands("finalization", candidate, self.repo)
        business_model_commands = executor.validator_commands(
            "business-model", candidate, self.repo
        )
        tech_behavior = next(
            command for command in tech_commands if "validate_behavior_doc.py" in command[1]
        )
        api_behavior = next(
            command for command in api_commands if "validate_behavior_doc.py" in command[1]
        )
        tech_pack = next(
            command for command in tech_commands if "validate_pack_links.py" in command[1]
        )
        api_pack = next(
            command for command in api_commands if "validate_pack_links.py" in command[1]
        )
        diagnostic_pack = next(
            command
            for command in diagnostic_commands
            if "validate_pack_links.py" in command[1]
        )
        self.assertIn("--allow-missing-api-contracts", tech_behavior)
        self.assertNotIn("--allow-missing-api-contracts", api_behavior)
        self.assertEqual(
            tech_pack[tech_pack.index("--validation-profile") + 1],
            "tech-publication",
        )
        self.assertEqual(
            api_pack[api_pack.index("--validation-profile") + 1],
            "complete",
        )
        self.assertEqual(
            diagnostic_pack[diagnostic_pack.index("--validation-profile") + 1],
            "tech-publication",
        )
        self.assertIn("--skip-artifact-manifest", diagnostic_pack)
        self.assertNotIn("--require-artifact-manifest", diagnostic_pack)
        for commands in (tech_commands, api_commands, ba_commands, final_commands):
            self.assertTrue(
                any("validate_publication_maturity.py" in command[1] for command in commands)
            )
        self.assertFalse(
            any(
                "validate_publication_maturity.py" in command[1]
                for command in business_model_commands
            )
        )

    def test_api_stage_skip_rejects_behavior_or_catalog_intent(self) -> None:
        executor = load_executor_module()
        candidate = self.root / "pack"
        state = candidate / ".work" / "analysis-state.yaml"
        state.parent.mkdir(exist_ok=True)
        state.write_text('business_model_status: "pending"\n', encoding="utf-8")

        contract = "../contracts/sample-repo.get-customer.api-contract.md"
        self.document.write_text(
            behavior_document([("sample-repo.get-customer", contract)]),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(executor.ExecutorError, "API Behaviors"):
            executor.stage_skip_allowed(
                "api-contract-publication", candidate, "No API expected"
            )

        self.document.write_text(behavior_document([], entry_type="sqs"), encoding="utf-8")
        catalog = candidate / "tech-pack" / "behavior-catalog.yaml"
        catalog.parent.mkdir(exist_ok=True)
        catalog.write_text(
            "behaviors:\n"
            '  - behavior_id: "sample-repo.event"\n'
            "    api_contracts:\n"
            '      - endpoint_id: "sample-repo.get-customer"\n'
            '        document: "contracts/sample-repo.get-customer.api-contract.md"\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(executor.ExecutorError, "planned API Contracts"):
            executor.stage_skip_allowed(
                "api-contract-publication", candidate, "No API expected"
            )

        catalog.write_text("behaviors: []\n", encoding="utf-8")
        executor.stage_skip_allowed(
            "api-contract-publication", candidate, "Event-only repository"
        )


if __name__ == "__main__":
    unittest.main()
