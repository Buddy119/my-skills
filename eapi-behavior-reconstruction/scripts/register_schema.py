#!/usr/bin/env python3
"""Load and mechanically validate the versioned Repository Register schema."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_REGISTER_SCHEMA_VERSIONS = {"3"}
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "register-schema.json"


class RegisterSchemaError(RuntimeError):
    """The bundled schema contract is unreadable or internally inconsistent."""


@dataclass(frozen=True)
class TableContract:
    key: str
    domain: str
    section: str
    headers: tuple[str, ...]


@dataclass(frozen=True)
class RegisterSchema:
    version: str
    tables: dict[str, TableContract]
    domain_dependencies: dict[str, tuple[str, ...]]

    def tables_for_domain(self, domain: str) -> tuple[TableContract, ...]:
        return tuple(table for table in self.tables.values() if table.domain == domain)


@dataclass(frozen=True)
class ContractCheck:
    version: str | None
    errors: tuple[str, ...]
    domain_errors: dict[str, tuple[str, ...]]

    @property
    def valid(self) -> bool:
        return not self.errors and not any(self.domain_errors.values())


def load_register_schema(path: Path = DEFAULT_SCHEMA_PATH) -> RegisterSchema:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegisterSchemaError(f"cannot load register schema {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegisterSchemaError("register schema root must be an object")
    version = payload.get("register_schema_version")
    if not isinstance(version, str) or version not in SUPPORTED_REGISTER_SCHEMA_VERSIONS:
        raise RegisterSchemaError(f"unsupported bundled register schema version: {version!r}")
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, dict) or not raw_tables:
        raise RegisterSchemaError("register schema must define at least one table")
    tables: dict[str, TableContract] = {}
    sections: set[str] = set()
    for key, raw in raw_tables.items():
        if not isinstance(key, str) or not isinstance(raw, dict):
            raise RegisterSchemaError("each register table must be a named object")
        domain = raw.get("domain")
        section = raw.get("section")
        headers = raw.get("headers")
        if not isinstance(domain, str) or not domain:
            raise RegisterSchemaError(f"register table {key} has no domain")
        if not isinstance(section, str) or not section:
            raise RegisterSchemaError(f"register table {key} has no section")
        if section in sections:
            raise RegisterSchemaError(f"duplicate register section in schema: {section}")
        if not isinstance(headers, list) or not headers or not all(
            isinstance(item, str) and item for item in headers
        ):
            raise RegisterSchemaError(f"register table {key} has invalid headers")
        if len(set(headers)) != len(headers):
            raise RegisterSchemaError(f"register table {key} contains duplicate headers")
        sections.add(section)
        tables[key] = TableContract(key, domain, section, tuple(headers))
    raw_dependencies = payload.get("domain_dependencies", {})
    if not isinstance(raw_dependencies, dict):
        raise RegisterSchemaError("domain_dependencies must be an object")
    domain_dependencies: dict[str, tuple[str, ...]] = {}
    for group, domains in raw_dependencies.items():
        if not isinstance(group, str) or not isinstance(domains, list) or not all(
            isinstance(item, str) and item for item in domains
        ):
            raise RegisterSchemaError(f"invalid domain dependency group: {group!r}")
        domain_dependencies[group] = tuple(domains)
    return RegisterSchema(version, tables, domain_dependencies)


def scalar_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", text, re.M)
    return match.group(1).strip() if match else None


def section_value(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<content>.*?)(?=^##\s+|\Z)",
        text,
        re.M | re.S,
    )
    return match.group("content") if match else ""


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_header(text: str, section: str) -> list[str]:
    for line in section_value(text, section).splitlines():
        if line.strip().startswith("|"):
            return table_cells(line)
    return []


def validate_register_text(text: str, schema: RegisterSchema) -> ContractCheck:
    artifact_type = scalar_value(text, "artifact_type")
    version = scalar_value(text, "artifact_schema_version")
    global_errors: list[str] = []
    domain_errors: dict[str, list[str]] = {}
    if artifact_type != "repository-register":
        global_errors.append(
            "artifact_type must be repository-register; "
            f"observed {artifact_type or '<missing>'}"
        )
    if version != schema.version:
        global_errors.append(
            f"repository-register artifact_schema_version must be {schema.version}; "
            f"observed {version or '<missing>'}"
        )
    if global_errors:
        return ContractCheck(version, tuple(global_errors), {})
    for table in schema.tables.values():
        observed = table_header(text, table.section)
        if observed != list(table.headers):
            detail = (
                f"{table.section}: expected {list(table.headers)!r}; "
                f"observed {observed!r}"
            )
            domain_errors.setdefault(table.domain, []).append(detail)
    return ContractCheck(
        version,
        tuple(global_errors),
        {domain: tuple(items) for domain, items in domain_errors.items()},
    )


def validate_register_file(path: Path, schema: RegisterSchema) -> ContractCheck:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ContractCheck(None, (f"cannot read repository register {path}: {exc}",), {})
    return validate_register_text(text, schema)


def validate_bundled_contract(
    template_path: Path,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> ContractCheck:
    schema = load_register_schema(schema_path)
    return validate_register_file(template_path, schema)
