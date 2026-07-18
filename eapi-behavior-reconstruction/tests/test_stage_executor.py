from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = SKILL_ROOT / "scripts" / "stage_executor.py"


def load_executor_module():
    specification = importlib.util.spec_from_file_location("stage_executor", EXECUTOR)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class StageExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "sample-repo"
        self.repo.mkdir()
        self.output = self.root / "knowledge"
        self.run_cmd("init", "--repo", str(self.repo), "--output", str(self.output))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cmd(self, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(EXECUTOR), *arguments, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            expected,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def begin(self, stage: str) -> tuple[str, Path]:
        result = self.run_cmd("begin", "--output", str(self.output), "--stage", stage)
        payload = json.loads(result.stdout)
        return payload["transaction_id"], Path(payload["candidate"])

    def test_partial_candidate_does_not_advance_formal_state(self) -> None:
        transaction, candidate = self.begin("inventory")
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertIn("evidence-index.json", " ".join(payload["errors"]))
        formal = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "inventory"', formal)
        self.assertIn('stage_status: "failed"', formal)
        self.assertTrue(candidate.is_dir())
        receipts = list((self.output / ".work" / "execution" / "receipts").glob("*-inventory.json"))
        self.assertEqual(receipts, [])

    def test_inventory_commit_creates_receipt_and_advances_once(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text("{}\n", encoding="utf-8")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)
        status = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(status["current_stage"], "tracing")
        self.assertEqual(status["stage_status"], "pending")
        self.assertIsNone(status["active_transaction"])
        receipts = list((self.output / ".work" / "execution" / "receipts").glob("*-inventory.json"))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
        self.assertEqual(receipt["result"], "committed")
        self.assertEqual(receipt["stage"], "inventory")
        self.assertFalse(candidate.exists())

    def test_second_begin_is_rejected_until_active_transaction_finishes(self) -> None:
        transaction, _candidate = self.begin("inventory")
        self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "inventory",
            expected=2,
        )
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)
        formal = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('stage_status: "pending"', formal)
        self.assertIn("active_transaction: null", formal)
        self.assertFalse((self.output / ".work" / "execution" / "active.lock").exists())

    def test_executor_does_not_modify_writable_skill_scripts(self) -> None:
        protected = [
            EXECUTOR,
            SKILL_ROOT / "scripts" / "validate_analysis_state.py",
            SKILL_ROOT / "scripts" / "build_evidence_index.py",
        ]
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected
        }
        transaction, _candidate = self.begin("inventory")
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected
        }
        self.assertEqual(before, after)

    def test_executor_initializes_output_from_read_only_skill_copy(self) -> None:
        read_only_skill = self.root / "read-only-skill"
        shutil.copytree(
            SKILL_ROOT,
            read_only_skill,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        try:
            for path in sorted(read_only_skill.rglob("*"), reverse=True):
                path.chmod(0o555 if path.is_dir() else 0o444)
            read_only_skill.chmod(0o555)
            output = self.root / "read-only-output"
            result = subprocess.run(
                [
                    sys.executable,
                    str(read_only_skill / "scripts" / "stage_executor.py"),
                    "init",
                    "--repo",
                    str(self.repo),
                    "--output",
                    str(output),
                    "--json",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((output / ".work" / "analysis-state.yaml").is_file())
        finally:
            read_only_skill.chmod(0o755)
            for path in read_only_skill.rglob("*"):
                path.chmod(0o755 if path.is_dir() else 0o644)

    def test_mark_behavior_requires_main_transaction_and_existing_dossier(self) -> None:
        transaction, candidate = self.begin("inventory")
        state = candidate / ".work" / "analysis-state.yaml"
        state.write_text(
            state.read_text(encoding="utf-8").replace(
                "behaviors: []",
                'behaviors:\n  - behavior_id: "sample-repo.handle-request"\n'
                '    status: "discovered"\n    dossier: null\n    notes: null',
            ),
            encoding="utf-8",
        )
        catalog = candidate / ".work" / "behavior-catalog.yaml"
        catalog.write_text(
            catalog.read_text(encoding="utf-8").replace(
                "behaviors: []",
                'behaviors:\n  - behavior_id: "sample-repo.handle-request"\n'
                '    status: "documented"\n    document: "behaviors/sample-repo.handle-request.md"',
            ),
            encoding="utf-8",
        )
        (candidate / ".work" / "evidence-index.json").write_text("{}\n", encoding="utf-8")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, tracing_candidate = self.begin("tracing")
        dossier = tracing_candidate / ".work" / "behavior-dossiers" / "sample-repo.handle-request.md"
        dossier.write_text('behavior_id: "sample-repo.handle-request"\n', encoding="utf-8")
        self.run_cmd(
            "mark-behavior",
            "--output",
            str(self.output),
            "--transaction",
            tracing,
            "--behavior-id",
            "sample-repo.handle-request",
            "--status",
            "understood",
            "--dossier",
            "behavior-dossiers/sample-repo.handle-request.md",
        )
        candidate_state = (tracing_candidate / ".work" / "analysis-state.yaml").read_text(
            encoding="utf-8"
        )
        formal_state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('status: "understood"', candidate_state)
        self.assertIn('status: "discovered"', formal_state)
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)
        final_state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "synthesis"', final_state)
        self.assertIn('status: "understood"', final_state)

    def test_changed_files_are_archived_with_checksums(self) -> None:
        original_register = (self.output / ".work" / "repository-register.md").read_text(
            encoding="utf-8"
        )
        transaction, candidate = self.begin("inventory")
        register = candidate / ".work" / "repository-register.md"
        register.write_text(register.read_text(encoding="utf-8") + "\nInventory note.\n", encoding="utf-8")
        (candidate / ".work" / "evidence-index.json").write_text("{}\n", encoding="utf-8")
        result = self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)
        receipt_path = Path(json.loads(result.stdout)["receipt"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        archive = Path(receipt["archive"])
        archived_register = archive / ".work" / "repository-register.md"
        self.assertEqual(archived_register.read_text(encoding="utf-8"), original_register)
        archive_manifest = json.loads((archive / "archive-manifest.json").read_text(encoding="utf-8"))
        self.assertIn(".work/repository-register.md", archive_manifest["files"])
        status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertTrue(status["archive_audits"])
        self.assertTrue(all(item["valid"] for item in status["archive_audits"]))

    def test_legacy_ba_directory_is_archived_as_one_verified_tree(self) -> None:
        legacy = self.output / "ba-pack" / "behaviors"
        legacy.mkdir(parents=True)
        (legacy / "old.md").write_text("legacy\n", encoding="utf-8")
        transaction, candidate = self.begin("inventory")
        candidate_legacy = candidate / "ba-pack" / "behaviors"
        (candidate_legacy / "old.md").unlink()
        candidate_legacy.rmdir()
        (candidate / ".work" / "evidence-index.json").write_text("{}\n", encoding="utf-8")
        result = self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)
        receipt = json.loads(Path(json.loads(result.stdout)["receipt"]).read_text(encoding="utf-8"))
        legacy_archive = Path(receipt["legacy_ba_archive"])
        self.assertEqual((legacy_archive / "behaviors" / "old.md").read_text(), "legacy\n")
        self.assertFalse((self.output / "ba-pack" / "behaviors").exists())
        status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertTrue(status["legacy_archive_audits"])
        self.assertTrue(all(item["valid"] for item in status["legacy_archive_audits"]))
        self.assertEqual(status["temporary_paths"], [])

    def test_business_model_begin_removes_legacy_ba_only_from_candidate(self) -> None:
        legacy = self.output / "ba-pack" / "behaviors"
        legacy.mkdir(parents=True)
        (legacy / "old.md").write_text("legacy\n", encoding="utf-8")
        executor = load_executor_module()
        state = self.output / ".work" / "analysis-state.yaml"
        text = state.read_text(encoding="utf-8")
        text = executor.set_scalar(text, "phase", "publishing")
        text = executor.set_scalar(text, "current_stage", "business-model")
        text = executor.set_scalar(text, "stage_status", "pending")
        text = executor.set_scalar(text, "last_committed_stage", "api-contract-publication")
        text = executor.set_scalar(text, "publication_status", "in-progress")
        state.write_text(text, encoding="utf-8")
        transaction, candidate = self.begin("business-model")
        self.assertTrue(legacy.is_dir())
        self.assertFalse((candidate / "ba-pack" / "behaviors").exists())
        transaction_record = json.loads(
            (
                self.output
                / ".work"
                / "execution"
                / "transactions"
                / transaction
                / "transaction.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(transaction_record["automatic_actions"])
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)
        self.assertTrue(legacy.is_dir())

    def test_legacy_resume_does_not_trust_completed_without_receipt(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        text = state.read_text(encoding="utf-8")
        for key in (
            "workflow_schema_version",
            "repository_path",
            "current_stage",
            "stage_status",
            "active_transaction",
            "last_committed_stage",
        ):
            text = "\n".join(
                line for line in text.splitlines() if not line.startswith(key + ":")
            ) + "\n"
        text = text.replace('phase: "inventory"', 'phase: "completed"')
        text = text.replace('publication_status: "pending"', 'publication_status: "complete"')
        state.write_text(text, encoding="utf-8")
        result = self.run_cmd("resume", "--repo", str(self.repo), "--state", str(state))
        payload = json.loads(result.stdout)
        self.assertNotEqual(payload["current_stage"], "completed")
        upgraded = state.read_text(encoding="utf-8")
        self.assertIn('workflow_schema_version: "2"', upgraded)
        self.assertNotIn('current_stage: "completed"', upgraded)

    def test_recover_rolls_back_an_interrupted_promotion(self) -> None:
        transaction, _candidate = self.begin("inventory")
        partial = self.output / "partial-publication.md"
        partial.write_text("partial\n", encoding="utf-8")
        tx_dir = self.output / ".work" / "execution" / "transactions" / transaction
        journal_path = tx_dir / "promotion-journal.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal.update(
            {
                "phase": "promoting",
                "archive": None,
                "operations": [{"kind": "add", "path": "partial-publication.md"}],
                "completed_operations": [
                    {"kind": "add", "path": "partial-publication.md"}
                ],
            }
        )
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
        result = self.run_cmd("recover", "--output", str(self.output))
        self.assertEqual(json.loads(result.stdout)["result"], "rolled-back")
        self.assertFalse(partial.exists())
        state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "inventory"', state)
        self.assertIn('stage_status: "failed"', state)
        self.assertIn(f'active_transaction: "{transaction}"', state)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_completed_state_requires_a_finalization_receipt(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        module = load_executor_module()
        text = state.read_text(encoding="utf-8")
        for key, value in (
            ("phase", "completed"),
            ("current_stage", "completed"),
            ("stage_status", "committed"),
            ("active_transaction", None),
            ("last_committed_stage", "finalization"),
            ("synthesis_status", "complete"),
            ("business_model_status", "blocked"),
            ("publication_status", "complete"),
        ):
            text = module.set_scalar(text, key, value)
        state.write_text(text, encoding="utf-8")
        validator = SKILL_ROOT / "scripts" / "validate_analysis_state.py"
        command = [
            sys.executable,
            str(validator),
            str(state),
            "--repo",
            str(self.repo),
            "--catalog",
            str(self.output / ".work" / "behavior-catalog.yaml"),
            "--dossiers-dir",
            str(self.output / ".work" / "behavior-dossiers"),
        ]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("finalization receipt", missing.stdout)
        receipt = self.output / ".work" / "execution" / "receipts" / "999-finalization.json"
        receipt.write_text(
            json.dumps({"stage": "finalization", "result": "committed"}),
            encoding="utf-8",
        )
        valid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, msg=valid.stdout + valid.stderr)

    def test_status_reports_completed_state_without_receipt_as_corrupt(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        module = load_executor_module()
        text = state.read_text(encoding="utf-8")
        text = module.set_scalar(text, "phase", "completed")
        text = module.set_scalar(text, "current_stage", "completed")
        text = module.set_scalar(text, "stage_status", "committed")
        text = module.set_scalar(text, "last_committed_stage", "finalization")
        text = module.set_scalar(text, "publication_status", "complete")
        state.write_text(text, encoding="utf-8")
        payload = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertIn("finalization Receipt", " ".join(payload["integrity_errors"]))

    def test_java_and_node_inventory_forward_paths(self) -> None:
        fixtures = {
            "java-forward": (
                "src/main/java/example/Handler.java",
                "package example; public class Handler { public String handle(String value) { return value; } }\n",
            ),
            "node-forward": (
                "src/handler.js",
                "exports.handler = async (event) => ({ statusCode: 200, body: event.id });\n",
            ),
        }
        for name, (relative_source, source_text) in fixtures.items():
            with self.subTest(name=name):
                repo = self.root / name
                source = repo / relative_source
                source.parent.mkdir(parents=True)
                source.write_text(source_text, encoding="utf-8")
                output = self.root / f"{name}-knowledge"
                initialized = subprocess.run(
                    [
                        sys.executable,
                        str(EXECUTOR),
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
                self.assertEqual(initialized.returncode, 0, initialized.stderr)
                begun = subprocess.run(
                    [
                        sys.executable,
                        str(EXECUTOR),
                        "begin",
                        "--output",
                        str(output),
                        "--stage",
                        "inventory",
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(begun.returncode, 0, begun.stderr)
                begin_payload = json.loads(begun.stdout)
                candidate = Path(begin_payload["candidate"])
                index = subprocess.run(
                    [
                        sys.executable,
                        str(SKILL_ROOT / "scripts" / "build_evidence_index.py"),
                        "--repo",
                        str(repo),
                        "--output",
                        str(candidate / ".work" / "evidence-index.json"),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(index.returncode, 0, index.stderr)
                committed = subprocess.run(
                    [
                        sys.executable,
                        str(EXECUTOR),
                        "commit",
                        "--output",
                        str(output),
                        "--transaction",
                        begin_payload["transaction_id"],
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(committed.returncode, 0, committed.stdout + committed.stderr)
                state = (output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
                self.assertIn('current_stage: "tracing"', state)

    def test_full_mechanical_stage_chain_requires_final_receipt(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text("{}\n", encoding="utf-8")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, _candidate = self.begin("tracing")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)

        synthesis, candidate = self.begin("synthesis")
        executor = load_executor_module()
        register_text = "# Repository register\n\n" + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.REGISTER_HEADINGS)
        ) + "\n"
        synthesis_text = "# Repository synthesis\n\n" + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.SYNTHESIS_HEADINGS)
        ) + "\n"
        (candidate / ".work" / "repository-register.md").write_text(
            register_text, encoding="utf-8"
        )
        (candidate / ".work" / "repository-synthesis.md").write_text(
            synthesis_text, encoding="utf-8"
        )
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            synthesis,
            "--semantic-result",
            "complete",
        )

        tech, candidate = self.begin("tech-publication")
        (candidate / "tech-pack" / "behaviors").mkdir(parents=True)
        (candidate / "tech-pack" / "repository-overview.md").write_text(
            "# Repository overview\n\nNo executable behavior was observed in this fixture.\n",
            encoding="utf-8",
        )
        (candidate / "tech-pack" / "behavior-catalog.yaml").write_text(
            (candidate / ".work" / "behavior-catalog.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tech)

        api, _candidate = self.begin("api-contract-publication")
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            api,
            "--skip",
            "--reason",
            "No application route was observed in the fixture.",
        )

        model, candidate = self.begin("business-model")
        model_text = "# Business model\n\n" + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.BUSINESS_MODEL_HEADINGS)
        ) + "\n"
        (candidate / ".work" / "business-model.md").write_text(model_text, encoding="utf-8")
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            model,
            "--semantic-result",
            "blocked",
        )

        ba, _candidate = self.begin("ba-publication")
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            ba,
            "--skip",
            "--reason",
            "No safe business model can be published for this empty fixture.",
        )

        finalization, _candidate = self.begin("finalization")
        completed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            finalization,
        )
        completed_payload = json.loads(completed.stdout)
        self.assertEqual(completed_payload["next_stage"], "completed")
        final_status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertEqual(final_status["current_stage"], "completed")
        self.assertEqual(final_status["stage_status"], "committed")
        self.assertEqual(final_status["integrity_errors"], [])
        final_receipt = Path(completed_payload["receipt"])
        receipt_payload = json.loads(final_receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt_payload["stage"], "finalization")
        self.assertEqual(receipt_payload["result"], "committed")

    def test_archive_helper_detects_checksum_complete_tree(self) -> None:
        module = load_executor_module()
        source = self.root / "source"
        candidate = self.root / "candidate"
        (source / "ba-pack" / "behaviors").mkdir(parents=True)
        (source / "ba-pack" / "behaviors" / "a.md").write_text("a", encoding="utf-8")
        candidate.mkdir()
        archive = module.archive_legacy_ba(source, candidate, "test-tx")
        self.assertIsNotNone(archive)
        manifest = json.loads((archive / "archive-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["summary"]["files"], 1)


if __name__ == "__main__":
    unittest.main()
