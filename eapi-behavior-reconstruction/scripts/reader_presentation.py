#!/usr/bin/env python3
"""Mechanical Reader Pack presentation checks.

The working model keeps complete evidence and status.  This module validates only
the publication projection: generic Status/Evidence columns are absent, exceptional
qualifiers use the public vocabulary, Tech evidence is grouped into Source Notes,
and BA documents do not expose repository source citations.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markdown_structure import MarkdownStructure, parse_markdown


DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "reader-presentation-schema.json"
READER_PRESENTATION_VALIDATION_VERSION = "2"
SOURCE_CITATION_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):"
    r"(?P<start>\d+)(?:-(?P<end>\d+))?`"
)
MARKER_LINK_RE = re.compile(r"\[(?P<label>E[1-9][0-9]*)\]\(#(?P<anchor>e[1-9][0-9]*)\)")
MARKER_DEFINITION_RE = re.compile(
    r"<a\s+(?:id|name)=[\"'](?P<anchor>e[1-9][0-9]*)[\"']\s*></a>\s*"
    r"\*\*(?P<label>E[1-9][0-9]*)\*\*",
    re.I,
)
STATUS_QUALIFIER_RE = re.compile(r"\*\((?P<value>[^)\n]+)\)\*")


class ReaderPresentationError(RuntimeError):
    """The bundled presentation contract or one Reader artifact is invalid."""


@dataclass(frozen=True)
class PresentationIssue:
    code: str
    line: int
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "line": self.line, "message": self.message}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReaderPresentationError(f"cannot read Reader presentation schema {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReaderPresentationError("Reader presentation schema must be a JSON object")
    return payload


def load_reader_presentation_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    schema = _load_json(path)
    if schema.get("reader_presentation_schema_version") != "2":
        raise ReaderPresentationError("unsupported Reader presentation schema version")
    if schema.get("validation_version") != READER_PRESENTATION_VALIDATION_VERSION:
        raise ReaderPresentationError("unsupported Reader presentation validation version")
    qualifiers = schema.get("exception_qualifiers")
    expected = {
        "Inferred": "*(Inferred)*",
        "Unknown": "*(Unknown)*",
        "Conflicting": "*(Conflicting)*",
    }
    if qualifiers != expected or schema.get("confirmed_baseline") != "Confirmed":
        raise ReaderPresentationError("Reader qualifier vocabulary does not match the public contract")
    forbidden = schema.get("forbidden_table_headers")
    if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
        raise ReaderPresentationError("forbidden_table_headers must be a string list")
    affected = schema.get("affected_artifacts")
    if not isinstance(affected, dict) or not affected:
        raise ReaderPresentationError("affected_artifacts must be a non-empty object")
    for artifact_type, definition in affected.items():
        if not isinstance(artifact_type, str) or not isinstance(definition, dict):
            raise ReaderPresentationError("invalid affected_artifacts entry")
        if definition.get("audience") not in {"tech", "ba"}:
            raise ReaderPresentationError(f"invalid audience for {artifact_type}")
        if not isinstance(definition.get("version"), str):
            raise ReaderPresentationError(f"invalid version for {artifact_type}")
        if not isinstance(definition.get("source_notes"), bool):
            raise ReaderPresentationError(f"invalid source_notes flag for {artifact_type}")
    return schema


def scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def _outside_fence_lines(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    fence_char: str | None = None
    fence_length = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        if fence_char is None:
            result.append((line_number, line))
    return result


def _definition_blocks(
    lines: list[tuple[int, str]],
) -> dict[str, tuple[int, str, frozenset[int]]]:
    definitions: dict[str, tuple[int, str, frozenset[int]]] = {}
    for index, (line_number, line) in enumerate(lines):
        match = MARKER_DEFINITION_RE.search(line)
        if not match:
            continue
        anchor = match.group("anchor").lower()
        label = match.group("label").lower()
        if anchor != label:
            definitions[f"invalid:{line_number}"] = (line_number, line, frozenset({line_number}))
            continue
        block = [line]
        block_lines = {line_number}
        cursor = index + 1
        while cursor < len(lines):
            _next_line_number, next_line = lines[cursor]
            if not next_line.strip() or re.match(r"^#{1,6}\s+", next_line):
                break
            if MARKER_DEFINITION_RE.search(next_line):
                break
            block.append(next_line)
            block_lines.add(_next_line_number)
            cursor += 1
        definitions[anchor] = (line_number, "\n".join(block), frozenset(block_lines))
    return definitions


def _validate_citation(match: re.Match[str], repo: Path, line: int) -> PresentationIssue | None:
    relative = match.group("path")
    start = int(match.group("start"))
    end = int(match.group("end")) if match.group("end") else start
    if end < start:
        return PresentationIssue("READER-SOURCE-RANGE", line, f"invalid source range: {relative}:{start}-{end}")
    source = (repo / relative).resolve()
    try:
        source.relative_to(repo.resolve())
    except ValueError:
        return PresentationIssue("READER-SOURCE-ESCAPE", line, f"source citation escapes repository: {relative}")
    if not source.is_file():
        return PresentationIssue("READER-SOURCE-MISSING", line, f"source citation does not exist: {relative}")
    try:
        with source.open(encoding="utf-8", errors="replace") as handle:
            line_count = sum(1 for _ in handle)
    except OSError as exc:
        return PresentationIssue("READER-SOURCE-READ", line, f"cannot read source citation {relative}: {exc}")
    if start < 1 or end > line_count:
        rendered = f"{relative}:{start}" if start == end else f"{relative}:{start}-{end}"
        return PresentationIssue("READER-SOURCE-BOUNDS", line, f"source citation outside file bounds: {rendered}")
    return None


def validate_reader_document(
    path: Path,
    *,
    root: Path,
    repo: Path | None,
    schema: dict[str, Any],
    max_issues: int = 20,
) -> tuple[str, list[PresentationIssue]]:
    text = path.read_text(encoding="utf-8")
    structure = parse_markdown(text)
    if structure.issues:
        return "unknown", [
            PresentationIssue("READER-MARKDOWN-PREREQUISITE", issue.line, issue.message)
            for issue in structure.issues[:1]
        ]
    artifact_type = scalar_value(structure.frontmatter, "artifact_type") or "unknown"
    artifact_version = scalar_value(structure.frontmatter, "artifact_schema_version")
    definition = schema["affected_artifacts"].get(artifact_type)
    if definition is None:
        return artifact_type, []
    issues: list[PresentationIssue] = []
    if artifact_version != definition["version"]:
        issues.append(
            PresentationIssue(
                "READER-ARTIFACT-VERSION",
                1,
                f"{artifact_type} must use artifact schema {definition['version']}",
            )
        )
        return artifact_type, issues

    forbidden = set(schema["forbidden_table_headers"])
    for table in structure.tables:
        invalid_headers = [header for header in table.headers if header in forbidden]
        if invalid_headers:
            issues.append(
                PresentationIssue(
                    "READER-GENERIC-COLUMN",
                    table.start_line,
                    "Reader table uses forbidden generic column(s): " + ", ".join(invalid_headers),
                )
            )

    visible_lines = _outside_fence_lines(text)
    for line_number, line in visible_lines:
        for qualifier in STATUS_QUALIFIER_RE.finditer(line):
            value = qualifier.group("value")
            canonical = next(
                (item for item in ("Confirmed", "Inferred", "Unknown", "Conflicting") if item.lower() == value.lower()),
                None,
            )
            if canonical is None:
                issues.append(
                    PresentationIssue(
                        "READER-QUALIFIER-VALUE",
                        line_number,
                        "Reader exception qualifier must be Inferred, Unknown, or Conflicting",
                    )
                )
                continue
            if canonical == "Confirmed":
                issues.append(
                    PresentationIssue(
                        "READER-CONFIRMED-QUALIFIER",
                        line_number,
                        "Confirmed is the Reader baseline and must not be repeated as a qualifier",
                    )
                )
            elif qualifier.group(0) != schema["exception_qualifiers"][canonical]:
                issues.append(
                    PresentationIssue(
                        "READER-QUALIFIER-FORM",
                        line_number,
                        f"use the exact qualifier {schema['exception_qualifiers'][canonical]}",
                    )
                )

    citations = [
        (line_number, match)
        for line_number, line in visible_lines
        for match in SOURCE_CITATION_RE.finditer(line)
    ]
    if definition["audience"] == "ba":
        source_headings = {
            title.lower() for level, title, _line in structure.headings if level >= 2
        }
        accepted = {item.lower() for item in schema["source_notes"]["accepted_heading_text"]}
        if source_headings & accepted:
            issues.append(
                PresentationIssue("READER-BA-SOURCE-NOTES", 1, "BA Reader artifacts must not publish Source Notes")
            )
        for line_number, _match in citations:
            issues.append(
                PresentationIssue(
                    "READER-BA-SOURCE-CITATION",
                    line_number,
                    "BA Reader artifacts trace through Scenarios and Tech Behaviors, not repository source citations",
                )
            )
    elif definition.get("source_notes"):
        accepted = {item.lower() for item in schema["source_notes"]["accepted_heading_text"]}
        source_heading_lines = [
            line for level, title, line in structure.headings if level >= 2 and title.lower() in accepted
        ]
        if not source_heading_lines:
            issues.append(PresentationIssue("READER-SOURCE-NOTES-MISSING", 1, "Tech Reader artifact must contain a Source notes section"))
        marker_uses: dict[str, list[int]] = {}
        for line_number, line in visible_lines:
            for match in MARKER_LINK_RE.finditer(line):
                label = match.group("label").lower()
                anchor = match.group("anchor").lower()
                if label != anchor:
                    issues.append(PresentationIssue("READER-SOURCE-MARKER", line_number, "Source Note marker label and anchor must match"))
                marker_uses.setdefault(anchor, []).append(line_number)
        definitions = _definition_blocks(visible_lines)
        invalid_definition = definitions.pop(next((key for key in definitions if key.startswith("invalid:")), ""), None)
        if invalid_definition:
            issues.append(PresentationIssue("READER-SOURCE-DEFINITION", invalid_definition[0], "Source Note definition label and anchor must match"))
        if not marker_uses:
            issues.append(PresentationIssue("READER-SOURCE-MARKER-MISSING", 1, "Tech Reader artifact must use at least one grouped [E#](#e#) marker"))
        for marker, use_lines in sorted(marker_uses.items()):
            if marker not in definitions:
                issues.append(PresentationIssue("READER-SOURCE-UNDEFINED", use_lines[0], f"Source Note marker {marker.upper()} has no definition"))
        definition_lines = {
            line_number
            for _marker, (_start, _block, lines) in definitions.items()
            for line_number in lines
        }
        for citation_line, _match in citations:
            if citation_line not in definition_lines:
                issues.append(
                    PresentationIssue(
                        "READER-INLINE-SOURCE-CITATION",
                        citation_line,
                        "Tech Reader source citations belong in Source Notes; use a grouped [E#](#e#) marker in the body",
                    )
                )
        for marker, (line_number, block, _block_lines) in sorted(definitions.items()):
            if marker not in marker_uses:
                issues.append(PresentationIssue("READER-SOURCE-UNUSED", line_number, f"Source Note {marker.upper()} is not referenced by Reader content"))
            block_citations = list(SOURCE_CITATION_RE.finditer(block))
            if not block_citations:
                issues.append(PresentationIssue("READER-SOURCE-CITATION-MISSING", line_number, f"Source Note {marker.upper()} must cite repository source"))
            elif repo is not None:
                for match in block_citations:
                    citation_issue = _validate_citation(match, repo, line_number)
                    if citation_issue:
                        issues.append(citation_issue)

    # Do not turn density into a content metric.  This validator deliberately has
    # no minimum markers per row and no Confirmed-word frequency check.
    del root
    return artifact_type, issues[:max_issues]


def reader_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for directory in (root / "tech-pack", root / "ba-pack"):
        if directory.is_dir():
            result.extend(path for path in directory.rglob("*.md") if path.is_file())
    return sorted(result)


def validate_bundled_reader_contract(
    registry: Any,
    *,
    assets_root: Path,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    schema = load_reader_presentation_schema(schema_path or assets_root / "reader-presentation-schema.json")
    errors: list[str] = []
    for artifact_type, expected in schema["affected_artifacts"].items():
        definition = registry.definitions.get(artifact_type)
        if definition is None:
            errors.append(f"Reader schema references unknown artifact type: {artifact_type}")
            continue
        if definition.current_version != expected["version"]:
            errors.append(
                f"Reader schema/registry version mismatch for {artifact_type}: "
                f"{expected['version']} != {definition.current_version}"
            )
        if not definition.template:
            errors.append(f"Reader artifact has no template: {artifact_type}")
            continue
        template = assets_root / definition.template
        if not template.is_file():
            errors.append(f"Reader template does not exist: {definition.template}")
            continue
        structure = parse_markdown(template.read_text(encoding="utf-8"))
        if structure.issues:
            errors.append(f"Reader template Markdown is invalid: {definition.template}")
            continue
        if scalar_value(structure.frontmatter, "artifact_type") != artifact_type:
            errors.append(f"Reader template artifact_type mismatch: {definition.template}")
        if scalar_value(structure.frontmatter, "artifact_schema_version") != expected["version"]:
            errors.append(f"Reader template version mismatch: {definition.template}")
        forbidden = set(schema["forbidden_table_headers"])
        for table in structure.tables:
            overlap = forbidden.intersection(table.headers)
            if overlap:
                errors.append(
                    f"Reader template {definition.template} has forbidden table header(s): "
                    + ", ".join(sorted(overlap))
                )
        _artifact_type, presentation_issues = validate_reader_document(
            template,
            root=assets_root,
            repo=None,
            schema=schema,
        )
        errors.extend(
            f"Reader template {definition.template}: {issue.code}: {issue.message}"
            for issue in presentation_issues
        )
    if errors:
        raise ReaderPresentationError("; ".join(errors))
    return schema
