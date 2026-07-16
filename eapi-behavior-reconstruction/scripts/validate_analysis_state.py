#!/usr/bin/env python3
"""Validate mechanical analysis-state, catalog, dossier, and publish-gate consistency."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_KEYS = {
    "repository",
    "source_commit",
    "analysis_mode",
    "phase",
    "synthesis_status",
    "publication_status",
    "output_directory",
    "behaviors",
}
ALLOWED_MODES = {"automatic"}
ALLOWED_PHASES = {"inventory", "tracing", "synthesis", "publishing", "completed"}
ALLOWED_SYNTHESIS = {"pending", "complete", "partial"}
ALLOWED_PUBLICATION = {"pending", "in-progress", "complete"}
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
    publication = scalar_value(state_text, "publication_status")
    source_commit = scalar_value(state_text, "source_commit")

    if mode not in ALLOWED_MODES:
        errors.append("analysis_mode must be automatic; targeted analysis is not supported")
    if phase not in ALLOWED_PHASES:
        errors.append("phase must be inventory, tracing, synthesis, publishing, or completed")
    if synthesis not in ALLOWED_SYNTHESIS:
        errors.append("synthesis_status must be pending, complete, or partial")
    if publication not in ALLOWED_PUBLICATION:
        errors.append("publication_status must be pending, in-progress, or complete")

    if scalar_value(catalog_text, "repository") != scalar_value(state_text, "repository"):
        errors.append("state and catalog must have the same repository")
    if scalar_value(catalog_text, "source_commit") != source_commit:
        errors.append("state and catalog must have the same source_commit")
    if scalar_value(catalog_text, "analysis_mode") != mode:
        errors.append("state and catalog must have the same analysis_mode")

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

    if phase == "completed" and publication != "complete":
        errors.append("phase completed requires publication_status: complete")
    if publication == "complete" and phase != "completed":
        errors.append("publication_status complete requires phase: completed")

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
        f"phase={phase}, synthesis={synthesis}, {len(warnings)} warning(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
