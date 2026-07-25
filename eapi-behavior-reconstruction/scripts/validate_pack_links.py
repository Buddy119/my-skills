#!/usr/bin/env python3
"""Validate pack links plus mechanical endpoint, call, dependency, and failure integrity."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from artifact_schema import ArtifactSchemaError, load_registry, validate_artifact_manifest
from lifecycle_model import (
    LIFECYCLE_MODEL_VALIDATION_VERSION,
    LifecycleSchemaError,
    load_lifecycle_schema,
    validate_behavior_lifecycle_projection,
    validate_lifecycle_document,
    validate_lifecycle_register,
)
from markdown_structure import MARKDOWN_FRAGMENT_VALIDATION_VERSION, parse_markdown
from register_schema import (
    RegisterSchema,
    load_register_schema,
    validate_register_file,
)


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")
SOURCE_CITATION_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)"
    r"(?:-(?P<end>\d+))?`"
)
CATALOG_PATH_RE = re.compile(
    r"^\s*document:\s*[\"']?(?P<target>[^\"'\n#]+?)[\"']?\s*$", re.M
)
PLACEHOLDERS = (
    "TODO",
    "TEMPLATE:",
    "path/to/",
    "repository.behavior-name",
    "repository.journey.business-goal",
    "repository.scenario.context-outcome",
    "repository.method-route",
    "Business journey title",
    "Business scenario title",
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
DEPENDENCY_OBSERVATION_ID_RE = re.compile(r"DEP-OBS-\d+")
DEPENDENCY_ID_RE = re.compile(r"DEP-\d+")
DEPENDENCY_OPERATION_ID_RE = re.compile(r"DEP-\d+-OP\d+")
FAILURE_OBSERVATION_ID_RE = re.compile(r"FO-\d+")
FAILURE_PATTERN_ID_RE = re.compile(r"FAIL-\d+")
CONFIG_OBSERVATION_ID_RE = re.compile(r"CFG-OBS-\d+")
CONFIG_ID_RE = re.compile(r"CFG-\d+")
CONFIG_IMPACT_ID_RE = re.compile(r"CFG-\d+-I\d+")
JAVA_TYPE_ID_RE = re.compile(r"JTYPE-\d+")
JAVA_EDGE_ID_RE = re.compile(r"JEDGE-\d+")
JAVA_BINDING_ID_RE = re.compile(r"JIMPL-\d+")
EVIDENCE_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
DEPENDENCY_CRITICALITIES = {"Required", "Degradable", "Optional", "Unknown"}
CALLER_VISIBILITIES = {
    "Explicit error",
    "Degraded result",
    "Success with loss",
    "Swallowed",
    "Async only",
    "Unknown",
}
STATE_OUTCOMES = {
    "Unchanged",
    "Rolled back",
    "Partial",
    "Committed before failure",
    "Unknown",
}
RETRY_SAFETIES = {"Safe", "Conditional", "Unsafe", "Unknown"}
RECOVERY_MODES = {
    "Automatic retry",
    "Rollback",
    "Compensation",
    "Manual",
    "None observed",
    "Unknown",
}
RISK_ATTENTIONS = {"High", "Medium", "Low", "Unknown"}
CONFIG_IMPACT_TYPES = {
    "application availability",
    "authentication/authorization",
    "validation",
    "branch/variant",
    "implementation selection",
    "dependency target",
    "timeout/retry/recovery",
    "output/status",
    "state/side effect",
    "other",
}
JAVA_EDGE_RELATIONS = {
    "calls",
    "injects",
    "implements",
    "extends",
    "creates",
    "framework-dispatch",
    "generated-delegate",
}
FIELD_OPERATION_HEADERS = [
    "Call ID",
    "Method and Logical Target",
    "Client Operation",
    "Observable Purpose",
    "Related Behaviors",
    "Details",
]
FIELD_USAGE_HEADERS = [
    "Usage ID",
    "Behavior",
    "Executable Call Site",
    "Invocation Condition or Config",
]
FIELD_OVERVIEW_HEADERS = [
    "Method",
    "Logical Target",
    "Client Operation",
    "Observable Purpose",
    "Related Behaviors",
    "Usage Summary",
]
FIELD_MAPPING_HEADERS = [
    "Mapping ID",
    "Applies to Usage(s)",
    "Source Field(s)",
    "Target Field(s)",
    "Transformation",
    "Condition/Default",
    "Lossy",
]
DEPENDENCY_LANDSCAPE_HEADERS = [
    "Dependency",
    "Type and repository-observed role",
    "Dependent capabilities",
    "Criticality",
    "Availability impact",
    "Details",
]
DEPENDENCY_OPERATION_DOCUMENT_HEADERS = [
    "Operation",
    "Boundary reference",
    "Purpose and condition",
    "Concepts sent, consumed, read, or written",
    "Affected capabilities/behaviors",
]
FAILURE_PATTERN_INDEX_HEADERS = [
    "Failure pattern",
    "Category",
    "Affected capabilities",
    "Caller visibility",
    "State outcome",
    "Retry safety",
    "Risk attention",
    "Details",
]


MAX_ERRORS_PER_GROUP = 10
MAX_DEFERRED_LINK_DETAILS = 50
DOMAIN_STATUSES = {"valid", "partial", "invalid", "skipped"}
VALIDATION_PROFILES = {"tech-publication", "complete"}
TECH_DEFERRED_CHECKS = ("api-materialization", "ba-traceability")


@dataclass
class DomainResult:
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in DOMAIN_STATUSES:
            raise ValueError(f"invalid domain status: {self.status}")


@dataclass(frozen=True)
class LocalLinkTarget:
    path: str
    query: str
    fragment: str | None
    same_document: bool


@dataclass(frozen=True)
class MarkdownLinkReference:
    raw_target: str
    line: int


class ValidationReport:
    """Group, de-duplicate, budget, and summarize mechanical validation results."""

    def __init__(self, validation_profile: str = "complete") -> None:
        if validation_profile not in VALIDATION_PROFILES:
            raise ValueError(f"invalid validation profile: {validation_profile}")
        self.validation_profile = validation_profile
        self.error_groups: dict[str, list[str]] = {}
        self.skipped_groups: dict[str, str] = {}
        self.warnings: list[str] = []
        self.domain_statuses: dict[str, str] = {}
        self.deferred_checks: list[str] = (
            list(TECH_DEFERRED_CHECKS)
            if validation_profile == "tech-publication"
            else []
        )
        self.deferred_link_count = 0
        self.deferred_links: list[dict[str, str]] = []
        self.checked_links = 0
        self.checked_documents = 0
        self.checked_fragments = 0
        self.fragment_target_documents: set[str] = set()

    def add_errors(self, code: str, messages: list[str]) -> None:
        target = self.error_groups.setdefault(code, [])
        seen = set(target)
        for message in messages:
            if message not in seen:
                target.append(message)
                seen.add(message)
        if not target:
            self.error_groups.pop(code, None)

    def error(self, code: str, message: str) -> None:
        self.add_errors(code, [message])

    def skip(self, code: str, reason: str) -> None:
        self.skipped_groups.setdefault(code, reason)

    def defer_link(self, check: str, source: str, target: str) -> None:
        self.deferred_link_count += 1
        if len(self.deferred_links) < MAX_DEFERRED_LINK_DETAILS:
            self.deferred_links.append(
                {"check": check, "source": source, "target": target}
            )

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    @property
    def primary_error_count(self) -> int:
        return sum(len(messages) for messages in self.error_groups.values())

    @property
    def suppressed_error_count(self) -> int:
        return sum(max(0, len(messages) - MAX_ERRORS_PER_GROUP) for messages in self.error_groups.values())

    @property
    def failed(self) -> bool:
        return bool(self.error_groups or self.skipped_groups)

    def payload(self, markdown_count: int) -> dict[str, Any]:
        visible_errors = {
            code: messages[:MAX_ERRORS_PER_GROUP]
            for code, messages in self.error_groups.items()
        }
        suppressed = {
            code: len(messages) - MAX_ERRORS_PER_GROUP
            for code, messages in self.error_groups.items()
            if len(messages) > MAX_ERRORS_PER_GROUP
        }
        return {
            "result": "failed" if self.failed else "ok",
            "validation_profile": self.validation_profile,
            "deferred_checks": self.deferred_checks,
            "deferred_link_count": self.deferred_link_count,
            "deferred_links": self.deferred_links,
            "deferred_links_suppressed": max(
                0, self.deferred_link_count - len(self.deferred_links)
            ),
            "primary_errors": self.primary_error_count,
            "warnings": len(self.warnings),
            "skipped_validation_groups": len(self.skipped_groups),
            "suppressed_row_errors": self.suppressed_error_count,
            "checked_links": self.checked_links,
            "checked_documents": self.checked_documents,
            "markdown_fragment_validation_version": MARKDOWN_FRAGMENT_VALIDATION_VERSION,
            "lifecycle_model_validation_version": LIFECYCLE_MODEL_VALIDATION_VERSION,
            "checked_fragments": self.checked_fragments,
            "fragment_target_documents": len(self.fragment_target_documents),
            "fragment_error_count": len(self.error_groups.get("MARKDOWN-FRAGMENT", [])),
            "fragment_skipped_group_count": sum(
                1 for code in self.skipped_groups if code.startswith("MARKDOWN-FRAGMENT:")
            ),
            "markdown_files": markdown_count,
            "domain_statuses": self.domain_statuses,
            "errors": visible_errors,
            "suppressed_by_group": suppressed,
            "skipped": self.skipped_groups,
            "warning_messages": self.warnings,
        }

    def render_text(self, markdown_count: int) -> None:
        payload = self.payload(markdown_count)
        for code, messages in payload["errors"].items():
            for message in messages:
                print(f"ERROR [{code}] {message}")
            suppressed = payload["suppressed_by_group"].get(code, 0)
            if suppressed:
                print(f"ERROR [{code}] {suppressed} additional error(s) suppressed")
        for code, reason in self.skipped_groups.items():
            print(f"SKIPPED [{code}] {reason}")
        for check in self.deferred_checks:
            print(f"DEFERRED [{check}] later publication stage")
        for warning in self.warnings:
            print(f"WARNING {warning}")
        print(
            "SUMMARY: "
            f"primary_errors={payload['primary_errors']} "
            f"warnings={payload['warnings']} "
            f"skipped_groups={payload['skipped_validation_groups']} "
            f"suppressed_errors={payload['suppressed_row_errors']} "
            f"deferred_links={payload['deferred_link_count']} "
            f"checked_links={payload['checked_links']} "
            f"checked_fragments={payload['checked_fragments']} "
            f"checked_documents={payload['checked_documents']}"
        )
        if not self.failed:
            print(
                f"OK: {markdown_count} Markdown file(s), "
                f"{self.checked_links} local link(s) checked"
            )


def register_headers(schema: RegisterSchema, table_key: str) -> list[str]:
    return list(schema.tables[table_key].headers)


_REGISTER_SCHEMA = load_register_schema()
REGISTER_OPERATION_HEADERS = register_headers(_REGISTER_SCHEMA, "http_operations")
REGISTER_USAGE_HEADERS = register_headers(_REGISTER_SCHEMA, "http_usages")
REGISTER_MAPPING_HEADERS = register_headers(_REGISTER_SCHEMA, "http_mappings")
REGISTER_DEPENDENCY_OBSERVATION_HEADERS = register_headers(
    _REGISTER_SCHEMA, "dependency_observations"
)
REGISTER_DEPENDENCY_CONTRACT_HEADERS = register_headers(
    _REGISTER_SCHEMA, "dependency_contracts"
)
REGISTER_DEPENDENCY_OPERATION_HEADERS = register_headers(
    _REGISTER_SCHEMA, "dependency_operations"
)
REGISTER_FAILURE_OBSERVATION_HEADERS = register_headers(
    _REGISTER_SCHEMA, "failure_observations"
)
REGISTER_FAILURE_PATTERN_HEADERS = register_headers(_REGISTER_SCHEMA, "failure_patterns")
REGISTER_CONFIG_OBSERVATION_HEADERS = register_headers(
    _REGISTER_SCHEMA, "runtime_config_observations"
)
REGISTER_CONFIG_RECORD_HEADERS = register_headers(
    _REGISTER_SCHEMA, "runtime_config_records"
)
REGISTER_CONFIG_IMPACT_HEADERS = register_headers(
    _REGISTER_SCHEMA, "runtime_config_impacts"
)
REGISTER_JAVA_TYPE_HEADERS = register_headers(_REGISTER_SCHEMA, "java_types")
REGISTER_JAVA_EDGE_HEADERS = register_headers(_REGISTER_SCHEMA, "java_edges")
REGISTER_JAVA_BINDING_HEADERS = register_headers(_REGISTER_SCHEMA, "java_bindings")


def local_target(raw: str) -> LocalLinkTarget | None:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    split = urlsplit(target)
    if split.scheme or split.netloc:
        return None
    fragment = unquote(split.fragment) if "#" in target else None
    path = unquote(split.path)
    if not path and fragment is None:
        return None
    return LocalLinkTarget(
        path=path,
        query=split.query,
        fragment=fragment,
        same_document=path == "",
    )


def _mask_inline_code(line: str) -> str:
    pattern = re.compile(r"(?P<ticks>`+).*?(?P=ticks)")
    return pattern.sub(lambda match: " " * len(match.group(0)), line)


def markdown_link_references(text: str) -> list[MarkdownLinkReference]:
    """Extract inline Markdown links outside Frontmatter and fenced/inline code."""

    references: list[MarkdownLinkReference] = []
    in_frontmatter = text.startswith("---\n")
    in_fence = False
    fence_marker: str | None = None
    for line_number, original in enumerate(text.splitlines(), start=1):
        if in_frontmatter:
            if line_number > 1 and original.strip() == "---":
                in_frontmatter = False
            continue
        fence = re.match(r"^\s*(?P<marker>`{3,}|~{3,})", original)
        if fence:
            marker = fence.group("marker")
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif fence_marker and marker[0] == fence_marker[0] and len(marker) >= len(fence_marker):
                in_fence = False
                fence_marker = None
            continue
        if in_fence:
            continue
        masked = _mask_inline_code(original)
        for match in MARKDOWN_LINK_RE.finditer(masked):
            start, end = match.span("target")
            references.append(MarkdownLinkReference(original[start:end], line_number))
    return references


def target_fragment_ids(
    target: Path,
    root: Path,
    report: ValidationReport,
    cache: dict[Path, frozenset[str] | None],
) -> frozenset[str] | None:
    if target in cache:
        return cache[target]
    relative = target.relative_to(root).as_posix()
    try:
        structure = parse_markdown(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        report.skip(
            f"MARKDOWN-FRAGMENT:{relative}",
            f"cannot read Markdown fragment target: {exc}",
        )
        cache[target] = None
        return None
    if structure.issues:
        report.skip(
            f"MARKDOWN-FRAGMENT:{relative}",
            "fragment checks require a structurally valid target Markdown document",
        )
        cache[target] = None
        return None
    cache[target] = structure.fragment_ids
    report.fragment_target_documents.add(relative)
    return cache[target]


def within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def deferred_check_for_missing_target(
    path: Path,
    root: Path,
    validation_profile: str,
) -> str | None:
    """Return the later publication check that owns a missing target."""
    if validation_profile != "tech-publication" or not within_root(path, root):
        return None
    relative = path.relative_to(root)
    parts = relative.parts
    if relative.as_posix() == "tech-pack/endpoint-matrix.md":
        return "api-materialization"
    if (
        len(parts) == 3
        and parts[:2] == ("tech-pack", "contracts")
        and parts[2].endswith(".api-contract.md")
    ):
        return "api-materialization"
    if parts and parts[0] == "ba-pack":
        return "ba-traceability"
    return None


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


def rows_after_header(text: str, headers: list[str]) -> list[list[str]]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("|") and table_cells(line) == headers:
            rows: list[list[str]] = []
            for candidate in lines[index + 1 :]:
                if not candidate.strip().startswith("|"):
                    if rows:
                        break
                    continue
                cells = table_cells(candidate)
                if is_separator_row(cells):
                    continue
                rows.append(cells)
            return rows
    return []


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


def frontmatter_text(document: Path) -> str | None:
    text = document.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    return text[4:end] if end != -1 else None


def linked_document_entries(
    frontmatter: str, block_key: str, id_key: str
) -> list[tuple[str, str]]:
    block = yaml_block(frontmatter, block_key)
    identifiers = re.findall(
        rf"^\s*-\s+{re.escape(id_key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
        block,
        re.M,
    )
    documents = re.findall(
        r"^\s+document:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", block, re.M
    )
    return list(zip((item.strip() for item in identifiers), (item.strip() for item in documents)))


def pack_behavior_and_endpoint_ids(root: Path) -> tuple[set[str], set[str]]:
    """Collect the stable Reader identities available at the current stage.

    Endpoint IDs declared as Tech-stage Contract forward references are valid
    identities even before the Contract and Endpoint Matrix are materialized.
    """

    behavior_ids: set[str] = set()
    endpoint_ids: set[str] = set()
    for document in sorted((root / "tech-pack" / "behaviors").glob("*.md")):
        frontmatter = frontmatter_text(document)
        if frontmatter is None:
            continue
        behavior_id = scalar_value(frontmatter, "behavior_id")
        if behavior_id:
            behavior_ids.add(behavior_id)
        endpoint_ids.update(
            identifier
            for identifier, _document in linked_document_entries(
                frontmatter, "api_contracts", "endpoint_id"
            )
        )
    for contract in sorted((root / "tech-pack" / "contracts").glob("*.api-contract.md")):
        frontmatter = frontmatter_text(contract)
        if frontmatter is None:
            continue
        endpoint_id = scalar_value(frontmatter, "endpoint_id")
        if endpoint_id:
            endpoint_ids.add(endpoint_id)
    return behavior_ids, endpoint_ids


def stable_endpoint_references(value: str) -> set[str]:
    """Extract endpoint-shaped stable IDs without interpreting trigger labels."""

    return {
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", value)
        if "." in token
    }


def validate_ba_traceability(root: Path, errors: list[str]) -> None:
    ba_root = root / "ba-pack"
    if not ba_root.is_dir():
        return
    if (ba_root / "behaviors").exists():
        errors.append("legacy ba-pack/behaviors directory remains in the published Pack")

    journey_documents = sorted((ba_root / "journeys").glob("*.md"))
    scenario_documents = sorted((ba_root / "scenarios").glob("*.md"))
    if not journey_documents and not scenario_documents:
        return
    for required in (ba_root / "business-overview.md", ba_root / "business-catalog.md"):
        if not required.is_file():
            errors.append(f"BA Pack is missing required reader document: {required.name}")

    journeys: dict[str, tuple[Path, str]] = {}
    scenarios: dict[str, tuple[Path, str]] = {}
    tech_behaviors: dict[str, tuple[Path, str]] = {}

    for document, id_key, destination, label in (
        *((path, "journey_id", journeys, "Journey") for path in journey_documents),
        *((path, "scenario_id", scenarios, "Scenario") for path in scenario_documents),
        *(
            (path, "behavior_id", tech_behaviors, "Tech Behavior")
            for path in sorted((root / "tech-pack" / "behaviors").glob("*.md"))
        ),
    ):
        frontmatter = frontmatter_text(document)
        if frontmatter is None:
            errors.append(f"{label} has invalid YAML frontmatter: {document.relative_to(root)}")
            continue
        identifier = scalar_value(frontmatter, id_key)
        if not identifier:
            errors.append(f"{label} is missing {id_key}: {document.relative_to(root)}")
            continue
        if identifier in destination:
            errors.append(f"duplicate {label} ID: {identifier}")
            continue
        destination[identifier] = (document.resolve(), frontmatter)

    for scenario_id, (scenario_path, scenario_frontmatter) in scenarios.items():
        journey_entries = linked_document_entries(
            scenario_frontmatter, "journeys", "journey_id"
        )
        tech_entries = linked_document_entries(
            scenario_frontmatter, "tech_behaviors", "behavior_id"
        )
        if not journey_entries:
            errors.append(f"BA Scenario has no Journey relationship: {scenario_id}")
        if not tech_entries:
            errors.append(f"BA Scenario has no supporting Tech Behavior: {scenario_id}")

        for journey_id, document in journey_entries:
            journey = journeys.get(journey_id)
            if journey is None:
                errors.append(f"BA Scenario references unknown Journey: {scenario_id} -> {journey_id}")
                continue
            if (scenario_path.parent / document).resolve() != journey[0]:
                errors.append(
                    f"BA Scenario resolves the wrong Journey document: "
                    f"{scenario_id} -> {journey_id}"
                )
            backlinks = linked_document_entries(journey[1], "scenarios", "scenario_id")
            if not any(
                backlink_id == scenario_id
                and (journey[0].parent / backlink_document).resolve() == scenario_path
                for backlink_id, backlink_document in backlinks
            ):
                errors.append(f"BA Journey lacks Scenario backlink: {journey_id} -> {scenario_id}")

        for behavior_id, document in tech_entries:
            tech = tech_behaviors.get(behavior_id)
            if tech is None:
                errors.append(
                    f"BA Scenario references unknown Tech Behavior: {scenario_id} -> {behavior_id}"
                )
                continue
            if (scenario_path.parent / document).resolve() != tech[0]:
                errors.append(
                    f"BA Scenario resolves the wrong Tech Behavior document: "
                    f"{scenario_id} -> {behavior_id}"
                )
            backlinks = linked_document_entries(tech[1], "ba_scenarios", "scenario_id")
            if not any(
                backlink_id == scenario_id
                and (tech[0].parent / backlink_document).resolve() == scenario_path
                for backlink_id, backlink_document in backlinks
            ):
                errors.append(
                    f"Tech Behavior lacks BA Scenario backlink: {behavior_id} -> {scenario_id}"
                )

    for journey_id, (journey_path, journey_frontmatter) in journeys.items():
        scenario_entries = linked_document_entries(
            journey_frontmatter, "scenarios", "scenario_id"
        )
        tech_entries = linked_document_entries(
            journey_frontmatter, "supporting_tech_behaviors", "behavior_id"
        )
        if not scenario_entries:
            errors.append(f"BA Journey has no Scenario: {journey_id}")
        derived_tech: dict[str, Path] = {}
        for scenario_id, document in scenario_entries:
            scenario = scenarios.get(scenario_id)
            if scenario is None:
                errors.append(f"BA Journey references unknown Scenario: {journey_id} -> {scenario_id}")
                continue
            if (journey_path.parent / document).resolve() != scenario[0]:
                errors.append(
                    f"BA Journey resolves the wrong Scenario document: "
                    f"{journey_id} -> {scenario_id}"
                )
            for behavior_id, behavior_document in linked_document_entries(
                scenario[1], "tech_behaviors", "behavior_id"
            ):
                behavior_path = (scenario[0].parent / behavior_document).resolve()
                if behavior_id in derived_tech and derived_tech[behavior_id] != behavior_path:
                    errors.append(
                        f"BA Scenarios resolve the same Tech Behavior differently: {behavior_id}"
                    )
                derived_tech[behavior_id] = behavior_path

        declared_tech = {
            behavior_id: (journey_path.parent / document).resolve()
            for behavior_id, document in tech_entries
        }
        if set(declared_tech) != set(derived_tech):
            missing = sorted(set(derived_tech) - set(declared_tech))
            extra = sorted(set(declared_tech) - set(derived_tech))
            if missing:
                errors.append(
                    f"BA Journey omits Scenario-derived Tech Behaviors {journey_id}: "
                    + ", ".join(missing)
                )
            if extra:
                errors.append(
                    f"BA Journey lists Tech Behaviors not used by its Scenarios {journey_id}: "
                    + ", ".join(extra)
                )
        for behavior_id in sorted(set(declared_tech) & set(derived_tech)):
            if declared_tech[behavior_id] != derived_tech[behavior_id]:
                errors.append(
                    f"BA Journey and Scenario resolve Tech Behavior differently: "
                    f"{journey_id} -> {behavior_id}"
                )

    for behavior_id, (behavior_path, behavior_frontmatter) in tech_behaviors.items():
        for scenario_id, document in linked_document_entries(
            behavior_frontmatter, "ba_scenarios", "scenario_id"
        ):
            scenario = scenarios.get(scenario_id)
            if scenario is None:
                errors.append(
                    f"Tech Behavior references unknown BA Scenario: {behavior_id} -> {scenario_id}"
                )
            elif (behavior_path.parent / document).resolve() != scenario[0]:
                errors.append(
                    f"Tech Behavior resolves the wrong BA Scenario document: "
                    f"{behavior_id} -> {scenario_id}"
                )


def normalized_label(cell: str) -> str:
    return re.sub(r"\s+", " ", code_value(cell)).strip()


def validate_exact_label(
    cell: str,
    allowed: set[str],
    context: str,
    errors: list[str],
) -> str | None:
    value = normalized_label(cell)
    if value not in allowed:
        errors.append(f"{context} has an invalid value: {value or '<empty>'}")
        return None
    return value


def validate_reader_status_qualifier(
    cell: str,
    status: str,
    context: str,
    errors: list[str],
) -> None:
    qualifiers = re.findall(r"\*\((Confirmed|Inferred|Unknown|Conflicting)\)\*", cell)
    if status == "Confirmed":
        if qualifiers:
            errors.append(f"{context} repeats a qualifier for Confirmed Reader content")
        return
    expected = f"*({status})*"
    if expected not in cell:
        errors.append(f"{context} must preserve Register status with {expected}")
    if any(item != status for item in qualifiers):
        errors.append(f"{context} qualifier conflicts with Register status {status}")


def validate_usage_criticality(cell: str, context: str, errors: list[str]) -> None:
    value = normalized_label(cell)
    found = {
        label
        for label in DEPENDENCY_CRITICALITIES
        if re.search(rf"\b{re.escape(label)}\b", value)
    }
    if not found:
        errors.append(f"{context} has no valid Criticality classification")


def validate_recovery_modes(cell: str, context: str, errors: list[str]) -> None:
    value = normalized_label(cell)
    parts = [
        part.strip()
        for part in re.split(r"\s*(?:<br\s*/?>|[,;/])\s*", value, flags=re.I)
        if part.strip()
    ]
    if not parts or any(part not in RECOVERY_MODES for part in parts):
        errors.append(f"{context} has invalid Recovery value(s): {value or '<empty>'}")


def anchored_sections(text: str, identifier_re: re.Pattern[str]) -> dict[str, str]:
    matches = list(
        re.finditer(
            rf"^##\s+`?(?P<identifier>{identifier_re.pattern})`?(?:\s+[—-].*)?\s*$",
            text,
            re.M,
        )
    )
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        identifier = match.group("identifier")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[identifier] = text[match.end() : end]
    return sections


def validate_source_citations(
    document: Path,
    repo: Path | None,
    errors: list[str],
) -> None:
    if repo is None:
        return
    text = document.read_text(encoding="utf-8")
    citations = list(SOURCE_CITATION_RE.finditer(text))
    if not citations:
        errors.append(f"reader document has no source citations: {document.name}")
        return

    checked: set[tuple[str, int, int | None]] = set()
    for match in citations:
        rel = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end")) if match.group("end") else None
        key = (rel, start, end)
        if key in checked:
            continue
        checked.add(key)
        source = (repo / rel).resolve()
        if not within_root(source, repo):
            errors.append(f"source citation escapes repository: {document.name} -> {rel}")
            continue
        if not source.is_file():
            errors.append(f"cited source does not exist: {document.name} -> {rel}")
            continue
        if end is not None and end < start:
            errors.append(f"invalid source line range: {document.name} -> {rel}:{start}-{end}")
            continue
        try:
            line_count = sum(1 for _ in source.open(encoding="utf-8", errors="replace"))
        except OSError as exc:
            errors.append(f"cannot read cited source {rel}: {exc}")
            continue
        final_line = end or start
        if start < 1 or final_line > line_count:
            suffix = f"-{end}" if end is not None else ""
            errors.append(
                f"source citation outside file bounds: {document.name} -> "
                f"{rel}:{start}{suffix}"
            )


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


def validate_http_register(register: Path) -> DomainResult:
    errors: list[str] = []
    partial = False
    call_ids: set[str] = set()
    usages_by_call: dict[str, set[str]] = {}
    usage_to_call: dict[str, str] = {}
    mapping_directions: dict[str, str] = {}
    call_statuses: dict[str, str] = {}
    usage_statuses: dict[str, str] = {}
    mapping_statuses: dict[str, str] = {}
    if not register.is_file():
        return DomainResult("invalid", errors=[f"repository register is missing: {register}"])

    text = register.read_text(encoding="utf-8")
    if section_value(text, "Proven outbound HTTP calls and mappings"):
        errors.append("repository register still uses the legacy flattened outbound HTTP table")

    operation_header, operation_rows = table_in_section(text, "Outbound HTTP operation records")
    usage_header, usage_rows = table_in_section(text, "Outbound HTTP operation usages")
    mapping_header, mapping_rows = table_in_section(text, "External HTTP field mapping records")

    for row in operation_rows:
        if len(row) != len(REGISTER_OPERATION_HEADERS):
            errors.append("repository register outbound operation row has the wrong number of columns")
            partial = True
            continue
        call_id = code_value(row[0])
        if not CALL_ID_RE.fullmatch(call_id):
            errors.append(f"invalid outbound Call ID in repository register: {call_id or '<empty>'}")
            partial = True
            continue
        if call_id in call_ids:
            errors.append(f"duplicate outbound Call ID in repository register: {call_id}")
            partial = True
            continue
        call_ids.add(call_id)
        usages_by_call.setdefault(call_id, set())
        call_statuses[call_id] = code_value(row[7])
        validate_exact_label(row[7], EVIDENCE_STATUSES, f"Outbound Call {call_id} Status", errors)

    usage_refs_by_id: dict[str, str] = {}
    for row in usage_rows:
        if len(row) != len(REGISTER_USAGE_HEADERS):
            errors.append("repository register outbound usage row has the wrong number of columns")
            partial = True
            continue
        usage_id = code_value(row[0])
        call_id = code_value(row[1])
        if not USAGE_ID_RE.fullmatch(usage_id):
            errors.append(f"invalid outbound Usage ID in repository register: {usage_id or '<empty>'}")
            partial = True
            continue
        if usage_id in usage_to_call:
            errors.append(f"duplicate outbound Usage ID in repository register: {usage_id}")
            partial = True
            continue
        usage_to_call[usage_id] = call_id
        usage_refs_by_id[usage_id] = call_id
        usage_statuses[usage_id] = code_value(row[5])
        validate_exact_label(row[5], EVIDENCE_STATUSES, f"Outbound Usage {usage_id} Status", errors)
        if not usage_id.startswith(f"{call_id}-U"):
            errors.append(f"outbound Usage ID does not belong to its Call ID: {usage_id} -> {call_id}")

    mapping_refs: list[tuple[str, str, str]] = []
    for row in mapping_rows:
        if len(row) != len(REGISTER_MAPPING_HEADERS):
            errors.append("repository register outbound mapping row has the wrong number of columns")
            partial = True
            continue
        mapping_id = code_value(row[0])
        call_id = code_value(row[1])
        applies_to = code_value(row[2])
        direction = code_value(row[3]).lower()
        if not MAPPING_ID_RE.fullmatch(mapping_id):
            errors.append(f"invalid outbound Mapping ID in repository register: {mapping_id or '<empty>'}")
            partial = True
            continue
        if mapping_id in mapping_directions:
            errors.append(f"duplicate outbound Mapping ID in repository register: {mapping_id}")
            partial = True
            continue
        mapping_directions[mapping_id] = direction
        mapping_statuses[mapping_id] = code_value(row[9])
        validate_exact_label(row[9], EVIDENCE_STATUSES, f"Outbound Mapping {mapping_id} Status", errors)
        mapping_refs.append((mapping_id, call_id, applies_to))
        if direction not in {"eapi-to-external", "external-to-eapi"}:
            errors.append(f"outbound Mapping {mapping_id} has an invalid direction: {direction}")

    if not partial:
        for usage_id, call_id in sorted(usage_refs_by_id.items()):
            if call_id not in call_ids:
                errors.append(f"outbound Usage {usage_id} references unknown Call ID: {call_id}")
                continue
            usages_by_call.setdefault(call_id, set()).add(usage_id)
        for call_id in sorted(call_ids):
            if not usages_by_call.get(call_id):
                errors.append(f"outbound Call has no executable Usage in repository register: {call_id}")
        for mapping_id, call_id, applies_to in mapping_refs:
            if call_id not in call_ids:
                errors.append(f"outbound Mapping {mapping_id} references unknown Call ID: {call_id}")
                continue
            if applies_to.lower() == "all":
                continue
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

    return DomainResult(
        "partial" if partial else "valid",
        {
            "call_ids": call_ids,
            "usages_by_call": usages_by_call,
            "usage_to_call": usage_to_call,
            "mapping_directions": mapping_directions,
            "call_statuses": call_statuses,
            "usage_statuses": usage_statuses,
            "mapping_statuses": mapping_statuses,
        },
        errors,
    )


def validate_dependency_register(
    register: Path,
    call_ids: set[str] | None,
) -> DomainResult:
    errors: list[str] = []
    partial = False
    dependency_ids: set[str] = set()
    operations_by_dependency: dict[str, set[str]] = {}
    http_refs_by_operation: dict[str, set[str]] = {}
    dependency_statuses: dict[str, str] = {}
    operation_statuses: dict[str, str] = {}
    if not register.is_file():
        return DomainResult("invalid", errors=[f"repository register is missing: {register}"])

    text = register.read_text(encoding="utf-8")
    if section_value(text, "External dependencies"):
        errors.append("repository register still uses the legacy flattened External dependencies table")

    observation_header, observation_rows = table_in_section(
        text, "External dependency observations"
    )
    contract_header, contract_rows = table_in_section(text, "Dependency contract records")
    operation_header, operation_rows = table_in_section(text, "Dependency operation records")

    observation_assignments: dict[str, str] = {}
    for row in observation_rows:
        if len(row) != len(REGISTER_DEPENDENCY_OBSERVATION_HEADERS):
            errors.append("repository register Dependency Observation row has the wrong column count")
            partial = True
            continue
        observation_id = code_value(row[0])
        if not DEPENDENCY_OBSERVATION_ID_RE.fullmatch(observation_id):
            errors.append(
                f"invalid Dependency Observation ID: {observation_id or '<empty>'}"
            )
            partial = True
            continue
        if observation_id in observation_assignments:
            errors.append(f"duplicate Dependency Observation ID: {observation_id}")
            partial = True
            continue
        validate_exact_label(
            row[7], EVIDENCE_STATUSES, f"Dependency Observation {observation_id} Status", errors
        )
        reconciliation = code_value(row[9])
        if reconciliation != "Unresolved" and not DEPENDENCY_ID_RE.fullmatch(reconciliation):
            errors.append(
                f"Dependency Observation {observation_id} has invalid reconciliation: "
                f"{reconciliation or '<empty>'}"
            )
        observation_assignments[observation_id] = reconciliation

    contract_observations: dict[str, set[str]] = {}
    declared_operations: dict[str, set[str]] = {}
    for row in contract_rows:
        if len(row) != len(REGISTER_DEPENDENCY_CONTRACT_HEADERS):
            errors.append("repository register Dependency Contract row has the wrong column count")
            partial = True
            continue
        dependency_id = code_value(row[0])
        if not DEPENDENCY_ID_RE.fullmatch(dependency_id):
            errors.append(f"invalid Dependency ID: {dependency_id or '<empty>'}")
            partial = True
            continue
        if dependency_id in dependency_ids:
            errors.append(f"duplicate Dependency ID: {dependency_id}")
            partial = True
            continue
        dependency_ids.add(dependency_id)
        dependency_statuses[dependency_id] = code_value(row[9])
        operations_by_dependency.setdefault(dependency_id, set())
        validate_exact_label(
            row[9], EVIDENCE_STATUSES, f"Dependency Contract {dependency_id} Status", errors
        )
        validate_usage_criticality(
            row[6], f"Dependency Contract {dependency_id}", errors
        )
        observation_refs = set(DEPENDENCY_OBSERVATION_ID_RE.findall(row[7]))
        if not observation_refs:
            errors.append(f"Dependency Contract has no Observation IDs: {dependency_id}")
        contract_observations[dependency_id] = observation_refs
        declared_operations[dependency_id] = set(DEPENDENCY_OPERATION_ID_RE.findall(row[4]))

    operation_parents: dict[str, str] = {}
    for row in operation_rows:
        if len(row) != len(REGISTER_DEPENDENCY_OPERATION_HEADERS):
            errors.append("repository register Dependency Operation row has the wrong column count")
            partial = True
            continue
        operation_id = code_value(row[0])
        dependency_id = code_value(row[1])
        if not DEPENDENCY_OPERATION_ID_RE.fullmatch(operation_id):
            errors.append(f"invalid Dependency Operation ID: {operation_id or '<empty>'}")
            partial = True
            continue
        if operation_id in operation_parents:
            errors.append(f"duplicate Dependency Operation ID: {operation_id}")
            partial = True
            continue
        operation_parents[operation_id] = dependency_id
        operation_statuses[operation_id] = code_value(row[8])
        if not DEPENDENCY_ID_RE.fullmatch(dependency_id):
            errors.append(
                f"Dependency Operation {operation_id} has invalid Dependency ID: "
                f"{dependency_id or '<empty>'}"
            )
        elif not operation_id.startswith(f"{dependency_id}-OP"):
            errors.append(
                f"Dependency Operation ID does not belong to its Dependency: "
                f"{operation_id} -> {dependency_id}"
            )
        operations_by_dependency.setdefault(dependency_id, set()).add(operation_id)
        validate_exact_label(
            row[8], EVIDENCE_STATUSES, f"Dependency Operation {operation_id} Status", errors
        )
        validate_usage_criticality(
            row[6], f"Dependency Operation {operation_id}", errors
        )
        http_refs = set(CALL_ID_RE.findall(row[2]))
        http_refs_by_operation[operation_id] = http_refs

    if not partial:
        if call_ids is not None:
            for operation_id, http_refs in sorted(http_refs_by_operation.items()):
                for call_id in sorted(http_refs - call_ids):
                    errors.append(
                        f"Dependency Operation {operation_id} references unknown outbound Call ID: {call_id}"
                    )
        for observation_id, reconciliation in sorted(observation_assignments.items()):
            if DEPENDENCY_ID_RE.fullmatch(reconciliation) and reconciliation not in dependency_ids:
                errors.append(
                    f"Dependency Observation {observation_id} references unknown Dependency: "
                    f"{reconciliation}"
                )
        for dependency_id, observation_refs in sorted(contract_observations.items()):
            for observation_id in sorted(observation_refs):
                if observation_id not in observation_assignments:
                    errors.append(
                        f"Dependency Contract {dependency_id} references unknown Observation: "
                        f"{observation_id}"
                    )
                elif observation_assignments[observation_id] != dependency_id:
                    errors.append(
                        f"Dependency Contract {dependency_id} references Observation assigned to "
                        f"{observation_assignments[observation_id]}: {observation_id}"
                    )
        for operation_id, dependency_id in sorted(operation_parents.items()):
            if dependency_id not in dependency_ids:
                errors.append(
                    f"Dependency Operation {operation_id} references unknown Dependency: {dependency_id}"
                )
        for dependency_id in sorted(dependency_ids):
            actual = operations_by_dependency.get(dependency_id, set())
            declared = declared_operations.get(dependency_id, set())
            if not actual:
                errors.append(f"Dependency Contract has no Operation record: {dependency_id}")
            for operation_id in sorted(declared - actual):
                errors.append(
                    f"Dependency Contract {dependency_id} declares unknown Operation: {operation_id}"
                )
            for operation_id in sorted(actual - declared):
                errors.append(
                    f"Dependency Operation is missing from its Contract record: "
                    f"{dependency_id} -> {operation_id}"
                )

    return DomainResult(
        "partial" if partial else "valid",
        {
            "dependency_ids": dependency_ids,
            "operations_by_dependency": operations_by_dependency,
            "http_refs_by_operation": http_refs_by_operation,
            "dependency_statuses": dependency_statuses,
            "operation_statuses": operation_statuses,
        },
        errors,
    )


def validate_failure_register(
    register: Path,
    dependency_ids: set[str] | None,
) -> DomainResult:
    errors: list[str] = []
    partial = False
    pattern_ids: set[str] = set()
    if not register.is_file():
        return DomainResult("invalid", errors=[f"repository register is missing: {register}"])

    text = register.read_text(encoding="utf-8")
    observation_header, observation_rows = table_in_section(text, "Failure observations")
    pattern_header, pattern_rows = table_in_section(text, "Failure pattern reconciliation")

    observation_assignments: dict[str, str] = {}
    for row in observation_rows:
        if len(row) != len(REGISTER_FAILURE_OBSERVATION_HEADERS):
            errors.append("repository register Failure Observation row has the wrong column count")
            partial = True
            continue
        observation_id = code_value(row[0])
        if not FAILURE_OBSERVATION_ID_RE.fullmatch(observation_id):
            errors.append(f"invalid Failure Observation ID: {observation_id or '<empty>'}")
            partial = True
            continue
        if observation_id in observation_assignments:
            errors.append(f"duplicate Failure Observation ID: {observation_id}")
            partial = True
            continue
        validate_exact_label(
            row[10], EVIDENCE_STATUSES, f"Failure Observation {observation_id} Status", errors
        )
        reconciliation = code_value(row[12])
        if reconciliation != "Unresolved" and not FAILURE_PATTERN_ID_RE.fullmatch(reconciliation):
            errors.append(
                f"Failure Observation {observation_id} has invalid reconciliation: "
                f"{reconciliation or '<empty>'}"
            )
        observation_assignments[observation_id] = reconciliation

    pattern_observations: dict[str, set[str]] = {}
    for row in pattern_rows:
        if len(row) != len(REGISTER_FAILURE_PATTERN_HEADERS):
            errors.append("repository register Failure Pattern row has the wrong column count")
            partial = True
            continue
        pattern_id = code_value(row[0])
        if not FAILURE_PATTERN_ID_RE.fullmatch(pattern_id):
            errors.append(f"invalid Failure Pattern ID: {pattern_id or '<empty>'}")
            partial = True
            continue
        if pattern_id in pattern_ids:
            errors.append(f"duplicate Failure Pattern ID: {pattern_id}")
            partial = True
            continue
        pattern_ids.add(pattern_id)
        observation_refs = set(FAILURE_OBSERVATION_ID_RE.findall(row[3]))
        if not observation_refs:
            errors.append(f"Failure Pattern has no Observation IDs: {pattern_id}")
        pattern_observations[pattern_id] = observation_refs
        if dependency_ids is not None:
            for dependency_id in sorted(set(DEPENDENCY_ID_RE.findall(row[5])) - dependency_ids):
                errors.append(
                    f"Failure Pattern {pattern_id} references unknown Dependency: {dependency_id}"
                )
        validate_exact_label(
            row[6], CALLER_VISIBILITIES, f"Failure Pattern {pattern_id} Caller visibility", errors
        )
        validate_exact_label(
            row[7], STATE_OUTCOMES, f"Failure Pattern {pattern_id} State outcome", errors
        )
        validate_exact_label(
            row[8], RETRY_SAFETIES, f"Failure Pattern {pattern_id} Retry safety", errors
        )
        validate_recovery_modes(row[9], f"Failure Pattern {pattern_id}", errors)
        validate_exact_label(
            row[10], RISK_ATTENTIONS, f"Failure Pattern {pattern_id} Risk attention", errors
        )

    if not partial:
        for observation_id, reconciliation in sorted(observation_assignments.items()):
            if FAILURE_PATTERN_ID_RE.fullmatch(reconciliation) and reconciliation not in pattern_ids:
                errors.append(
                    f"Failure Observation {observation_id} references unknown Pattern: {reconciliation}"
                )
        for pattern_id, observation_refs in sorted(pattern_observations.items()):
            for observation_id in sorted(observation_refs):
                if observation_id not in observation_assignments:
                    errors.append(
                        f"Failure Pattern {pattern_id} references unknown Observation: {observation_id}"
                    )
                elif observation_assignments[observation_id] != pattern_id:
                    errors.append(
                        f"Failure Pattern {pattern_id} references Observation assigned to "
                        f"{observation_assignments[observation_id]}: {observation_id}"
                    )

    return DomainResult(
        "partial" if partial else "valid",
        {"pattern_ids": pattern_ids},
        errors,
    )


def validate_config_register(register: Path) -> DomainResult:
    errors: list[str] = []
    partial = False
    if not register.is_file():
        return DomainResult("invalid", errors=[f"repository register is missing: {register}"])
    text = register.read_text(encoding="utf-8")
    _, observation_rows = table_in_section(text, "Runtime configuration observations")
    _, config_rows = table_in_section(text, "Runtime configuration records")
    _, impact_rows = table_in_section(text, "Runtime configuration impact records")

    observations: dict[str, str] = {}
    configs: dict[str, set[str]] = {}
    config_statuses: dict[str, str] = {}
    impacts: dict[str, dict[str, str]] = {}
    impact_statuses: dict[str, str] = {}

    for row in observation_rows:
        if len(row) != len(REGISTER_CONFIG_OBSERVATION_HEADERS):
            errors.append("repository register Config Observation row has the wrong column count")
            partial = True
            continue
        observation_id = code_value(row[0])
        if not CONFIG_OBSERVATION_ID_RE.fullmatch(observation_id):
            errors.append(f"invalid Config Observation ID: {observation_id or '<empty>'}")
            partial = True
            continue
        if observation_id in observations:
            errors.append(f"duplicate Config Observation ID: {observation_id}")
            partial = True
            continue
        validate_exact_label(
            row[7], EVIDENCE_STATUSES, f"Config Observation {observation_id} Status", errors
        )
        reconciliation = code_value(row[9])
        if reconciliation != "Unresolved" and not CONFIG_ID_RE.fullmatch(reconciliation):
            errors.append(
                f"Config Observation {observation_id} has invalid reconciliation: "
                f"{reconciliation or '<empty>'}"
            )
        observations[observation_id] = reconciliation

    for row in config_rows:
        if len(row) != len(REGISTER_CONFIG_RECORD_HEADERS):
            errors.append("repository register Config row has the wrong column count")
            partial = True
            continue
        config_id = code_value(row[0])
        if not CONFIG_ID_RE.fullmatch(config_id):
            errors.append(f"invalid Config ID: {config_id or '<empty>'}")
            partial = True
            continue
        if config_id in configs:
            errors.append(f"duplicate Config ID: {config_id}")
            partial = True
            continue
        refs = set(CONFIG_OBSERVATION_ID_RE.findall(row[5]))
        if not refs:
            errors.append(f"Config record has no Observation IDs: {config_id}")
        configs[config_id] = refs
        config_statuses[config_id] = code_value(row[6])
        validate_exact_label(
            row[6], EVIDENCE_STATUSES, f"Config {config_id} Status", errors
        )

    for row in impact_rows:
        if len(row) != len(REGISTER_CONFIG_IMPACT_HEADERS):
            errors.append("repository register Config Impact row has the wrong column count")
            partial = True
            continue
        impact_id = code_value(row[0])
        config_id = code_value(row[1])
        if not CONFIG_IMPACT_ID_RE.fullmatch(impact_id):
            errors.append(f"invalid Config Impact ID: {impact_id or '<empty>'}")
            partial = True
            continue
        if impact_id in impacts:
            errors.append(f"duplicate Config Impact ID: {impact_id}")
            partial = True
            continue
        if not impact_id.startswith(f"{config_id}-I"):
            errors.append(
                f"Config Impact ID does not belong to its Config: {impact_id} -> {config_id}"
            )
        impact_type = normalized_label(row[4]).lower()
        if impact_type not in CONFIG_IMPACT_TYPES:
            errors.append(
                f"Config Impact {impact_id} has invalid impact type: "
                f"{impact_type or '<empty>'}"
            )
        impact_statuses[impact_id] = code_value(row[8])
        validate_exact_label(
            row[8], EVIDENCE_STATUSES, f"Config Impact {impact_id} Status", errors
        )
        impacts[impact_id] = {
            "config_id": config_id,
            "behavior_id": code_value(row[2]),
            "endpoint_ids": code_value(row[3]),
            "impact_type": impact_type,
        }

    if not partial:
        for observation_id, reconciliation in sorted(observations.items()):
            if CONFIG_ID_RE.fullmatch(reconciliation) and reconciliation not in configs:
                errors.append(
                    f"Config Observation {observation_id} references unknown Config: {reconciliation}"
                )
        for config_id, refs in sorted(configs.items()):
            for observation_id in sorted(refs):
                if observation_id not in observations:
                    errors.append(
                        f"Config {config_id} references unknown Observation: {observation_id}"
                    )
                elif observations[observation_id] != config_id:
                    errors.append(
                        f"Config {config_id} references Observation assigned to "
                        f"{observations[observation_id]}: {observation_id}"
                    )
        for impact_id, impact in sorted(impacts.items()):
            if impact["config_id"] not in configs:
                errors.append(
                    f"Config Impact {impact_id} references unknown Config: {impact['config_id']}"
                )

    return DomainResult(
        "partial" if partial else "valid",
        {
            "config_ids": set(configs),
            "config_statuses": config_statuses,
            "impact_ids": set(impacts),
            "impacts": impacts,
            "impact_statuses": impact_statuses,
        },
        errors,
    )


def validate_java_register(register: Path) -> DomainResult:
    errors: list[str] = []
    partial = False
    if not register.is_file():
        return DomainResult("invalid", errors=[f"repository register is missing: {register}"])
    text = register.read_text(encoding="utf-8")
    _, type_rows = table_in_section(text, "Java type records")
    _, edge_rows = table_in_section(text, "Java dependency edge records")
    _, binding_rows = table_in_section(
        text, "Behavior and endpoint Java implementation bindings"
    )

    type_ids: set[str] = set()
    edge_ids: set[str] = set()
    binding_ids: set[str] = set()
    type_relationships: dict[str, tuple[str, str]] = {}
    edges: dict[str, tuple[str, str]] = {}
    edge_behaviors: dict[str, str] = {}
    bindings: dict[str, dict[str, str]] = {}

    for row in type_rows:
        if len(row) != len(REGISTER_JAVA_TYPE_HEADERS):
            errors.append("repository register Java Type row has the wrong column count")
            partial = True
            continue
        type_id = code_value(row[0])
        if not JAVA_TYPE_ID_RE.fullmatch(type_id):
            errors.append(f"invalid Java Type ID: {type_id or '<empty>'}")
            partial = True
            continue
        if type_id in type_ids:
            errors.append(f"duplicate Java Type ID: {type_id}")
            partial = True
            continue
        type_ids.add(type_id)
        type_relationships[type_id] = (row[4], row[5])
        validate_exact_label(
            row[6], EVIDENCE_STATUSES, f"Java Type {type_id} Status", errors
        )

    for row in edge_rows:
        if len(row) != len(REGISTER_JAVA_EDGE_HEADERS):
            errors.append("repository register Java Edge row has the wrong column count")
            partial = True
            continue
        edge_id = code_value(row[0])
        if not JAVA_EDGE_ID_RE.fullmatch(edge_id):
            errors.append(f"invalid Java Edge ID: {edge_id or '<empty>'}")
            partial = True
            continue
        if edge_id in edge_ids:
            errors.append(f"duplicate Java Edge ID: {edge_id}")
            partial = True
            continue
        relation = normalized_label(row[2])
        if relation not in JAVA_EDGE_RELATIONS:
            errors.append(
                f"Java Edge {edge_id} has invalid relation: {relation or '<empty>'}"
            )
        edge_ids.add(edge_id)
        edges[edge_id] = (code_value(row[1]), code_value(row[3]))
        edge_behaviors[edge_id] = row[4]
        validate_exact_label(
            row[6], EVIDENCE_STATUSES, f"Java Edge {edge_id} Status", errors
        )

    for row in binding_rows:
        if len(row) != len(REGISTER_JAVA_BINDING_HEADERS):
            errors.append("repository register Java Binding row has the wrong column count")
            partial = True
            continue
        binding_id = code_value(row[0])
        if not JAVA_BINDING_ID_RE.fullmatch(binding_id):
            errors.append(f"invalid Java Binding ID: {binding_id or '<empty>'}")
            partial = True
            continue
        if binding_id in binding_ids:
            errors.append(f"duplicate Java Binding ID: {binding_id}")
            partial = True
            continue
        binding_ids.add(binding_id)
        bindings[binding_id] = {
            "behavior_id": code_value(row[1]),
            "endpoint_ids": code_value(row[2]),
            "type_ids": row[4],
            "edge_ids": row[5],
        }
        validate_exact_label(
            row[7], EVIDENCE_STATUSES, f"Java Binding {binding_id} Status", errors
        )

    if not partial:
        for edge_id, (source_id, target_id) in sorted(edges.items()):
            if source_id not in type_ids:
                errors.append(f"Java Edge {edge_id} references unknown source Type: {source_id}")
            if target_id not in type_ids:
                errors.append(f"Java Edge {edge_id} references unknown target Type: {target_id}")
        for binding_id, binding in sorted(bindings.items()):
            for type_id in sorted(set(JAVA_TYPE_ID_RE.findall(binding["type_ids"]))):
                if type_id not in type_ids:
                    errors.append(
                        f"Java Binding {binding_id} references unknown Type: {type_id}"
                    )
            for edge_id in sorted(set(JAVA_EDGE_ID_RE.findall(binding["edge_ids"]))):
                if edge_id not in edge_ids:
                    errors.append(
                        f"Java Binding {binding_id} references unknown Edge: {edge_id}"
                    )

    return DomainResult(
        "partial" if partial else "valid",
        {
            "type_ids": type_ids,
            "edge_ids": edge_ids,
            "binding_ids": binding_ids,
            "type_relationships": type_relationships,
            "edge_behaviors": edge_behaviors,
            "bindings": bindings,
        },
        errors,
    )


def validate_config_java_reader_identities(
    root: Path,
    config_result: DomainResult,
    java_result: DomainResult,
) -> tuple[list[str], list[str]]:
    """Check Config/Java relationships against declared Behavior/Endpoint IDs."""

    behavior_ids, endpoint_ids = pack_behavior_and_endpoint_ids(root)
    config_errors: list[str] = []
    java_errors: list[str] = []

    if config_result.status == "valid":
        for impact_id, impact in sorted(config_result.data["impacts"].items()):
            behavior_id = impact["behavior_id"]
            if behavior_id not in behavior_ids:
                config_errors.append(
                    f"Config Impact {impact_id} references unknown Behavior: {behavior_id}"
                )
            for endpoint_id in sorted(
                stable_endpoint_references(impact["endpoint_ids"])
            ):
                if endpoint_id not in endpoint_ids:
                    config_errors.append(
                        f"Config Impact {impact_id} references unknown Endpoint: "
                        f"{endpoint_id}"
                    )

    if java_result.status == "valid":
        for type_id, (behavior_refs, endpoint_refs) in sorted(
            java_result.data["type_relationships"].items()
        ):
            for behavior_id in sorted(stable_endpoint_references(behavior_refs)):
                if behavior_id not in behavior_ids:
                    java_errors.append(
                        f"Java Type {type_id} references unknown Behavior: {behavior_id}"
                    )
            for endpoint_id in sorted(stable_endpoint_references(endpoint_refs)):
                if endpoint_id not in endpoint_ids:
                    java_errors.append(
                        f"Java Type {type_id} references unknown Endpoint: {endpoint_id}"
                    )
        for edge_id, behavior_refs in sorted(
            java_result.data["edge_behaviors"].items()
        ):
            for behavior_id in sorted(stable_endpoint_references(behavior_refs)):
                if behavior_id not in behavior_ids:
                    java_errors.append(
                        f"Java Edge {edge_id} references unknown Behavior: {behavior_id}"
                    )
        for binding_id, binding in sorted(java_result.data["bindings"].items()):
            behavior_id = binding["behavior_id"]
            if behavior_id not in behavior_ids:
                java_errors.append(
                    f"Java Binding {binding_id} references unknown Behavior: "
                    f"{behavior_id}"
                )
            for endpoint_id in sorted(
                stable_endpoint_references(binding["endpoint_ids"])
            ):
                if endpoint_id not in endpoint_ids:
                    java_errors.append(
                        f"Java Binding {binding_id} references unknown Endpoint: "
                        f"{endpoint_id}"
                    )
    return config_errors, java_errors


def validate_field_mapping_document(
    document: Path,
    register_call_ids: set[str],
    register_usages_by_call: dict[str, set[str]],
    register_usage_to_call: dict[str, str],
    register_mapping_directions: dict[str, str],
    register_call_statuses: dict[str, str],
    register_usage_statuses: dict[str, str],
    register_mapping_statuses: dict[str, str],
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
        call_match = CALL_ID_RE.search(row[0])
        call_id = call_match.group(0) if call_match else ""
        if not call_id:
            errors.append("invalid Call ID in Field Validation and Mapping index: <empty>")
            continue
        if call_id in index_call_ids:
            errors.append(f"duplicate Call ID in Field Validation and Mapping index: {call_id}")
        index_call_ids.add(call_id)
        if call_id in register_call_statuses:
            validate_reader_status_qualifier(
                row[0], register_call_statuses[call_id], f"Outbound Call {call_id}", errors
            )
        anchor = call_id.lower()
        if not re.search(rf"\]\(#{re.escape(anchor)}\)", row[5]):
            errors.append(f"Field operation index does not link its Call anchor: {call_id}")

    call_heading_matches = list(
        re.finditer(r"^##\s+`?(?P<call>HTTP-\d+)`?(?:\s+.*)?$", text, re.M)
    )
    section_call_ids: set[str] = set()
    final_usage_ids: set[str] = set()
    final_mapping_ids: set[str] = set()
    final_mapping_directions: dict[str, str] = {}
    final_usages_by_call: dict[str, set[str]] = {}
    usage_summaries_by_call: dict[str, str] = {}

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
        overview_rows = rows_after_header(section, FIELD_OVERVIEW_HEADERS)
        if not overview_rows:
            errors.append(f"Field Call Overview has no valid summary table: {call_id}")
        elif len(overview_rows[0]) != len(FIELD_OVERVIEW_HEADERS):
            errors.append(f"Field Call Overview row has the wrong column count: {call_id}")
        else:
            usage_summaries_by_call[call_id] = overview_rows[0][5]
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
            usage_match = USAGE_ID_RE.search(cells[0])
            mapping_match = MAPPING_ID_RE.search(cells[0])
            if usage_match:
                first = usage_match.group(0)
                if len(cells) != len(FIELD_USAGE_HEADERS):
                    errors.append(f"Field Usage row has the wrong column count: {first}")
                    continue
                if first in final_usage_ids:
                    errors.append(f"duplicate Usage ID in Field Validation and Mapping: {first}")
                final_usage_ids.add(first)
                if first in register_usage_statuses:
                    validate_reader_status_qualifier(
                        cells[0], register_usage_statuses[first], f"Outbound Usage {first}", errors
                    )
                final_usages_by_call.setdefault(call_id, set()).add(first)
                if not first.startswith(f"{call_id}-U"):
                    errors.append(f"Usage ID appears under the wrong Call section: {first} -> {call_id}")
            elif mapping_match:
                first = mapping_match.group(0)
                if len(cells) != len(FIELD_MAPPING_HEADERS):
                    errors.append(f"Field Mapping row has the wrong column count: {first}")
                    continue
                if first in final_mapping_ids:
                    errors.append(f"duplicate Mapping ID in Field Validation and Mapping: {first}")
                final_mapping_ids.add(first)
                if first in register_mapping_statuses:
                    validate_reader_status_qualifier(
                        cells[0], register_mapping_statuses[first], f"Outbound Mapping {first}", errors
                    )
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
        elif len(usage_ids) == 1:
            usage_id = next(iter(usage_ids))
            if usage_id not in final_usage_ids:
                summary = usage_summaries_by_call.get(call_id, "")
                if usage_id not in summary:
                    errors.append(
                        f"single-usage outbound Call summary omits Usage ID: {usage_id}"
                    )
                elif usage_id in register_usage_statuses:
                    validate_reader_status_qualifier(
                        summary,
                        register_usage_statuses[usage_id],
                        f"Outbound Usage {usage_id}",
                        errors,
                    )
    for usage_id in sorted(final_usage_ids):
        if usage_id not in register_usage_to_call:
            errors.append(f"Field document contains an unregistered Usage ID: {usage_id}")

    return section_call_ids


def validate_behavior_call_links(
    root: Path,
    call_ids: set[str],
    call_statuses: dict[str, str],
    errors: list[str],
) -> None:
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
            link_match = re.search(
                rf"^(?P<line>[^\n]*\]\({re.escape(expected_target)}\)[^\n]*)$",
                text,
                re.M,
            )
            if link_match and call_id in call_statuses:
                visible = link_match.group("line")
                validate_reader_status_qualifier(
                    visible,
                    call_statuses[call_id],
                    f"Tech Behavior {behavior.relative_to(root)} outbound Call {call_id}",
                    errors,
                )


def validate_external_dependency_document(
    document: Path,
    dependency_ids: set[str],
    operations_by_dependency: dict[str, set[str]],
    http_refs_by_operation: dict[str, set[str]],
    dependency_statuses: dict[str, str],
    operation_statuses: dict[str, str],
    repo: Path | None,
    errors: list[str],
) -> None:
    if not document.is_file():
        if dependency_ids:
            errors.append("Dependency Contracts exist but external-dependency-contracts.md is missing")
        return
    if not dependency_ids:
        errors.append("external-dependency-contracts.md exists without reconciled Dependency Contracts")
        return

    text = document.read_text(encoding="utf-8")
    validate_source_citations(document, repo, errors)
    if section_value(text, "Observed operations and contracts"):
        errors.append("External Dependency Contracts still uses the legacy operation/evidence layout")
    if section_value(text, "External dependency observations"):
        errors.append("External Dependency Contracts publishes the working Observation inventory")

    index_header, index_rows = table_in_section(text, "Dependency landscape")
    if index_header != DEPENDENCY_LANDSCAPE_HEADERS:
        errors.append("External Dependency landscape columns are invalid")

    index_ids: set[str] = set()
    for row in index_rows:
        if len(row) != len(DEPENDENCY_LANDSCAPE_HEADERS):
            errors.append("External Dependency landscape row has the wrong column count")
            continue
        match = DEPENDENCY_ID_RE.search(row[0])
        if not match:
            errors.append("External Dependency landscape row is missing a Dependency ID")
            continue
        dependency_id = match.group(0)
        if dependency_id in index_ids:
            errors.append(f"duplicate Dependency landscape ID: {dependency_id}")
        index_ids.add(dependency_id)
        if dependency_id in dependency_statuses:
            validate_reader_status_qualifier(
                row[0], dependency_statuses[dependency_id], f"Dependency {dependency_id}", errors
            )
        validate_exact_label(
            row[3],
            DEPENDENCY_CRITICALITIES,
            f"Dependency landscape {dependency_id} Criticality",
            errors,
        )
        if not re.search(rf"\]\(#{re.escape(dependency_id.lower())}\)", row[5]):
            errors.append(f"Dependency landscape does not link its detail anchor: {dependency_id}")

    sections = anchored_sections(text, DEPENDENCY_ID_RE)
    section_ids = set(sections)
    for dependency_id in sorted(section_ids):
        anchor = dependency_id.lower()
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(anchor)}[\"']\s*></a>\s*\n\s*"
            rf"##\s+`?{re.escape(dependency_id)}`?",
            text,
            re.I,
        ):
            errors.append(f"External Dependency document is missing stable anchor: {dependency_id}")

    for dependency_id in sorted(dependency_ids - index_ids):
        errors.append(f"registered Dependency is missing from the landscape: {dependency_id}")
    for dependency_id in sorted(index_ids - dependency_ids):
        errors.append(f"Dependency landscape ID is missing from the register: {dependency_id}")
    for dependency_id in sorted(dependency_ids - section_ids):
        errors.append(f"registered Dependency is missing its detail section: {dependency_id}")
    for dependency_id in sorted(section_ids - dependency_ids):
        errors.append(f"Dependency detail section is missing from the register: {dependency_id}")

    for dependency_id in sorted(dependency_ids):
        operation_ids = operations_by_dependency.get(dependency_id, set())
        section = sections.get(dependency_id, "")
        if operation_ids and not any(
            table_cells(line) == DEPENDENCY_OPERATION_DOCUMENT_HEADERS
            for line in section.splitlines()
            if line.strip().startswith("|")
        ):
            errors.append(
                f"Dependency detail section has no valid Operation table: {dependency_id}"
            )
        operation_rows = rows_after_header(section, DEPENDENCY_OPERATION_DOCUMENT_HEADERS)
        published_operations: set[str] = set()
        for row in operation_rows:
            if len(row) != len(DEPENDENCY_OPERATION_DOCUMENT_HEADERS):
                errors.append(f"Dependency Operation row has the wrong column count: {dependency_id}")
                continue
            match = DEPENDENCY_OPERATION_ID_RE.search(row[0])
            if not match:
                errors.append(f"Dependency Operation row is missing an Operation ID: {dependency_id}")
                continue
            operation_id = match.group(0)
            published_operations.add(operation_id)
            if operation_id in operation_statuses:
                validate_reader_status_qualifier(
                    row[0], operation_statuses[operation_id], f"Dependency Operation {operation_id}", errors
                )
        for operation_id in sorted(published_operations - operation_ids):
            errors.append(f"Dependency detail section contains an unregistered Operation: {operation_id}")
        for operation_id in sorted(operation_ids):
            if not re.search(rf"\b{re.escape(operation_id)}\b", section):
                errors.append(
                    f"Dependency Operation is missing from its final section: {operation_id}"
                )
            for call_id in sorted(http_refs_by_operation.get(operation_id, set())):
                expected = f"field-validation-and-mapping.md#{call_id.lower()}"
                if not re.search(rf"\]\({re.escape(expected)}\)", section):
                    errors.append(
                        f"Dependency Operation does not link its HTTP Call anchor: "
                        f"{operation_id} -> {call_id}"
                    )


def validate_failure_taxonomy_document(
    document: Path,
    pattern_ids: set[str],
    repo: Path | None,
    errors: list[str],
) -> None:
    if not document.is_file():
        if pattern_ids:
            errors.append("Failure Patterns exist but failure-taxonomy.md is missing")
        return
    if not pattern_ids:
        errors.append("failure-taxonomy.md exists without reconciled Failure Patterns")
        return

    text = document.read_text(encoding="utf-8")
    validate_source_citations(document, repo, errors)
    if section_value(text, "Failure observations"):
        errors.append("Failure Taxonomy publishes the working Failure Observation inventory")

    index_header, index_rows = table_in_section(text, "Failure pattern index")
    if index_header != FAILURE_PATTERN_INDEX_HEADERS:
        errors.append("Failure Pattern index columns are invalid")

    index_ids: set[str] = set()
    for row in index_rows:
        if len(row) != len(FAILURE_PATTERN_INDEX_HEADERS):
            errors.append("Failure Pattern index row has the wrong column count")
            continue
        match = FAILURE_PATTERN_ID_RE.search(row[0])
        if not match:
            errors.append("Failure Pattern index row is missing a Pattern ID")
            continue
        pattern_id = match.group(0)
        if pattern_id in index_ids:
            errors.append(f"duplicate Failure Pattern index ID: {pattern_id}")
        index_ids.add(pattern_id)
        validate_exact_label(
            row[3], CALLER_VISIBILITIES, f"Failure index {pattern_id} Caller visibility", errors
        )
        validate_exact_label(
            row[4], STATE_OUTCOMES, f"Failure index {pattern_id} State outcome", errors
        )
        validate_exact_label(
            row[5], RETRY_SAFETIES, f"Failure index {pattern_id} Retry safety", errors
        )
        validate_exact_label(
            row[6], RISK_ATTENTIONS, f"Failure index {pattern_id} Risk attention", errors
        )
        if not re.search(rf"\]\(#{re.escape(pattern_id.lower())}\)", row[7]):
            errors.append(f"Failure Pattern index does not link its detail anchor: {pattern_id}")

    sections = anchored_sections(text, FAILURE_PATTERN_ID_RE)
    section_ids = set(sections)
    for pattern_id in sorted(section_ids):
        anchor = pattern_id.lower()
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(anchor)}[\"']\s*></a>\s*\n\s*"
            rf"##\s+`?{re.escape(pattern_id)}`?",
            text,
            re.I,
        ):
            errors.append(f"Failure Taxonomy is missing stable anchor: {pattern_id}")

    for pattern_id in sorted(pattern_ids - index_ids):
        errors.append(f"registered Failure Pattern is missing from the index: {pattern_id}")
    for pattern_id in sorted(index_ids - pattern_ids):
        errors.append(f"Failure Pattern index ID is missing from the register: {pattern_id}")
    for pattern_id in sorted(pattern_ids - section_ids):
        errors.append(f"registered Failure Pattern is missing its detail section: {pattern_id}")
    for pattern_id in sorted(section_ids - pattern_ids):
        errors.append(f"Failure detail section is missing from the register: {pattern_id}")


def validate_java_implementation_document(
    document: Path,
    java_result: DomainResult,
    repo: Path | None,
    errors: list[str],
) -> None:
    type_ids: set[str] = java_result.data["type_ids"]
    edge_ids: set[str] = java_result.data["edge_ids"]
    binding_ids: set[str] = java_result.data["binding_ids"]
    if not type_ids and not edge_ids and not binding_ids:
        if document.is_file():
            errors.append(
                "Java Implementation Map exists but the Register contains no Java implementation records"
            )
        return
    if not document.is_file():
        errors.append("Java implementation records exist but java-implementation-map.md is missing")
        return
    text = document.read_text(encoding="utf-8")
    for type_id in sorted(type_ids):
        if type_id not in text:
            errors.append(f"Java Implementation Map omits registered Type: {type_id}")
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(type_id.lower())}[\"']\s*></a>",
            text,
            re.I,
        ):
            errors.append(f"Java Implementation Map is missing stable Type anchor: {type_id}")
    for edge_id in sorted(edge_ids):
        if edge_id not in text:
            errors.append(f"Java Implementation Map omits registered Edge: {edge_id}")
    for binding_id in sorted(binding_ids):
        if binding_id not in text:
            errors.append(f"Java Implementation Map omits registered Binding: {binding_id}")
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(binding_id.lower())}[\"']\s*></a>\s*\n\s*"
            rf"##\s+`?{re.escape(binding_id)}`?",
            text,
            re.I,
        ):
            errors.append(
                f"Java Implementation Map is missing stable implementation slice: {binding_id}"
            )
    validate_source_citations(document, repo, errors)


def validate_runtime_config_document(
    document: Path,
    config_result: DomainResult,
    repo: Path | None,
    errors: list[str],
) -> None:
    config_ids: set[str] = config_result.data["config_ids"]
    impact_ids: set[str] = config_result.data["impact_ids"]
    if not config_ids and not impact_ids:
        if document.is_file():
            errors.append(
                "Runtime Config Matrix exists but the Register contains no reconciled Config records"
            )
        return
    if not document.is_file():
        errors.append("reconciled Config records exist but runtime-config-matrix.md is missing")
        return
    text = document.read_text(encoding="utf-8")
    for config_id in sorted(config_ids):
        if config_id not in text:
            errors.append(f"Runtime Config Matrix omits registered Config: {config_id}")
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(config_id.lower())}[\"']\s*></a>",
            text,
            re.I,
        ):
            errors.append(f"Runtime Config Matrix is missing stable Config anchor: {config_id}")
    for impact_id in sorted(impact_ids):
        if impact_id not in text:
            errors.append(f"Runtime Config Matrix omits registered Impact: {impact_id}")
        if not re.search(
            rf"<a\s+(?:id|name)=[\"']{re.escape(impact_id.lower())}[\"']\s*></a>",
            text,
            re.I,
        ):
            errors.append(
                f"Runtime Config Matrix is missing stable Impact anchor: {impact_id}"
            )
    if impact_ids and "## Endpoint reverse impact index" not in text:
        errors.append("Runtime Config Matrix is missing the Endpoint reverse impact index")
    validate_source_citations(document, repo, errors)


def validate_behavior_repository_links(
    root: Path,
    dependency_ids: set[str] | None,
    dependency_statuses: dict[str, str] | None,
    pattern_ids: set[str] | None,
    java_binding_ids: set[str] | None,
    config_impact_ids: set[str] | None,
    errors: list[str],
) -> None:
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

        if dependency_ids is not None:
            dependency_block = yaml_block(frontmatter, "external_dependencies")
            behavior_dependencies = set(
                re.findall(
                    r"^\s*-\s+dependency_id:\s*[\"']?(DEP-\d+)[\"']?\s*$",
                    dependency_block,
                    re.M,
                )
            )
            for dependency_id in sorted(behavior_dependencies):
                if dependency_id not in dependency_ids:
                    errors.append(
                        f"Tech Behavior references unknown Dependency: "
                        f"{behavior.relative_to(root)} -> {dependency_id}"
                    )
                    continue
                expected = f"../external-dependency-contracts.md#{dependency_id.lower()}"
                if not re.search(rf"\]\({re.escape(expected)}\)", text):
                    errors.append(
                        f"Tech Behavior does not link its Dependency anchor: "
                        f"{behavior.relative_to(root)} -> {dependency_id}"
                    )
                link_match = re.search(
                    rf"^(?P<line>[^\n]*\]\({re.escape(expected)}\)[^\n]*)$",
                    text,
                    re.M,
                )
                if link_match and dependency_statuses and dependency_id in dependency_statuses:
                    validate_reader_status_qualifier(
                        link_match.group("line"),
                        dependency_statuses[dependency_id],
                        f"Tech Behavior {behavior.relative_to(root)} Dependency {dependency_id}",
                        errors,
                    )
            for dependency_id in set(
                re.findall(r"external-dependency-contracts\.md#(dep-\d+)", text, re.I)
            ):
                normalized = dependency_id.upper()
                if normalized not in dependency_ids:
                    errors.append(
                        f"Tech Behavior links unknown Dependency anchor: "
                        f"{behavior.relative_to(root)} -> {dependency_id}"
                    )

        if pattern_ids is not None:
            failure_block = yaml_block(frontmatter, "failure_patterns")
            behavior_patterns = set(FAILURE_PATTERN_ID_RE.findall(failure_block))
            for pattern_id in sorted(behavior_patterns):
                if pattern_id not in pattern_ids:
                    errors.append(
                        f"Tech Behavior references unknown Failure Pattern: "
                        f"{behavior.relative_to(root)} -> {pattern_id}"
                    )
                    continue
                expected = f"../failure-taxonomy.md#{pattern_id.lower()}"
                if not re.search(rf"\]\({re.escape(expected)}\)", text):
                    errors.append(
                        f"Tech Behavior does not link its Failure Pattern anchor: "
                        f"{behavior.relative_to(root)} -> {pattern_id}"
                    )
            for pattern_id in set(
                re.findall(r"failure-taxonomy\.md#(fail-\d+)", text, re.I)
            ):
                normalized = pattern_id.upper()
                if normalized not in pattern_ids:
                    errors.append(
                        f"Tech Behavior links unknown Failure Pattern anchor: "
                        f"{behavior.relative_to(root)} -> {pattern_id}"
                    )

        if java_binding_ids is not None:
            binding_entries = linked_document_entries(
                frontmatter, "java_bindings", "binding_id"
            )
            for binding_id, document in binding_entries:
                if binding_id not in java_binding_ids:
                    errors.append(
                        f"Tech Behavior references unknown Java Binding: "
                        f"{behavior.relative_to(root)} -> {binding_id}"
                    )
                    continue
                expected = f"../java-implementation-map.md#{binding_id.lower()}"
                if document != expected or not re.search(
                    rf"\]\({re.escape(expected)}\)", text
                ):
                    errors.append(
                        f"Tech Behavior does not link its Java implementation slice: "
                        f"{behavior.relative_to(root)} -> {binding_id}"
                    )

        if config_impact_ids is not None:
            impact_entries = linked_document_entries(
                frontmatter, "runtime_config_impacts", "impact_id"
            )
            for impact_id, document in impact_entries:
                if impact_id not in config_impact_ids:
                    errors.append(
                        f"Tech Behavior references unknown Config Impact: "
                        f"{behavior.relative_to(root)} -> {impact_id}"
                    )
                    continue
                expected = f"../runtime-config-matrix.md#{impact_id.lower()}"
                if document != expected or not re.search(
                    rf"\]\({re.escape(expected)}\)", text
                ):
                    errors.append(
                        f"Tech Behavior does not link its Runtime Config impact: "
                        f"{behavior.relative_to(root)} -> {impact_id}"
                    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack_root", type=Path)
    parser.add_argument(
        "--repo",
        type=Path,
        help="optional repository root for validating source citations in repository reader documents",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable validation report",
    )
    parser.add_argument(
        "--require-artifact-manifest",
        action="store_true",
        help="require and validate the versioned Artifact Manifest",
    )
    parser.add_argument(
        "--skip-artifact-manifest",
        action="store_true",
        help="skip Manifest only during executor post-promotion checks before State commit",
    )
    parser.add_argument(
        "--validation-profile",
        choices=sorted(VALIDATION_PROFILES),
        default="complete",
        help=(
            "validation maturity: tech-publication defers only missing future API/BA "
            "artifacts; complete requires the fully materialized Pack"
        ),
    )
    args = parser.parse_args()

    if not args.pack_root.is_dir():
        print(f"ERROR: pack root does not exist: {args.pack_root}")
        return 2

    root = args.pack_root.resolve()
    repo = args.repo.resolve() if args.repo is not None else None
    if repo is not None and not repo.is_dir():
        print(f"ERROR: repository directory does not exist: {args.repo}")
        return 2
    report = ValidationReport(args.validation_profile)

    manifest_path = root / ".work" / "artifact-manifest.json"
    if not args.skip_artifact_manifest and (
        args.require_artifact_manifest or manifest_path.is_file()
    ):
        try:
            artifact_errors = validate_artifact_manifest(root, load_registry())
        except ArtifactSchemaError as exc:
            artifact_errors = [str(exc)]
        report.add_errors("ARTIFACT-SCHEMA", artifact_errors)

    markdown_files = sorted(
        path for path in root.rglob("*.md") if ".work" not in path.relative_to(root).parts
    )
    fragment_cache: dict[Path, frozenset[str] | None] = {}
    for document in markdown_files:
        text = document.read_text(encoding="utf-8")
        document_errors: list[str] = []
        fragment_errors: list[str] = []
        if any(placeholder in text for placeholder in PLACEHOLDERS):
            document_errors.append(f"template placeholder remains: {document.relative_to(root)}")
        for reference in markdown_link_references(text):
            target = local_target(reference.raw_target)
            if target is None:
                continue
            report.checked_links += 1
            resolved = document if target.same_document else (document.parent / target.path).resolve()
            if not within_root(resolved, root):
                document_errors.append(
                    f"local link escapes pack root: {document.relative_to(root)}:{reference.line} "
                    f"-> {reference.raw_target}"
                )
            elif not resolved.exists():
                deferred_check = deferred_check_for_missing_target(
                    resolved, root, args.validation_profile
                )
                if deferred_check:
                    report.defer_link(
                        deferred_check,
                        document.relative_to(root).as_posix(),
                        reference.raw_target,
                    )
                else:
                    document_errors.append(
                        f"broken local link: {document.relative_to(root)}:{reference.line} "
                        f"-> {reference.raw_target}"
                    )
            elif target.fragment:
                if resolved.suffix.lower() != ".md":
                    report.warn(
                        "MARKDOWN-FRAGMENT-UNVERIFIED: "
                        f"{document.relative_to(root)}:{reference.line} -> {reference.raw_target} "
                        "targets a non-Markdown file"
                    )
                    continue
                fragment_ids = target_fragment_ids(
                    resolved, root, report, fragment_cache
                )
                if fragment_ids is None:
                    continue
                report.checked_fragments += 1
                if target.fragment not in fragment_ids:
                    fragment_errors.append(
                        f"fragment target does not exist: "
                        f"{document.relative_to(root)}:{reference.line} -> "
                        f"{reference.raw_target} (target {resolved.relative_to(root)})"
                    )
        report.add_errors("MARKDOWN-LINK", document_errors)
        report.add_errors("MARKDOWN-FRAGMENT", fragment_errors)

    catalog = root / "tech-pack" / "behavior-catalog.yaml"
    if catalog.is_file():
        catalog_text = catalog.read_text(encoding="utf-8")
        if any(placeholder in catalog_text for placeholder in PLACEHOLDERS):
            report.error(
                "CATALOG-DOCUMENT",
                "template placeholder remains: tech-pack/behavior-catalog.yaml",
            )
        for match in CATALOG_PATH_RE.finditer(catalog_text):
            target = match.group("target").strip()
            if target.lower() in {"null", "none"}:
                continue
            report.checked_links += 1
            resolved = (catalog.parent / target).resolve()
            if not within_root(resolved, root):
                report.error("CATALOG-LINK", f"catalog path escapes pack root: {target}")
            elif not resolved.exists():
                deferred_check = deferred_check_for_missing_target(
                    resolved, root, args.validation_profile
                )
                if deferred_check:
                    report.defer_link(
                        deferred_check,
                        catalog.relative_to(root).as_posix(),
                        target,
                    )
                else:
                    report.error("CATALOG-LINK", f"broken catalog document path: {target}")

    endpoint_matrix = root / "tech-pack" / "endpoint-matrix.md"
    if args.validation_profile == "complete" and endpoint_matrix.is_file():
        endpoint_errors: list[str] = []
        validate_endpoint_matrix(endpoint_matrix, root, endpoint_errors)
        report.add_errors("ENDPOINT-DOCUMENT", endpoint_errors)

    register = root / ".work" / "repository-register.md"
    schema_check = validate_register_file(register, _REGISTER_SCHEMA)
    if schema_check.errors:
        report.error("REG-SCHEMA-VERSION", "; ".join(schema_check.errors))
    schema_codes = {
        "lifecycle": "REG-LIFECYCLE-SCHEMA",
        "http": "REG-HTTP-SCHEMA",
        "config": "REG-CONFIG-SCHEMA",
        "java": "REG-JAVA-SCHEMA",
        "dependency": "REG-DEP-SCHEMA",
        "failure": "REG-FAIL-SCHEMA",
    }
    for domain, messages in schema_check.domain_errors.items():
        report.error(
            schema_codes.get(domain, f"REG-{domain.upper()}-SCHEMA"),
            " | ".join(messages),
        )

    def domain_schema_valid(domain: str) -> bool:
        return not schema_check.errors and not schema_check.domain_errors.get(domain)

    def prerequisites_available(group: str) -> bool:
        return all(
            report.domain_statuses.get(domain) == "valid"
            for domain in _REGISTER_SCHEMA.domain_dependencies[group]
        )

    lifecycle_schema: dict[str, Any] | None = None
    if domain_schema_valid("lifecycle"):
        try:
            lifecycle_schema = load_lifecycle_schema()
        except LifecycleSchemaError as exc:
            lifecycle_result = DomainResult("invalid", errors=[str(exc)])
        else:
            typed_lifecycle = validate_lifecycle_register(
                register, _REGISTER_SCHEMA, lifecycle_schema
            )
            lifecycle_result = DomainResult(
                typed_lifecycle.status,
                typed_lifecycle.data,
                typed_lifecycle.errors,
            )
        report.add_errors("REG-LIFECYCLE-ROW", lifecycle_result.errors)
    else:
        lifecycle_result = DomainResult("invalid")
    report.domain_statuses["lifecycle"] = lifecycle_result.status

    if prerequisites_available("lifecycle_document"):
        lifecycle_document_errors = validate_lifecycle_document(
            root / "tech-pack" / "data-lifecycle.md",
            lifecycle_result,
            repo,
            lifecycle_schema,
        )
        report.add_errors("LIFECYCLE-DOCUMENT", lifecycle_document_errors)
        behavior_lifecycle_errors = validate_behavior_lifecycle_projection(
            root, lifecycle_result
        )
        report.add_errors(
            "BEHAVIOR-LIFECYCLE-BACKLINK", behavior_lifecycle_errors
        )
    else:
        report.skip(
            "LIFECYCLE-DOCUMENT",
            f"prerequisite Lifecycle Register is {lifecycle_result.status}",
        )
        report.skip(
            "BEHAVIOR-LIFECYCLE-BACKLINK",
            f"prerequisite Lifecycle Register is {lifecycle_result.status}",
        )

    if domain_schema_valid("http"):
        http_result = validate_http_register(register)
        report.add_errors("REG-HTTP-ROW", http_result.errors)
    else:
        http_result = DomainResult("invalid")
    report.domain_statuses["http"] = http_result.status

    published_call_ids: set[str] = set()
    if prerequisites_available("http_document"):
        http_document_errors: list[str] = []
        published_call_ids = validate_field_mapping_document(
            root / "tech-pack" / "field-validation-and-mapping.md",
            http_result.data["call_ids"],
            http_result.data["usages_by_call"],
            http_result.data["usage_to_call"],
            http_result.data["mapping_directions"],
            http_result.data["call_statuses"],
            http_result.data["usage_statuses"],
            http_result.data["mapping_statuses"],
            http_document_errors,
        )
        report.add_errors("HTTP-DOCUMENT", http_document_errors)
        behavior_http_errors: list[str] = []
        validate_behavior_call_links(
            root, published_call_ids, http_result.data["call_statuses"], behavior_http_errors
        )
        report.add_errors("BEHAVIOR-HTTP-BACKLINK", behavior_http_errors)
    else:
        report.skip(
            "HTTP-DOCUMENT",
            f"prerequisite HTTP Register is {http_result.status}",
        )
        report.skip(
            "BEHAVIOR-HTTP-BACKLINK",
            f"prerequisite HTTP Register is {http_result.status}",
        )

    trusted_call_ids = (
        http_result.data.get("call_ids") if http_result.status == "valid" else None
    )
    if domain_schema_valid("dependency"):
        dependency_result = validate_dependency_register(register, trusted_call_ids)
        report.add_errors("REG-DEP-ROW", dependency_result.errors)
    else:
        dependency_result = DomainResult("invalid")
    report.domain_statuses["dependency"] = dependency_result.status
    if not prerequisites_available("dependency_http_cross_reference"):
        report.skip(
            "DEP-HTTP-XREF",
            "prerequisite Dependency or HTTP Register index is unavailable",
        )

    if domain_schema_valid("failure"):
        trusted_dependencies = (
            dependency_result.data.get("dependency_ids")
            if dependency_result.status == "valid"
            else None
        )
        failure_result = validate_failure_register(register, trusted_dependencies)
        report.add_errors("REG-FAIL-ROW", failure_result.errors)
    else:
        failure_result = DomainResult("invalid")
    report.domain_statuses["failure"] = failure_result.status
    if not prerequisites_available("failure_dependency_cross_reference"):
        report.skip(
            "FAIL-DEP-XREF",
            "prerequisite Failure or Dependency Register index is unavailable",
        )

    if domain_schema_valid("config"):
        config_result = validate_config_register(register)
        report.add_errors("REG-CONFIG-ROW", config_result.errors)
    else:
        config_result = DomainResult("invalid")
    report.domain_statuses["config"] = config_result.status

    if domain_schema_valid("java"):
        java_result = validate_java_register(register)
        report.add_errors("REG-JAVA-ROW", java_result.errors)
    else:
        java_result = DomainResult("invalid")
    report.domain_statuses["java"] = java_result.status

    config_identity_errors, java_identity_errors = validate_config_java_reader_identities(
        root, config_result, java_result
    )
    report.add_errors("REG-CONFIG-XREF", config_identity_errors)
    report.add_errors("REG-JAVA-XREF", java_identity_errors)

    dependency_ids: set[str] | None = None
    pattern_ids: set[str] | None = None
    if prerequisites_available("dependency_document"):
        dependency_ids = dependency_result.data["dependency_ids"]
        dependency_document_errors: list[str] = []
        validate_external_dependency_document(
            root / "tech-pack" / "external-dependency-contracts.md",
            dependency_ids,
            dependency_result.data["operations_by_dependency"],
            dependency_result.data["http_refs_by_operation"],
            dependency_result.data["dependency_statuses"],
            dependency_result.data["operation_statuses"],
            repo,
            dependency_document_errors,
        )
        report.add_errors("DEP-DOCUMENT", dependency_document_errors)
    else:
        report.skip(
            "DEP-DOCUMENT",
            f"prerequisite Dependency Register is {dependency_result.status}",
        )
        report.skip(
            "BEHAVIOR-DEP-BACKLINK",
            f"prerequisite Dependency Register is {dependency_result.status}",
        )

    if prerequisites_available("failure_document"):
        pattern_ids = failure_result.data["pattern_ids"]
        failure_document_errors: list[str] = []
        validate_failure_taxonomy_document(
            root / "tech-pack" / "failure-taxonomy.md",
            pattern_ids,
            repo,
            failure_document_errors,
        )
        report.add_errors("FAIL-DOCUMENT", failure_document_errors)
    else:
        report.skip(
            "FAIL-DOCUMENT",
            f"prerequisite Failure Register is {failure_result.status}",
        )
        report.skip(
            "BEHAVIOR-FAIL-BACKLINK",
            f"prerequisite Failure Register is {failure_result.status}",
        )

    config_impact_ids: set[str] | None = None
    if prerequisites_available("config_document"):
        config_impact_ids = config_result.data["impact_ids"]
        config_document_errors: list[str] = []
        validate_runtime_config_document(
            root / "tech-pack" / "runtime-config-matrix.md",
            config_result,
            repo,
            config_document_errors,
        )
        report.add_errors("CONFIG-DOCUMENT", config_document_errors)
    else:
        report.skip(
            "CONFIG-DOCUMENT",
            f"prerequisite Config Register is {config_result.status}",
        )
        report.skip(
            "BEHAVIOR-CONFIG-BACKLINK",
            f"prerequisite Config Register is {config_result.status}",
        )

    java_binding_ids: set[str] | None = None
    if prerequisites_available("java_document"):
        java_binding_ids = java_result.data["binding_ids"]
        java_document_errors: list[str] = []
        validate_java_implementation_document(
            root / "tech-pack" / "java-implementation-map.md",
            java_result,
            repo,
            java_document_errors,
        )
        report.add_errors("JAVA-DOCUMENT", java_document_errors)
    else:
        report.skip(
            "JAVA-DOCUMENT",
            f"prerequisite Java Register is {java_result.status}",
        )
        report.skip(
            "BEHAVIOR-JAVA-BACKLINK",
            f"prerequisite Java Register is {java_result.status}",
        )

    behavior_repository_errors: list[str] = []
    validate_behavior_repository_links(
        root,
        dependency_ids,
        dependency_result.data.get("dependency_statuses")
        if dependency_result.status == "valid"
        else None,
        pattern_ids,
        java_binding_ids,
        config_impact_ids,
        behavior_repository_errors,
    )
    report.add_errors("BEHAVIOR-REPOSITORY-BACKLINK", behavior_repository_errors)

    if args.validation_profile == "complete":
        ba_errors: list[str] = []
        validate_ba_traceability(root, ba_errors)
        report.add_errors("BA-LINK", ba_errors)

    if report.error_groups.get("MARKDOWN-FRAGMENT"):
        report.domain_statuses["markdown-fragment"] = "invalid"
    elif any(code.startswith("MARKDOWN-FRAGMENT:") for code in report.skipped_groups):
        report.domain_statuses["markdown-fragment"] = "skipped"
    else:
        report.domain_statuses["markdown-fragment"] = "valid"
    report.checked_documents = len(markdown_files)
    if args.json:
        print(json.dumps(report.payload(len(markdown_files)), indent=2, sort_keys=True))
    else:
        report.render_text(len(markdown_files))
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
