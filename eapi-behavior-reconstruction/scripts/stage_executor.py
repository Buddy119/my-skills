#!/usr/bin/env python3
"""Run recoverable mechanical stages for an EAPI repository knowledge pack.

The executor deliberately does not generate or judge repository knowledge.  It owns
only lifecycle state, candidate snapshots, mechanical gates, validation, archives,
promotion journals, receipts, and recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from artifact_schema import (
    ArtifactSchemaError,
    add_artifact_metadata,
    artifact_metadata,
    build_migration_plan,
    current_pack_is_versioned,
    load_migration_plan,
    load_registry,
    migration_allowed_paths,
    source_snapshot,
    validate_artifact_manifest,
    validate_plan_snapshot,
    validate_template_contract,
    write_artifact_manifest,
    write_migration_plan,
)
from register_schema import (
    RegisterSchemaError,
    load_register_schema,
    validate_bundled_contract,
    validate_register_file,
)


WORKFLOW_SCHEMA_VERSION = "3"
MIGRATION_STAGE = "migration"
STAGES = (
    "inventory",
    "tracing",
    "synthesis",
    "tech-publication",
    "api-contract-publication",
    "business-model",
    "ba-publication",
    "finalization",
    "completed",
)
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGES)}
ALLOWED_STAGE_STATUS = {"pending", "in-progress", "failed", "committed", "skipped"}
ALLOWED_BEHAVIOR_STATUS = {"discovered", "tracing", "understood", "blocked"}
REGISTER_HEADINGS = {
    "Endpoint evidence records",
    "Endpoint reconciliation",
    "Business objects, data resources, and state changes",
    "Field validation and internal transformation observations",
    "Outbound HTTP operation records",
    "Outbound HTTP operation usages",
    "External HTTP field mapping records",
    "Runtime configuration effects",
    "External dependency observations",
    "Dependency contract records",
    "Dependency operation records",
    "Failure observations",
    "Failure pattern reconciliation",
    "Cross-behavior relationships",
    "Register conflicts and unresolved items",
}
SYNTHESIS_HEADINGS = {
    "Observable repository responsibility",
    "Capability and behavior model",
    "Behavior relationships",
    "Business objects and data lifecycle",
    "Endpoint and contract model",
    "Outbound HTTP operation and mapping model",
    "Runtime configuration effects",
    "Dependency contract model",
    "Repository-wide failure pattern model",
    "Repository connection model",
    "Shared behavior model",
    "Coverage, conflicts, and unknowns",
    "Publication decisions",
}
BUSINESS_MODEL_HEADINGS = {
    "Observable business boundary",
    "Business capabilities",
    "Actors and participants",
    "Business objects and lifecycle",
    "Journey records",
    "Scenario records",
    "Shared business rules",
    "Business-visible exceptions",
    "Journey–Scenario relationships",
    "Tech coverage and BA disposition",
    "Publication decisions",
}
SNAPSHOT_EXCLUDED_PREFIXES = {
    ".work/execution/active.lock",
    ".work/execution/transactions",
    ".work/execution/archive",
    ".work/legacy-ba-pack",
    ".work/legacy-artifacts",
}
STATE_FILE = Path(".work/analysis-state.yaml")


class ExecutorError(RuntimeError):
    """A user-correctable workflow error."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def emit(payload: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, sort_keys=True)
        else:
            rendered = str(value)
        print(f"{key}: {rendered}")


