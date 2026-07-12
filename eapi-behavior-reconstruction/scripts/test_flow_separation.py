#!/usr/bin/env python3
"""Regression tests for Tech/BA perspective separation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validate_flow_separation import validate_pair


TECH_SUMMARY = (
    "The handler receives a request, validates the customer identifier, "
    "and returns an error or success response."
)
TECH_LABELS = [
    "Receive request in handler",
    "Validate customer identifier",
    "Return error response",
    "Return success response",
]


class FlowSeparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.pack = self.root / "pack"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src" / "handler.py").write_text("handler = True\n", encoding="utf-8")
        (self.pack / ".work" / "flow-models").mkdir(parents=True)
        (self.pack / "tech-pack" / "behaviors").mkdir(parents=True)
        (self.pack / "ba-pack" / "behaviors").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_pair(self, ba_summary: str, ba_labels: list[str]) -> tuple[Path, Path]:
        tech_model = self.model("technical", TECH_SUMMARY, TECH_LABELS)
        ba_model = self.model("business", ba_summary, ba_labels)
        tech_model_path = self.pack / ".work" / "flow-models" / "sample.behavior.tech-flow.json"
        ba_model_path = self.pack / ".work" / "flow-models" / "sample.behavior.ba-flow.json"
        tech_model_path.write_text(json.dumps(tech_model, indent=2), encoding="utf-8")
        ba_model_path.write_text(json.dumps(ba_model, indent=2), encoding="utf-8")

        tech_document = self.pack / "tech-pack" / "behaviors" / "sample.behavior.md"
        ba_document = self.pack / "ba-pack" / "behaviors" / "sample.behavior.md"
        tech_document.write_text(
            self.document("technical", "Summary", TECH_SUMMARY, TECH_LABELS),
            encoding="utf-8",
        )
        ba_document.write_text(
            self.document("business", "Business summary", ba_summary, ba_labels),
            encoding="utf-8",
        )
        return tech_document, ba_document

    @staticmethod
    def model(perspective: str, summary: str, labels: list[str]) -> dict[str, object]:
        prefix = "T" if perspective == "technical" else "B"
        tech_types = ["trigger-adapter", "validation", "failure", "technical-outcome"]
        ba_types = ["actor-event", "business-decision", "business-exception", "business-outcome"]
        semantic_types = tech_types if perspective == "technical" else ba_types
        nodes = []
        for index, (label, semantic_type) in enumerate(zip(labels, semantic_types), start=1):
            node: dict[str, object] = {
                "node_id": f"{prefix}{index}",
                "semantic_type": semantic_type,
                "label": label,
                "claim_ids": [f"CLM-sample-behavior-{perspective}-node-{index}"],
            }
            if perspective == "technical":
                node["evidence"] = ["src/handler.py:1"]
            else:
                node["status"] = "Confirmed"
            nodes.append(node)
        return {
            "behavior_id": "sample.behavior",
            "repository": "sample",
            "source_commit": "unknown",
            "perspective": perspective,
            "summary": summary,
            "summary_claim_ids": [f"CLM-sample-behavior-{perspective}-summary"],
            "nodes": nodes,
            "edges": [
                {"from": f"{prefix}1", "to": f"{prefix}2", "condition": None, "claim_ids": [f"CLM-sample-behavior-{perspective}-edge-1"]},
                {"from": f"{prefix}2", "to": f"{prefix}3", "condition": "failure", "claim_ids": [f"CLM-sample-behavior-{perspective}-edge-2"]},
                {"from": f"{prefix}2", "to": f"{prefix}4", "condition": "success", "claim_ids": [f"CLM-sample-behavior-{perspective}-edge-3"]},
            ],
            **(
                {
                    "derived_from": {
                        "behavior_ids": ["sample.behavior"],
                        "business_rule_ids": [],
                        "business_exception_ids": [],
                    }
                }
                if perspective == "business"
                else {}
            ),
        }

    @staticmethod
    def document(perspective: str, heading: str, summary: str, labels: list[str]) -> str:
        prefix = "T" if perspective == "technical" else "B"
        model_key = "tech_flow_model" if perspective == "technical" else "ba_flow_model"
        suffix = "tech-flow" if perspective == "technical" else "ba-flow"
        diagram = "\n".join(
            [
                "flowchart TD",
                f'    {prefix}1["{labels[0]}"] --> {prefix}2{{"{labels[1]}"}}',
                f'    {prefix}2 -->|failure| {prefix}3["{labels[2]}"]',
                f'    {prefix}2 -->|success| {prefix}4["{labels[3]}"]',
            ]
        )
        return f"""---
