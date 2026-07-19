from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
VALIDATOR = SCRIPTS / "validate_publication_maturity.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


publication_maturity = load_module(
    "publication_maturity", SCRIPTS / "publication_maturity.py"
)


class PublicationMaturityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "tech-pack" / "behaviors").mkdir(parents=True)
        (self.root / "ba-pack" / "scenarios").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def validate(self) -> dict:
        return publication_maturity.validate_reader_artifacts(self.root)

    def test_explicit_workflow_residue_blocks_reader_pack(self) -> None:
        phrases = (
            "This is a forward reference.",
            "The Contract is N/A until API publication.",
            "The document will be materialized in the next stage.",
            "Use the planned Contract path.",
            "During Tech publication this link is incomplete.",
            "API publication materializes the Contract.",
        )
        self.write(
            "tech-pack/behaviors/repository.example.md",
            "# Example\n\n" + "\n\n".join(phrases) + "\n",
        )
        report = self.validate()
        self.assertEqual(report["result"], "invalid")
        self.assertEqual(report["blocking_count"], len(phrases))
        self.assertTrue(
            all(item["code"] == "DOC-PUBLICATION-RESIDUE" for item in report["blocking_residues"])
        )

    def test_ambiguous_domain_terms_warn_without_blocking(self) -> None:
        self.write(
            "ba-pack/scenarios/repository.scenario.approval.md",
            "# Approval\n\nThe customer request remains pending approval and may be processed later.\n",
        )
        report = self.validate()
        self.assertEqual(report["result"], "valid")
        self.assertEqual(report["blocking_count"], 0)
        self.assertEqual(report["review_count"], 2)
        self.assertEqual(
            {item["code"] for item in report["review_terms"]},
            {"DOC-PUBLICATION-TERM"},
        )

    def test_markdown_code_links_and_template_comments_are_not_scanned(self) -> None:
        self.write(
            "tech-pack/behaviors/repository.example.md",
            """---
document: "../planned-contract.md"
---
# Example

<!-- TEMPLATE: This is a forward reference. -->

`planned Contract` and [durable link](../planned-contract.md)

[contract]: ../future-contract.md

```text
N/A until API publication
```
""",
        )
        report = self.validate()
        self.assertEqual(report["blocking_count"], 0)
        self.assertEqual(report["review_count"], 0)

    def test_yaml_reader_artifact_is_scanned_but_template_comment_is_ignored(self) -> None:
        self.write(
            "tech-pack/behavior-catalog.yaml",
            "# TEMPLATE: planned Contract path\ndocument: \"contracts/future-api.md\"\nsummary: \"pending publication\"\n",
        )
        report = self.validate()
        self.assertEqual(report["blocking_count"], 1)
        self.assertEqual(report["blocking_residues"][0]["path"], "tech-pack/behavior-catalog.yaml")

    def test_working_artifacts_are_out_of_scope(self) -> None:
        self.write(
            ".work/analysis-state.yaml",
            'stage_status: "pending"\nnotes: "forward reference"\n',
        )
        report = self.validate()
        self.assertEqual(report["checked_files"], 0)
        self.assertEqual(report["blocking_count"], 0)
        self.assertEqual(report["review_count"], 0)

    def test_cli_uses_blocking_exit_code_and_json_contract(self) -> None:
        self.write(
            "tech-pack/behaviors/repository.example.md",
            "# Example\n\nThe API Contract is not available until publication.\n",
        )
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.root), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["publication_maturity_validation_version"], "1")
        self.assertEqual(payload["blocking_count"], 1)


if __name__ == "__main__":
    unittest.main()
