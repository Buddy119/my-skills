#!/usr/bin/env python3
"""Validate a repository knowledge pack as one linked, evidence-grounded graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ALLOWED_EVIDENCE_STATUS = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
ALLOWED_COVERAGE = {"complete", "partial", "blocked"}
EVIDENCE_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?`"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")

DOCUMENTS = {
    "knowledge_map": "knowledge-map.md",
    "coverage_report": "coverage-report.md",
    "tech_overview": "tech-pack/repository-overview.md",
    "behavior_catalog": "tech-pack/behavior-catalog.yaml",
    "endpoint_matrix": "tech-pack/endpoints/endpoint-matrix.md",
    "data_asset_catalog": "tech-pack/data/data-asset-catalog.md",
    "data_lineage": "tech-pack/data/data-lineage.md",
    "state_transition_matrix": "tech-pack/data/state-transition-matrix.md",
    "field_catalog": "tech-pack/fields/field-catalog.md",
    "validation_rule_matrix": "tech-pack/fields/validation-rule-matrix.md",
    "field_lineage": "tech-pack/fields/field-lineage.md",
    "external_http_mapping_matrix": "tech-pack/fields/external-http-mapping-matrix.md",
    "runtime_config_matrix": "tech-pack/runtime/runtime-config-matrix.md",
    "dependency_matrix": "tech-pack/dependencies/dependency-matrix.md",
    "failure_taxonomy": "tech-pack/reliability/failure-taxonomy.md",
    "ba_overview": "ba-pack/business-overview.md",
    "ba_capability_map": "ba-pack/capability-map.md",
    "ba_data_lifecycle": "ba-pack/business-data-lifecycle.md",
    "ba_rule_catalog": "ba-pack/business-rule-catalog.md",
    "ba_exception_catalog": "ba-pack/business-exception-catalog.md",
    "ba_behavior_catalog": "ba-pack/behavior-catalog.md",
}

REQUIRED_HEADINGS = {
    "knowledge-map.md": {
        "Start here", "Repository at a glance", "Knowledge navigation",
        "Relationship map", "Coverage and known gaps",
    },
    "coverage-report.md": {
        "Inventory coverage", "Entry-point disposition", "Evidence surface coverage",
        "Unresolved coverage gaps", "Coverage conclusion",
    },
    "tech-pack/repository-overview.md": {
        "Observable responsibility", "Knowledge pack navigation", "Technology and deployment",
        "Entry-point inventory", "Behavior summary", "External connections",
        "Shared rules and components", "Coverage and limitations", "Repository-level open questions",
    },
    "tech-pack/endpoints/endpoint-matrix.md": {
        "Inbound endpoint inventory", "Shared handlers and aliases", "Endpoint coverage gaps",
    },
    "tech-pack/data/data-asset-catalog.md": {
        "Data assets", "Data ownership and consistency", "Data asset gaps",
    },
    "tech-pack/data/data-lineage.md": {
        "Repository data flow", "Object-level lineage", "Transaction and partial-success boundaries", "Lineage gaps",
    },
    "tech-pack/data/state-transition-matrix.md": {
        "Confirmed and inferred transitions", "Transition guards and concurrency", "No-state and unresolved cases",
    },
    "tech-pack/fields/field-catalog.md": {
        "Boundary and significant fields", "Enum and code sets", "Field coverage gaps",
    },
    "tech-pack/fields/validation-rule-matrix.md": {
        "Executable and schema rules", "Cross-field and conditional rules", "Assertion evidence", "Validation gaps",
    },
    "tech-pack/fields/field-lineage.md": {
        "Internal field transformations", "Unmapped, dropped, and generated fields", "Lineage gaps",
    },
    "tech-pack/fields/external-http-mapping-matrix.md": {
        "Proven outbound HTTP calls", "Request and consumed-response mappings", "Unmapped and unresolved external fields",
    },
    "tech-pack/runtime/runtime-config-matrix.md": {
        "Application configuration", "AWS Lambda and trigger runtime", "Configuration conflicts and gaps",
    },
    "tech-pack/dependencies/dependency-matrix.md": {
        "Dependency inventory", "Interaction and availability summary", "Dependency coverage gaps",
    },
    "tech-pack/reliability/failure-taxonomy.md": {
        "Failure registry", "Failure category summary", "Partial success and compensation", "Failure coverage gaps",
    },
    "ba-pack/business-overview.md": {
        "BA knowledge navigation", "Business capabilities", "Business actors and participants",
        "Business behavior landscape", "External business participants", "Cross-behavior business rules",
        "Business exceptions and dependencies", "Coverage and open questions",
    },
    "ba-pack/capability-map.md": {"Capabilities and outcomes", "Capability relationships", "Capability gaps"},
    "ba-pack/business-data-lifecycle.md": {"Business information journey", "Business data objects", "Business-visible state changes", "Lifecycle gaps"},
    "ba-pack/business-rule-catalog.md": {"Business-meaningful rules", "Rule interactions", "Excluded technical validation", "Rule gaps"},
    "ba-pack/business-exception-catalog.md": {"Business-visible exceptions", "Partial and delayed outcomes", "Exception gaps"},
}

ENTITY_SPECS = {
    "behaviors": ("behavior_id", "tech-pack/behavior-catalog.yaml", "document"),
    "endpoints": ("endpoint_id", "tech-pack/endpoints/endpoint-matrix.md", "contract_document"),
    "data_assets": ("data_asset_id", "tech-pack/data/data-asset-catalog.md", None),
    "fields": ("field_id", "tech-pack/fields/field-catalog.md", None),
    "validation_rules": ("rule_id", "tech-pack/fields/validation-rule-matrix.md", None),
    "dependencies": ("dependency_id", "tech-pack/dependencies/dependency-matrix.md", "stub_document"),
    "configs": ("config_id", "tech-pack/runtime/runtime-config-matrix.md", None),
    "failures": ("failure_id", "tech-pack/reliability/failure-taxonomy.md", None),
    "external_http_calls": ("call_id", "tech-pack/fields/external-http-mapping-matrix.md", None),
    "field_mappings": ("mapping_id", "tech-pack/fields/external-http-mapping-matrix.md", None),
}

ID_PATTERNS = {
    "behaviors": re.compile(r"^[a-z0-9][a-z0-9._-]+$"),
    "endpoints": re.compile(r"^EP-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "data_assets": re.compile(r"^DATA-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "fields": re.compile(r"^FIELD-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "validation_rules": re.compile(r"^VR-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "dependencies": re.compile(r"^DEP-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "configs": re.compile(r"^CFG-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "failures": re.compile(r"^FAIL-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "external_http_calls": re.compile(r"^HTTP-[A-Za-z0-9][A-Za-z0-9._-]*$"),
    "field_mappings": re.compile(r"^MAP-[A-Za-z0-9][A-Za-z0-9._-]*$"),
}

REQUIRED_ENTITY_KEYS = {
    "behaviors": {
        "behavior_id", "category", "status", "document", "ba_document", "duplicate_of",
        "endpoint_ids", "data_asset_ids", "field_ids", "dependency_ids", "config_ids", "failure_ids",
    },
    "endpoints": {
        "endpoint_id", "method", "route", "status", "primary_behavior_id", "behavior_ids",
        "contract_document", "contract_alias_of",
    },
    "data_assets": {"data_asset_id", "kind", "name", "status", "behavior_ids"},
    "fields": {"field_id", "boundary_id", "path", "status", "validation_rule_ids"},
    "validation_rules": {"rule_id", "status", "behavior_ids", "field_ids", "failure_ids"},
    "dependencies": {
        "dependency_id", "type", "material", "status", "stub_document", "behavior_ids",
        "endpoint_ids", "config_ids", "failure_ids",
    },
    "configs": {
        "config_id", "key", "category", "status", "behavior_ids", "endpoint_ids",
        "dependency_ids", "failure_ids",
    },
    "failures": {
        "failure_id", "category", "status", "behavior_ids", "endpoint_ids", "dependency_ids", "config_ids",
    },
    "external_http_calls": {
        "call_id", "dependency_id", "status", "behavior_ids", "config_ids", "failure_ids",
    },
    "field_mappings": {"mapping_id", "call_id", "direction", "status", "field_ids"},
}

REFERENCE_SECTIONS = {
    "behavior_ids": "behaviors",
    "endpoint_ids": "endpoints",
    "data_asset_ids": "data_assets",
    "field_ids": "fields",
    "validation_rule_ids": "validation_rules",
    "dependency_ids": "dependencies",
    "config_ids": "configs",
    "failure_ids": "failures",
    "external_http_call_ids": "external_http_calls",
    "external_mapping_ids": "field_mappings",
}

PLACEHOLDERS = (
    "repository-name", "git-commit-or-unknown", "repository.behavior-name", "path/to/",
)


def clean_value(value: str) -> str | None | list[str]:
    value = value.strip()
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    if value.lower() in {"null", "none"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def top_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", text, re.M)
    return match.group(1).strip() if match else None


def section_lines(text: str, section: str) -> list[str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line == f"{section}: []":
            return []
        if line != f"{section}:":
            continue
        result: list[str] = []
        for nested in lines[index + 1 :]:
            if nested and not nested[0].isspace():
                break
            result.append(nested)
        return result
    return []


def parse_mapping(text: str, section: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in section_lines(text, section):
        match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if match:
            value = clean_value(match.group(2))
            if isinstance(value, str):
                result[match.group(1)] = value
    return result


def parse_entities(text: str, section: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    active_list: str | None = None
    for line in section_lines(text, section):
        start = re.match(r"^  - ([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if start:
            if current is not None:
                entries.append(current)
            current = {start.group(1): clean_value(start.group(2))}
            active_list = None
            continue
        scalar = re.match(r"^    ([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if scalar and current is not None:
            value = clean_value(scalar.group(2))
            current[scalar.group(1)] = value if value != "" else []
            active_list = scalar.group(1) if value == "" or value == [] else None
            continue
        item = re.match(r"^      -\s*[\"']?([^\"'\n]+?)[\"']?\s*$", line)
        if item and current is not None and active_list:
            values = current.setdefault(active_list, [])
            if isinstance(values, list):
                values.append(item.group(1).strip())
    if current is not None:
        entries.append(current)
    return entries


def split_frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end], text[end + 5 :]


def resolve_pack_path(pack: Path, relative: str) -> Path | None:
    target = (pack / relative).resolve()
    try:
        target.relative_to(pack)
    except ValueError:
        return None
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()

    pack = args.pack.expanduser().resolve()
    repo = args.repo.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not pack.is_dir():
        print(f"ERROR: pack directory does not exist: {pack}")
        return 2
    if not repo.is_dir():
        print(f"ERROR: repository directory does not exist: {repo}")
        return 2

    manifest_path = pack / "knowledge-manifest.yaml"
    if not manifest_path.is_file():
        print("ERROR: knowledge-manifest.yaml does not exist")
        return 1
    manifest = manifest_path.read_text(encoding="utf-8")

    repository = top_scalar(manifest, "repository")
    source_commit = top_scalar(manifest, "source_commit")
    analysis_mode = top_scalar(manifest, "analysis_mode")
    coverage_status = top_scalar(manifest, "coverage_status")
    if not repository:
        errors.append("manifest repository is missing")
    if not source_commit:
        errors.append("manifest source_commit is missing")
    if analysis_mode not in {"automatic", "targeted"}:
        errors.append("manifest analysis_mode must be automatic or targeted")
    if coverage_status not in ALLOWED_COVERAGE:
        errors.append("manifest coverage_status must be complete, partial, or blocked")
    if analysis_mode == "targeted" and coverage_status == "complete":
        errors.append("targeted analysis cannot claim complete coverage")

    document_map = parse_mapping(manifest, "documents")
    for key, expected in DOCUMENTS.items():
        if document_map.get(key) != expected:
            errors.append(f"manifest documents.{key} must be {expected}")
        target = pack / expected
        if not target.is_file():
            errors.append(f"required knowledge document does not exist: {expected}")

    evidence_index = pack / ".work/evidence-index.json"
    if not evidence_index.is_file():
        errors.append(".work/evidence-index.json does not exist")
    else:
        try:
            indexed = json.loads(evidence_index.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"evidence index is not valid JSON: {exc}")
        else:
            if indexed.get("repository") != repo.name:
                errors.append("evidence index repository does not match --repo directory name")
            indexed_commit = indexed.get("source_commit")
            if indexed_commit and indexed_commit != source_commit:
                errors.append("evidence index source_commit does not match manifest")
            files = indexed.get("files")
            summary_data = indexed.get("summary")
            skipped = indexed.get("skipped")
            if not isinstance(files, list) or not isinstance(skipped, list) or not isinstance(summary_data, dict):
                errors.append("evidence index must contain files, skipped, and summary structures")
            else:
                if summary_data.get("indexed_files") != len(files):
                    errors.append("evidence index indexed_files count does not match files")
                if summary_data.get("skipped_files") != len(skipped):
                    errors.append("evidence index skipped_files count does not match skipped")
                if not isinstance(summary_data.get("marker_counts"), dict):
                    errors.append("evidence index summary.marker_counts must be an object")

    all_entities: dict[str, list[dict[str, object]]] = {}
    id_index: dict[str, str] = {}
    for section, (id_key, canonical_document, path_key) in ENTITY_SPECS.items():
        entries = parse_entities(manifest, section)
        all_entities[section] = entries
        canonical_path = pack / canonical_document
        canonical_text = canonical_path.read_text(encoding="utf-8") if canonical_path.is_file() else ""
        for entry in entries:
            missing_entry_keys = sorted(REQUIRED_ENTITY_KEYS[section] - set(entry))
            if missing_entry_keys:
                errors.append(f"manifest {section} entry missing key(s): " + ", ".join(missing_entry_keys))
            entity_id = entry.get(id_key)
            if not isinstance(entity_id, str) or not entity_id:
                errors.append(f"manifest {section} entry is missing {id_key}")
                continue
            if entity_id in id_index:
                errors.append(f"duplicate manifest ID: {entity_id}")
            id_index[entity_id] = section
            if not ID_PATTERNS[section].fullmatch(entity_id):
                errors.append(f"invalid stable ID for {section}: {entity_id}")
            if entity_id not in canonical_text:
                errors.append(f"{entity_id} is missing from canonical document {canonical_document}")
            status = entry.get("status")
            if section == "behaviors":
                allowed = {"documented", "technical", "duplicate", "excluded", "blocked"}
                if status not in allowed:
                    errors.append(f"invalid behavior status for {entity_id}: {status}")
            elif status not in ALLOWED_EVIDENCE_STATUS:
                errors.append(f"invalid evidence status for {entity_id}: {status}")
            if section == "field_mappings" and entry.get("direction") not in {
                "eapi-to-external", "external-to-eapi"
            }:
                errors.append(f"invalid external HTTP mapping direction for {entity_id}")
            requires_path = True
            if section == "behaviors" and status in {"duplicate", "excluded", "blocked"}:
                requires_path = False
            if section == "dependencies":
                material = entry.get("material")
                if material not in {"Yes", "No"}:
                    errors.append(f"dependency {entity_id} material must be Yes or No")
                requires_path = material == "Yes"
            if path_key:
                path_value = entry.get(path_key)
                if not isinstance(path_value, str) and requires_path:
                    errors.append(f"{entity_id} is missing {path_key}")
                elif isinstance(path_value, str):
                    target = resolve_pack_path(pack, path_value)
                    if target is None or not target.is_file():
                        errors.append(f"{entity_id} linked document does not exist: {path_value}")
            if section == "behaviors":
                ba_document = entry.get("ba_document")
                if isinstance(ba_document, str):
                    target = resolve_pack_path(pack, ba_document)
                    if target is None or not target.is_file():
                        errors.append(f"{entity_id} BA document does not exist: {ba_document}")
                category = entry.get("category")
                if category in {"business", "integration"} and status == "documented" and not isinstance(ba_document, str):
                    errors.append(f"business/integration behavior {entity_id} must have ba_document")
                if category == "technical" and isinstance(ba_document, str):
                    errors.append(f"technical behavior {entity_id} must not have ba_document")

    for section, entries in all_entities.items():
        for entry in entries:
            entity_label = next((str(entry.get(key)) for key in entry if key.endswith("_id") and entry.get(key)), section)
            for key, value in entry.items():
                if key in REFERENCE_SECTIONS and isinstance(value, list):
                    for reference in value:
                        if id_index.get(reference) != REFERENCE_SECTIONS[key]:
                            errors.append(f"{entity_label} references unknown or wrong-type ID in {key}: {reference}")
            scalar_references = {
                "primary_behavior_id": "behaviors",
                "dependency_id": "dependencies",
                "call_id": "external_http_calls",
                "contract_alias_of": "endpoints",
                "duplicate_of": "behaviors",
            }
            for key, expected_section in scalar_references.items():
                value = entry.get(key)
                if isinstance(value, str) and id_index.get(value) != expected_section:
                    errors.append(f"{entity_label} references unknown {key}: {value}")

    summary = parse_mapping(manifest, "summary")
    for section in ENTITY_SPECS:
        raw = summary.get(section)
        try:
            reported = int(raw) if raw is not None else None
        except ValueError:
            reported = None
        actual = len(all_entities[section])
        if reported != actual:
            errors.append(f"manifest summary.{section} is {raw}; expected {actual}")

    coverage_text = (pack / "coverage-report.md").read_text(encoding="utf-8") if (pack / "coverage-report.md").is_file() else ""
    coverage_rows = {
        "Behaviors": len(all_entities["behaviors"]),
        "Endpoints": len(all_entities["endpoints"]),
        "Data assets": len(all_entities["data_assets"]),
        "Fields": len(all_entities["fields"]),
        "Validation rules": len(all_entities["validation_rules"]),
        "Dependencies": len(all_entities["dependencies"]),
        "Runtime configurations": len(all_entities["configs"]),
        "Failures": len(all_entities["failures"]),
        "External HTTP calls and mappings": len(all_entities["external_http_calls"]) + len(all_entities["field_mappings"]),
    }
    for label, expected in coverage_rows.items():
        match = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*(\d+)\s*\|", coverage_text, re.M)
        if not match:
            errors.append(f"coverage-report.md is missing inventory row: {label}")
        elif int(match.group(1)) != expected:
            errors.append(f"coverage discovered count for {label} is {match.group(1)}; expected {expected}")

    markdown_files = sorted(pack.rglob("*.md"))
    for document in markdown_files:
        relative = document.relative_to(pack).as_posix()
        text = document.read_text(encoding="utf-8")
        if any(placeholder in text for placeholder in PLACEHOLDERS):
            errors.append(f"template placeholder remains in {relative}")
        parsed = split_frontmatter(text)
        if parsed:
            frontmatter, body = parsed
            doc_repository = top_scalar(frontmatter, "repository")
            doc_commit = top_scalar(frontmatter, "source_commit")
            if not doc_repository:
                errors.append(f"repository is missing from frontmatter in {relative}")
            elif doc_repository != repository:
                errors.append(f"repository mismatch in {relative}")
            if not doc_commit:
                errors.append(f"source_commit is missing from frontmatter in {relative}")
            elif doc_commit != source_commit:
                errors.append(f"source_commit mismatch in {relative}")
        else:
            body = text
            errors.append(f"Markdown document must contain YAML frontmatter: {relative}")

        required = REQUIRED_HEADINGS.get(relative)
        if required:
            headings = set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))
            missing = sorted(required - headings)
            if missing:
                errors.append(f"{relative} missing section(s): " + ", ".join(missing))

        if relative.startswith("ba-pack/") and EVIDENCE_RE.search(body):
            errors.append(f"BA document contains raw source citation: {relative}")

        for match in MARKDOWN_LINK_RE.finditer(body):
            target_text = match.group("target").strip().strip("<>")
            if not target_text or target_text.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_text = target_text.split("#", 1)[0]
            target = (document.parent / target_text).resolve()
            try:
                target.relative_to(pack)
            except ValueError:
                errors.append(f"local link escapes pack in {relative}: {target_text}")
                continue
            if not target.exists():
                errors.append(f"broken local link in {relative}: {target_text}")

        if relative.startswith("tech-pack/"):
            citations = list(EVIDENCE_RE.finditer(body))
            if not citations and relative not in {"tech-pack/behavior-catalog.yaml"}:
                warnings.append(f"no source citation found in technical document: {relative}")
            for citation in citations:
                source_relative = citation.group("path")
                start = int(citation.group("start"))
                end = int(citation.group("end") or start)
                source = (repo / source_relative).resolve()
                try:
                    source.relative_to(repo)
                except ValueError:
                    errors.append(f"citation escapes repository in {relative}: {source_relative}")
                    continue
                if not source.is_file():
                    errors.append(f"cited file does not exist in {relative}: {source_relative}")
                    continue
                line_count = sum(1 for _ in source.open(encoding="utf-8", errors="replace"))
                if start < 1 or end < start or end > line_count:
                    errors.append(f"citation outside bounds in {relative}: {source_relative}:{start}-{end}")

    for warning in sorted(set(warnings)):
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(set(warnings))} warning(s)")
        return 1
    counts = ", ".join(f"{section}={len(entries)}" for section, entries in all_entities.items())
    print(f"OK: repository knowledge pack is consistent ({counts}); {len(set(warnings))} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
