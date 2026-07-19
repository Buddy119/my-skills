from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from lifecycle_model import (  # noqa: E402
    NO_TRANSITION_SENTENCE,
    validate_lifecycle_document,
    validate_lifecycle_register,
)
from register_schema import load_register_schema  # noqa: E402


class LifecycleModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repository"
        self.pack = self.root / "pack"
        source = self.repo / "src" / "Service.java"
        source.parent.mkdir(parents=True)
        source.write_text("\n".join(f"line {index}" for index in range(1, 41)) + "\n", encoding="utf-8")
        self.schema = json.loads(
            (SKILL_ROOT / "assets" / "register-schema.json").read_text(encoding="utf-8")
        )
        self.rows = {key: [] for key in self.schema["tables"]}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add(self, table: str, *cells: str) -> None:
        self.rows[table].append(list(cells))

    def write_register(self) -> Path:
        parts = [
            "---",
            'artifact_type: "repository-register"',
            'artifact_schema_version: "2"',
            'repository: "fixture"',
            'source_commit: "unknown"',
            'register_status: "reconciled"',
            "---",
            "",
            "# Repository working register",
        ]
        for key, contract in self.schema["tables"].items():
            headers = contract["headers"]
            parts.extend(
                [
                    "",
                    f"## {contract['section']}",
                    "",
                    "| " + " | ".join(headers) + " |",
                    "|" + "|".join("---" for _ in headers) + "|",
                ]
            )
            for row in self.rows[key]:
                self.assertEqual(len(row), len(headers), key)
                parts.append("| " + " | ".join(row) + " |")
        path = self.pack / ".work" / "repository-register.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(parts) + "\n", encoding="utf-8")
        return path

    def add_action_only_model(self, role: str = "Read") -> None:
        self.add(
            "lifecycle_observations",
            "LIFE-OBS-001",
            "Customer record",
            "fixture.read-customer",
            role,
            "customer store",
            "handler",
            "direct call observation",
            "Confirmed",
            "src/Service.java:3",
            "OBJ-001; ACT-001",
        )
        self.add(
            "business_objects",
            "OBJ-001",
            "Customer record",
            "record",
            "customer store",
            "fixture.read-customer",
            "LIFE-OBS-001",
            "Confirmed",
            "State vocabulary not established",
        )
        self.add(
            "processing_actions",
            "ACT-001",
            "OBJ-001",
            "fixture.read-customer",
            role,
            "customer store",
            "handler",
            "None",
            "always",
            "Confirmed",
            "src/Service.java:3",
        )

    def add_transition_model(self, *, transition_status: str = "Confirmed") -> None:
        self.add(
            "lifecycle_observations",
            "LIFE-OBS-001",
            "Customer record",
            "fixture.activate-customer",
            "status field changes",
            "PENDING",
            "ACTIVE",
            "persisted status field",
            "Confirmed",
            "src/Service.java:8-12",
            "OBJ-001; STATE-001; STATE-002; ACT-001; TRANS-001",
        )
        self.add(
            "business_objects",
            "OBJ-001",
            "Customer record",
            "business-object",
            "customer table",
            "fixture.activate-customer",
            "LIFE-OBS-001",
            "Confirmed",
            "None observed",
        )
        self.add(
            "object_states",
            "STATE-001",
            "OBJ-001",
            "Pending",
            "Explicit",
            "status equals PENDING",
            "persisted status field",
            "Confirmed",
            "src/Service.java:8",
        )
        self.add(
            "object_states",
            "STATE-002",
            "OBJ-001",
            "Active",
            "Explicit",
            "status equals ACTIVE",
            "persisted status field",
            "Confirmed",
            "src/Service.java:10",
        )
        self.add(
            "processing_actions",
            "ACT-001",
            "OBJ-001",
            "fixture.activate-customer",
            "Persist",
            "PENDING customer",
            "ACTIVE customer",
            "TRANS-001",
            "activation accepted",
            "Confirmed",
            "src/Service.java:8-12",
        )
        self.add(
            "state_transitions",
            "TRANS-001",
            "OBJ-001",
            "STATE-001",
            "STATE-002",
            "fixture.activate-customer",
            "ACT-001",
            "activation accepted",
            "status ACTIVE is persisted",
            "same transaction",
            transition_status,
            "src/Service.java:8-12",
        )

    def action_only_document(self, *, processing_code: str | None = None) -> str:
        diagram = processing_code or (
            'flowchart LR\n    STORE["Customer store"] --> ACT_001["ACT-001 — Read"]\n'
            '    ACT_001 --> HANDLER["Handler"]'
        )
        return (
            "---\n"
            'artifact_type: "data-lifecycle"\n'
            'artifact_schema_version: "2"\n'
            'repository: "fixture"\n'
            'source_commit: "unknown"\n'
            'coverage_status: "complete"\n'
            "---\n\n"
            "# Data and state lifecycle\n\n"
            "## Object landscape\n\n"
            "| Object ID | Logical object or resource | Type | Source, ownership, and store | Behaviors | State model | Processing and data movement | Status | Details |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| `OBJ-001` | Customer record | record | Customer store | fixture.read-customer | Not established | Read | Confirmed | [Details](#obj-001) |\n\n"
            '<a id="obj-001"></a>\n'
            "## `OBJ-001` — Customer record\n\n"
            "### Object identity and ownership\n\nCustomer record in the customer store.\n\n"
            "### State vocabulary\n\n"
            "| State ID | State | Basis | Definition or derivation | Persistence or observability | Status | Evidence |\n"
            "|---|---|---|---|---|---|---|\n\n"
            f"{NO_TRANSITION_SENTENCE}\n\n"
            "### Processing and data movement\n\n"
            "<!-- lifecycle-processing-diagram: OBJ-001 -->\n"
            f"```mermaid\n{diagram}\n```\n\n"
            "| Action ID | Role | Behavior | Input or source | Output or destination | Related transition | Condition | Status | Evidence |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| `ACT-001` | Read | fixture.read-customer | customer store | handler | None | always | Confirmed | `src/Service.java:3` |\n\n"
            "### Consistency and unresolved questions\n\nNo object state vocabulary was established.\n"
        )

    def transition_document(self, *, state_code: str | None = None) -> str:
        diagram = state_code or (
            'stateDiagram-v2\n'
            '    state "STATE-001 — Pending" as STATE_001\n'
            '    state "STATE-002 — Active" as STATE_002\n'
            '    STATE_001 --> STATE_002: TRANS-001 [Confirmed]'
        )
        return (
            "---\n"
            'artifact_type: "data-lifecycle"\n'
            'artifact_schema_version: "2"\n'
            'repository: "fixture"\n'
            'source_commit: "unknown"\n'
            'coverage_status: "complete"\n'
            "---\n\n"
            "# Data and state lifecycle\n\n"
            "## Object landscape\n\n"
            "| Object ID | Logical object or resource | Type | Source, ownership, and store | Behaviors | State model | Processing and data movement | Status | Details |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| `OBJ-001` | Customer record | business-object | Customer table | fixture.activate-customer | Confirmed | Persist | Confirmed | [Details](#obj-001) |\n\n"
            '<a id="obj-001"></a>\n'
            "## `OBJ-001` — Customer record\n\n"
            "### Object identity and ownership\n\nCustomer record persisted by this repository.\n\n"
            "### State vocabulary\n\n"
            "| State ID | State | Basis | Definition or derivation | Persistence or observability | Status | Evidence |\n"
            "|---|---|---|---|---|---|---|\n"
            "| `STATE-001` | Pending | Explicit | status PENDING | persisted field | Confirmed | `src/Service.java:8` |\n"
            "| `STATE-002` | Active | Explicit | status ACTIVE | persisted field | Confirmed | `src/Service.java:10` |\n\n"
            "### State lifecycle diagram\n\n"
            "<!-- lifecycle-state-diagram: OBJ-001 -->\n"
            f"```mermaid\n{diagram}\n```\n\n"
            '<a id="trans-001"></a>\n'
            "### State transitions\n\n"
            "| Transition ID | From state | To state | Triggering behavior | Causing action(s) | Condition | Result and consistency impact | Status | Evidence |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| `TRANS-001` | `STATE-001` | `STATE-002` | fixture.activate-customer | `ACT-001` | activation accepted | ACTIVE persisted in one transaction | Confirmed | `src/Service.java:8-12` |\n\n"
            "### Processing and data movement\n\n"
            "<!-- lifecycle-processing-diagram: OBJ-001 -->\n"
            "```mermaid\nflowchart LR\n    INPUT[Pending record] --> ACT_001[\"ACT-001 — Persist\"]\n    ACT_001 --> STORE[Customer table]\n```\n\n"
            "| Action ID | Role | Behavior | Input or source | Output or destination | Related transition | Condition | Status | Evidence |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| `ACT-001` | Persist | fixture.activate-customer | Pending customer | customer table | `TRANS-001` | activation accepted | Confirmed | `src/Service.java:8-12` |\n\n"
            "### Consistency and unresolved questions\n\nThe change occurs in one observed transaction.\n"
        )

    def validate_document(self, body: str):
        register = self.write_register()
        lifecycle = validate_lifecycle_register(register, load_register_schema())
        path = self.pack / "tech-pack" / "data-lifecycle.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return lifecycle, validate_lifecycle_document(path, lifecycle, self.repo)

    def test_read_validate_map_and_emit_remain_actions_without_states(self) -> None:
        for role in ("Read", "Observe", "Validate", "Map", "Emit"):
            with self.subTest(role=role):
                self.rows = {key: [] for key in self.schema["tables"]}
                self.add_action_only_model(role)
                lifecycle, errors = self.validate_document(
                    self.action_only_document().replace("| Read |", f"| {role} |", 1)
                )
                self.assertEqual(lifecycle.errors, [])
                self.assertEqual(lifecycle.data["states"], {})
                self.assertEqual(lifecycle.data["transitions"], {})
                self.assertEqual(errors, [])

    def test_persist_without_before_after_evidence_does_not_create_transition(self) -> None:
        self.add_action_only_model("Persist")
        lifecycle, errors = self.validate_document(
            self.action_only_document().replace("| Read |", "| Persist |", 1)
        )
        self.assertEqual(lifecycle.errors, [])
        self.assertEqual(lifecycle.data["transitions"], {})
        self.assertEqual(errors, [])

    def test_explicit_state_transition_and_typed_diagrams_are_valid(self) -> None:
        self.add_transition_model()
        lifecycle, errors = self.validate_document(self.transition_document())
        self.assertEqual(lifecycle.errors, [])
        self.assertEqual(errors, [])

    def test_derived_state_cannot_be_confirmed(self) -> None:
        self.add_transition_model()
        self.rows["object_states"][1][3] = "Derived"
        lifecycle = validate_lifecycle_register(self.write_register(), load_register_schema())
        self.assertIn("Derived State cannot be Confirmed: STATE-002", lifecycle.errors)

    def test_transition_cannot_cross_object_boundaries(self) -> None:
        self.add_transition_model()
        self.rows["object_states"][1][1] = "OBJ-002"
        self.add(
            "business_objects",
            "OBJ-002",
            "Other record",
            "record",
            "other table",
            "fixture.activate-customer",
            "LIFE-OBS-001",
            "Confirmed",
            "None observed",
        )
        lifecycle = validate_lifecycle_register(self.write_register(), load_register_schema())
        self.assertTrue(any("crosses Object boundaries" in item for item in lifecycle.errors))

    def test_unknown_transition_is_not_publishable_as_state_edge(self) -> None:
        self.add_transition_model(transition_status="Unknown")
        body = self.transition_document().replace("[Confirmed]", "[Inferred]")
        _lifecycle, errors = self.validate_document(body)
        self.assertTrue(any("no established Transition but publishes a State Diagram" in item for item in errors))
        self.assertTrue(any("publishes non-established Transition" in item for item in errors))

    def test_state_diagram_rejects_action_nodes_and_unregistered_edges(self) -> None:
        self.add_transition_model()
        diagram = (
            'stateDiagram-v2\n'
            '    state "STATE-001 — Pending" as STATE_001\n'
            '    state "STATE-002 — Active" as STATE_002\n'
            '    state "ACT-001 — Persist" as ACT_001\n'
            '    STATE_001 --> STATE_002: TRANS-999 [Confirmed]'
        )
        _lifecycle, errors = self.validate_document(self.transition_document(state_code=diagram))
        self.assertTrue(any("contains an Action identity" in item for item in errors))
        self.assertTrue(any("unknown Transition: TRANS-999" in item for item in errors))

    def test_processing_diagram_rejects_state_identity(self) -> None:
        self.add_action_only_model()
        code = (
            'flowchart LR\n    STORE["Customer store"] --> ACT_001["ACT-001 — Read"]\n'
            '    ACT_001 --> STATE_001["STATE-001 — Read complete"]'
        )
        _lifecycle, errors = self.validate_document(self.action_only_document(processing_code=code))
        self.assertTrue(any("Processing Diagram OBJ-001 contains a State identity" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
