from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from finalization_review import (  # noqa: E402
    FinalizationReviewError,
    evaluate_reviews,
    initialize_review_baseline,
    load_review_schema,
    persist_review_sidecar,
    persisted_review_status,
    receipt_review_summary,
    record_review,
    review_content_sha256,
    sha256_file,
)


class FinalizationReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repository"
        self.repo.mkdir()
        (self.repo / "src").mkdir()
        (self.repo / "src" / "Handler.java").write_text(
            "class Handler {\n  void handle() {}\n}\n", encoding="utf-8"
        )
        self.candidate = self.root / "candidate"
        (self.candidate / ".work").mkdir(parents=True)
        (self.candidate / ".work" / "repository-synthesis.md").write_text(
            "# Synthesis\n", encoding="utf-8"
        )
        (self.candidate / "tech-pack" / "behaviors").mkdir(parents=True)
        (self.candidate / "tech-pack" / "repository-overview.md").write_text(
            "# Repository overview\n", encoding="utf-8"
        )
        (self.candidate / "tech-pack" / "behaviors" / "repo.behavior.md").write_text(
            "# Behavior\n", encoding="utf-8"
        )
        self.tx = self.root / "transaction"
        self.tx.mkdir()
        initialize_review_baseline(self.tx, self.candidate)
        self.schema = load_review_schema()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def review_input(
        self,
        review_type: str,
        *,
        reviewed_category: str | None = None,
        outcome: str = "passed",
        corrections: list[dict] | None = None,
    ) -> dict:
        categories = self.schema["reviews"][review_type]["categories"]
        reviewed = reviewed_category or categories[0]
        coverage = [
            {
                "category": category,
                "status": "reviewed" if category == reviewed else "not-applicable",
                "reason": None if category == reviewed else "Not observed in this fixture.",
            }
            for category in categories
        ]
        return {
            "overall_conclusion": (
                "passed-with-corrections" if outcome == "corrected" else "passed"
            ),
            "summary": f"Completed the {review_type} review.",
            "coverage": coverage,
            "items": [
                {
                    "sample_id": review_type.replace("-", "_") + "_001",
                    "category": reviewed,
                    "subject": {
                        "path": "tech-pack/repository-overview.md",
                        "identity": "repository-overview",
                    },
                    "question": "Does the sampled statement match its intended review concern?",
                    "outcome": outcome,
                    "conclusion": "The sampled item satisfies the recorded review concern.",
                    "findings": [],
                    "corrections": corrections or [],
                    "evidence": (
                        [
                            {
                                "path": "src/Handler.java",
                                "start_line": 1,
                                "end_line": 2,
                            }
                        ]
                        if review_type == "semantic-fact"
                        else []
                    ),
                }
            ],
            "warning_dispositions": [],
        }

    def record(self, review_type: str, payload: dict, mechanical: dict | None = None) -> dict:
        return record_review(
            transaction_dir=self.tx,
            candidate=self.candidate,
            repository=self.repo,
            transaction_id="tx-1",
            generation_id="generation-1",
            source_commit="unknown",
            review_type=review_type,
            input_payload=payload,
            mechanical_summary=mechanical,
        )

    def evaluate(self) -> dict:
        return evaluate_reviews(
            transaction_dir=self.tx,
            candidate=self.candidate,
            transaction_id="tx-1",
            generation_id="generation-1",
            repository=self.repo,
            source_commit="unknown",
        )

    def test_three_reviews_bind_one_candidate_and_become_stale_after_change(self) -> None:
        mechanical = {
            "result": "passed",
            "primary_error_count": 0,
            "skipped_group_count": 0,
            "warning_count": 0,
            "artifact_manifest_status": "valid",
        }
        self.record("mechanical", self.review_input("mechanical"), mechanical)
        self.record("semantic-fact", self.review_input("semantic-fact"))
        self.record("reader", self.review_input("reader"))
        evaluation = self.evaluate()
        self.assertEqual(
            evaluation["statuses"],
            {"mechanical": "current", "semantic-fact": "current", "reader": "current"},
        )
        self.assertEqual(evaluation["counts"]["unresolved"], 0)
        summary = receipt_review_summary(evaluation)
        self.assertEqual(summary["mechanical_pass_status"], "passed")

        overview = self.candidate / "tech-pack" / "repository-overview.md"
        overview.write_text("# Changed overview\n", encoding="utf-8")
        stale = self.evaluate()
        self.assertEqual(
            stale["statuses"],
            {"mechanical": "stale", "semantic-fact": "stale", "reader": "stale"},
        )
        self.assertEqual(stale["counts"]["stale"], 3)

    def test_coverage_and_correction_rules_are_mechanical(self) -> None:
        payload = self.review_input("reader")
        payload["coverage"].pop()
        with self.assertRaisesRegex(FinalizationReviewError, "missing coverage categories"):
            self.record("reader", payload)

        payload = self.review_input(
            "reader",
            outcome="corrected",
            corrections=[
                {
                    "path": "tech-pack/repository-overview.md",
                    "summary": "Clarified the repository role.",
                }
            ],
        )
        payload["items"][0]["findings"] = ["The repository role was unclear."]
        with self.assertRaisesRegex(FinalizationReviewError, "did not change"):
            self.record("reader", payload)

        overview = self.candidate / "tech-pack" / "repository-overview.md"
        overview.write_text("# Repository overview\n\nClarified role.\n", encoding="utf-8")
        ledger = self.record("reader", payload)
        correction = ledger["reviews"]["reader"]["items"][0]["corrections"][0]
        self.assertNotEqual(correction["before_sha256"], correction["after_sha256"])

    def test_persisted_sidecar_is_bound_to_receipt_and_published_content(self) -> None:
        mechanical = {
            "result": "passed",
            "primary_error_count": 0,
            "skipped_group_count": 0,
            "warning_count": 0,
            "artifact_manifest_status": "valid",
        }
        self.record("mechanical", self.review_input("mechanical"), mechanical)
        self.record("semantic-fact", self.review_input("semantic-fact"))
        self.record("reader", self.review_input("reader"))
        evaluation = self.evaluate()
        output = self.root / "output"
        output.mkdir()
        for source in self.candidate.rglob("*"):
            relative = source.relative_to(self.candidate)
            destination = output / relative
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
        sidecar, sidecar_hash = persist_review_sidecar(
            transaction_dir=self.tx,
            output=output,
            sequence=3,
            generation_id="generation-1",
        )
        receipt = {
            **receipt_review_summary(evaluation),
            "finalization_review_record": sidecar.relative_to(output).as_posix(),
            "finalization_review_record_sha256": sidecar_hash,
            "generation_id": "generation-1",
            "transaction_id": "tx-1",
        }
        status = persisted_review_status(
            output=output,
            receipt=receipt,
            repository=str(self.repo),
            source_commit="unknown",
        )
        self.assertEqual(status["status"], "current")
        sidecar.write_text("{}\n", encoding="utf-8")
        invalid = persisted_review_status(
            output=output,
            receipt=receipt,
            repository=str(self.repo),
            source_commit="unknown",
        )
        self.assertEqual(invalid["status"], "invalid")
        self.assertNotEqual(sha256_file(sidecar), sidecar_hash)

    def test_not_applicable_evidence_unresolved_and_warning_gates(self) -> None:
        payload = self.review_input("reader")
        payload["coverage"][1]["reason"] = ""
        with self.assertRaisesRegex(FinalizationReviewError, "not-applicable reason"):
            self.record("reader", payload)

        fact = self.review_input("semantic-fact")
        fact["items"][0]["evidence"][0]["end_line"] = 99
        with self.assertRaisesRegex(FinalizationReviewError, "exceeds file length"):
            self.record("semantic-fact", fact)

        reader = self.review_input("reader")
        reader["overall_conclusion"] = "blocked"
        reader["items"][0]["outcome"] = "unresolved"
        reader["items"][0]["findings"] = ["The overview does not explain state risk."]
        self.record("reader", reader)
        blocked = self.evaluate()
        self.assertEqual(blocked["statuses"]["reader"], "blocked")
        self.assertEqual(blocked["counts"]["unresolved"], 1)

        mechanical = {
            "result": "passed",
            "primary_error_count": 0,
            "skipped_group_count": 0,
            "warning_count": 1,
            "warnings": ["Review the word pending in context."],
            "artifact_manifest_status": "valid",
        }
        with self.assertRaisesRegex(FinalizationReviewError, "adjudicate"):
            self.record("mechanical", self.review_input("mechanical"), mechanical)
        mechanical_input = self.review_input("mechanical")
        mechanical_input["warning_dispositions"] = [
            {
                "warning": "Review the word pending in context.",
                "decision": "retained",
                "reason": "It describes a customer approval state.",
            }
        ]
        self.record("mechanical", mechanical_input, mechanical)


if __name__ == "__main__":
    unittest.main()
