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
    assess_artifact_manifest,
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
from artifact_scaffold import (
    ArtifactScaffoldError,
    existing_artifact_matches,
    load_scaffold_schema,
    parse_identity_arguments,
    render_artifact,
)
from register_schema import (
    RegisterSchemaError,
    load_register_schema,
    validate_bundled_contract,
    validate_register_file,
)
from markdown_structure import (
    load_api_contract_structure,
    parse_markdown,
    validate_api_contract_tables,
)
from migration_transforms import MigrationTransformError, execute_transform


WORKFLOW_SCHEMA_VERSION = "4"
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
ALLOWED_CHECKPOINT_STATUS = {"pending", "in-progress", "complete", "skipped", "blocked", "failed"}
TERMINAL_CHECKPOINT_STATUS = {"complete", "skipped", "blocked"}
STAGE_CHECKPOINTS: dict[str, tuple[str, ...]] = {
    "inventory": ("project-detection", "entrypoint-inventory", "evidence-index"),
    "tracing": ("behavior-tracing", "coverage-review"),
    "synthesis": (
        "endpoint-reconciliation",
        "outbound-http-reconciliation",
        "dependency-reconciliation",
        "failure-reconciliation",
        "lifecycle-config-reconciliation",
        "connection-shared-model",
        "synthesis-review",
    ),
    "tech-publication": (
        "tech-behaviors",
        "repository-overview",
        "repository-reference-docs",
        "tech-cross-links",
        "tech-validation",
    ),
    "api-contract-publication": (
        "endpoint-matrix",
        "api-contracts",
        "api-backlinks",
        "api-validation",
    ),
    "business-model": (
        "capability-object-model",
        "journey-scenario-model",
        "tech-coverage",
        "business-model-review",
    ),
    "ba-publication": (
        "journeys",
        "scenarios",
        "ba-overview-catalog",
        "ba-backlinks",
        "ba-validation",
    ),
    "finalization": (
        "mechanical-review",
        "fact-sampling",
        "readability-review",
        "release-readiness",
    ),
    "migration": (
        "plan-verification",
        "evidence-preservation",
        "artifact-migration",
        "migration-validation",
    ),
}
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
    ".work/execution/generations",
    ".work/legacy-ba-pack",
    ".work/legacy-artifacts",
}
STATE_FILE = Path(".work/analysis-state.yaml")
GENERATION_STAGES = {
    "synthesis",
    "tech-publication",
    "api-contract-publication",
    "business-model",
    "ba-publication",
    "finalization",
}
FORMAL_DRIFT_EXCLUDES = {
    ".work/analysis-state.yaml",
    ".work/artifact-manifest.json",
    ".work/migration-plan.yaml",
}
STAGE_VALIDATION_REPORT_SCHEMA_VERSION = "1"
VALIDATION_DETAIL_LIMIT = 50
VALIDATION_PER_CODE_LIMIT = 10
VALIDATABLE_TRANSACTION_STATUSES = {"in-progress", "failed"}
VALIDATABLE_JOURNAL_PHASES = {
    "not-started",
    "rolled-back",
    "rolled-back-after-commit-error",
    "rolled-back-after-post-validation",
    "rolled-back-by-recover",
    "rolled-back-generation",
}


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


def yaml_block(text: str, key: str) -> tuple[str, str]:
    match = re.search(
        rf"^{re.escape(key)}:[ \t]*(?P<inline>[^\n]*)\n"
        rf"(?P<body>(?:[ \t]+[^\n]*(?:\n|$))*)",
        text,
        re.M,
    )
    if not match:
        return "", ""
    return match.group("inline").strip(), match.group("body")


def markdown_frontmatter(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    return text[4:end] if end != -1 else None


def set_scalar(text: str, key: str, value: str | None) -> str:
    line = f"{key}: {yaml_scalar(value)}"
    pattern = re.compile(rf"^{re.escape(key)}:\s*[^\n]*(?:\n|$)", re.M)
    if pattern.search(text):
        return pattern.sub(line + "\n", text, count=1)
    behavior_match = re.search(r"^behaviors:\s*", text, re.M)
    if behavior_match:
        return text[: behavior_match.start()] + line + "\n" + text[behavior_match.start() :]
    return text.rstrip() + "\n" + line + "\n"


def remove_scalar(text: str, key: str) -> str:
    return re.sub(rf"^{re.escape(key)}:\s*[^\n]*(?:\n|$)", "", text, count=1, flags=re.M)


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


def knowledge_manifest(root: Path) -> dict[str, dict[str, Any]]:
    """Manifest only knowledge artifacts; executor lifecycle files are excluded."""

    manifest: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return manifest
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".work/execution/") or relative in FORMAL_DRIFT_EXCLUDES:
            continue
        if not relative.startswith((".work/", "tech-pack/", "ba-pack/")):
            continue
        stat = path.stat()
        manifest[relative] = {"size": stat.st_size, "sha256": sha256_file(path)}
    return manifest


def restore_formal_drift(output: Path, baseline: Path, expected: dict[str, Any]) -> list[str]:
    current = knowledge_manifest(output)
    diff = manifest_diff(expected, current)
    changed = sorted(set(diff["added"] + diff["changed"] + diff["deleted"]))
    for relative in diff["added"]:
        target = output / relative
        if target.is_file():
            target.unlink()
    for relative in sorted(set(diff["changed"] + diff["deleted"])):
        source = baseline / relative
        target = output / relative
        if not source.is_file():
            raise ExecutorError(f"baseline cannot restore formal artifact: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.parent / f".{target.name}.formal-drift.tmp"
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    if knowledge_manifest(output) != expected:
        raise ExecutorError("formal drift restoration did not reproduce the baseline manifest")
    return changed


def generations_root(output: Path) -> Path:
    return execution_root(output) / "generations"


def generation_dir(output: Path, generation_id: str) -> Path:
    return generations_root(output) / generation_id


def generation_candidate_root(output: Path, generation_id: str) -> Path:
    return generation_dir(output, generation_id) / "candidate-root"


def create_generation(output: Path, formal_state: str) -> tuple[str, Path]:
    generation_id = f"gen-{now_utc().replace(':', '').replace('+00:00', 'Z')}-{uuid.uuid4().hex[:8]}"
    root = generation_candidate_root(output, generation_id)
    root.parent.mkdir(parents=True, exist_ok=False)
    snapshot_copy(output, root)
    payload = {
        "artifact_type": "generation-manifest",
        "artifact_schema_version": "1",
        "generation_id": generation_id,
        "repository": scalar_value(formal_state, "repository"),
        "source_commit": scalar_value(formal_state, "source_commit"),
        "status": "staging",
        "created_at": now_utc(),
        "last_committed_stage": scalar_value(formal_state, "last_committed_stage"),
        "candidate_manifest": manifest_summary(file_manifest(root)),
        "stage_history": [],
    }
    atomic_write_json(generation_dir(output, generation_id) / "generation-manifest.json", payload)
    atomic_write_json(generation_dir(output, generation_id) / "stage-history.json", {"stages": []})
    return generation_id, root


def load_generation_manifest(output: Path, generation_id: str) -> dict[str, Any]:
    path = generation_dir(output, generation_id) / "generation-manifest.json"
    payload = read_json(path)
    if payload.get("artifact_type") != "generation-manifest" or payload.get("artifact_schema_version") != "1":
        raise ExecutorError("working generation has an unsupported manifest")
    if payload.get("generation_id") != generation_id:
        raise ExecutorError("working generation identity mismatch")
    if not generation_candidate_root(output, generation_id).is_dir():
        raise ExecutorError("working generation candidate root is missing")
    return payload


def update_generation_manifest(
    output: Path,
    generation_id: str,
    stage: str,
    transaction_id: str,
    candidate_root: Path,
) -> None:
    directory = generation_dir(output, generation_id)
    manifest = load_generation_manifest(output, generation_id)
    manifest["status"] = "published" if stage == "finalization" else "staging"
    manifest["last_committed_stage"] = stage
    manifest["last_transaction"] = transaction_id
    manifest["updated_at"] = now_utc()
    manifest["candidate_manifest"] = manifest_summary(file_manifest(candidate_root))
    if stage == "finalization":
        manifest["published_source_commit"] = scalar_value(state_text(output), "source_commit")
        manifest["published_knowledge_manifest"] = knowledge_manifest(output)
    history_path = directory / "stage-history.json"
    history = read_json(history_path)
    stages = history.setdefault("stages", [])
    stages.append({"stage": stage, "transaction_id": transaction_id, "committed_at": now_utc()})
    atomic_write_json(history_path, history)
    manifest["stage_history"] = stages
    atomic_write_json(directory / "generation-manifest.json", manifest)


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
        f"artifact_schema_version: {yaml_scalar('2')}\n"
        f"workflow_schema_version: {yaml_scalar(WORKFLOW_SCHEMA_VERSION)}\n"
        f"repository: {yaml_scalar(repository)}\n"
        f"repository_path: {yaml_scalar(str(repository_path))}\n"
        f"source_commit: {yaml_scalar(commit)}\n"
        f"analysis_mode: {yaml_scalar('automatic')}\n"
        f"current_stage: {yaml_scalar('inventory')}\n"
        f"stage_status: {yaml_scalar('pending')}\n"
        "current_checkpoint: null\n"
        f"checkpoint_status: {yaml_scalar('pending')}\n"
        "active_transaction: null\n"
        "last_committed_stage: null\n"
        "working_generation_id: null\n"
        "published_generation_id: null\n"
        "published_source_commit: null\n"
        f"formal_drift_status: {yaml_scalar('clean')}\n"
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
        "artifact_schema_version": "2",
        **payload,
    }
    atomic_write_json(path, payload)
    return path


def checkpoint_path(tx_dir: Path) -> Path:
    return tx_dir / "checkpoints.json"


def initialize_checkpoints(tx_dir: Path, transaction_id: str, stage: str) -> dict[str, Any]:
    names = STAGE_CHECKPOINTS[stage]
    entries = [
        {
            "checkpoint_id": name,
            "status": "in-progress" if index == 0 else "pending",
            "reason": None,
            "updated_at": now_utc() if index == 0 else None,
        }
        for index, name in enumerate(names)
    ]
    payload = {
        "artifact_type": "checkpoint-ledger",
        "artifact_schema_version": "1",
        "transaction_id": transaction_id,
        "stage": stage,
        "checkpoints": entries,
    }
    atomic_write_json(checkpoint_path(tx_dir), payload)
    return payload


def load_checkpoints(tx_dir: Path, transaction_id: str, stage: str) -> dict[str, Any]:
    payload = read_json(checkpoint_path(tx_dir))
    if payload.get("artifact_type") != "checkpoint-ledger" or payload.get("artifact_schema_version") != "1":
        raise ExecutorError("checkpoint ledger has an unsupported schema")
    if payload.get("transaction_id") != transaction_id or payload.get("stage") != stage:
        raise ExecutorError("checkpoint ledger identity mismatch")
    entries = payload.get("checkpoints")
    if not isinstance(entries, list) or [item.get("checkpoint_id") for item in entries if isinstance(item, dict)] != list(STAGE_CHECKPOINTS[stage]):
        raise ExecutorError("checkpoint ledger does not match the stage checkpoint contract")
    return payload


