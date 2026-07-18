#!/usr/bin/env python3
"""Mechanical Markdown structure checks shared by Knowledge Pack validators.

The parser intentionally validates only syntax that the Skill publishes: YAML
frontmatter boundaries, heading hierarchy, fenced code blocks, explicit HTML
anchors, and pipe tables.  It does not judge prose, evidence quality, or business
meaning.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FENCE_RE = re.compile(r"^\s*(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
ANCHOR_RE = re.compile(r"<a\s+(?:id|name)=[\"'](?P<anchor>[^\"']+)[\"']\s*></a>", re.I)
DELIMITER_CELL_RE = re.compile(r"^:?-{3,}:?$")


@dataclass(frozen=True)
class MarkdownIssue:
    code: str
    line: int
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "line": self.line, "message": self.message}


@dataclass(frozen=True)
class MarkdownTable:
    start_line: int
    end_line: int
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class MarkdownStructure:
    frontmatter: str
    body: str
    headings: tuple[tuple[int, str, int], ...]
    tables: tuple[MarkdownTable, ...]
    issues: tuple[MarkdownIssue, ...]


def split_frontmatter(text: str) -> tuple[str, str, int]:
    if not text.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("YAML frontmatter is not closed with ---")
    frontmatter = text[4:end]
    body = text[end + 5 :]
    body_start_line = text[: end + 5].count("\n") + 1
    return frontmatter, body, body_start_line


def _structural_pipe_count(line: str) -> int:
    escaped = False
    code_ticks = 0
    count = 0
    index = 0
    while index < len(line):
        char = line[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if char == "\\":
            escaped = True
            index += 1
            continue
        if char == "`":
            run = 1
            while index + run < len(line) and line[index + run] == "`":
                run += 1
            if code_ticks == 0:
                code_ticks = run
            elif code_ticks == run:
                code_ticks = 0
            index += run
            continue
        if char == "|" and code_ticks == 0:
            count += 1
        index += 1
    return count


def _is_table_row(line: str) -> bool:
    return _structural_pipe_count(line) > 0


def _is_table_start(lines: list[str], index: int) -> bool:
    stripped = lines[index].strip()
    if not _is_table_row(lines[index]):
        return False
    if stripped.startswith("|") or stripped.endswith("|"):
        return True
    if index + 1 >= len(lines) or not _is_table_row(lines[index + 1]):
        return False
    delimiter = split_table_row(lines[index + 1])
    return bool(delimiter) and all(re.fullmatch(r":?-+:?", cell) for cell in delimiter)


def split_table_row(line: str) -> list[str]:
    """Split a Skill-style pipe row, ignoring escaped and inline-code pipes."""

    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    code_ticks = 0
    index = 0
    while index < len(stripped):
        char = stripped[index]
        if escaped:
            current.append(char)
            escaped = False
            index += 1
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            index += 1
            continue
        if char == "`":
            run = 1
            while index + run < len(stripped) and stripped[index + run] == "`":
                run += 1
            if code_ticks == 0:
                code_ticks = run
            elif code_ticks == run:
                code_ticks = 0
            current.extend("`" * run)
            index += run
            continue
        if char == "|" and code_ticks == 0:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    cells.append("".join(current).strip())
    return cells


def _table_issues(lines: list[str], start: int, base_line: int) -> tuple[list[MarkdownIssue], MarkdownTable | None]:
    issues: list[MarkdownIssue] = []
    block: list[str] = []
    index = start
    while index < len(lines) and _is_table_row(lines[index]):
        block.append(lines[index])
        index += 1
    line_number = base_line + start
    if len(block) < 2:
        return [MarkdownIssue("MD-TABLE-ORPHAN", line_number, "pipe row is not a complete Markdown table")], None

    rows = [split_table_row(line) for line in block]
    width = len(rows[0])
    if width == 0:
        issues.append(MarkdownIssue("MD-TABLE-EMPTY", line_number, "table header has no columns"))
    delimiter = rows[1]
    if len(delimiter) != width or not all(DELIMITER_CELL_RE.fullmatch(cell) for cell in delimiter):
        issues.append(
            MarkdownIssue(
                "MD-TABLE-DELIMITER",
                line_number + 1,
                "second table row must contain one valid --- delimiter per header column",
            )
        )
    for offset, row in enumerate(rows[2:], start=2):
        if len(row) != width:
            issues.append(
                MarkdownIssue(
                    "MD-TABLE-WIDTH",
                    line_number + offset,
                    f"table row has {len(row)} columns; expected {width}",
                )
            )
    if issues:
        return issues, None
    return (
        [],
        MarkdownTable(
            start_line=line_number,
            end_line=line_number + len(block) - 1,
            headers=tuple(rows[0]),
            rows=tuple(tuple(row) for row in rows[2:]),
        ),
    )


def parse_markdown(text: str, *, max_issues: int = 10) -> MarkdownStructure:
    issues: list[MarkdownIssue] = []
    try:
        frontmatter, body, body_start = split_frontmatter(text)
    except ValueError as exc:
        return MarkdownStructure("", text, (), (), (MarkdownIssue("MD-FRONTMATTER", 1, str(exc)),))

    lines = body.splitlines()
    headings: list[tuple[int, str, int]] = []
    tables: list[MarkdownTable] = []
    anchors: dict[str, int] = {}
    fence_marker: str | None = None
    fence_line = 0
    previous_heading_level = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        absolute_line = body_start + index
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group("marker")
            if fence_marker is None:
                fence_marker = marker
                fence_line = absolute_line
            elif marker[0] == fence_marker[0] and len(marker) >= len(fence_marker):
                fence_marker = None
            index += 1
            continue
        if fence_marker is not None:
            index += 1
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group("marks"))
            title = heading.group("title").strip()
            headings.append((level, title, absolute_line))
            if previous_heading_level and level > previous_heading_level + 1:
                issues.append(
                    MarkdownIssue(
                        "MD-HEADING-JUMP",
                        absolute_line,
                        f"heading level jumps from H{previous_heading_level} to H{level}",
                    )
                )
            previous_heading_level = level

        for anchor in ANCHOR_RE.finditer(line):
            identifier = anchor.group("anchor")
            if identifier in anchors:
                issues.append(
                    MarkdownIssue(
                        "MD-ANCHOR-DUPLICATE",
                        absolute_line,
                        f"explicit anchor '{identifier}' duplicates line {anchors[identifier]}",
                    )
                )
            else:
                anchors[identifier] = absolute_line

        if _is_table_start(lines, index):
            table_issues, table = _table_issues(lines, index, body_start)
            issues.extend(table_issues)
            block_length = 1
            while index + block_length < len(lines) and _is_table_row(lines[index + block_length]):
                block_length += 1
            if table is not None:
                tables.append(table)
            index += block_length
        else:
            index += 1

        if len(issues) >= max_issues:
            break

    if fence_marker is not None and len(issues) < max_issues:
        issues.append(MarkdownIssue("MD-FENCE-UNCLOSED", fence_line, "fenced code block is not closed"))
    h1 = [item for item in headings if item[0] == 1]
    if not h1 and len(issues) < max_issues:
        issues.append(MarkdownIssue("MD-H1-MISSING", body_start, "document body must contain one H1 heading"))
    elif len(h1) > 1 and len(issues) < max_issues:
        issues.append(MarkdownIssue("MD-H1-MULTIPLE", h1[1][2], "document body must contain only one H1 heading"))

    return MarkdownStructure(
        frontmatter=frontmatter,
        body=body,
        headings=tuple(headings),
        tables=tuple(tables),
        issues=tuple(issues[:max_issues]),
    )


def load_api_contract_structure(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("api_contract_structure_schema_version") != "1":
        raise ValueError("unsupported API Contract structure schema version")
    return payload


def section_ranges(structure: MarkdownStructure) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    h2 = [item for item in structure.headings if item[0] == 2]
    for index, (_level, title, line) in enumerate(h2):
        end = h2[index + 1][2] - 1 if index + 1 < len(h2) else 10**9
        result[title] = (line, end)
    return result


def validate_api_contract_tables(
    structure: MarkdownStructure,
    schema: dict[str, Any],
) -> list[MarkdownIssue]:
    issues: list[MarkdownIssue] = []
    ranges = section_ranges(structure)
    definitions = schema.get("tables", {})
    for name, definition in definitions.items():
        section = definition["section"]
        expected = tuple(definition["headers"])
        required = bool(definition.get("required", False))
        section_range = ranges.get(section)
        matching = []
        if section_range:
            matching = [
                table
                for table in structure.tables
                if section_range[0] < table.start_line <= section_range[1]
                and table.headers == expected
            ]
        if required and not matching:
            issues.append(
                MarkdownIssue(
                    "API-TABLE-MISSING",
                    section_range[0] if section_range else 1,
                    f"{name} must contain table headers: {' | '.join(expected)}",
                )
            )

    for section in ("Request", "Responses"):
        section_range = ranges.get(section)
        if not section_range:
            continue
        allowed = {
            tuple(definition["headers"])
            for definition in definitions.values()
            if definition.get("section") == section
        }
        for table in structure.tables:
            if (
                section_range[0] < table.start_line <= section_range[1]
                and table.headers not in allowed
            ):
                issues.append(
                    MarkdownIssue(
                        "API-TABLE-HEADERS",
                        table.start_line,
                        f"{section} table headers do not match the API Contract structure schema",
                    )
                )
    return issues
