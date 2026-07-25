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

    def add_behavior_with_legacy_dossier(
        self, version: str | None
    ) -> tuple[str, Path, bytes]:
        behavior_id = "repo.handle-request"
        state = self.output / ".work" / "analysis-state.yaml"
        state.write_text(
            state.read_text(encoding="utf-8").replace(
                "behaviors: []",
                "behaviors:\n"
                f'  - behavior_id: "{behavior_id}"\n'
                '    status: "understood"\n'
                f'    dossier: "behavior-dossiers/{behavior_id}.md"\n'
                '    notes: "Legacy understanding result"',
            ),
            encoding="utf-8",
        )
        catalog = self.output / ".work" / "behavior-catalog.yaml"
        catalog.write_text(
            catalog.read_text(encoding="utf-8").replace(
                "behaviors: []",
                "behaviors:\n"
                f'  - behavior_id: "{behavior_id}"\n'
                '    title: "Handle request"\n'
                '    category: "business"\n'
                '    triggers: []\n'
                '    entry_points: []\n'
                '    status: "documented"\n'
                '    duplicate_of: null\n'
                f'    document: "behaviors/{behavior_id}.md"\n'
                '    ba_scenarios: []\n'
                '    api_contracts: []',
            ),
            encoding="utf-8",
        )
        dossier = self.output / ".work" / "behavior-dossiers" / f"{behavior_id}.md"
        dossier.parent.mkdir(parents=True, exist_ok=True)
        version_line = (
            f'artifact_schema_version: "{version}"\n' if version is not None else ""
        )
        legacy_bytes = (
            "---\n"
            'artifact_type: "behavior-dossier"\n'
            + version_line
            + f'behavior_id: "{behavior_id}"\n'
            + 'repository: "repo"\n'
            + 'source_commit: "unknown"\n'
            + "---\n\n"
            + "# Legacy dossier\n\n"
            + "This legacy semantic conclusion must not be mechanically adopted.\n"
        ).encode("utf-8")
        dossier.write_bytes(legacy_bytes)
        return behavior_id, dossier, legacy_bytes

    def add_legacy_dossiers(self, count: int) -> list[tuple[str, Path, bytes]]:
        state_entries: list[str] = []
        catalog_entries: list[str] = []
        dossiers: list[tuple[str, Path, bytes]] = []
        dossier_root = self.output / ".work" / "behavior-dossiers"
        dossier_root.mkdir(parents=True, exist_ok=True)
        for index in range(1, count + 1):
            behavior_id = f"repo.behavior-{index}"
            state_entries.extend(
                [
                    f'  - behavior_id: "{behavior_id}"',
                    '    status: "understood"',
                    f'    dossier: "behavior-dossiers/{behavior_id}.md"',
                    '    notes: "Legacy understanding result"',
                ]
            )
            catalog_entries.extend(
                [
                    f'  - behavior_id: "{behavior_id}"',
                    f'    title: "Behavior {index}"',
                    '    category: "business"',
                    '    triggers: []',
                    '    entry_points: []',
                    '    status: "documented"',
                    '    duplicate_of: null',
                    f'    document: "behaviors/{behavior_id}.md"',
                    '    ba_scenarios: []',
                    '    api_contracts: []',
                ]
            )
            dossier = dossier_root / f"{behavior_id}.md"
            content = (
                "---\n"
                'artifact_type: "behavior-dossier"\n'
                'artifact_schema_version: "1"\n'
                f'behavior_id: "{behavior_id}"\n'
                'repository: "repo"\n'
                'source_commit: "unknown"\n'
                "---\n\n"
                f"# Legacy dossier {index}\n"
            ).encode("utf-8")
            dossier.write_bytes(content)
            dossiers.append((behavior_id, dossier, content))
        state = self.output / ".work" / "analysis-state.yaml"
        state.write_text(
            state.read_text(encoding="utf-8").replace(
                "behaviors: []", "behaviors:\n" + "\n".join(state_entries)
            ),
            encoding="utf-8",
        )
        catalog = self.output / ".work" / "behavior-catalog.yaml"
        catalog.write_text(
            catalog.read_text(encoding="utf-8").replace(
                "behaviors: []", "behaviors:\n" + "\n".join(catalog_entries)
            ),
            encoding="utf-8",
        )
        return dossiers

    @staticmethod
    def rewrite_plan_id(plan: dict) -> None:
        identity = {
            key: value
            for key, value in plan.items()
            if key not in {"plan_id", "status", "created_at"}
        }
        canonical = json.dumps(
            identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        plan["plan_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

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

    def test_dossier_template_registry_and_transform_contract_are_consistent(self) -> None:
        registry = json.loads(
            (SKILL_ROOT / "assets" / "artifact-schema.json").read_text(encoding="utf-8")
        )
        definition = registry["artifact_types"]["behavior-dossier"]
        self.assertEqual(definition["current_version"], "3")
        self.assertEqual(
            definition["migrations"],
            {
                "0": {"to": "3", "action": "archive-and-rebuild"},
                "1": {"to": "3", "action": "archive-and-rebuild"},
                "2": {"to": "3", "action": "archive-and-rebuild"},
            },
        )
        template = (SKILL_ROOT / "assets" / "behavior-dossier-template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('artifact_schema_version: "3"', template)
        transforms = json.loads(
            (SKILL_ROOT / "assets" / "migration-transform-registry.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(
            any(
                transform.get("artifact_type") == "behavior-dossier"
                for transform in transforms["transforms"].values()
            )
        )

    def test_init_rejects_artifact_registry_template_drift(self) -> None:
        copied = self.root / "skill-copy"
        shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        template = copied / "assets" / "business-model-template.md"
        template.write_text(
            template.read_text().replace(
                'artifact_schema_version: "1"', 'artifact_schema_version: "99"', 1
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

    def test_init_rejects_migration_that_does_not_target_current_version(self) -> None:
        copied = self.root / "skill-copy-target-drift"
        shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        registry_path = copied / "assets" / "artifact-schema.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["artifact_types"]["behavior-dossier"]["migrations"]["1"]["to"] = "2"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        output = self.root / "target-drift-output"
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
        self.assertIn("must target current version 3", result.stderr)
        self.assertFalse(output.exists())

    def test_init_rejects_migration_from_current_version(self) -> None:
        copied = self.root / "skill-copy-current-source"
        shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        registry_path = copied / "assets" / "artifact-schema.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["artifact_types"]["behavior-dossier"]["migrations"]["3"] = {
            "to": "3",
            "action": "archive-and-rebuild",
        }
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        output = self.root / "current-source-output"
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
        self.assertIn("cannot declare a migration from its current version 3", result.stderr)
        self.assertFalse(output.exists())

    def test_schema_one_dossier_is_archived_reset_and_retraced_as_schema_three(self) -> None:
        self.add_evidence()
        behavior_id, dossier, legacy_bytes = self.add_behavior_with_legacy_dossier("1")

        resumed = self.resume()
        self.assertEqual(resumed["result"], "migration-planned")
        plan = self.plan()
        dossier_step = next(
            step for step in plan["steps"] if step["artifact_type"] == "behavior-dossier"
        )
        self.assertEqual(dossier_step["source_version"], "1")
        self.assertEqual(dossier_step["target_version"], "3")
        self.assertEqual(dossier_step["action"], "archive-and-rebuild")
        self.assertNotIn("transform_id", dossier_step)
        self.assertEqual(plan["resume_stage_after_migration"], "tracing")

        begun = self.begin_migration()
        candidate_dossier = Path(begun["candidate"]) / dossier.relative_to(self.output)
        self.assertFalse(candidate_dossier.exists())
        committed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )

        legacy_root = Path(committed["legacy_artifacts_archive"])
        archived = legacy_root / dossier.relative_to(self.output)
        self.assertEqual(archived.read_bytes(), legacy_bytes)
        self.assertEqual(hashlib.sha256(archived.read_bytes()).hexdigest(), hashlib.sha256(legacy_bytes).hexdigest())
        self.assertFalse(dossier.exists())
        migrated_state = (self.output / ".work" / "analysis-state.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn('current_stage: "tracing"', migrated_state)
        self.assertIn(f'behavior_id: "{behavior_id}"', migrated_state)
        self.assertIn('status: "discovered"', migrated_state)
        self.assertIn("dossier: null", migrated_state)
        self.assertIn("requires retracing under Schema 3", migrated_state)
        receipt = json.loads(Path(committed["receipt"]).read_text(encoding="utf-8"))
        self.assertFalse(
            any(
                report.get("artifact_type") == "behavior-dossier"
                for report in receipt.get("transform_reports", [])
            )
        )

        tracing = self.run_cmd(
            "begin", "--output", str(self.output), "--stage", "tracing"
        )
        scaffolded = self.run_cmd(
            "scaffold",
            "--output",
            str(self.output),
            "--transaction",
            tracing["transaction_id"],
            "--artifact-type",
            "behavior-dossier",
            "--identity",
            f"behavior_id={behavior_id}",
        )
        rebuilt = Path(scaffolded["path"])
        self.assertIn(
            'artifact_schema_version: "3"', rebuilt.read_text(encoding="utf-8")
        )
        self.run_cmd(
            "mark-behavior",
            "--output",
            str(self.output),
            "--transaction",
            tracing["transaction_id"],
            "--behavior-id",
            behavior_id,
            "--status",
            "understood",
            "--dossier",
            f"behavior-dossiers/{behavior_id}.md",
        )
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            tracing["transaction_id"],
        )
        rebuilt_hash = hashlib.sha256(dossier.read_bytes()).hexdigest()
        current_resume = self.resume()
        self.assertEqual(current_resume["result"], "resume-ready")
        self.assertEqual(hashlib.sha256(dossier.read_bytes()).hexdigest(), rebuilt_hash)
        self.assertEqual(self.plan()["status"], "committed")

    def test_unversioned_dossier_is_archived_and_returns_to_tracing(self) -> None:
        self.add_evidence()
        _behavior_id, _dossier, _legacy_bytes = self.add_behavior_with_legacy_dossier(None)
        resumed = self.resume()
        self.assertEqual(resumed["result"], "migration-planned")
        plan = self.plan()
        dossier_step = next(
            step for step in plan["steps"] if step["artifact_type"] == "behavior-dossier"
        )
        self.assertEqual(dossier_step["source_version"], "unknown")
        self.assertEqual(dossier_step["target_version"], "3")
        self.assertEqual(dossier_step["action"], "archive-and-rebuild")
        self.assertNotIn("transform_id", dossier_step)
        self.assertEqual(plan["resume_stage_after_migration"], "tracing")

    def test_six_archived_dossiers_set_the_plan_and_state_to_tracing(self) -> None:
        self.add_evidence()
        dossiers = self.add_legacy_dossiers(6)
        resumed = self.resume()
        self.assertEqual(resumed["resume_stage_after_migration"], "tracing")
        plan = self.plan()
        dossier_steps = [
            step
            for step in plan["steps"]
            if step["artifact_type"] == "behavior-dossier"
            and step["action"] == "archive-and-rebuild"
        ]
        self.assertEqual(len(dossier_steps), 1)
        self.assertEqual(dossier_steps[0]["rebuilding_stage"], "tracing")
        self.assertEqual(
            set(dossier_steps[0]["paths"]),
            {dossier.relative_to(self.output).as_posix() for _id, dossier, _data in dossiers},
        )

        begun = self.begin_migration()
        committed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )
        self.assertEqual(committed["next_stage"], "tracing")
        state = (self.output / ".work" / "analysis-state.yaml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(state.count('status: "discovered"'), 6)
        self.assertEqual(state.count("dossier: null"), 6)
        for behavior_id, dossier, legacy_bytes in dossiers:
            self.assertFalse(dossier.exists())
            archived = (
                Path(committed["legacy_artifacts_archive"])
                / dossier.relative_to(self.output)
            )
            self.assertEqual(archived.read_bytes(), legacy_bytes, behavior_id)

        direct_synthesis = self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "synthesis",
            expected=2,
        )
        self.assertIn("expected stage tracing", direct_synthesis["stderr"])

    def test_conflicting_plan_resume_stage_is_rejected_before_begin(self) -> None:
        self.add_evidence()
        self.add_legacy_dossiers(6)
        self.resume()
        plan_path = self.output / ".work" / "migration-plan.yaml"
        plan = self.plan()
        plan["resume_stage_after_migration"] = "synthesis"
        self.rewrite_plan_id(plan)
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        try:
            from artifact_schema import ArtifactSchemaError, load_migration_plan, load_registry

            with self.assertRaisesRegex(
                ArtifactSchemaError,
                "resume stage synthesis is later than required tracing",
            ):
                load_migration_plan(plan_path, load_registry())
        finally:
            sys.path.pop(0)
        transactions = self.output / ".work" / "execution" / "transactions"
        before = set(transactions.iterdir()) if transactions.is_dir() else set()

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
                str(plan_path),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "resume stage synthesis is later than required tracing",
            result.stderr,
        )
        after = set(transactions.iterdir()) if transactions.is_dir() else set()
        self.assertEqual(before, after)
        self.assertFalse(
            (self.output / ".work" / "execution" / "active.lock").exists()
        )

    def test_dossier_api_and_ba_rebuilds_choose_tracing(self) -> None:
        self.add_evidence()
        self.add_behavior_with_legacy_dossier("1")
        contract = self.output / "tech-pack" / "contracts" / "repo.get-x.api-contract.md"
        contract.parent.mkdir(parents=True, exist_ok=True)
        contract.write_text(
            '---\nartifact_type: "api-contract"\nartifact_schema_version: "2"\n---\n',
            encoding="utf-8",
        )
        overview = self.output / "ba-pack" / "business-overview.md"
        overview.parent.mkdir(parents=True, exist_ok=True)
        overview.write_text(
            '---\nartifact_type: "ba-overview"\nartifact_schema_version: "1"\n---\n',
            encoding="utf-8",
        )
        resumed = self.resume()
        self.assertEqual(resumed["resume_stage_after_migration"], "tracing")
        rebuilt_types = {
            step["artifact_type"]
            for step in self.plan()["steps"]
            if step["action"] == "archive-and-rebuild"
        }
        self.assertTrue(
            {"behavior-dossier", "api-contract", "ba-overview"}.issubset(rebuilt_types)
        )

    def test_missing_evidence_takes_precedence_over_dossier_tracing(self) -> None:
        self.add_behavior_with_legacy_dossier("1")
        resumed = self.resume()
        self.assertEqual(resumed["resume_stage_after_migration"], "inventory")

    def test_committed_inconsistent_pack_plans_lifecycle_repair_at_tracing(self) -> None:
        self.add_evidence()
        behavior_id, dossier, _legacy_bytes = self.add_behavior_with_legacy_dossier("2")
        dossier.unlink()
        state_path = self.output / ".work" / "analysis-state.yaml"
        state = state_path.read_text(encoding="utf-8")
        state = state.replace('current_stage: "inventory"', 'current_stage: "synthesis"')
        state = state.replace('status: "understood"', 'status: "discovered"')
        state = state.replace(
            f'dossier: "behavior-dossiers/{behavior_id}.md"', "dossier: null"
        )
        state_path.write_text(state, encoding="utf-8")
        synthesis = self.output / ".work" / "repository-synthesis.md"
        synthesis.write_text(
            '---\nartifact_type: "repository-synthesis"\nartifact_schema_version: "3"\n'
            'repository: "repo"\nsource_commit: "unknown"\n---\n',
            encoding="utf-8",
        )
        overview = self.output / "tech-pack" / "repository-overview.md"
        overview.parent.mkdir(parents=True, exist_ok=True)
        overview.write_text(
            '---\nartifact_type: "repository-overview"\nartifact_schema_version: "3"\n'
            'repository: "repo"\nsource_commit: "unknown"\n---\n',
            encoding="utf-8",
        )
        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        try:
            from artifact_schema import load_registry, write_artifact_manifest

            write_artifact_manifest(
                self.output,
                load_registry(),
                str(self.repo),
                "unknown",
                "migration",
                "previous-bad-migration",
                [],
            )
        finally:
            sys.path.pop(0)

        resumed = self.resume()
        self.assertEqual(resumed["result"], "migration-planned")
        self.assertEqual(resumed["resume_stage_after_migration"], "tracing")
        plan = self.plan()
        archived_types = {
            step["artifact_type"]
            for step in plan["steps"]
            if step["action"] == "archive-and-rebuild"
        }
        self.assertIn("repository-synthesis", archived_types)
        self.assertIn("repository-overview", archived_types)

        begun = self.begin_migration()
        committed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begun["transaction_id"],
        )
        self.assertEqual(committed["next_stage"], "tracing")
        self.assertFalse(synthesis.exists())
        self.assertFalse(overview.exists())
        repaired_state = state_path.read_text(encoding="utf-8")
        self.assertIn('status: "discovered"', repaired_state)
        self.assertIn("dossier: null", repaired_state)

    def test_begin_rejects_manifest_and_artifact_metadata_mismatch(self) -> None:
        register = self.output / ".work" / "repository-register.md"
        register.write_text(
            register.read_text().replace(
                'artifact_schema_version: "3"', 'artifact_schema_version: "99"', 1
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

    def test_reader_priority_versions_rebuild_synthesis_before_reader_publication(self) -> None:
        self.add_evidence()
        synthesis = self.output / ".work" / "repository-synthesis.md"
        synthesis.write_text(
            "---\nartifact_type: \"repository-synthesis\"\n"
            "artifact_schema_version: \"2\"\nrepository: \"repo\"\n"
            "source_commit: \"unknown\"\n---\n\n# Repository synthesis\n",
            encoding="utf-8",
        )
        business_model = self.output / ".work" / "business-model.md"
        business_model.write_text(
            "---\nartifact_type: \"business-model\"\n"
            "artifact_schema_version: \"1\"\nrepository: \"repo\"\n"
            "source_commit: \"unknown\"\n---\n\n# Business model\n",
            encoding="utf-8",
        )
        overview = self.output / "tech-pack" / "repository-overview.md"
        overview.parent.mkdir(parents=True)
        overview.write_text(
            "---\nartifact_type: \"repository-overview\"\n"
            "artifact_schema_version: \"1\"\n---\n\n# Old overview\n",
            encoding="utf-8",
        )
        ba_overview = self.output / "ba-pack" / "business-overview.md"
        ba_overview.parent.mkdir(parents=True)
        ba_overview.write_text(
            "---\nartifact_type: \"ba-overview\"\n"
            "artifact_schema_version: \"1\"\n---\n\n# Old BA overview\n",
            encoding="utf-8",
        )

        payload = self.resume()
        self.assertEqual(payload["resume_stage_after_migration"], "synthesis")
        steps = {step["artifact_type"]: step for step in self.plan()["steps"]}
        self.assertEqual(steps["repository-overview"]["action"], "archive-and-rebuild")
        self.assertEqual(steps["ba-overview"]["action"], "archive-and-rebuild")
        self.assertEqual(steps["repository-synthesis"]["action"], "archive-and-rebuild")
        self.assertEqual(steps["business-model"]["action"], "preserve")

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
        self.add_evidence()
        fixture = (
            SKILL_ROOT
            / "tests"
            / "fixtures"
            / "migration"
            / "repository-register-2.md"
        )
        register = self.output / ".work" / "repository-register.md"
        shutil.copy2(fixture, register)
        self.resume()
        self.assertEqual(self.plan()["resume_stage_after_migration"], "synthesis")
        step = next(
            item
            for item in self.plan()["steps"]
            if item["artifact_type"] == "repository-register"
        )
        self.assertEqual(step["action"], "mechanical-migrate")
        self.assertEqual(
            step["transform_id"], "repository-register-2-to-3"
        )
        self.assertEqual(step["source_artifact"]["artifact_schema_version"], "2")
        self.assertEqual(
            step["expected"]["source_record_counts"]["runtime_config_effects"], 2
        )
        self.assertEqual(
            step["expected"]["source_record_counts"]["failure_observations"], 1
        )

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
        self.assertIn('artifact_schema_version: "3"', candidate_text)
        self.assertIn("CFG-OBS-", candidate_text)
        self.assertIn("FO-003", candidate_text)
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
        self.assertIn("repository-register-2-to-3", transform_ids)
        register_report = next(
            item
            for item in receipt["transform_reports"]
            if item["transform_id"] == "repository-register-2-to-3"
        )
        self.assertEqual(register_report["input_summary"]["file_count"], 1)
        self.assertEqual(
            register_report["output_records"]["runtime_config_observations"], 2
        )
        self.assertEqual(register_report["output_records"]["runtime_config_impacts"], 0)
        self.assertEqual(register_report["output_records"]["java_types"], 0)
        self.assertEqual(register_report["output_records"]["failure_observations"], 1)
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
