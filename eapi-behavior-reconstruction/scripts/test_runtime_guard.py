#!/usr/bin/env python3
"""Regression tests for immutable runtime and output-boundary enforcement."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runtime_guard import (
    RELEASE_DIRECTORIES,
    RuntimeGuardError,
    bundle_sha256,
    discover_release_files,
    resolve_outside_skill,
    sha256_file,
    skill_root,
    verify_integrity,
)


ROOT = skill_root()
LAUNCHER = ROOT / "bin/eapi-pack"


def write_test_lock(root: Path) -> None:
    (root / "SKILL.md").write_text("---\nname: fixture\n---\n", encoding="utf-8")
    for directory in RELEASE_DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "scripts/tool.py").write_text("VALUE = 1\n", encoding="utf-8")
    files = {
        relative: sha256_file(path)
        for relative, path in discover_release_files(root).items()
    }
    lock = {
        "schema_version": 1,
        "algorithm": "sha256",
        "runtime": {
            "python_minimum": "3.9",
            "isolated_flags": ["-E", "-S", "-B", "-X utf8"],
            "third_party_dependencies": [],
        },
        "bundle_sha256": bundle_sha256(files),
        "files": dict(sorted(files.items())),
    }
    lock_path = root / "integrity/runtime-lock.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class RuntimeGuardTests(unittest.TestCase):
    def isolated_launcher(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-E", "-S", "-B", "-X", "utf8", str(LAUNCHER), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_current_release_integrity_passes(self) -> None:
        report = verify_integrity(ROOT)
        self.assertGreater(report["file_count"], 1)
        self.assertTrue(str(report["bundle_sha256"]).startswith("sha256:"))

    def test_tampered_artifact_fails_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_test_lock(root)
            (root / "scripts/tool.py").write_text("VALUE = 2\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeGuardError, "digest mismatch"):
                verify_integrity(root)

    def test_unlocked_release_artifact_fails_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_test_lock(root)
            (root / "references/late-file.md").write_text("late\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeGuardError, "unlocked release artifact"):
                verify_integrity(root)

    def test_skill_root_and_symlinked_targets_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeGuardError, "overlaps immutable SKILL_ROOT"):
            resolve_outside_skill(ROOT / "scripts/forbidden.txt")
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / "skill-link"
            link.symlink_to(ROOT, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeGuardError, "overlaps immutable SKILL_ROOT"):
                resolve_outside_skill(link / "assets/forbidden.txt")

    def test_launcher_preflight_passes_in_isolated_mode(self) -> None:
        result = self.isolated_launcher("preflight")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("immutable runtime verified", result.stdout)

    def test_launcher_without_isolated_flags_fails_closed(self) -> None:
        result = subprocess.run(
            [sys.executable, str(LAUNCHER), "preflight"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(70, result.returncode)
        self.assertIn("isolated interpreter flags are required", result.stderr)

    def test_launcher_rejects_pack_inside_skill_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            result = self.isolated_launcher(
                "scaffold",
                "--repo",
                str(repo),
                "--pack",
                str(ROOT / "forbidden-pack"),
            )
        self.assertEqual(70, result.returncode)
        self.assertIn("overlaps immutable SKILL_ROOT", result.stderr)
        self.assertFalse((ROOT / "forbidden-pack").exists())

    def test_direct_writer_without_isolation_fails_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            output = Path(temporary) / "index.json"
            repo.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build_evidence_index.py"),
                    "--repo",
                    str(repo),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(70, result.returncode)
            self.assertFalse(output.exists())

    def test_direct_writer_rejects_skill_root_output(self) -> None:
        forbidden = ROOT / "forbidden-index.json"
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    "-E",
                    "-S",
                    "-B",
                    "-X",
                    "utf8",
                    str(ROOT / "scripts/build_evidence_index.py"),
                    "--repo",
                    str(repo),
                    "--output",
                    str(forbidden),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(70, result.returncode)
        self.assertIn("overlaps immutable SKILL_ROOT", result.stderr)
        self.assertFalse(forbidden.exists())

    def test_missing_repository_is_an_invocation_error(self) -> None:
        result = self.isolated_launcher(
            "scaffold",
            "--repo",
            "/path/that/does/not/exist",
            "--pack",
            "/tmp/not-created-by-runtime-test",
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("INVOCATION_ERROR", result.stderr)

    def test_draft_claim_validation_uses_fixed_ledger_and_audit_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            pack = root / "pack"
            repo.mkdir()
            (repo / "handler.py").write_text("def handler(event, context):\n    return event\n", encoding="utf-8")
            scaffold = self.isolated_launcher(
                "scaffold", "--repo", str(repo), "--pack", str(pack)
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stdout + scaffold.stderr)
            result = self.isolated_launcher(
                "validate-claims", "--repo", str(repo), "--pack", str(pack), "--draft"
            )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("--draft is supported only with --ledger", result.stdout + result.stderr)
        self.assertIn("VALIDATION_FAILED", result.stderr)

    def test_successful_evidence_output_may_contain_runtime_words(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            (repo / "message.py").write_text('MESSAGE = "ImportError:"\n', encoding="utf-8")
            result = self.isolated_launcher(
                "show-evidence", "--repo", str(repo), "message.py:1"
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("ImportError:", result.stdout)
        self.assertNotIn("FATAL_RUNTIME", result.stderr)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can bypass mode bits")
    def test_output_permission_error_is_actionable_invocation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            readonly = root / "readonly"
            repo.mkdir()
            readonly.mkdir()
            readonly.chmod(0o500)
            try:
                result = self.isolated_launcher(
                    "scaffold",
                    "--repo",
                    str(repo),
                    "--pack",
                    str(readonly / "pack"),
                )
            finally:
                readonly.chmod(0o700)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("OUTPUT_PERMISSION_ERROR", result.stderr)
        self.assertIn("never request write access to SKILL_ROOT", result.stderr)

    def test_scaffold_rejects_internal_symlink_before_skill_write(self) -> None:
        protected = ROOT / "references/evidence-policy.md"
        before = sha256_file(protected)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            pack = root / "pack"
            repo.mkdir()
            first = self.isolated_launcher(
                "scaffold", "--repo", str(repo), "--pack", str(pack)
            )
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            linked = pack / "knowledge-map.md"
            linked.unlink()
            linked.symlink_to(protected)
            result = self.isolated_launcher(
                "scaffold", "--repo", str(repo), "--pack", str(pack), "--force"
            )
        self.assertEqual(70, result.returncode, result.stdout + result.stderr)
        self.assertIn("symbolic link", result.stderr)
        self.assertEqual(before, sha256_file(protected))

    def test_copied_release_tamper_stops_launcher_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "skill"
            shutil.copytree(ROOT, copied)
            target = copied / "scripts/show_evidence.py"
            target.write_text(target.read_text(encoding="utf-8") + "# tampered\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-E",
                    "-S",
                    "-B",
                    "-X",
                    "utf8",
                    str(copied / "bin/eapi-pack"),
                    "preflight",
                ],
                cwd=copied,
                capture_output=True,
                text=True,
            )
        self.assertEqual(70, result.returncode)
        self.assertIn("artifact digest mismatch", result.stderr)

    def test_compiled_python_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_test_lock(root)
            cache = root / "scripts/__pycache__/tool.pyc"
            cache.parent.mkdir()
            cache.write_bytes(b"not bytecode")
            with self.assertRaisesRegex(RuntimeGuardError, "compiled Python artifacts are forbidden"):
                verify_integrity(root)

    def test_protected_seed_hardlink_is_rejected_before_pack_update(self) -> None:
        protected = ROOT / "references/evidence-policy.md"
        before = sha256_file(protected)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            pack = root / "pack"
            repo.mkdir()
            first = self.isolated_launcher(
                "scaffold", "--repo", str(repo), "--pack", str(pack)
            )
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            seed = pack / ".work/claim-ledger.json"
            seed.unlink()
            try:
                os.link(protected, seed)
            except OSError as exc:
                self.skipTest(f"hardlinks across these temporary paths are unavailable: {exc}")
            result = self.isolated_launcher(
                "scaffold", "--repo", str(repo), "--pack", str(pack), "--force"
            )
        self.assertEqual(70, result.returncode, result.stdout + result.stderr)
        self.assertIn("non-hardlinked", result.stderr)
        self.assertEqual(before, sha256_file(protected))

    def test_symlinked_release_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_test_lock(root)
            outside = root / "outside"
            outside.mkdir()
            (root / "assets").rmdir()
            (root / "assets").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeGuardError, "release directories must not be symbolic links"):
                verify_integrity(root)

    def test_symlinked_integrity_lock_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_test_lock(root)
            lock = root / "integrity/runtime-lock.json"
            moved = root / "runtime-lock-copy.json"
            lock.replace(moved)
            lock.symlink_to(moved)
            with self.assertRaisesRegex(RuntimeGuardError, "integrity lock must not be reached"):
                verify_integrity(root)


if __name__ == "__main__":
    unittest.main()