behavior_id: "sample.behavior"
repository: "sample"
source_commit: "unknown"
flow_perspective: "{perspective}"
summary_perspective: "{perspective}"
{model_key}: "../../.work/flow-models/sample.behavior.{suffix}.json"
---

# Behavior

## {heading}

{summary}

## Flow

```mermaid
{diagram}
```
"""

    def test_independent_business_flow_passes(self) -> None:
        tech, ba = self.write_pair(
            "Customer information is checked so the request can be accepted or rejected.",
            [
                "Customer information is submitted",
                "Customer identifier present?",
                "Request rejected",
                "Request accepted",
            ],
        )
        errors, _warnings, metrics = validate_pair(tech, ba, self.repo)
        self.assertEqual([], errors)
        self.assertLess(metrics["node_similarity"], 0.60)

    def test_identical_flow_is_rejected(self) -> None:
        tech, ba = self.write_pair(TECH_SUMMARY, TECH_LABELS)
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertTrue(any("identical" in error for error in errors), errors)

    def test_mechanical_noun_insertion_is_rejected_for_legacy_v1(self) -> None:
        tech, ba = self.write_pair(
            "The business handler receives a request, validates the customer identifier, "
            "and returns a business error or success response.",
            [
                "Receive business request in handler",
                "Validate customer identifier",
                "Return business error response",
                "Return business success response",
            ],
        )
        errors, _warnings, metrics = validate_pair(tech, ba, self.repo)
        self.assertGreaterEqual(metrics["node_similarity"], 0.72)
        self.assertTrue(any("near-identical" in error for error in errors), errors)

    def test_technical_terminology_in_ba_flow_is_rejected_for_legacy_v1(self) -> None:
        tech, ba = self.write_pair(
            "A customer request is checked and receives an accepted or rejected outcome.",
            [
                "Customer submits request",
                "Business condition satisfied?",
                "Lambda returns HTTP 400",
                "Request accepted",
            ],
        )
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertTrue(any("implementation terminology" in error for error in errors), errors)

    def test_legacy_v1_does_not_gain_long_paragraph_reuse_gate(self) -> None:
        tech, ba = self.write_pair(
            "Customer information is checked so the request can be accepted or rejected.",
            [
                "Customer information is submitted",
                "Customer identifier present?",
                "Request rejected",
                "Request accepted",
            ],
        )
        shared = (
            "This long shared limitation explains that the available repository evidence does not "
            "establish ownership outside the current boundary and that another system may determine "
            "the eventual end-to-end result after this repository completes its local responsibility."
        )
        for document in (tech, ba):
            document.write_text(
                document.read_text(encoding="utf-8") + "\n## Shared limitation\n\n" + shared + "\n",
                encoding="utf-8",
            )
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertEqual([], errors)

    def test_edge_without_claim_ids_is_rejected(self) -> None:
        tech, ba = self.write_pair(
            "Customer information is checked so the request can be accepted or rejected.",
            [
                "Customer information is submitted",
                "Customer identifier present?",
                "Request rejected",
                "Request accepted",
            ],
        )
        model_path = self.pack / ".work" / "flow-models" / "sample.behavior.ba-flow.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        del model["edges"][0]["claim_ids"]
        model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertTrue(any("edge 1 must contain valid claim_ids" in error for error in errors), errors)

    def test_flow_model_outside_canonical_directory_is_rejected(self) -> None:
        tech, ba = self.write_pair(
            "Customer information is checked so the request can be accepted or rejected.",
            [
                "Customer information is submitted",
                "Customer identifier present?",
                "Request rejected",
                "Request accepted",
            ],
        )
        canonical = self.pack / ".work" / "flow-models" / "sample.behavior.ba-flow.json"
        external = self.root / "external-ba-flow.json"
        external.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")
        text = ba.read_text(encoding="utf-8").replace(
            '../../.work/flow-models/sample.behavior.ba-flow.json',
            str(external),
        )
        ba.write_text(text, encoding="utf-8")
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertTrue(any("canonical .work/flow-models directory" in error for error in errors), errors)

    def test_mermaid_topology_must_match_model(self) -> None:
        tech, ba = self.write_pair(
            "Customer information is checked so the request can be accepted or rejected.",
            [
                "Customer information is submitted",
                "Customer identifier present?",
                "Request rejected",
                "Request accepted",
            ],
        )
        text = ba.read_text(encoding="utf-8").replace(
            '    B2 -->|success| B4["Request accepted"]',
            '    B4["Request accepted"] -->|success| B2',
        )
        ba.write_text(text, encoding="utf-8")
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertTrue(any("edge topology/conditions" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
