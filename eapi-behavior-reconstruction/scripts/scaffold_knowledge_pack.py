#!/usr/bin/env python3
"""Create the deterministic static skeleton for one repository knowledge pack."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from runtime_guard import (
    RuntimeGuardError,
    atomic_write_text,
    ensure_output_directory,
    reject_tree_overlap,
    resolve_outside_skill,
    run_guarded,
    validate_output_target,
)


TEMPLATE_MAP = {
    "knowledge-manifest-template.yaml": "knowledge-manifest.yaml",
    "knowledge-map-template.md": "knowledge-map.md",
    "coverage-report-template.md": "coverage-report.md",
    "repository-overview-template.md": "tech-pack/repository-overview.md",
    "behavior-catalog-template.yaml": "tech-pack/behavior-catalog.yaml",
    "endpoint-matrix-template.md": "tech-pack/endpoints/endpoint-matrix.md",
    "data-asset-catalog-template.md": "tech-pack/data/data-asset-catalog.md",
    "data-lineage-template.md": "tech-pack/data/data-lineage.md",
    "state-transition-matrix-template.md": "tech-pack/data/state-transition-matrix.md",
    "field-catalog-template.md": "tech-pack/fields/field-catalog.md",
    "validation-rule-matrix-template.md": "tech-pack/fields/validation-rule-matrix.md",
    "field-lineage-template.md": "tech-pack/fields/field-lineage.md",
    "external-http-mapping-matrix-template.md": "tech-pack/fields/external-http-mapping-matrix.md",
    "runtime-config-matrix-template.md": "tech-pack/runtime/runtime-config-matrix.md",
    "dependency-matrix-template.md": "tech-pack/dependencies/dependency-matrix.md",
    "failure-taxonomy-template.md": "tech-pack/reliability/failure-taxonomy.md",
    "ba-overview-template.md": "ba-pack/business-overview.md",
    "ba-capability-map-template.md": "ba-pack/capability-map.md",
    "ba-business-data-lifecycle-template.md": "ba-pack/business-data-lifecycle.md",
    "ba-business-rule-catalog-template.md": "ba-pack/business-rule-catalog.md",
    "ba-business-exception-catalog-template.md": "ba-pack/business-exception-catalog.md",
    "ba-behavior-catalog-template.md": "ba-pack/behavior-catalog.md",
}

PROTECTED_SEED_MAP = {
    "claim-ledger-template.json": ".work/claim-ledger.json",
    "claim-audit-template.json": ".work/claim-audit.json",
}

DYNAMIC_DIRECTORIES = (
    ".work",
    ".work/flow-models",
    "tech-pack/behaviors",
    "tech-pack/endpoints/contracts",
    "tech-pack/dependencies/stubs",
    "ba-pack/behaviors",
)


def git_commit(repo: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite only static document destinations; claims and dynamic documents are never overwritten",
    )
    args = parser.parse_args()

    repo = args.repo.expanduser().resolve()
    output = resolve_outside_skill(args.output, label="scaffold output")
    if not repo.is_dir():
        print(f"ERROR: repository directory does not exist: {repo}", file=sys.stderr)
        return 2
    try:
        reject_tree_overlap(
            output,
            repo,
            label="scaffold output",
            protected_label="the analyzed repository",
        )
    except RuntimeGuardError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    assets = Path(__file__).resolve().parent.parent / "assets"
    missing_templates = [
        name for name in (*TEMPLATE_MAP, *PROTECTED_SEED_MAP) if not (assets / name).is_file()
    ]
    if missing_templates:
        print("ERROR: missing template(s): " + ", ".join(missing_templates), file=sys.stderr)
        return 2

    # Validate the complete write set before creating or replacing anything so
    # a later unsafe link cannot leave a partially updated pack.
    for directory in DYNAMIC_DIRECTORIES:
        validate_output_target(output / directory, output, label=f"pack directory {directory}")
    for relative in TEMPLATE_MAP.values():
        validate_output_target(output / relative, output, label=f"scaffold document {relative}")
    for relative in PROTECTED_SEED_MAP.values():
        destination = validate_output_target(
            output / relative,
            output,
            label=f"protected seed {relative}",
        )
        if destination.exists():
            if not destination.is_file() or destination.stat().st_nlink != 1:
                raise RuntimeGuardError(
                    f"protected seed must be one regular, non-hardlinked file: {destination}"
                )

    existing = [
        relative
        for relative in TEMPLATE_MAP.values()
        if (output / relative).exists() or (output / relative).is_symlink()
    ]
    if existing and not args.force:
        print(
            "ERROR: static knowledge-pack files already exist; use --force to overwrite them: "
            + ", ".join(existing[:5])
            + (" ..." if len(existing) > 5 else ""),
            file=sys.stderr,
        )
        return 1

    repository_name = repo.name
    source_commit = git_commit(repo)
    for directory in DYNAMIC_DIRECTORIES:
        ensure_output_directory(output / directory, output, label=f"pack directory {directory}")

    written: list[str] = []
    for template_name, relative in TEMPLATE_MAP.items():
        template = (assets / template_name).read_text(encoding="utf-8")
        populated = template.replace("repository-name", repository_name).replace(
            "git-commit-or-unknown", source_commit
        )
        destination = output / relative
        atomic_write_text(
            destination,
            populated,
            output_root=output,
            label=f"scaffold document {relative}",
        )
        written.append(relative)

    for template_name, relative in PROTECTED_SEED_MAP.items():
        destination = output / relative
        ensure_output_directory(destination.parent, output, label=f"seed parent {relative}")
        if destination.is_symlink():
            raise RuntimeGuardError(f"write boundary violation: seed document is a symbolic link: {destination}")
        if destination.exists():
            if not destination.is_file() or destination.stat().st_nlink != 1:
                raise RuntimeGuardError(
                    f"protected seed must be one regular, non-hardlinked file: {destination}"
                )
            continue
        template = (assets / template_name).read_text(encoding="utf-8")
        populated = template.replace("repository-name", repository_name).replace(
            "git-commit-or-unknown", source_commit
        )
        atomic_write_text(
            destination,
            populated,
            output_root=output,
            label=f"seed document {relative}",
        )
        written.append(relative)

    print(
        f"OK: scaffolded {len(written)} static document(s) for {repository_name} "
        f"at commit {source_commit} under {output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