def checkpoint_summary(payload: dict[str, Any]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in payload.get("checkpoints", []):
        status = str(item.get("status"))
        summary[status] = summary.get(status, 0) + 1
    return summary


def checkpoint_ledger_sha256(path: Path) -> str:
    return sha256_file(path)


def checkpoint_commit_gate(payload: dict[str, Any]) -> list[str]:
    return [
        str(item.get("checkpoint_id"))
        for item in payload.get("checkpoints", [])
        if item.get("status") not in TERMINAL_CHECKPOINT_STATUS
    ]


def skip_all_checkpoints(payload: dict[str, Any], reason: str) -> dict[str, Any]:
    for item in payload.get("checkpoints", []):
        item["status"] = "skipped"
        item["reason"] = reason
        item["updated_at"] = now_utc()
    return payload


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
        if (
            payload.get("artifact_type") == "stage-receipt"
            and payload.get("artifact_schema_version") == "2"
            and payload.get("stage") == "finalization"
            and payload.get("result") == "committed"
            and payload.get("promotion_scope") == "formal-pack"
            and payload.get("formal_pack_published") is True
        ):
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
        load_scaffold_schema(registry, assets_root=template_root())
    except RegisterSchemaError as exc:
        raise ExecutorError(f"bundled Register Schema is invalid: {exc}") from exc
    except ArtifactSchemaError as exc:
        raise ExecutorError(f"bundled Artifact Schema is invalid: {exc}") from exc
    except ArtifactScaffoldError as exc:
        raise ExecutorError(f"bundled Artifact Scaffold Schema is invalid: {exc}") from exc
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
    try:
        contract_structure = load_api_contract_structure(
            template_root() / "api-contract-structure.json"
        )
        contract_template = parse_markdown(
            (template_root() / "api-contract-document-template.md").read_text(encoding="utf-8")
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ExecutorError(f"bundled API Contract structure contract is invalid: {exc}") from exc
    contract_structure_errors = list(contract_template.issues)
    contract_structure_errors.extend(
        validate_api_contract_tables(contract_template, contract_structure)
    )
    if contract_structure_errors:
        raise ExecutorError(
            "API Contract template and structure contract are out of sync: "
            + " | ".join(issue.message for issue in contract_structure_errors)
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


def validator_commands(
    stage: str,
    candidate: Path,
    repo: Path,
    *,
    diagnostic_manifest: bool = False,
    analysis_state_override: Path | None = None,
) -> list[list[str]]:
    scripts = Path(__file__).resolve().parent
    python = sys.executable
    state = analysis_state_override or candidate / ".work" / "analysis-state.yaml"
    catalog = candidate / ".work" / "behavior-catalog.yaml"
    dossiers = candidate / ".work" / "behavior-dossiers"
    commands: list[list[str]] = []
    publication_stages = {
        "tech-publication",
        "api-contract-publication",
        "business-model",
        "ba-publication",
        "finalization",
    }
    if stage in publication_stages:
        commands.append(
            [
                python,
                str(scripts / "validate_markdown_structure.py"),
                str(candidate),
                "--json",
            ]
        )

    def structurally_valid(document: Path) -> bool:
        try:
            return not parse_markdown(document.read_text(encoding="utf-8")).issues
        except OSError:
            return False
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
            if not structurally_valid(document):
                continue
            command = [python, str(scripts / "validate_behavior_doc.py"), str(document), "--repo", str(repo)]
            if stage in {"tech-publication", "api-contract-publication"}:
                command.append("--allow-missing-ba")
            if stage == "tech-publication":
                command.append("--allow-missing-api-contracts")
            commands.append(command)

    if stage in {"api-contract-publication", "ba-publication", "finalization"}:
        for document in sorted((candidate / "tech-pack" / "contracts").glob("*.api-contract.md")):
            if not structurally_valid(document):
                continue
            commands.append(
                [python, str(scripts / "validate_api_contract.py"), str(document), "--repo", str(repo)]
            )

    if stage in {"ba-publication", "finalization"}:
        for document in sorted((candidate / "ba-pack" / "journeys").glob("*.md")):
            if not structurally_valid(document):
                continue
            commands.append([python, str(scripts / "validate_ba_journey.py"), str(document)])
        for document in sorted((candidate / "ba-pack" / "scenarios").glob("*.md")):
            if not structurally_valid(document):
                continue
            commands.append([python, str(scripts / "validate_ba_scenario.py"), str(document)])

    if stage in {
        "tech-publication",
        "api-contract-publication",
        "ba-publication",
        "finalization",
    }:
        command = [
            python,
            str(scripts / "validate_pack_links.py"),
            str(candidate),
            "--repo",
            str(repo),
            "--json",
            "--validation-profile",
            "tech-publication" if stage == "tech-publication" else "complete",
        ]
        command.append(
            "--skip-artifact-manifest"
            if diagnostic_manifest
            else "--require-artifact-manifest"
        )
        commands.append(command)
    return commands


def stage_gates(
    stage: str,
    candidate: Path,
    repo: Path,
    *,
    diagnostic_manifest: bool = False,
    analysis_state_override: Path | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    try:
        registry = load_registry()
        if diagnostic_manifest:
            assessment = assess_artifact_manifest(candidate, registry)
            errors.extend(
                f"Artifact Schema: {message}" for message in assessment.errors
            )
        else:
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

    results = [
        run_validator(command, candidate)
        for command in validator_commands(
            stage,
            candidate,
            repo,
            diagnostic_manifest=diagnostic_manifest,
            analysis_state_override=analysis_state_override,
        )
    ]
    for result in results:
        if result["exit_code"] != 0:
            errors.append("validator failed: " + " ".join(result["command"]))
    return errors, results


def validation_item(
    code: str,
    message: str,
    *,
    source: str,
    path: str | None = None,
    line: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "code": code,
        "source": source,
        "message": message,
    }
    if path:
        item["path"] = path
    if line is not None:
        item["line"] = line
    return item


def compact_validation_section(
    items: list[dict[str, Any]],
    *,
    total_count: int | None = None,
) -> dict[str, Any]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    visible: list[dict[str, Any]] = []
    per_code: dict[str, int] = {}
    for item in unique:
        code = str(item.get("code", "UNKNOWN"))
        if len(visible) >= VALIDATION_DETAIL_LIMIT:
            continue
        if per_code.get(code, 0) >= VALIDATION_PER_CODE_LIMIT:
            continue
        visible.append(item)
        per_code[code] = per_code.get(code, 0) + 1
    observed_count = len(unique) if total_count is None else max(total_count, len(unique))
    return {
        "count": observed_count,
        "items": visible,
        "suppressed_count": max(0, observed_count - len(visible)),
    }


def validator_name(result: dict[str, Any]) -> str:
    command = result.get("command", [])
    if isinstance(command, list) and len(command) > 1:
        return Path(str(command[1])).name
    return "validator"


def parse_validator_diagnostics(
    result: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    int,
    int,
    int,
]:
    """Classify one Validator result without copying its raw output into the report."""
    name = validator_name(result)
    semantic: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    forward: list[dict[str, Any]] = []
    forward_total = 0
    semantic_total = 0
    warning_total = 0
    stdout = str(result.get("stdout", ""))
    payload: dict[str, Any] | None = None
    try:
        candidate_payload = json.loads(stdout)
        if isinstance(candidate_payload, dict):
            payload = candidate_payload
    except json.JSONDecodeError:
        payload = None

    if payload is not None and isinstance(payload.get("documents"), list):
        for document in payload["documents"]:
            if not isinstance(document, dict):
                continue
            path = str(document.get("path", "")) or None
            for issue in document.get("issues", []):
                if not isinstance(issue, dict):
                    continue
                line_value = issue.get("line")
                semantic.append(
                    validation_item(
                        str(issue.get("code", "MARKDOWN-STRUCTURE")),
                        str(issue.get("message", "invalid Markdown structure")),
                        source=name,
                        path=path,
                        line=line_value if isinstance(line_value, int) else None,
                    )
                )
        semantic_total = len(semantic)
    elif payload is not None and isinstance(payload.get("errors"), dict):
        for code, messages in payload["errors"].items():
            if not isinstance(messages, list):
                continue
            semantic.extend(
                validation_item(str(code), str(message), source=name)
                for message in messages
            )
        skipped = payload.get("skipped", {})
        if isinstance(skipped, dict):
            semantic.extend(
                validation_item(
                    f"SKIPPED:{code}",
                    str(reason),
                    source=name,
                )
                for code, reason in skipped.items()
            )
        primary_errors = payload.get("primary_errors")
        semantic_total = (
            primary_errors if isinstance(primary_errors, int) else len(semantic)
        ) + (len(skipped) if isinstance(skipped, dict) else 0)
        warning_messages = payload.get("warning_messages", [])
        if isinstance(warning_messages, list):
            warnings.extend(
                validation_item("VALIDATOR-WARNING", str(message), source=name)
                for message in warning_messages
            )
        declared_warnings = payload.get("warnings")
        warning_total = (
            declared_warnings
            if isinstance(declared_warnings, int)
            else len(warnings)
        )
        forward_total = (
            payload.get("deferred_link_count", 0)
            if isinstance(payload.get("deferred_link_count", 0), int)
            else 0
        )
        deferred_links = payload.get("deferred_links", [])
        if isinstance(deferred_links, list):
            for item in deferred_links:
                if not isinstance(item, dict):
                    continue
                forward.append(
                    {
                        "code": str(item.get("check", "cross-stage-reference")),
                        "source": str(item.get("source", "")),
                        "target": str(item.get("target", "")),
                    }
                )
    else:
        error_pattern = re.compile(
            r"^ERROR(?:\s+\[(?P<code>[^]]+)\])?(?::\s*|\s+)(?P<message>.*)$"
        )
        warning_pattern = re.compile(
            r"^WARNING(?:\s+\[(?P<code>[^]]+)\])?(?::\s*|\s+)(?P<message>.*)$"
        )
        for line in stdout.splitlines():
            if match := error_pattern.match(line.strip()):
                semantic.append(
                    validation_item(
                        match.group("code") or "DOCUMENT-VALIDATION",
                        match.group("message"),
                        source=name,
                    )
                )
            elif match := warning_pattern.match(line.strip()):
                warnings.append(
                    validation_item(
                        match.group("code") or "VALIDATOR-WARNING",
                        match.group("message"),
                        source=name,
                    )
                )
        semantic_total = len(semantic)
        warning_total = len(warnings)

    if result.get("exit_code") != 0 and not semantic:
        stderr = str(result.get("stderr", "")).strip()
        detail = stderr.splitlines()[0] if stderr else "Validator exited without structured errors"
        blocking.append(
            validation_item("VALIDATOR-EXECUTION", detail, source=name)
        )
    return (
        semantic,
        blocking,
        warnings,
        forward,
        forward_total,
        max(semantic_total, len(semantic)),
        max(warning_total, len(warnings)),
    )


def projected_validation_state(
    stage: str,
    candidate: Path,
) -> tuple[str, list[dict[str, Any]]]:
    state = (candidate / STATE_FILE).read_text(encoding="utf-8")
    semantic: list[dict[str, Any]] = []
    if stage == "synthesis":
        state = candidate_state_for_commit(state, stage, "complete", False)
    elif stage == "business-model":
        model = candidate / ".work" / "business-model.md"
        model_status = None
        if model.is_file():
            model_status = scalar_value(model.read_text(encoding="utf-8"), "business_model_status")
        if model_status in {"complete", "partial", "blocked"}:
            state = candidate_state_for_commit(state, stage, model_status, False)
        else:
            semantic.append(
                validation_item(
                    "BUSINESS-MODEL-SEMANTIC-RESULT",
                    "business-model.md must declare business_model_status complete, partial, or blocked before validation",
                    source="stage-executor",
                    path=".work/business-model.md",
                )
            )
    return state, semantic


def empty_stage_validation_report(
    stage: str | None,
    transaction_id: str,
) -> dict[str, Any]:
    return {
        "stage_validation_report_schema_version": STAGE_VALIDATION_REPORT_SCHEMA_VERSION,
        "result": "ready",
        "stage": stage,
        "transaction_id": transaction_id,
        "semantic_or_document_errors": compact_validation_section([]),
        "expected_candidate_manifest_drift": {
            "status": "none",
            "refresh_on_commit": False,
            "reasons": [],
        },
        "cross_stage_forward_references": {
            "count": 0,
            "groups": [],
            "items": [],
            "suppressed_count": 0,
        },
        "blocking_errors": compact_validation_section([]),
        "warnings": compact_validation_section([]),
        "validator_summary": [],
    }


def forward_reference_section(
    items: list[dict[str, Any]], total_count: int
) -> dict[str, Any]:
    compact = compact_validation_section(items, total_count=total_count)
    groups: dict[str, int] = {}
    for item in items:
        code = str(item.get("code", "cross-stage-reference"))
        groups[code] = groups.get(code, 0) + 1
    return {
        "count": compact["count"],
        "groups": [
            {"kind": kind, "count": count}
            for kind, count in sorted(groups.items())
        ],
        "items": compact["items"],
        "suppressed_count": compact["suppressed_count"],
    }


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
    text = set_scalar(text, "current_checkpoint", None)
    text = set_scalar(text, "checkpoint_status", "pending")
    if stage == "finalization":
        text = set_scalar(text, "current_stage", "completed")
        text = set_scalar(text, "stage_status", "committed")
        text = set_scalar(text, "publication_status", "complete")
        generation_id = scalar_value(text, "working_generation_id")
        text = set_scalar(text, "published_generation_id", generation_id)
        text = set_scalar(text, "published_source_commit", scalar_value(text, "source_commit"))
    else:
        text = set_scalar(text, "current_stage", upcoming)
        text = set_scalar(text, "stage_status", "pending")
        if upcoming in {"tech-publication", "api-contract-publication", "business-model", "ba-publication", "finalization"} or stage == "synthesis":
            text = set_scalar(text, "publication_status", "staging")
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

        api_behaviors: list[str] = []
        declared_contracts: set[str] = set()
        unreadable_behaviors: list[str] = []
        behaviors_dir = candidate / "tech-pack" / "behaviors"
        for document in sorted(behaviors_dir.glob("*.md")):
            frontmatter = markdown_frontmatter(document)
            if frontmatter is None:
                unreadable_behaviors.append(document.name)
                continue
            if scalar_value(frontmatter, "entry_type") == "api":
                api_behaviors.append(
                    scalar_value(frontmatter, "behavior_id") or document.name
                )
            _, api_contract_block = yaml_block(frontmatter, "api_contracts")
            declared_contracts.update(
                item.strip()
                for item in re.findall(
                    r"^\s*-\s+endpoint_id:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
                    api_contract_block,
                    re.M,
                )
            )

        catalog = candidate / "tech-pack" / "behavior-catalog.yaml"
        if catalog.is_file():
            declared_contracts.update(
                item.strip()
                for item in re.findall(
                    r"^\s*-\s+endpoint_id:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
                    catalog.read_text(encoding="utf-8"),
                    re.M,
                )
            )

        blockers: list[str] = []
        if api_behaviors:
            blockers.append("API Behaviors: " + ", ".join(sorted(api_behaviors)))
        if declared_contracts:
            blockers.append(
                "planned API Contracts: " + ", ".join(sorted(declared_contracts))
            )
        if unreadable_behaviors:
            blockers.append(
                "unreadable Tech Behavior frontmatter: "
                + ", ".join(sorted(unreadable_behaviors))
            )
        if blockers:
            raise ExecutorError(
                "cannot skip API Contract publication while API publication intent exists ("
                + "; ".join(blockers)
                + ")"
            )
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


def _reinitialize_archived_artifact(
    candidate: Path,
    step: dict[str, Any],
    repo: Path,
    commit: str,
    output: Path,
) -> str:
    paths = [str(item) for item in step.get("output_paths", [])]
    if len(paths) != 1:
        raise ExecutorError("template reinitialization requires exactly one output path")
    target = candidate / paths[0]
    artifact_type = str(step.get("artifact_type"))
    if artifact_type == "analysis-state":
        text = initial_state(repo.name, repo, commit, output)
    elif artifact_type == "working-behavior-catalog":
        text = initial_catalog(repo.name, commit)
    elif artifact_type == "repository-register":
        text = render_template("repository-register-template.md", repo.name, commit)
    else:
        raise ExecutorError(
            f"archive-and-rebuild cannot reinitialize unsupported artifact type: {artifact_type}"
        )
    atomic_write_text(target, text)
    return paths[0]


def _assert_transform_report_matches_plan(
    step: dict[str, Any], report: dict[str, Any]
) -> None:
    expected = step.get("expected", {})
    comparisons = {
        "input_file_count": report.get("input_summary", {}).get("file_count"),
        "output_file_count": report.get("output_summary", {}).get("file_count"),
        "source_record_counts": report.get("source_records"),
        "output_record_counts": report.get("output_records"),
    }
    mismatches = [
        f"{key}: expected {expected.get(key)!r}, observed {observed!r}"
        for key, observed in comparisons.items()
        if expected.get(key) != observed
    ]
    expected_checks = set(expected.get("referential_checks", []))
    observed_checks = report.get("referential_check_results", {})
    missing_checks = sorted(
        check for check in expected_checks if observed_checks.get(check) != "passed"
    )
    if mismatches or missing_checks:
        detail = mismatches + ["failed referential checks: " + ", ".join(missing_checks)]
        raise ExecutorError(
            f"registered transform {step.get('transform_id')} violated its plan: "
            + " | ".join(detail)
        )


def _complete_migration_checkpoints(tx_dir: Path, transaction_id: str) -> dict[str, Any]:
    ledger = initialize_checkpoints(tx_dir, transaction_id, MIGRATION_STAGE)
    for item in ledger["checkpoints"]:
        item["status"] = "complete"
        item["reason"] = "completed by the deterministic migration executor"
        item["updated_at"] = now_utc()
    atomic_write_json(checkpoint_path(tx_dir), ledger)
    return ledger


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
        automatic_actions: list[str] = []
        transform_reports: list[dict[str, Any]] = []
        reinitialized_artifacts: list[str] = []
        for step in plan.get("steps", []):
            action = step.get("action")
            for relative in step.get("paths", []):
                target = candidate / str(relative)
                if action == "archive-and-rebuild":
                    _remove_candidate_path(target)
                    automatic_actions.append(f"invalidated {relative}")
            if action == "archive-and-rebuild" and step.get("reinitialize_from_template"):
                relative = _reinitialize_archived_artifact(
                    candidate, step, repo, commit, output
                )
                reinitialized_artifacts.append(relative)
                automatic_actions.append(f"reinitialized structural shell for {relative}")
            elif action == "mechanical-migrate":
                transform_id = str(step.get("transform_id", ""))
                transform = registry.transform_registry.definitions.get(transform_id)
                if transform is None:
                    raise ExecutorError(
                        f"Migration step references unregistered transform: {transform_id or '<missing>'}"
                    )
                try:
                    report = execute_transform(
                        transform,
                        candidate,
                        [str(item) for item in step.get("input_paths", [])],
                        [str(item) for item in step.get("output_paths", [])],
                        registry.transform_registry.root,
                    )
                except MigrationTransformError as exc:
                    raise ExecutorError(
                        f"registered transform {transform_id} failed: {exc}"
                    ) from exc
                _assert_transform_report_matches_plan(step, report)
                transform_reports.append(report)
                automatic_actions.append(f"executed {transform_id}")

        candidate_state_path = candidate / STATE_FILE
        if not candidate_state_path.is_file():
            raise ExecutorError("Migration Candidate has no reinitialized or migrated analysis state")
        candidate_state = _finalize_migration_candidate_state(candidate, plan, repo)
        candidate_plan = dict(plan)
        candidate_plan["status"] = "committed"
        write_migration_plan(candidate_plan_path, candidate_plan)
        write_artifact_manifest(
            candidate,
            registry,
            str(repo),
            commit,
            MIGRATION_STAGE,
            transaction_id,
            plan.get("invalidated_artifacts", []),
        )
        checkpoints = _complete_migration_checkpoints(tx_dir, transaction_id)
        errors, diff = _validate_migration_candidate(
            output, candidate, plan, registry, repo, commit, transaction_id
        )
        if errors:
            raise ExecutorError(
                "deterministic Migration Candidate failed validation: " + " | ".join(errors)
            )
        mechanical_output_manifest = {
            "mechanical_output_manifest_schema_version": "1",
            "plan_id": plan["plan_id"],
            "transaction_id": transaction_id,
            "repository": str(repo),
            "source_commit": commit,
            "candidate_manifest": file_manifest(candidate),
            "candidate_summary": manifest_summary(file_manifest(candidate)),
            "changes": diff,
            "transform_reports": transform_reports,
            "reinitialized_artifacts": reinitialized_artifacts,
            "invalidated_artifacts": plan.get("invalidated_artifacts", []),
            "checkpoint_summary": checkpoint_summary(checkpoints),
            "sealed_at": now_utc(),
        }
        mechanical_manifest_path = tx_dir / "mechanical-output-manifest.json"
        atomic_write_json(mechanical_manifest_path, mechanical_output_manifest)

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
            "mechanical_output_manifest": str(mechanical_manifest_path),
            "mechanical_output_manifest_sha256": sha256_file(mechanical_manifest_path),
            "candidate_sealed": True,
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
            "mechanical_output_manifest": str(tx_dir / "mechanical-output-manifest.json"),
            "instruction": "Candidate is executor-generated and sealed; inspect the plan and mechanical report, then commit without editing Candidate",
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
    generation_id = scalar_value(formal_state, "working_generation_id")
    generation_created = False
    try:
        tx_dir.mkdir(parents=True, exist_ok=False)
        baseline = tx_dir / "baseline"
        snapshot_copy(output, baseline)
        atomic_write_json(tx_dir / "baseline-manifest.json", knowledge_manifest(output))
        source_root = output
        if current_stage in GENERATION_STAGES:
            if generation_id is None:
                if current_stage != "synthesis":
                    raise ExecutorError("a working generation must exist before this stage")
                generation_id, source_root = create_generation(output, formal_state)
                generation_created = True
            else:
                load_generation_manifest(output, generation_id)
                source_root = generation_candidate_root(output, generation_id)
        snapshot_copy(source_root, candidate)
        automatic_actions: list[str] = []
        candidate_state = (candidate / STATE_FILE).read_text(encoding="utf-8")
        candidate_state = set_scalar(candidate_state, "stage_status", "in-progress")
        candidate_state = set_scalar(candidate_state, "active_transaction", transaction_id)
        first_checkpoint = STAGE_CHECKPOINTS[current_stage][0]
        candidate_state = set_scalar(candidate_state, "current_checkpoint", first_checkpoint)
        candidate_state = set_scalar(candidate_state, "checkpoint_status", "in-progress")
        candidate_state = set_scalar(candidate_state, "working_generation_id", generation_id)
        candidate_state = set_scalar(candidate_state, "formal_drift_status", "clean")
        if current_stage in GENERATION_STAGES:
            candidate_state = set_scalar(candidate_state, "publication_status", "staging")
        atomic_write_text(candidate / STATE_FILE, candidate_state)
        candidate_invalidated: list[dict[str, Any]] = []
        candidate_manifest_path = candidate / ".work" / "artifact-manifest.json"
        if candidate_manifest_path.is_file():
            observed_invalidated = read_json(candidate_manifest_path).get(
                "invalidated_artifacts", []
            )
            if isinstance(observed_invalidated, list):
                candidate_invalidated = [
                    item for item in observed_invalidated if isinstance(item, dict)
                ]
        write_artifact_manifest(
            candidate,
            registry,
            str(repo),
            commit,
            current_stage,
            transaction_id,
            candidate_invalidated,
        )
        candidate_manifest_errors = validate_artifact_manifest(candidate, registry)
        if candidate_manifest_errors:
            raise ExecutorError(
                "cannot initialize Candidate Artifact Manifest: "
                + " | ".join(candidate_manifest_errors)
            )
        initialize_checkpoints(tx_dir, transaction_id, current_stage)
        transaction = {
            "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
            "transaction_id": transaction_id,
            "stage": current_stage,
            "status": "in-progress",
            "repository": str(repo),
            "source_commit": commit,
            "output": str(output),
            "candidate": str(candidate),
            "baseline": str(baseline),
            "generation_id": generation_id,
            "generation_created": generation_created,
            "promotion_scope": "generation" if current_stage in GENERATION_STAGES and current_stage != "finalization" else "formal-pack",
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
        formal_state = set_scalar(formal_state, "current_checkpoint", first_checkpoint)
        formal_state = set_scalar(formal_state, "checkpoint_status", "in-progress")
        formal_state = set_scalar(formal_state, "working_generation_id", generation_id)
        formal_state = set_scalar(formal_state, "formal_drift_status", "clean")
        if current_stage in GENERATION_STAGES:
            formal_state = set_scalar(formal_state, "publication_status", "staging")
        atomic_write_text(state_path(output), formal_state)
    except Exception:
        if tx_dir.exists():
            shutil.rmtree(tx_dir, ignore_errors=True)
        if generation_created and generation_id:
            shutil.rmtree(generation_dir(output, generation_id), ignore_errors=True)
        release_lock(output, transaction_id)
        raise
    emit(
        {
            "result": "begun",
            "stage": current_stage,
            "transaction_id": transaction_id,
            "candidate": str(candidate),
            "generation_id": generation_id,
            "promotion_scope": "generation" if current_stage in GENERATION_STAGES and current_stage != "finalization" else "formal-pack",
            "instruction": "write every stage artifact under candidate, then run commit",
        },
        args.json,
    )
    return 0


def command_checkpoint(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    tx_dir, transaction, candidate = load_transaction(output, args.transaction)
    stage = str(transaction.get("stage"))
    if stage == MIGRATION_STAGE:
        raise ExecutorError(
            "migration checkpoints are executor-owned and complete when the sealed Candidate is created"
        )
    else:
        formal = state_text(output)
        if scalar_value(formal, "active_transaction") != args.transaction:
            raise ExecutorError("analysis state does not own this transaction")
    ledger = load_checkpoints(tx_dir, args.transaction, stage)
    entries = ledger["checkpoints"]
    target = next((item for item in entries if item["checkpoint_id"] == args.checkpoint), None)
    if target is None:
        raise ExecutorError(f"checkpoint is not valid for {stage}: {args.checkpoint}")
    if args.status not in ALLOWED_CHECKPOINT_STATUS - {"pending"}:
        raise ExecutorError("checkpoint status cannot be set to pending")
    if args.status in {"skipped", "blocked", "failed"} and not (args.reason or "").strip():
        raise ExecutorError(f"checkpoint status {args.status} requires --reason")
    first_open = next(
        (item for item in entries if item.get("status") in {"pending", "in-progress", "failed"}),
        entries[-1],
    )
    if target is not first_open and target.get("status") not in TERMINAL_CHECKPOINT_STATUS:
        raise ExecutorError(f"checkpoint order violation; current checkpoint is {first_open['checkpoint_id']}")

    target["status"] = args.status
    target["reason"] = args.reason
    target["updated_at"] = now_utc()
    if args.status in TERMINAL_CHECKPOINT_STATUS:
        target_index = entries.index(target)
        next_item = next(
            (item for item in entries[target_index + 1 :] if item.get("status") == "pending"),
            None,
        )
        if next_item is not None:
            next_item["status"] = "in-progress"
            next_item["updated_at"] = now_utc()
            current_id = next_item["checkpoint_id"]
            current_status = "in-progress"
        else:
            current_id = target["checkpoint_id"]
            current_status = target["status"]
    else:
        current_id = target["checkpoint_id"]
        current_status = target["status"]
    atomic_write_json(checkpoint_path(tx_dir), ledger)

    candidate_state_path = candidate / STATE_FILE
    candidate_state = candidate_state_path.read_text(encoding="utf-8")
    candidate_state = set_scalar(candidate_state, "current_checkpoint", current_id)
    candidate_state = set_scalar(candidate_state, "checkpoint_status", current_status)
    candidate_state = set_scalar(
        candidate_state,
        "stage_status",
        "failed" if args.status == "failed" else "in-progress",
    )
    atomic_write_text(candidate_state_path, candidate_state)
    if stage != MIGRATION_STAGE:
        formal = set_scalar(formal, "current_checkpoint", current_id)
        formal = set_scalar(formal, "checkpoint_status", current_status)
        formal = set_scalar(formal, "stage_status", "failed" if args.status == "failed" else "in-progress")
        atomic_write_text(state_path(output), formal)
    emit(
        {
            "result": "checkpoint-updated",
            "stage": stage,
            "checkpoint": args.checkpoint,
            "checkpoint_status": args.status,
            "current_checkpoint": current_id,
            "summary": checkpoint_summary(ledger),
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
    generation_move_in_progress = (
        transaction.get("status") == "generation-promoting" and not candidate.exists()
    )
    if candidate != (tx_dir / "candidate").resolve() or (
        not candidate.is_dir() and not generation_move_in_progress
    ):
        raise ExecutorError("transaction candidate is missing or outside its transaction")
    return tx_dir, transaction, candidate


def command_scaffold(args: argparse.Namespace) -> int:
    """Create one identity-correct template Artifact inside an owned Candidate."""
    output = args.output.expanduser().resolve()
    tx_dir, transaction, candidate = load_transaction(output, args.transaction)
    stage = str(transaction.get("stage"))
    if stage in {MIGRATION_STAGE, "finalization"}:
        raise ExecutorError(f"Artifact scaffolding is not allowed during {stage}")
    if transaction.get("status") not in VALIDATABLE_TRANSACTION_STATUSES:
        raise ExecutorError(
            f"transaction status {transaction.get('status')} does not allow Artifact scaffolding"
        )

    formal = state_text(output)
    if scalar_value(formal, "active_transaction") != args.transaction:
        raise ExecutorError("analysis state does not own this transaction")
    lock = read_json(lock_path(output))
    if lock.get("transaction_id") != args.transaction or lock.get("stage") != stage:
        raise ExecutorError("execution lock does not own the requested transaction and stage")
    journal = read_json(tx_dir / "promotion-journal.json")
    if journal.get("phase") not in VALIDATABLE_JOURNAL_PHASES:
        raise ExecutorError(
            f"promotion journal phase {journal.get('phase')} requires recover before scaffolding"
        )

    repo, actual_commit = verify_repo_and_commit(formal)
    if transaction.get("repository") != str(repo):
        raise ExecutorError("transaction repository does not match analysis state")
    if transaction.get("source_commit") != actual_commit:
        raise ExecutorError("transaction source commit does not match the current repository")
    repository = scalar_value(formal, "repository")
    source_commit_value = scalar_value(formal, "source_commit") or "unknown"
    if not repository:
        raise ExecutorError("analysis state is missing repository identity")

    try:
        registry = load_registry()
        scaffold_schema = load_scaffold_schema(
            registry, assets_root=template_root()
        )
        identity = parse_identity_arguments(list(args.identity or []))
        scaffold_definition = scaffold_schema.definitions.get(args.artifact_type)
        if scaffold_definition is None:
            raise ArtifactScaffoldError(
                f"Artifact type is not scaffoldable: {args.artifact_type}"
            )
        artifact_definition = registry.definitions[args.artifact_type]
        if artifact_definition.producing_stage != stage:
            raise ArtifactScaffoldError(
                f"Artifact {args.artifact_type} belongs to stage "
                f"{artifact_definition.producing_stage}, not {stage}"
            )
        rendered = render_artifact(
            registry,
            scaffold_schema,
            template_root(),
            args.artifact_type,
            repository,
            source_commit_value,
            identity,
        )
    except (ArtifactSchemaError, ArtifactScaffoldError) as exc:
        raise ExecutorError(str(exc)) from exc

    relative = Path(rendered.relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ExecutorError("Scaffold destination must remain inside the Candidate")
    destination = candidate / relative
    candidate_root = candidate.resolve()
    try:
        destination.resolve(strict=False).relative_to(candidate_root)
    except ValueError as exc:
        raise ExecutorError("Scaffold destination escapes the Candidate") from exc
    cursor = candidate_root
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ExecutorError(f"Scaffold destination traverses a symbolic link: {cursor}")

    result = "created"
    if destination.exists():
        if not destination.is_file() or destination.is_symlink():
            raise ExecutorError(f"Scaffold destination is not a regular file: {destination}")
        try:
            matches, mismatches = existing_artifact_matches(
                destination,
                rendered,
                repository,
                source_commit_value,
            )
        except ArtifactScaffoldError as exc:
            raise ExecutorError(str(exc)) from exc
        if not matches:
            raise ExecutorError(
                "existing Artifact identity conflicts with Scaffold request: "
                + " | ".join(mismatches)
            )
        result = "already-exists"
    else:
        try:
            pre_assessment = assess_artifact_manifest(candidate, registry)
        except ArtifactSchemaError as exc:
            raise ExecutorError(f"cannot assess Candidate Artifact Manifest: {exc}") from exc
        if pre_assessment.status == "invalid":
            raise ExecutorError(
                "Candidate Artifact Manifest is invalid before scaffolding: "
                + " | ".join(pre_assessment.errors)
            )
        atomic_write_text(destination, rendered.content)

    try:
        assessment = assess_artifact_manifest(candidate, registry)
    except ArtifactSchemaError as exc:
        if result == "created" and destination.is_file():
            destination.unlink()
        raise ExecutorError(f"cannot assess scaffolded Artifact: {exc}") from exc
    if assessment.status == "invalid":
        if result == "created" and destination.is_file():
            destination.unlink()
        raise ExecutorError(
            "scaffolded Artifact has invalid identity or schema: "
            + " | ".join(assessment.errors)
        )

    emit(
        {
            "result": result,
            "stage": stage,
            "transaction_id": args.transaction,
            "artifact_type": rendered.artifact_type,
            "artifact_schema_version": rendered.artifact_schema_version,
            "relative_path": rendered.relative_path,
            "path": str(destination),
            "identity": rendered.identity,
            "candidate_manifest_status": assessment.status,
        },
        args.json,
    )
    return 0


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
                "--validation-profile",
                "complete",
                "--skip-artifact-manifest",
            ]
        )
    if stage == "finalization":
        commands.insert(
            0,
            [
                sys.executable,
                str(scripts / "validate_markdown_structure.py"),
                str(output),
                "--json",
            ],
        )
    return [run_validator(command, output) for command in commands]


def pack_validation_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge structured domain summaries without treating unavailable indexes as empty."""
    summary: dict[str, Any] = {
        "validator_domain_statuses": {},
        "primary_error_count": 0,
        "skipped_group_count": 0,
        "suppressed_error_count": 0,
    }
    for result in results:
        try:
            payload = json.loads(result.get("stdout", ""))
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        domain_statuses = payload.get("domain_statuses", {})
        if isinstance(domain_statuses, dict):
            summary["validator_domain_statuses"].update(domain_statuses)
        for source_key, target_key in (
            ("primary_errors", "primary_error_count"),
            ("skipped_validation_groups", "skipped_group_count"),
            ("suppressed_row_errors", "suppressed_error_count"),
        ):
            value = payload.get(source_key, 0)
            if isinstance(value, int):
                summary[target_key] += value
    return summary


def archive_legacy_artifacts(
    output: Path, plan: dict[str, Any], transaction_id: str
) -> Path | None:
    paths = sorted(
        {
            str(relative)
            for step in plan.get("steps", [])
            if step.get("action") == "archive-and-rebuild"
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
    add_artifact_metadata(path, "analysis-state", "2")
    text = path.read_text(encoding="utf-8")
    text = remove_scalar(text, "phase")
    target = str(plan["resume_stage_after_migration"])
    text = set_scalar(text, "workflow_schema_version", WORKFLOW_SCHEMA_VERSION)
    text = set_scalar(text, "repository_path", str(repo))
    text = set_scalar(text, "current_stage", target)
    text = set_scalar(text, "stage_status", "pending")
    text = set_scalar(text, "active_transaction", None)
    text = set_scalar(text, "last_committed_stage", previous_stage(target))
    text = set_scalar(text, "current_checkpoint", None)
    text = set_scalar(text, "checkpoint_status", "pending")
    text = set_scalar(text, "working_generation_id", None)
    text = set_scalar(text, "published_generation_id", None)
    text = set_scalar(text, "published_source_commit", None)
    text = set_scalar(text, "formal_drift_status", "clean")
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
        retained = step.get("action") in {"mechanical-migrate", "preserve"} or (
            step.get("action") == "archive-and-rebuild"
            and step.get("reinitialize_from_template")
        )
        if not retained:
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
                    f"mechanical Migration output does not use the current schema: {relative}; expected "
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
                    "mechanically migrated or reinitialized Register does not match the current schema: "
                    + " | ".join(register_errors)
                )
    errors.extend(validate_artifact_manifest(candidate, registry))
    return errors, diff


def _load_sealed_mechanical_output(
    tx_dir: Path,
    transaction: dict[str, Any],
    candidate: Path,
) -> dict[str, Any]:
    path = tx_dir / "mechanical-output-manifest.json"
    if not path.is_file():
        raise ExecutorError("migration transaction has no Mechanical Output Manifest")
    expected_hash = transaction.get("mechanical_output_manifest_sha256")
    if not isinstance(expected_hash, str) or sha256_file(path) != expected_hash:
        raise ExecutorError("Mechanical Output Manifest was modified after Candidate sealing")
    payload = read_json(path)
    if (
        payload.get("mechanical_output_manifest_schema_version") != "1"
        or payload.get("transaction_id") != transaction.get("transaction_id")
        or payload.get("plan_id") != transaction.get("plan_id")
    ):
        raise ExecutorError("Mechanical Output Manifest identity is invalid")
    sealed_manifest = payload.get("candidate_manifest")
    if not isinstance(sealed_manifest, dict):
        raise ExecutorError("Mechanical Output Manifest has no Candidate file inventory")
    if file_manifest(candidate) != sealed_manifest:
        raise ExecutorError(
            "sealed Migration Candidate was modified after deterministic execution"
        )
    return payload


def command_commit_migration(
    args: argparse.Namespace,
    output: Path,
    tx_dir: Path,
    transaction: dict[str, Any],
    candidate: Path,
) -> int:
    if args.skip or args.semantic_result is not None:
        raise ExecutorError("Migration cannot use --skip or --semantic-result")
    checkpoints = load_checkpoints(tx_dir, args.transaction, MIGRATION_STAGE)
    incomplete_checkpoints = checkpoint_commit_gate(checkpoints)
    if incomplete_checkpoints:
        raise ExecutorError(
            "migration has incomplete checkpoints: " + ", ".join(incomplete_checkpoints)
        )
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
    try:
        mechanical_output = _load_sealed_mechanical_output(
            tx_dir, transaction, candidate
        )
    except ExecutorError as exc:
        transaction["status"] = "failed"
        transaction["last_attempt_at"] = now_utc()
        transaction["errors"] = [str(exc)]
        atomic_write_json(tx_dir / "transaction.json", transaction)
        emit(
            {
                "result": "failed",
                "stage": MIGRATION_STAGE,
                "transaction_id": args.transaction,
                "errors": [str(exc)],
                "candidate": str(candidate),
            },
            args.json,
        )
        return 1
    candidate_state_path = candidate / STATE_FILE
    candidate_state = candidate_state_path.read_text(encoding="utf-8")
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
            "mechanical_output_manifest_sha256": transaction.get(
                "mechanical_output_manifest_sha256"
            ),
            "mechanical_output_manifest": mechanical_output,
            "transform_reports": mechanical_output.get("transform_reports", []),
            "reinitialized_artifacts": mechanical_output.get(
                "reinitialized_artifacts", []
            ),
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
            "checkpoint_summary": checkpoint_summary(checkpoints),
            "checkpoint_ledger_sha256": checkpoint_ledger_sha256(checkpoint_path(tx_dir)),
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


def commit_generation_stage(
    *,
    output: Path,
    tx_dir: Path,
    transaction: dict[str, Any],
    candidate: Path,
    candidate_state: str,
    stage: str,
    repo: Path,
    commit: str,
    registry: Any,
    invalidated: list[dict[str, Any]],
    validators: list[dict[str, Any]],
    checkpoints: dict[str, Any],
    skipped: bool,
    skip_reason: str | None,
    as_json: bool,
) -> int:
    generation_id = str(transaction.get("generation_id") or "")
    if not generation_id:
        raise ExecutorError(f"stage {stage} has no working generation")
    current_root = generation_candidate_root(output, generation_id)
    load_generation_manifest(output, generation_id)
    if not current_root.is_dir():
        raise ExecutorError("working generation root is missing")

    sequence = receipt_count(output)
    input_manifest = file_manifest(current_root)
    diff = manifest_diff(input_manifest, file_manifest(candidate))
    directories = directory_diff(current_root, candidate)
    validation_summary = pack_validation_summary(validators)
    receipt_payload = {
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "artifact_schema_registry_version": registry.registry_version,
        "repository_register_artifact_schema_version": scalar_value(
            (candidate / ".work" / "repository-register.md").read_text(encoding="utf-8"),
            "artifact_schema_version",
        ),
        **validation_summary,
        "transaction_id": transaction["transaction_id"],
        "stage": stage,
        "stage_result": "skipped" if skipped else "committed",
        "skip_reason": skip_reason if skipped else None,
        "repository": str(repo),
        "source_commit": commit,
        "generation_id": generation_id,
        "promotion_scope": "generation",
        "formal_pack_published": False,
        "started_at": transaction.get("created_at"),
        "completed_at": now_utc(),
        "checkpoint_summary": checkpoint_summary(checkpoints),
        "checkpoint_ledger_sha256": checkpoint_ledger_sha256(checkpoint_path(tx_dir)),
        "baseline_manifest": manifest_summary(read_json(tx_dir / "baseline-manifest.json")),
        "candidate_manifest": manifest_summary(file_manifest(candidate)),
        "input_manifest": manifest_summary(input_manifest),
        "output_manifest": manifest_summary(file_manifest(candidate)),
        "changes": diff,
        "directory_changes": directories,
        "archive": None,
        "archive_summary": None,
        "validators": validators,
        "result": "committed",
    }
    candidate_receipt = write_receipt(candidate, sequence, stage, receipt_payload)
    write_artifact_manifest(
        candidate,
        registry,
        str(repo),
        commit,
        stage,
        transaction["transaction_id"],
        invalidated,
    )
    candidate_errors = validate_artifact_manifest(candidate, registry)
    if candidate_errors:
        raise ExecutorError(
            "Generation Candidate manifest is invalid: " + " | ".join(candidate_errors)
        )

    previous = generation_dir(output, generation_id) / f"previous-{transaction['transaction_id']}"
    formal_receipt = execution_root(output) / "receipts" / candidate_receipt.name
    formal_pre_state = (tx_dir / "pre-state.yaml").read_text(encoding="utf-8")
    journal_path = tx_dir / "promotion-journal.json"
    journal = {
        "transaction_id": transaction["transaction_id"],
        "stage": stage,
        "phase": "generation-promoting",
        "generation_id": generation_id,
        "current_root": str(current_root),
        "previous_root": str(previous),
        "candidate": str(candidate),
        "formal_receipt": str(formal_receipt),
        "operations": [],
        "updated_at": now_utc(),
    }
    transaction["status"] = "generation-promoting"
    atomic_write_json(tx_dir / "transaction.json", transaction)
    atomic_write_json(journal_path, journal)
    try:
        os.replace(current_root, previous)
        journal["phase"] = "generation-old-moved"
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        os.replace(candidate, current_root)
        journal["phase"] = "generation-promoted"
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        update_generation_manifest(
            output, generation_id, stage, transaction["transaction_id"], current_root
        )
        formal_receipt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current_root / candidate_receipt.relative_to(candidate), formal_receipt)
        atomic_write_text(state_path(output), candidate_state)
        write_artifact_manifest(
            output,
            registry,
            str(repo),
            commit,
            stage,
            transaction["transaction_id"],
            invalidated,
        )
        manifest_errors = validate_artifact_manifest(output, registry)
        if manifest_errors:
            raise ExecutorError(
                "formal operational manifest is invalid after Generation commit: "
                + " | ".join(manifest_errors)
            )
        journal["phase"] = "generation-committed"
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        shutil.rmtree(previous)
        release_lock(output, transaction["transaction_id"])
        shutil.rmtree(tx_dir)
    except Exception:
        if candidate.exists():
            shutil.rmtree(candidate, ignore_errors=True)
        if current_root.exists():
            os.replace(current_root, candidate)
        if previous.exists():
            os.replace(previous, current_root)
        if formal_receipt.exists():
            formal_receipt.unlink()
        atomic_write_text(state_path(output), formal_pre_state)
        write_artifact_manifest(
            output,
            registry,
            str(repo),
            commit,
            previous_stage(stage) or "init",
            None,
            invalidated,
        )
        transaction["status"] = "failed"
        atomic_write_json(tx_dir / "transaction.json", transaction)
        journal["phase"] = "rolled-back-generation"
        journal["updated_at"] = now_utc()
        atomic_write_json(journal_path, journal)
        raise

    emit(
        {
            "result": "skipped" if skipped else "committed",
            "stage": stage,
            "transaction_id": transaction["transaction_id"],
            "generation_id": generation_id,
            "promotion_scope": "generation",
            "formal_pack_published": False,
            "next_stage": scalar_value(candidate_state, "current_stage"),
            "receipt": str(formal_receipt),
        },
        as_json,
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
    baseline_manifest_path = tx_dir / "baseline-manifest.json"
    baseline_root = tx_dir / "baseline"
    if not baseline_manifest_path.is_file() or not baseline_root.is_dir():
        raise ExecutorError("transaction baseline is missing")
    expected_formal = read_json(baseline_manifest_path)
    if knowledge_manifest(output) != expected_formal:
        transaction["status"] = "failed"
        transaction["last_attempt_at"] = now_utc()
        try:
            drifted = restore_formal_drift(output, baseline_root, expected_formal)
        except Exception as exc:
            formal_text = set_scalar(formal_text, "stage_status", "failed")
            formal_text = set_scalar(formal_text, "formal_drift_status", "recovery-required")
            atomic_write_text(state_path(output), formal_text)
            transaction["errors"] = [f"FORMAL-DRIFT-RECOVERY-REQUIRED: {exc}"]
            atomic_write_json(tx_dir / "transaction.json", transaction)
            raise ExecutorError(f"formal artifact drift could not be restored: {exc}") from exc
        formal_text = set_scalar(formal_text, "stage_status", "failed")
        formal_text = set_scalar(formal_text, "formal_drift_status", "restored")
        atomic_write_text(state_path(output), formal_text)
        transaction["errors"] = ["FORMAL-DRIFT-RESTORED: " + ", ".join(drifted)]
        atomic_write_json(tx_dir / "transaction.json", transaction)
        emit(
            {
                "result": "failed",
                "stage": stage,
                "transaction_id": args.transaction,
                "errors": transaction["errors"],
                "candidate": str(candidate),
                "formal_drift_status": "restored",
            },
            args.json,
        )
        return 1
    checkpoints = load_checkpoints(tx_dir, args.transaction, stage)
    if args.skip:
        stage_skip_allowed(stage, candidate, args.reason)
        checkpoints = skip_all_checkpoints(checkpoints, str(args.reason))
        atomic_write_json(checkpoint_path(tx_dir), checkpoints)
    incomplete_checkpoints = checkpoint_commit_gate(checkpoints)
    if incomplete_checkpoints:
        raise ExecutorError(
            f"stage {stage} has incomplete checkpoints: " + ", ".join(incomplete_checkpoints)
        )
    candidate_state_path = candidate / STATE_FILE
    candidate_state = candidate_state_path.read_text(encoding="utf-8")
    candidate_state = candidate_state_for_commit(
        candidate_state,
        stage,
        args.semantic_result,
        args.skip,
    )
    candidate_state = set_scalar(candidate_state, "formal_drift_status", "clean")
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

    if stage in GENERATION_STAGES and stage != "finalization":
        return commit_generation_stage(
            output=output,
            tx_dir=tx_dir,
            transaction=transaction,
            candidate=candidate,
            candidate_state=candidate_state,
            stage=stage,
            repo=repo,
            commit=commit,
            registry=registry,
            invalidated=invalidated if isinstance(invalidated, list) else [],
            validators=validators,
            checkpoints=checkpoints,
            skipped=args.skip,
            skip_reason=args.reason,
            as_json=args.json,
        )

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
            "generation_id": transaction.get("generation_id"),
            "promotion_scope": "formal-pack",
            "formal_pack_published": stage == "finalization",
            "started_at": transaction.get("created_at"),
            "completed_at": now_utc(),
            "checkpoint_summary": checkpoint_summary(checkpoints),
            "checkpoint_ledger_sha256": checkpoint_ledger_sha256(checkpoint_path(tx_dir)),
            "baseline_manifest": manifest_summary(expected_formal),
            "candidate_manifest": manifest_summary(candidate_manifest),
            "input_manifest": manifest_summary(current_manifest),
            "output_manifest": manifest_summary(candidate_manifest),
            "changes": diff,
            "directory_changes": directories,
            "archive": str(archive) if archive else None,
            "archive_summary": archive_summary,
            "validators": validators + post_results,
            "result": "committed",
        }
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
        if stage == "finalization" and transaction.get("generation_id"):
            generation_manifest_path = generation_dir(
                output, str(transaction["generation_id"])
            ) / "generation-manifest.json"
            shutil.copy2(
                generation_manifest_path,
                tx_dir / "generation-manifest-before-finalization.json",
            )
            update_generation_manifest(
                output,
                str(transaction["generation_id"]),
                stage,
                args.transaction,
                generation_candidate_root(output, str(transaction["generation_id"])),
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
                "--allow-missing-final-receipt",
            ],
            output,
        )
        if state_check["exit_code"] != 0:
            raise ExecutorError("pre-receipt state validation failed")
        receipt_path = write_receipt(output, sequence, stage, receipt_payload)
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
                "post-receipt Artifact Manifest validation failed: "
                + " | ".join(manifest_errors)
            )
        final_state_check = run_validator(
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
        if final_state_check["exit_code"] != 0:
            raise ExecutorError("post-receipt state validation failed")
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
            generation_backup = tx_dir / "generation-manifest-before-finalization.json"
            generation_id = transaction.get("generation_id")
            if generation_id and generation_backup.is_file():
                shutil.copy2(
                    generation_backup,
                    generation_dir(output, str(generation_id)) / "generation-manifest.json",
                )
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
        "rolled-back-generation",
    }:
        raise ExecutorError("transaction has promotion work; run recover instead of abort")
    if not is_migration:
        pre_state = tx_dir / "pre-state.yaml"
        if pre_state.is_file():
            formal = pre_state.read_text(encoding="utf-8")
        else:
            formal = set_scalar(formal, "stage_status", "pending")
            formal = set_scalar(formal, "active_transaction", None)
            formal = set_scalar(formal, "current_checkpoint", None)
            formal = set_scalar(formal, "checkpoint_status", "pending")
        atomic_write_text(state_path(output), formal)
        if transaction.get("generation_created") and transaction.get("generation_id"):
            shutil.rmtree(
                generation_dir(output, str(transaction["generation_id"])),
                ignore_errors=True,
            )
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


def trusted_lifecycle_manifest_staleness(
    output: Path,
    state: str,
    stale_paths: Iterable[str],
) -> bool:
    """Allow only executor-owned State drift backed by one coherent transaction."""

    if set(stale_paths) != {STATE_FILE.as_posix()}:
        return False
    transaction_id = scalar_value(state, "active_transaction")
    if not transaction_id:
        return False
    try:
        lock = read_json(lock_path(output))
        transaction = read_json(
            transaction_dir(output, transaction_id) / "transaction.json"
        )
    except ExecutorError:
        return False
    stage = scalar_value(state, "current_stage")
    if lock.get("transaction_id") != transaction_id or lock.get("stage") != stage:
        return False
    if transaction.get("transaction_id") != transaction_id or transaction.get("stage") != stage:
        return False
    if transaction.get("repository") != scalar_value(state, "repository_path"):
        return False
    if transaction.get("source_commit") != scalar_value(state, "source_commit"):
        return False
    if transaction.get("status") not in {
        "in-progress",
        "failed",
        "generation-promoting",
    }:
        return False
    return True


def formal_manifest_diagnostics(
    output: Path,
    state: str,
    registry: Any,
) -> tuple[str, list[str], list[str]]:
    assessment = assess_artifact_manifest(output, registry)
    if assessment.status == "valid":
        return "valid", [], []
    if assessment.status == "invalid":
        return "invalid", [], list(assessment.errors)
    if trusted_lifecycle_manifest_staleness(
        output, state, assessment.stale_paths
    ):
        return "stale", list(assessment.stale_reasons), []
    return (
        "invalid",
        [],
        [
            "unexpected formal Artifact Manifest drift: " + reason
            for reason in assessment.stale_reasons
        ],
    )


def collect_stage_validation_report(
    output: Path,
    transaction_id: str,
) -> dict[str, Any]:
    tx_dir, transaction, candidate = load_transaction(output, transaction_id)
    stage = str(transaction.get("stage"))
    report = empty_stage_validation_report(stage, transaction_id)
    semantic: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    forward: list[dict[str, Any]] = []
    forward_total = 0
    semantic_suppressed_by_validators = 0
    warnings_suppressed_by_validators = 0
    validator_summaries: list[dict[str, Any]] = []

    formal = state_text(output)
    transaction_status = str(transaction.get("status"))
    if transaction_status not in VALIDATABLE_TRANSACTION_STATUSES:
        blocking.append(
            validation_item(
                "TRANSACTION-STATUS",
                f"transaction status {transaction_status} requires commit recovery or cleanup before validation",
                source="stage-executor",
            )
        )

    lock: dict[str, Any] = {}
    try:
        lock = read_json(lock_path(output))
    except ExecutorError as exc:
        blocking.append(
            validation_item("EXECUTION-LOCK", str(exc), source="stage-executor")
        )
    if lock.get("transaction_id") != transaction_id or lock.get("stage") != stage:
        blocking.append(
            validation_item(
                "EXECUTION-LOCK",
                "execution lock does not own the requested transaction and stage",
                source="stage-executor",
            )
        )
    if stage != MIGRATION_STAGE and scalar_value(formal, "active_transaction") != transaction_id:
        blocking.append(
            validation_item(
                "TRANSACTION-OWNERSHIP",
                "analysis state does not own the requested transaction",
                source="stage-executor",
            )
        )

    journal_path = tx_dir / "promotion-journal.json"
    try:
        journal = read_json(journal_path)
    except ExecutorError as exc:
        blocking.append(
            validation_item("PROMOTION-JOURNAL", str(exc), source="stage-executor")
        )
    else:
        phase = str(journal.get("phase"))
        if phase not in VALIDATABLE_JOURNAL_PHASES:
            blocking.append(
                validation_item(
                    "RECOVERY-REQUIRED",
                    f"promotion journal phase {phase} must be recovered before validation",
                    source="stage-executor",
                )
            )

    repo: Path | None = None
    commit = "unknown"
    try:
        repo, commit = verify_repo_and_commit(formal)
    except ExecutorError as exc:
        blocking.append(
            validation_item("REPOSITORY-COMMIT", str(exc), source="stage-executor")
        )
    else:
        if transaction.get("repository") != str(repo):
            blocking.append(
                validation_item(
                    "REPOSITORY-COMMIT",
                    "transaction repository does not match analysis state",
                    source="stage-executor",
                )
            )
        if transaction.get("source_commit") != commit:
            blocking.append(
                validation_item(
                    "REPOSITORY-COMMIT",
                    "transaction source commit does not match the current repository",
                    source="stage-executor",
                )
            )

    try:
        registry = load_registry()
    except ArtifactSchemaError as exc:
        registry = None
        blocking.append(
            validation_item(
                "ARTIFACT-REGISTRY", str(exc), source="stage-executor"
            )
        )
    else:
        # A migration transaction intentionally starts from artifacts whose
        # versions may be incompatible with the current registry. Its trusted
        # source boundary is the sealed Migration Plan snapshot, not a current-
        # schema formal Manifest. The migration-specific validation below
        # verifies that snapshot and the sealed mechanical output instead.
        if stage != MIGRATION_STAGE:
            try:
                formal_status, _formal_stale, formal_errors = formal_manifest_diagnostics(
                    output, formal, registry
                )
            except (ArtifactSchemaError, ExecutorError) as exc:
                blocking.append(
                    validation_item(
                        "FORMAL-MANIFEST", str(exc), source="stage-executor"
                    )
                )
            else:
                if formal_status == "invalid":
                    blocking.extend(
                        validation_item(
                            "FORMAL-MANIFEST", message, source="stage-executor"
                        )
                        for message in formal_errors
                    )

        if candidate.is_dir():
            try:
                assessment = assess_artifact_manifest(candidate, registry)
            except ArtifactSchemaError as exc:
                blocking.append(
                    validation_item(
                        "CANDIDATE-MANIFEST", str(exc), source="stage-executor"
                    )
                )
            else:
                if assessment.status == "invalid":
                    blocking.extend(
                        validation_item(
                            "CANDIDATE-MANIFEST", message, source="stage-executor"
                        )
                        for message in assessment.errors
                    )
                elif assessment.status == "stale":
                    if stage == MIGRATION_STAGE:
                        blocking.extend(
                            validation_item(
                                "SEALED-MIGRATION-DRIFT",
                                message,
                                source="stage-executor",
                            )
                            for message in assessment.stale_reasons
                        )
                    else:
                        report["expected_candidate_manifest_drift"] = {
                            "status": "pending-refresh",
                            "refresh_on_commit": True,
                            "reasons": list(assessment.stale_reasons)[:VALIDATION_DETAIL_LIMIT],
                        }
        else:
            blocking.append(
                validation_item(
                    "CANDIDATE-MISSING",
                    "transaction Candidate is unavailable; run recover before validation",
                    source="stage-executor",
                )
            )

    if stage != MIGRATION_STAGE:
        baseline_manifest_path = tx_dir / "baseline-manifest.json"
        try:
            expected_formal = read_json(baseline_manifest_path)
        except ExecutorError as exc:
            blocking.append(
                validation_item("FORMAL-BASELINE", str(exc), source="stage-executor")
            )
        else:
            current_formal = knowledge_manifest(output)
            if current_formal != expected_formal:
                drift = manifest_diff(expected_formal, current_formal)
                changed = sorted(
                    set(drift["added"] + drift["changed"] + drift["deleted"])
                )
                blocking.append(
                    validation_item(
                        "FORMAL-DRIFT",
                        "formal knowledge artifacts changed outside the transaction: "
                        + ", ".join(changed[:VALIDATION_PER_CODE_LIMIT]),
                        source="stage-executor",
                    )
                )

    try:
        checkpoints = load_checkpoints(tx_dir, transaction_id, stage)
    except ExecutorError as exc:
        blocking.append(
            validation_item("CHECKPOINT-LEDGER", str(exc), source="stage-executor")
        )
    else:
        incomplete = checkpoint_commit_gate(checkpoints)
        if incomplete:
            blocking.append(
                validation_item(
                    "CHECKPOINT-INCOMPLETE",
                    "stage has incomplete checkpoints: " + ", ".join(incomplete),
                    source="stage-executor",
                )
            )

    infrastructure_blocked = any(
        item["code"]
        in {
            "CANDIDATE-MISSING",
            "EXECUTION-LOCK",
            "RECOVERY-REQUIRED",
            "REPOSITORY-COMMIT",
            "TRANSACTION-OWNERSHIP",
        }
        for item in blocking
    )
    if stage == MIGRATION_STAGE:
        if not infrastructure_blocked and registry is not None and repo is not None:
            try:
                formal_plan_path = output / ".work" / "migration-plan.yaml"
                plan = load_migration_plan(formal_plan_path, registry)
                if transaction.get("plan_id") != plan.get("plan_id"):
                    raise ExecutorError("transaction and Migration Plan IDs do not match")
                _load_sealed_mechanical_output(tx_dir, transaction, candidate)
                migration_errors, _diff = _validate_migration_candidate(
                    output,
                    candidate,
                    plan,
                    registry,
                    repo,
                    commit,
                    transaction_id,
                )
                blocking.extend(
                    validation_item(
                        "MIGRATION-VALIDATION", message, source="stage-executor"
                    )
                    for message in migration_errors
                )
            except (ArtifactSchemaError, ExecutorError) as exc:
                blocking.append(
                    validation_item(
                        "MIGRATION-VALIDATION", str(exc), source="stage-executor"
                    )
                )
    elif not infrastructure_blocked and repo is not None:
        projected_state, projection_errors = projected_validation_state(stage, candidate)
        semantic.extend(projection_errors)
        with tempfile.TemporaryDirectory(prefix="eapi-stage-validation-") as temporary:
            temporary_state = Path(temporary) / ".work" / "analysis-state.yaml"
            temporary_state.parent.mkdir(parents=True)
            temporary_state.write_text(projected_state, encoding="utf-8")
            gate_errors, validator_results = stage_gates(
                stage,
                candidate,
                repo,
                diagnostic_manifest=True,
                analysis_state_override=temporary_state,
            )
        for error in gate_errors:
            if error.startswith("validator failed:"):
                continue
            if error.startswith("Artifact Schema:"):
                blocking.append(
                    validation_item(
                        "CANDIDATE-MANIFEST",
                        error.removeprefix("Artifact Schema:").strip(),
                        source="stage-executor",
                    )
                )
            else:
                semantic.append(
                    validation_item("STAGE-GATE", error, source="stage-executor")
                )
        for result in validator_results:
            (
                validator_semantic,
                validator_blocking,
                validator_warnings,
                validator_forward,
                validator_forward_total,
                validator_semantic_total,
                validator_warning_total,
            ) = parse_validator_diagnostics(result)
            semantic.extend(validator_semantic)
            blocking.extend(validator_blocking)
            warnings.extend(validator_warnings)
            forward.extend(validator_forward)
            forward_total += validator_forward_total
            semantic_suppressed_by_validators += max(
                0, validator_semantic_total - len(validator_semantic)
            )
            warnings_suppressed_by_validators += max(
                0, validator_warning_total - len(validator_warnings)
            )
            validator_summaries.append(
                {
                    "validator": validator_name(result),
                    "result": "ok" if result.get("exit_code") == 0 else "failed",
                    "error_count": validator_semantic_total + len(validator_blocking),
                    "warning_count": validator_warning_total,
                    "forward_reference_count": validator_forward_total,
                }
            )

        if stage in {"api-contract-publication", "ba-publication"}:
            try:
                stage_skip_allowed(stage, candidate, "stage validation")
            except ExecutorError:
                pass
            else:
                warnings.append(
                    validation_item(
                        "STAGE-SKIP-AVAILABLE",
                        "this stage has no publication intent and should be committed with --skip and an explicit reason",
                        source="stage-executor",
                    )
                )

    report["semantic_or_document_errors"] = compact_validation_section(
        semantic,
        total_count=len(semantic) + semantic_suppressed_by_validators,
    )
    report["blocking_errors"] = compact_validation_section(blocking)
    report["warnings"] = compact_validation_section(
        warnings,
        total_count=len(warnings) + warnings_suppressed_by_validators,
    )
    report["cross_stage_forward_references"] = forward_reference_section(
        forward, forward_total
    )
    report["validator_summary"] = validator_summaries
    if report["semantic_or_document_errors"]["count"] or report["blocking_errors"]["count"]:
        report["result"] = "blocked"
    return report


def command_validate(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    report = collect_stage_validation_report(output, args.transaction)
    emit(report, args.json)
    return 0 if report["result"] == "ready" else 1


def status_payload(output: Path) -> dict[str, Any]:
    text = state_text(output)
    payload: dict[str, Any] = {
        "workflow_schema_version": scalar_value(text, "workflow_schema_version") or "legacy",
        "repository": scalar_value(text, "repository"),
        "repository_path": scalar_value(text, "repository_path"),
        "source_commit": scalar_value(text, "source_commit"),
        "current_stage": scalar_value(text, "current_stage"),
        "stage_status": scalar_value(text, "stage_status"),
        "current_checkpoint": scalar_value(text, "current_checkpoint"),
        "checkpoint_status": scalar_value(text, "checkpoint_status"),
        "active_transaction": scalar_value(text, "active_transaction"),
        "last_committed_stage": scalar_value(text, "last_committed_stage"),
        "synthesis_status": scalar_value(text, "synthesis_status"),
        "business_model_status": scalar_value(text, "business_model_status"),
        "publication_status": scalar_value(text, "publication_status"),
        "working_generation_id": scalar_value(text, "working_generation_id"),
        "working_generation_status": "none",
        "published_generation_id": scalar_value(text, "published_generation_id"),
        "published_source_commit": scalar_value(text, "published_source_commit"),
        "formal_drift_status": scalar_value(text, "formal_drift_status") or "unknown",
        "release_readiness": "not-ready",
        "migration_status": scalar_value(text, "migration_status") or "unknown",
        "migration_plan": None,
        "artifact_manifest_status": "unknown",
        "artifact_manifest_stale_reasons": [],
        "artifact_manifest_errors": [],
        "candidate_artifact_manifest_status": "not-applicable",
        "candidate_artifact_manifest_stale_reasons": [],
        "candidate_artifact_manifest_errors": [],
        "manifest_refresh_pending": "none",
        "behavior_counts": {},
        "formal_manifest": manifest_summary(file_manifest(output)),
        "receipt_count": receipt_count(output),
        "lock": None,
        "transaction": None,
        "candidate_diff": None,
        "candidate_directory_diff": None,
        "checkpoint_summary": {},
        "checkpoints": [],
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
        manifest_status, stale_reasons, artifact_errors = formal_manifest_diagnostics(
            output, text, registry
        )
        payload["artifact_manifest_status"] = manifest_status
        payload["artifact_manifest_stale_reasons"] = stale_reasons
        payload["artifact_manifest_errors"] = artifact_errors
    except ArtifactSchemaError as exc:
        payload["artifact_manifest_status"] = "invalid"
        payload["artifact_manifest_errors"] = [str(exc)]

    working_generation_id = payload.get("working_generation_id")
    if working_generation_id:
        try:
            generation = load_generation_manifest(output, str(working_generation_id))
            payload["working_generation_status"] = generation.get("status", "unknown")
            payload["working_generation_manifest"] = generation
            if generation.get("status") == "published":
                published_manifest = generation.get("published_knowledge_manifest")
                if not isinstance(published_manifest, dict):
                    payload["integrity_errors"].append(
                        "Published Generation has no knowledge manifest"
                    )
                elif published_manifest != knowledge_manifest(output):
                    payload["integrity_errors"].append(
                        "Published Generation does not match the formal knowledge Pack"
                    )
                elif payload.get("published_generation_id") != working_generation_id:
                    payload["integrity_errors"].append(
                        "published_generation_id does not match working_generation_id"
                    )
                elif generation.get("published_source_commit") != payload.get("published_source_commit"):
                    payload["integrity_errors"].append(
                        "Published Generation source commit does not match analysis state"
                    )
                elif payload["artifact_manifest_status"] == "valid":
                    payload["release_readiness"] = "ready"
        except ExecutorError as exc:
            payload["working_generation_status"] = "invalid"
            payload["integrity_errors"].append(f"Working Generation invalid: {exc}")

    active = payload["active_transaction"]
    if not active and isinstance(payload["lock"], dict) and payload["lock"].get("stage") == MIGRATION_STAGE:
        active = payload["lock"].get("transaction_id")
    if active:
        try:
            tx_dir, transaction, candidate = load_transaction(output, str(active))
            payload["transaction"] = transaction
            payload["candidate_manifest"] = manifest_summary(file_manifest(candidate))
            try:
                candidate_assessment = assess_artifact_manifest(
                    candidate, load_registry()
                )
            except ArtifactSchemaError as exc:
                payload["candidate_artifact_manifest_status"] = "invalid"
                payload["candidate_artifact_manifest_errors"] = [str(exc)]
            else:
                payload["candidate_artifact_manifest_status"] = (
                    candidate_assessment.status
                )
                if candidate_assessment.status == "stale":
                    payload["candidate_artifact_manifest_stale_reasons"] = list(
                        candidate_assessment.stale_reasons
                    )
                elif candidate_assessment.status == "invalid":
                    payload["candidate_artifact_manifest_errors"] = list(
                        candidate_assessment.errors
                    )
            comparison_root = output
            transaction_generation = transaction.get("generation_id")
            if transaction_generation:
                candidate_root = generation_candidate_root(output, str(transaction_generation))
                if candidate_root.is_dir():
                    comparison_root = candidate_root
            payload["candidate_diff"] = manifest_diff(file_manifest(comparison_root), file_manifest(candidate))
            payload["candidate_directory_diff"] = directory_diff(comparison_root, candidate)
            stage = str(transaction.get("stage"))
            try:
                ledger = load_checkpoints(tx_dir, str(active), stage)
                payload["checkpoint_summary"] = checkpoint_summary(ledger)
                payload["checkpoints"] = ledger.get("checkpoints", [])
            except ExecutorError as exc:
                payload["integrity_errors"].append(f"Checkpoint ledger invalid: {exc}")
            if stage == MIGRATION_STAGE:
                try:
                    mechanical = _load_sealed_mechanical_output(
                        tx_dir, transaction, candidate
                    )
                except ExecutorError as exc:
                    payload["integrity_errors"].append(str(exc))
                    payload["requirements"] = [
                        "restore or abort the invalid sealed Migration transaction"
                    ]
                else:
                    payload["mechanical_output_manifest"] = {
                        "path": str(tx_dir / "mechanical-output-manifest.json"),
                        "sha256": transaction.get(
                            "mechanical_output_manifest_sha256"
                        ),
                        "transform_count": len(
                            mechanical.get("transform_reports", [])
                        ),
                        "candidate_sealed": True,
                    }
                    payload["requirements"] = [
                        "inspect the Migration Plan and Mechanical Output Manifest, then commit without editing Candidate"
                    ]
            else:
                try:
                    repo, _commit = verify_repo_and_commit(text)
                    requirements, status_validators = stage_gates(
                        stage,
                        candidate,
                        repo,
                        diagnostic_manifest=True,
                    )
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
    pending_scopes: list[str] = []
    if payload["artifact_manifest_status"] == "stale":
        pending_scopes.append("formal")
    if payload["candidate_artifact_manifest_status"] == "stale":
        pending_scopes.append("candidate")
    payload["manifest_refresh_pending"] = (
        "both" if len(pending_scopes) == 2 else pending_scopes[0] if pending_scopes else "none"
    )
    if payload["artifact_manifest_status"] != "valid" or payload["integrity_errors"]:
        payload["release_readiness"] = "not-ready"
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

    if scalar_value(text, "active_transaction") or lock_path(output).exists():
        raise ExecutorError(
            "resume cannot run while an execution transaction is active; use "
            "status, commit, abort, or recover instead"
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


def rollback_generation_transaction(
    output: Path,
    tx_dir: Path,
    transaction: dict[str, Any],
    journal: dict[str, Any],
    state_text_value: str,
) -> None:
    candidate = tx_dir / "candidate"
    current_root = Path(str(journal.get("current_root", "")))
    previous = Path(str(journal.get("previous_root", "")))
    if current_root.is_dir() and not candidate.exists():
        os.replace(current_root, candidate)
    if previous.is_dir():
        if current_root.exists():
            shutil.rmtree(current_root)
        os.replace(previous, current_root)
    formal_receipt_value = journal.get("formal_receipt")
    if formal_receipt_value:
        formal_receipt = Path(str(formal_receipt_value))
        if formal_receipt.is_file():
            formal_receipt.unlink()
    pre_state = tx_dir / "pre-state.yaml"
    recovered = pre_state.read_text(encoding="utf-8") if pre_state.is_file() else state_text_value
    recovered = set_scalar(recovered, "stage_status", "failed")
    recovered = set_scalar(recovered, "active_transaction", str(transaction["transaction_id"]))
    current_checkpoint = STAGE_CHECKPOINTS[str(transaction["stage"])][-1]
    recovered = set_scalar(recovered, "current_checkpoint", current_checkpoint)
    recovered = set_scalar(recovered, "checkpoint_status", "failed")
    atomic_write_text(state_path(output), recovered)
    transaction["status"] = "failed"
    atomic_write_json(tx_dir / "transaction.json", transaction)
    journal["phase"] = "rolled-back-generation"
    journal["updated_at"] = now_utc()
    atomic_write_json(tx_dir / "promotion-journal.json", journal)


def restore_finalization_generation_manifest(
    output: Path, tx_dir: Path, transaction: dict[str, Any]
) -> None:
    generation_id = transaction.get("generation_id")
    backup = tx_dir / "generation-manifest-before-finalization.json"
    if not generation_id or not backup.is_file():
        return
    destination = generation_dir(output, str(generation_id)) / "generation-manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, destination)


def repair_operational_manifest_after_receipt(
    output: Path, transaction: dict[str, Any]
) -> None:
    registry = load_registry()
    repo = Path(str(transaction.get("repository", ""))).expanduser().resolve()
    commit = str(transaction.get("source_commit") or "unknown")
    invalidated: list[dict[str, Any]] = []
    manifest_path = output / ".work" / "artifact-manifest.json"
    if manifest_path.is_file():
        observed = read_json(manifest_path).get("invalidated_artifacts", [])
        if isinstance(observed, list):
            invalidated = [item for item in observed if isinstance(item, dict)]
    write_artifact_manifest(
        output,
        registry,
        str(repo),
        commit,
        str(transaction.get("stage")),
        str(transaction.get("transaction_id")),
        invalidated,
    )
    errors = validate_artifact_manifest(output, registry)
    if errors:
        raise ExecutorError(
            "cannot recover the operational Artifact Manifest: " + " | ".join(errors)
        )


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
            if receipt is not None and tx_dir.is_dir():
                orphan_transaction = read_json(tx_dir / "transaction.json")
                orphan_journal = read_json(tx_dir / "promotion-journal.json")
                if orphan_journal.get("phase") in {
                    "generation-promoting",
                    "generation-old-moved",
                    "generation-promoted",
                }:
                    rollback_generation_transaction(
                        output, tx_dir, orphan_transaction, orphan_journal, text
                    )
                    emit(
                        {
                            "result": "rolled-back-orphan-generation",
                            "transaction_id": transaction_id,
                        },
                        args.json,
                    )
                    return 0
            if receipt is not None:
                recovery_record = (
                    orphan_transaction
                    if tx_dir.is_dir()
                    else read_json(receipt)
                )
                repair_operational_manifest_after_receipt(output, recovery_record)
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
                if journal.get("phase") in {
                    "generation-promoting",
                    "generation-old-moved",
                    "generation-promoted",
                }:
                    rollback_generation_transaction(output, tx_dir, transaction, journal, text)
                    emit(
                        {
                            "result": "rolled-back-orphan-generation",
                            "transaction_id": transaction_id,
                            "instruction": "inspect the restored Candidate, then commit again or abort",
                        },
                        args.json,
                    )
                    return 0
                archive_value = journal.get("archive")
                archive = Path(archive_value) if archive_value else None
                rollback_promotion(
                    output,
                    archive,
                    {"operations": journal.get("completed_operations", [])},
                )
                restore_finalization_generation_manifest(output, tx_dir, transaction)
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
    if phase in {"generation-promoting", "generation-old-moved", "generation-promoted"}:
        rollback_generation_transaction(output, tx_dir, transaction, journal, text)
        emit(
            {
                "result": "rolled-back-generation",
                "transaction_id": active,
                "stage": transaction.get("stage"),
                "instruction": "inspect the restored Candidate, then commit again or abort",
            },
            args.json,
        )
        return 0
    if phase == "generation-committed" and receipt is not None:
        release_lock(output, active)
        shutil.rmtree(tx_dir)
        emit(
            {
                "result": "cleaned-committed-generation",
                "transaction_id": active,
                "receipt": str(receipt),
            },
            args.json,
        )
        return 0
    if receipt is not None:
        candidate_state = (candidate / STATE_FILE).read_text(encoding="utf-8")
        atomic_write_text(state_path(output), candidate_state)
        repair_operational_manifest_after_receipt(output, transaction)
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
        "rolled-back-generation",
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
    restore_finalization_generation_manifest(output, tx_dir, transaction)
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

    validate = subparsers.add_parser("validate")
    validate.add_argument("--output", type=Path, required=True)
    validate.add_argument("--transaction", required=True)
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(handler=command_validate)

    scaffold = subparsers.add_parser("scaffold")
    scaffold.add_argument("--output", type=Path, required=True)
    scaffold.add_argument("--transaction", required=True)
    scaffold.add_argument("--artifact-type", required=True)
    scaffold.add_argument("--identity", action="append", default=[])
    scaffold.add_argument("--json", action="store_true")
    scaffold.set_defaults(handler=command_scaffold)

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

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--output", type=Path, required=True)
    checkpoint.add_argument("--transaction", required=True)
    checkpoint.add_argument("--checkpoint", required=True)
    checkpoint.add_argument(
        "--status",
        choices=sorted(ALLOWED_CHECKPOINT_STATUS - {"pending"}),
        required=True,
    )
    checkpoint.add_argument("--reason")
    checkpoint.add_argument("--json", action="store_true")
    checkpoint.set_defaults(handler=command_checkpoint)

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
        if args.command == "validate" and getattr(args, "json", False):
            report = empty_stage_validation_report(
                None, str(getattr(args, "transaction", ""))
            )
            report["result"] = "error"
            report["blocking_errors"] = compact_validation_section(
                [
                    validation_item(
                        "VALIDATION-COMMAND",
                        str(exc),
                        source="stage-executor",
                    )
                ]
            )
            emit(report, True)
            return 2
        if args.command == "scaffold" and getattr(args, "json", False):
            emit(
                {
                    "result": "error",
                    "transaction_id": str(getattr(args, "transaction", "")),
                    "artifact_type": str(getattr(args, "artifact_type", "")),
                    "error": str(exc),
                },
                True,
            )
            return 2
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        if args.command == "validate" and getattr(args, "json", False):
            report = empty_stage_validation_report(
                None, str(getattr(args, "transaction", ""))
            )
            report["result"] = "error"
            report["blocking_errors"] = compact_validation_section(
                [
                    validation_item(
                        "VALIDATION-FILESYSTEM",
                        str(exc),
                        source="stage-executor",
                    )
                ]
            )
            emit(report, True)
            return 2
        if args.command == "scaffold" and getattr(args, "json", False):
            emit(
                {
                    "result": "error",
                    "transaction_id": str(getattr(args, "transaction", "")),
                    "artifact_type": str(getattr(args, "artifact_type", "")),
                    "error": f"filesystem operation failed: {exc}",
                },
                True,
            )
            return 2
        print(f"ERROR: filesystem operation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
