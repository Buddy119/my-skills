#!/usr/bin/env python3
"""Regression tests for claim provenance and repository snapshot freshness."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_claim_ledger import (
    canonical_excerpt,
    claim_document_paths,
    claim_sha256,
    text_sha256,
    validate_claim_artifacts,
    validate_document_claims,
)
from validate_evidence_index import validate_evidence_index


class ClaimProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.pack = self.root / "pack"
        self.repo.mkdir()
        (self.pack / ".work").mkdir(parents=True)
        (self.pack / "tech-pack").mkdir(parents=True)
        self.source = self.repo / "handler.py"
        self.source.write_text(
            "def handler(event):\n"
            "    if not event.get('customerId'):\n"
            "        return {'statusCode': 400}\n"
            "    return {'statusCode': 200}\n",
            encoding="utf-8",
        )
        lines = self.source.read_text(encoding="utf-8").splitlines()
        self.excerpt_hash = text_sha256(canonical_excerpt(lines, 1, 4))
        self.claim = {
            "claim_id": "CLM-handler-returns-status",
            "subject_ids": ["repo.handle-request"],
            "claim_type": "behavior-step",
            "statement": "The function returns the numeric literal 400 when customerId is falsey and 200 otherwise.",
            "status": "Confirmed",
            "risk": "normal",
            "reasoning": None,
            "needed_evidence": None,
            "search_scope": None,
            "verification": {
                "mode": "contains-all",
                "tokens": ["customerId", "400"],
                "evidence_sources": ["handler.py:1-4"],
            },
            "render_terms": ["400", "200", "customerId"],
            "evidence": [
                {
                    "source": "handler.py:1-4",
                    "source_kind": "implementation",
                    "relation": "supports",
                    "support_level": "direct",
                    "excerpt_sha256": self.excerpt_hash,
                    "rationale": "The branch and both return literals appear in the selected executable lines.",
                }
            ],
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def artifacts(self, claim: dict[str, object]) -> tuple[Path, Path]:
        ledger = {
            "schema_version": 1,
            "repository": "repo",
            "source_commit": "unknown",
            "claims": [claim],
        }
        evidence_hashes = [
            item["excerpt_sha256"]
            for item in claim.get("evidence", [])
            if isinstance(item, dict) and isinstance(item.get("excerpt_sha256"), str)
        ]
        audit = {
            "schema_version": 1,
            "repository": "repo",
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
                    "reviewed_statement_sha256": text_sha256(str(claim["statement"])),
                    "reviewed_claim_sha256": claim_sha256(claim),
                    "reviewed_evidence_hashes": evidence_hashes,
                    "entailment_notes": "The statement is limited to the observed branch and return values.",
                    "overstatement_check": "Pass",
                }
            ],
        }
        ledger_path = self.pack / ".work" / "claim-ledger.json"
        audit_path = self.pack / ".work" / "claim-audit.json"
        ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        return ledger_path, audit_path

    def validate(self, claim: dict[str, object]) -> list[str]:
        ledger, audit = self.artifacts(claim)
        errors, _warnings, _claims = validate_claim_artifacts(
            ledger, audit, self.repo, "repo", "unknown"
        )
        return errors

    def test_valid_confirmed_claim_and_marked_document_pass(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(
            ledger, audit, self.repo, "repo", "unknown"
        )
        self.assertEqual([], errors)
        document = self.pack / "tech-pack" / "repository-overview.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Technical repository overview\n\n## Observable responsibility\n\n"
            "The function returns the numeric literal 400 when customerId is falsey and 200 otherwise. "
            "<!-- claims: CLM-handler-returns-status -->\n",
            encoding="utf-8",
        )
        document_errors, _document_warnings, used = validate_document_claims(
            document, self.pack, claims
        )
        self.assertEqual([], document_errors)
        self.assertEqual({"CLM-handler-returns-status"}, used)

    def test_confirmed_without_direct_support_fails(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["evidence"][0]["support_level"] = "indirect"
        errors = self.validate(claim)
        self.assertTrue(any("requires direct supporting evidence" in error for error in errors), errors)

    def test_stale_excerpt_hash_fails(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["evidence"][0]["excerpt_sha256"] = "sha256:" + "0" * 64
        errors = self.validate(claim)
        self.assertTrue(any("excerpt hash is stale" in error for error in errors), errors)

    def test_structured_claim_with_unrelated_valid_citation_fails_token_check(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["claim_type"] = "validation"
        claim["verification"] = {
            "mode": "contains-all",
            "tokens": ["CUSTOMER_ID_REQUIRED"],
            "evidence_sources": ["handler.py:1-4"],
        }
        errors = self.validate(claim)
        self.assertTrue(any("token(s) absent from evidence" in error for error in errors), errors)

    def test_inferred_without_reasoning_fails(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["status"] = "Inferred"
        claim["evidence"][0]["support_level"] = "indirect"
        claim["reasoning"] = None
        claim["needed_evidence"] = "An executed contract test."
        errors = self.validate(claim)
        self.assertTrue(any("requires reasoning" in error for error in errors), errors)

    def test_affirmative_unknown_claim_fails(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["statement"] = "The caller receives a standard error envelope."
        claim["status"] = "Unknown"
        claim["reasoning"] = "Serialization is unavailable."
        claim["needed_evidence"] = "The shared error serializer."
        claim["evidence"] = []
        claim["verification"] = {"mode": "manual", "tokens": [], "evidence_sources": []}
        errors = self.validate(claim)
        self.assertTrue(any("must explicitly express uncertainty" in error for error in errors), errors)

    def test_compound_unknown_claim_fails(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["statement"] = "The actor and business outcome are Unknown."
        claim["status"] = "Unknown"
        claim["reasoning"] = "The implementation exposes no business context."
        claim["needed_evidence"] = "Upstream requirements and downstream consumer documentation."
        claim["evidence"] = []
        claim["verification"] = {"mode": "manual", "tokens": [], "evidence_sources": []}
        claim["render_terms"] = ["actor", "business outcome"]
        errors = self.validate(claim)
        self.assertTrue(any("appears compound" in error for error in errors), errors)

    def test_conflict_without_opposing_evidence_fails(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["status"] = "Conflicting"
        claim["reasoning"] = "The published schema may differ from executable behavior."
        claim["needed_evidence"] = "A current consumer contract."
        errors = self.validate(claim)
        self.assertTrue(any("requires supporting and contradicting" in error for error in errors), errors)

    def test_high_risk_confirmed_claim_requires_independent_sources(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["statement"] = "The operation persists the customer record."
        claim["risk"] = "high"
        errors = self.validate(claim)
        self.assertTrue(any("two distinct physical files" in error for error in errors), errors)

    def test_multisentence_claim_is_rejected(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["statement"] = "The function reads customerId. It encrypts the value before returning."
        claim["verification"]["tokens"] = ["customerId"]
        errors = self.validate(claim)
        self.assertTrue(any("multiple sentences" in error for error in errors), errors)

    def test_single_sentence_unsupported_encryption_semantics_are_rejected(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["statement"] = "The function encrypts customerId before returning 400."
        claim["verification"]["tokens"] = ["customerId", "400"]
        errors = self.validate(claim)
        self.assertTrue(any("encryption/redaction semantics absent" in error for error in errors), errors)

    def test_confirmed_other_claim_type_is_rejected(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["claim_type"] = "other"
        errors = self.validate(claim)
        self.assertTrue(any("other is allowed only for Unknown" in error for error in errors), errors)

    def test_verification_token_must_appear_in_statement(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["verification"]["tokens"] = ["event.get"]
        errors = self.validate(claim)
        self.assertTrue(any("absent from claim statement" in error for error in errors), errors)

    def test_same_physical_file_cannot_satisfy_independent_sources(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["statement"] = "The operation persists the customer record."
        claim["risk"] = "high"
        duplicate = copy.deepcopy(claim["evidence"][0])
        duplicate["source_kind"] = "test"
        claim["evidence"].append(duplicate)
        errors = self.validate(claim)
        self.assertTrue(any("same physical evidence range" in error for error in errors), errors)
        self.assertTrue(any("two distinct physical files" in error for error in errors), errors)

    def test_confirmed_claim_with_contradiction_is_rejected(self) -> None:
        claim = copy.deepcopy(self.claim)
        lines = self.source.read_text(encoding="utf-8").splitlines()
        claim["evidence"].append(
            {
                "source": "handler.py:4",
                "source_kind": "implementation",
                "relation": "contradicts",
                "support_level": "direct",
                "excerpt_sha256": text_sha256(canonical_excerpt(lines, 4, 4)),
                "rationale": "The other branch returns 200 and therefore contradicts an unconditional 400 result.",
            }
        )
        errors = self.validate(claim)
        self.assertTrue(any("cannot carry contradicting evidence" in error for error in errors), errors)

    def test_unmarked_factual_paragraph_fails(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertEqual([], errors)
        document = self.pack / "tech-pack" / "repository-overview.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Technical repository overview\n\nThe function always returns a response.\n",
            encoding="utf-8",
        )
        document_errors, _warnings, _used = validate_document_claims(document, self.pack, claims)
        self.assertTrue(any("has no claim marker" in error for error in document_errors), document_errors)

    def test_unrelated_claim_marker_does_not_validate_template_fact(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertEqual([], errors)
        document = self.pack / "tech-pack" / "repository-overview.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Technical repository overview\n\n"
            "| Scenario | HTTP status |\n|---|---|\n"
            "| Not authenticated | 401 <!-- claims: CLM-handler-returns-status --> |\n",
            encoding="utf-8",
        )
        document_errors, _warnings, _used = validate_document_claims(document, self.pack, claims)
        self.assertTrue(any("does not contain a render term" in error for error in document_errors), document_errors)

    def test_real_claim_cannot_launder_an_appended_sentence(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertEqual([], errors)
        document = self.pack / "tech-pack" / "repository-overview.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Technical repository overview\n\n"
            "The function returns 400 for falsey customerId. Customer data is encrypted for seven years. "
            "<!-- claims: CLM-handler-returns-status -->\n",
            encoding="utf-8",
        )
        document_errors, _warnings, _used = validate_document_claims(document, self.pack, claims)
        self.assertTrue(any("multiple sentences" in error for error in document_errors), document_errors)

    def test_real_claim_cannot_launder_encryption_in_one_sentence(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertEqual([], errors)
        document = self.pack / "tech-pack" / "repository-overview.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Technical repository overview\n\n"
            "The function returns 400 for falsey customerId and encrypts customer data. "
            "<!-- claims: CLM-handler-returns-status -->\n",
            encoding="utf-8",
        )
        document_errors, _warnings, _used = validate_document_claims(document, self.pack, claims)
        self.assertTrue(any("adds encryption/redaction semantics" in error for error in document_errors), document_errors)

    def test_unrelated_unknown_does_not_disable_semantic_checks(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertEqual([], errors)
        document = self.pack / "tech-pack" / "repository-overview.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Technical repository overview\n\n"
            "The wider schema is Unknown, and customerId is encrypted before returning 400. "
            "<!-- claims: CLM-handler-returns-status -->\n",
            encoding="utf-8",
        )
        document_errors, _warnings, _used = validate_document_claims(document, self.pack, claims)
        self.assertTrue(any("adds encryption/redaction semantics" in error for error in document_errors), document_errors)

    def test_unrecognized_factual_heading_requires_a_claim(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertEqual([], errors)
        document = self.pack / "tech-pack" / "repository-overview.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Technical repository overview\n\n## All customer records are permanently deleted\n\n"
            "The function returns 400 for falsey customerId. <!-- claims: CLM-handler-returns-status -->\n",
            encoding="utf-8",
        )
        document_errors, _warnings, _used = validate_document_claims(document, self.pack, claims)
        self.assertTrue(any("factual heading has no claim marker" in error for error in document_errors), document_errors)

    def test_field_row_cannot_launder_type_requiredness_or_ownership(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        errors, _warnings, claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertEqual([], errors)
        directory = self.pack / "tech-pack" / "fields"
        directory.mkdir(parents=True)
        document = directory / "field-catalog.md"
        document.write_text(
            "---\nrepository: repo\nsource_commit: unknown\n"
            "claim_ids:\n  - CLM-handler-returns-status\n---\n\n"
            "# Field catalog\n\n## Boundary and significant fields\n\n"
            "| Field ID | Boundary ID/type | Field path | Meaning | Type/format | Required | Nullable | Source/default | Status | Evidence |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            "| FIELD-customer-id | handler input | customerId | CRM owner | UUID | Always required | Never nullable | Master CRM record | Confirmed | handler.py <!-- claims: CLM-handler-returns-status --> |\n",
            encoding="utf-8",
        )
        document_errors, _warnings, _used = validate_document_claims(document, self.pack, claims)
        joined = "\n".join(document_errors)
        self.assertIn("Type/format value is not asserted", joined)
        self.assertIn("Meaning adds a field semantic", joined)
        self.assertIn("Required adds a field semantic", joined)
        self.assertIn("Nullable adds a field semantic", joined)
        self.assertIn("Source/default adds a field semantic", joined)

    def test_evidence_index_detects_added_candidate_file(self) -> None:
        index_path = self.pack / ".work" / "evidence-index.json"
        builder = Path(__file__).with_name("build_evidence_index.py")
        subprocess.run(
            [
                sys.executable,
                "-E",
                "-S",
                "-B",
                "-X",
                "utf8",
                str(builder),
                "--repo",
                str(self.repo),
                "--output",
                str(index_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        errors, _warnings, _index = validate_evidence_index(index_path, self.repo, "repo", "unknown")
        self.assertEqual([], errors)
        (self.repo / "template.yaml").write_text("Resources: {}\n", encoding="utf-8")
        errors, _warnings, _index = validate_evidence_index(index_path, self.repo, "repo", "unknown")
        self.assertTrue(any("added after evidence indexing" in error for error in errors), errors)

    def test_root_knowledge_and_coverage_documents_are_claim_bearing(self) -> None:
        (self.pack / "knowledge-manifest.yaml").write_text("repository: repo\n", encoding="utf-8")
        knowledge_map = self.pack / "knowledge-map.md"
        knowledge_map.write_text("---\nrepository: repo\n---\n", encoding="utf-8")
        coverage_report = self.pack / "coverage-report.md"
        coverage_report.write_text("---\nrepository: repo\n---\n", encoding="utf-8")
        paths = claim_document_paths(self.pack)
        self.assertIn(knowledge_map, paths)
        self.assertIn(coverage_report, paths)

    def test_audit_preparer_never_auto_passes_claims(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        audit.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": "repo",
                    "source_commit": "unknown",
                    "review": {
                        "mode": "ReviewRequired",
                        "author_id": "REPLACE_AUTHOR_CONTEXT",
                        "reviewer_id": "REPLACE_INDEPENDENT_REVIEWER_CONTEXT",
                    },
                    "audits": [],
                    "scaffold_state": "SCAFFOLD_ONLY_REMOVE_AFTER_REVIEW",
                }
            ),
            encoding="utf-8",
        )
        preparer = Path(__file__).with_name("prepare_claim_audit.py")
        subprocess.run(
            [
                sys.executable,
                "-E",
                "-S",
                "-B",
                "-X",
                "utf8",
                str(preparer),
                "--ledger",
                str(ledger),
                "--output",
                str(audit),
                "--repo",
                str(self.repo),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        prepared = json.loads(audit.read_text(encoding="utf-8"))
        self.assertEqual("ReviewRequired", prepared["audits"][0]["verdict"])
        self.assertEqual("ReviewRequired", prepared["review"]["mode"])
        errors, _warnings, _claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertTrue(any("invalid verdict" in error for error in errors), errors)

    def test_audit_author_and_reviewer_must_differ(self) -> None:
        ledger, audit = self.artifacts(self.claim)
        data = json.loads(audit.read_text(encoding="utf-8"))
        data["review"]["reviewer_id"] = data["review"]["author_id"]
        audit.write_text(json.dumps(data), encoding="utf-8")
        errors, _warnings, _claims = validate_claim_artifacts(ledger, audit, self.repo)
        self.assertTrue(any("must be different contexts" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
