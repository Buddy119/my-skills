#!/usr/bin/env python3
"""Deterministic Reader Projection relationships and transaction plans.

The module updates only stable identities, paths, links, and counts.  It never
creates repository explanations or decides whether two business concepts are
semantically equivalent.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


READER_PROJECTION_VALIDATION_VERSION = "2"
PLAN_FILENAME = "reader-projection-plan.json"
TERMINAL_REVIEW_STATUSES = {"refreshed", "reviewed-no-change"}
ALLOWED_REVIEW_STATUSES = TERMINAL_REVIEW_STATUSES
PROJECTION_STAGES = {
    "tech-publication",
    "api-contract-publication",
    "business-model",
    "ba-publication",
    "finalization",
}
REFRESH_STAGES = {"api-contract-publication", "ba-publication", "finalization"}


class ReaderProjectionError(RuntimeError):
    """A projection relationship or transaction contract is invalid."""


@dataclass
class RelationshipGraph:
    behaviors: dict[str, dict[str, Any]] = field(default_factory=dict)
    contracts: dict[str, dict[str, Any]] = field(default_factory=dict)
    scenarios: dict[str, dict[str, Any]] = field(default_factory=dict)
    journeys: dict[str, dict[str, Any]] = field(default_factory=dict)
    matrix_rows: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def api_intent(self) -> bool:
        return bool(
            self.contracts
            or self.matrix_rows
            or any(item.get("entry_type") == "api" for item in self.behaviors.values())
            or any(item.get("api_contracts") for item in self.behaviors.values())
        )

    def ba_intent(self) -> bool:
        return bool(self.scenarios or self.journeys)

    def api_payload(self) -> dict[str, Any]:
        return {
            "behaviors": {
                identifier: {
                    "entry_type": item.get("entry_type"),
                    "api_contracts": item.get("api_contracts", []),
                }
                for identifier, item in sorted(self.behaviors.items())
            },
            "contracts": self.contracts,
            "matrix_rows": self.matrix_rows,
        }

    def ba_payload(self) -> dict[str, Any]:
        return {
            "behaviors": {
                identifier: {"ba_scenarios": item.get("ba_scenarios", [])}
                for identifier, item in sorted(self.behaviors.items())
            },
            "scenarios": self.scenarios,
            "journeys": self.journeys,
        }

    def domain_hash(self, domain: str) -> str:
        payload = self.api_payload() if domain == "api" else self.ba_payload()
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def load_projection_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or Path(__file__).resolve().parents[1] / "assets" / "reader-projection-schema.json"
    try:
        payload = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReaderProjectionError(f"Reader Projection Schema cannot be loaded: {exc}") from exc
    if payload.get("reader_projection_schema_version") != "2":
        raise ReaderProjectionError("unsupported Reader Projection Schema version")
    if payload.get("validation_version") != READER_PROJECTION_VALIDATION_VERSION:
        raise ReaderProjectionError("Reader Projection validation version is inconsistent")
    stages = payload.get("stages")
    if not isinstance(stages, dict) or set(stages) != PROJECTION_STAGES:
        raise ReaderProjectionError("Reader Projection Schema stage coverage is incomplete")
    for stage, domains in stages.items():
        if not isinstance(domains, dict) or set(domains) != {"api", "ba"}:
            raise ReaderProjectionError(f"Reader Projection stage {stage} must define API and BA")
        if any(value not in {"deferred", "required", "receipt-or-current"} for value in domains.values()):
            raise ReaderProjectionError(f"Reader Projection stage {stage} has an invalid requirement")
    return payload


def _frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end], text[end + 5 :]


def _scalar(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def _yaml_block(frontmatter: str, key: str) -> str:
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        if re.fullmatch(rf"{re.escape(key)}:\s*(?:\[\])?\s*", line):
            end = index + 1
            while end < len(lines) and (not lines[end] or lines[end][0].isspace()):
                end += 1
            return "\n".join(lines[index + 1 : end])
    return ""


def _linked_entries(frontmatter: str, block_key: str, id_key: str) -> list[dict[str, str]]:
    block = _yaml_block(frontmatter, block_key)
    identifiers = re.findall(
        rf"^\s*-\s+{re.escape(id_key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
        block,
        re.M,
    )
    documents = re.findall(
        r"^\s+document:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
        block,
        re.M,
    )
    if len(identifiers) != len(documents):
        return []
    return [
        {id_key: identifier.strip(), "document": document.strip()}
        for identifier, document in zip(identifiers, documents)
    ]


def _replace_root_list(
    frontmatter: str,
    key: str,
    id_key: str,
    entries: list[dict[str, str]],
) -> str:
    lines = frontmatter.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if re.fullmatch(rf"{re.escape(key)}:\s*(?:\[\])?\s*", line)),
        None,
    )
    rendered = [f"{key}: []"] if not entries else [f"{key}:"]
    for entry in entries:
        rendered.extend(
            [
                f'  - {id_key}: "{entry[id_key]}"',
                f'    document: "{entry["document"]}"',
            ]
        )
    if start is None:
        raise ReaderProjectionError(f"frontmatter is missing required projection field: {key}")
    end = start + 1
    while end < len(lines) and (not lines[end] or lines[end][0].isspace()):
        end += 1
    return "\n".join(lines[:start] + rendered + lines[end:])


def _replace_related_links(
    body: str,
    heading: str,
    links: list[tuple[str, str]],
) -> str:
    replacement = "".join(f"- [{label}]({target})\n" for label, target in links)
    pattern = re.compile(
        rf"(?ms)^#{{2,3}}\s+{re.escape(heading)}\s*$\n.*?(?=^#{{2,3}}\s+|\Z)"
    )
    match = pattern.search(body)
    section = f"### {heading}\n\n{replacement}\n"
    if match:
        if not links:
            return body[: match.start()] + body[match.end() :]
        return body[: match.start()] + section + body[match.end() :]
    if not links:
        return body
    parent = re.search(r"(?m)^##\s+Related documents\s*$\n", body)
    if parent:
        return body[: parent.end()] + "\n" + section + body[parent.end() :]
    marker = re.search(r"(?m)^##\s+Behavior flow\s*$", body)
    if marker:
        return body[: marker.start()] + section + body[marker.start() :]
    raise ReaderProjectionError(
        f"cannot insert {heading}: Related documents and Behavior flow are missing"
    )


def _catalog_behavior_blocks(text: str) -> dict[str, tuple[int, int, str]]:
    matches = list(re.finditer(r"(?m)^  - behavior_id:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", text))
    blocks: dict[str, tuple[int, int, str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        summary = re.search(r"(?m)^summary:\s*$", text[match.end() : end])
        if summary:
            end = match.end() + summary.start()
        blocks[match.group(1).strip()] = (match.start(), end, text[match.start() : end])
    return blocks


def _replace_catalog_list(
    block: str,
    key: str,
    id_key: str,
    entries: list[dict[str, str]],
) -> str:
    lines = block.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if re.fullmatch(rf"    {re.escape(key)}:\s*(?:\[\])?\s*", line)),
        None,
    )
    if start is None:
        raise ReaderProjectionError(f"catalog behavior is missing required projection field: {key}")
    end = start + 1
    while end < len(lines) and (
        not lines[end]
        or len(lines[end]) - len(lines[end].lstrip(" ")) > 4
    ):
        end += 1
    rendered = [f"    {key}: []"] if not entries else [f"    {key}:"]
    for entry in entries:
        rendered.extend(
            [
                f'      - {id_key}: "{entry[id_key]}"',
                f'        document: "{entry["document"]}"',
            ]
        )
    suffix_newline = "\n" if block.endswith("\n") else ""
    return "\n".join(lines[:start] + rendered + lines[end:]) + suffix_newline


def _catalog_linked_entries(
    block: str, key: str, id_key: str
) -> list[dict[str, str]]:
    lines = block.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if re.fullmatch(rf"    {re.escape(key)}:\s*(?:\[\])?\s*", line)),
        None,
    )
    if start is None:
        return []
    end = start + 1
    while end < len(lines) and (
        not lines[end]
        or len(lines[end]) - len(lines[end].lstrip(" ")) > 4
    ):
        end += 1
    nested = "\n".join(lines[start + 1 : end])
    identifiers = re.findall(
        rf"^\s*-\s+{re.escape(id_key)}:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
        nested,
        re.M,
    )
    documents = re.findall(
        r"^\s+document:\s*[\"']?([^\"'\n]+?)[\"']?\s*$",
        nested,
        re.M,
    )
    return [
        {id_key: identifier.strip(), "document": document.strip()}
        for identifier, document in zip(identifiers, documents)
    ]


def _update_catalog(
    text: str,
    relationships: dict[str, dict[str, list[dict[str, str]]]],
    domain: str,
) -> str:
    key, id_key = ("api_contracts", "endpoint_id") if domain == "api" else ("ba_scenarios", "scenario_id")
    blocks = _catalog_behavior_blocks(text)
    missing = sorted(set(relationships) - set(blocks))
    if missing:
        raise ReaderProjectionError("Tech Catalog is missing Behaviors: " + ", ".join(missing))
    replacements: list[tuple[int, int, str]] = []
    for behavior_id, values in relationships.items():
        start, end, block = blocks[behavior_id]
        replacements.append((start, end, _replace_catalog_list(block, key, id_key, values[key])))
    for start, end, replacement in sorted(replacements, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _section(text: str, heading: str) -> tuple[int, int, str] | None:
    match = re.search(rf"(?m)^(?P<marks>##{{1,5}})\s+{re.escape(heading)}\s*$", text)
    if not match:
        return None
    level = len(match.group("marks"))
    following = re.search(rf"(?m)^#{{1,{level}}}\s+", text[match.end() :])
    end = match.end() + following.start() if following else len(text)
    return match.start(), end, text[match.start() : end]


def _replace_table_lines(section: str, updater: Any) -> str:
    lines = section.splitlines()
    table_indexes = [index for index, line in enumerate(lines) if line.strip().startswith("|")]
    if len(table_indexes) < 2:
        raise ReaderProjectionError("Reader projection table is missing or malformed")
    header_index = table_indexes[0]
    headers = _table_cells(lines[header_index])
    for index in table_indexes[2:]:
        cells = _table_cells(lines[index])
        if len(cells) != len(headers):
            raise ReaderProjectionError("Reader projection table has inconsistent columns")
        updated = updater(headers, cells)
        if updated is not None:
            lines[index] = "| " + " | ".join(updated) + " |"
    return "\n".join(lines) + ("\n" if section.endswith("\n") else "")


def _link_list(entries: Iterable[dict[str, str]], id_key: str, labels: dict[str, str]) -> str:
    rendered = []
    for entry in entries:
        identifier = entry[id_key]
        label = labels.get(identifier, identifier)
        rendered.append(f"[{label}]({entry['document']})")
    return ", ".join(rendered) if rendered else "N/A"


def _update_overview(
    text: str,
    graph: RelationshipGraph,
    domain: str,
) -> tuple[str, list[str]]:
    missing_semantic: list[str] = []
    if _section(text, "Capability paths") is None:
        missing_semantic.append("Capability paths is missing")
    if _section(text, "Behavior variants") is None:
        missing_semantic.append("Behavior variants is missing")
    if _section(text, "Risk hotspots") is None:
        missing_semantic.append("Risk hotspots is missing")

    if domain == "api" and graph.contracts:
        exposure = _section(text, "Endpoint exposure summary")
        if exposure is None:
            missing_semantic.append("Endpoint exposure summary is missing")
        else:
            start, end, content = exposure
            counts = {
                "Application endpoints": sum(
                    row.get("operation_role") == "application-endpoint"
                    for row in graph.matrix_rows.values()
                ),
                "Meaningful external exposures": sum(
                    row.get("operation_role") == "meaningful-external-exposure"
                    for row in graph.matrix_rows.values()
                ),
                "Unresolved or conflicting exceptions": sum(
                    row.get("operation_role") == "unresolved"
                    or "Conflicting" in str(row.get("raw", ""))
                    for row in graph.matrix_rows.values()
                ),
            }

            def update_count(headers: list[str], cells: list[str]) -> list[str] | None:
                if "Category" not in headers or "Count" not in headers:
                    raise ReaderProjectionError("Endpoint exposure summary has no Category/Count columns")
                category = cells[headers.index("Category")]
                if category in counts:
                    cells[headers.index("Count")] = str(counts[category])
                return cells

            updated = _replace_table_lines(content, update_count)
            text = text[:start] + updated + text[end:]
        knowledge = _section(text, "Knowledge pack index")
        if knowledge is not None:
            start, end, content = knowledge

            def update_availability(headers: list[str], cells: list[str]) -> list[str] | None:
                if "Knowledge area" not in headers or "Availability" not in headers:
                    raise ReaderProjectionError("Knowledge pack index has invalid columns")
                if cells[headers.index("Knowledge area")] == "Endpoints":
                    cells[headers.index("Availability")] = "Available"
                return cells

            updated = _replace_table_lines(content, update_availability)
            text = text[:start] + updated + text[end:]
    return text, missing_semantic


def _parse_matrix(root: Path, graph: RelationshipGraph) -> None:
    path = root / "tech-pack" / "endpoint-matrix.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    section = _section(text, "Endpoint summary")
    if section is None:
        graph.errors.append("Endpoint Matrix is missing Endpoint summary")
        return
    rows = [line for line in section[2].splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        graph.errors.append("Endpoint Matrix summary table is malformed")
        return
    headers = _table_cells(rows[0])
    if "Endpoint or Exposure ID" not in headers or "Operation Role" not in headers:
        graph.errors.append("Endpoint Matrix summary identity columns are missing")
        return
    for line in rows[2:]:
        cells = _table_cells(line)
        if len(cells) != len(headers):
            continue
        identifier = cells[headers.index("Endpoint or Exposure ID")].strip("` ")
        if not identifier:
            continue
        graph.matrix_rows[identifier] = {
            "operation_role": cells[headers.index("Operation Role")].strip("` "),
            "raw": line,
        }


def _load_behavior_graph(root: Path, graph: RelationshipGraph) -> None:
    for path in sorted((root / "tech-pack" / "behaviors").glob("*.md")):
        parsed = _frontmatter(path.read_text(encoding="utf-8"))
        if parsed is None:
            graph.errors.append(f"Tech Behavior frontmatter is invalid: {path.relative_to(root)}")
            continue
        frontmatter, _body = parsed
        identifier = _scalar(frontmatter, "behavior_id")
        if not identifier:
            graph.errors.append(f"Tech Behavior has no behavior_id: {path.relative_to(root)}")
            continue
        if identifier in graph.behaviors:
            graph.errors.append(f"duplicate Tech Behavior ID: {identifier}")
            continue
        graph.behaviors[identifier] = {
            "path": path.relative_to(root).as_posix(),
            "entry_type": _scalar(frontmatter, "entry_type"),
            "api_contracts": _linked_entries(frontmatter, "api_contracts", "endpoint_id"),
            "ba_scenarios": _linked_entries(frontmatter, "ba_scenarios", "scenario_id"),
            "failure_patterns": re.findall(r"FAIL-\d+", _yaml_block(frontmatter, "failure_patterns")),
        }


def _load_contract_graph(root: Path, graph: RelationshipGraph) -> None:
    for path in sorted((root / "tech-pack" / "contracts").glob("*.api-contract.md")):
        parsed = _frontmatter(path.read_text(encoding="utf-8"))
        if parsed is None:
            graph.errors.append(f"API Contract frontmatter is invalid: {path.relative_to(root)}")
            continue
        frontmatter, _body = parsed
        endpoint_id = _scalar(frontmatter, "endpoint_id")
        behavior_id = _scalar(frontmatter, "behavior_id")
        if not endpoint_id or not behavior_id:
            graph.errors.append(f"API Contract identity is incomplete: {path.relative_to(root)}")
            continue
        if endpoint_id in graph.contracts:
            graph.errors.append(f"duplicate API Contract Endpoint ID: {endpoint_id}")
            continue
        graph.contracts[endpoint_id] = {
            "behavior_id": behavior_id,
            "path": path.relative_to(root).as_posix(),
            "method": _scalar(frontmatter, "method"),
            "route": _scalar(frontmatter, "route"),
            "title": _scalar(frontmatter, "title"),
            "contract_status": _scalar(frontmatter, "contract_status"),
        }


def _load_ba_graph(root: Path, graph: RelationshipGraph) -> None:
    for kind, folder, id_key, destination in (
        ("Scenario", "scenarios", "scenario_id", graph.scenarios),
        ("Journey", "journeys", "journey_id", graph.journeys),
    ):
        for path in sorted((root / "ba-pack" / folder).glob("*.md")):
            parsed = _frontmatter(path.read_text(encoding="utf-8"))
            if parsed is None:
                graph.errors.append(f"BA {kind} frontmatter is invalid: {path.relative_to(root)}")
                continue
            frontmatter, _body = parsed
            identifier = _scalar(frontmatter, id_key)
            if not identifier:
                graph.errors.append(f"BA {kind} has no {id_key}: {path.relative_to(root)}")
                continue
            if identifier in destination:
                graph.errors.append(f"duplicate BA {kind} ID: {identifier}")
                continue
            item: dict[str, Any] = {
                "path": path.relative_to(root).as_posix(),
                "title": _scalar(frontmatter, "title"),
            }
            if kind == "Scenario":
                item["journeys"] = _linked_entries(frontmatter, "journeys", "journey_id")
                item["tech_behaviors"] = _linked_entries(frontmatter, "tech_behaviors", "behavior_id")
            else:
                item["scenarios"] = _linked_entries(frontmatter, "scenarios", "scenario_id")
                item["supporting_tech_behaviors"] = _linked_entries(
                    frontmatter, "supporting_tech_behaviors", "behavior_id"
                )
            destination[identifier] = item


def build_relationship_graph(root: Path) -> RelationshipGraph:
    graph = RelationshipGraph()
    _load_behavior_graph(root, graph)
    _load_contract_graph(root, graph)
    _parse_matrix(root, graph)
    _load_ba_graph(root, graph)

    declared: dict[str, str] = {}
    for behavior_id, behavior in graph.behaviors.items():
        for entry in behavior.get("api_contracts", []):
            endpoint_id = entry["endpoint_id"]
            previous = declared.get(endpoint_id)
            if previous and previous != behavior_id:
                graph.errors.append(
                    f"Endpoint {endpoint_id} is declared by multiple Tech Behaviors"
                )
            declared[endpoint_id] = behavior_id
    for endpoint_id, contract in graph.contracts.items():
        behavior_id = contract["behavior_id"]
        if behavior_id not in graph.behaviors:
            graph.errors.append(
                f"API Contract {endpoint_id} references unknown Tech Behavior {behavior_id}"
            )
        elif declared.get(endpoint_id) != behavior_id:
            graph.errors.append(
                f"API Contract {endpoint_id} conflicts with the Tech Behavior declaration"
            )
        row = graph.matrix_rows.get(endpoint_id)
        if row is None:
            graph.errors.append(f"API Contract {endpoint_id} is absent from Endpoint Matrix")
        elif row.get("operation_role") != "application-endpoint":
            graph.errors.append(
                f"API Contract {endpoint_id} is not an application-endpoint in Endpoint Matrix"
            )
    if graph.contracts:
        for endpoint_id in sorted(set(declared) - set(graph.contracts)):
            graph.errors.append(f"declared API Contract is not materialized: {endpoint_id}")

    scenario_to_tech: dict[str, set[str]] = {}
    for scenario_id, scenario in graph.scenarios.items():
        tech_ids = {entry["behavior_id"] for entry in scenario.get("tech_behaviors", [])}
        scenario_to_tech[scenario_id] = tech_ids
        for behavior_id in tech_ids:
            if behavior_id not in graph.behaviors:
                graph.errors.append(
                    f"BA Scenario {scenario_id} references unknown Tech Behavior {behavior_id}"
                )
        for entry in scenario.get("journeys", []):
            journey_id = entry["journey_id"]
            journey = graph.journeys.get(journey_id)
            if journey is None:
                graph.errors.append(
                    f"BA Scenario {scenario_id} references unknown Journey {journey_id}"
                )
            elif scenario_id not in {
                item["scenario_id"] for item in journey.get("scenarios", [])
            }:
                graph.errors.append(
                    f"BA Journey {journey_id} lacks Scenario backlink {scenario_id}"
                )
    for journey_id, journey in graph.journeys.items():
        scenario_ids = {entry["scenario_id"] for entry in journey.get("scenarios", [])}
        derived = set().union(*(scenario_to_tech.get(identifier, set()) for identifier in scenario_ids)) if scenario_ids else set()
        declared_tech = {
            entry["behavior_id"] for entry in journey.get("supporting_tech_behaviors", [])
        }
        if declared_tech != derived:
            graph.errors.append(
                f"BA Journey {journey_id} supporting Tech Behaviors do not match its Scenarios"
            )
    return graph


def _relationships(graph: RelationshipGraph, domain: str) -> dict[str, dict[str, list[dict[str, str]]]]:
    relationships = {
        behavior_id: {"api_contracts": [], "ba_scenarios": []}
        for behavior_id in graph.behaviors
    }
    if domain == "api":
        for endpoint_id, contract in sorted(graph.contracts.items()):
            behavior_id = contract["behavior_id"]
            if behavior_id in relationships:
                relationships[behavior_id]["api_contracts"].append(
                    {
                        "endpoint_id": endpoint_id,
                        "document": f"../contracts/{endpoint_id}.api-contract.md",
                    }
                )
    else:
        for scenario_id, scenario in sorted(graph.scenarios.items()):
            for entry in scenario.get("tech_behaviors", []):
                behavior_id = entry["behavior_id"]
                if behavior_id in relationships:
                    relationships[behavior_id]["ba_scenarios"].append(
                        {
                            "scenario_id": scenario_id,
                            "document": f"../../ba-pack/scenarios/{scenario_id}.md",
                        }
                    )
    return relationships


def _mechanical_updates(
    root: Path,
    graph: RelationshipGraph,
    domain: str,
) -> tuple[dict[Path, str], list[dict[str, Any]], list[str]]:
    relationships = _relationships(graph, domain)
    updates: dict[Path, str] = {}
    items: list[dict[str, Any]] = []
    semantic_notes: list[str] = []
    key, id_key = ("api_contracts", "endpoint_id") if domain == "api" else ("ba_scenarios", "scenario_id")

    for behavior_id, relationship in relationships.items():
        behavior = graph.behaviors[behavior_id]
        path = root / behavior["path"]
        original = path.read_text(encoding="utf-8")
        parsed = _frontmatter(original)
        if parsed is None:
            raise ReaderProjectionError(f"Tech Behavior frontmatter is invalid: {behavior['path']}")
        frontmatter, body = parsed
        frontmatter = _replace_root_list(frontmatter, key, id_key, relationship[key])
        if domain == "api":
            labels = {
                endpoint_id: f"{contract.get('method') or ''} {contract.get('route') or endpoint_id}".strip()
                for endpoint_id, contract in graph.contracts.items()
            }
            links = [
                (labels.get(entry[id_key], entry[id_key]), entry["document"])
                for entry in relationship[key]
            ]
            body = _replace_related_links(body, "API contracts", links)
        else:
            labels = {
                scenario_id: str(scenario.get("title") or scenario_id)
                for scenario_id, scenario in graph.scenarios.items()
            }
            links = [
                (labels.get(entry[id_key], entry[id_key]), entry["document"])
                for entry in relationship[key]
            ]
            body = _replace_related_links(body, "BA scenarios", links)
        rendered = "---\n" + frontmatter + "\n---\n" + body
        updates[path] = rendered
        items.append(
            {
                "projection_id": f"{domain}:behavior:{behavior_id}",
                "surface": f"tech-behavior.{key}",
                "path": behavior["path"],
                "status": "refreshed" if rendered != original else "already-current",
                "before_sha256": _sha256(path),
                "after_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            }
        )

    catalog = root / "tech-pack" / "behavior-catalog.yaml"
    if catalog.is_file():
        original = catalog.read_text(encoding="utf-8")
        catalog_relationships: dict[str, dict[str, list[dict[str, str]]]] = {}
        for behavior_id, relationship in relationships.items():
            entries = []
            for entry in relationship[key]:
                item = dict(entry)
                if domain == "api":
                    item["document"] = f"contracts/{entry[id_key]}.api-contract.md"
                else:
                    item["document"] = f"../ba-pack/scenarios/{entry[id_key]}.md"
                entries.append(item)
            catalog_relationships[behavior_id] = {key: entries}
        rendered = _update_catalog(original, catalog_relationships, domain)
        updates[catalog] = rendered
        items.append(
            {
                "projection_id": f"{domain}:catalog",
                "surface": f"tech-behavior-catalog.{key}",
                "path": catalog.relative_to(root).as_posix(),
                "status": "refreshed" if rendered != original else "already-current",
                "before_sha256": _sha256(catalog),
                "after_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            }
        )

    overview = root / "tech-pack" / "repository-overview.md"
    if overview.is_file():
        original = overview.read_text(encoding="utf-8")
        rendered, missing = _update_overview(original, graph, domain)
        semantic_notes.extend(missing)
        updates[overview] = rendered
        items.append(
            {
                "projection_id": f"{domain}:repository-overview-navigation",
                "surface": f"repository-overview.{domain}-navigation",
                "path": overview.relative_to(root).as_posix(),
                "status": "refreshed" if rendered != original else "already-current",
                "before_sha256": _sha256(overview),
                "after_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            }
        )
    return updates, items, semantic_notes


def _semantic_paths(root: Path, graph: RelationshipGraph, domain: str) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    overview = root / "tech-pack" / "repository-overview.md"
    if overview.is_file():
        paths.append((overview.relative_to(root).as_posix(), f"{domain}-repository-summary"))
    if domain == "api":
        for behavior in graph.behaviors.values():
            if behavior.get("api_contracts"):
                paths.append((behavior["path"], "api-behavior-summary"))
        field = root / "tech-pack" / "field-validation-and-mapping.md"
        if field.is_file():
            paths.append((field.relative_to(root).as_posix(), "api-contract-index"))
        failure = root / "tech-pack" / "failure-taxonomy.md"
        if failure.is_file() and any(
            behavior.get("failure_patterns") and behavior.get("api_contracts")
            for behavior in graph.behaviors.values()
        ):
            paths.append((failure.relative_to(root).as_posix(), "caller-visible-failure-summary"))
    else:
        for behavior in graph.behaviors.values():
            if behavior.get("ba_scenarios"):
                paths.append((behavior["path"], "ba-scenario-context"))
        for relative, purpose in (
            ("ba-pack/business-overview.md", "journey-landscape"),
            ("ba-pack/business-catalog.md", "journey-scenario-coverage"),
        ):
            if (root / relative).is_file():
                paths.append((relative, purpose))
    return sorted(set(paths))


def _section_contains_all(text: str, heading: str, targets: Iterable[str]) -> list[str]:
    found = _section(text, heading)
    if found is None:
        return [f"missing section {heading}"]
    return [target for target in targets if target not in found[2]]


def validate_mechanical_projection(
    root: Path,
    graph: RelationshipGraph,
    domain: str,
) -> list[str]:
    errors: list[str] = []
    relationships = _relationships(graph, domain)
    key, id_key = ("api_contracts", "endpoint_id") if domain == "api" else ("ba_scenarios", "scenario_id")
    for behavior_id, expected in relationships.items():
        observed = graph.behaviors[behavior_id].get(key, [])
        expected_pairs = {(item[id_key], item["document"]) for item in expected[key]}
        observed_pairs = {(item[id_key], item["document"]) for item in observed}
        if expected_pairs != observed_pairs:
            errors.append(f"Tech Behavior {behavior_id} has stale {key}")

    catalog = root / "tech-pack" / "behavior-catalog.yaml"
    if catalog.is_file():
        text = catalog.read_text(encoding="utf-8")
        blocks = _catalog_behavior_blocks(text)
        for behavior_id, expected in relationships.items():
            block = blocks.get(behavior_id)
            if block is None:
                errors.append(f"Tech Catalog is missing Behavior {behavior_id}")
                continue
            entries = _catalog_linked_entries(block[2], key, id_key)
            expected_ids = {item[id_key] for item in expected[key]}
            observed_ids = {item[id_key] for item in entries}
            if expected_ids != observed_ids:
                errors.append(f"Tech Catalog has stale {key} for {behavior_id}")

    if domain == "api" and graph.contracts:
        field = root / "tech-pack" / "field-validation-and-mapping.md"
        if field.is_file():
            text = field.read_text(encoding="utf-8")
            missing = _section_contains_all(
                text,
                "API contract index",
                [
                    f"contracts/{endpoint_id}.api-contract.md"
                    for endpoint_id in sorted(graph.contracts)
                ],
            )
            errors.extend(f"Field Pack API Contract index omits {item}" for item in missing)
    if domain == "ba" and graph.ba_intent():
        catalog_path = root / "ba-pack" / "business-catalog.md"
        overview_path = root / "ba-pack" / "business-overview.md"
        if catalog_path.is_file():
            text = catalog_path.read_text(encoding="utf-8")
            for heading, targets in (
                ("Journey index", [f"journeys/{identifier}.md" for identifier in sorted(graph.journeys)]),
                ("Scenario index", [f"scenarios/{identifier}.md" for identifier in sorted(graph.scenarios)]),
                ("Tech coverage map", [f"../tech-pack/behaviors/{identifier}.md" for identifier in sorted(graph.behaviors)]),
            ):
                missing = _section_contains_all(text, heading, targets)
                errors.extend(f"BA Catalog {heading} omits {item}" for item in missing)
        else:
            errors.append("BA Catalog is missing")
        if overview_path.is_file():
            text = overview_path.read_text(encoding="utf-8")
            missing = _section_contains_all(
                text,
                "Journey landscape",
                [f"journeys/{identifier}.md" for identifier in sorted(graph.journeys)],
            )
            errors.extend(f"BA Overview Journey landscape omits {item}" for item in missing)
        else:
            errors.append("BA Overview is missing")
    return errors


def _load_plan(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReaderProjectionError(f"Reader Projection Plan cannot be loaded: {exc}") from exc
    if payload.get("reader_projection_plan_schema_version") != "1":
        raise ReaderProjectionError("unsupported Reader Projection Plan version")
    return payload


def plan_path(transaction_dir: Path) -> Path:
    return transaction_dir / PLAN_FILENAME


def refresh_projections(
    *,
    root: Path,
    transaction_dir: Path,
    transaction_id: str,
    stage: str,
    repository: str,
    source_commit: str,
) -> dict[str, Any]:
    load_projection_schema()
    if stage not in REFRESH_STAGES:
        raise ReaderProjectionError(f"Reader Projections cannot be refreshed during {stage}")
    graph = build_relationship_graph(root)
    domains = ["api"] if stage == "api-contract-publication" else ["ba"] if stage == "ba-publication" else ["api", "ba"]
    relevant_errors = list(graph.errors)
    if relevant_errors:
        payload = {
            "reader_projection_plan_schema_version": "1",
            "validation_version": READER_PROJECTION_VALIDATION_VERSION,
            "transaction_id": transaction_id,
            "stage": stage,
            "repository": repository,
            "source_commit": source_commit,
            "status": "invalid",
            "relationship_errors": relevant_errors,
            "domain_graph_sha256": {domain: graph.domain_hash(domain) for domain in domains},
            "mechanical_items": [],
            "semantic_items": [],
        }
        _atomic_json(plan_path(transaction_dir), payload)
        return payload

    previous = _load_plan(plan_path(transaction_dir)) or {}
    pending_updates: dict[Path, str] = {}
    mechanical_items: list[dict[str, Any]] = []
    semantic_notes: list[str] = []
    for domain in domains:
        applicable = graph.api_intent() if domain == "api" else graph.ba_intent()
        if not applicable:
            continue
        updates, items, notes = _mechanical_updates(root, graph, domain)
        pending_updates.update(updates)
        mechanical_items.extend(items)
        semantic_notes.extend(f"{domain}: {note}" for note in notes)

    for path, text in pending_updates.items():
        if path.read_text(encoding="utf-8") != text:
            _atomic_write(path, text)

    graph = build_relationship_graph(root)
    relationship_errors = list(graph.errors)
    for domain in domains:
        applicable = graph.api_intent() if domain == "api" else graph.ba_intent()
        if applicable:
            relationship_errors.extend(validate_mechanical_projection(root, graph, domain))

    old_items = {
        str(item.get("projection_id")): item
        for item in previous.get("semantic_items", [])
        if isinstance(item, dict)
    }
    semantic_items: list[dict[str, Any]] = []
    for domain in domains:
        applicable = graph.api_intent() if domain == "api" else graph.ba_intent()
        if not applicable:
            continue
        domain_hash = graph.domain_hash(domain)
        for relative, purpose in _semantic_paths(root, graph, domain):
            projection_id = f"{domain}:semantic:{relative}:{purpose}"
            target = root / relative
            current_hash = _sha256(target)
            item = {
                "projection_id": projection_id,
                "domain": domain,
                "path": relative,
                "purpose": purpose,
                "status": "pending",
                "reason": None,
                "source_graph_sha256": domain_hash,
                "baseline_sha256": current_hash,
                "reviewed_sha256": None,
            }
            old = old_items.get(projection_id)
            if (
                old
                and old.get("status") in TERMINAL_REVIEW_STATUSES
                and old.get("source_graph_sha256") == domain_hash
                and old.get("reviewed_sha256") == current_hash
            ):
                item.update(
                    status=old["status"],
                    reason=old.get("reason"),
                    baseline_sha256=old.get("baseline_sha256"),
                    reviewed_sha256=current_hash,
                )
            semantic_items.append(item)

    payload = {
        "reader_projection_plan_schema_version": "1",
        "validation_version": READER_PROJECTION_VALIDATION_VERSION,
        "transaction_id": transaction_id,
        "stage": stage,
        "repository": repository,
        "source_commit": source_commit,
        "status": "invalid" if relationship_errors else "in-progress",
        "domain_graph_sha256": {domain: graph.domain_hash(domain) for domain in domains},
        "relationship_errors": sorted(set(relationship_errors)),
        "semantic_notes": sorted(set(semantic_notes)),
        "mechanical_items": mechanical_items,
        "semantic_items": semantic_items,
    }
    _atomic_json(plan_path(transaction_dir), payload)
    return payload


def mark_projection(
    *,
    root: Path,
    transaction_dir: Path,
    transaction_id: str,
    projection_id: str,
    status: str,
    reason: str | None,
) -> dict[str, Any]:
    if status not in ALLOWED_REVIEW_STATUSES:
        raise ReaderProjectionError(f"invalid Reader Projection review status: {status}")
    if status == "reviewed-no-change" and not (reason and reason.strip()):
        raise ReaderProjectionError("reviewed-no-change requires a non-empty reason")
    path = plan_path(transaction_dir)
    plan = _load_plan(path)
    if plan is None:
        raise ReaderProjectionError("Reader Projection Plan does not exist; run refresh-projections")
    if plan.get("transaction_id") != transaction_id:
        raise ReaderProjectionError("Reader Projection Plan transaction mismatch")
    item = next(
        (
            candidate
            for candidate in plan.get("semantic_items", [])
            if candidate.get("projection_id") == projection_id
        ),
        None,
    )
    if item is None:
        raise ReaderProjectionError(f"unknown semantic Reader Projection: {projection_id}")
    target = root / str(item.get("path"))
    current_hash = _sha256(target)
    if current_hash is None:
        raise ReaderProjectionError(f"Reader Projection target is missing: {item.get('path')}")
    baseline_hash = item.get("baseline_sha256")
    if status == "refreshed" and current_hash == baseline_hash:
        raise ReaderProjectionError(
            "refreshed requires a target content change; use reviewed-no-change with a reason"
        )
    if status == "reviewed-no-change" and current_hash != baseline_hash:
        raise ReaderProjectionError(
            "target changed after projection planning; use refreshed or rerun refresh-projections"
        )
    item["status"] = status
    item["reason"] = reason.strip() if reason else None
    item["reviewed_sha256"] = current_hash
    if all(candidate.get("status") in TERMINAL_REVIEW_STATUSES for candidate in plan.get("semantic_items", [])):
        plan["status"] = "reviewed"
    _atomic_json(path, plan)
    return item


def _latest_projection_receipt(root: Path, domain: str) -> dict[str, Any] | None:
    receipt_root = root / ".work" / "execution" / "receipts"
    if not receipt_root.is_dir():
        return None
    for path in sorted(receipt_root.glob("*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            payload.get("reader_projection_validation_version") == READER_PROJECTION_VALIDATION_VERSION
            and payload.get(f"reader_projection_{domain}_status") in {"current", "not-applicable"}
        ):
            return payload
    return None


def evaluate_projection(
    *,
    root: Path,
    transaction_dir: Path | None,
    transaction_id: str | None,
    stage: str,
    repository: str,
    source_commit: str,
) -> dict[str, Any]:
    schema = load_projection_schema()
    if stage not in PROJECTION_STAGES:
        return {
            "validation_version": READER_PROJECTION_VALIDATION_VERSION,
            "statuses": {"api": "not-applicable", "ba": "not-applicable"},
            "graph_sha256": {},
            "pending_count": 0,
            "stale_count": 0,
            "semantic_errors": [],
            "blocking_errors": [],
            "mechanical_refresh_count": 0,
            "semantic_review_count": 0,
        }
    graph = build_relationship_graph(root)
    requirements = schema["stages"][stage]
    plan = _load_plan(plan_path(transaction_dir)) if transaction_dir else None
    semantic_errors: list[str] = []
    blocking_errors: list[str] = []
    statuses: dict[str, str] = {}
    graph_hashes = {"api": graph.domain_hash("api"), "ba": graph.domain_hash("ba")}
    pending_count = 0
    stale_count = 0
    mechanical_refresh_count = 0
    semantic_review_count = 0
    if graph.errors:
        blocking_errors.extend(graph.errors)

    for domain in ("api", "ba"):
        applicable = graph.api_intent() if domain == "api" else graph.ba_intent()
        if domain == "ba":
            state = root / ".work" / "analysis-state.yaml"
            if state.is_file() and re.search(
                r'^business_model_status:\s*["\']?blocked["\']?\s*$',
                state.read_text(encoding="utf-8"),
                re.M,
            ):
                applicable = False
        requirement = requirements[domain]
        if domain == "ba" and requirement == "deferred" and not applicable:
            statuses[domain] = "deferred"
            continue
        if not applicable:
            statuses[domain] = "not-applicable"
            continue
        if requirement == "deferred":
            statuses[domain] = "deferred"
            continue

        current_plan = (
            plan
            if plan
            and plan.get("transaction_id") == transaction_id
            and plan.get("stage") == stage
            and plan.get("repository") == repository
            and plan.get("source_commit") == source_commit
            and domain in plan.get("domain_graph_sha256", {})
            else None
        )
        if current_plan is not None:
            if current_plan.get("domain_graph_sha256", {}).get(domain) != graph_hashes[domain]:
                statuses[domain] = "stale"
                stale_count += 1
                blocking_errors.append(f"{domain.upper()} Reader Projection relationship graph changed after refresh")
                continue
            plan_errors = current_plan.get("relationship_errors", [])
            if plan_errors:
                statuses[domain] = "invalid"
                blocking_errors.extend(str(item) for item in plan_errors)
                continue
            mechanical = validate_mechanical_projection(root, graph, domain)
            if mechanical:
                statuses[domain] = "invalid"
                semantic_errors.extend(mechanical)
                continue
            domain_items = [
                item
                for item in current_plan.get("semantic_items", [])
                if item.get("domain") == domain
            ]
            pending = []
            for item in domain_items:
                target_hash = _sha256(root / str(item.get("path")))
                if (
                    item.get("status") not in TERMINAL_REVIEW_STATUSES
                    or item.get("reviewed_sha256") != target_hash
                ):
                    pending.append(str(item.get("projection_id")))
            if pending:
                statuses[domain] = "stale"
                pending_count += len(pending)
                semantic_errors.extend(
                    f"Reader Projection semantic review is pending: {identifier}"
                    for identifier in pending
                )
            else:
                statuses[domain] = "current"
                semantic_review_count += len(domain_items)
                mechanical_refresh_count += sum(
                    item.get("status") == "refreshed"
                    for item in current_plan.get("mechanical_items", [])
                    if str(item.get("projection_id", "")).startswith(f"{domain}:")
                )
            continue

        receipt = _latest_projection_receipt(root, domain)
        if (
            requirement == "receipt-or-current"
            and receipt
            and receipt.get(f"reader_projection_{domain}_graph_sha256") == graph_hashes[domain]
        ):
            mechanical = validate_mechanical_projection(root, graph, domain)
            if mechanical:
                statuses[domain] = "invalid"
                semantic_errors.extend(mechanical)
            else:
                statuses[domain] = str(receipt[f"reader_projection_{domain}_status"])
            continue

        statuses[domain] = "stale"
        stale_count += 1
        blocking_errors.append(
            f"{domain.upper()} Reader Projection Plan is missing or outdated; run refresh-projections"
        )

    return {
        "validation_version": READER_PROJECTION_VALIDATION_VERSION,
        "statuses": statuses,
        "graph_sha256": graph_hashes,
        "pending_count": pending_count,
        "stale_count": stale_count,
        "semantic_errors": sorted(set(semantic_errors)),
        "blocking_errors": sorted(set(blocking_errors)),
        "mechanical_refresh_count": mechanical_refresh_count,
        "semantic_review_count": semantic_review_count,
    }


def receipt_projection_summary(evaluation: dict[str, Any]) -> dict[str, Any]:
    statuses = evaluation.get("statuses", {})
    hashes = evaluation.get("graph_sha256", {})
    return {
        "reader_projection_validation_version": evaluation.get("validation_version"),
        "reader_projection_api_status": statuses.get("api"),
        "reader_projection_ba_status": statuses.get("ba"),
        "reader_projection_api_graph_sha256": hashes.get("api"),
        "reader_projection_ba_graph_sha256": hashes.get("ba"),
        "reader_projection_pending_count": evaluation.get("pending_count", 0),
        "reader_projection_stale_count": evaluation.get("stale_count", 0),
        "reader_projection_mechanical_refresh_count": evaluation.get("mechanical_refresh_count", 0),
        "reader_projection_semantic_review_count": evaluation.get("semantic_review_count", 0),
    }
