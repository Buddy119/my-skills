#!/usr/bin/env python3
"""Regression tests for v2 fact-grounded, high-freedom Narrative rendering."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validate_ba_behavior import OBVIOUS_SECRET_RE, RAW_CITATION_RE
from validate_claim_ledger import (
    canonical_excerpt,
    claim_sha256,
    material_semantic_findings,
    pack_format_version,
    text_sha256,
    validate_claim_pack,
    validate_narrative_document_claims,
    validate_v2_reference_document_claims,
)
from validate_readability import readability_diagnostics
from validate_flow_separation import first_narrative_section, validate_pair


class V2NarrativeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.pack = Path(self.temporary.name) / "pack"
        (self.pack / ".work").mkdir(parents=True)
        (self.pack / "tech-pack" / "behaviors").mkdir(parents=True)
        (self.pack / "tech-pack" / "endpoints").mkdir(parents=True)
        (self.pack / "knowledge-manifest.yaml").write_text(
            'pack_format_version: 2\nrepository: "repo"\nsource_commit: "commit"\n',
            encoding="utf-8",
        )
        self.claims = {
            "CLM-receives-request": {
                "claim_id": "CLM-receives-request",
                "statement": "The handler receives customerId from the request.",
                "status": "Confirmed",
                "claim_type": "input",
                "risk": "normal",
                "subject_ids": ["repo.behavior"],
                "render_terms": ["customerId"],
            },
            "CLM-returns-result": {
                "claim_id": "CLM-returns-result",
                "statement": "The handler returns a local result after validation.",
                "status": "Confirmed",
                "claim_type": "output",
                "risk": "normal",
                "subject_ids": ["repo.behavior"],
                "render_terms": ["result"],
            },
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_narrative(self, body: str) -> Path:
        document = self.pack / "tech-pack" / "behaviors" / "repo.behavior.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: commit\nbehavior_id: repo.behavior\nclaim_ids:\n"
            "  - CLM-receives-request\n  - CLM-returns-result\n---\n\n" + body,
            encoding="utf-8",
        )
        return document

    def test_multisentence_narrative_without_markers_passes(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\n"
            "A request starts the behavior. The implementation checks the supplied information "
            "before producing its local result, which gives a developer the main path without "
            "repeating each atomic Claim.\n"
        )
        errors, warnings, used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertEqual([], errors)
        self.assertEqual([], warnings)
        self.assertEqual(set(self.claims), used)

    def test_narrative_does_not_require_render_terms(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\n"
            "The incoming information is checked before a local outcome is produced.\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertEqual([], errors)

    def test_unsupported_persistence_is_rejected_as_material(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\nThe behavior persists the customer record after validation.\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertTrue(any("persistence/commit" in error for error in errors), errors)

    def test_unsupported_material_heading_is_rejected(self) -> None:
        document = self.write_narrative(
            "## Guaranteed persistence\n\nThe implementation completes its local work.\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertTrue(any("persistence/commit" in error for error in errors), errors)

    def test_unsupported_material_table_value_is_rejected(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\n| Concern | Result |\n|---|---|\n| Storage | Persists the customer record |\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertTrue(any("persistence/commit" in error for error in errors), errors)

    def test_behavior_cannot_borrow_another_behaviors_claim(self) -> None:
        claims = dict(self.claims)
        claims["CLM-receives-request"] = dict(
            claims["CLM-receives-request"], subject_ids=["repo.other-behavior"]
        )
        document = self.write_narrative(
            "## At a glance\n\nThe incoming information is checked before a local result is returned.\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(document, self.pack, claims)
        self.assertTrue(any("is not bound to behavior" in error for error in errors), errors)

    def test_inferred_material_claim_cannot_render_as_certain(self) -> None:
        claims = dict(self.claims)
        claims["CLM-persists-record"] = {
            "claim_id": "CLM-persists-record",
            "statement": "The repository call may persist the customer record.",
            "status": "Inferred",
            "claim_type": "data-write",
            "risk": "high",
            "subject_ids": ["repo.behavior"],
            "render_terms": ["persist"],
        }
        document = self.pack / "tech-pack" / "behaviors" / "repo.behavior.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: commit\nbehavior_id: repo.behavior\nclaim_ids:\n"
            "  - CLM-persists-record\n---\n\n## At a glance\n\nThe behavior persists the customer record.\n",
            encoding="utf-8",
        )
        errors, _warnings, _used = validate_narrative_document_claims(document, self.pack, claims)
        self.assertTrue(any("only Inferred/Conflicting" in error for error in errors), errors)

    def test_tentative_material_wording_preserves_inferred_status(self) -> None:
        claims = {
            "CLM-persists-record": {
                "claim_id": "CLM-persists-record",
                "statement": "The repository call may persist the customer record.",
                "status": "Inferred",
                "claim_type": "data-write",
                "risk": "high",
                "subject_ids": ["repo.behavior"],
                "render_terms": ["persist"],
            }
        }
        document = self.pack / "tech-pack" / "behaviors" / "repo.behavior.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: commit\nbehavior_id: repo.behavior\nclaim_ids:\n"
            "  - CLM-persists-record\n---\n\n## At a glance\n\nThe repository call may persist the customer record.\n",
            encoding="utf-8",
        )
        errors, _warnings, _used = validate_narrative_document_claims(document, self.pack, claims)
        self.assertEqual([], errors)

    def test_status_literal_transition_requires_state_claim(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\nAfter validation, status becomes ACTIVE.\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertTrue(any("business state transition" in error for error in errors), errors)

    def test_reverse_status_word_order_is_also_material(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\nAfter validation, the handler sets status to ACTIVE.\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertTrue(any("business state transition" in error for error in errors), errors)

    def test_claim_category_allows_natural_persistence_synonym(self) -> None:
        claims = {
            "CLM-writes-record": {
                "claim_id": "CLM-writes-record",
                "statement": "The operation writes the customer record to durable storage.",
                "status": "Confirmed",
                "claim_type": "data-write",
                "risk": "high",
                "subject_ids": ["repo.behavior"],
                "render_terms": ["writes"],
            }
        }
        errors, _warnings = material_semantic_findings(
            "The behavior persists the customer record.",
            bound_claims=list(claims.values()),
            context="flow node",
        )
        self.assertEqual([], errors)

    def test_flow_material_text_cannot_launder_unrelated_claims(self) -> None:
        unrelated = list(self.claims.values())
        for rendered in (
            "Guaranteed persistence path",
            "Charge the payment fee",
            "status becomes ACTIVE",
        ):
            with self.subTest(rendered=rendered):
                errors, _warnings = material_semantic_findings(
                    rendered, bound_claims=unrelated, context="flow element"
                )
                self.assertTrue(errors, rendered)

    def test_material_exact_values_and_objects_cannot_change(self) -> None:
        cases = (
            (
                "HTTP 200 is returned.",
                {"statement": "HTTP 400 is returned.", "claim_type": "endpoint-contract", "risk": "high"},
                "HTTP status",
            ),
            (
                "HTTP 302 is returned.",
                {"statement": "HTTP 301 is returned.", "claim_type": "endpoint-contract", "risk": "high"},
                "HTTP redirect status",
            ),
            (
                "status becomes ACTIVE",
                {"statement": "status becomes INACTIVE", "claim_type": "state-transition", "risk": "high"},
                "state literal",
            ),
            (
                "The operation persists the customer record.",
                {"statement": "The operation persists the audit record.", "claim_type": "data-write", "risk": "high"},
                "persisted object",
            ),
            (
                "The mapper maps customerId to partyId.",
                {"statement": "The mapper maps accountId to ledgerId.", "claim_type": "mapping", "risk": "normal"},
                "mapping pair",
            ),
            (
                "The mapper maps customer_id to party_id.",
                {"statement": "The mapper maps account_id to ledger_id.", "claim_type": "mapping", "risk": "normal"},
                "snake-case mapping pair",
            ),
            (
                "The amount is 20 USD.",
                {"statement": "The amount is 10 USD.", "claim_type": "field", "risk": "high"},
                "monetary literal",
            ),
            (
                "The amount is 20.",
                {"statement": "The amount is 10.", "claim_type": "field", "risk": "high"},
                "bare monetary literal",
            ),
            (
                "The timeout defaults to 60s.",
                {"statement": "The timeout defaults to 30s.", "claim_type": "configuration", "risk": "normal"},
                "default literal",
            ),
            (
                "The timeout has a default of 60s.",
                {"statement": "The timeout has a default of 30s.", "claim_type": "configuration", "risk": "normal"},
                "default-of literal",
            ),
            (
                "customerId is required.",
                {"statement": "accountId is required.", "claim_type": "validation", "risk": "normal"},
                "validation field",
            ),
            (
                "customer_id is required.",
                {"statement": "account_id is required.", "claim_type": "validation", "risk": "normal"},
                "snake-case validation field",
            ),
        )
        for rendered, claim, label in cases:
            with self.subTest(label=label):
                bound = [{"status": "Confirmed", **claim}]
                errors, _warnings = material_semantic_findings(
                    rendered, bound_claims=bound, context="Narrative"
                )
                self.assertTrue(errors, (label, errors))

    def test_same_exact_fact_allows_different_sentence_wording(self) -> None:
        claims = [
            {
                "statement": "The operation changes status to ACTIVE.",
                "claim_type": "state-transition",
                "status": "Confirmed",
                "risk": "high",
            }
        ]
        errors, _warnings = material_semantic_findings(
            "Once processing finishes, the handler sets status to ACTIVE.",
            bound_claims=claims,
            context="Narrative",
        )
        self.assertEqual([], errors)

    def test_table_is_not_used_as_narrative_summary_fallback(self) -> None:
        body = "## Inventory\n\n| Key | Value |\n|---|---|\n| A | B |\n"
        self.assertEqual("", first_narrative_section(body))

    def test_ba_plain_source_citation_and_obvious_secret_are_detected(self) -> None:
        self.assertIsNotNone(RAW_CITATION_RE.search("See src/Foo.java:12 for details."))
        self.assertIsNotNone(
            OBVIOUS_SECRET_RE.search("aws_secret_access_key='abcdefghijklmnopqrstuvwxyz0123456789ABCD'")
        )

    def test_explicit_unknown_material_semantics_do_not_need_affirmative_claim(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\nPersistence is Unknown from the available repository evidence.\n"
        )
        errors, _warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        self.assertEqual([], errors)

    def test_reference_prose_is_free_but_structured_row_is_exact(self) -> None:
        document = self.pack / "tech-pack" / "endpoints" / "endpoint-matrix.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: commit\nclaim_ids:\n"
            "  - CLM-receives-request\n---\n\n"
            "## Endpoint orientation\n\nThis paragraph can explain the endpoint naturally. "
            "It may contain more than one sentence.\n\n"
            "| Field | Meaning |\n|---|---|\n"
            "| customerId | Incoming identifier <!-- claims: CLM-receives-request --> |\n",
            encoding="utf-8",
        )
        errors, _warnings, _used = validate_v2_reference_document_claims(
            document, self.pack, self.claims
        )
        self.assertEqual([], errors)

    def test_reference_structured_row_without_marker_fails(self) -> None:
        document = self.pack / "tech-pack" / "endpoints" / "endpoint-matrix.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: commit\nclaim_ids:\n"
            "  - CLM-receives-request\n---\n\n"
            "| Field | Meaning |\n|---|---|\n| customerId | Incoming identifier |\n",
            encoding="utf-8",
        )
        errors, _warnings, _used = validate_v2_reference_document_claims(
            document, self.pack, self.claims
        )
        self.assertTrue(any("structured table row has no claim marker" in error for error in errors), errors)

    def test_claim_dump_is_a_diagnostic_not_a_truth_error(self) -> None:
        document = self.write_narrative(
            "## At a glance\n\n"
            "The handler receives customerId from the request.\n\n"
            "The handler returns a local result after validation.\n"
        )
        truth_errors, _truth_warnings, _used = validate_narrative_document_claims(
            document, self.pack, self.claims
        )
        diagnostics = readability_diagnostics(document, self.claims)
        self.assertEqual([], truth_errors)
        self.assertTrue(any("Claim-dump" in warning for warning in diagnostics), diagnostics)

    def test_manifest_version_defaults_only_for_legacy(self) -> None:
        self.assertEqual(2, pack_format_version(self.pack))
        (self.pack / "knowledge-manifest.yaml").write_text(
            'repository: "repo"\nsource_commit: "commit"\n', encoding="utf-8"
        )
        self.assertEqual(1, pack_format_version(self.pack))


class V2FlowTests(unittest.TestCase):
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
        (self.pack / "knowledge-manifest.yaml").write_text(
            'pack_format_version: 2\nrepository: "sample"\nsource_commit: "unknown"\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_unrelated_claim_artifacts(self) -> None:
        source = self.repo / "src" / "handler.py"
        excerpt_hash = text_sha256(canonical_excerpt(source.read_text(encoding="utf-8").splitlines(), 1, 1))
        claim = {
            "claim_id": "CLM-unrelated-step",
            "subject_ids": ["sample.behavior"],
            "claim_type": "behavior-step",
            "statement": "The handler begins the local implementation path.",
            "status": "Confirmed",
            "risk": "normal",
            "reasoning": None,
            "needed_evidence": None,
            "search_scope": None,
            "verification": {
                "mode": "contains-all",
                "tokens": ["handler"],
                "evidence_sources": ["src/handler.py:1"],
            },
            "render_terms": ["handler"],
            "evidence": [
                {
                    "source": "src/handler.py:1",
                    "source_kind": "implementation",
                    "relation": "supports",
                    "support_level": "direct",
                    "excerpt_sha256": excerpt_hash,
                    "rationale": "The executable source contains the handler symbol used by the claim.",
                }
            ],
        }
        ledger = {
            "schema_version": 1,
            "repository": "sample",
            "source_commit": "unknown",
            "claims": [claim],
        }
        audit = {
            "schema_version": 1,
            "repository": "sample",
            "source_commit": "unknown",
            "review": {
                "mode": "independent-subagent",
                "author_id": "author-context",
                "reviewer_id": "reviewer-context",
            },
            "audits": [
                {
                    "claim_id": claim["claim_id"],
                    "verdict": "Pass",
                    "reviewed_statement_sha256": text_sha256(claim["statement"]),
                    "reviewed_claim_sha256": claim_sha256(claim),
                    "reviewed_evidence_hashes": [excerpt_hash],
                    "entailment_notes": "The statement is limited to the observed local handler symbol and adds no outcome.",
                    "overstatement_check": "Pass",
                }
            ],
        }
        (self.pack / ".work" / "claim-ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        (self.pack / ".work" / "claim-audit.json").write_text(json.dumps(audit), encoding="utf-8")

    @staticmethod
    def model(perspective: str) -> dict[str, object]:
        tech = perspective == "technical"
        prefix = "T" if tech else "B"
        labels = ["Receive request", "Return local result"] if tech else ["Information submitted", "Outcome available"]
        types = ["trigger-adapter", "technical-outcome"] if tech else ["actor-event", "business-outcome"]
        nodes: list[dict[str, object]] = []
        for index, (label, semantic_type) in enumerate(zip(labels, types), start=1):
            node: dict[str, object] = {
                "node_id": f"{prefix}{index}",
                "semantic_type": semantic_type,
                "label": label,
                "claim_ids": [f"CLM-{perspective}-node-{index}"],
            }
            if tech:
                node["evidence"] = ["src/handler.py:1"]
            else:
                node["status"] = "Confirmed"
            nodes.append(node)
        value: dict[str, object] = {
            "behavior_id": "sample.behavior",
            "repository": "sample",
            "source_commit": "unknown",
            "perspective": perspective,
            "diagram_caption": "Implementation path" if tech else "Business journey",
            "diagram_claim_ids": [f"CLM-{perspective}-caption"],
            "nodes": nodes,
            "edges": [
                {
                    "from": f"{prefix}1",
                    "to": f"{prefix}2",
                    "condition": None,
                    "claim_ids": [f"CLM-{perspective}-edge"],
                }
            ],
        }
        if not tech:
            value["derived_from"] = {
                "behavior_ids": ["sample.behavior"],
                "business_rule_ids": [],
                "business_exception_ids": [],
            }
        return value

    def write_pair(self, shared_summary: bool = False) -> tuple[Path, Path]:
        tech_model = self.model("technical")
        ba_model = self.model("business")
        (self.pack / ".work" / "flow-models" / "sample.behavior.tech-flow.json").write_text(
            json.dumps(tech_model), encoding="utf-8"
        )
        (self.pack / ".work" / "flow-models" / "sample.behavior.ba-flow.json").write_text(
            json.dumps(ba_model), encoding="utf-8"
        )
        tech_summary = "The implementation receives a request and returns a local result."
        ba_summary = tech_summary if shared_summary else "Submitted information leads to an available outcome."
        tech = self.pack / "tech-pack" / "behaviors" / "sample.behavior.md"
        ba = self.pack / "ba-pack" / "behaviors" / "sample.behavior.md"
        tech.write_text(
            "---\nbehavior_id: sample.behavior\nrepository: sample\nsource_commit: unknown\n"
            "flow_perspective: technical\nsummary_perspective: technical\n"
            "tech_flow_model: ../../.work/flow-models/sample.behavior.tech-flow.json\n---\n\n"
            f"## At a glance\n\n{tech_summary}\n\n## Execution story\n\n"
            "```mermaid\nflowchart TD\nT1[\"Receive request\"] --> T2[\"Return local result\"]\n```\n",
            encoding="utf-8",
        )
        ba.write_text(
            "---\nbehavior_id: sample.behavior\nrepository: sample\nsource_commit: unknown\n"
            "flow_perspective: business\nsummary_perspective: business\n"
            "ba_flow_model: ../../.work/flow-models/sample.behavior.ba-flow.json\n---\n\n"
            f"## Scenario at a glance\n\n{ba_summary}\n\n## Business journey\n\n"
            "```mermaid\nflowchart TD\nB1[\"Information submitted\"] --> B2[\"Outcome available\"]\n```\n",
            encoding="utf-8",
        )
        return tech, ba

    def test_v2_document_summaries_need_not_copy_flow_captions(self) -> None:
        tech, ba = self.write_pair()
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertEqual([], errors)

    def test_v2_directly_reused_document_summary_is_rejected(self) -> None:
        tech, ba = self.write_pair(shared_summary=True)
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertTrue(any("directly reused" in error for error in errors), errors)

    def test_v2_near_similar_flow_is_reader_warning(self) -> None:
        tech, ba = self.write_pair()
        model_path = self.pack / ".work" / "flow-models" / "sample.behavior.ba-flow.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        model["nodes"][0]["label"] = "Receive business request"
        model["nodes"][1]["label"] = "Return business local result"
        model_path.write_text(json.dumps(model), encoding="utf-8")
        text = ba.read_text(encoding="utf-8")
        text = text.replace("Information submitted", "Receive business request")
        text = text.replace("Outcome available", "Return business local result")
        ba.write_text(text, encoding="utf-8")
        errors, warnings, metrics = validate_pair(tech, ba, self.repo)
        self.assertEqual([], errors)
        self.assertGreaterEqual(metrics["node_similarity"], 0.60)
        self.assertTrue(any("overlap" in warning or "near-identical" in warning for warning in warnings), warnings)

    def test_v2_implementation_terminology_is_reader_warning(self) -> None:
        tech, ba = self.write_pair()
        model_path = self.pack / ".work" / "flow-models" / "sample.behavior.ba-flow.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        model["nodes"][1]["label"] = "Lambda returns HTTP 400"
        model_path.write_text(json.dumps(model), encoding="utf-8")
        ba.write_text(
            ba.read_text(encoding="utf-8").replace("Outcome available", "Lambda returns HTTP 400"),
            encoding="utf-8",
        )
        errors, warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertEqual([], errors)
        self.assertTrue(any("implementation terminology" in warning for warning in warnings), warnings)

    def test_v2_directly_reused_long_paragraph_is_rejected(self) -> None:
        tech, ba = self.write_pair()
        shared = (
            "This deliberately long paragraph describes the same event, decision, information, "
            "visible result, and recovery boundary in exactly the same wording across both views, "
            "which indicates that one rendered narrative was reused instead of independently written."
        )
        for document in (tech, ba):
            document.write_text(
                document.read_text(encoding="utf-8") + "\n## Additional explanation\n\n" + shared + "\n",
                encoding="utf-8",
            )
        errors, _warnings, _metrics = validate_pair(tech, ba, self.repo)
        self.assertTrue(any("long Narrative paragraph" in error for error in errors), errors)

    def test_v2_flow_caption_node_and_condition_require_material_claims(self) -> None:
        self.write_unrelated_claim_artifacts()
        base = {
            "behavior_id": "sample.behavior",
            "repository": "sample",
            "source_commit": "unknown",
            "perspective": "technical",
            "diagram_caption": "Implementation path",
            "diagram_claim_ids": ["CLM-unrelated-step"],
            "nodes": [
                {
                    "node_id": "T1",
                    "semantic_type": "trigger-adapter",
                    "label": "Receive request",
                    "claim_ids": ["CLM-unrelated-step"],
                    "evidence": ["src/handler.py:1"],
                },
                {
                    "node_id": "T2",
                    "semantic_type": "technical-outcome",
                    "label": "Return local result",
                    "claim_ids": ["CLM-unrelated-step"],
                    "evidence": ["src/handler.py:1"],
                },
            ],
            "edges": [
                {
                    "from": "T1",
                    "to": "T2",
                    "condition": None,
                    "claim_ids": ["CLM-unrelated-step"],
                }
            ],
        }
        model_path = self.pack / ".work" / "flow-models" / "sample.behavior.tech-flow.json"
        cases = (
            ("caption", lambda model: model.update(diagram_caption="Guaranteed persistence")),
            ("node", lambda model: model["nodes"][1].update(label="Charge the payment fee")),
            ("condition", lambda model: model["edges"][0].update(condition="status becomes ACTIVE")),
        )
        for label, mutate in cases:
            with self.subTest(label=label):
                model = json.loads(json.dumps(base))
                mutate(model)
                model_path.write_text(json.dumps(model), encoding="utf-8")
                errors, _warnings, _claims = validate_claim_pack(
                    self.pack, self.repo, "sample", "unknown"
                )
                self.assertTrue(any("material" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
