#!/usr/bin/env python3
"""Validate the minimum structure and source evidence of a behavior document."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from runtime_guard import run_guarded
from validate_claim_ledger import validate_single_document
from validate_flow_separation import validate_tech_document


REQUIRED_KEYS = {
    "behavior_id",
    "title",
    "repository",
    "source_commit",
    "claim_ids",
    "entry_type",
    "entry_point",
    "behavior_category",
    "overall_status",
    "flow_perspective",
    "summary_perspective",
    "tech_flow_model",
    "ba_behavior_document",
    "endpoint_ids",
    "api_contract_documents",
    "data_asset_ids",
    "field_ids",
    "dependency_ids",
    "config_ids",
    "validation_rule_ids",
    "failure_ids",
    "external_http_call_ids",
    "external_mapping_ids",
    "consumes",
    "produces",
    "reads",
    "writes",
    "analysis_limitations",
}

REQUIRED_HEADINGS = {
    "Summary",
    "Trigger and entry point",
    "Behavior flow",
    "Inputs",
    "Related repository knowledge",
    "Preconditions and business rules",
    "Happy path",
    "Data access and state changes",
    "Outputs and side effects",
    "Failures, retries, and partial success",
    "External dependency stubs",
    "Open questions and conflicts",
    "Evidence index",
}

ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
ALLOWED_CATEGORIES = {"business", "integration", "technical"}
ALLOWED_ENTRY_TYPES = {"api", "sqs", "sns", "eventbridge", "schedule", "stream", "step-function", "other"}
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


def list_values(frontmatter: str, key: str) -> list[str]:
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        match = re.match(rf"^{re.escape(key)}:\s*(.*?)\s*$", line)
        if not match:
            continue
        inline = match.group(1)
        if inline == "[]" or inline.lower() in {"null", "none"}:
            return []
        if inline.startswith("[") and inline.endswith("]"):
            return [item.strip().strip("\"'") for item in inline[1:-1].split(",") if item.strip()]
        values: list[str] = []
        for nested in lines[index + 1 :]:
            if nested and not nested[0].isspace():
                break
            item = re.match(r"^\s+-\s*[\"']?([^\"'\n]+?)[\"']?\s*$", nested)
            if item:
                values.append(item.group(1).strip())
        return values
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--allow-missing-ba",
        action="store_true",
        help="pre-BA validation only: allow the declared BA target file to be created later",
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

    flow_errors, flow_warnings = validate_tech_document(args.document.resolve(), args.repo.resolve())
    errors.extend(flow_errors)
    warnings.extend(flow_warnings)
    claim_errors, claim_warnings = validate_single_document(args.document.resolve(), args.repo.resolve())
    errors.extend("claim provenance: " + error for error in claim_errors)
    warnings.extend("claim provenance: " + warning for warning in claim_warnings)

    entry_type = scalar_value(frontmatter, "entry_type")
    if entry_type not in ALLOWED_ENTRY_TYPES:
        errors.append("entry_type must be api, sqs, sns, eventbridge, schedule, stream, step-function, or other")
    endpoint_ids = list_values(frontmatter, "endpoint_ids")
    api_contract_documents = list_values(frontmatter, "api_contract_documents")
    has_endpoint_links = bool(endpoint_ids or api_contract_documents)
    if entry_type == "api" and not endpoint_ids:
        errors.append("API behavior must list at least one endpoint_id")
    if entry_type == "api" and not api_contract_documents:
        errors.append("API behavior must list at least one api_contract_documents entry")
    if bool(endpoint_ids) != bool(api_contract_documents):
        errors.append("endpoint_ids and api_contract_documents must either both be populated or both be empty")
    if has_endpoint_links:
        if "API contracts" not in headings:
            errors.append("behavior with endpoint links is missing the API contracts section")
        for endpoint_id in endpoint_ids:
            if not re.fullmatch(r"EP-[A-Za-z0-9][A-Za-z0-9._-]*", endpoint_id):
                errors.append(f"invalid endpoint ID: {endpoint_id}")
            if not re.search(rf"\b{re.escape(endpoint_id)}\b", body):
                errors.append(f"API behavior body must reference endpoint ID: {endpoint_id}")
        for contract_document in api_contract_documents:
            contract_path = (args.document.parent / contract_document).resolve()
            if not contract_path.is_file():
                errors.append(f"linked API contract does not exist: {contract_document}")
            if not re.search(rf"\]\({re.escape(contract_document)}\)", body):
                errors.append(f"API behavior body must link contract: {contract_document}")
    elif "API contracts" in headings:
        errors.append("behavior without endpoint links must omit the API contracts section")

    ba_behavior_document = scalar_value(frontmatter, "ba_behavior_document")
    if behavior_category in {"business", "integration"}:
        if "BA view" not in headings:
            errors.append("business or integration behavior is missing the BA view link section")
        if not ba_behavior_document or ba_behavior_document.lower() in {"null", "none"}:
            errors.append("business or integration behavior must set ba_behavior_document")
        else:
            ba_path = (args.document.parent / ba_behavior_document).resolve()
            if not ba_path.is_file() and not args.allow_missing_ba:
                errors.append(f"linked BA behavior does not exist: {ba_behavior_document}")
            if not re.search(rf"\]\({re.escape(ba_behavior_document)}\)", body):
                errors.append("Tech behavior body must contain a Markdown link matching ba_behavior_document")
    elif behavior_category == "technical":
        if ba_behavior_document and ba_behavior_document.lower() not in {"null", "none"}:
            errors.append("technical behavior must set ba_behavior_document to null")
        if "BA view" in headings:
            errors.append("technical behavior must omit the BA view section")

    external_mapping_ids = list_values(frontmatter, "external_mapping_ids")
    external_http_call_ids = list_values(frontmatter, "external_http_call_ids")
    if external_mapping_ids:
        if not external_http_call_ids:
            errors.append("external_mapping_ids require a proven external_http_call_id")
        if "External HTTP field mappings" not in headings:
            errors.append("external_mapping_ids exist but External HTTP field mappings section is missing")
        for mapping_id in external_mapping_ids:
            if mapping_id not in body:
                errors.append(f"behavior body must reference external mapping ID: {mapping_id}")
    for call_id in external_http_call_ids:
        if not re.fullmatch(r"HTTP-[A-Za-z0-9][A-Za-z0-9._-]*", call_id):
            errors.append(f"invalid outbound HTTP call ID: {call_id}")
    for mapping_id in external_mapping_ids:
        if not re.fullmatch(r"MAP-[A-Za-z0-9][A-Za-z0-9._-]*", mapping_id):
            errors.append(f"invalid external mapping ID: {mapping_id}")

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
            with source.open(encoding="utf-8", errors="replace") as handle:
                line_count = sum(1 for _ in handle)
        except OSError as exc:
            errors.append(f"cannot read cited file {rel}: {exc}")
            continue
        final_line = end or start
        if start < 1 or final_line > line_count:
            errors.append(f"citation outside file bounds: {rel}:{start}" + (f"-{end}" if end else ""))

    if "Unknown" not in body and "Conflicting" not in body:
        warnings.append("document contains no Unknown or Conflicting review items")
    placeholders = ("TODO", "path/to/", "repository.behavior-name", "FAIL- ID", "DATA- ID")
    if any(placeholder in text for placeholder in placeholders):
        errors.append("template placeholders remain in the document")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {len(citations)} citation occurrence(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
