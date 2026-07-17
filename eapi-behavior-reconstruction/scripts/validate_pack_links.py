#!/usr/bin/env python3
"""Validate local Markdown links and final Tech catalog document paths."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")
CATALOG_PATH_RE = re.compile(
    r"^\s*(?:document|ba_document):\s*[\"']?(?P<target>[^\"'\n#]+?)[\"']?\s*$", re.M
)
PLACEHOLDERS = (
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
ENDPOINT_STATUSES = {"Confirmed", "Conflicting", "Unknown", "Not observed"}
ENDPOINT_ROLES = {
    "application-endpoint",
    "meaningful-external-exposure",
    "protocol-support",
    "unresolved",
}
ENDPOINT_HEADERS = [
    "Endpoint or Exposure ID",
    "Operation Role",
    "Application Route",
    "External Entry Declaration",
    "Environment Deployment Intent",
    "Observed Runtime Deployment",
    "External Reachability",
    "Behavior",
    "Contract",
]
CALL_ID_RE = re.compile(r"HTTP-\d+")
USAGE_ID_RE = re.compile(r"HTTP-\d+-U\d+")
MAPPING_ID_RE = re.compile(r"FM-\d+")
FIELD_OPERATION_HEADERS = [
    "Call ID",
    "Method and Logical Target",
    "Client Operation",
    "Observable Purpose",
    "Related Behaviors",
    "Status",
    "Details",
]
FIELD_USAGE_HEADERS = [
    "Usage ID",
    "Behavior",
    "Executable Call Site",
    "Invocation Condition or Config",
    "Status",
    "Evidence",
]
FIELD_MAPPING_HEADERS = [
    "Mapping ID",
    "Applies to Usage(s)",
    "Source Field(s)",
    "Target Field(s)",
    "Transformation",
    "Condition/Default",
    "Lossy",
    "Status",
    "Evidence",
]
REGISTER_OPERATION_HEADERS = [
    "Call ID",
    "Method",
    "Logical Target",
    "Client Operation",
    "Observable Purpose",
    "Related Behaviors",
    "Aliases",
    "Status",
    "Evidence",
]
REGISTER_USAGE_HEADERS = [
    "Usage ID",
    "Call ID",
    "Behavior ID",
    "Executable Call Site",
    "Invocation Condition or Config",
    "Status",
    "Evidence",
]
REGISTER_MAPPING_HEADERS = [
    "Mapping ID",
    "Call ID",
    "Applies to Usage(s)",
    "Direction",
    "Source Field(s)",
    "Target Field(s)",
    "Transformation",
    "Condition/Default",
    "Lossy",
    "Status",
    "Evidence",
]


def local_target(raw: str) -> str | None:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    return unquote(target) if target else None


def within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def section_value(body: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<content>.*?)(?=^##\s+|\Z)",
        body,
        re.M | re.S,
    )
    return match.group("content") if match else ""


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def table_in_section(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    section = section_value(text, heading)
    rows = [table_cells(line) for line in section.splitlines() if line.strip().startswith("|")]
    if not rows:
        return [], []
    return rows[0], [row for row in rows[1:] if not is_separator_row(row)]


def code_value(cell: str) -> str:
    return cell.strip().strip("` ")


def yaml_block(frontmatter: str, key: str) -> str:
    match = re.search(
        rf"^{re.escape(key)}:[ \t]*(?:[^\n]*)\n(?P<body>(?:[ \t]+[^\n]*(?:\n|$))*)",
        frontmatter,
        re.M,
    )
    return match.group("body") if match else ""


def endpoint_status(cell: str) -> str | None:
    found = [status for status in ENDPOINT_STATUSES if re.search(rf"\b{re.escape(status)}\b", cell)]
    return found[0] if len(found) == 1 else None


def endpoint_anchor(identifier: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", identifier.lower()).strip("-")


def scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def validate_endpoint_matrix(matrix: Path, root: Path, errors: list[str]) -> None:
    text = matrix.read_text(encoding="utf-8")
    summary = section_value(text, "Endpoint summary")
    protocol_summary = section_value(text, "Protocol-support summary")
    rows = [table_cells(line) for line in summary.splitlines() if line.strip().startswith("|")]
    if not rows:
        errors.append("Endpoint Matrix is missing the Endpoint summary table")
        return
    if rows[0] != ENDPOINT_HEADERS:
        errors.append("Endpoint Matrix summary columns do not match the layered endpoint model")
        return

    data_rows = [row for row in rows[1:] if not is_separator_row(row)]
    if not data_rows and not protocol_summary:
        errors.append("Endpoint Matrix has neither endpoint rows nor a protocol-support summary")

    identifiers: set[str] = set()
    for row in data_rows:
        if len(row) != len(ENDPOINT_HEADERS):
            errors.append("Endpoint Matrix summary row has the wrong number of columns")
            continue
        identifier = row[0].strip("` ")
        if not identifier:
            errors.append("Endpoint Matrix row is missing an endpoint or exposure ID")
            continue
        if identifier in identifiers:
            errors.append(f"duplicate Endpoint Matrix ID: {identifier}")
        identifiers.add(identifier)
        anchor = endpoint_anchor(identifier)
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(anchor)}[\"']\s*></a>",
            text,
            re.I,
        ):
            errors.append(f"Endpoint Matrix is missing the stable detail anchor for {identifier}")

        operation_role = row[1].strip("` ")
        if operation_role not in ENDPOINT_ROLES:
            errors.append(f"Endpoint Matrix {identifier} has an invalid Operation Role")

        statuses = [endpoint_status(cell) for cell in row[2:7]]
        if any(status is None for status in statuses):
            errors.append(f"Endpoint Matrix {identifier} has an invalid or ambiguous layer status")
            continue
        if statuses[0] == "Confirmed" and operation_role != "application-endpoint":
            errors.append(
                f"Confirmed Application Route is not classified as application-endpoint: {identifier}"
            )
        if statuses[0] == "Confirmed":
            if not re.search(r"\[[^\]]+\]\([^)]+\)", row[7]):
                errors.append(f"confirmed application endpoint lacks a Behavior link: {identifier}")
            if not re.search(r"\[[^\]]+\]\([^)]+\.api-contract\.md\)", row[8]):
                errors.append(f"confirmed application endpoint lacks an API Contract link: {identifier}")

    if protocol_summary and not re.search(
        r"\[[^\]]+\]\([^)]*\.work/repository-register\.md(?:#[^)]+)?\)",
        protocol_summary,
    ):
        errors.append(
            "Endpoint Matrix Protocol-support summary does not link the repository register"
        )

    contracts_dir = root / "tech-pack" / "contracts"
    if contracts_dir.is_dir():
        for contract in sorted(contracts_dir.glob("*.api-contract.md")):
            contract_text = contract.read_text(encoding="utf-8")
            if not contract_text.startswith("---\n"):
                continue
            end = contract_text.find("\n---\n", 4)
            if end == -1:
                continue
            endpoint_id = scalar_value(contract_text[4:end], "endpoint_id")
            if endpoint_id and endpoint_id not in identifiers:
                errors.append(f"API Contract endpoint_id is missing from Endpoint Matrix: {endpoint_id}")
            expected_link = f"contracts/{contract.name}"
            if expected_link not in text:
                errors.append(f"Endpoint Matrix does not link API Contract: {contract.name}")


def validate_http_register(
    register: Path, errors: list[str]
) -> tuple[set[str], dict[str, set[str]], dict[str, str], dict[str, str]]:
    call_ids: set[str] = set()
    usages_by_call: dict[str, set[str]] = {}
    usage_to_call: dict[str, str] = {}
    mapping_directions: dict[str, str] = {}
    if not register.is_file():
        return call_ids, usages_by_call, usage_to_call, mapping_directions

    text = register.read_text(encoding="utf-8")
    if section_value(text, "Proven outbound HTTP calls and mappings"):
        errors.append("repository register still uses the legacy flattened outbound HTTP table")

    operation_header, operation_rows = table_in_section(text, "Outbound HTTP operation records")
    usage_header, usage_rows = table_in_section(text, "Outbound HTTP operation usages")
    mapping_header, mapping_rows = table_in_section(text, "External HTTP field mapping records")

    if operation_header and operation_header != REGISTER_OPERATION_HEADERS:
        errors.append("repository register outbound operation columns are invalid")
    if usage_header and usage_header != REGISTER_USAGE_HEADERS:
        errors.append("repository register outbound usage columns are invalid")
    if mapping_header and mapping_header != REGISTER_MAPPING_HEADERS:
        errors.append("repository register outbound mapping columns are invalid")

    for row in operation_rows:
        if len(row) != len(REGISTER_OPERATION_HEADERS):
            errors.append("repository register outbound operation row has the wrong number of columns")
            continue
        call_id = code_value(row[0])
        if not CALL_ID_RE.fullmatch(call_id):
            errors.append(f"invalid outbound Call ID in repository register: {call_id or '<empty>'}")
            continue
        if call_id in call_ids:
            errors.append(f"duplicate outbound Call ID in repository register: {call_id}")
        call_ids.add(call_id)
        usages_by_call.setdefault(call_id, set())

    for row in usage_rows:
        if len(row) != len(REGISTER_USAGE_HEADERS):
            errors.append("repository register outbound usage row has the wrong number of columns")
            continue
        usage_id = code_value(row[0])
        call_id = code_value(row[1])
        if not USAGE_ID_RE.fullmatch(usage_id):
            errors.append(f"invalid outbound Usage ID in repository register: {usage_id or '<empty>'}")
            continue
        if usage_id in usage_to_call:
            errors.append(f"duplicate outbound Usage ID in repository register: {usage_id}")
            continue
        usage_to_call[usage_id] = call_id
        if call_id not in call_ids:
            errors.append(f"outbound Usage {usage_id} references unknown Call ID: {call_id}")
            continue
        if not usage_id.startswith(f"{call_id}-U"):
            errors.append(f"outbound Usage ID does not belong to its Call ID: {usage_id} -> {call_id}")
        usages_by_call.setdefault(call_id, set()).add(usage_id)

    for call_id in sorted(call_ids):
        if not usages_by_call.get(call_id):
            errors.append(f"outbound Call has no executable Usage in repository register: {call_id}")

    for row in mapping_rows:
        if len(row) != len(REGISTER_MAPPING_HEADERS):
            errors.append("repository register outbound mapping row has the wrong number of columns")
            continue
        mapping_id = code_value(row[0])
        call_id = code_value(row[1])
        applies_to = code_value(row[2])
        direction = code_value(row[3]).lower()
        if not MAPPING_ID_RE.fullmatch(mapping_id):
            errors.append(f"invalid outbound Mapping ID in repository register: {mapping_id or '<empty>'}")
            continue
        if mapping_id in mapping_directions:
            errors.append(f"duplicate outbound Mapping ID in repository register: {mapping_id}")
        mapping_directions[mapping_id] = direction
        if call_id not in call_ids:
            errors.append(f"outbound Mapping {mapping_id} references unknown Call ID: {call_id}")
        if direction not in {"eapi-to-external", "external-to-eapi"}:
            errors.append(f"outbound Mapping {mapping_id} has an invalid direction: {direction}")
        if applies_to.lower() != "all":
            usage_refs = set(USAGE_ID_RE.findall(applies_to))
            if not usage_refs:
                errors.append(f"outbound Mapping {mapping_id} has no applicable Usage ID or all")
            for usage_id in sorted(usage_refs):
                if usage_id not in usage_to_call:
                    errors.append(
                        f"outbound Mapping {mapping_id} references unknown Usage ID: {usage_id}"
                    )
                elif usage_to_call[usage_id] != call_id:
                    errors.append(
                        f"outbound Mapping {mapping_id} references Usage {usage_id} from another Call"
                    )

    return call_ids, usages_by_call, usage_to_call, mapping_directions


def validate_field_mapping_document(
    document: Path,
    register_call_ids: set[str],
    register_usages_by_call: dict[str, set[str]],
    register_usage_to_call: dict[str, str],
    register_mapping_directions: dict[str, str],
    errors: list[str],
) -> set[str]:
    if not document.is_file():
        if register_call_ids:
            errors.append("outbound HTTP operations exist but Field Validation and Mapping is missing")
        return set()

    text = document.read_text(encoding="utf-8")
    if section_value(text, "Proven external HTTP calls") or section_value(
        text, "External HTTP field mappings"
    ):
        errors.append("Field Validation and Mapping still uses legacy global outbound HTTP tables")

    index_header, index_rows = table_in_section(text, "Outbound HTTP operation index")
    if index_header and index_header != FIELD_OPERATION_HEADERS:
        errors.append("Field Validation and Mapping operation-index columns are invalid")

    index_call_ids: set[str] = set()
    for row in index_rows:
        if len(row) != len(FIELD_OPERATION_HEADERS):
            errors.append("Field Validation and Mapping operation-index row has the wrong column count")
            continue
        call_id = code_value(row[0])
        if not CALL_ID_RE.fullmatch(call_id):
            errors.append(f"invalid Call ID in Field Validation and Mapping index: {call_id or '<empty>'}")
            continue
        if call_id in index_call_ids:
            errors.append(f"duplicate Call ID in Field Validation and Mapping index: {call_id}")
        index_call_ids.add(call_id)
        anchor = call_id.lower()
        if not re.search(rf"\]\(#{re.escape(anchor)}\)", row[6]):
            errors.append(f"Field operation index does not link its Call anchor: {call_id}")

    call_heading_matches = list(
        re.finditer(r"^##\s+`?(?P<call>HTTP-\d+)`?(?:\s+.*)?$", text, re.M)
    )
    section_call_ids: set[str] = set()
    final_usage_ids: set[str] = set()
    final_mapping_ids: set[str] = set()
    final_mapping_directions: dict[str, str] = {}
    final_usages_by_call: dict[str, set[str]] = {}

    for match in call_heading_matches:
        call_id = match.group("call")
        if call_id in section_call_ids:
            errors.append(f"duplicate Call section in Field Validation and Mapping: {call_id}")
        section_call_ids.add(call_id)
        anchor = call_id.lower()
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(anchor)}[\"']\s*></a>\s*\n\s*##\s+`?{re.escape(call_id)}`?",
            text,
            re.I,
        ):
            errors.append(f"Field Validation and Mapping is missing stable Call anchor: {call_id}")

        next_heading = re.search(r"^##\s+", text[match.end() :], re.M)
        section_end = match.end() + next_heading.start() if next_heading else len(text)
        section = text[match.end() : section_end]
        current_direction: str | None = None
        for line in section.splitlines():
            heading_match = re.match(r"^###\s+(.+?)\s*$", line)
            if heading_match:
                subsection = heading_match.group(1)
                if subsection == "Request mappings":
                    current_direction = "eapi-to-external"
                elif subsection == "Response mappings":
                    current_direction = "external-to-eapi"
                else:
                    current_direction = None
                continue
            if not line.strip().startswith("|"):
                continue
            cells = table_cells(line)
            if not cells:
                continue
            first = code_value(cells[0])
            if first == "Usage ID" and cells != FIELD_USAGE_HEADERS:
                errors.append(f"Field Usage table columns are invalid under Call: {call_id}")
                continue
            if first == "Mapping ID" and cells != FIELD_MAPPING_HEADERS:
                errors.append(f"Field Mapping table columns are invalid under Call: {call_id}")
                continue
            if USAGE_ID_RE.fullmatch(first):
                if len(cells) != len(FIELD_USAGE_HEADERS):
                    errors.append(f"Field Usage row has the wrong column count: {first}")
                    continue
                if first in final_usage_ids:
                    errors.append(f"duplicate Usage ID in Field Validation and Mapping: {first}")
                final_usage_ids.add(first)
                final_usages_by_call.setdefault(call_id, set()).add(first)
                if not first.startswith(f"{call_id}-U"):
                    errors.append(f"Usage ID appears under the wrong Call section: {first} -> {call_id}")
            elif MAPPING_ID_RE.fullmatch(first):
                if len(cells) != len(FIELD_MAPPING_HEADERS):
                    errors.append(f"Field Mapping row has the wrong column count: {first}")
                    continue
                if first in final_mapping_ids:
                    errors.append(f"duplicate Mapping ID in Field Validation and Mapping: {first}")
                final_mapping_ids.add(first)
                if current_direction is None:
                    errors.append(f"Field Mapping is outside Request or Response mappings: {first}")
                else:
                    final_mapping_directions[first] = current_direction
                applies_to = code_value(cells[1])
                if applies_to.lower() != "all":
                    usage_refs = set(USAGE_ID_RE.findall(applies_to))
                    if not usage_refs:
                        errors.append(f"Field Mapping {first} has no applicable Usage ID or all")
                    for usage_id in sorted(usage_refs):
                        if usage_id not in register_usage_to_call:
                            errors.append(f"Field Mapping {first} references unknown Usage: {usage_id}")
                        elif register_usage_to_call[usage_id] != call_id:
                            errors.append(
                                f"Field Mapping {first} references Usage from another Call: {usage_id}"
                            )

    if index_call_ids != section_call_ids:
        for call_id in sorted(index_call_ids - section_call_ids):
            errors.append(f"Field operation index has no matching Call section: {call_id}")
        for call_id in sorted(section_call_ids - index_call_ids):
            errors.append(f"Field Call section is missing from the operation index: {call_id}")

    if register_call_ids != section_call_ids:
        for call_id in sorted(register_call_ids - section_call_ids):
            errors.append(f"registered outbound Call is missing from Field document: {call_id}")
        for call_id in sorted(section_call_ids - register_call_ids):
            errors.append(f"Field document Call is missing from repository register: {call_id}")

    register_mapping_ids = set(register_mapping_directions)
    if register_mapping_ids != final_mapping_ids:
        for mapping_id in sorted(register_mapping_ids - final_mapping_ids):
            errors.append(f"registered outbound Mapping is missing from Field document: {mapping_id}")
        for mapping_id in sorted(final_mapping_ids - register_mapping_ids):
            errors.append(f"Field document Mapping is missing from repository register: {mapping_id}")

    for mapping_id in sorted(register_mapping_ids & final_mapping_ids):
        if final_mapping_directions.get(mapping_id) != register_mapping_directions[mapping_id]:
            errors.append(
                f"Field Mapping is published under the wrong request/response section: {mapping_id}"
            )

    for call_id, usage_ids in sorted(register_usages_by_call.items()):
        if len(usage_ids) > 1:
            missing = usage_ids - final_usages_by_call.get(call_id, set())
            for usage_id in sorted(missing):
                errors.append(
                    f"multi-usage outbound Call does not list Usage in Field document: {usage_id}"
                )
    for usage_id in sorted(final_usage_ids):
        if usage_id not in register_usage_to_call:
            errors.append(f"Field document contains an unregistered Usage ID: {usage_id}")

    return section_call_ids


def validate_behavior_call_links(root: Path, call_ids: set[str], errors: list[str]) -> None:
    behaviors_dir = root / "tech-pack" / "behaviors"
    if not behaviors_dir.is_dir():
        return
    for behavior in sorted(behaviors_dir.glob("*.md")):
        text = behavior.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end == -1:
            continue
        frontmatter = text[4:end]
        call_block = yaml_block(frontmatter, "external_http_calls")
        behavior_call_ids = re.findall(
            r"^\s*-\s+call_id:\s*[\"']?(HTTP-\d+)[\"']?\s*$", call_block, re.M
        )
        for call_id in behavior_call_ids:
            if call_id not in call_ids:
                errors.append(
                    f"Tech Behavior references outbound Call missing from Field document: "
                    f"{behavior.relative_to(root)} -> {call_id}"
                )
                continue
            expected_target = f"../field-validation-and-mapping.md#{call_id.lower()}"
            if not re.search(rf"\]\({re.escape(expected_target)}\)", text):
                errors.append(
                    f"Tech Behavior does not link its outbound Call anchor: "
                    f"{behavior.relative_to(root)} -> {call_id}"
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_root", type=Path)
    args = parser.parse_args()

    if not args.pack_root.is_dir():
        print(f"ERROR: pack root does not exist: {args.pack_root}")
        return 2

    root = args.pack_root.resolve()
    errors: list[str] = []
    checked_links = 0

    markdown_files = sorted(
        path for path in root.rglob("*.md") if ".work" not in path.relative_to(root).parts
    )
    for document in markdown_files:
        text = document.read_text(encoding="utf-8")
        if any(placeholder in text for placeholder in PLACEHOLDERS):
            errors.append(f"template placeholder remains: {document.relative_to(root)}")
        for match in MARKDOWN_LINK_RE.finditer(text):
            target = local_target(match.group("target"))
            if target is None:
                continue
            checked_links += 1
            resolved = (document.parent / target).resolve()
            if not within_root(resolved, root):
                errors.append(
                    f"local link escapes pack root: {document.relative_to(root)} -> {match.group('target')}"
                )
            elif not resolved.exists():
                errors.append(
                    f"broken local link: {document.relative_to(root)} -> {match.group('target')}"
                )

    catalog = root / "tech-pack" / "behavior-catalog.yaml"
    if catalog.is_file():
        catalog_text = catalog.read_text(encoding="utf-8")
        for match in CATALOG_PATH_RE.finditer(catalog_text):
            target = match.group("target").strip()
            if target.lower() in {"null", "none"}:
                continue
            checked_links += 1
            resolved = (catalog.parent / target).resolve()
            if not within_root(resolved, root):
                errors.append(f"catalog path escapes pack root: {target}")
            elif not resolved.exists():
                errors.append(f"broken catalog document path: {target}")

    endpoint_matrix = root / "tech-pack" / "endpoint-matrix.md"
    if endpoint_matrix.is_file():
        validate_endpoint_matrix(endpoint_matrix, root, errors)

    register = root / ".work" / "repository-register.md"
    call_ids, usages_by_call, usage_to_call, mapping_directions = validate_http_register(
        register, errors
    )
    field_document = root / "tech-pack" / "field-validation-and-mapping.md"
    published_call_ids = validate_field_mapping_document(
        field_document,
        call_ids,
        usages_by_call,
        usage_to_call,
        mapping_directions,
        errors,
    )
    validate_behavior_call_links(root, published_call_ids, errors)

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {checked_links} local link(s) checked")
        return 1
    print(f"OK: {len(markdown_files)} Markdown file(s), {checked_links} local link(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
