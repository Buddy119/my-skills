#!/usr/bin/env python3
"""Versioned artifact registry, manifest, and migration-plan mechanics.

The module deliberately validates file identity and lifecycle metadata only.  It does
not infer document generations from prose, headings, or framework-specific content.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "assets" / "artifact-schema.json"
CURRENT_WORKFLOW_SCHEMA_VERSION = "3"
FORMAL_PREFIXES = (".work/", "tech-pack/", "ba-pack/")
SNAPSHOT_EXCLUDES = (
    ".work/execution/",
    ".work/migration-plan.yaml",
    ".work/legacy-artifacts/",
    ".work/legacy-ba-pack/",
)
DISCOVERY_EXCLUDES = (
    ".work/execution/active.lock",
    ".work/execution/transactions/",
    ".work/execution/archive/",
    ".work/legacy-artifacts/",
    ".work/legacy-ba-pack/",
)
MIGRATION_ACTIONS = {
    "preserve",
    "mechanical-migrate",
    "review-and-adopt",
    "archive-and-rebuild",
    "block",
}
NORMAL_STAGES = (
    "inventory",
    "tracing",
    "synthesis",
    "tech-publication",
    "api-contract-publication",
    "business-model",
    "ba-publication",
    "finalization",
)
STAGE_INDEX = {stage: index for index, stage in enumerate(NORMAL_STAGES)}


class ArtifactSchemaError(RuntimeError):
    """The artifact registry, manifest, or migration plan is invalid."""


@dataclass(frozen=True)
class ArtifactDefinition:
    artifact_type: str
    current_version: str
    paths: tuple[str, ...]
    template: str | None
    producing_stage: str
    rebuild_stage: str
    unknown_action: str
    dependencies: tuple[str, ...]
    migrations: dict[str, dict[str, str]]


@dataclass(frozen=True)
class ArtifactRegistry:
    registry_version: str
    manifest_version: str
    migration_plan_version: str
    definitions: dict[str, ArtifactDefinition]

    def match(self, relative: str) -> ArtifactDefinition | None:
        matches = [
            definition
            for definition in self.definitions.values()
            if any(fnmatch.fnmatchcase(relative, pattern) for pattern in definition.paths)
        ]
        if len(matches) > 1:
            names = ", ".join(sorted(item.artifact_type for item in matches))
            raise ArtifactSchemaError(f"artifact path matches multiple types: {relative} -> {names}")
        return matches[0] if matches else None


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactSchemaError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactSchemaError(f"JSON object expected: {path}")
    return payload


def load_registry(path: Path = DEFAULT_REGISTRY_PATH) -> ArtifactRegistry:
    payload = _load_json_object(path)
    registry_version = payload.get("artifact_schema_registry_version")
    manifest_version = payload.get("manifest_schema_version")
    plan_version = payload.get("migration_plan_schema_version")
    if not all(isinstance(item, str) and item for item in (registry_version, manifest_version, plan_version)):
        raise ArtifactSchemaError("artifact registry versions must be non-empty strings")
    raw_definitions = payload.get("artifact_types")
    if not isinstance(raw_definitions, dict) or not raw_definitions:
        raise ArtifactSchemaError("artifact registry must define artifact_types")

    definitions: dict[str, ArtifactDefinition] = {}
    register_schema_path = path.parent / "register-schema.json"
    for artifact_type, raw in raw_definitions.items():
        if not isinstance(artifact_type, str) or not isinstance(raw, dict):
            raise ArtifactSchemaError("each artifact type must be a named object")
        version = raw.get("current_version")
        schema_ref = raw.get("schema_ref")
        if schema_ref is not None:
            if schema_ref != "register-schema.json":
                raise ArtifactSchemaError(
                    f"unsupported schema_ref for {artifact_type}: {schema_ref}"
                )
            version = _load_json_object(register_schema_path).get("register_schema_version")
        paths = raw.get("paths")
        template = raw.get("template")
        producing_stage = raw.get("producing_stage")
        rebuild_stage = raw.get("rebuild_stage")
        unknown_action = raw.get("unknown_action")
        dependencies = raw.get("dependencies", [])
        migrations = raw.get("migrations", {})
        if not isinstance(version, str) or not version:
            raise ArtifactSchemaError(f"artifact type {artifact_type} has no current version")
        if not isinstance(paths, list) or not paths or not all(isinstance(item, str) for item in paths):
            raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid paths")
        if template is not None and not isinstance(template, str):
            raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid template")
        if not isinstance(producing_stage, str) or not producing_stage:
            raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid producing_stage")
        if rebuild_stage not in set(NORMAL_STAGES) | {"migration"}:
            raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid rebuild_stage")
        if unknown_action not in MIGRATION_ACTIONS:
            raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid unknown_action")
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid dependencies")
        if not isinstance(migrations, dict):
            raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid migrations")
        normalized_migrations: dict[str, dict[str, str]] = {}
        for source, migration in migrations.items():
            if not isinstance(source, str) or not isinstance(migration, dict):
                raise ArtifactSchemaError(f"artifact type {artifact_type} has invalid migration")
            target = migration.get("to")
            action = migration.get("action")
            if not isinstance(target, str) or action not in MIGRATION_ACTIONS:
                raise ArtifactSchemaError(
                    f"artifact type {artifact_type} has invalid migration from {source}"
                )
            normalized_migrations[source] = {"to": target, "action": action}
        definitions[artifact_type] = ArtifactDefinition(
            artifact_type=artifact_type,
            current_version=version,
            paths=tuple(paths),
            template=template,
            producing_stage=producing_stage,
            rebuild_stage=rebuild_stage,
            unknown_action=unknown_action,
            dependencies=tuple(dependencies),
            migrations=normalized_migrations,
        )

    for definition in definitions.values():
        missing = sorted(set(definition.dependencies) - set(definitions))
        if missing:
            raise ArtifactSchemaError(
                f"artifact type {definition.artifact_type} has unknown dependencies: "
                + ", ".join(missing)
            )
    registry = ArtifactRegistry(registry_version, manifest_version, plan_version, definitions)
    _validate_path_patterns(registry)
    return registry


def _validate_path_patterns(registry: ArtifactRegistry) -> None:
    examples: list[tuple[str, str]] = []
    for definition in registry.definitions.values():
        for pattern in definition.paths:
            example = pattern.replace("*", "example")
            examples.append((definition.artifact_type, example))
    for expected, example in examples:
        matched = registry.match(example)
        if matched is None or matched.artifact_type != expected:
            raise ArtifactSchemaError(
                f"artifact path pattern is ambiguous or unreachable: {expected} -> {example}"
            )


def scalar_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n#]+?)[\"']?\s*$", text, re.M)
    return match.group(1).strip() if match else None


def artifact_metadata(path: Path) -> tuple[str | None, str | None]:
    try:
        if path.suffix.lower() == ".json":
            payload = _load_json_object(path)
            return _string(payload.get("artifact_type")), _string(payload.get("artifact_schema_version"))
        text = path.read_text(encoding="utf-8")
    except (OSError, ArtifactSchemaError):
        return None, None
    if text.lstrip().startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None, None
        if isinstance(payload, dict):
            return _string(payload.get("artifact_type")), _string(
                payload.get("artifact_schema_version")
            )
    if path.suffix.lower() == ".md":
        if not text.startswith("---\n"):
            return None, None
        end = text.find("\n---\n", 4)
        if end == -1:
            return None, None
        text = text[4:end]
    return scalar_value(text, "artifact_type"), scalar_value(text, "artifact_schema_version")


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def add_artifact_metadata(path: Path, artifact_type: str, version: str) -> None:
    """Mechanically add or replace explicit artifact identity metadata."""
    if path.suffix.lower() == ".json":
        payload = _load_json_object(path)
        payload["artifact_type"] = artifact_type
        payload["artifact_schema_version"] = version
        atomic_write_json(path, payload)
        return
    text = path.read_text(encoding="utf-8")
    for key, value in (("artifact_type", artifact_type), ("artifact_schema_version", version)):
        replacement = f'{key}: "{value}"'
        if re.search(rf"^{re.escape(key)}:\s*.*$", text, re.M):
            text = re.sub(rf"^{re.escape(key)}:\s*.*$", replacement, text, count=1, flags=re.M)
        elif path.suffix.lower() == ".md" and text.startswith("---\n"):
            text = "---\n" + replacement + "\n" + text[4:]
        else:
            text = replacement + "\n" + text
    atomic_write_text(path, text)


def validate_template_contract(registry: ArtifactRegistry, assets_root: Path) -> list[str]:
    errors: list[str] = []
    for definition in registry.definitions.values():
        if not definition.template:
            continue
        template = assets_root / definition.template
        if not template.is_file():
            errors.append(f"artifact template is missing: {definition.template}")
            continue
        observed_type, observed_version = artifact_metadata(template)
        if observed_type != definition.artifact_type or observed_version != definition.current_version:
            errors.append(
                f"artifact template metadata mismatch: {definition.template}; "
                f"expected {definition.artifact_type}@{definition.current_version}, "
                f"observed {observed_type or '<missing>'}@{observed_version or '<missing>'}"
            )
    return errors


def _excluded(relative: str, prefixes: Iterable[str]) -> bool:
    return any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in prefixes)


def formal_files(root: Path, include_operational: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if not relative.startswith(FORMAL_PREFIXES):
            continue
        if _excluded(relative, DISCOVERY_EXCLUDES):
            continue
        if not include_operational and relative == ".work/artifact-manifest.json":
            continue
        files.append(path)
    return files


def source_snapshot(root: Path) -> tuple[list[dict[str, Any]], str]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if not relative.startswith(FORMAL_PREFIXES) or _excluded(relative, SNAPSHOT_EXCLUDES):
            continue
        entries.append(
            {"path": relative, "size": path.stat().st_size, "sha256": sha256_file(path)}
        )
    return entries, sha256_bytes(canonical_json(entries).encode("utf-8"))


def build_artifact_manifest(
    root: Path,
    registry: ArtifactRegistry,
    repository: str,
    source_commit: str,
    producing_stage: str,
    transaction_id: str | None,
    invalidated: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    for path in formal_files(root):
        relative = path.relative_to(root).as_posix()
        definition = registry.match(relative)
        if definition is None:
            continue
        observed_type, observed_version = artifact_metadata(path)
        artifacts.append(
            {
                "path": relative,
                "artifact_type": observed_type,
                "artifact_schema_version": observed_version,
                "expected_artifact_type": definition.artifact_type,
                "expected_artifact_schema_version": definition.current_version,
                "sha256": sha256_file(path),
                "producing_stage": definition.producing_stage,
                "last_committed_stage": producing_stage,
            }
        )
    return {
        "artifact_type": "artifact-manifest",
        "artifact_schema_version": registry.definitions["artifact-manifest"].current_version,
        "manifest_schema_version": registry.manifest_version,
        "artifact_schema_registry_version": registry.registry_version,
        "repository": repository,
        "source_commit": source_commit,
        "generated_at": now_utc(),
        "last_transaction": transaction_id,
        "artifacts": artifacts,
        "invalidated_artifacts": invalidated or [],
    }


def write_artifact_manifest(
    root: Path,
    registry: ArtifactRegistry,
    repository: str,
    source_commit: str,
    producing_stage: str,
    transaction_id: str | None,
    invalidated: list[dict[str, Any]] | None = None,
) -> Path:
    path = root / ".work" / "artifact-manifest.json"
    atomic_write_json(
        path,
        build_artifact_manifest(
            root,
            registry,
            repository,
            source_commit,
            producing_stage,
            transaction_id,
            invalidated,
        ),
    )
    return path


def validate_artifact_manifest(root: Path, registry: ArtifactRegistry) -> list[str]:
    path = root / ".work" / "artifact-manifest.json"
    if not path.is_file():
        return ["artifact manifest is missing"]
    try:
        manifest = _load_json_object(path)
    except ArtifactSchemaError as exc:
        return [str(exc)]
    errors: list[str] = []
    if manifest.get("artifact_type") != "artifact-manifest":
        errors.append("artifact manifest has the wrong artifact_type")
    if manifest.get("artifact_schema_version") != registry.definitions["artifact-manifest"].current_version:
        errors.append("artifact manifest has an unsupported artifact_schema_version")
    if manifest.get("manifest_schema_version") != registry.manifest_version:
        errors.append("artifact manifest has an unsupported manifest_schema_version")
    if manifest.get("artifact_schema_registry_version") != registry.registry_version:
        errors.append("artifact manifest registry version does not match the bundled registry")
    raw_entries = manifest.get("artifacts")
    if not isinstance(raw_entries, list):
        errors.append("artifact manifest artifacts must be a list")
        return errors
    declared: dict[str, dict[str, Any]] = {}
    for entry in raw_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            errors.append("artifact manifest contains an invalid artifact entry")
            continue
        relative = entry["path"]
        if relative in declared:
            errors.append(f"artifact manifest contains a duplicate path: {relative}")
            continue
        declared[relative] = entry

    actual_paths: set[str] = set()
    for artifact in formal_files(root):
        relative = artifact.relative_to(root).as_posix()
        definition = registry.match(relative)
        if definition is None:
            errors.append(f"formal artifact is not registered: {relative}")
            continue
        actual_paths.add(relative)
        observed_type, observed_version = artifact_metadata(artifact)
        if observed_type != definition.artifact_type or observed_version != definition.current_version:
            errors.append(
                f"artifact metadata mismatch: {relative}; expected "
                f"{definition.artifact_type}@{definition.current_version}, observed "
                f"{observed_type or '<missing>'}@{observed_version or '<missing>'}"
            )
        entry = declared.get(relative)
        if entry is None:
            errors.append(f"artifact is missing from manifest: {relative}")
            continue
        if entry.get("artifact_type") != observed_type or entry.get("artifact_schema_version") != observed_version:
            errors.append(f"artifact manifest metadata differs from file: {relative}")
        if entry.get("sha256") != sha256_file(artifact):
            errors.append(f"artifact manifest checksum differs from file: {relative}")
    for relative in sorted(set(declared) - actual_paths):
        errors.append(f"artifact manifest references a missing file: {relative}")
    return errors


def current_pack_is_versioned(root: Path, registry: ArtifactRegistry) -> bool:
    state = root / ".work" / "analysis-state.yaml"
    if not state.is_file() or scalar_value(state.read_text(encoding="utf-8"), "workflow_schema_version") != CURRENT_WORKFLOW_SCHEMA_VERSION:
        return False
    return not validate_artifact_manifest(root, registry)


def _action_for(
    definition: ArtifactDefinition,
    observed_type: str | None,
    observed_version: str | None,
) -> tuple[str, str, str | None]:
    if observed_type not in {None, definition.artifact_type}:
        return "block", "artifact_type conflicts with its registered path", None
    if observed_version == definition.current_version and observed_type == definition.artifact_type:
        return "preserve", "artifact already uses the current schema", definition.current_version
    if observed_version is None:
        return definition.unknown_action, "artifact has no explicit schema version", definition.current_version
    migration = definition.migrations.get(observed_version)
    if migration and migration.get("to") == definition.current_version:
        return migration["action"], f"registered migration {observed_version}->{definition.current_version}", definition.current_version
    return "block", f"no migration path from {observed_version} to {definition.current_version}", None


def _unregistered_step(relative: str) -> tuple[str, str, str]:
    if relative.startswith("ba-pack/"):
        return "archive-and-rebuild", "business-model", "unregistered BA artifact"
    if relative.startswith("tech-pack/"):
        return "archive-and-rebuild", "tech-publication", "unregistered Tech artifact"
    return "block", "inventory", "unregistered working artifact"


def _behavior_entries(text: str) -> list[dict[str, str | None]]:
    match = re.search(r"^behaviors:\s*\n(?P<body>(?:[ \t]+[^\n]*(?:\n|$))*)", text, re.M)
    if not match:
        return []
    entries: list[dict[str, str | None]] = []
    current: dict[str, str | None] | None = None
    for line in match.group("body").splitlines():
        start = re.match(r"^\s*-\s+behavior_id:\s*[\"']?([^\"'\n]+)[\"']?\s*$", line)
        if start:
            if current:
                entries.append(current)
            current = {"behavior_id": start.group(1).strip()}
            continue
        field = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_-]*):\s*[\"']?([^\"'\n]*)[\"']?\s*$", line)
        if current is not None and field:
            current[field.group(1)] = field.group(2).strip() or None
    if current:
        entries.append(current)
    return entries


def _reverse_dependencies(registry: ArtifactRegistry) -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = {name: set() for name in registry.definitions}
    for definition in registry.definitions.values():
        for dependency in definition.dependencies:
            reverse.setdefault(dependency, set()).add(definition.artifact_type)
    return reverse


def _dependency_closure(registry: ArtifactRegistry, seeds: set[str]) -> set[str]:
    reverse = _reverse_dependencies(registry)
    result = set(seeds)
    queue = list(seeds)
    while queue:
        current = queue.pop()
        for dependent in reverse.get(current, set()):
            if dependent not in result:
                result.add(dependent)
                queue.append(dependent)
    return result


def build_migration_plan(
    root: Path,
    registry: ArtifactRegistry,
    repository_path: Path,
    source_commit: str,
) -> dict[str, Any]:
    snapshot, snapshot_hash = source_snapshot(root)
    grouped: dict[tuple[str, str, str, str, str], list[str]] = {}
    changed_types: set[str] = set()
    direct_rebuild_stages: list[str] = []
    blocked_reasons: list[str] = []
    expected_archives: list[str] = []

    for path in formal_files(root):
        relative = path.relative_to(root).as_posix()
        if relative == ".work/migration-plan.yaml":
            # A previous plan is superseded by this Resume Audit. It is not an
            # input whose old status can choose the new migration path.
            continue
        definition = registry.match(relative)
        if definition is None:
            action, rebuilding_stage, reason = _unregistered_step(relative)
            if action != "block" and rebuilding_stage in STAGE_INDEX:
                direct_rebuild_stages.append(rebuilding_stage)
            key = ("unregistered", "unknown", "unknown", action, rebuilding_stage)
            grouped.setdefault(key, []).append(relative)
            if action == "block":
                blocked_reasons.append(f"{relative}: {reason}")
            else:
                expected_archives.append(relative)
            continue
        observed_type, observed_version = artifact_metadata(path)
        action, reason, target = _action_for(definition, observed_type, observed_version)
        if definition.artifact_type == "analysis-state":
            action = "mechanical-migrate"
            reason = "migration lifecycle fields and recovery stage are executor-owned"
        source = observed_version or "unknown"
        key = (
            definition.artifact_type,
            source,
            target or definition.current_version,
            action,
            definition.rebuild_stage,
        )
        grouped.setdefault(key, []).append(relative)
        if action in {"review-and-adopt", "archive-and-rebuild"}:
            changed_types.add(definition.artifact_type)
        if action == "archive-and-rebuild":
            expected_archives.append(relative)
        if action == "block":
            blocked_reasons.append(f"{relative}: {reason}")

    manifest_path = root / ".work" / "artifact-manifest.json"
    manifest_definition = registry.definitions["artifact-manifest"]
    if manifest_path.is_file():
        observed_type, observed_version = artifact_metadata(manifest_path)
        action, _reason, target = _action_for(
            manifest_definition, observed_type, observed_version
        )
        # The Manifest is a derived inventory of the post-migration pack and is
        # always rebuilt, even when its own envelope version is already current.
        action = "mechanical-migrate"
        grouped.setdefault(
            (
                manifest_definition.artifact_type,
                observed_version or "unknown",
                target or manifest_definition.current_version,
                action,
                manifest_definition.rebuild_stage,
            ),
            [],
        ).append(".work/artifact-manifest.json")
        if action == "block":
            blocked_reasons.append(
                ".work/artifact-manifest.json: no registered migration path"
            )
    else:
        grouped.setdefault(
            (
                manifest_definition.artifact_type,
                "missing",
                manifest_definition.current_version,
                "mechanical-migrate",
                manifest_definition.rebuild_stage,
            ),
            [],
        ).append(".work/artifact-manifest.json")

    invalidated = _dependency_closure(registry, changed_types)
    invalidated -= {
        "analysis-state",
        "evidence-index",
        "working-behavior-catalog",
        "behavior-dossier",
        "repository-register",
        "artifact-manifest",
        "migration-plan",
        "stage-receipt",
    }

    state_path = root / ".work" / "analysis-state.yaml"
    state_text = state_path.read_text(encoding="utf-8") if state_path.is_file() else ""
    if not (root / ".work" / "evidence-index.json").is_file():
        resume_stage = "inventory"
    else:
        entries = _behavior_entries(state_text)
        catalog_path = root / ".work" / "behavior-catalog.yaml"
        catalog_entries = (
            _behavior_entries(catalog_path.read_text(encoding="utf-8"))
            if catalog_path.is_file()
            else []
        )
        dossier_root = root / ".work" / "behavior-dossiers"
        state_by_id = {
            entry.get("behavior_id"): entry
            for entry in entries
            if entry.get("behavior_id")
        }
        required_ids = set(state_by_id)
        required_ids.update(
            str(entry.get("behavior_id"))
            for entry in catalog_entries
            if entry.get("behavior_id")
            and entry.get("status") not in {"duplicate", "excluded"}
        )

        def dossier_exists(behavior_id: str) -> bool:
            entry = state_by_id.get(behavior_id, {})
            declared = entry.get("dossier")
            candidates = [dossier_root / f"{behavior_id}.md"]
            if declared:
                declared_path = Path(str(declared))
                candidates.extend(
                    [
                        root / ".work" / declared_path,
                        dossier_root / declared_path.name,
                    ]
                )
            return any(path.is_file() for path in candidates)

        missing_dossier = any(not dossier_exists(behavior_id) for behavior_id in required_ids)
        incomplete_behavior = any(
            entry.get("status") not in {"understood", "blocked"} for entry in entries
        )
        if missing_dossier or incomplete_behavior:
            resume_stage = "tracing"
        elif any(
            action == "review-and-adopt"
            for (_artifact, _source, _target, action, _stage) in grouped
        ):
            resume_stage = "synthesis"
            invalidated |= _dependency_closure(registry, {"repository-synthesis"})
        else:
            stages = direct_rebuild_stages + [
                registry.definitions[item].rebuild_stage
                for item in invalidated
                if item in registry.definitions
                and registry.definitions[item].rebuild_stage in STAGE_INDEX
            ]
            resume_stage = min(stages, key=STAGE_INDEX.get) if stages else "finalization"

    steps: list[dict[str, Any]] = []
    for index, key in enumerate(
        sorted(grouped, key=lambda item: (STAGE_INDEX.get(item[4], -1), item[0], item[1], item[3])),
        1,
    ):
        artifact_type, source, target, action, rebuilding_stage = key
        effective_action = (
            "archive-and-rebuild"
            if artifact_type in invalidated and action == "preserve"
            else action
        )
        if effective_action == "archive-and-rebuild":
            expected_archives.extend(grouped[key])
        reason = (
            "artifact already uses the current schema"
            if effective_action == "preserve"
            else "a migrated upstream artifact invalidates this derived artifact"
            if action == "preserve" and effective_action == "archive-and-rebuild"
            else "explicit artifact version requires the registered migration action"
            if source not in {"unknown", "missing"}
            else "artifact version is missing or the current manifest must be created"
        )
        steps.append(
            {
                "step_id": f"MIG-{index:03d}",
                "artifact_type": artifact_type,
                "source_version": source,
                "target_version": target,
                "action": effective_action,
                "paths": sorted(grouped[key]),
                "reason": reason,
                "rebuilding_stage": rebuilding_stage,
            }
        )

    invalidated_records = [
        {
            "artifact_type": artifact_type,
            "reason": "upstream artifact migration invalidates the published or synthesized result",
            "rebuilding_stage": registry.definitions[artifact_type].rebuild_stage,
        }
        for artifact_type in sorted(
            invalidated,
            key=lambda item: (STAGE_INDEX.get(registry.definitions[item].rebuild_stage, 99), item),
        )
    ]
    status = "blocked" if blocked_reasons else "planned"
    plan: dict[str, Any] = {
        "artifact_type": "migration-plan",
        "artifact_schema_version": registry.definitions["migration-plan"].current_version,
        "migration_plan_schema_version": registry.migration_plan_version,
        "plan_id": "",
        "status": status,
        "repository": str(repository_path.resolve()),
        "source_commit": source_commit,
        "source_manifest_sha256": snapshot_hash,
        "source_snapshot": snapshot,
        "target": {
            "workflow_schema_version": CURRENT_WORKFLOW_SCHEMA_VERSION,
            "artifact_schema_registry_version": registry.registry_version,
        },
        "resume_stage_after_migration": resume_stage,
        "steps": steps,
        "invalidated_artifacts": invalidated_records,
        "expected_archives": sorted(set(expected_archives)),
        "blocked_reasons": blocked_reasons,
        "created_at": now_utc(),
    }
    plan["plan_id"] = migration_plan_id(plan)
    return plan


def migration_plan_id(plan: dict[str, Any]) -> str:
    identity = {
        key: value
        for key, value in plan.items()
        if key not in {"plan_id", "status", "created_at"}
    }
    return sha256_bytes(canonical_json(identity).encode("utf-8"))


def write_migration_plan(path: Path, plan: dict[str, Any]) -> None:
    # JSON is a strict YAML 1.2 subset and keeps the standard-library parser deterministic.
    atomic_write_json(path, plan)


def load_migration_plan(path: Path, registry: ArtifactRegistry) -> dict[str, Any]:
    plan = _load_json_object(path)
    if plan.get("artifact_type") != "migration-plan":
        raise ArtifactSchemaError("migration plan has the wrong artifact_type")
    if plan.get("artifact_schema_version") != registry.definitions["migration-plan"].current_version:
        raise ArtifactSchemaError("migration plan has an unsupported artifact_schema_version")
    if plan.get("migration_plan_schema_version") != registry.migration_plan_version:
        raise ArtifactSchemaError("migration plan has an unsupported migration_plan_schema_version")
    if plan.get("plan_id") != migration_plan_id(plan):
        raise ArtifactSchemaError("migration plan ID does not match its canonical content")
    if plan.get("status") not in {"planned", "blocked", "in-progress", "committed"}:
        raise ArtifactSchemaError("migration plan has an invalid status")
    if plan.get("resume_stage_after_migration") not in NORMAL_STAGES:
        raise ArtifactSchemaError("migration plan has an invalid resume stage")
    steps = plan.get("steps")
    if not isinstance(steps, list):
        raise ArtifactSchemaError("migration plan steps must be a list")
    for step in steps:
        if not isinstance(step, dict) or step.get("action") not in MIGRATION_ACTIONS:
            raise ArtifactSchemaError("migration plan contains an invalid step")
        if not isinstance(step.get("paths"), list):
            raise ArtifactSchemaError("migration step paths must be a list")
    return plan


def validate_plan_snapshot(root: Path, plan: dict[str, Any]) -> None:
    _snapshot, current_hash = source_snapshot(root)
    if current_hash != plan.get("source_manifest_sha256"):
        raise ArtifactSchemaError(
            "Pack changed after the migration plan was generated; generate a new plan"
        )


def migration_allowed_paths(plan: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    mutable: set[str] = {
        ".work/analysis-state.yaml",
        ".work/artifact-manifest.json",
        ".work/migration-plan.yaml",
    }
    must_remove: set[str] = set()
    preserve: set[str] = set()
    for step in plan.get("steps", []):
        action = step.get("action")
        paths = {str(item) for item in step.get("paths", [])}
        if action in {"mechanical-migrate", "review-and-adopt"}:
            mutable |= paths
        elif action == "archive-and-rebuild":
            mutable |= paths
            must_remove |= paths
        elif action == "preserve":
            preserve |= paths
    return mutable, must_remove, preserve


def earliest_invalidated_stage(plan: dict[str, Any]) -> str:
    return str(plan.get("resume_stage_after_migration"))
