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
    sys.path.insert(0, str(EXECUTOR.parent))
    specification = importlib.util.spec_from_file_location("stage_executor", EXECUTOR)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    try:
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


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
        if arguments and arguments[0] == "commit":
            values = list(arguments)
            output = Path(values[values.index("--output") + 1])
            transaction = values[values.index("--transaction") + 1]
            tx_dir = output / ".work" / "execution" / "transactions" / transaction
            ledger_path = tx_dir / "checkpoints.json"
            if ledger_path.is_file():
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                for item in ledger["checkpoints"]:
                    if item["status"] in {"complete", "skipped", "blocked"}:
                        continue
                    completed = subprocess.run(
                        [
                            sys.executable,
                            str(EXECUTOR),
                            "checkpoint",
                            "--output",
                            str(output),
                            "--transaction",
                            transaction,
                            "--checkpoint",
                            item["checkpoint_id"],
                            "--status",
                            "complete",
                            "--json",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
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
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
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

    def test_state_uses_stage_and_checkpoint_without_legacy_phase(self) -> None:
        state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertNotIn("\nphase:", "\n" + state)
        transaction, _candidate = self.begin("inventory")
        status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertEqual(status["current_stage"], "inventory")
        self.assertEqual(status["current_checkpoint"], "project-detection")
        self.assertEqual(status["checkpoint_status"], "in-progress")
        self.assertEqual(len(status["checkpoints"]), 3)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_commit_rejects_incomplete_checkpoints(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(EXECUTOR),
                "commit",
                "--output",
                str(self.output),
                "--transaction",
                transaction,
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("incomplete checkpoints", result.stderr)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_formal_drift_is_restored_and_commit_is_rejected(self) -> None:
        original = (self.output / ".work" / "repository-register.md").read_bytes()
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        (self.output / ".work" / "repository-register.md").write_text(
            "unauthorized formal write\n", encoding="utf-8"
        )
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertIn("FORMAL-DRIFT-RESTORED", " ".join(payload["errors"]))
        self.assertEqual(
            (self.output / ".work" / "repository-register.md").read_bytes(), original
        )
        self.assertTrue(candidate.is_dir())
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_recover_restores_interrupted_generation_swap(self) -> None:
        module = load_executor_module()
        transaction_id = "03-synthesis-interrupted"
        generation_id = "gen-interrupted"
        generation = self.output / ".work" / "execution" / "generations" / generation_id
        current_root = generation / "candidate-root"
        current_root.mkdir(parents=True)
        (current_root / "old.md").write_text("old generation\n", encoding="utf-8")
        tx_dir = self.output / ".work" / "execution" / "transactions" / transaction_id
        candidate = tx_dir / "candidate"
        candidate.mkdir(parents=True)
        (candidate / "new.md").write_text("new generation\n", encoding="utf-8")
        previous = generation / f"previous-{transaction_id}"
        current_root.rename(previous)
        state_path = self.output / ".work" / "analysis-state.yaml"
        original_state = state_path.read_text(encoding="utf-8")
        state = original_state
        state = module.set_scalar(state, "current_stage", "synthesis")
        state = module.set_scalar(state, "stage_status", "in-progress")
        state = module.set_scalar(state, "active_transaction", transaction_id)
        state = module.set_scalar(state, "current_checkpoint", "endpoint-reconciliation")
        state = module.set_scalar(state, "checkpoint_status", "in-progress")
        state_path.write_text(state, encoding="utf-8")
        (tx_dir / "pre-state.yaml").write_text(original_state, encoding="utf-8")
        (tx_dir / "transaction.json").write_text(
            json.dumps(
                {
                    "transaction_id": transaction_id,
                    "stage": "synthesis",
                    "status": "generation-promoting",
                    "candidate": str(candidate),
                }
            ),
            encoding="utf-8",
        )
        (tx_dir / "promotion-journal.json").write_text(
            json.dumps(
                {
                    "transaction_id": transaction_id,
                    "phase": "generation-old-moved",
                    "generation_id": generation_id,
                    "current_root": str(current_root),
                    "previous_root": str(previous),
                    "candidate": str(candidate),
                    "operations": [],
                }
            ),
            encoding="utf-8",
        )
        module.acquire_lock(
            self.output,
            {"transaction_id": transaction_id, "stage": "synthesis"},
        )
        recovered = self.run_cmd("recover", "--output", str(self.output))
        self.assertEqual(json.loads(recovered.stdout)["result"], "rolled-back-generation")
        self.assertEqual((current_root / "old.md").read_text(), "old generation\n")
        self.assertEqual((candidate / "new.md").read_text(), "new generation\n")
        recovered_state = state_path.read_text(encoding="utf-8")
        self.assertIn('stage_status: "failed"', recovered_state)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction_id)

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
            SKILL_ROOT / "scripts" / "artifact_schema.py",
            SKILL_ROOT / "scripts" / "validate_analysis_state.py",
            SKILL_ROOT / "scripts" / "build_evidence_index.py",
            SKILL_ROOT / "scripts" / "register_schema.py",
            SKILL_ROOT / "scripts" / "validate_pack_links.py",
            SKILL_ROOT / "assets" / "register-schema.json",
            SKILL_ROOT / "assets" / "artifact-schema.json",
            SKILL_ROOT / "assets" / "repository-register-template.md",
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
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, tracing_candidate = self.begin("tracing")
        dossier = tracing_candidate / ".work" / "behavior-dossiers" / "sample-repo.handle-request.md"
        dossier.write_text(
            "---\n"
            'artifact_type: "behavior-dossier"\n'
            'artifact_schema_version: "1"\n'
            'behavior_id: "sample-repo.handle-request"\n'
            "---\n",
            encoding="utf-8",
        )
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
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
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

    def test_legacy_ba_directory_is_archived_only_by_migration(self) -> None:
        legacy = self.output / "ba-pack" / "behaviors"
        legacy.mkdir(parents=True)
        (legacy / "old.md").write_text("legacy\n", encoding="utf-8")
        (self.output / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        planned = self.run_cmd(
            "resume",
            "--repo",
            str(self.repo),
            "--state",
            str(self.output / ".work" / "analysis-state.yaml"),
        )
        plan_payload = json.loads(planned.stdout)
        self.assertEqual(plan_payload["resume_stage_after_migration"], "business-model")
        self.assertTrue(legacy.is_dir())
        begun = self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "migration",
            "--plan",
            str(self.output / ".work" / "migration-plan.yaml"),
        )
        begin_payload = json.loads(begun.stdout)
        candidate = Path(begin_payload["candidate"])
        self.assertFalse((candidate / "ba-pack" / "behaviors" / "old.md").exists())
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begin_payload["transaction_id"],
        )
        receipt = json.loads(
            Path(json.loads(result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        archive = Path(receipt["archive"])
        self.assertEqual((archive / "ba-pack" / "behaviors" / "old.md").read_text(), "legacy\n")
        self.assertFalse((self.output / "ba-pack" / "behaviors").exists())
        self.assertEqual(receipt["stage"], "migration")

    def test_publication_stage_never_performs_legacy_ba_migration(self) -> None:
        legacy = self.output / "ba-pack" / "behaviors"
        legacy.mkdir(parents=True)
        (legacy / "old.md").write_text("legacy\n", encoding="utf-8")
        self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "inventory",
            expected=2,
        )
        self.assertTrue(legacy.is_dir())

    def test_resume_plans_unknown_pack_without_mutating_state(self) -> None:
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
        before = state.read_bytes()
        result = self.run_cmd(
            "resume", "--repo", str(self.repo), "--state", str(state), expected=1
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "migration-blocked")
        self.assertIn("current_stage", " ".join(payload["blocked_reasons"]))
        self.assertEqual(state.read_bytes(), before)
        self.assertTrue((self.output / ".work" / "migration-plan.yaml").is_file())

    def test_unversioned_register_creates_synthesis_migration_plan(self) -> None:
        (self.output / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        register = self.output / ".work" / "repository-register.md"
        register.write_text(
            "\n".join(
                line
                for line in register.read_text(encoding="utf-8").splitlines()
                if not line.startswith(("artifact_type:", "artifact_schema_version:"))
            )
            + "\n",
            encoding="utf-8",
        )
        result = self.run_cmd(
            "resume",
            "--repo",
            str(self.repo),
            "--state",
            str(self.output / ".work" / "analysis-state.yaml"),
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["resume_stage_after_migration"], "synthesis")
        plan = json.loads((self.output / ".work" / "migration-plan.yaml").read_text())
        register_steps = [
            step for step in plan["steps"] if step["artifact_type"] == "repository-register"
        ]
        self.assertEqual(register_steps[0]["source_version"], "unknown")
        self.assertEqual(register_steps[0]["action"], "archive-and-rebuild")
        self.assertEqual(
            register_steps[0]["reinitialize_from_template"],
            "repository-register-template.md",
        )

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
            ("current_stage", "completed"),
            ("stage_status", "committed"),
            ("active_transaction", None),
            ("last_committed_stage", "finalization"),
            ("synthesis_status", "complete"),
            ("business_model_status", "blocked"),
            ("publication_status", "complete"),
            ("working_generation_id", "gen-completed"),
            ("published_generation_id", "gen-completed"),
            ("published_source_commit", "unknown"),
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
            json.dumps(
                {
                    "artifact_type": "stage-receipt",
                    "artifact_schema_version": "2",
                    "stage": "finalization",
                    "result": "committed",
                    "promotion_scope": "formal-pack",
                    "formal_pack_published": True,
                    "generation_id": "gen-completed",
                }
            ),
            encoding="utf-8",
        )
        valid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, msg=valid.stdout + valid.stderr)

    def test_status_reports_completed_state_without_receipt_as_corrupt(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        module = load_executor_module()
        text = state.read_text(encoding="utf-8")
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
                committed = self.run_cmd(
                    "commit",
                    "--output",
                    str(output),
                    "--transaction",
                    begin_payload["transaction_id"],
                )
                self.assertEqual(committed.returncode, 0, committed.stdout + committed.stderr)
                state = (output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
                self.assertIn('current_stage: "tracing"', state)

    def test_full_mechanical_stage_chain_requires_final_receipt(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, _candidate = self.begin("tracing")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)

        synthesis, candidate = self.begin("synthesis")
        executor = load_executor_module()
        register_schema = json.loads(
            (SKILL_ROOT / "assets" / "register-schema.json").read_text(encoding="utf-8")
        )
        tables_by_section = {
            table["section"]: table["headers"]
            for table in register_schema["tables"].values()
        }
        register_parts = [
            "---",
            'artifact_type: "repository-register"',
            'artifact_schema_version: "1"',
            'repository: "sample-repo"',
            'source_commit: "unknown"',
            'register_status: "reconciled"',
            "---",
            "",
            "# Repository register",
        ]
        for heading in sorted(executor.REGISTER_HEADINGS):
            register_parts.extend(["", f"## {heading}", ""])
            headers = tables_by_section[heading]
            register_parts.append("| " + " | ".join(headers) + " |")
            register_parts.append("|" + "|".join("---" for _ in headers) + "|")
        register_text = "\n".join(register_parts) + "\n"
        synthesis_text = (
            "---\n"
            'artifact_type: "repository-synthesis"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Repository synthesis\n\n"
        ) + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.SYNTHESIS_HEADINGS)
        ) + "\n"
        (candidate / ".work" / "repository-register.md").write_text(
            register_text, encoding="utf-8"
        )
        (candidate / ".work" / "repository-synthesis.md").write_text(
            synthesis_text, encoding="utf-8"
        )
        synthesis_result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            synthesis,
            "--semantic-result",
            "complete",
        )
        synthesis_receipt = json.loads(
            Path(json.loads(synthesis_result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        generation_id = synthesis_receipt["generation_id"]
        self.assertEqual(synthesis_receipt["promotion_scope"], "generation")
        self.assertFalse(synthesis_receipt["formal_pack_published"])
        self.assertFalse((self.output / ".work" / "repository-synthesis.md").exists())
        self.assertTrue(
            (
                self.output
                / ".work"
                / "execution"
                / "generations"
                / generation_id
                / "candidate-root"
                / ".work"
                / "repository-synthesis.md"
            ).is_file()
        )

        tech, candidate = self.begin("tech-publication")
        (candidate / "tech-pack" / "behaviors").mkdir(parents=True)
        (candidate / "tech-pack" / "repository-overview.md").write_text(
            "---\n"
            'artifact_type: "repository-overview"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Repository overview\n\nNo executable behavior was observed in this fixture.\n",
            encoding="utf-8",
        )
        catalog_text = (candidate / ".work" / "behavior-catalog.yaml").read_text(
            encoding="utf-8"
        ).replace(
            'artifact_type: "working-behavior-catalog"',
            'artifact_type: "tech-behavior-catalog"',
            1,
        )
        (candidate / "tech-pack" / "behavior-catalog.yaml").write_text(
            catalog_text, encoding="utf-8"
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tech)
        self.assertFalse((self.output / "tech-pack" / "repository-overview.md").exists())

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
        model_text = (
            "---\n"
            'artifact_type: "business-model"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Business model\n\n"
        ) + "\n\n".join(
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
        self.assertEqual(final_status["working_generation_status"], "published")
        self.assertEqual(final_status["working_generation_id"], generation_id)
        self.assertEqual(final_status["published_generation_id"], generation_id)
        self.assertEqual(final_status["release_readiness"], "ready")
        self.assertEqual(final_status["integrity_errors"], [])
        final_receipt = Path(completed_payload["receipt"])
        receipt_payload = json.loads(final_receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt_payload["stage"], "finalization")
        self.assertEqual(receipt_payload["result"], "committed")
        self.assertEqual(receipt_payload["promotion_scope"], "formal-pack")
        self.assertTrue(receipt_payload["formal_pack_published"])
        self.assertTrue((self.output / "tech-pack" / "repository-overview.md").is_file())
        self.assertEqual(
            receipt_payload["repository_register_artifact_schema_version"], "1"
        )
        self.assertEqual(
            receipt_payload["validator_domain_statuses"],
            {
                "dependency": "valid",
                "failure": "valid",
                "http": "valid",
                "markdown": "valid",
            },
        )
        self.assertEqual(receipt_payload["primary_error_count"], 0)
        self.assertEqual(receipt_payload["skipped_group_count"], 0)

    def test_synthesis_commit_rejects_register_schema_drift(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, _candidate = self.begin("tracing")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)

        synthesis, candidate = self.begin("synthesis")
        executor = load_executor_module()
        register = candidate / ".work" / "repository-register.md"
        register.write_text(
            register.read_text(encoding="utf-8").replace(
                "| Dependency ID | Logical identity |",
                "| Dependency Identifier | Logical identity |",
                1,
            ),
            encoding="utf-8",
        )
        synthesis_text = "# Repository synthesis\n\n" + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.SYNTHESIS_HEADINGS)
        ) + "\n"
        (candidate / ".work" / "repository-synthesis.md").write_text(
            synthesis_text,
            encoding="utf-8",
        )
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            synthesis,
            "--semantic-result",
            "complete",
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertIn("Register Schema", " ".join(payload["errors"]))
        formal = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "synthesis"', formal)

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
