#!/usr/bin/env python3
"""Validate mechanical analysis-state, catalog, dossier, and publish-gate consistency."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_KEYS = {
    "artifact_type",
    "artifact_schema_version",
    "workflow_schema_version",
    "repository",
    "repository_path",
    "source_commit",
    "analysis_mode",
    "phase",
    "current_stage",
    "stage_status",
    "active_transaction",
    "last_committed_stage",
    "migration_status",
    "synthesis_status",
    "business_model_status",
    "publication_status",
    "output_directory",
    "behaviors",
}
ALLOWED_MODES = {"automatic"}
ALLOWED_PHASES = {"inventory", "tracing", "synthesis", "publishing", "completed"}
ALLOWED_STAGES = {
    "inventory",
    "tracing",
    "synthesis",
    "tech-publication",
    "api-contract-publication",
    "business-model",
    "ba-publication",
    "finalization",
    "completed",
}
ALLOWED_STAGE_STATUS = {"pending", "in-progress", "failed", "committed", "skipped"}
ALLOWED_SYNTHESIS = {"pending", "complete", "partial"}
ALLOWED_BUSINESS_MODEL = {"pending", "complete", "partial", "blocked"}
ALLOWED_PUBLICATION = {"pending", "in-progress", "stale", "complete"}
ALLOWED_MIGRATION = {"not-required", "planned", "in-progress", "committed", "blocked"}
ALLOWED_BEHAVIOR_STATUS = {"discovered", "tracing", "understood", "blocked"}
CATALOG_WITHOUT_DOSSIER = {"duplicate", "excluded"}


def unquote(value: str) -> str | None:
    value = value.strip()
    if value.lower() in {"null", "none", "~"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def scalar_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(?P<value>[^\n#]+?)\s*$", text, re.M)
    return unquote(match.group("value")) if match else None


def top_level_keys(text: str) -> set[str]:
    return {
        match.group(1)
        for line in text.splitlines()
        if line and not line[0].isspace()
        if (match := re.match(r"([A-Za-z_][A-Za-z0-9_-]*):", line))
    }


def behavior_entries(text: str) -> list[dict[str, str | None]]:
    match = re.search(r"^behaviors:\s*\n(?P<body>(?:[ \t]+[^\n]*(?:\n|$))*)", text, re.M)
    if not match:
        return []

    entries: list[dict[str, str | None]] = []
    current: dict[str, str | None] | None = None
    for line in match.group("body").splitlines():
        start = re.match(r"^\s*-\s+behavior_id:\s*(.+?)\s*$", line)
        if start:
            if current:
                entries.append(current)
            current = {"behavior_id": unquote(start.group(1))}
            continue
        field = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if current is not None and field:
            current[field.group(1)] = unquote(field.group(2))
    if current:
        entries.append(current)
    return entries


def current_git_commit(repo: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def dossier_path(state_file: Path, dossiers_dir: Path, declared: str | None, behavior_id: str) -> Path:
    if declared:
        declared_path = Path(declared)
        if declared_path.is_absolute():
            return declared_path
        from_state = state_file.parent / declared_path
        if from_state.is_file():
            return from_state
        return dossiers_dir / declared_path.name
    return dossiers_dir / f"{behavior_id}.md"


def dossier_behavior_id(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return scalar_value(text, "behavior_id")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--dossiers-dir", type=Path, required=True)
    parser.add_argument(
        "--require-publishable",
        action="store_true",
        help="require the synthesis gate needed to begin or complete formal publication",
    )
    parser.add_argument(
        "--require-ba-publishable",
        action="store_true",
        help="require completed repository synthesis and a complete or partial Business Model",
    )
    parser.add_argument(
        "--allow-missing-final-receipt",
        action="store_true",
        help="stage-executor candidate check only: allow final state before its Receipt is promoted",
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    for path, label in ((args.state, "state"), (args.catalog, "catalog")):
        if not path.is_file():
            errors.append(f"{label} file does not exist: {path}")
    if not args.repo.is_dir():
        errors.append(f"repository directory does not exist: {args.repo}")
    if not args.dossiers_dir.is_dir():
        errors.append(f"dossiers directory does not exist: {args.dossiers_dir}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 2

    state_text = args.state.read_text(encoding="utf-8")
    catalog_text = args.catalog.read_text(encoding="utf-8")

    missing_keys = sorted(REQUIRED_KEYS - top_level_keys(state_text))
    if missing_keys:
        errors.append("analysis state is missing keys: " + ", ".join(missing_keys))

    mode = scalar_value(state_text, "analysis_mode")
    phase = scalar_value(state_text, "phase")
    synthesis = scalar_value(state_text, "synthesis_status")
    business_model = scalar_value(state_text, "business_model_status")
    publication = scalar_value(state_text, "publication_status")
    source_commit = scalar_value(state_text, "source_commit")
    schema_version = scalar_value(state_text, "workflow_schema_version")
    repository_path = scalar_value(state_text, "repository_path")
    current_stage = scalar_value(state_text, "current_stage")
    stage_status = scalar_value(state_text, "stage_status")
    active_transaction = scalar_value(state_text, "active_transaction")
    last_committed_stage = scalar_value(state_text, "last_committed_stage")
    migration_status = scalar_value(state_text, "migration_status")

    if scalar_value(state_text, "artifact_type") != "analysis-state":
        errors.append("artifact_type must be analysis-state")
    if scalar_value(state_text, "artifact_schema_version") != "1":
        errors.append("analysis-state artifact_schema_version must be 1")
    if schema_version != "3":
        errors.append("workflow_schema_version must be 3; run stage_executor.py resume for legacy state")
    if mode not in ALLOWED_MODES:
        errors.append("analysis_mode must be automatic; targeted analysis is not supported")
    if phase not in ALLOWED_PHASES:
        errors.append("phase must be inventory, tracing, synthesis, publishing, or completed")
    if current_stage not in ALLOWED_STAGES:
        errors.append("current_stage is not a supported workflow stage")
    if stage_status not in ALLOWED_STAGE_STATUS:
        errors.append("stage_status must be pending, in-progress, failed, committed, or skipped")
    if synthesis not in ALLOWED_SYNTHESIS:
        errors.append("synthesis_status must be pending, complete, or partial")
    if business_model not in ALLOWED_BUSINESS_MODEL:
        errors.append("business_model_status must be pending, complete, partial, or blocked")
    if publication not in ALLOWED_PUBLICATION:
        errors.append("publication_status must be pending, in-progress, stale, or complete")
    if migration_status not in ALLOWED_MIGRATION:
        errors.append(
            "migration_status must be not-required, planned, in-progress, committed, or blocked"
        )

    if scalar_value(catalog_text, "repository") != scalar_value(state_text, "repository"):
        errors.append("state and catalog must have the same repository")
    if scalar_value(catalog_text, "artifact_type") != "working-behavior-catalog":
        errors.append("working catalog artifact_type must be working-behavior-catalog")
    if scalar_value(catalog_text, "artifact_schema_version") != "1":
        errors.append("working catalog artifact_schema_version must be 1")
    if scalar_value(catalog_text, "source_commit") != source_commit:
        errors.append("state and catalog must have the same source_commit")
    if scalar_value(catalog_text, "analysis_mode") != mode:
        errors.append("state and catalog must have the same analysis_mode")

    if repository_path:
        try:
            if Path(repository_path).expanduser().resolve() != args.repo.expanduser().resolve():
                errors.append("repository_path does not match --repo")
        except OSError:
            errors.append("repository_path could not be resolved")

    expected_phase = (
        current_stage
        if current_stage in {"inventory", "tracing", "synthesis"}
        else "completed"
        if current_stage == "completed"
        else "publishing"
    )
    if current_stage in ALLOWED_STAGES and phase != expected_phase:
        errors.append(f"phase {phase} is inconsistent with current_stage {current_stage}")
    if stage_status in {"in-progress", "failed"} and not active_transaction:
        errors.append(f"stage_status {stage_status} requires active_transaction")
    if stage_status in {"pending", "committed", "skipped"} and active_transaction:
        errors.append(f"stage_status {stage_status} cannot retain active_transaction")
    if last_committed_stage and last_committed_stage not in ALLOWED_STAGES - {"completed"}:
        errors.append("last_committed_stage is not a supported committed stage")

    git_commit = current_git_commit(args.repo)
    if git_commit is None:
        warnings.append("repository commit could not be read; source_commit was not compared with Git")
    elif source_commit and source_commit.lower() not in {"unknown", "git-commit-or-unknown"}:
        if source_commit != git_commit:
            errors.append(f"analysis state commit {source_commit} does not match repository HEAD {git_commit}")

    state_entries = behavior_entries(state_text)
    catalog_entries = behavior_entries(catalog_text)
    state_by_id: dict[str, dict[str, str | None]] = {}
    for entry in state_entries:
        behavior_id = entry.get("behavior_id")
        if not behavior_id:
            errors.append("analysis state contains a behavior without behavior_id")
            continue
        if behavior_id in state_by_id:
            errors.append(f"duplicate behavior in analysis state: {behavior_id}")
            continue
        state_by_id[behavior_id] = entry
        status = entry.get("status")
        if status not in ALLOWED_BEHAVIOR_STATUS:
            errors.append(f"invalid state for {behavior_id}: {status}")
            continue
        if status in {"tracing", "understood", "blocked"}:
            dossier = dossier_path(args.state, args.dossiers_dir, entry.get("dossier"), behavior_id)
            if not dossier.is_file():
                errors.append(f"{status} behavior is missing its dossier: {behavior_id}")
            elif dossier_behavior_id(dossier) != behavior_id:
                errors.append(f"dossier behavior_id does not match state: {dossier}")

    catalog_ids: set[str] = set()
    for entry in catalog_entries:
        behavior_id = entry.get("behavior_id")
        if not behavior_id:
            errors.append("catalog contains a behavior without behavior_id")
            continue
        catalog_ids.add(behavior_id)
        status = entry.get("status")
        if status not in CATALOG_WITHOUT_DOSSIER and behavior_id not in state_by_id:
            errors.append(f"catalog behavior has no analysis-state entry: {behavior_id}")

    for behavior_id in state_by_id:
        if behavior_id not in catalog_ids:
            errors.append(f"analysis-state behavior is missing from catalog: {behavior_id}")

    if args.require_publishable:
        if phase not in {"synthesis", "publishing", "completed"}:
            errors.append("publishable state requires phase synthesis, publishing, or completed")
        incomplete = sorted(
            behavior_id
            for behavior_id, entry in state_by_id.items()
            if entry.get("status") not in {"understood", "blocked"}
        )
        if incomplete:
            errors.append("publishable state has untraced behavior(s): " + ", ".join(incomplete))
        if synthesis != "complete":
            errors.append("full-repository publication requires synthesis_status: complete")

    if args.require_ba_publishable:
        if phase not in {"publishing", "completed"}:
            errors.append("BA publication requires phase publishing or completed")
        incomplete = sorted(
            behavior_id
            for behavior_id, entry in state_by_id.items()
            if entry.get("status") not in {"understood", "blocked"}
        )
        if incomplete:
            errors.append("BA-publishable state has untraced behavior(s): " + ", ".join(incomplete))
        if synthesis != "complete":
            errors.append("BA publication requires synthesis_status: complete")
        if business_model not in {"complete", "partial"}:
            errors.append(
                "BA publication requires business_model_status: complete or partial"
            )

    if phase == "completed" and publication != "complete":
        errors.append("phase completed requires publication_status: complete")
    if phase == "completed" and business_model == "pending":
        errors.append("phase completed requires the Business Model to be complete, partial, or blocked")
    if publication == "complete" and phase != "completed":
        errors.append("publication_status complete requires phase: completed")

    if current_stage == "completed":
        if stage_status != "committed":
            errors.append("current_stage completed requires stage_status: committed")
        if last_committed_stage != "finalization":
            errors.append("current_stage completed requires last_committed_stage: finalization")
        receipts = args.state.parent / "execution" / "receipts"
        final_receipt_found = False
        if receipts.is_dir():
            for receipt in receipts.glob("*.json"):
                try:
                    payload = json.loads(receipt.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if payload.get("stage") == "finalization" and payload.get("result") == "committed":
                    final_receipt_found = True
                    break
        if not final_receipt_found and not args.allow_missing_final_receipt:
            errors.append("completed workflow requires a committed finalization receipt")

    placeholders = ("repository-name", "git-commit-or-unknown", "repository.behavior-name")
    if any(placeholder in state_text for placeholder in placeholders):
        errors.append("template placeholders remain in analysis state")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(
        f"OK: {len(state_entries)} state behavior(s), {len(catalog_entries)} catalog behavior(s), "
        f"phase={phase}, stage={current_stage}, stage_status={stage_status}, "
        f"synthesis={synthesis}, business_model={business_model}, "
        f"{len(warnings)} warning(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
