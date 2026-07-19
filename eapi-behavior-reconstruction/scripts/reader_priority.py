#!/usr/bin/env python3
"""Mechanical checks for progressive Reader document ordering.

The contract deliberately checks only Artifact identity and section placement.  It
does not decide which capability is primary, whether a variant is meaningful, or
whether a risk deserves reader attention.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markdown_structure import parse_markdown


DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "reader-priority-schema.json"
READER_PRIORITY_VALIDATION_VERSION = "1"


class ReaderPriorityError(RuntimeError):
    """The bundled Reader Priority contract is invalid."""


@dataclass(frozen=True)
class ReaderPriorityIssue:
    code: str
    line: int
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "line": self.line, "message": self.message}


def _scalar(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def load_reader_priority_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReaderPriorityError(f"cannot read Reader Priority Schema {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReaderPriorityError("Reader Priority Schema must be a JSON object")
    if payload.get("reader_priority_schema_version") != "1":
        raise ReaderPriorityError("unsupported Reader Priority Schema version")
    if payload.get("validation_version") != READER_PRIORITY_VALIDATION_VERSION:
        raise ReaderPriorityError("Reader Priority validation version is inconsistent")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ReaderPriorityError("Reader Priority Schema must define artifacts")
    for artifact_type, definition in artifacts.items():
        if not isinstance(artifact_type, str) or not isinstance(definition, dict):
            raise ReaderPriorityError("invalid Reader Priority artifact definition")
        for key in ("artifact_schema_version", "template"):
            if not isinstance(definition.get(key), str) or not definition[key]:
                raise ReaderPriorityError(f"{artifact_type} has invalid {key}")
        required = definition.get("required_h2")
        ordered = definition.get("ordered_h2")
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise ReaderPriorityError(f"{artifact_type} has invalid required_h2")
        if not isinstance(ordered, list) or not all(isinstance(item, str) for item in ordered):
            raise ReaderPriorityError(f"{artifact_type} has invalid ordered_h2")
        if not set(required).issubset(set(ordered)):
            raise ReaderPriorityError(f"{artifact_type} required_h2 must be part of ordered_h2")
        if len(ordered) != len(set(ordered)):
            raise ReaderPriorityError(f"{artifact_type} ordered_h2 contains duplicates")
    return payload


def validate_reader_priority_document(
    path: Path,
    schema: dict[str, Any],
) -> tuple[str, list[ReaderPriorityIssue]]:
    text = path.read_text(encoding="utf-8")
    structure = parse_markdown(text)
    if structure.issues:
        issue = structure.issues[0]
        return "unknown", [
            ReaderPriorityIssue(
                "READER-PRIORITY-PREREQUISITE",
                issue.line,
                f"Markdown structure is invalid: {issue.message}",
            )
        ]
    artifact_type = _scalar(structure.frontmatter, "artifact_type") or "unknown"
    definition = schema["artifacts"].get(artifact_type)
    if definition is None:
        return artifact_type, []
    issues: list[ReaderPriorityIssue] = []
    version = _scalar(structure.frontmatter, "artifact_schema_version")
    if version != definition["artifact_schema_version"]:
        issues.append(
            ReaderPriorityIssue(
                "READER-PRIORITY-VERSION",
                1,
                f"{artifact_type} must use Artifact Schema {definition['artifact_schema_version']}",
            )
        )
    h2 = [(title, line) for level, title, line in structure.headings if level == 2]
    positions = {title: (index, line) for index, (title, line) in enumerate(h2)}
    for heading in definition["required_h2"]:
        if heading not in positions:
            issues.append(
                ReaderPriorityIssue(
                    "READER-PRIORITY-SECTION",
                    1,
                    f"{artifact_type} is missing required Reader section: {heading}",
                )
            )
    observed = [heading for heading in definition["ordered_h2"] if heading in positions]
    observed_positions = [positions[heading][0] for heading in observed]
    if observed_positions != sorted(observed_positions):
        offending = next(
            (
                heading
                for index, heading in enumerate(observed[1:], start=1)
                if positions[heading][0] < positions[observed[index - 1]][0]
            ),
            observed[-1] if observed else "Reader sections",
        )
        issues.append(
            ReaderPriorityIssue(
                "READER-PRIORITY-ORDER",
                positions.get(offending, (0, 1))[1],
                f"{artifact_type} Reader sections do not follow progressive-disclosure order",
            )
        )
    return artifact_type, issues


def validate_bundled_reader_priority_contract(
    *,
    assets_root: Path,
    registry_versions: dict[str, str],
) -> list[str]:
    schema = load_reader_priority_schema(assets_root / "reader-priority-schema.json")
    errors: list[str] = []
    for artifact_type, definition in schema["artifacts"].items():
        expected = definition["artifact_schema_version"]
        if registry_versions.get(artifact_type) != expected:
            errors.append(
                f"Reader Priority {artifact_type} version {expected} does not match Artifact Registry"
            )
        template = assets_root / definition["template"]
        if not template.is_file():
            errors.append(f"Reader Priority template is missing: {definition['template']}")
            continue
        observed_type, issues = validate_reader_priority_document(template, schema)
        if observed_type != artifact_type:
            errors.append(
                f"Reader Priority template {definition['template']} declares {observed_type}, expected {artifact_type}"
            )
        errors.extend(f"{definition['template']}: {issue.message}" for issue in issues)
    return errors


def validate_reader_priority_root(
    root: Path,
    schema: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    contract = schema or load_reader_priority_schema()
    patterns = {
        "repository-overview": ("tech-pack/repository-overview.md",),
        "tech-behavior": ("tech-pack/behaviors/*.md",),
        "api-contract": ("tech-pack/contracts/*.api-contract.md",),
    }
    documents: list[dict[str, Any]] = []
    for artifact_type in contract["artifacts"]:
        for pattern in patterns[artifact_type]:
            for path in sorted(root.glob(pattern)):
                observed_type, issues = validate_reader_priority_document(path, contract)
                documents.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "artifact_type": observed_type,
                        "issues": [issue.as_dict() for issue in issues],
                    }
                )
    return documents
