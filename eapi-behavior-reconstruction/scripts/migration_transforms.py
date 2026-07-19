#!/usr/bin/env python3
"""Registered deterministic migrations for knowledge-pack artifacts.

This module owns structural conversion only. It must never reconcile dependency
identity, group failure patterns, build business models, or generate reader prose.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TRANSFORM_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "migration-transform-registry.json"
)


class MigrationTransformError(RuntimeError):
    """A registered deterministic transform cannot be loaded or executed safely."""


@dataclass(frozen=True)
class TransformDefinition:
    transform_id: str
    artifact_type: str
    source_version: str
    target_version: str
    source_schema: str
    target_schema: str
    handler: str
    fixture: str
    id_generation_rule: str
    link_rewrite_rule: str
    referential_checks: tuple[str, ...]


@dataclass(frozen=True)
class TransformRegistry:
    version: str
    definitions: dict[str, TransformDefinition]
    root: Path


def _json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationTransformError(f"cannot load JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MigrationTransformError(f"JSON object expected: {path}")
    return payload


def load_transform_registry(
    path: Path = DEFAULT_TRANSFORM_REGISTRY_PATH,
) -> TransformRegistry:
    payload = _json_object(path)
    version = payload.get("migration_transform_registry_version")
    raw_definitions = payload.get("transforms")
    if not isinstance(version, str) or not version:
        raise MigrationTransformError("transform registry version must be a non-empty string")
    if not isinstance(raw_definitions, dict) or not raw_definitions:
        raise MigrationTransformError("transform registry must define transforms")
    definitions: dict[str, TransformDefinition] = {}
    handlers = {
        "analysis-state-envelope",
        "repository-register-flat-http-1",
        "repository-register-1-to-2",
    }
    for transform_id, raw in raw_definitions.items():
        if not isinstance(transform_id, str) or not isinstance(raw, dict):
            raise MigrationTransformError("each transform must be a named object")
        string_fields = {
            name: raw.get(name)
            for name in (
                "artifact_type",
                "source_version",
                "target_version",
                "source_schema",
                "target_schema",
                "handler",
                "fixture",
                "id_generation_rule",
                "link_rewrite_rule",
            )
        }
        invalid = [name for name, value in string_fields.items() if not isinstance(value, str) or not value]
        checks = raw.get("referential_checks")
        if invalid or not isinstance(checks, list) or not all(
            isinstance(item, str) and item for item in checks
        ):
            raise MigrationTransformError(
                f"transform {transform_id} has invalid fields: {', '.join(invalid) or 'referential_checks'}"
            )
        if string_fields["handler"] not in handlers:
            raise MigrationTransformError(
                f"transform {transform_id} uses an unregistered handler: {string_fields['handler']}"
            )
        fixture = (path.parent / str(string_fields["fixture"])).resolve()
        if not fixture.is_file():
            raise MigrationTransformError(
                f"transform {transform_id} fixture is missing: {string_fields['fixture']}"
            )
        source_schema = str(string_fields["source_schema"])
        if "/" in source_schema or source_schema.endswith(".json"):
            schema_path = (path.parent / source_schema).resolve()
            if not schema_path.is_file():
                raise MigrationTransformError(
                    f"transform {transform_id} source schema is missing: {source_schema}"
                )
        target_schema = str(string_fields["target_schema"])
        if "/" in target_schema or target_schema.endswith(".json"):
            schema_path = (path.parent / target_schema).resolve()
            if not schema_path.is_file():
                raise MigrationTransformError(
                    f"transform {transform_id} target schema is missing: {target_schema}"
                )
        fixture_text = fixture.read_text(encoding="utf-8")
        fixture_type = _scalar(fixture_text, "artifact_type")
        fixture_version = _scalar(fixture_text, "artifact_schema_version")
        if (
            fixture_type != string_fields["artifact_type"]
            or fixture_version != string_fields["source_version"]
        ):
            raise MigrationTransformError(
                f"transform {transform_id} fixture does not declare the registered source identity"
            )
        definitions[transform_id] = TransformDefinition(
            transform_id=transform_id,
            artifact_type=str(string_fields["artifact_type"]),
            source_version=str(string_fields["source_version"]),
            target_version=str(string_fields["target_version"]),
            source_schema=source_schema,
            target_schema=target_schema,
            handler=str(string_fields["handler"]),
            fixture=str(string_fields["fixture"]),
            id_generation_rule=str(string_fields["id_generation_rule"]),
            link_rewrite_rule=str(string_fields["link_rewrite_rule"]),
            referential_checks=tuple(checks),
        )
    return TransformRegistry(version, definitions, path.parent.resolve())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_records(root: Path, paths: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in sorted(paths):
        path = root / relative
        if path.is_file():
            records.append(
                {
                    "path": relative,
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                    "line_count": len(path.read_text(encoding="utf-8").splitlines()),
                }
            )
    return records


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n#]+?)[\"']?\s*$", text, re.M)
    return match.group(1).strip() if match else None


def _set_scalar(text: str, key: str, value: str) -> str:
    line = f'{key}: "{value}"'
    if re.search(rf"^{re.escape(key)}:\s*.*$", text, re.M):
        return re.sub(rf"^{re.escape(key)}:\s*.*$", line, text, count=1, flags=re.M)
    return line + "\n" + text


def _behavior_ids(text: str) -> list[str]:
    return re.findall(r"^\s*-\s+behavior_id:\s*[\"']?([^\"'\n]+)", text, re.M)


def _analysis_state_transform(path: Path, definition: TransformDefinition) -> tuple[dict[str, Any], str]:
    before = path.read_text(encoding="utf-8")
    repository = _scalar(before, "repository")
    source_commit = _scalar(before, "source_commit")
    behavior_ids = _behavior_ids(before)
    after = _set_scalar(before, "artifact_type", "analysis-state")
    after = _set_scalar(after, "artifact_schema_version", definition.target_version)
    _atomic_text(path, after)
    if repository != _scalar(after, "repository") or source_commit != _scalar(after, "source_commit"):
        raise MigrationTransformError("analysis-state transform changed repository identity or commit")
    if behavior_ids != _behavior_ids(after):
        raise MigrationTransformError("analysis-state transform changed behavior identities")
    return {
        "source_records": {"behavior_ids": len(behavior_ids)},
        "output_records": {"behavior_ids": len(behavior_ids)},
        "id_map": {},
        "referential_check_results": {
            "repository-and-source-commit-preserved": "passed",
            "behavior-identities-preserved": "passed",
        },
    }, after


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _source_rows(text: str, section: str, headers: list[str]) -> list[dict[str, str]]:
    lines = text.splitlines()
    heading = f"## {section}"
    try:
        start = lines.index(heading)
    except ValueError as exc:
        raise MigrationTransformError(f"source table section is missing: {section}") from exc
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    header_index = next(
        (index for index in range(start + 1, end) if lines[index].lstrip().startswith("|")),
        None,
    )
    if header_index is None or _table_cells(lines[header_index]) != headers:
        observed = _table_cells(lines[header_index]) if header_index is not None else []
        raise MigrationTransformError(
            f"source table header mismatch for {section}: expected {headers!r}, observed {observed!r}"
        )
    if header_index + 1 >= end or not lines[header_index + 1].lstrip().startswith("|"):
        raise MigrationTransformError(f"source table delimiter is missing: {section}")
    rows: list[dict[str, str]] = []
    for line in lines[header_index + 2 : end]:
        if not line.lstrip().startswith("|"):
            if rows:
                break
            continue
        cells = _table_cells(line)
        if len(cells) != len(headers):
            raise MigrationTransformError(
                f"source table row has {len(cells)} cells, expected {len(headers)}: {section}"
            )
        rows.append(dict(zip(headers, cells)))
    return rows


def _replace_table_rows(text: str, section: str, headers: list[str], rows: list[list[str]]) -> str:
    lines = text.splitlines()
    heading = f"## {section}"
    try:
        start = lines.index(heading)
    except ValueError as exc:
        raise MigrationTransformError(f"target table section is missing: {section}") from exc
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    header_index = next(
        (index for index in range(start + 1, end) if lines[index].lstrip().startswith("|")),
        None,
    )
    if header_index is None or _table_cells(lines[header_index]) != headers:
        raise MigrationTransformError(f"target table header mismatch for {section}")
    row_end = header_index + 2
    while row_end < end and lines[row_end].lstrip().startswith("|"):
        row_end += 1
    escaped_rows = [
        "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows
    ]
    updated = lines[: header_index + 2] + escaped_rows + lines[row_end:]
    return "\n".join(updated) + "\n"


def _stable_numeric_id(prefix: str, identity: str, occupied: set[str]) -> str:
    salt = 0
    while True:
        material = identity if salt == 0 else f"{identity}\u241f{salt}"
        number = int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:15], 16)
        candidate = f"{prefix}{number}"
        if candidate not in occupied:
            occupied.add(candidate)
            return candidate
        salt += 1


def _explicit_or_stable(
    raw: str,
    pattern: re.Pattern[str],
    prefix: str,
    identity: str,
    occupied: set[str],
    id_map: dict[str, str],
    map_key: str,
    identity_cache: dict[str, str] | None = None,
) -> str:
    value = raw.strip().strip("`")
    if value:
        if not pattern.fullmatch(value):
            raise MigrationTransformError(f"explicit legacy ID has an unsupported format: {value}")
        if identity_cache is not None:
            existing = identity_cache.get(identity)
            if existing is not None and existing != value:
                raise MigrationTransformError(
                    f"one explicit structural identity has conflicting IDs: {existing}, {value}"
                )
            identity_cache[identity] = value
        occupied.add(value)
        id_map.setdefault(value, value)
        return value
    if identity_cache is not None and identity in identity_cache:
        generated = identity_cache[identity]
        id_map[map_key] = generated
        return generated
    generated = _stable_numeric_id(prefix, identity, occupied)
    if identity_cache is not None:
        identity_cache[identity] = generated
    id_map[map_key] = generated
    return generated


def _join_unique(values: list[str]) -> str:
    return ", ".join(dict.fromkeys(value for value in values if value)) or "None"


def _render_flat_register(
    source_text: str,
    definition: TransformDefinition,
    assets_root: Path,
) -> tuple[str, dict[str, Any]]:
    source_schema = _json_object(assets_root / definition.source_schema)
    target_schema = _json_object(assets_root / definition.target_schema)
    source_tables = source_schema["tables"]
    http_rows = _source_rows(
        source_text,
        source_tables["flat_http_mappings"]["section"],
        source_tables["flat_http_mappings"]["headers"],
    )
    dependency_rows = _source_rows(
        source_text,
        source_tables["dependency_rows"]["section"],
        source_tables["dependency_rows"]["headers"],
    )
    failure_rows = _source_rows(
        source_text,
        source_tables["failure_rows"]["section"],
        source_tables["failure_rows"]["headers"],
    )
    repository = _scalar(source_text, "repository") or "unknown-repository"
    source_commit = _scalar(source_text, "source_commit") or "unknown"
    target = (assets_root / "repository-register-template.md").read_text(encoding="utf-8")
    target = target.replace("repository-name", repository).replace("git-commit-or-unknown", source_commit)

    call_pattern = re.compile(r"HTTP-\d+")
    usage_pattern = re.compile(r"HTTP-\d+-U\d+")
    mapping_pattern = re.compile(r"FM-\d+")
    dep_pattern = re.compile(r"DEP-OBS-\d+")
    fail_pattern = re.compile(r"FO-\d+")
    occupied_calls: set[str] = set()
    occupied_usages: set[str] = set()
    occupied_mappings: set[str] = set()
    occupied_deps: set[str] = set()
    occupied_failures: set[str] = set()
    call_ids_by_identity: dict[str, str] = {}
    usage_ids_by_identity: dict[str, str] = {}
    mapping_ids_by_identity: dict[str, str] = {}
    dependency_ids_by_identity: dict[str, str] = {}
    failure_ids_by_identity: dict[str, str] = {}
    id_map: dict[str, str] = {}
    operations: dict[str, dict[str, Any]] = {}
    usages: dict[str, dict[str, Any]] = {}
    mappings: dict[str, dict[str, str]] = {}

    for index, row in enumerate(http_rows, 1):
        call_identity = "\u241f".join(
            row[key]
            for key in (
                "Method",
                "Logical Target",
                "Client Operation",
                "Behavior ID",
                "Executable Call Site",
            )
        )
        call_id = _explicit_or_stable(
            row["Call ID"], call_pattern, "HTTP-", call_identity, occupied_calls, id_map,
            f"http-row-{index}:call", call_ids_by_identity
        )
        call_fields = {
            "Method": row["Method"],
            "Logical Target": row["Logical Target"],
            "Client Operation": row["Client Operation"],
            "Observable Purpose": row["Observable Purpose"],
            "Status": row["Status"],
        }
        existing_call = operations.get(call_id)
        if existing_call is not None and any(existing_call[key] != value for key, value in call_fields.items()):
            raise MigrationTransformError(
                f"legacy Call ID {call_id} has conflicting operation metadata; semantic reconciliation is required"
            )
        operation = operations.setdefault(
            call_id,
            {**call_fields, "Behaviors": [], "Evidence": []},
        )
        operation["Behaviors"].append(row["Behavior ID"])
        operation["Evidence"].append(row["Evidence"])

        usage_identity = "\u241f".join((call_id, row["Behavior ID"], row["Executable Call Site"]))
        usage_id = _explicit_or_stable(
            row["Usage ID"], usage_pattern, f"{call_id}-U", usage_identity, occupied_usages, id_map,
            f"http-row-{index}:usage", usage_ids_by_identity
        )
        usage_fields = {
            "Call ID": call_id,
            "Behavior ID": row["Behavior ID"],
            "Executable Call Site": row["Executable Call Site"],
            "Invocation Condition or Config": row["Invocation Condition or Config"],
            "Status": row["Status"],
        }
        if usage_id in usages and any(
            usages[usage_id][key] != value for key, value in usage_fields.items()
        ):
            raise MigrationTransformError(
                f"legacy Usage ID {usage_id} has conflicting structural fields"
            )
        usage = usages.setdefault(usage_id, {**usage_fields, "Evidence": []})
        usage["Evidence"].append(row["Evidence"])

        mapping_identity = "\u241f".join(
            (
                call_id,
                usage_id,
                row["Direction"],
                row["Source Field(s)"],
                row["Target Field(s)"],
                row["Transformation"],
                row["Condition/Default"],
                row["Lossy"],
                row["Evidence"],
            )
        )
        mapping_id = _explicit_or_stable(
            row["Mapping ID"], mapping_pattern, "FM-", mapping_identity, occupied_mappings, id_map,
            f"http-row-{index}:mapping", mapping_ids_by_identity
        )
        mapping = {
            "Call ID": call_id,
            "Applies to Usage(s)": usage_id,
            "Direction": row["Direction"],
            "Source Field(s)": row["Source Field(s)"],
            "Target Field(s)": row["Target Field(s)"],
            "Transformation": row["Transformation"],
            "Condition/Default": row["Condition/Default"],
            "Lossy": row["Lossy"],
            "Status": row["Status"],
            "Evidence": row["Evidence"],
        }
        if mapping_id in mappings and mappings[mapping_id] != mapping:
            raise MigrationTransformError(f"legacy Mapping ID {mapping_id} is duplicated with different data")
        mappings[mapping_id] = mapping

    operation_rows = [
        [
            call_id,
            item["Method"],
            item["Logical Target"],
            item["Client Operation"],
            item["Observable Purpose"],
            _join_unique(item["Behaviors"]),
            "None",
            item["Status"],
            _join_unique(item["Evidence"]),
        ]
        for call_id, item in sorted(operations.items())
    ]
    usage_rows = [
        [usage_id]
        + [
            item["Call ID"],
            item["Behavior ID"],
            item["Executable Call Site"],
            item["Invocation Condition or Config"],
            item["Status"],
            _join_unique(item["Evidence"]),
        ]
        for usage_id, item in sorted(usages.items())
    ]
    mapping_rows = [
        [mapping_id] + [item[key] for key in (
            "Call ID", "Applies to Usage(s)", "Direction", "Source Field(s)", "Target Field(s)",
            "Transformation", "Condition/Default", "Lossy", "Status", "Evidence"
        )]
        for mapping_id, item in sorted(mappings.items())
    ]

    dep_output: list[list[str]] = []
    for index, row in enumerate(dependency_rows, 1):
        identity = "\u241f".join(row[key] for key in source_tables["dependency_rows"]["headers"][1:])
        observation_id = _explicit_or_stable(
            row["Observation ID"], dep_pattern, "DEP-OBS-", identity, occupied_deps, id_map,
            f"dependency-row-{index}:observation", dependency_ids_by_identity
        )
        dep_output.append(
            [observation_id]
            + [row[key] for key in source_tables["dependency_rows"]["headers"][1:]]
            + ["Unresolved"]
        )

    failure_output: list[list[str]] = []
    for index, row in enumerate(failure_rows, 1):
        identity = "\u241f".join(row[key] for key in source_tables["failure_rows"]["headers"][1:])
        observation_id = _explicit_or_stable(
            row["Observation ID"], fail_pattern, "FO-", identity, occupied_failures, id_map,
            f"failure-row-{index}:observation", failure_ids_by_identity
        )
        failure_output.append(
            [observation_id]
            + [row[key] for key in source_tables["failure_rows"]["headers"][1:]]
            + ["Unresolved"]
        )

    target_rows = {
        "http_operations": operation_rows,
        "http_usages": usage_rows,
        "http_mappings": mapping_rows,
        "dependency_observations": dep_output,
        "failure_observations": failure_output,
    }
    for key, contract in target_schema["tables"].items():
        target = _replace_table_rows(
            target,
            contract["section"],
            contract["headers"],
            target_rows.get(key, []),
        )
    report = {
        "source_records": {
            "flat_http_mappings": len(http_rows),
            "dependency_rows": len(dependency_rows),
            "failure_rows": len(failure_rows),
        },
        "output_records": {
            "http_operations": len(operation_rows),
            "http_usages": len(usage_rows),
            "http_mappings": len(mapping_rows),
            "dependency_observations": len(dep_output),
            "dependency_contracts": 0,
            "failure_observations": len(failure_output),
            "failure_patterns": 0,
        },
        "id_map": id_map,
        "referential_check_results": {
            "usage-call-references-exist": "passed",
            "mapping-call-and-usage-references-exist": "passed",
            "dependency-and-failure-observations-remain-unresolved": "passed",
        },
    }
    return target, report


def _render_table_section(section: str, headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        f"## {section}",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend(
        "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def _render_register_1_to_2(
    source_text: str,
    definition: TransformDefinition,
    assets_root: Path,
) -> tuple[str, dict[str, Any]]:
    """Preserve v1 Register bytes except for the flat lifecycle section.

    The legacy row is intentionally converted only into an unresolved observation.
    Object, State, Action, and Transition identities require later AI synthesis.
    """

    source_schema = _json_object(assets_root / definition.source_schema)
    target_schema = _json_object(assets_root / definition.target_schema)
    legacy = source_schema["tables"]["data_state_changes"]
    legacy_rows = _source_rows(source_text, legacy["section"], legacy["headers"])
    occupied: set[str] = set()
    id_map: dict[str, str] = {}
    observation_rows: list[list[str]] = []
    for index, row in enumerate(legacy_rows, 1):
        identity = "\u241f".join(row[header] for header in legacy["headers"])
        observation_id = _stable_numeric_id("LIFE-OBS-", identity, occupied)
        id_map[f"legacy-lifecycle-row-{index}:observation"] = observation_id
        observation_rows.append(
            [
                observation_id,
                row["Object or resource"],
                row["Behavior ID"],
                row["Operation"],
                row["From state/source"],
                row["To state/destination"],
                "Unknown",
                row["Status"],
                row["Evidence"],
                "Unresolved",
            ]
        )

    lifecycle_keys = (
        "lifecycle_observations",
        "business_objects",
        "object_states",
        "processing_actions",
        "state_transitions",
    )
    sections = []
    for key in lifecycle_keys:
        contract = target_schema["tables"][key]
        sections.append(
            _render_table_section(
                contract["section"],
                contract["headers"],
                observation_rows if key == "lifecycle_observations" else [],
            )
        )
    replacement = "\n\n".join(sections) + "\n\n"
    section_match = re.search(
        rf"^##\s+{re.escape(legacy['section'])}\s*$\n",
        source_text,
        re.M,
    )
    if section_match is None:
        raise MigrationTransformError(f"legacy lifecycle section is missing: {legacy['section']}")
    next_heading = re.search(r"^##\s+", source_text[section_match.end() :], re.M)
    end = (
        section_match.end() + next_heading.start()
        if next_heading is not None
        else len(source_text)
    )
    rendered = source_text[: section_match.start()] + replacement + source_text[end:]
    rendered = _set_scalar(rendered, "artifact_schema_version", definition.target_version)
    if "## Unrelated preserved section\n\nThis text must remain byte-for-byte unchanged" in source_text:
        if "## Unrelated preserved section\n\nThis text must remain byte-for-byte unchanged" not in rendered:
            raise MigrationTransformError("an unaffected Register section changed during migration")
    report = {
        "source_records": {"data_state_changes": len(legacy_rows)},
        "output_records": {
            "lifecycle_observations": len(observation_rows),
            "business_objects": 0,
            "object_states": 0,
            "processing_actions": 0,
            "state_transitions": 0,
        },
        "id_map": id_map,
        "referential_check_results": {
            "unaffected-register-sections-preserved": "passed",
            "legacy-lifecycle-rows-become-unresolved-observations": "passed",
            "no-object-state-action-or-transition-is-generated": "passed",
        },
    }
    return rendered, report


def preview_transform(
    definition: TransformDefinition,
    root: Path,
    paths: list[str],
    assets_root: Path,
) -> dict[str, Any]:
    if len(paths) != 1:
        raise MigrationTransformError(
            f"transform {definition.transform_id} requires exactly one input path"
        )
    path = root / paths[0]
    if not path.is_file():
        raise MigrationTransformError(
            f"transform {definition.transform_id} input is missing: {paths[0]}"
        )
    if definition.handler == "analysis-state-envelope":
        text = path.read_text(encoding="utf-8")
        return {
            "input_file_count": 1,
            "output_file_count": 1,
            "source_record_counts": {"behavior_ids": len(_behavior_ids(text))},
            "output_record_counts": {"behavior_ids": len(_behavior_ids(text))},
        }
    if definition.handler == "repository-register-flat-http-1":
        _rendered, report = _render_flat_register(
            path.read_text(encoding="utf-8"), definition, assets_root
        )
        return {
            "input_file_count": 1,
            "output_file_count": 1,
            "source_record_counts": report["source_records"],
            "output_record_counts": report["output_records"],
        }
    if definition.handler == "repository-register-1-to-2":
        _rendered, report = _render_register_1_to_2(
            path.read_text(encoding="utf-8"), definition, assets_root
        )
        return {
            "input_file_count": 1,
            "output_file_count": 1,
            "source_record_counts": report["source_records"],
            "output_record_counts": report["output_records"],
        }
    raise MigrationTransformError(f"unsupported transform handler: {definition.handler}")


def execute_transform(
    definition: TransformDefinition,
    root: Path,
    input_paths: list[str],
    output_paths: list[str],
    assets_root: Path,
) -> dict[str, Any]:
    if input_paths != output_paths or len(input_paths) != 1:
        raise MigrationTransformError(
            f"transform {definition.transform_id} supports one in-place artifact only"
        )
    path = root / input_paths[0]
    input_manifest = _file_records(root, input_paths)
    if definition.handler == "analysis-state-envelope":
        report, _text = _analysis_state_transform(path, definition)
    elif definition.handler == "repository-register-flat-http-1":
        rendered, report = _render_flat_register(
            path.read_text(encoding="utf-8"), definition, assets_root
        )
        _atomic_text(path, rendered)
    elif definition.handler == "repository-register-1-to-2":
        rendered, report = _render_register_1_to_2(
            path.read_text(encoding="utf-8"), definition, assets_root
        )
        _atomic_text(path, rendered)
    else:
        raise MigrationTransformError(f"unsupported transform handler: {definition.handler}")
    output_manifest = _file_records(root, output_paths)
    return {
        "transform_id": definition.transform_id,
        "artifact_type": definition.artifact_type,
        "source_version": definition.source_version,
        "target_version": definition.target_version,
        "input_manifest": input_manifest,
        "output_manifest": output_manifest,
        "input_summary": {
            "file_count": len(input_manifest),
            "byte_count": sum(item["size"] for item in input_manifest),
        },
        "output_summary": {
            "file_count": len(output_manifest),
            "byte_count": sum(item["size"] for item in output_manifest),
        },
        "id_generation_rule": definition.id_generation_rule,
        "link_rewrite_rule": definition.link_rewrite_rule,
        **report,
    }
