from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = SKILL_ROOT / "scripts" / "stage_executor.py"


class ArtifactMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.output = self.root / "pack"
        self.run_cmd("init", "--repo", str(self.repo), "--output", str(self.output))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cmd(self, *args: str, expected: int = 0) -> dict:
        if args and args[0] == "commit":
            values = list(args)
            output = Path(values[values.index("--output") + 1])
            transaction = values[values.index("--transaction") + 1]
            ledger_path = output / ".work" / "execution" / "transactions" / transaction / "checkpoints.json"
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
            [sys.executable, str(EXECUTOR), *args, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            expected,
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return json.loads(result.stdout) if result.stdout else {"stderr": result.stderr}

    def resume(self, expected: int = 0) -> dict:
        return self.run_cmd(
            "resume",
            "--repo",
            str(self.repo),
            "--state",
            str(self.output / ".work" / "analysis-state.yaml"),
            expected=expected,
        )

    def add_evidence(self) -> None:
        (self.output / ".work" / "evidence-index.json").write_text(
            json.dumps(
                {
                    "artifact_type": "evidence-index",
                    "artifact_schema_version": "1",
                    "repository": "repo",
                    "source_commit": "unknown",
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def knowledge_hashes(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for path in sorted(self.output.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(self.output).as_posix()
            if relative.startswith(".work/execution/") or relative == ".work/migration-plan.yaml":
                continue
            values[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return values

    def plan(self) -> dict:
        return json.loads(
            (self.output / ".work" / "migration-plan.yaml").read_text(encoding="utf-8")
        )

    def begin_migration(self) -> dict:
        return self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "migration",
            "--plan",
            str(self.output / ".work" / "migration-plan.yaml"),
        )

    def test_new_and_current_resume_do_not_create_migration_plan(self) -> None:
        self.assertFalse((self.output / ".work" / "migration-plan.yaml").exists())
        payload = self.resume()
        self.assertEqual(payload["result"], "resume-ready")
        self.assertFalse((self.output / ".work" / "migration-plan.yaml").exists())

    def test_init_rejects_artifact_registry_template_drift(self) -> None:
        copied = self.root / "skill-copy"
        shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        template = copied / "assets" / "api-contract-document-template.md"
        template.write_text(
            template.read_text().replace(
                'artifact_schema_version: "2"', 'artifact_schema_version: "99"', 1
            )
        )
        output = self.root / "drift-output"
        result = subprocess.run(
            [
                sys.executable,
                str(copied / "scripts" / "stage_executor.py"),
                "init",
                "--repo",
                str(self.repo),
                "--output",
                str(output),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Artifact Schema and templates are out of sync", result.stderr)
        self.assertFalse(output.exists())

    def test_init_rejects_unregistered_mechanical_transform(self) -> None:
        copied = self.root / "skill-copy-transform-drift"
        shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        registry = copied / "assets" / "artifact-schema.json"
        registry.write_text(
            registry.read_text(encoding="utf-8").replace(
                '"transform_id": "analysis-state-1-to-2"',
                '"transform_id": "not-registered"',
                1,
            ),
            encoding="utf-8",
        )
        output = self.root / "transform-drift-output"
        result = subprocess.run(
            [
                sys.executable,
                str(copied / "scripts" / "stage_executor.py"),
                "init",
                "--repo",
                str(self.repo),
                "--output",
                str(output),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unregistered transform", result.stderr)
        self.assertFalse(output.exists())

    def test_begin_rejects_manifest_and_artifact_metadata_mismatch(self) -> None:
        register = self.output / ".work" / "repository-register.md"
        register.write_text(
            register.read_text().replace(
                'artifact_schema_version: "1"', 'artifact_schema_version: "99"', 1
            )
        )
        result = subprocess.run(
            [
                sys.executable,
                str(EXECUTOR),
                "begin",
                "--output",
                str(self.output),
                "--stage",
                "inventory",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("formal Artifact Manifest is invalid", result.stderr)

    def test_resume_audit_changes_only_plan_and_planning_receipt(self) -> None:
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
        (self.output / ".work" / "artifact-manifest.json").unlink()
        before = self.knowledge_hashes()
        payload = self.resume()
        after = self.knowledge_hashes()
        self.assertEqual(payload["result"], "migration-planned")
        self.assertEqual(before, after)
        receipt = Path(payload["receipt"])
        self.assertEqual(json.loads(receipt.read_text())["kind"], "migration-planning")

    def test_pack_change_after_planning_rejects_migration_begin(self) -> None:
        (self.output / "ba-pack" / "behaviors").mkdir(parents=True)
        legacy = self.output / "ba-pack" / "behaviors" / "old.md"
        legacy.write_text("legacy\n", encoding="utf-8")
        self.resume()
        legacy.write_text("changed after plan\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(EXECUTOR),
                "begin",
                "--output",
                str(self.output),
                "--stage",
                "migration",
                "--plan",
                str(self.output / ".work" / "migration-plan.yaml"),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("changed after the migration plan", result.stderr.lower())

    def test_api_version_drives_recovery_without_body_feature_detection(self) -> None:
        self.add_evidence()
        contracts = self.output / "tech-pack" / "contracts"
        contracts.mkdir(parents=True)
        contract = contracts / "repo.get-x.api-contract.md"
        contract.write_text(
            "---\nartifact_type: \"api-contract\"\nartifact_schema_version: \"0\"\n"
            "---\n\n# Contract\n\n## L1 L2 L3 words are irrelevant\n",
            encoding="utf-8",
        )
        payload = self.resume()
        self.assertEqual(payload["resume_stage_after_migration"], "api-contract-publication")
        step = next(step for step in self.plan()["steps"] if step["artifact_type"] == "api-contract")
        self.assertEqual(step["source_version"], "0")
        self.assertEqual(step["action"], "archive-and-rebuild")

    def test_previous_api_schema_is_republished_even_with_current_words(self) -> None:
        self.add_evidence()
        contracts = self.output / "tech-pack" / "contracts"
        contracts.mkdir(parents=True)
        (contracts / "repo.get-x.api-contract.md").write_text(
            "---\nartifact_type: \"api-contract\"\nartifact_schema_version: \"1\"\n"
            "---\n\n# Contract\n\nExposure and reachability; L1/L2/L3.\n",
            encoding="utf-8",
        )
        payload = self.resume()
        self.assertEqual(payload["resume_stage_after_migration"], "api-contract-publication")
        step = next(step for step in self.plan()["steps"] if step["artifact_type"] == "api-contract")
        self.assertEqual(step["action"], "archive-and-rebuild")

    def test_unversioned_new_looking_contract_remains_unknown(self) -> None:
        self.add_evidence()
        contracts = self.output / "tech-pack" / "contracts"
        contracts.mkdir(parents=True)
        (contracts / "repo.get-x.api-contract.md").write_text(
            "---\nrepository: \"repo\"\n---\n\n# Consumer-first Contract\n",
            encoding="utf-8",
        )
        self.resume()
        step = next(step for step in self.plan()["steps"] if step["artifact_type"] == "api-contract")
        self.assertEqual(step["source_version"], "unknown")
        self.assertEqual(step["action"], "archive-and-rebuild")

    def test_missing_migration_chain_produces_blocked_plan_without_pack_mutation(self) -> None:
        self.add_evidence()
        contracts = self.output / "tech-pack" / "contracts"
        contracts.mkdir(parents=True)
        (contracts / "repo.get-x.api-contract.md").write_text(
            "---\nartifact_type: \"api-contract\"\nartifact_schema_version: \"99\"\n"
            "---\n\n# Unsupported future contract\n",
            encoding="utf-8",
        )
        before = self.knowledge_hashes()
        payload = self.resume(expected=1)
        self.assertEqual(payload["result"], "migration-blocked")
        self.assertTrue(payload["blocked_reasons"])
        self.assertEqual(before, self.knowledge_hashes())
        begin = subprocess.run(
            [
                sys.executable,
                str(EXECUTOR),
                "begin",
                "--output",
                str(self.output),
                "--stage",
                "migration",
                "--plan",
                str(self.output / ".work" / "migration-plan.yaml"),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(begin.returncode, 2)
        self.assertIn("blocked", begin.stderr.lower())

    def test_migration_rejects_candidate_file_outside_plan(self) -> None:
        (self.output / "ba-pack" / "behaviors").mkdir(parents=True)
        (self.output / "ba-pack" / "behaviors" / "old.md").write_text("legacy\n")
        self.resume()
        begun = self.begin_migration()
        candidate = Path(begun["candidate"])
        synthesis = candidate / ".work" / "repository-synthesis.md"
        synthesis.write_text(
            "---\nartifact_type: \"repository-synthesis\"\n"
            "artifact_schema_version: \"1\"\n---\n# Invented during migration\n"
        )
        validation = self.run_cmd(
            "validate",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
            expected=1,
        )
        self.assertEqual(validation["result"], "blocked")
        self.assertTrue(
            any(
                item["code"] in {"CANDIDATE-MANIFEST", "MIGRATION-VALIDATION"}
                for item in validation["blocking_errors"]["items"]
            )
        )
        failed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
            expected=1,
        )
        self.assertIn("sealed Migration Candidate", " ".join(failed["errors"]))
        self.assertFalse((self.output / ".work" / "repository-synthesis.md").exists())

    def test_migration_and_publication_receipts_have_separate_roles(self) -> None:
        self.add_evidence()
        (self.output / "ba-pack" / "behaviors").mkdir(parents=True)
        (self.output / "ba-pack" / "behaviors" / "old.md").write_text("legacy\n")
        self.resume()
        begun = self.begin_migration()
        committed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )
        receipt = json.loads(Path(committed["receipt"]).read_text())
        self.assertEqual(receipt["kind"], "migration")
        self.assertEqual(receipt["stage"], "migration")
        self.assertNotIn("publication_status", receipt)
        self.assertIn("mechanical_output_manifest_sha256", receipt)
        self.assertIn("transform_reports", receipt)
        state = (self.output / ".work" / "analysis-state.yaml").read_text()
        self.assertIn('migration_status: "committed"', state)
        self.assertIn('publication_status: "pending"', state)

    def test_registered_transform_is_planned_executed_and_sealed(self) -> None:
        fixture = (
            SKILL_ROOT
            / "tests"
            / "fixtures"
            / "migration"
            / "repository-register-flat-http-1.md"
        )
        register = self.output / ".work" / "repository-register.md"
        shutil.copy2(fixture, register)
        self.resume()
        step = next(
            item
            for item in self.plan()["steps"]
            if item["artifact_type"] == "repository-register"
        )
        self.assertEqual(step["action"], "mechanical-migrate")
        self.assertEqual(
            step["transform_id"], "repository-register-flat-http-1-to-1"
        )
        self.assertEqual(step["source_artifact"]["artifact_schema_version"], "flat-http-1")
        self.assertEqual(step["expected"]["source_record_counts"]["flat_http_mappings"], 2)

        begun = self.begin_migration()
        scaffold = self.run_cmd(
            "scaffold",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
            "--artifact-type",
            "repository-synthesis",
            expected=2,
        )
        self.assertIn("not allowed during migration", scaffold["error"])
        validation = self.run_cmd(
            "validate",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )
        self.assertEqual(validation["result"], "ready")
        self.assertEqual(validation["semantic_or_document_errors"]["count"], 0)
        self.assertEqual(validation["blocking_errors"]["count"], 0)
        mechanical_manifest = json.loads(
            Path(begun["mechanical_output_manifest"]).read_text(encoding="utf-8")
        )
        self.assertEqual(len(mechanical_manifest["transform_reports"]), 2)
        candidate_register = Path(begun["candidate"]) / ".work" / "repository-register.md"
        candidate_text = candidate_register.read_text(encoding="utf-8")
        self.assertIn('artifact_schema_version: "1"', candidate_text)
        self.assertIn("HTTP-007-U01", candidate_text)
        self.assertIn("Unresolved", candidate_text)
        status = self.run_cmd("status", "--output", str(self.output))
        self.assertTrue(status["mechanical_output_manifest"]["candidate_sealed"])
        self.assertEqual(status["mechanical_output_manifest"]["transform_count"], 2)

        checkpoint = self.run_cmd(
            "checkpoint",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
            "--checkpoint",
            "plan-verification",
            "--status",
            "complete",
            expected=2,
        )
        self.assertIn("executor-owned", checkpoint["stderr"])

        committed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )
        receipt = json.loads(Path(committed["receipt"]).read_text(encoding="utf-8"))
        transform_ids = {item["transform_id"] for item in receipt["transform_reports"]}
        self.assertIn("repository-register-flat-http-1-to-1", transform_ids)
        register_report = next(
            item
            for item in receipt["transform_reports"]
            if item["transform_id"] == "repository-register-flat-http-1-to-1"
        )
        self.assertEqual(register_report["input_summary"]["file_count"], 1)
        self.assertEqual(register_report["output_records"]["http_mappings"], 2)
        self.assertTrue(register_report["id_map"])
        self.assertNotIn("dependency_contracts", receipt)
        self.assertNotIn("failure_patterns", receipt)

    def test_known_analysis_state_schema_migrates_lifecycle_mechanically(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        text = state.read_text(encoding="utf-8")
        text = text.replace('artifact_schema_version: "2"', 'artifact_schema_version: "1"', 1)
        text = text.replace('workflow_schema_version: "4"', 'workflow_schema_version: "3"', 1)
        text = 'phase: "inventory"\n' + text
        state.write_text(text, encoding="utf-8")
        self.resume()
        state_step = next(
            item
            for item in self.plan()["steps"]
            if item["artifact_type"] == "analysis-state"
        )
        self.assertEqual(state_step["transform_id"], "analysis-state-1-to-2")
        begun = self.begin_migration()
        committed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )
        self.assertEqual(committed["next_stage"], "inventory")
        migrated = state.read_text(encoding="utf-8")
        self.assertIn('artifact_schema_version: "2"', migrated)
        self.assertIn('workflow_schema_version: "4"', migrated)
        self.assertIn('migration_status: "committed"', migrated)
        self.assertNotIn("\nphase:", "\n" + migrated)

    def test_unknown_register_is_archived_and_reinitialized_without_ai_adoption(self) -> None:
        register = self.output / ".work" / "repository-register.md"
        legacy_bytes = register.read_bytes()
        register.write_text(
            "\n".join(
                line
                for line in register.read_text(encoding="utf-8").splitlines()
                if not line.startswith(("artifact_type:", "artifact_schema_version:"))
            )
            + "\n",
            encoding="utf-8",
        )
        self.resume()
        step = next(
            item
            for item in self.plan()["steps"]
            if item["artifact_type"] == "repository-register"
        )
        self.assertEqual(step["action"], "archive-and-rebuild")
        self.assertEqual(
            step["reinitialize_from_template"], "repository-register-template.md"
        )
        begun = self.begin_migration()
        candidate_register = Path(begun["candidate"]) / ".work" / "repository-register.md"
        self.assertIn(
            'artifact_type: "repository-register"',
            candidate_register.read_text(encoding="utf-8"),
        )
        committed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )
        legacy_root = Path(committed["legacy_artifacts_archive"])
        archived = legacy_root / ".work" / "repository-register.md"
        self.assertTrue(archived.is_file())
        self.assertNotEqual(archived.read_bytes(), legacy_bytes)
        self.assertNotIn("artifact_type:", archived.read_text(encoding="utf-8"))

    def test_completed_without_finalization_receipt_is_integrity_error(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        text = state.read_text()
        replacements = {
            'phase: "inventory"': 'phase: "completed"',
            'current_stage: "inventory"': 'current_stage: "completed"',
            'stage_status: "pending"': 'stage_status: "committed"',
            "last_committed_stage: null": 'last_committed_stage: "finalization"',
            'publication_status: "pending"': 'publication_status: "complete"',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        state.write_text(text)
        result = subprocess.run(
            [
                sys.executable,
                str(EXECUTOR),
                "resume",
                "--repo",
                str(self.repo),
                "--state",
                str(state),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("integrity failure", result.stderr)
        self.assertFalse((self.output / ".work" / "migration-plan.yaml").exists())


if __name__ == "__main__":
    unittest.main()
