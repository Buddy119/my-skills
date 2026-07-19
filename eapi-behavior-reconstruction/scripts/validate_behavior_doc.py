#!/usr/bin/env python3
"""Validate mechanical structure, links, and source citations of a Tech behavior."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from markdown_structure import parse_markdown


REQUIRED_KEYS = {
    "behavior_id",
    "title",
    "repository",
    "source_commit",
    "entry_type",
    "entry_point",
    "behavior_category",
    "overall_status",
    "api_contracts",
    "ba_scenarios",
    "consumes",
    "produces",
    "reads",
    "writes",
    "external_dependencies",
    "external_http_calls",
    "field_mappings",
    "analysis_limitations",
}

REQUIRED_HEADINGS = {
    "Summary",
    "Trigger and entry point",
    "Behavior flow",
    "Inputs",
    "Preconditions and business rules",
    "Happy path",
    "Data access and state changes",
    "Outputs and side effects",
    "Failures, retries, and partial success",
    "Open questions and conflicts",
    "Evidence index",
}

ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
ALLOWED_CATEGORIES = {"business", "integration", "technical"}
EVIDENCE_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?`"
)


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("YAML frontmatter is not closed with ---")
    return text[4:end], text[end + 5 :]


def top_level_keys(frontmatter: str) -> set[str]:
    keys: set[str] = set()
    for line in frontmatter.splitlines():
        if line and not line[0].isspace():
            match = re.match(r"([A-Za-z_][A-Za-z0-9_-]*):", line)
            if match:
                keys.add(match.group(1))
    return keys


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


def linked_entries(frontmatter: str, block_key: str, id_key: str) -> list[tuple[str, str]]:
    inline, block = yaml_block(frontmatter, block_key)
    if inline == "[]":
        return []
    identifiers = re.findall(
        rf"^\s*-\s+{re.escape(id_key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
        block,
        re.M,
    )
    documents = re.findall(r"^\s+document:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", block, re.M)
    return list(zip((item.strip() for item in identifiers), (item.strip() for item in documents)))


def api_contract_entries(frontmatter: str) -> list[tuple[str, str]]:
    return linked_entries(frontmatter, "api_contracts", "endpoint_id")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--allow-missing-ba",
        action="store_true",
        help="pre-BA validation only: allow the declared BA target file to be created later",
    )
    parser.add_argument(
        "--allow-missing-api-contracts",
        action="store_true",
        help=(
            "Tech-publication validation only: allow declared API Contract target files "
            "to be materialized by the next stage"
        ),
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

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
        print("SKIPPED [TECH-BEHAVIOR-SEMANTICS] prerequisite Markdown structure is invalid")
        return 1
    try:
        frontmatter, body = split_frontmatter(text)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    missing_keys = sorted(REQUIRED_KEYS - top_level_keys(frontmatter))
    if missing_keys:
        errors.append("missing YAML keys: " + ", ".join(missing_keys))

    status = scalar_value(frontmatter, "overall_status")
    if status not in ALLOWED_STATUSES:
        errors.append("overall_status must be Confirmed, Inferred, Conflicting, or Unknown")

    behavior_category = scalar_value(frontmatter, "behavior_category")
    if behavior_category not in ALLOWED_CATEGORIES:
        errors.append("behavior_category must be business, integration, or technical")

    headings = set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))
    missing_headings = sorted(REQUIRED_HEADINGS - headings)
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))

    if not re.search(r"```mermaid\s*\n\s*(?:flowchart|graph)\b", body, re.I):
        errors.append("Behavior flow must contain a Mermaid flowchart or graph")

    entry_type = scalar_value(frontmatter, "entry_type")
    api_inline, api_block = yaml_block(frontmatter, "api_contracts")
    contracts = api_contract_entries(frontmatter)
    endpoint_count = len(re.findall(r"^\s*-\s+endpoint_id:", api_block, re.M))
    document_count = len(re.findall(r"^\s+document:", api_block, re.M))
    if endpoint_count != document_count:
        errors.append("every api_contracts entry must contain endpoint_id and document")
    if len({item[0] for item in contracts}) != len(contracts):
        errors.append("api_contracts contains duplicate Endpoint IDs")
    if len({item[1] for item in contracts}) != len(contracts):
        errors.append("api_contracts contains duplicate documents")

    if entry_type == "api":
        if "API contracts" not in headings:
            errors.append("API behavior is missing the API contracts link section")
        if not contracts:
            errors.append("API behavior must list at least one endpoint contract in api_contracts")
        for endpoint_id, document in contracts:
            expected_document = f"../contracts/{endpoint_id}.api-contract.md"
            if document != expected_document:
                errors.append(
                    "api_contracts document must match its Endpoint ID: "
                    f"{endpoint_id} -> {expected_document}"
                )
            contract_path = (args.document.parent / document).resolve()
            if not contract_path.is_file() and not args.allow_missing_api_contracts:
                errors.append(f"linked API contract does not exist: {document}")
            if not re.search(rf"\]\({re.escape(document)}\)", body):
                errors.append(f"API behavior body must link endpoint {endpoint_id}: {document}")
    else:
        if contracts or api_inline != "[]":
            errors.append("non-API behavior must set api_contracts: []")
        if "API contracts" in headings:
            errors.append("non-API behavior must omit the API contracts section")

    ba_inline, ba_block = yaml_block(frontmatter, "ba_scenarios")
    ba_scenarios = linked_entries(frontmatter, "ba_scenarios", "scenario_id")
    scenario_count = len(re.findall(r"^\s*-\s+scenario_id:", ba_block, re.M))
    scenario_document_count = len(re.findall(r"^\s+document:", ba_block, re.M))
    if scenario_count != scenario_document_count:
        errors.append("every ba_scenarios entry must contain scenario_id and document")
    if len({item[0] for item in ba_scenarios}) != len(ba_scenarios):
        errors.append("ba_scenarios contains duplicate Scenario IDs")
    if len({item[1] for item in ba_scenarios}) != len(ba_scenarios):
        errors.append("ba_scenarios contains duplicate documents")

    if ba_scenarios:
        if "BA scenarios" not in headings:
            errors.append("Tech behavior with ba_scenarios is missing the BA scenarios section")
        behavior_id = scalar_value(frontmatter, "behavior_id")
        repository = scalar_value(frontmatter, "repository")
        source_commit = scalar_value(frontmatter, "source_commit")
        for scenario_id, document in ba_scenarios:
            scenario_path = (args.document.parent / document).resolve()
            if not scenario_path.is_file():
                if not args.allow_missing_ba:
                    errors.append(f"linked BA Scenario does not exist: {document}")
            else:
                try:
                    scenario_frontmatter, _ = split_frontmatter(
                        scenario_path.read_text(encoding="utf-8")
                    )
                except ValueError as exc:
                    errors.append(f"linked BA Scenario is invalid: {document}: {exc}")
                else:
                    if scalar_value(scenario_frontmatter, "scenario_id") != scenario_id:
                        errors.append(
                            f"ba_scenarios ID does not match linked Scenario: {scenario_id}"
                        )
                    for key, expected in (
                        ("repository", repository),
                        ("source_commit", source_commit),
                    ):
                        if scalar_value(scenario_frontmatter, key) != expected:
                            errors.append(
                                f"Tech behavior and linked Scenario must have the same {key}: "
                                f"{scenario_id}"
                            )
                    backlinks = linked_entries(
                        scenario_frontmatter, "tech_behaviors", "behavior_id"
                    )
                    backlink_matches = [
                        backlink_document
                        for backlink_id, backlink_document in backlinks
                        if backlink_id == behavior_id
                        and (scenario_path.parent / backlink_document).resolve()
                        == args.document.resolve()
                    ]
                    if not backlink_matches:
                        errors.append(
                            "linked Scenario does not contain the Tech behavior backlink: "
                            f"{scenario_id} -> {behavior_id}"
                        )
            if not re.search(rf"\]\({re.escape(document)}\)", body):
                errors.append(
                    f"Tech behavior body must link BA Scenario {scenario_id}: {document}"
                )
    else:
        if ba_inline != "[]":
            errors.append("empty BA Scenario mapping must use ba_scenarios: []")
        if "BA scenarios" in headings:
            errors.append(
                "Tech behavior with ba_scenarios: [] must omit the BA scenarios section"
            )

    _, call_block = yaml_block(frontmatter, "external_http_calls")
    _, mapping_block = yaml_block(frontmatter, "field_mappings")
    dependency_inline, dependency_block = yaml_block(frontmatter, "external_dependencies")
    failure_inline, failure_block = yaml_block(frontmatter, "failure_patterns")
    call_ids = re.findall(
        r"^\s*-\s+call_id:\s*[\"']?(HTTP-\d+)[\"']?\s*$", call_block, re.M
    )
    usage_ids = re.findall(r"\bHTTP-\d+-U\d+\b", call_block)
    mapping_ids = re.findall(
        r"^\s*-\s+mapping_id:\s*[\"']?(FM-\d+)[\"']?\s*$", mapping_block, re.M
    )
    mapping_call_ids = re.findall(
        r"^\s+call_id:\s*[\"']?(HTTP-\d+)[\"']?\s*$", mapping_block, re.M
    )
    mapping_usage_ids = re.findall(r"\bHTTP-\d+-U\d+\b", mapping_block)
    applicable_usage_keys = re.findall(r"^\s+applicable_usage_ids:", mapping_block, re.M)
    has_external_http_calls = bool(call_ids)
    has_structured_mappings = bool(mapping_ids)
    dependency_ids = re.findall(
        r"^\s*-\s+dependency_id:\s*[\"']?(DEP-\d+)[\"']?\s*$",
        dependency_block,
        re.M,
    )
    failure_pattern_ids = re.findall(r"\bFAIL-\d+\b", failure_block)

    if len(call_ids) != len(set(call_ids)):
        errors.append("external_http_calls contains duplicate Call IDs")
    if len(usage_ids) != len(set(usage_ids)):
        errors.append("external_http_calls contains duplicate Usage IDs")
    if len(mapping_ids) != len(set(mapping_ids)):
        errors.append("field_mappings contains duplicate Mapping IDs")
    if len(dependency_ids) != len(set(dependency_ids)):
        errors.append("external_dependencies contains duplicate Dependency IDs")
    if len(failure_pattern_ids) != len(set(failure_pattern_ids)):
        errors.append("failure_patterns contains duplicate Failure Pattern IDs")
    for usage_id in usage_ids:
        if not any(usage_id.startswith(f"{call_id}-U") for call_id in call_ids):
            errors.append(f"Usage ID does not belong to a listed Call ID: {usage_id}")

    if has_external_http_calls:
        if not usage_ids:
            errors.append("external_http_calls must list at least one executable Usage ID")
        if "External HTTP calls and mappings" not in headings:
            errors.append(
                "structured external_http_calls exist but the External HTTP calls and mappings "
                "section is missing"
            )
        for call_id in call_ids:
            expected_target = f"../field-validation-and-mapping.md#{call_id.lower()}"
            if not re.search(rf"\]\({re.escape(expected_target)}\)", body):
                errors.append(f"Tech behavior does not link outbound Call anchor: {call_id}")

    if has_structured_mappings:
        if not has_external_http_calls:
            errors.append("field_mappings require a proven outbound call in external_http_calls")
        if len(mapping_call_ids) != len(mapping_ids):
            errors.append("every field_mappings entry must contain one Call ID")
        if len(applicable_usage_keys) != len(mapping_ids):
            errors.append("every field_mappings entry must contain applicable_usage_ids")
        unknown_call_ids = sorted(set(mapping_call_ids) - set(call_ids))
        if unknown_call_ids:
            errors.append(
                "field_mappings reference Call IDs not listed in external_http_calls: "
                + ", ".join(unknown_call_ids)
            )
        unknown_usage_ids = sorted(set(mapping_usage_ids) - set(usage_ids))
        if unknown_usage_ids:
            errors.append(
                "field_mappings reference Usage IDs not listed in external_http_calls: "
                + ", ".join(unknown_usage_ids)
            )
        directions = re.findall(r"^\s+direction:\s*[\"']?([^\"'\s]+)", mapping_block, re.M)
        if len(directions) != len(mapping_ids):
            errors.append("every field_mappings entry must contain one direction")
        invalid_directions = sorted(set(directions) - {"eapi-to-external", "external-to-eapi"})
        if invalid_directions:
            errors.append("invalid field mapping direction(s): " + ", ".join(invalid_directions))

    if dependency_ids:
        if "External dependencies" not in headings:
            errors.append(
                "structured external_dependencies exist but the External dependencies section is missing"
            )
        for dependency_id in dependency_ids:
            expected_target = f"../external-dependency-contracts.md#{dependency_id.lower()}"
            if not re.search(rf"\]\({re.escape(expected_target)}\)", body):
                errors.append(f"Tech behavior does not link Dependency anchor: {dependency_id}")
    else:
        if dependency_inline != "[]" or dependency_block.strip():
            errors.append(
                "external_dependencies entries must contain a Dependency ID or use external_dependencies: []"
            )
        if "External dependencies" in headings:
            errors.append(
                "behavior without reconciled Dependencies must omit the External dependencies section"
            )

    if failure_pattern_ids:
        for pattern_id in failure_pattern_ids:
            expected_target = f"../failure-taxonomy.md#{pattern_id.lower()}"
            if not re.search(rf"\]\({re.escape(expected_target)}\)", body):
                errors.append(f"Tech behavior does not link Failure Pattern anchor: {pattern_id}")
    elif failure_inline not in {"", "[]"} or failure_block.strip():
        errors.append(
            "failure_patterns entries must contain a Failure Pattern ID or use failure_patterns: []"
        )

    citations = list(EVIDENCE_RE.finditer(body))
    if not citations:
        errors.append("no source citations found; use `relative/path.ext:line`")

    checked: set[tuple[str, int, int | None]] = set()
    for match in citations:
        rel = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end")) if match.group("end") else None
        key = (rel, start, end)
        if key in checked:
            continue
        checked.add(key)

        source = args.repo / rel
        if not source.is_file():
            errors.append(f"cited file does not exist: {rel}")
            continue
        if end is not None and end < start:
            errors.append(f"invalid line range: {rel}:{start}-{end}")
            continue
        try:
            line_count = sum(1 for _ in source.open(encoding="utf-8", errors="replace"))
        except OSError as exc:
            errors.append(f"cannot read cited file {rel}: {exc}")
            continue
        final_line = end or start
        if start < 1 or final_line > line_count:
            errors.append(f"citation outside file bounds: {rel}:{start}" + (f"-{end}" if end else ""))

    if "Unknown" not in body and "Conflicting" not in body:
        warnings.append("document contains no Unknown or Conflicting review items")
    placeholders = (
        "TODO",
        "path/to/",
        "repository.behavior-name",
        "repository.method-route",
        "repository.scenario.context-outcome",
    )
    if any(placeholder in text for placeholder in placeholders):
        errors.append("template placeholders remain in the document")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {len(contracts)} endpoint contract(s), {len(citations)} citation occurrence(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