def unquote(value: str) -> str | None:
    value = value.strip()
    if value.lower() in {"null", "none", "~"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        try:
            return json.loads(value) if value[0] == '"' else value[1:-1]
        except json.JSONDecodeError:
            return value[1:-1]
    return value


def yaml_scalar(value: str | None) -> str:
    return "null" if value is None else json.dumps(str(value), ensure_ascii=False)


def scalar_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(?P<value>[^\n#]+?)\s*$", text, re.M)
    return unquote(match.group("value")) if match else None


def set_scalar(text: str, key: str, value: str | None) -> str:
    line = f"{key}: {yaml_scalar(value)}"
    pattern = re.compile(rf"^{re.escape(key)}:\s*[^\n]*(?:\n|$)", re.M)
    if pattern.search(text):
        return pattern.sub(line + "\n", text, count=1)
    behavior_match = re.search(r"^behaviors:\s*", text, re.M)
    if behavior_match:
        return text[: behavior_match.start()] + line + "\n" + text[behavior_match.start() :]
    return text.rstrip() + "\n" + line + "\n"


def behavior_entries(text: str) -> list[dict[str, str | None]]:
    match = re.search(r"^behaviors:\s*(?:\[\])?\s*\n(?P<body>(?:[ \t]+[^\n]*(?:\n|$))*)", text, re.M)
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


def update_behavior(
    text: str,
    behavior_id: str,
    status: str,
    dossier: str | None,
    notes: str | None,
) -> str:
    lines = text.splitlines()
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        match = re.match(r"^\s*-\s+behavior_id:\s*(.+?)\s*$", line)
        if not match:
            continue
        found = unquote(match.group(1))
        if start is not None:
            end = index
            break
        if found == behavior_id:
            start = index
    if start is None:
        raise ExecutorError(f"behavior is not present in analysis state: {behavior_id}")

    def replace_field(name: str, value: str | None) -> None:
        nonlocal end
        rendered = f"    {name}: {yaml_scalar(value)}"
        for index in range(start + 1, end):
            if re.match(rf"^\s+{re.escape(name)}:\s*", lines[index]):
                lines[index] = rendered
                return
        lines.insert(end, rendered)
        end += 1

    replace_field("status", status)
    if dossier is not None:
        replace_field("dossier", dossier)
    if notes is not None:
        replace_field("notes", notes)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExecutorError(f"cannot read JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExecutorError(f"JSON object expected: {path}")
    return value


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


def source_commit(repo: Path) -> str:
    return current_git_commit(repo) or "unknown"


def phase_for_stage(stage: str) -> str:
    if stage in {"inventory", "tracing", "synthesis"}:
        return stage
    if stage == "completed":
        return "completed"
    return "publishing"


def previous_stage(stage: str) -> str | None:
    index = STAGE_INDEX[stage]
    return STAGES[index - 1] if index > 0 else None


def next_stage(stage: str) -> str:
    index = STAGE_INDEX[stage]
    if index + 1 >= len(STAGES):
        return "completed"
    return STAGES[index + 1]


def normalized_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ExecutorError(f"path escapes output root: {path}") from exc


def is_snapshot_excluded(relative: str) -> bool:
    return any(relative == prefix or relative.startswith(prefix + "/") for prefix in SNAPSHOT_EXCLUDED_PREFIXES)


def snapshot_copy(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source).as_posix()
        if is_snapshot_excluded(relative):
            continue
        target = destination / relative
        if path.is_symlink():
            raise ExecutorError(f"output snapshots do not support symbolic links: {path}")
        elif path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_manifest(root: Path) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return manifest
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if is_snapshot_excluded(relative):
            continue
        stat = path.stat()
        manifest[relative] = {
            "size": stat.st_size,
            "sha256": sha256_file(path),
        }
    return manifest


def directory_set(root: Path) -> set[str]:
    directories: set[str] = set()
    if not root.exists():
        return directories
    for path in root.rglob("*"):
        if not path.is_dir() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if not is_snapshot_excluded(relative):
            directories.add(relative)
    return directories


def manifest_summary(manifest: dict[str, dict[str, Any]]) -> dict[str, int]:
    return {
        "files": len(manifest),
        "bytes": sum(int(item["size"]) for item in manifest.values()),
    }


def manifest_diff(
    current: dict[str, dict[str, Any]], candidate: dict[str, dict[str, Any]]
) -> dict[str, list[str]]:
    current_paths = set(current)
    candidate_paths = set(candidate)
    return {
        "added": sorted(candidate_paths - current_paths),
        "changed": sorted(
            path for path in current_paths & candidate_paths if current[path] != candidate[path]
        ),
        "deleted": sorted(current_paths - candidate_paths),
    }


def directory_diff(current_root: Path, candidate_root: Path) -> dict[str, list[str]]:
    current = directory_set(current_root)
    candidate = directory_set(candidate_root)
    return {
        "added": sorted(candidate - current),
        "deleted": sorted(current - candidate),
    }


def state_path(output: Path) -> Path:
    return output / STATE_FILE


def execution_root(output: Path) -> Path:
    return output / ".work" / "execution"


def lock_path(output: Path) -> Path:
    return execution_root(output) / "active.lock"


def transaction_dir(output: Path, transaction_id: str) -> Path:
    return execution_root(output) / "transactions" / transaction_id


def state_text(output: Path) -> str:
    path = state_path(output)
    if not path.is_file():
        raise ExecutorError(f"analysis state does not exist: {path}")
    return path.read_text(encoding="utf-8")


def state_repository(text: str) -> Path:
    repository_path = scalar_value(text, "repository_path")
    if not repository_path:
        raise ExecutorError("analysis state is missing repository_path; run resume to upgrade it")
    return Path(repository_path).expanduser().resolve()


def verify_repo_and_commit(text: str, repo_override: Path | None = None) -> tuple[Path, str]:
    repo = repo_override.expanduser().resolve() if repo_override is not None else state_repository(text)
    if not repo.is_dir():
        raise ExecutorError(f"repository directory does not exist: {repo}")
    recorded_path = scalar_value(text, "repository_path")
    if recorded_path and Path(recorded_path).expanduser().resolve() != repo:
        raise ExecutorError("repository path does not match analysis state")
    recorded_commit = scalar_value(text, "source_commit") or "unknown"
    actual_commit = source_commit(repo)
    if recorded_commit != "unknown" and actual_commit != "unknown" and recorded_commit != actual_commit:
        raise ExecutorError(
            f"repository commit mismatch: state={recorded_commit}, current={actual_commit}"
        )
    return repo, actual_commit


def acquire_lock(output: Path, payload: dict[str, Any]) -> None:
    path = lock_path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        try:
            existing = read_json(path)
        except ExecutorError:
            existing = {"status": "unreadable"}
        raise ExecutorError(f"an active workflow lock already exists: {existing}") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def release_lock(output: Path, transaction_id: str) -> None:
    path = lock_path(output)
    if not path.exists():
        return
    lock = read_json(path)
    if lock.get("transaction_id") != transaction_id:
        raise ExecutorError("refusing to remove a lock owned by another transaction")
    path.unlink()


def template_root() -> Path:
    return Path(__file__).resolve().parent.parent / "assets"


def render_template(name: str, repository: str, commit: str) -> str:
    text = (template_root() / name).read_text(encoding="utf-8")
    return text.replace("repository-name", repository).replace("git-commit-or-unknown", commit)


def initial_state(repository: str, repository_path: Path, commit: str, output: Path) -> str:
    return (
        f"artifact_type: {yaml_scalar('analysis-state')}\n"
        f"artifact_schema_version: {yaml_scalar('1')}\n"
        f"workflow_schema_version: {yaml_scalar(WORKFLOW_SCHEMA_VERSION)}\n"
        f"repository: {yaml_scalar(repository)}\n"
        f"repository_path: {yaml_scalar(str(repository_path))}\n"
        f"source_commit: {yaml_scalar(commit)}\n"
        f"analysis_mode: {yaml_scalar('automatic')}\n"
        f"phase: {yaml_scalar('inventory')}\n"
        f"current_stage: {yaml_scalar('inventory')}\n"
        f"stage_status: {yaml_scalar('pending')}\n"
        "active_transaction: null\n"
        "last_committed_stage: null\n"
        f"migration_status: {yaml_scalar('not-required')}\n"
        f"synthesis_status: {yaml_scalar('pending')}\n"
        f"business_model_status: {yaml_scalar('pending')}\n"
        f"publication_status: {yaml_scalar('pending')}\n"
        f"output_directory: {yaml_scalar(str(output))}\n"
        "behaviors: []\n"
    )


def initial_catalog(repository: str, commit: str) -> str:
    return (
        f"artifact_type: {yaml_scalar('working-behavior-catalog')}\n"
        f"artifact_schema_version: {yaml_scalar('1')}\n"
        f"repository: {yaml_scalar(repository)}\n"
        f"source_commit: {yaml_scalar(commit)}\n"
        f"analysis_mode: {yaml_scalar('automatic')}\n"
        "behaviors: []\n"
        "summary:\n"
        "  discovered: 0\n"
        "  documented: 0\n"
        "  technical: 0\n"
        "  duplicate: 0\n"
        "  excluded: 0\n"
        "  blocked: 0\n"
    )


def write_receipt(output: Path, sequence: int, stage: str, payload: dict[str, Any]) -> Path:
    receipts = execution_root(output) / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    path = receipts / f"{sequence:03d}-{stage}.json"
    payload = {
        "artifact_type": "stage-receipt",
        "artifact_schema_version": "1",
        **payload,
    }
    atomic_write_json(path, payload)
    return path


def receipt_count(output: Path) -> int:
    receipts = execution_root(output) / "receipts"
    return len(list(receipts.glob("*.json"))) if receipts.is_dir() else 0


def receipt_for_transaction(output: Path, transaction_id: str) -> Path | None:
    receipts = execution_root(output) / "receipts"
    if not receipts.is_dir():
        return None
    for path in sorted(receipts.glob("*.json")):
        try:
            payload = read_json(path)
        except ExecutorError:
            continue
        if payload.get("transaction_id") == transaction_id and payload.get("result") == "committed":
            return path
    return None


def committed_finalization_receipt(output: Path) -> Path | None:
    receipts = execution_root(output) / "receipts"
    if not receipts.is_dir():
        return None
    for path in sorted(receipts.glob("*.json")):
        try:
            payload = read_json(path)
        except ExecutorError:
            continue
        if payload.get("stage") == "finalization" and payload.get("result") == "committed":
            return path
    return None


def audit_archive_directory(path: Path) -> dict[str, Any]:
    manifest_path = path / "archive-manifest.json"
    if not manifest_path.is_file():
        return {"path": str(path), "valid": False, "error": "archive-manifest.json is missing"}
    try:
        declared = read_json(manifest_path).get("files", {})
    except ExecutorError as exc:
        return {"path": str(path), "valid": False, "error": str(exc)}
    actual = file_manifest(path)
    actual.pop("archive-manifest.json", None)
    valid = declared == actual
    return {
        "path": str(path),
        "valid": valid,
        "declared": manifest_summary(declared) if isinstance(declared, dict) else None,
        "actual": manifest_summary(actual),
        "error": None if valid else "archive file count, size, or checksum differs from its manifest",
    }


def temporary_paths(output: Path) -> list[str]:
    found: list[str] = []
    for path in output.rglob("*"):
        if path.name.endswith(".tmp") or (path.name.startswith(".") and ".tmp" in path.name):
            found.append(path.relative_to(output).as_posix())
    return sorted(found)


def command_init(args: argparse.Namespace) -> int:
    repo = args.repo.expanduser().resolve()
    output = args.output.expanduser().resolve()
    template = template_root() / "repository-register-template.md"
    try:
        bundled_check = validate_bundled_contract(template)
        registry = load_registry()
    except RegisterSchemaError as exc:
        raise ExecutorError(f"bundled Register Schema is invalid: {exc}") from exc
    except ArtifactSchemaError as exc:
        raise ExecutorError(f"bundled Artifact Schema is invalid: {exc}") from exc
    if not bundled_check.valid:
        details = list(bundled_check.errors)
        details.extend(
            message
            for messages in bundled_check.domain_errors.values()
            for message in messages
        )
        raise ExecutorError(
            "bundled Register Schema and template are out of sync: " + " | ".join(details)
        )
    template_errors = validate_template_contract(registry, template_root())
    if template_errors:
        raise ExecutorError(
            "bundled Artifact Schema and templates are out of sync: "
            + " | ".join(template_errors)
        )
    if not repo.is_dir():
        raise ExecutorError(f"repository directory does not exist: {repo}")
    if output.exists() and any(output.iterdir()):
        raise ExecutorError(f"output directory is not empty; use resume: {output}")
    commit = source_commit(repo)
    repository = repo.name
    (output / ".work" / "behavior-dossiers").mkdir(parents=True, exist_ok=True)
    atomic_write_text(state_path(output), initial_state(repository, repo, commit, output))
    atomic_write_text(output / ".work" / "behavior-catalog.yaml", initial_catalog(repository, commit))
    atomic_write_text(
        output / ".work" / "repository-register.md",
        render_template("repository-register-template.md", repository, commit),
    )
    receipt = {
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "artifact_schema_registry_version": registry.registry_version,
        "repository_register_artifact_schema_version": bundled_check.version,
        "validator_domain_statuses": {},
        "primary_error_count": 0,
        "skipped_group_count": 0,
        "suppressed_error_count": 0,
        "kind": "initialization",
        "repository": str(repo),
        "source_commit": commit,
        "output": str(output),
        "created_at": now_utc(),
        "result": "committed",
    }
    receipt_path = write_receipt(output, 0, "init", receipt)
    write_artifact_manifest(
        output,
        registry,
        str(repo),
        commit,
        "init",
        None,
    )
    manifest_errors = validate_artifact_manifest(output, registry)
    if manifest_errors:
        raise ExecutorError(
            "initial Artifact Manifest is invalid: " + " | ".join(manifest_errors)
        )
    emit(
        {
            "result": "initialized",
            "repository": str(repo),
            "source_commit": commit,
            "output": str(output),
            "current_stage": "inventory",
            "receipt": str(receipt_path),
        },
        args.json,
    )
    return 0


def headings(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return set(re.findall(r"^##\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.M))


def require_paths(root: Path, paths: Iterable[str], errors: list[str]) -> None:
    for relative in paths:
        if not (root / relative).exists():
            errors.append(f"required stage artifact is missing: {relative}")


def validate_heading_set(path: Path, expected: set[str], label: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"{label} does not exist: {path}")
        return
    missing = sorted(expected - headings(path))
    if missing:
        errors.append(f"{label} is missing sections: {', '.join(missing)}")


def run_validator(command: list[str], cwd: Path) -> dict[str, Any]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def validator_commands(stage: str, candidate: Path, repo: Path) -> list[list[str]]:
    scripts = Path(__file__).resolve().parent
    python = sys.executable
    state = candidate / ".work" / "analysis-state.yaml"
    catalog = candidate / ".work" / "behavior-catalog.yaml"
    dossiers = candidate / ".work" / "behavior-dossiers"
    commands: list[list[str]] = []
    if stage in {"tracing", "synthesis", "business-model", "finalization"}:
        command = [
            python,
            str(scripts / "validate_analysis_state.py"),
            str(state),
            "--repo",
            str(repo),
            "--catalog",
            str(catalog),
            "--dossiers-dir",
            str(dossiers),
        ]
        if stage in {"synthesis", "business-model", "finalization"}:
            command.append("--require-publishable")
        if stage == "business-model" and scalar_value(state.read_text(encoding="utf-8"), "business_model_status") in {"complete", "partial"}:
            command.append("--require-ba-publishable")
        if stage == "finalization":
            command.append("--allow-missing-final-receipt")
        commands.append(command)

    if stage in {"tech-publication", "api-contract-publication", "ba-publication", "finalization"}:
        for document in sorted((candidate / "tech-pack" / "behaviors").glob("*.md")):
            command = [python, str(scripts / "validate_behavior_doc.py"), str(document), "--repo", str(repo)]
            if stage in {"tech-publication", "api-contract-publication"}:
                command.append("--allow-missing-ba")
            commands.append(command)

    if stage in {"api-contract-publication", "ba-publication", "finalization"}:
        for document in sorted((candidate / "tech-pack" / "contracts").glob("*.api-contract.md")):
            commands.append(
                [python, str(scripts / "validate_api_contract.py"), str(document), "--repo", str(repo)]
            )

    if stage in {"ba-publication", "finalization"}:
        for document in sorted((candidate / "ba-pack" / "journeys").glob("*.md")):
            commands.append([python, str(scripts / "validate_ba_journey.py"), str(document)])
        for document in sorted((candidate / "ba-pack" / "scenarios").glob("*.md")):
            commands.append([python, str(scripts / "validate_ba_scenario.py"), str(document)])

    if stage in {"api-contract-publication", "ba-publication", "finalization"}:
        commands.append(
            [
                python,
                str(scripts / "validate_pack_links.py"),
                str(candidate),
                "--repo",
                str(repo),
                "--json",
                "--require-artifact-manifest",
            ]
        )
    return commands


def stage_gates(stage: str, candidate: Path, repo: Path) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    try:
        registry = load_registry()
        errors.extend(
            f"Artifact Schema: {message}"
            for message in validate_artifact_manifest(candidate, registry)
        )
    except ArtifactSchemaError as exc:
        errors.append(f"bundled Artifact Schema is invalid: {exc}")
    require_paths(
        candidate,
        [
            ".work/analysis-state.yaml",
            ".work/behavior-catalog.yaml",
            ".work/repository-register.md",
            ".work/behavior-dossiers",
        ],
        errors,
    )
    if stage == "inventory":
        require_paths(candidate, [".work/evidence-index.json"], errors)
        evidence = candidate / ".work" / "evidence-index.json"
        if evidence.is_file():
            try:
                json.loads(evidence.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"evidence index is not valid JSON: {exc}")
    if stage in {"tracing", "synthesis", "tech-publication", "api-contract-publication", "business-model", "ba-publication", "finalization"}:
        state = candidate / ".work" / "analysis-state.yaml"
        if state.is_file():
            incomplete = sorted(
                entry.get("behavior_id") or "<missing-id>"
                for entry in behavior_entries(state.read_text(encoding="utf-8"))
                if entry.get("status") not in {"understood", "blocked"}
            )
            if incomplete:
                errors.append("behavior tracing is incomplete: " + ", ".join(incomplete))
    if stage in {"synthesis", "tech-publication", "api-contract-publication", "business-model", "ba-publication", "finalization"}:
        register = candidate / ".work" / "repository-register.md"
        try:
            schema = load_register_schema()
            register_check = validate_register_file(register, schema)
        except RegisterSchemaError as exc:
            errors.append(f"bundled Register Schema is invalid: {exc}")
        else:
            schema_errors = list(register_check.errors)
            schema_errors.extend(
                message
                for messages in register_check.domain_errors.values()
                for message in messages
            )
            if schema_errors:
                errors.append(
                    "repository register does not match Register Schema "
                    f"{schema.version}: " + " | ".join(schema_errors)
                )
        validate_heading_set(
            register,
            REGISTER_HEADINGS,
            "repository register",
            errors,
        )
        validate_heading_set(
            candidate / ".work" / "repository-synthesis.md",
            SYNTHESIS_HEADINGS,
            "repository synthesis",
            errors,
        )
    if stage in {"tech-publication", "api-contract-publication", "business-model", "ba-publication", "finalization"}:
        require_paths(
            candidate,
            ["tech-pack/repository-overview.md", "tech-pack/behavior-catalog.yaml", "tech-pack/behaviors"],
            errors,
        )
    if stage in {"business-model", "ba-publication", "finalization"}:
        validate_heading_set(
            candidate / ".work" / "business-model.md",
            BUSINESS_MODEL_HEADINGS,
            "business model",
            errors,
        )
    if stage in {"ba-publication", "finalization"}:
        model_status = scalar_value(
            (candidate / ".work" / "analysis-state.yaml").read_text(encoding="utf-8"),
            "business_model_status",
        )
        if model_status in {"complete", "partial"}:
            require_paths(
                candidate,
                ["ba-pack/business-overview.md", "ba-pack/business-catalog.md", "ba-pack/journeys", "ba-pack/scenarios"],
                errors,
            )
        elif stage == "ba-publication" and model_status != "blocked":
            errors.append("BA publication requires business_model_status complete, partial, or blocked")
    if stage == "finalization":
        try:
            invalidated = read_json(candidate / ".work" / "artifact-manifest.json").get(
                "invalidated_artifacts", []
            )
        except ExecutorError as exc:
            errors.append(str(exc))
        else:
            if invalidated:
                errors.append(
                    "finalization cannot commit while Artifact types remain invalidated: "
                    + ", ".join(
                        sorted(
                            str(item.get("artifact_type", "<unknown>"))
                            for item in invalidated
                            if isinstance(item, dict)
                        )
                    )
                )

    results = [run_validator(command, candidate) for command in validator_commands(stage, candidate, repo)]
    for result in results:
        if result["exit_code"] != 0:
            errors.append("validator failed: " + " ".join(result["command"]))
    return errors, results


def candidate_state_for_commit(
    text: str,
    stage: str,
    semantic_result: str | None,
    skipped: bool,
) -> str:
    if stage == "synthesis":
        if semantic_result != "complete":
            raise ExecutorError("synthesis commit requires --semantic-result complete")
        text = set_scalar(text, "synthesis_status", "complete")
    elif stage == "business-model":
        if semantic_result not in {"complete", "partial", "blocked"}:
            raise ExecutorError(
                "business-model commit requires --semantic-result complete, partial, or blocked"
            )
        text = set_scalar(text, "business_model_status", semantic_result)
    elif semantic_result is not None:
        raise ExecutorError(f"--semantic-result is not accepted for stage {stage}")

    upcoming = next_stage(stage)
    text = set_scalar(text, "last_committed_stage", stage)
    text = set_scalar(text, "active_transaction", None)
    if stage == "finalization":
        text = set_scalar(text, "current_stage", "completed")
        text = set_scalar(text, "stage_status", "committed")
        text = set_scalar(text, "phase", "completed")
        text = set_scalar(text, "publication_status", "complete")
    else:
        text = set_scalar(text, "current_stage", upcoming)
        text = set_scalar(text, "stage_status", "pending")
        text = set_scalar(text, "phase", phase_for_stage(upcoming))
        if upcoming in {"tech-publication", "api-contract-publication", "business-model", "ba-publication", "finalization"}:
            text = set_scalar(text, "publication_status", "in-progress")
        else:
            text = set_scalar(text, "publication_status", "pending")
    return text


def stage_skip_allowed(stage: str, candidate: Path, reason: str | None) -> None:
    if not reason or not reason.strip():
        raise ExecutorError("a non-empty --reason is required when skipping a stage")
    state = (candidate / STATE_FILE).read_text(encoding="utf-8")
    if stage == "api-contract-publication":
        contracts = list((candidate / "tech-pack" / "contracts").glob("*.api-contract.md"))
        if contracts:
            raise ExecutorError("cannot skip API Contract publication while application contracts exist")
        return
    if stage == "ba-publication" and scalar_value(state, "business_model_status") == "blocked":
        return
    raise ExecutorError(f"stage cannot be skipped: {stage}")


def _migration_plan_path(output: Path, requested: Path | None) -> Path:
    expected = (output / ".work" / "migration-plan.yaml").resolve()
    if requested is None:
        raise ExecutorError("migration begin requires --plan")
    observed = requested.expanduser().resolve()
    if observed != expected:
        raise ExecutorError(f"--plan must point to {expected}")
    return expected


def _plan_repository_and_commit(plan: dict[str, Any]) -> tuple[Path, str]:
    repo = Path(str(plan.get("repository", ""))).expanduser().resolve()
    if not repo.is_dir():
        raise ExecutorError(f"Migration Plan repository does not exist: {repo}")
    actual = source_commit(repo)
    planned = str(plan.get("source_commit", "unknown"))
    if planned != "unknown" and actual != "unknown" and planned != actual:
        raise ExecutorError(
            f"Migration Plan commit no longer matches the repository: plan={planned}, current={actual}"
        )
    return repo, actual


def _remove_candidate_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    parent = path.parent
    while parent.name not in {"candidate", ".work"} and parent.is_dir():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def command_begin_migration(args: argparse.Namespace, output: Path) -> int:
    plan_path = _migration_plan_path(output, args.plan)
    try:
        registry = load_registry()
        plan = load_migration_plan(plan_path, registry)
        validate_plan_snapshot(output, plan)
    except ArtifactSchemaError as exc:
        raise ExecutorError(f"Migration Plan is not executable: {exc}") from exc
    if plan.get("status") == "blocked":
        raise ExecutorError(
            "Migration Plan is blocked: " + " | ".join(plan.get("blocked_reasons", []))
        )
    if plan.get("status") != "planned":
        raise ExecutorError(f"Migration Plan must be planned, observed {plan.get('status')}")
    repo, commit = _plan_repository_and_commit(plan)
    transaction_id = f"00-migration-{uuid.uuid4().hex[:10]}"
    acquire_lock(
        output,
        {
            "transaction_id": transaction_id,
            "stage": MIGRATION_STAGE,
            "plan_id": plan["plan_id"],
            "created_at": now_utc(),
            "pid": os.getpid(),
        },
    )
    tx_dir = transaction_dir(output, transaction_id)
    candidate = tx_dir / "candidate"
    try:
        tx_dir.mkdir(parents=True, exist_ok=False)
        snapshot_copy(output, candidate)
        candidate_plan_path = candidate / ".work" / "migration-plan.yaml"
        if not candidate_plan_path.is_file():
            candidate_plan_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(plan_path, candidate_plan_path)
        candidate_plan = dict(plan)
        candidate_plan["status"] = "in-progress"
        write_migration_plan(candidate_plan_path, candidate_plan)

        automatic_actions: list[str] = []
        for step in plan.get("steps", []):
            action = step.get("action")
            for relative in step.get("paths", []):
                target = candidate / str(relative)
                if action == "archive-and-rebuild":
                    _remove_candidate_path(target)
                    automatic_actions.append(f"invalidated {relative}")
                elif action == "mechanical-migrate" and target.is_file():
                    definition = registry.definitions.get(str(step.get("artifact_type")))
                    if definition is None:
                        raise ExecutorError(
                            f"Migration step references unknown artifact type: {step.get('artifact_type')}"
                        )
                    add_artifact_metadata(
                        target, definition.artifact_type, definition.current_version
                    )
                    automatic_actions.append(f"upgraded metadata for {relative}")

        candidate_state_path = candidate / STATE_FILE
        if not candidate_state_path.is_file():
            raise ExecutorError("Migration Candidate has no analysis state")
        add_artifact_metadata(candidate_state_path, "analysis-state", "1")
        candidate_state = candidate_state_path.read_text(encoding="utf-8")
        candidate_state = set_scalar(candidate_state, "workflow_schema_version", WORKFLOW_SCHEMA_VERSION)
        candidate_state = set_scalar(candidate_state, "repository_path", str(repo))
        candidate_state = set_scalar(candidate_state, "migration_status", "in-progress")
        candidate_state = set_scalar(candidate_state, "publication_status", "stale")
        candidate_state = set_scalar(candidate_state, "active_transaction", transaction_id)
        atomic_write_text(candidate_state_path, candidate_state)

        transaction = {
            "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
            "transaction_id": transaction_id,
            "stage": MIGRATION_STAGE,
            "plan_id": plan["plan_id"],
            "source_manifest_sha256": plan["source_manifest_sha256"],
            "status": "in-progress",
            "repository": str(repo),
            "source_commit": commit,
            "candidate": str(candidate),
            "created_at": now_utc(),
            "automatic_actions": automatic_actions,
        }
        atomic_write_text(tx_dir / "pre-state.yaml", state_text(output))
        atomic_write_json(tx_dir / "transaction.json", transaction)
        atomic_write_json(
            tx_dir / "promotion-journal.json",
            {
                "transaction_id": transaction_id,
                "stage": MIGRATION_STAGE,
                "plan_id": plan["plan_id"],
                "phase": "not-started",
                "operations": [],
            },
        )
    except Exception:
        if tx_dir.exists():
            shutil.rmtree(tx_dir, ignore_errors=True)
        release_lock(output, transaction_id)
        raise
    emit(
        {
            "result": "begun",
            "stage": MIGRATION_STAGE,
            "transaction_id": transaction_id,
            "plan_id": plan["plan_id"],
            "candidate": str(candidate),
            "automatic_actions": automatic_actions,
            "instruction": (
                "review-and-adopt only the planned working artifacts in Candidate; "
                "do not write synthesis or reader documents"
            ),
        },
        args.json,
    )
    return 0


def command_begin(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    if args.stage == MIGRATION_STAGE:
        return command_begin_migration(args, output)
    if args.plan is not None:
        raise ExecutorError("--plan is accepted only for the migration stage")
    formal_state = state_text(output)
    repo, commit = verify_repo_and_commit(formal_state)
    current_stage = scalar_value(formal_state, "current_stage")
    status = scalar_value(formal_state, "stage_status")
    if scalar_value(formal_state, "workflow_schema_version") != WORKFLOW_SCHEMA_VERSION:
        raise ExecutorError("analysis state is legacy; run resume before begin")
    try:
        registry = load_registry()
        manifest_errors = validate_artifact_manifest(output, registry)
    except ArtifactSchemaError as exc:
        raise ExecutorError(f"bundled Artifact Schema is invalid: {exc}") from exc
    if manifest_errors:
        raise ExecutorError(
            "formal Artifact Manifest is invalid; run resume audit: "
            + " | ".join(manifest_errors)
        )
    if current_stage == "completed":
        raise ExecutorError("workflow is already completed")
    if current_stage not in STAGE_INDEX:
        raise ExecutorError(f"invalid current_stage in analysis state: {current_stage}")
    if args.stage != current_stage:
        raise ExecutorError(f"expected stage {current_stage}, received {args.stage}")
    if status not in {"pending"}:
        raise ExecutorError(f"stage cannot begin from status {status}; use status, commit, abort, or recover")
    transaction_id = f"{STAGE_INDEX[current_stage] + 1:02d}-{current_stage}-{uuid.uuid4().hex[:10]}"
    acquire_lock(
        output,
        {
            "transaction_id": transaction_id,
            "stage": current_stage,
            "created_at": now_utc(),
            "pid": os.getpid(),
        },
    )
    tx_dir = transaction_dir(output, transaction_id)
    candidate = tx_dir / "candidate"
    try:
        tx_dir.mkdir(parents=True, exist_ok=False)
        snapshot_copy(output, candidate)
        automatic_actions: list[str] = []
        candidate_state = (candidate / STATE_FILE).read_text(encoding="utf-8")
        candidate_state = set_scalar(candidate_state, "stage_status", "in-progress")
        candidate_state = set_scalar(candidate_state, "active_transaction", transaction_id)
        candidate_state = set_scalar(candidate_state, "phase", phase_for_stage(current_stage))
        atomic_write_text(candidate / STATE_FILE, candidate_state)
        transaction = {
            "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
            "transaction_id": transaction_id,
            "stage": current_stage,
            "status": "in-progress",
            "repository": str(repo),
            "source_commit": commit,
            "output": str(output),
            "candidate": str(candidate),
            "created_at": now_utc(),
            "automatic_actions": automatic_actions,
        }
        atomic_write_text(tx_dir / "pre-state.yaml", formal_state)
        atomic_write_json(tx_dir / "transaction.json", transaction)
        atomic_write_json(
            tx_dir / "promotion-journal.json",
            {"transaction_id": transaction_id, "stage": current_stage, "phase": "not-started", "operations": []},
        )
        formal_state = set_scalar(formal_state, "stage_status", "in-progress")
        formal_state = set_scalar(formal_state, "active_transaction", transaction_id)
        formal_state = set_scalar(formal_state, "phase", phase_for_stage(current_stage))
        atomic_write_text(state_path(output), formal_state)
    except Exception:
        if tx_dir.exists():
            shutil.rmtree(tx_dir, ignore_errors=True)
        release_lock(output, transaction_id)
        raise
    emit(
        {
            "result": "begun",
            "stage": current_stage,
            "transaction_id": transaction_id,
            "candidate": str(candidate),
            "instruction": "write every stage artifact under candidate, then run commit",
        },
        args.json,
    )
    return 0


def load_transaction(output: Path, transaction_id: str) -> tuple[Path, dict[str, Any], Path]:
    tx_dir = transaction_dir(output, transaction_id)
    transaction = read_json(tx_dir / "transaction.json")
    if transaction.get("transaction_id") != transaction_id:
        raise ExecutorError("transaction identity mismatch")
    candidate = Path(str(transaction.get("candidate", ""))).resolve()
    if candidate != (tx_dir / "candidate").resolve() or not candidate.is_dir():
        raise ExecutorError("transaction candidate is missing or outside its transaction")
    return tx_dir, transaction, candidate


def command_mark_behavior(args: argparse.Namespace) -> int:
    if args.status not in ALLOWED_BEHAVIOR_STATUS:
        raise ExecutorError(f"invalid behavior status: {args.status}")
    output = args.output.expanduser().resolve()
    _tx_dir, transaction, candidate = load_transaction(output, args.transaction)
    if transaction.get("stage") != "tracing":
        raise ExecutorError("mark-behavior is allowed only during the tracing stage")
    path = candidate / STATE_FILE
    text = path.read_text(encoding="utf-8")
    if args.status in {"tracing", "understood", "blocked"} and not args.dossier:
        existing = next(
            (entry for entry in behavior_entries(text) if entry.get("behavior_id") == args.behavior_id),
            None,
        )
        if not existing or not existing.get("dossier"):
            raise ExecutorError(f"status {args.status} requires --dossier")
    dossier = args.dossier
    if dossier is not None:
        dossier_path = (candidate / ".work" / dossier).resolve() if not Path(dossier).is_absolute() else Path(dossier).resolve()
        try:
            dossier_path.relative_to(candidate.resolve())
        except ValueError as exc:
            raise ExecutorError("dossier path must remain inside the candidate") from exc
        if args.status in {"understood", "blocked"} and not dossier_path.is_file():
            raise ExecutorError(f"dossier does not exist: {dossier_path}")
    updated = update_behavior(text, args.behavior_id, args.status, dossier, args.notes)
    atomic_write_text(path, updated)
    emit(
        {
            "result": "behavior-updated",
            "transaction_id": args.transaction,
            "behavior_id": args.behavior_id,
            "status": args.status,
        },
        args.json,
    )
    return 0


def verify_archive(source_root: Path, archive_root: Path, paths: Iterable[str]) -> None:
    for relative in paths:
        source = source_root / relative
        archived = archive_root / relative
        if not archived.is_file():
            raise ExecutorError(f"archive is missing file: {relative}")
        if source.stat().st_size != archived.stat().st_size or sha256_file(source) != sha256_file(archived):
            raise ExecutorError(f"archive checksum mismatch: {relative}")


def create_archive(
    output: Path,
    transaction_id: str,
    changed_or_deleted: list[str],
) -> tuple[Path | None, dict[str, Any]]:
    existing = [relative for relative in changed_or_deleted if (output / relative).is_file()]
    if not existing:
        return None, {"files": 0, "bytes": 0}
    archive_parent = execution_root(output) / "archive"
    temporary = archive_parent / f".{transaction_id}.tmp"
    final = archive_parent / transaction_id
    if final.is_dir():
        verify_archive(output, final, existing)
        archived = read_json(final / "archive-manifest.json")
        summary = archived.get("summary")
        return final, summary if isinstance(summary, dict) else manifest_summary(file_manifest(final))
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True, exist_ok=False)
    for relative in existing:
        source = output / relative
        destination = temporary / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    verify_archive(output, temporary, existing)
    manifest = file_manifest(temporary)
    atomic_write_json(
        temporary / "archive-manifest.json",
        {
            "transaction_id": transaction_id,
            "created_at": now_utc(),
            "files": manifest,
            "summary": manifest_summary(manifest),
        },
    )
    archive_parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary, final)
    return final, manifest_summary(manifest)


def archive_legacy_ba(output: Path, candidate: Path, transaction_id: str) -> Path | None:
    legacy = output / "ba-pack" / "behaviors"
    candidate_legacy = candidate / "ba-pack" / "behaviors"
    if not legacy.is_dir() or candidate_legacy.exists():
        return None
    parent = output / ".work" / "legacy-ba-pack"
    temporary = parent / f".{transaction_id}.tmp"
    final = parent / transaction_id
    if final.is_dir():
        if file_manifest(legacy) != file_manifest(final / "behaviors"):
            raise ExecutorError("existing legacy BA archive does not match the current legacy tree")
        return final
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True, exist_ok=False)
    shutil.copytree(legacy, temporary / "behaviors")
    source_manifest = file_manifest(legacy)
    archive_manifest = file_manifest(temporary / "behaviors")
    if source_manifest != archive_manifest:
        shutil.rmtree(temporary, ignore_errors=True)
        raise ExecutorError("legacy BA archive verification failed")
    atomic_write_json(
        temporary / "archive-manifest.json",
        {
            "transaction_id": transaction_id,
            "created_at": now_utc(),
            "files": {f"behaviors/{path}": value for path, value in archive_manifest.items()},
            "summary": manifest_summary(archive_manifest),
        },
    )
    parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary, final)
    return final


def rollback_promotion(output: Path, archive: Path | None, journal: dict[str, Any]) -> None:
    for operation in reversed(journal.get("operations", [])):
        relative = operation["path"]
        destination = output / relative
        if operation["kind"] == "mkdir":
            try:
                destination.rmdir()
            except (FileNotFoundError, OSError):
                pass
        elif operation["kind"] == "rmdir":
            destination.mkdir(parents=True, exist_ok=True)
        elif operation["kind"] == "add":
            try:
                destination.unlink()
            except FileNotFoundError:
                pass
        elif archive is not None:
            source = archive / relative
            if source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.parent / f".{destination.name}.rollback.tmp"
                shutil.copy2(source, temporary)
                os.replace(temporary, destination)


def promote_candidate(
    output: Path,
    candidate: Path,
    transaction_id: str,
    diff: dict[str, list[str]],
    archive: Path | None,
    journal_path: Path,
) -> dict[str, Any]:
    state_relative = STATE_FILE.as_posix()
    operations: list[dict[str, str]] = []
    current_directories = directory_set(output)
    candidate_directories = directory_set(candidate)
    for relative in sorted(
        candidate_directories - current_directories,
        key=lambda value: (len(Path(value).parts), value),
    ):
        operations.append({"kind": "mkdir", "path": relative})
    for relative in diff["added"]:
        if relative != state_relative:
            operations.append({"kind": "add", "path": relative})
    for relative in diff["changed"]:
        if relative != state_relative:
            operations.append({"kind": "change", "path": relative})
    for relative in diff["deleted"]:
        if relative != state_relative:
            operations.append({"kind": "delete", "path": relative})
    for relative in sorted(
        current_directories - candidate_directories,
        key=lambda value: (len(Path(value).parts), value),
        reverse=True,
    ):
        operations.append({"kind": "rmdir", "path": relative})
    journal = {
        "transaction_id": transaction_id,
        "phase": "promoting",
        "operations": operations,
        "completed_operations": [],
        "archive": str(archive) if archive else None,
        "updated_at": now_utc(),
    }
    atomic_write_json(journal_path, journal)
    try:
        for operation in operations:
            relative = operation["path"]
            destination = output / relative
            if operation["kind"] == "mkdir":
                destination.mkdir(parents=True, exist_ok=True)
            elif operation["kind"] == "rmdir":
                try:
                    destination.rmdir()
                except (FileNotFoundError, OSError):
                    pass
            elif operation["kind"] == "delete":
                try:
                    destination.unlink()
                except FileNotFoundError:
                    pass
            else:
                source = candidate / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.parent / f".{destination.name}.{transaction_id}.tmp"
                shutil.copy2(source, temporary)
                os.replace(temporary, destination)
            journal["completed_operations"].append(operation)
            atomic_write_json(journal_path, journal)
        journal["phase"] = "content-promoted"
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        return journal
    except Exception:
        journal["phase"] = "promotion-failed"
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        rollback_promotion(output, archive, {"operations": journal["completed_operations"]})
        journal["phase"] = "rolled-back"
        atomic_write_json(journal_path, journal)
        raise


def post_promotion_checks(stage: str, output: Path, repo: Path) -> list[dict[str, Any]]:
    scripts = Path(__file__).resolve().parent
    commands: list[list[str]] = []
    if stage in {"api-contract-publication", "ba-publication", "finalization"}:
        commands.append(
            [
                sys.executable,
                str(scripts / "validate_pack_links.py"),
                str(output),
                "--repo",
                str(repo),
                "--json",
                "--skip-artifact-manifest",
            ]
        )
    return [run_validator(command, output) for command in commands]


def pack_validation_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the last structured Pack validation result for a stage Receipt."""
    summary: dict[str, Any] = {
        "validator_domain_statuses": {},
        "primary_error_count": 0,
        "skipped_group_count": 0,
        "suppressed_error_count": 0,
    }
    for result in results:
        command = [str(item) for item in result.get("command", [])]
        if not any(Path(item).name == "validate_pack_links.py" for item in command):
            continue
        try:
            payload = json.loads(result.get("stdout", ""))
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        summary = {
            "validator_domain_statuses": payload.get("domain_statuses", {}),
            "primary_error_count": payload.get("primary_errors", 0),
            "skipped_group_count": payload.get("skipped_validation_groups", 0),
            "suppressed_error_count": payload.get("suppressed_row_errors", 0),
        }
    return summary


def archive_legacy_artifacts(
    output: Path, plan: dict[str, Any], transaction_id: str
) -> Path | None:
    paths = sorted(
        {
            str(relative)
            for step in plan.get("steps", [])
            if step.get("action") == "review-and-adopt"
            for relative in step.get("paths", [])
            if (output / str(relative)).is_file()
        }
    )
    if not paths:
        return None
    parent = output / ".work" / "legacy-artifacts"
    temporary = parent / f".{plan['plan_id']}.tmp"
    final = parent / str(plan["plan_id"])
    if final.is_dir():
        audit = audit_archive_directory(final)
        if not audit["valid"]:
            raise ExecutorError("existing legacy-artifacts archive failed checksum audit")
        return final
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True, exist_ok=False)
    for relative in paths:
        destination = temporary / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / relative, destination)
    verify_archive(output, temporary, paths)
    manifest = file_manifest(temporary)
    atomic_write_json(
        temporary / "archive-manifest.json",
        {
            "plan_id": plan["plan_id"],
            "transaction_id": transaction_id,
            "created_at": now_utc(),
            "files": manifest,
            "summary": manifest_summary(manifest),
        },
    )
    parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary, final)
    return final


def _finalize_migration_candidate_state(
    candidate: Path, plan: dict[str, Any], repo: Path
) -> str:
    path = candidate / STATE_FILE
    add_artifact_metadata(path, "analysis-state", "1")
    text = path.read_text(encoding="utf-8")
    target = str(plan["resume_stage_after_migration"])
    text = set_scalar(text, "workflow_schema_version", WORKFLOW_SCHEMA_VERSION)
    text = set_scalar(text, "repository_path", str(repo))
    text = set_scalar(text, "current_stage", target)
    text = set_scalar(text, "stage_status", "pending")
    text = set_scalar(text, "active_transaction", None)
    text = set_scalar(text, "last_committed_stage", previous_stage(target))
    text = set_scalar(text, "phase", phase_for_stage(target))
    text = set_scalar(text, "migration_status", "committed")
    target_index = STAGE_INDEX[target]
    if target_index <= STAGE_INDEX["synthesis"]:
        text = set_scalar(text, "synthesis_status", "pending")
    if target_index <= STAGE_INDEX["business-model"]:
        text = set_scalar(text, "business_model_status", "pending")
    publication = "stale" if plan.get("invalidated_artifacts") else "pending"
    text = set_scalar(text, "publication_status", publication)
    atomic_write_text(path, text)
    return text


def _validate_migration_candidate(
    output: Path,
    candidate: Path,
    plan: dict[str, Any],
    registry: Any,
    repo: Path,
    commit: str,
    transaction_id: str,
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    try:
        validate_plan_snapshot(output, plan)
    except ArtifactSchemaError as exc:
        errors.append(str(exc))
    allowed, must_remove, preserve = migration_allowed_paths(plan)
    current_manifest = file_manifest(output)
    candidate_manifest = file_manifest(candidate)
    diff = manifest_diff(current_manifest, candidate_manifest)
    changed_paths = set(diff["added"] + diff["changed"] + diff["deleted"])
    unexpected = sorted(changed_paths - allowed)
    if unexpected:
        errors.append(
            "Migration Candidate changed paths outside the plan: " + ", ".join(unexpected)
        )
    for relative in sorted(must_remove):
        if (candidate / relative).exists():
            errors.append(f"planned archive-and-rebuild Artifact still exists: {relative}")

    source_by_path = {
        str(item.get("path")): str(item.get("sha256"))
        for item in plan.get("source_snapshot", [])
        if isinstance(item, dict)
    }
    for relative in sorted(preserve):
        source_hash = source_by_path.get(relative)
        path = candidate / relative
        if source_hash is not None and (
            not path.is_file() or sha256_file(path) != source_hash
        ):
            errors.append(f"preserved Artifact changed during Migration: {relative}")

    for step in plan.get("steps", []):
        if step.get("action") not in {"mechanical-migrate", "review-and-adopt", "preserve"}:
            continue
        definition = registry.definitions.get(str(step.get("artifact_type")))
        if definition is None:
            continue
        for relative in step.get("paths", []):
            path = candidate / str(relative)
            if not path.is_file():
                if definition.artifact_type == "artifact-manifest":
                    continue
                errors.append(f"planned retained Artifact is missing: {relative}")
                continue
            observed_type, observed_version = artifact_metadata(path)
            if (
                observed_type != definition.artifact_type
                or observed_version != definition.current_version
            ):
                errors.append(
                    f"Artifact was not adopted to the current schema: {relative}; expected "
                    f"{definition.artifact_type}@{definition.current_version}"
                )

    register = candidate / ".work" / "repository-register.md"
    if register.is_file():
        try:
            register_check = validate_register_file(register, load_register_schema())
        except RegisterSchemaError as exc:
            errors.append(f"bundled Register Schema is invalid: {exc}")
        else:
            register_errors = list(register_check.errors)
            register_errors.extend(
                item
                for values in register_check.domain_errors.values()
                for item in values
            )
            if register_errors:
                errors.append(
                    "review-and-adopt Register does not match the current schema: "
                    + " | ".join(register_errors)
                )

    write_artifact_manifest(
        candidate,
        registry,
        str(repo),
        commit,
        MIGRATION_STAGE,
        transaction_id,
        plan.get("invalidated_artifacts", []),
    )
    errors.extend(validate_artifact_manifest(candidate, registry))
    return errors, diff


def command_commit_migration(
    args: argparse.Namespace,
    output: Path,
    tx_dir: Path,
    transaction: dict[str, Any],
    candidate: Path,
) -> int:
    if args.skip or args.semantic_result is not None:
        raise ExecutorError("Migration cannot use --skip or --semantic-result")
    lock = read_json(lock_path(output)) if lock_path(output).is_file() else {}
    if lock.get("transaction_id") != args.transaction or lock.get("stage") != MIGRATION_STAGE:
        raise ExecutorError("migration execution lock does not own this transaction")
    try:
        registry = load_registry()
        formal_plan_path = output / ".work" / "migration-plan.yaml"
        plan = load_migration_plan(formal_plan_path, registry)
    except ArtifactSchemaError as exc:
        raise ExecutorError(f"Migration Plan is invalid: {exc}") from exc
    if transaction.get("plan_id") != plan.get("plan_id"):
        raise ExecutorError("transaction and Migration Plan IDs do not match")
    if plan.get("status") != "planned":
        raise ExecutorError("formal Migration Plan is no longer planned")
    repo, commit = _plan_repository_and_commit(plan)

    candidate_plan = dict(plan)
    candidate_plan["status"] = "committed"
    write_migration_plan(candidate / ".work" / "migration-plan.yaml", candidate_plan)
    candidate_state = _finalize_migration_candidate_state(candidate, plan, repo)
    errors, diff = _validate_migration_candidate(
        output, candidate, plan, registry, repo, commit, args.transaction
    )
    if errors:
        transaction["status"] = "failed"
        transaction["last_attempt_at"] = now_utc()
        transaction["errors"] = errors
        atomic_write_json(tx_dir / "transaction.json", transaction)
        emit(
            {
                "result": "failed",
                "stage": MIGRATION_STAGE,
                "transaction_id": args.transaction,
                "errors": errors,
                "candidate": str(candidate),
            },
            args.json,
        )
        return 1

    current_manifest = file_manifest(output)
    candidate_manifest = file_manifest(candidate)
    diff = manifest_diff(current_manifest, candidate_manifest)
    directories = directory_diff(output, candidate)
    archive_paths = sorted(
        path
        for path in set(diff["changed"] + diff["deleted"])
        if path != STATE_FILE.as_posix()
    )
    archive, archive_summary = create_archive(output, args.transaction, archive_paths)
    legacy_artifacts = archive_legacy_artifacts(output, plan, args.transaction)
    legacy_ba_archive = archive_legacy_ba(output, candidate, args.transaction)
    journal_path = tx_dir / "promotion-journal.json"
    journal: dict[str, Any] | None = None
    receipt_path: Path | None = None
    try:
        journal = promote_candidate(
            output, candidate, args.transaction, diff, archive, journal_path
        )
        atomic_write_text(state_path(output), candidate_state)
        receipt_payload = {
            "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
            "artifact_schema_registry_version": registry.registry_version,
            "kind": "migration",
            "transaction_id": args.transaction,
            "stage": MIGRATION_STAGE,
            "plan_id": plan["plan_id"],
            "repository": str(repo),
            "source_commit": commit,
            "source_manifest_sha256": plan["source_manifest_sha256"],
            "resume_stage_after_migration": plan["resume_stage_after_migration"],
            "steps": plan["steps"],
            "invalidated_artifacts": plan["invalidated_artifacts"],
            "expected_archives": plan["expected_archives"],
            "archive": str(archive) if archive else None,
            "archive_summary": archive_summary,
            "legacy_artifacts_archive": str(legacy_artifacts) if legacy_artifacts else None,
            "legacy_ba_archive": str(legacy_ba_archive) if legacy_ba_archive else None,
            "changes": diff,
            "directory_changes": directories,
            "started_at": transaction.get("created_at"),
            "completed_at": now_utc(),
            "validators": [
                {
                    "group": "artifact-schema-and-manifest",
                    "result": "passed",
                },
                {
                    "group": "repository-register-schema",
                    "result": "passed" if (candidate / ".work" / "repository-register.md").is_file() else "not-applicable",
                },
            ],
            "result": "committed",
        }
        receipt_path = write_receipt(
            output, receipt_count(output), MIGRATION_STAGE, receipt_payload
        )
        write_artifact_manifest(
            output,
            registry,
            str(repo),
            commit,
            MIGRATION_STAGE,
            args.transaction,
            plan.get("invalidated_artifacts", []),
        )
        manifest_errors = validate_artifact_manifest(output, registry)
        if manifest_errors:
            raise ExecutorError(
                "post-migration Artifact Manifest validation failed: "
                + " | ".join(manifest_errors)
            )
        journal["phase"] = "committed"
        journal["receipt"] = str(receipt_path)
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        release_lock(output, args.transaction)
        shutil.rmtree(tx_dir)
    except Exception:
        if journal is not None and journal.get("phase") == "content-promoted":
            rollback_promotion(output, archive, journal)
            journal["phase"] = "rolled-back-after-commit-error"
            journal["updated_at"] = now_utc()
            atomic_write_json(journal_path, journal)
            atomic_write_text(state_path(output), (tx_dir / "pre-state.yaml").read_text(encoding="utf-8"))
        if receipt_path is not None and receipt_path.exists():
            receipt_path.unlink()
        raise
    emit(
        {
            "result": "committed",
            "stage": MIGRATION_STAGE,
            "transaction_id": args.transaction,
            "plan_id": plan["plan_id"],
            "next_stage": plan["resume_stage_after_migration"],
            "receipt": str(receipt_path),
            "archive": str(archive) if archive else None,
            "legacy_artifacts_archive": str(legacy_artifacts) if legacy_artifacts else None,
            "legacy_ba_archive": str(legacy_ba_archive) if legacy_ba_archive else None,
        },
        args.json,
    )
    return 0


def command_commit(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    tx_dir, transaction, candidate = load_transaction(output, args.transaction)
    stage = str(transaction.get("stage"))
    if stage == MIGRATION_STAGE:
        return command_commit_migration(args, output, tx_dir, transaction, candidate)
    formal_text = state_text(output)
    if scalar_value(formal_text, "active_transaction") != args.transaction:
        raise ExecutorError("analysis state does not own this transaction")
    repo, commit = verify_repo_and_commit(formal_text)
    if args.skip:
        stage_skip_allowed(stage, candidate, args.reason)
    candidate_state_path = candidate / STATE_FILE
    candidate_state = candidate_state_path.read_text(encoding="utf-8")
    candidate_state = candidate_state_for_commit(
        candidate_state,
        stage,
        args.semantic_result,
        args.skip,
    )
    atomic_write_text(candidate_state_path, candidate_state)

    try:
        registry = load_registry()
        invalidated = read_json(candidate / ".work" / "artifact-manifest.json").get(
            "invalidated_artifacts", []
        )
        if isinstance(invalidated, list):
            produced_now = {
                artifact_type
                for artifact_type, definition in registry.definitions.items()
                if definition.producing_stage == stage
            }
            invalidated = [
                item
                for item in invalidated
                if not isinstance(item, dict)
                or item.get("artifact_type") not in produced_now
            ]
        write_artifact_manifest(
            candidate,
            registry,
            str(repo),
            commit,
            stage,
            args.transaction,
            invalidated if isinstance(invalidated, list) else [],
        )
    except (ArtifactSchemaError, ExecutorError) as exc:
        raise ExecutorError(f"cannot refresh Candidate Artifact Manifest: {exc}") from exc

    errors, validators = stage_gates(stage, candidate, repo)
    candidate_state_check = run_validator(
        [
            sys.executable,
            str(Path(__file__).resolve().parent / "validate_analysis_state.py"),
            str(candidate_state_path),
            "--repo",
            str(repo),
            "--catalog",
            str(candidate / ".work" / "behavior-catalog.yaml"),
            "--dossiers-dir",
            str(candidate / ".work" / "behavior-dossiers"),
            "--allow-missing-final-receipt",
        ],
        candidate,
    )
    validators.append(candidate_state_check)
    if candidate_state_check["exit_code"] != 0:
        errors.append("candidate analysis state validation failed")
    if errors:
        transaction["status"] = "failed"
        transaction["last_attempt_at"] = now_utc()
        transaction["errors"] = errors
        transaction["validators"] = validators
        atomic_write_json(tx_dir / "transaction.json", transaction)
        formal_text = set_scalar(formal_text, "stage_status", "failed")
        atomic_write_text(state_path(output), formal_text)
        emit(
            {
                "result": "failed",
                "stage": stage,
                "transaction_id": args.transaction,
                "errors": errors,
                "candidate": str(candidate),
            },
            args.json,
        )
        return 1

    current_manifest = file_manifest(output)
    candidate_manifest = file_manifest(candidate)
    diff = manifest_diff(current_manifest, candidate_manifest)
    directories = directory_diff(output, candidate)
    archive_paths = sorted(
        path
        for path in set(diff["changed"] + diff["deleted"])
        if path != STATE_FILE.as_posix()
    )
    archive, archive_summary = create_archive(output, args.transaction, archive_paths)
    journal_path = tx_dir / "promotion-journal.json"
    journal: dict[str, Any] | None = None
    receipt_path: Path | None = None
    commit_recorded = False
    try:
        journal = promote_candidate(
            output,
            candidate,
            args.transaction,
            diff,
            archive,
            journal_path,
        )
        post_results = post_promotion_checks(stage, output, repo)
        failed_post = [result for result in post_results if result["exit_code"] != 0]
        if failed_post:
            rollback_promotion(output, archive, journal)
            journal["phase"] = "rolled-back-after-post-validation"
            atomic_write_json(journal_path, journal)
            details = " | ".join(
                (result.get("stdout") or result.get("stderr") or "validator failed").strip()
                for result in failed_post
            )
            raise ExecutorError(
                "post-promotion validation failed; published content was rolled back: "
                + details
            )

        sequence = receipt_count(output)
        validation_summary = pack_validation_summary(validators + post_results)
        register_artifact_schema_version = scalar_value(
            (candidate / ".work" / "repository-register.md").read_text(encoding="utf-8"),
            "artifact_schema_version",
        )
        receipt_payload = {
            "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
            "artifact_schema_registry_version": registry.registry_version,
            "repository_register_artifact_schema_version": register_artifact_schema_version,
            **validation_summary,
            "transaction_id": args.transaction,
            "stage": stage,
            "stage_result": "skipped" if args.skip else "committed",
            "skip_reason": args.reason if args.skip else None,
            "repository": str(repo),
            "source_commit": commit,
            "started_at": transaction.get("created_at"),
            "completed_at": now_utc(),
            "input_manifest": manifest_summary(current_manifest),
            "output_manifest": manifest_summary(candidate_manifest),
            "changes": diff,
            "directory_changes": directories,
            "archive": str(archive) if archive else None,
            "archive_summary": archive_summary,
            "validators": validators + post_results,
            "result": "committed",
        }
        receipt_path = write_receipt(output, sequence, stage, receipt_payload)
        atomic_write_text(state_path(output), candidate_state)
        write_artifact_manifest(
            output,
            registry,
            str(repo),
            commit,
            stage,
            args.transaction,
            invalidated if isinstance(invalidated, list) else [],
        )
        manifest_errors = validate_artifact_manifest(output, registry)
        if manifest_errors:
            raise ExecutorError(
                "post-commit Artifact Manifest validation failed: "
                + " | ".join(manifest_errors)
            )
        state_check = run_validator(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "validate_analysis_state.py"),
                str(state_path(output)),
                "--repo",
                str(repo),
                "--catalog",
                str(output / ".work" / "behavior-catalog.yaml"),
                "--dossiers-dir",
                str(output / ".work" / "behavior-dossiers"),
            ],
            output,
        )
        if state_check["exit_code"] != 0:
            raise ExecutorError("post-commit state validation failed")
        commit_recorded = True
        journal["phase"] = "committed"
        journal["receipt"] = str(receipt_path)
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        try:
            release_lock(output, args.transaction)
            shutil.rmtree(tx_dir)
        except OSError:
            # The Receipt and state are authoritative; status/recover may clean stale execution files.
            pass
    except Exception as exc:
        if commit_recorded:
            # State plus Receipt already establish completion. Leave cleanup to status/recover.
            pass
        elif journal is not None and journal.get("phase") == "content-promoted":
            rollback_promotion(output, archive, journal)
            journal["phase"] = "rolled-back-after-commit-error"
            journal["updated_at"] = now_utc()
            atomic_write_json(journal_path, journal)
        if commit_recorded:
            emit(
                {
                    "result": "committed-with-cleanup-warning",
                    "stage": stage,
                    "transaction_id": args.transaction,
                    "receipt": str(receipt_path),
                    "warning": str(exc),
                },
                args.json,
            )
            return 0
        if receipt_path is not None:
            try:
                receipt_path.unlink()
            except FileNotFoundError:
                pass
        transaction["status"] = "failed"
        transaction["last_attempt_at"] = now_utc()
        transaction["errors"] = [str(exc)]
        atomic_write_json(tx_dir / "transaction.json", transaction)
        failed_state = formal_text
        failed_state = set_scalar(failed_state, "stage_status", "failed")
        failed_state = set_scalar(failed_state, "active_transaction", args.transaction)
        atomic_write_text(state_path(output), failed_state)
        raise

    emit(
        {
            "result": "skipped" if args.skip else "committed",
            "stage": stage,
            "transaction_id": args.transaction,
            "next_stage": scalar_value(candidate_state, "current_stage"),
            "receipt": str(receipt_path),
            "archive": str(archive) if archive else None,
        },
        args.json,
    )
    return 0


def command_abort(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    tx_dir, transaction, _candidate = load_transaction(output, args.transaction)
    formal = state_text(output)
    is_migration = transaction.get("stage") == MIGRATION_STAGE
    if not is_migration and scalar_value(formal, "active_transaction") != args.transaction:
        raise ExecutorError("analysis state does not own this transaction")
    if is_migration:
        lock = read_json(lock_path(output)) if lock_path(output).is_file() else {}
        if lock.get("transaction_id") != args.transaction:
            raise ExecutorError("migration execution lock does not own this transaction")
    journal = read_json(tx_dir / "promotion-journal.json")
    if journal.get("phase") not in {
        "not-started",
        "rolled-back",
        "rolled-back-after-post-validation",
        "rolled-back-after-state-validation",
        "rolled-back-after-commit-error",
        "rolled-back-by-recover",
    }:
        raise ExecutorError("transaction has promotion work; run recover instead of abort")
    if not is_migration:
        formal = set_scalar(formal, "stage_status", "pending")
        formal = set_scalar(formal, "active_transaction", None)
        atomic_write_text(state_path(output), formal)
    release_lock(output, args.transaction)
    shutil.rmtree(tx_dir)
    emit(
        {
            "result": "aborted",
            "transaction_id": args.transaction,
            "stage": transaction.get("stage"),
        },
        args.json,
    )
    return 0


def status_payload(output: Path) -> dict[str, Any]:
    text = state_text(output)
    payload: dict[str, Any] = {
        "workflow_schema_version": scalar_value(text, "workflow_schema_version") or "legacy",
        "repository": scalar_value(text, "repository"),
        "repository_path": scalar_value(text, "repository_path"),
        "source_commit": scalar_value(text, "source_commit"),
        "phase": scalar_value(text, "phase"),
        "current_stage": scalar_value(text, "current_stage"),
        "stage_status": scalar_value(text, "stage_status"),
        "active_transaction": scalar_value(text, "active_transaction"),
        "last_committed_stage": scalar_value(text, "last_committed_stage"),
        "synthesis_status": scalar_value(text, "synthesis_status"),
        "business_model_status": scalar_value(text, "business_model_status"),
        "publication_status": scalar_value(text, "publication_status"),
        "migration_status": scalar_value(text, "migration_status") or "unknown",
        "migration_plan": None,
        "artifact_manifest_status": "unknown",
        "artifact_manifest_errors": [],
        "behavior_counts": {},
        "formal_manifest": manifest_summary(file_manifest(output)),
        "receipt_count": receipt_count(output),
        "lock": None,
        "transaction": None,
        "candidate_diff": None,
        "candidate_directory_diff": None,
        "requirements": [],
        "integrity_errors": [],
        "validator_summary": [],
        "archive_audits": [],
        "legacy_archive_audits": [],
        "legacy_artifact_archive_audits": [],
        "temporary_paths": temporary_paths(output),
    }
    counts: dict[str, int] = {}
    for entry in behavior_entries(text):
        status = str(entry.get("status"))
        counts[status] = counts.get(status, 0) + 1
    payload["behavior_counts"] = counts
    if lock_path(output).is_file():
        try:
            payload["lock"] = read_json(lock_path(output))
        except ExecutorError as exc:
            payload["lock"] = {"error": str(exc)}
    plan_path = output / ".work" / "migration-plan.yaml"
    if plan_path.is_file():
        try:
            registry = load_registry()
            plan = load_migration_plan(plan_path, registry)
            payload["migration_plan"] = {
                "path": str(plan_path),
                "plan_id": plan.get("plan_id"),
                "status": plan.get("status"),
                "resume_stage_after_migration": plan.get("resume_stage_after_migration"),
                "invalidated_artifacts": plan.get("invalidated_artifacts", []),
                "blocked_reasons": plan.get("blocked_reasons", []),
            }
        except ArtifactSchemaError as exc:
            payload["integrity_errors"].append(f"Migration Plan invalid: {exc}")
    try:
        registry = load_registry()
        artifact_errors = validate_artifact_manifest(output, registry)
        payload["artifact_manifest_errors"] = artifact_errors
        payload["artifact_manifest_status"] = "valid" if not artifact_errors else "invalid"
    except ArtifactSchemaError as exc:
        payload["artifact_manifest_status"] = "invalid"
        payload["artifact_manifest_errors"] = [str(exc)]

    active = payload["active_transaction"]
    if not active and isinstance(payload["lock"], dict) and payload["lock"].get("stage") == MIGRATION_STAGE:
        active = payload["lock"].get("transaction_id")
    if active:
        try:
            tx_dir, transaction, candidate = load_transaction(output, str(active))
            payload["transaction"] = transaction
            payload["candidate_manifest"] = manifest_summary(file_manifest(candidate))
            payload["candidate_diff"] = manifest_diff(file_manifest(output), file_manifest(candidate))
            payload["candidate_directory_diff"] = directory_diff(output, candidate)
            stage = str(transaction.get("stage"))
            try:
                repo, _commit = verify_repo_and_commit(text)
                requirements, status_validators = stage_gates(stage, candidate, repo)
                payload["requirements"] = requirements
                payload["validator_summary"] = [
                    {
                        "command": result["command"],
                        "exit_code": result["exit_code"],
                    }
                    for result in status_validators
                ]
            except ExecutorError as exc:
                payload["requirements"] = [str(exc)]
            journal_path = tx_dir / "promotion-journal.json"
            payload["promotion_journal"] = read_json(journal_path) if journal_path.is_file() else None
        except ExecutorError as exc:
            payload["transaction"] = {"error": str(exc)}
    if payload["current_stage"] == "completed" and committed_finalization_receipt(output) is None:
        payload["integrity_errors"].append(
            "completed state has no committed finalization Receipt"
        )
    if (
        payload["active_transaction"] is None
        and payload["lock"] is not None
        and not (
            isinstance(payload["lock"], dict)
            and payload["lock"].get("stage") == MIGRATION_STAGE
        )
    ):
        payload["integrity_errors"].append("workflow lock exists without active_transaction")
    archive_root = execution_root(output) / "archive"
    if archive_root.is_dir():
        payload["archive_audits"] = [
            audit_archive_directory(path)
            for path in sorted(archive_root.iterdir())
            if path.is_dir() and not path.name.startswith(".")
        ]
    legacy_root = output / ".work" / "legacy-ba-pack"
    if legacy_root.is_dir():
        payload["legacy_archive_audits"] = [
            audit_archive_directory(path)
            for path in sorted(legacy_root.iterdir())
            if path.is_dir() and not path.name.startswith(".")
        ]
    legacy_artifacts_root = output / ".work" / "legacy-artifacts"
    if legacy_artifacts_root.is_dir():
        payload["legacy_artifact_archive_audits"] = [
            audit_archive_directory(path)
            for path in sorted(legacy_artifacts_root.iterdir())
            if path.is_dir() and not path.name.startswith(".")
        ]
    for audit in (
        payload["archive_audits"]
        + payload["legacy_archive_audits"]
        + payload["legacy_artifact_archive_audits"]
    ):
        if not audit["valid"]:
            payload["integrity_errors"].append(
                f"archive integrity failed: {audit['path']}"
            )
    return payload


def command_status(args: argparse.Namespace) -> int:
    payload = status_payload(args.output.expanduser().resolve())
    emit(payload, args.json)
    return 0


def command_resume(args: argparse.Namespace) -> int:
    state = args.state.expanduser().resolve()
    if state.name != "analysis-state.yaml" or state.parent.name != ".work":
        raise ExecutorError("--state must point to <output>/.work/analysis-state.yaml")
    output = state.parent.parent
    text = state.read_text(encoding="utf-8")
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        raise ExecutorError(f"repository directory does not exist: {repo}")
    recorded_commit = scalar_value(text, "source_commit") or "unknown"
    actual_commit = source_commit(repo)
    if recorded_commit != "unknown" and actual_commit != "unknown" and recorded_commit != actual_commit:
        raise ExecutorError(
            f"cannot resume a different commit: state={recorded_commit}, current={actual_commit}"
        )
    if scalar_value(text, "analysis_mode") != "automatic":
        raise ExecutorError("only automatic full-repository analysis can be resumed")
    try:
        registry = load_registry()
    except ArtifactSchemaError as exc:
        raise ExecutorError(f"bundled Artifact Schema is invalid: {exc}") from exc

    if (
        scalar_value(text, "workflow_schema_version") == WORKFLOW_SCHEMA_VERSION
        and scalar_value(text, "current_stage") == "completed"
        and committed_finalization_receipt(output) is None
    ):
        raise ExecutorError(
            "completed state has no committed finalization Receipt; this is an integrity "
            "failure and cannot be converted into a migration recovery point"
        )

    if current_pack_is_versioned(output, registry):
        verify_repo_and_commit(text, repo)
        status = status_payload(output)
        if status["current_stage"] == "completed" and committed_finalization_receipt(output) is None:
            raise ExecutorError(
                "completed state has no committed finalization Receipt; "
                "this is an integrity failure and cannot be repaired by rewriting State"
            )
        emit({"result": "resume-ready", **status}, args.json)
        return 0

    if lock_path(output).exists():
        raise ExecutorError("resume audit cannot run while an execution transaction is active")
    try:
        plan = build_migration_plan(output, registry, repo, actual_commit)
        plan_path = output / ".work" / "migration-plan.yaml"
        write_migration_plan(plan_path, plan)
    except ArtifactSchemaError as exc:
        raise ExecutorError(f"cannot build Migration Plan: {exc}") from exc
    receipt = {
        "workflow_schema_version": scalar_value(text, "workflow_schema_version") or "unknown",
        "artifact_schema_registry_version": registry.registry_version,
        "kind": "migration-planning",
        "plan_id": plan["plan_id"],
        "repository": str(repo),
        "source_commit": actual_commit,
        "source_manifest_sha256": plan["source_manifest_sha256"],
        "target_workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "resume_stage_after_migration": plan["resume_stage_after_migration"],
        "blocked_reasons": plan["blocked_reasons"],
        "created_at": now_utc(),
        "result": "blocked" if plan["status"] == "blocked" else "planned",
    }
    receipt_path = write_receipt(output, receipt_count(output), "migration-planning", receipt)
    emit(
        {
            "result": "migration-blocked" if plan["status"] == "blocked" else "migration-planned",
            "output": str(output),
            "plan": str(plan_path),
            "plan_id": plan["plan_id"],
            "plan_status": plan["status"],
            "resume_stage_after_migration": plan["resume_stage_after_migration"],
            "invalidated_artifacts": plan["invalidated_artifacts"],
            "blocked_reasons": plan["blocked_reasons"],
            "receipt": str(receipt_path),
        },
        args.json,
    )
    return 1 if plan["status"] == "blocked" else 0


def command_recover(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    text = state_text(output)
    active = scalar_value(text, "active_transaction")
    if not active:
        if lock_path(output).exists():
            lock = read_json(lock_path(output))
            transaction_id = str(lock.get("transaction_id", ""))
            tx_dir = transaction_dir(output, transaction_id)
            receipt = receipt_for_transaction(output, transaction_id)
            if receipt is not None:
                lock_path(output).unlink()
                if tx_dir.exists():
                    shutil.rmtree(tx_dir)
                emit(
                    {
                        "result": "cleaned-committed-transaction",
                        "transaction_id": transaction_id,
                        "receipt": str(receipt),
                    },
                    args.json,
                )
                return 0
            if tx_dir.is_dir():
                transaction = read_json(tx_dir / "transaction.json")
                journal = read_json(tx_dir / "promotion-journal.json")
                archive_value = journal.get("archive")
                archive = Path(archive_value) if archive_value else None
                rollback_promotion(
                    output,
                    archive,
                    {"operations": journal.get("completed_operations", [])},
                )
                pre_state = tx_dir / "pre-state.yaml"
                if transaction.get("stage") == MIGRATION_STAGE:
                    if pre_state.is_file():
                        atomic_write_text(
                            state_path(output), pre_state.read_text(encoding="utf-8")
                        )
                else:
                    recovered = pre_state.read_text(encoding="utf-8") if pre_state.is_file() else text
                    recovered = set_scalar(recovered, "stage_status", "failed")
                    recovered = set_scalar(recovered, "active_transaction", transaction_id)
                    atomic_write_text(state_path(output), recovered)
                journal["phase"] = "rolled-back-by-recover"
                atomic_write_json(tx_dir / "promotion-journal.json", journal)
                emit(
                    {
                        "result": "rolled-back-orphan-transaction",
                        "transaction_id": transaction_id,
                        "instruction": "inspect candidate, then commit again or abort",
                    },
                    args.json,
                )
                return 0
            lock_path(output).unlink()
            emit({"result": "removed-orphan-lock", "output": str(output)}, args.json)
            return 0
        if scalar_value(text, "current_stage") == "completed" and committed_finalization_receipt(output) is None:
            raise ExecutorError(
                "completed state has no finalization Receipt; run resume audit instead of trusting it"
            )
        emit({"result": "nothing-to-recover", "output": str(output)}, args.json)
        return 0
    tx_dir, transaction, candidate = load_transaction(output, active)
    journal_path = tx_dir / "promotion-journal.json"
    journal = read_json(journal_path)
    phase = journal.get("phase")
    receipt = receipt_for_transaction(output, active)
    if receipt is not None:
        candidate_state = (candidate / STATE_FILE).read_text(encoding="utf-8")
        atomic_write_text(state_path(output), candidate_state)
        journal["phase"] = "committed"
        journal["receipt"] = str(receipt)
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        release_lock(output, active)
        shutil.rmtree(tx_dir)
        emit(
            {
                "result": "completed-recorded-transaction",
                "transaction_id": active,
                "receipt": str(receipt),
            },
            args.json,
        )
        return 0
    if phase in {
        "not-started",
        "rolled-back",
        "rolled-back-after-post-validation",
        "rolled-back-after-state-validation",
        "rolled-back-after-commit-error",
        "rolled-back-by-recover",
    }:
        emit(
            {
                "result": "transaction-retained",
                "transaction_id": active,
                "stage": transaction.get("stage"),
                "instruction": "fix candidate and commit, or abort the transaction",
            },
            args.json,
        )
        return 0
    archive_value = journal.get("archive")
    archive = Path(archive_value) if archive_value else None
    rollback_promotion(output, archive, {"operations": journal.get("completed_operations", [])})
    journal["phase"] = "rolled-back-by-recover"
    journal["updated_at"] = now_utc()
    atomic_write_json(journal_path, journal)
    pre_state = tx_dir / "pre-state.yaml"
    recovered = pre_state.read_text(encoding="utf-8") if pre_state.is_file() else text
    recovered = set_scalar(recovered, "stage_status", "failed")
    recovered = set_scalar(recovered, "active_transaction", active)
    atomic_write_text(state_path(output), recovered)
    emit(
        {
            "result": "rolled-back",
            "transaction_id": active,
            "stage": transaction.get("stage"),
            "instruction": "inspect candidate, then commit again or abort",
        },
        args.json,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mechanical stage executor for EAPI knowledge-pack reconstruction"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--repo", type=Path, required=True)
    init.add_argument("--output", type=Path, required=True)
    init.add_argument("--json", action="store_true")
    init.set_defaults(handler=command_init)

    resume = subparsers.add_parser("resume")
    resume.add_argument("--repo", type=Path, required=True)
    resume.add_argument("--state", type=Path, required=True)
    resume.add_argument("--json", action="store_true")
    resume.set_defaults(handler=command_resume)

    status = subparsers.add_parser("status")
    status.add_argument("--output", type=Path, required=True)
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=command_status)

    begin = subparsers.add_parser("begin")
    begin.add_argument("--output", type=Path, required=True)
    begin.add_argument("--stage", choices=(MIGRATION_STAGE,) + STAGES[:-1], required=True)
    begin.add_argument("--plan", type=Path)
    begin.add_argument("--json", action="store_true")
    begin.set_defaults(handler=command_begin)

    mark = subparsers.add_parser("mark-behavior")
    mark.add_argument("--output", type=Path, required=True)
    mark.add_argument("--transaction", required=True)
    mark.add_argument("--behavior-id", required=True)
    mark.add_argument("--status", choices=sorted(ALLOWED_BEHAVIOR_STATUS), required=True)
    mark.add_argument("--dossier")
    mark.add_argument("--notes")
    mark.add_argument("--json", action="store_true")
    mark.set_defaults(handler=command_mark_behavior)

    commit = subparsers.add_parser("commit")
    commit.add_argument("--output", type=Path, required=True)
    commit.add_argument("--transaction", required=True)
    commit.add_argument("--semantic-result", choices=("complete", "partial", "blocked"))
    commit.add_argument("--skip", action="store_true")
    commit.add_argument("--reason")
    commit.add_argument("--json", action="store_true")
    commit.set_defaults(handler=command_commit)

    abort = subparsers.add_parser("abort")
    abort.add_argument("--output", type=Path, required=True)
    abort.add_argument("--transaction", required=True)
    abort.add_argument("--json", action="store_true")
    abort.set_defaults(handler=command_abort)

    recover = subparsers.add_parser("recover")
    recover.add_argument("--output", type=Path, required=True)
    recover.add_argument("--json", action="store_true")
    recover.set_defaults(handler=command_recover)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.handler(args))
    except ExecutorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: filesystem operation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
