#!/usr/bin/env python3
"""Validate that the evidence index still matches the repository snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from runtime_guard import run_guarded
from build_evidence_index import IGNORED_DIRS, git_commit, is_candidate


def current_candidate_paths(repo: Path) -> set[str]:
    paths: set[str] = set()
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(repo)
        if any(part in IGNORED_DIRS for part in relative_path.parts):
            continue
        if is_candidate(path):
            paths.add(relative_path.as_posix())
    return paths


def validate_evidence_index(
    index_path: Path,
    repo: Path,
    expected_repository: str | None = None,
    expected_commit: str | None = None,
) -> tuple[list[str], list[str], dict[str, object] | None]:
    errors: list[str] = []
    warnings: list[str] = []
    repo = repo.expanduser().resolve()
    if not index_path.is_file():
        return [f"evidence index does not exist: {index_path}"], warnings, None
    try:
        indexed = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"evidence index is not valid JSON: {exc}"], warnings, None
    if not isinstance(indexed, dict):
        return ["evidence index root must be an object"], warnings, None

    if expected_repository is not None and indexed.get("repository") != expected_repository:
        errors.append("evidence index repository does not match manifest")
    actual_commit = git_commit(repo)
    indexed_commit = indexed.get("source_commit")
    if actual_commit is not None:
        if indexed_commit != actual_commit:
            errors.append("evidence index source_commit does not match current repository HEAD")
        if expected_commit is not None and expected_commit != actual_commit:
            errors.append("manifest source_commit does not match current repository HEAD")
    elif indexed_commit is not None:
        errors.append("evidence index records a Git commit but repository has no readable HEAD")
    elif expected_commit not in {None, "unknown"}:
        errors.append("manifest records a commit but repository has no readable HEAD")

    files = indexed.get("files")
    skipped = indexed.get("skipped")
    summary = indexed.get("summary")
    if not isinstance(files, list) or not isinstance(skipped, list) or not isinstance(summary, dict):
        errors.append("evidence index must contain files, skipped, and summary structures")
        return errors, warnings, indexed
    if summary.get("indexed_files") != len(files):
        errors.append("evidence index indexed_files count does not match files")
    if summary.get("skipped_files") != len(skipped):
        errors.append("evidence index skipped_files count does not match skipped")
    if not isinstance(summary.get("marker_counts"), dict):
        errors.append("evidence index summary.marker_counts must be an object")

    indexed_paths: set[str] = set()
    current_file_items: list[tuple[str, str]] = []
    observed_marker_counts: dict[str, int] = {}
    for item in files:
        if not isinstance(item, dict):
            errors.append("evidence index files entries must be objects")
            continue
        relative = item.get("path")
        expected_hash = item.get("sha256")
        if not isinstance(relative, str) or not relative:
            errors.append("evidence index file entry has no path")
            continue
        if relative in indexed_paths:
            errors.append(f"evidence index contains duplicate path: {relative}")
            continue
        indexed_paths.add(relative)
        source = (repo / relative).resolve()
        try:
            source.relative_to(repo)
        except ValueError:
            errors.append(f"evidence index path escapes repository: {relative}")
            continue
        if not source.is_file():
            errors.append(f"indexed repository file is missing: {relative}")
            continue
        actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        current_file_items.append((relative, actual_hash))
        if expected_hash != actual_hash:
            errors.append(f"indexed repository file changed after evidence indexing: {relative}")
        markers = item.get("markers")
        if not isinstance(markers, dict):
            errors.append(f"evidence index file has invalid markers object: {relative}")
        else:
            for kind, occurrences in markers.items():
                if not isinstance(occurrences, list):
                    errors.append(f"evidence index marker list is invalid for {relative}:{kind}")
                    continue
                observed_marker_counts[str(kind)] = observed_marker_counts.get(str(kind), 0) + len(occurrences)
                for occurrence in occurrences:
                    if not isinstance(occurrence, dict) or not isinstance(occurrence.get("line"), int):
                        errors.append(f"evidence index marker is invalid for {relative}:{kind}")
                    elif set(occurrence) != {"line"}:
                        errors.append(
                            f"evidence index marker must contain location only, not source text: {relative}:{kind}"
                        )

    expected_marker_counts = summary.get("marker_counts")
    if isinstance(expected_marker_counts, dict) and expected_marker_counts != dict(sorted(observed_marker_counts.items())):
        errors.append("evidence index marker_counts do not match indexed marker locations")

    skipped_paths: set[str] = set()
    current_skipped_items: list[tuple[str, str]] = []
    for item in skipped:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append("evidence index skipped entries must contain a path")
            continue
        relative = str(item["path"])
        skipped_paths.add(relative)
        source = (repo / relative).resolve()
        if not source.is_file():
            continue
        actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        current_skipped_items.append((relative, actual_hash))
        if item.get("sha256") != actual_hash:
            errors.append(f"skipped repository file changed after evidence indexing: {relative}")
    represented = indexed_paths | skipped_paths
    current = current_candidate_paths(repo)
    for relative in sorted(current - represented):
        errors.append(f"repository candidate file was added after evidence indexing: {relative}")
    for relative in sorted(represented - current):
        errors.append(f"indexed candidate file is no longer present: {relative}")

    fingerprint_input = "\n".join(
        f"{relative}:{digest}" for relative, digest in sorted(current_file_items)
    ) + "\n" + "\n".join(
        f"SKIPPED:{relative}:{digest}" for relative, digest in sorted(current_skipped_items)
    )
    actual_fingerprint = "sha256:" + hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()
    if indexed.get("repository_fingerprint") != actual_fingerprint:
        errors.append("evidence index repository_fingerprint is stale or invalid")
    return errors, warnings, indexed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--repository")
    parser.add_argument("--source-commit")
    args = parser.parse_args()

    errors, warnings, indexed = validate_evidence_index(
        args.index,
        args.repo,
        args.repository,
        args.source_commit,
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    file_count = len(indexed.get("files", [])) if indexed else 0
    print(f"OK: evidence index matches the current repository snapshot (files={file_count})")
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
