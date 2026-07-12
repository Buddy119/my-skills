#!/usr/bin/env python3
"""Validate a repository knowledge pack as one linked, evidence-grounded graph."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from runtime_guard import run_guarded
from validate_claim_ledger import CLAIM_MARKER_RE, material_blocks, validate_claim_pack
from validate_evidence_index import validate_evidence_index
from validate_flow_separation import validate_pair, validate_tech_document


ALLOWED_EVIDENCE_STATUS = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
ALLOWED_COVERAGE = {"complete", "partial", "blocked"}
EVIDENCE_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?`"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")

DOCUMENTS = {
    "claim_ledger": ".work/claim-ledger.json",
    "claim_audit": ".work/claim-audit.json",
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
        "tech_flow_model", "ba_flow_model", "endpoint_ids", "data_asset_ids", "field_ids",
        "dependency_ids", "config_ids", "failure_ids", "claim_ids",
    },
    "endpoints": {
        "endpoint_id", "method", "route", "status", "primary_behavior_id", "behavior_ids",
        "contract_document", "contract_alias_of", "claim_ids",
    },
    "data_assets": {"data_asset_id", "kind", "name", "status", "behavior_ids", "claim_ids"},
    "fields": {
        "field_id", "boundary_id", "boundary_kind", "observation_kind", "path",
        "status", "validation_rule_ids", "claim_ids",
    },
    "validation_rules": {"rule_id", "status", "behavior_ids", "field_ids", "failure_ids", "claim_ids"},
    "dependencies": {
        "dependency_id", "type", "material", "status", "stub_document", "behavior_ids",
        "endpoint_ids", "config_ids", "failure_ids", "claim_ids",
    },
    "configs": {
        "config_id", "key", "category", "status", "behavior_ids", "endpoint_ids",
        "dependency_ids", "failure_ids", "claim_ids",
    },
    "failures": {
        "failure_id", "category", "status", "behavior_ids", "endpoint_ids", "dependency_ids", "config_ids", "claim_ids",
    },
    "external_http_calls": {
        "call_id", "dependency_id", "status", "behavior_ids", "config_ids", "failure_ids", "claim_ids",
    },
    "field_mappings": {"mapping_id", "call_id", "direction", "status", "field_ids", "claim_ids"},
}

ENTITY_CLAIM_TYPES = {
    "behaviors": {
        "behavior-trigger", "behavior-step", "behavior-branch", "input", "output",
        "side-effect-call", "validation", "data-read", "data-write", "state-transition",
        "configuration", "dependency", "failure", "retry", "mapping", "business-meaning",
        "business-rule", "business-outcome",
    },
    "endpoints": {"endpoint-contract"},
    "data_assets": {"data-read", "data-write", "state-transition", "side-effect-call"},
    "fields": {"field", "input", "output", "validation", "mapping", "endpoint-contract", "side-effect-call"},
    "validation_rules": {"validation", "business-rule"},
    "dependencies": {"dependency", "side-effect-call"},
    "configs": {"configuration"},
    "failures": {"failure"},
    "external_http_calls": {"side-effect-call"},
    "field_mappings": {"mapping"},
}

FIELD_BOUNDARY_KINDS = {
    "inbound-api", "outbound-http-request", "outbound-http-response", "event",
    "persistence", "dependency-call", "local-input", "local-result", "local-lookup", "unknown",
}
FIELD_OBSERVATION_KINDS = {
    "declared-contract-field", "schema-field", "executable-boundary-read",
    "executable-boundary-write", "local-lookup-key", "local-result", "inferred-field", "unknown",
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
    "repository-name", "git-commit-or-unknown", "repository.behavior-name", "path/to/", "SCAFFOLD_ONLY",
)

ROOT_TEMPLATE_BY_DOCUMENT = {
    "knowledge-map.md": "knowledge-map-template.md",
    "coverage-report.md": "coverage-report-template.md",
}


def normalized_material_block(value: str) -> str:
    value = CLAIM_MARKER_RE.sub("", value)
    return " ".join(value.split())


def validate_entity_claim_types(
    section: str,
    entity_id: str,
    entity_claims: list[dict[str, object]],
) -> list[str]:
    compatible_types = ENTITY_CLAIM_TYPES[section]
    if entity_claims and not any(
        claim.get("claim_type") in compatible_types for claim in entity_claims
    ):
        return [
            f"{entity_id} has no entity-compatible claim type; expected one of: "
            + ", ".join(sorted(compatible_types))
        ]
    return []


def manifest_claim_corpus(entity_claims: list[dict[str, object]]) -> str:
    values: list[str] = []
    for claim in entity_claims:
        values.append(str(claim.get("statement", "")))
        for key in ("render_terms",):
            raw = claim.get(key)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
        verification = claim.get("verification")
        if isinstance(verification, dict) and isinstance(verification.get("tokens"), list):
            values.extend(str(item) for item in verification["tokens"])
    return " ".join(values).lower()


def validate_entity_scalar_claim_bindings(
    section: str,
    entity_id: str,
    entry: dict[str, object],
    entity_claims: list[dict[str, object]],
) -> list[str]:
    """Bind machine-readable manifest values to the content of approved claims."""

    errors: list[str] = []
    corpus = manifest_claim_corpus(entity_claims)
    checks: list[tuple[str, str, list[str]]] = []
    if section == "endpoints":
        for key in ("method", "route"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                checks.append((key, value, [value.lower()]))
    elif section == "fields":
        value = entry.get("path")
        if isinstance(value, str) and value not in {"", "$", "Unknown"}:
            tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9_]+", value)]
            candidates = [value.lower(), *sorted(tokens, key=len, reverse=True)]
            checks.append(("path", value, candidates))
    elif section == "configs":
        value = entry.get("key")
        if isinstance(value, str) and value:
            checks.append(("key", value, [value.lower()]))
    elif section == "dependencies":
        value = entry.get("type")
        if isinstance(value, str) and value.lower() not in {"", "other", "unknown", "opaque"}:
            checks.append(("type", value, [value.lower()]))
    elif section == "failures":
        value = entry.get("category")
        if isinstance(value, str) and value.lower() not in {"", "unknown", "unknown/unclassified"}:
            checks.append(("category", value, [value.lower()]))
    elif section == "field_mappings":
        value = entry.get("direction")
        if isinstance(value, str) and value:
            checks.append(("direction", value, [value.lower(), value.lower().replace("-", " ")]))

    for key, value, candidates in checks:
        meaningful = [candidate for candidate in candidates if len(candidate) >= 2]
        if meaningful and not any(candidate in corpus for candidate in meaningful):
            errors.append(
                f"{entity_id} manifest {key} is not asserted by its bound claims: {value}"
            )
    return errors


def validate_field_entity(
    entity_id: str,
    entry: dict[str, object],
    entity_claims: list[dict[str, object]],
) -> list[str]:
    errors: list[str] = []
    boundary_kind = entry.get("boundary_kind")
    observation_kind = entry.get("observation_kind")
    status = entry.get("status")
    if boundary_kind not in FIELD_BOUNDARY_KINDS:
        errors.append(f"{entity_id} has invalid boundary_kind: {boundary_kind}")
    if observation_kind not in FIELD_OBSERVATION_KINDS:
        errors.append(f"{entity_id} has invalid observation_kind: {observation_kind}")
    if observation_kind == "local-lookup-key" and boundary_kind != "local-lookup":
        errors.append(
            f"{entity_id} local-lookup-key must use boundary_kind local-lookup; "
            "a local lookup does not establish an external response field"
        )
    if boundary_kind == "outbound-http-response" and status == "Confirmed":
        has_direct_schema = any(
            isinstance(evidence, dict)
            and evidence.get("relation") == "supports"
            and evidence.get("support_level") == "direct"
            and evidence.get("source_kind") == "schema"
            for claim in entity_claims
            if isinstance(claim.get("evidence"), list)
            for evidence in claim["evidence"]
        )
        if observation_kind not in {"declared-contract-field", "schema-field"} or not has_direct_schema:
            errors.append(
                f"{entity_id} Confirmed outbound HTTP response field requires direct schema evidence; "
                "an executable lookup alone must be modeled as local-lookup-key"
            )
    return errors


def run_document_validator(
    script_name: str,
    document: Path,
    repo: Path,
) -> tuple[list[str], list[str]]:
    script = Path(__file__).resolve().with_name(script_name)
    command = [
        sys.executable,
        "-E",
        "-S",
        "-B",
        "-X",
        "utf8",
        str(script),
        str(document),
        "--repo",
        str(repo),
    ]
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("PYTHON")
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        cwd=script.parent.parent,
    )
    output_lines = [line for line in (result.stdout + result.stderr).splitlines() if line]
    warnings = [line for line in output_lines if line.startswith("WARNING:")]
    if result.returncode == 0:
        return [], warnings
    details = " | ".join(output_lines[:12])
    return [f"{script_name} failed for {document.name}: {details}"], warnings


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


def validate_behavior_catalog(
    catalog_path: Path,
    pack: Path,
    manifest_behaviors: list[dict[str, object]],
    repository: str | None,
    source_commit: str | None,
    analysis_mode: str | None,
) -> list[str]:
    errors: list[str] = []
    if not catalog_path.is_file():
        return ["tech-pack/behavior-catalog.yaml does not exist"]
    text = catalog_path.read_text(encoding="utf-8")
    for key, expected in (
        ("repository", repository),
        ("source_commit", source_commit),
        ("analysis_mode", analysis_mode),
    ):
        if top_scalar(text, key) != expected:
            errors.append(f"behavior catalog {key} does not match manifest")

    catalog_entries = parse_entities(text, "behaviors")
    catalog_by_id = {
        entry.get("behavior_id"): entry
        for entry in catalog_entries
        if isinstance(entry.get("behavior_id"), str)
    }
    manifest_by_id = {
        entry.get("behavior_id"): entry
        for entry in manifest_behaviors
        if isinstance(entry.get("behavior_id"), str)
    }
    if set(catalog_by_id) != set(manifest_by_id):
        errors.append("behavior catalog IDs do not exactly match manifest behaviors")

    scalar_keys = {"category", "status", "duplicate_of"}
    list_keys = {
        "claim_ids", "endpoint_ids", "data_asset_ids", "field_ids",
        "dependency_ids", "config_ids", "failure_ids",
    }
    path_keys = {"document", "ba_document", "tech_flow_model", "ba_flow_model"}
    for behavior_id in sorted(set(catalog_by_id) & set(manifest_by_id)):
        catalog_entry = catalog_by_id[behavior_id]
        manifest_entry = manifest_by_id[behavior_id]
        for key in scalar_keys | list_keys:
            if catalog_entry.get(key) != manifest_entry.get(key):
                errors.append(f"behavior catalog {behavior_id} {key} does not match manifest")
        for key in path_keys:
            catalog_value = catalog_entry.get(key)
            manifest_value = manifest_entry.get(key)
            if catalog_value is None and manifest_value is None:
                continue
            if not isinstance(catalog_value, str) or not isinstance(manifest_value, str):
                errors.append(f"behavior catalog {behavior_id} {key} does not match manifest")
                continue
            catalog_target = (catalog_path.parent / catalog_value).resolve()
            manifest_target = resolve_pack_path(pack, manifest_value)
            if manifest_target is None or catalog_target != manifest_target:
                errors.append(f"behavior catalog {behavior_id} {key} does not resolve to the manifest path")

    summary = parse_mapping(text, "summary")
    expected_summary = {
        "total_inventory": len(manifest_behaviors),
        "pending": 0,
        "documented": sum(entry.get("status") == "documented" for entry in manifest_behaviors),
        "technical": sum(entry.get("status") == "technical" for entry in manifest_behaviors),
        "duplicate": sum(entry.get("status") == "duplicate" for entry in manifest_behaviors),
        "excluded": sum(entry.get("status") == "excluded" for entry in manifest_behaviors),
        "blocked": sum(entry.get("status") == "blocked" for entry in manifest_behaviors),
    }
    for key, expected in expected_summary.items():
        try:
            actual = int(summary.get(key, ""))
        except ValueError:
            actual = None
        if actual != expected:
            errors.append(f"behavior catalog summary.{key} is {summary.get(key)}; expected {expected}")
    return errors


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

    index_errors, index_warnings, indexed_snapshot = validate_evidence_index(
        pack / ".work" / "evidence-index.json",
        repo,
        repository,
        source_commit,
    )
    errors.extend("evidence snapshot: " + error for error in index_errors)
    warnings.extend("evidence snapshot: " + warning for warning in index_warnings)

    claim_errors, claim_warnings, claims_by_id = validate_claim_pack(
        pack,
        repo,
        repository,
        source_commit,
    )
    errors.extend("claim provenance: " + error for error in claim_errors)
    warnings.extend("claim provenance: " + warning for warning in claim_warnings)

    all_entities: dict[str, list[dict[str, object]]] = {}
    id_index: dict[str, str] = {}
    for section, (id_key, canonical_document, path_key) in ENTITY_SPECS.items():
        entries = parse_entities(manifest, section)
        all_entities[section] = entries
        canonical_path = pack / canonical_document
        canonical_text = canonical_path.read_text(encoding="utf-8") if canonical_path.is_file() else ""
        for entry in entries:
            missing_entry_keys = sorted(REQUIRED_ENTITY_KEYS[section] - set(entry))
            unexpected_entry_keys = sorted(set(entry) - REQUIRED_ENTITY_KEYS[section])
            if missing_entry_keys:
                errors.append(f"manifest {section} entry missing key(s): " + ", ".join(missing_entry_keys))
            if unexpected_entry_keys:
                errors.append(f"manifest {section} entry contains unexpected key(s): " + ", ".join(unexpected_entry_keys))
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
            entity_claim_ids = entry.get("claim_ids")
            entity_claims: list[dict[str, object]] = []
            if not isinstance(entity_claim_ids, list) or not entity_claim_ids:
                errors.append(f"{entity_id} must reference at least one approved claim_id")
            else:
                if len(entity_claim_ids) != len(set(entity_claim_ids)):
                    errors.append(f"{entity_id} claim_ids contains duplicates")
                for claim_id in entity_claim_ids:
                    claim = claims_by_id.get(claim_id) if isinstance(claim_id, str) else None
                    if claim is None:
                        errors.append(f"{entity_id} references unknown claim_id: {claim_id}")
                        continue
                    entity_claims.append(claim)
                    subjects = claim.get("subject_ids")
                    if not isinstance(subjects, list) or entity_id not in subjects:
                        errors.append(f"claim {claim_id} is not bound to manifest entity {entity_id}")
                errors.extend(validate_entity_claim_types(section, entity_id, entity_claims))
                errors.extend(
                    validate_entity_scalar_claim_bindings(section, entity_id, entry, entity_claims)
                )
            status = entry.get("status")
            if section == "behaviors":
                allowed = {"documented", "technical", "duplicate", "excluded", "blocked"}
                if status not in allowed:
                    errors.append(f"invalid behavior status for {entity_id}: {status}")
            elif status not in ALLOWED_EVIDENCE_STATUS:
                errors.append(f"invalid evidence status for {entity_id}: {status}")
            elif entity_claims:
                status_strength = {"Unknown": 0, "Conflicting": 1, "Inferred": 2, "Confirmed": 3}
                weakest = min(status_strength.get(str(claim.get("status")), 0) for claim in entity_claims)
                if status_strength[status] > weakest:
                    errors.append(f"{entity_id} status is stronger than one or more bound claims")
            if section == "fields":
                errors.extend(validate_field_entity(entity_id, entry, entity_claims))
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
            if section == "endpoints" and isinstance(entry.get("contract_document"), str):
                contract_path = resolve_pack_path(pack, str(entry["contract_document"]))
                if contract_path is not None and contract_path.is_file():
                    parsed_contract = split_frontmatter(contract_path.read_text(encoding="utf-8"))
                    if parsed_contract is None:
                        errors.append(f"{entity_id} contract has no valid frontmatter")
                    else:
                        contract_frontmatter, _contract_body = parsed_contract
                        for manifest_key, contract_key in (
                            ("endpoint_id", "endpoint_id"),
                            ("method", "method"),
                            ("route", "route"),
                            ("primary_behavior_id", "primary_behavior_id"),
                        ):
                            if entry.get(manifest_key) != top_scalar(contract_frontmatter, contract_key):
                                errors.append(
                                    f"{entity_id} manifest {manifest_key} does not match endpoint contract"
                                )
                        if entry.get("status") != top_scalar(contract_frontmatter, "contract_status"):
                            errors.append(f"{entity_id} manifest status does not match endpoint contract")
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
                tech_flow_model = entry.get("tech_flow_model")
                ba_flow_model = entry.get("ba_flow_model")
                requires_tech_model = status in {"documented", "technical"}
                if not isinstance(tech_flow_model, str) and requires_tech_model:
                    errors.append(f"behavior {entity_id} must have tech_flow_model")
                elif isinstance(tech_flow_model, str):
                    target = resolve_pack_path(pack, tech_flow_model)
                    if target is None or not target.is_file():
                        errors.append(f"behavior {entity_id} Tech flow model does not exist: {tech_flow_model}")
                requires_ba_model = category in {"business", "integration"} and status == "documented"
                if not isinstance(ba_flow_model, str) and requires_ba_model:
                    errors.append(f"business/integration behavior {entity_id} must have ba_flow_model")
                elif isinstance(ba_flow_model, str):
                    target = resolve_pack_path(pack, ba_flow_model)
                    if target is None or not target.is_file():
                        errors.append(f"behavior {entity_id} BA flow model does not exist: {ba_flow_model}")
                if category == "technical" and isinstance(ba_flow_model, str):
                    errors.append(f"technical behavior {entity_id} must not have ba_flow_model")

    errors.extend(
        validate_behavior_catalog(
            pack / "tech-pack" / "behavior-catalog.yaml",
            pack,
            all_entities["behaviors"],
            repository,
            source_commit,
            analysis_mode,
        )
    )

    for claim_id, claim in claims_by_id.items():
        subjects = claim.get("subject_ids")
        if isinstance(subjects, list):
            for subject_id in subjects:
                if subject_id not in id_index:
                    errors.append(f"claim {claim_id} references subject ID absent from manifest: {subject_id}")

    if coverage_status == "complete" and isinstance(indexed_snapshot, dict):
        snapshot_summary = indexed_snapshot.get("summary")
        marker_counts = snapshot_summary.get("marker_counts") if isinstance(snapshot_summary, dict) else None
        if isinstance(marker_counts, dict):
            signal_requirements = {
                "endpoint": ("endpoints",),
                "lambda-entry": ("behaviors",),
                "external-http-call": ("external_http_calls", "dependencies"),
                "config-read": ("configs",),
                "data-access": ("data_assets", "dependencies"),
                "event-publish": ("data_assets", "dependencies"),
                "failure-branch": ("failures",),
                "retry-resilience": ("configs", "failures"),
                "state-mutation": ("data_assets",),
                "auth": ("fields", "validation_rules", "failures"),
            }
            for marker_kind, sections in signal_requirements.items():
                marker_count = marker_counts.get(marker_kind, 0)
                if isinstance(marker_count, int) and marker_count > 0 and not any(all_entities[section] for section in sections):
                    errors.append(
                        f"coverage cannot be complete: {marker_count} {marker_kind} signal(s) have no canonical entity disposition"
                    )

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

    for entry in all_entities["behaviors"]:
        status = entry.get("status")
        document_value = entry.get("document")
        if status not in {"documented", "technical"} or not isinstance(document_value, str):
            continue
        tech_document = resolve_pack_path(pack, document_value)
        ba_document_value = entry.get("ba_document")
        if tech_document is None or not tech_document.is_file():
            continue
        parsed_tech = split_frontmatter(tech_document.read_text(encoding="utf-8"))
        if parsed_tech is not None:
            tech_frontmatter, _tech_body = parsed_tech
            document_model_value = top_scalar(tech_frontmatter, "tech_flow_model")
            manifest_model_value = entry.get("tech_flow_model")
            if isinstance(document_model_value, str) and isinstance(manifest_model_value, str):
                document_model = (tech_document.parent / document_model_value).resolve()
                manifest_model = resolve_pack_path(pack, manifest_model_value)
                if manifest_model is None or document_model != manifest_model:
                    errors.append(
                        f"{entry.get('behavior_id')} manifest tech_flow_model does not match Tech document frontmatter"
                    )
        document_errors, document_warnings = run_document_validator(
            "validate_behavior_doc.py", tech_document, repo
        )
        errors.extend(document_errors)
        warnings.extend(document_warnings)
        if isinstance(ba_document_value, str):
            ba_document = resolve_pack_path(pack, ba_document_value)
            if ba_document is not None and ba_document.is_file():
                parsed_ba = split_frontmatter(ba_document.read_text(encoding="utf-8"))
                if parsed_ba is not None:
                    ba_frontmatter, _ba_body = parsed_ba
                    document_model_value = top_scalar(ba_frontmatter, "ba_flow_model")
                    manifest_model_value = entry.get("ba_flow_model")
                    if isinstance(document_model_value, str) and isinstance(manifest_model_value, str):
                        document_model = (ba_document.parent / document_model_value).resolve()
                        manifest_model = resolve_pack_path(pack, manifest_model_value)
                        if manifest_model is None or document_model != manifest_model:
                            errors.append(
                                f"{entry.get('behavior_id')} manifest ba_flow_model does not match BA document frontmatter"
                            )
                ba_errors, ba_warnings = run_document_validator(
                    "validate_ba_behavior.py", ba_document, repo
                )
                errors.extend(ba_errors)
                warnings.extend(ba_warnings)
                flow_errors, flow_warnings, _metrics = validate_pair(tech_document, ba_document, repo)
                errors.extend(f"{entry.get('behavior_id')} flow separation: {error}" for error in flow_errors)
                warnings.extend(f"{entry.get('behavior_id')} flow separation: {warning}" for warning in flow_warnings)
        else:
            flow_errors, flow_warnings = validate_tech_document(tech_document, repo)
            errors.extend(f"{entry.get('behavior_id')} Tech flow: {error}" for error in flow_errors)
            warnings.extend(f"{entry.get('behavior_id')} Tech flow: {warning}" for warning in flow_warnings)

    for entry in all_entities["endpoints"]:
        contract_value = entry.get("contract_document")
        if not isinstance(contract_value, str):
            continue
        contract_document = resolve_pack_path(pack, contract_value)
        if contract_document is None or not contract_document.is_file():
            continue
        contract_errors, contract_warnings = run_document_validator(
            "validate_api_contract.py", contract_document, repo
        )
        errors.extend(contract_errors)
        warnings.extend(contract_warnings)

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
        template_name = ROOT_TEMPLATE_BY_DOCUMENT.get(relative)
        if template_name:
            template_path = Path(__file__).resolve().parent.parent / "assets" / template_name
            template_text = template_path.read_text(encoding="utf-8")
            template_parsed = split_frontmatter(template_text)
            template_body = template_parsed[1] if template_parsed else template_text
            template_blocks = {
                normalized_material_block(block)
                for _line, _kind, block in material_blocks(template_body)
                if normalized_material_block(block) and "SCAFFOLD_ONLY" not in block
            }
            generated_parsed = split_frontmatter(text)
            generated_body = generated_parsed[1] if generated_parsed else text
            for line, kind, block in material_blocks(generated_body):
                normalized = normalized_material_block(block)
                if normalized and normalized in template_blocks:
                    errors.append(
                        f"template-derived {kind} remains unchanged in {relative}:{line}: {normalized[:120]}"
                    )
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
                with source.open(encoding="utf-8", errors="replace") as handle:
                    line_count = sum(1 for _ in handle)
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
    print(
        f"OK: repository knowledge pack provenance, claim coverage, and structure are valid "
        f"({counts}); {len(set(warnings))} warning(s). Semantic entailment still depends on the independent claim audit and final rendered-document review."
    )
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
