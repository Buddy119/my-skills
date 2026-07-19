#!/usr/bin/env python3
"""Validate an endpoint-level API contract, evidence, and behavior backlink."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from markdown_structure import (
    load_api_contract_structure,
    parse_markdown,
    section_ranges,
    validate_api_contract_tables,
)


REQUIRED_KEYS = {
    "artifact_type",
    "artifact_schema_version",
    "behavior_id",
    "endpoint_id",
    "title",
    "repository",
    "source_commit",
    "entry_point",
    "method",
    "route",
    "contract_status",
    "application_route_status",
    "external_reachability_status",
    "behavior_document",
    "endpoint_matrix",
}

REQUIRED_HEADINGS = {
    "Quick reference",
    "Request",
    "Responses",
    "Related documents",
    "Source notes",
}

ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
ALLOWED_ENDPOINT_STATUSES = {"Confirmed", "Conflicting", "Unknown", "Not observed"}
EVIDENCE_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?`"
)
EVIDENCE_MARKER_RE = re.compile(r"\[(?P<label>E\d+)\]\(#(?P<anchor>e\d+)\)", re.I)
SOURCE_NOTE_RE = re.compile(
    r"<a\s+(?:id|name)=[\"'](?P<anchor>e\d+)[\"']\s*></a>\s*"
    r"(?:\*\*)?(?P<label>E\d+)(?:\*\*)?",
    re.I,
)
JSON_BLOCK_RE = re.compile(
    r"^```json[ \t]*\n(?P<content>.*?)^```[ \t]*$",
    re.M | re.S,
)
COMPLETE_FIELD_HEADERS = (
    "Location",
    "Field path",
    "Type/format",
    "Required or present when",
    "Nullable",
    "Default",
    "Rules",
    "Basis",
)
ALLOWED_COMPLETE_LOCATIONS = {"Header", "Path", "Query", "Body", "Response"}
ALLOWED_FIELD_BASES = {"Executable", "Schema only", "Shared or opaque", "Conflict"}


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("YAML frontmatter is not closed with ---")
    return text[4:end], text[end + 5 :]


def top_level_keys(frontmatter: str) -> set[str]:
    return {
        match.group(1)
        for line in frontmatter.splitlines()
        if line and not line[0].isspace()
        if (match := re.match(r"([A-Za-z_][A-Za-z0-9_-]*):", line))
    }


def scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def yaml_block(frontmatter: str, key: str) -> tuple[str, str]:
    match = re.search(
        rf"^{re.escape(key)}:[ \t]*(?P<inline>[^\n]*)\n(?P<body>(?:[ \t]+[^\n]*(?:\n|$))*)",
        frontmatter,
        re.M,
    )
    if not match:
        return "", ""
    return match.group("inline").strip(), match.group("body")


def section_value(body: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<content>.*?)(?=^##\s+|\Z)",
        body,
        re.M | re.S,
    )
    return match.group("content") if match else ""


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def endpoint_status(cell: str) -> str | None:
    found = [
        status
        for status in ALLOWED_ENDPOINT_STATUSES
        if re.search(rf"\b{re.escape(status)}\b", cell)
    ]
    return found[0] if len(found) == 1 else None


def _plain_field(value: str) -> str:
    return value.strip().strip("`").strip().lower()


def _heading_context(structure: object, line: int) -> str | None:
    headings = getattr(structure, "headings", ())
    candidates = [
        title
        for level, title, heading_line in headings
        if level == 3 and heading_line < line
    ]
    return candidates[-1] if candidates else None


def validate_progressive_field_reference(structure: object) -> list[str]:
    """Keep caller-first and remaining Schema fields mutually exclusive.

    This is intentionally a referential check.  It does not decide whether a
    field is important enough for the caller-first section or whether all Schema
    fields were semantically reconstructed.
    """

    errors: list[str] = []
    ranges = section_ranges(structure)  # type: ignore[arg-type]
    core: set[tuple[str, str]] = set()
    complete: set[tuple[str, str]] = set()
    complete_tables = []
    request_range = ranges.get("Request")
    response_range = ranges.get("Responses")
    detail_range = ranges.get("Complete field reference")
    for table in getattr(structure, "tables", ()):
        if request_range and request_range[0] < table.start_line <= request_range[1]:
            context = _heading_context(structure, table.start_line)
            if table.headers and table.headers[0] == "Header":
                location = "Header"
            elif table.headers and table.headers[0] == "Field path":
                location = "Body"
            elif table.headers and table.headers[0] == "Field":
                location = "Path" if context == "Path parameters" else "Query" if context == "Query parameters" else "Unknown"
            else:
                continue
            for row in table.rows:
                if row and _plain_field(row[0]):
                    core.add((location.lower(), _plain_field(row[0])))
        elif response_range and response_range[0] < table.start_line <= response_range[1]:
            if table.headers and table.headers[0] == "Field path":
                for row in table.rows:
                    if row and _plain_field(row[0]):
                        core.add(("response", _plain_field(row[0])))
        elif detail_range and detail_range[0] < table.start_line <= detail_range[1]:
            if table.headers != COMPLETE_FIELD_HEADERS:
                continue
            complete_tables.append(table)
            for row in table.rows:
                location = row[0].strip()
                field = _plain_field(row[1])
                basis = row[7].strip()
                if location not in ALLOWED_COMPLETE_LOCATIONS:
                    errors.append(
                        f"Complete field reference has invalid Location {location!r}; use Header, Path, Query, Body, or Response"
                    )
                if basis not in ALLOWED_FIELD_BASES:
                    errors.append(
                        f"Complete field reference has invalid Basis {basis!r}; use Executable, Schema only, Shared or opaque, or Conflict"
                    )
                identity = (location.lower(), field)
                if identity in complete:
                    errors.append(
                        f"Complete field reference repeats field identity: {location} {row[1]}"
                    )
                complete.add(identity)
    if detail_range and not complete_tables:
        errors.append("Complete field reference must use the registered field-reference table")
    for location, field in sorted(core & complete):
        errors.append(
            f"caller-first and Complete field reference sections duplicate field identity: {location} {field}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    if not args.document.is_file():
        print(f"ERROR: document does not exist: {args.document}")
        return 2
    if not args.repo.is_dir():
        print(f"ERROR: repository directory does not exist: {args.repo}")
        return 2

    text = args.document.read_text(encoding="utf-8")
    structure = parse_markdown(text)
    if structure.issues:
        for issue in structure.issues:
            print(f"ERROR [{issue.code}] line {issue.line}: {issue.message}")
        print("SKIPPED [API-CONTRACT-SEMANTICS] prerequisite Markdown structure is invalid")
        return 1
    try:
        frontmatter, body = split_frontmatter(text)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    missing_keys = sorted(REQUIRED_KEYS - top_level_keys(frontmatter))
    if missing_keys:
        errors.append("missing YAML keys: " + ", ".join(missing_keys))

    if scalar_value(frontmatter, "artifact_type") != "api-contract":
        errors.append("artifact_type must be api-contract")
    if scalar_value(frontmatter, "artifact_schema_version") != "3":
        errors.append("api-contract artifact_schema_version must be 3")

    try:
        structure_schema = load_api_contract_structure(
            Path(__file__).resolve().parent.parent / "assets" / "api-contract-structure.json"
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"API Contract structure schema is invalid: {exc}")
    else:
        errors.extend(
            f"[{issue.code}] line {issue.line}: {issue.message}"
            for issue in validate_api_contract_tables(structure, structure_schema)
        )
        errors.extend(validate_progressive_field_reference(structure))

    status = scalar_value(frontmatter, "contract_status")
    if status not in ALLOWED_STATUSES:
        errors.append("contract_status must be Confirmed, Inferred, Conflicting, or Unknown")

    application_route_status = scalar_value(frontmatter, "application_route_status")
    if application_route_status != "Confirmed":
        errors.append("a full API contract requires application_route_status: Confirmed")

    reachability_status = scalar_value(frontmatter, "external_reachability_status")
    if reachability_status not in ALLOWED_ENDPOINT_STATUSES:
        errors.append(
            "external_reachability_status must be Confirmed, Conflicting, Unknown, or Not observed"
        )

    endpoint_id = scalar_value(frontmatter, "endpoint_id")
    if endpoint_id:
        expected_name = f"{endpoint_id}.api-contract.md"
        if args.document.name != expected_name:
            errors.append(f"contract filename must match endpoint_id: {expected_name}")

    headings = set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))
    missing_headings = sorted(REQUIRED_HEADINGS - headings)
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))

    behavior_document = scalar_value(frontmatter, "behavior_document")
    if not behavior_document or behavior_document.lower() in {"null", "none"}:
        errors.append("behavior_document must point to the related behavior document")
    else:
        behavior_path = (args.document.parent / behavior_document).resolve()
        if not behavior_path.is_file():
            errors.append(f"linked behavior document does not exist: {behavior_document}")
        else:
            try:
                behavior_frontmatter, _ = split_frontmatter(behavior_path.read_text(encoding="utf-8"))
            except ValueError as exc:
                errors.append(f"linked behavior document is invalid: {exc}")
            else:
                if scalar_value(frontmatter, "behavior_id") != scalar_value(behavior_frontmatter, "behavior_id"):
                    errors.append("contract and behavior document must have the same behavior_id")
                _, api_block = yaml_block(behavior_frontmatter, "api_contracts")
                expected_document = (Path("../contracts") / args.document.name).as_posix()
                if not endpoint_id or not re.search(
                    rf"^\s*-\s+endpoint_id:\s*[\"']?{re.escape(endpoint_id)}[\"']?\s*$",
                    api_block,
                    re.M,
                ):
                    errors.append("linked behavior api_contracts must contain this endpoint_id")
                if not re.search(
                    rf"^\s+document:\s*[\"']?{re.escape(expected_document)}[\"']?\s*$",
                    api_block,
                    re.M,
                ):
                    errors.append("linked behavior api_contracts must point to this contract document")
        if not re.search(rf"\]\({re.escape(behavior_document)}\)", body):
            errors.append("contract body must contain a Markdown link matching behavior_document")

    endpoint_matrix = scalar_value(frontmatter, "endpoint_matrix")
    if not endpoint_matrix or endpoint_matrix.lower() in {"null", "none"}:
        errors.append("endpoint_matrix must point to this endpoint's Matrix section")
    else:
        matrix_parts = endpoint_matrix.split("#", 1)
        matrix_document = matrix_parts[0]
        matrix_anchor = matrix_parts[1] if len(matrix_parts) == 2 else ""
        matrix_path = (args.document.parent / matrix_document).resolve()
        if not matrix_path.is_file():
            errors.append(f"linked Endpoint Matrix does not exist: {matrix_document}")
        else:
            matrix_text = matrix_path.read_text(encoding="utf-8")
            summary = section_value(matrix_text, "Endpoint summary")
            matching_row: list[str] | None = None
            for line in summary.splitlines():
                if not line.strip().startswith("|"):
                    continue
                cells = table_cells(line)
                if cells and endpoint_id and cells[0].strip("` ") == endpoint_id:
                    matching_row = cells
                    break
            if matching_row is None:
                errors.append("Endpoint Matrix does not contain this endpoint_id summary row")
            elif len(matching_row) < 9:
                errors.append("Endpoint Matrix summary row is incomplete")
            else:
                matrix_operation_role = matching_row[1].strip("` ")
                matrix_application_status = endpoint_status(matching_row[2])
                matrix_reachability_status = endpoint_status(matching_row[6])
                if matrix_operation_role != "application-endpoint":
                    errors.append("API Contract Matrix row must be an application-endpoint")
                if matrix_application_status != application_route_status:
                    errors.append("application_route_status does not match Endpoint Matrix")
                if matrix_reachability_status != reachability_status:
                    errors.append("external_reachability_status does not match Endpoint Matrix")
            if not matrix_anchor:
                errors.append("endpoint_matrix must include the endpoint detail anchor")
            elif not re.search(
                rf"<a\s+(?:id|name)=[\"']{re.escape(matrix_anchor)}[\"']\s*></a>",
                matrix_text,
                re.I,
            ):
                errors.append("Endpoint Matrix does not define the linked endpoint detail anchor")
        if not re.search(rf"\]\({re.escape(endpoint_matrix)}\)", body):
            errors.append("contract body must contain a Markdown link matching endpoint_matrix")

    source_notes = section_value(body, "Source notes")
    markers = list(EVIDENCE_MARKER_RE.finditer(body))
    note_matches = list(SOURCE_NOTE_RE.finditer(source_notes))
    note_definitions: dict[str, str] = {}
    for match in note_matches:
        anchor = match.group("anchor").lower()
        label = match.group("label").lower()
        if anchor != label:
            errors.append(f"Source note label and anchor do not match: {label} -> #{anchor}")
        if anchor in note_definitions:
            errors.append(f"duplicate Source note anchor: {anchor}")
        note_definitions[anchor] = label

    if not markers:
        errors.append("no compact evidence markers found; use [E1](#e1)")
    for marker in markers:
        label = marker.group("label").lower()
        anchor = marker.group("anchor").lower()
        if label != anchor:
            errors.append(f"evidence marker label and anchor do not match: {label} -> #{anchor}")
        if anchor not in note_definitions:
            errors.append(f"evidence marker has no Source note definition: #{anchor}")

    citations = list(EVIDENCE_RE.finditer(source_notes))
    if not citations:
        errors.append("Source notes contain no source citations; use `relative/path.ext:line`")

    checked: set[tuple[str, int, int | None]] = set()
    for match in citations:
        relative = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end")) if match.group("end") else None
        key = (relative, start, end)
        if key in checked:
            continue
        checked.add(key)
        source = args.repo / relative
        if not source.is_file():
            errors.append(f"cited file does not exist: {relative}")
            continue
        if end is not None and end < start:
            errors.append(f"invalid line range: {relative}:{start}-{end}")
            continue
        try:
            line_count = sum(1 for _ in source.open(encoding="utf-8", errors="replace"))
        except OSError as exc:
            errors.append(f"cannot read cited file {relative}: {exc}")
            continue
        final_line = end or start
        if start < 1 or final_line > line_count:
            errors.append(
                f"citation outside file bounds: {relative}:{start}" + (f"-{end}" if end else "")
            )

    json_blocks = list(JSON_BLOCK_RE.finditer(body))
    for index, block in enumerate(json_blocks, start=1):
        try:
            json.loads(block.group("content"))
        except json.JSONDecodeError as exc:
            errors.append(
                f"JSON example {index} is invalid at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            )

    placeholders = (
        "TODO",
        "TEMPLATE:",
        "path/to/",
        "repository.behavior-name",
        "repository.method-route",
        "Human-readable API contract title",
        "METHOD /normalized/path",
        "Header-Name",
        "2xx/4xx/5xx",
        "supported-or-clearly-illustrative-value",
        "supported-value",
        "SUPPORTED_ERROR_CODE",
    )
    if any(placeholder in text for placeholder in placeholders):
        errors.append("template placeholders remain in the document")

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    print(
        f"OK: endpoint {endpoint_id}, {len(markers)} evidence marker(s), "
        f"{len(citations)} source citation(s), {len(json_blocks)} JSON example(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
