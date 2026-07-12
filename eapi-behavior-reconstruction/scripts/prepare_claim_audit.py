#!/usr/bin/env python3
"""Create a hash-bound, deliberately non-passing claim-audit review skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runtime_guard import atomic_write_text, reject_descendant, resolve_outside_skill, run_guarded
from validate_claim_ledger import claim_sha256, text_sha256, validate_claim_artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    ledger = args.ledger.expanduser().resolve()
    output = args.output.expanduser()
    if not output.is_absolute():
        output = Path.cwd() / output
    resolve_outside_skill(output, label="claim-audit output")
    repo = args.repo.expanduser().resolve()
    reject_descendant(
        output,
        repo,
        label="claim-audit output",
        protected_label="the analyzed repository",
    )
    errors, warnings, claims = validate_claim_artifacts(
        ledger,
        output,
        repo,
        require_audit=False,
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    if output.exists() and not args.force:
        try:
            current = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = None
        if not isinstance(current, dict) or "scaffold_state" not in current:
            print("ERROR: output already contains a non-scaffold audit; use --force to replace it")
            return 1

    ledger_data = json.loads(ledger.read_text(encoding="utf-8"))
    audits: list[dict[str, object]] = []
    for claim_id, claim in claims.items():
        evidence_hashes = sorted(
            str(item.get("excerpt_sha256"))
            for item in claim.get("evidence", [])
            if isinstance(item, dict) and isinstance(item.get("excerpt_sha256"), str)
        )
        audits.append(
            {
                "claim_id": claim_id,
                "verdict": "ReviewRequired",
                "reviewed_statement_sha256": text_sha256(str(claim.get("statement", ""))),
                "reviewed_claim_sha256": claim_sha256(claim),
                "reviewed_evidence_hashes": evidence_hashes,
                "entailment_notes": "",
                "overstatement_check": "ReviewRequired",
            }
        )
    artifact = {
        "schema_version": 1,
        "repository": ledger_data.get("repository"),
        "source_commit": ledger_data.get("source_commit"),
        "review": {
            "mode": "ReviewRequired",
            "author_id": "REPLACE_AUTHOR_CONTEXT",
            "reviewer_id": "REPLACE_INDEPENDENT_REVIEWER_CONTEXT",
        },
        "audits": audits,
    }
    output_root = (
        output.parents[1]
        if output.name == "claim-audit.json" and output.parent.name == ".work"
        else output.parent
    )
    atomic_write_text(
        output,
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        output_root=output_root,
        label="claim-audit output",
    )
    print(f"OK: prepared {len(audits)} non-passing audit item(s) for semantic review at {output}")
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
