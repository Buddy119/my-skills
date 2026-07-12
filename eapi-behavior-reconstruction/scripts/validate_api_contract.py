#!/usr/bin/env python3
"""Validate a consumer-first API contract, its evidence appendix, and backlink."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from runtime_guard import run_guarded
from validate_claim_ledger import validate_single_document

REQUIRED_KEYS = {
    "endpoint_id",
    "primary_behavior_id",
    "title",
    "repository",
    "source_commit",
    "claim_ids",
    "entry_point",
    "operation_id",
    "method",
    "route",
    "contract_status",
    "contract_coverage",
    "behavior_document",
    "endpoint_matrix",
    "openapi_document",
}

REQUIRED_HEADINGS = {
    "Endpoint summary",
    "API input contract",
    "API output contract",
    "Contract semantics",
    "Open questions and conflicts",
    "Evidence appendix",
    "Evidence index",
}

REQUIRED_INPUT_SUBHEADINGS = {
    "Headers",
    "Path parameters",
    "Query parameters",
    "Request body schema",
    "Request-level rules",
}

REQUIRED_OUTPUT_SUBHEADINGS = {
    "Response outcomes",
    "Success response body schema",
    "Error response schema",
    "Error catalogue",
}

REQUIRED_EVIDENCE_SUBHEADINGS = {
    "Evidence coverage summary",
    "L1 — Executable evidence",
    "L2 — Schema-level evidence",
    "L3 — Shared or opaque evidence",
    "Evidence conflicts",
}

ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
ALLOWED_COVERAGE = {"complete", "partial", "blocked"}
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
    return {
        match.group(1)
        for line in frontmatter.splitlines()
        if line and not line[0].isspace()
        if (match := re.match(r"([A-Za-z_][A-Za-z0-9_-]*):", line))
    }


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


def section_value(body: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<content>.*?)(?=^##\s+|\Z)",
        body,
        re.M | re.S,
    )
    return match.group("content") if match else ""


def subheadings(section: str) -> set[str]:
    return set(re.findall(r"^###\s+(.+?)\s*$", section, re.M))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
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

    status = scalar_value(frontmatter, "contract_status")
    if status not in ALLOWED_STATUSES:
        errors.append("contract_status must be Confirmed, Inferred, Conflicting, or Unknown")

    coverage = scalar_value(frontmatter, "contract_coverage")
    if coverage not in ALLOWED_COVERAGE:
        errors.append("contract_coverage must be complete, partial, or blocked")

    endpoint_id = scalar_value(frontmatter, "endpoint_id")
    if not endpoint_id or not re.fullmatch(r"EP-[A-Za-z0-9][A-Za-z0-9._-]*", endpoint_id):
        errors.append("endpoint_id must use the EP- stable ID format")

    headings = set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))
    missing_headings = sorted(REQUIRED_HEADINGS - headings)
    if missing_headings:
        errors.append("missing sections: " + ", ".join(missing_headings))

    input_section = section_value(body, "API input contract")
    missing_input = sorted(REQUIRED_INPUT_SUBHEADINGS - subheadings(input_section))
    if missing_input:
        errors.append("API input contract is missing subsection(s): " + ", ".join(missing_input))

    output_section = section_value(body, "API output contract")
    missing_output = sorted(REQUIRED_OUTPUT_SUBHEADINGS - subheadings(output_section))
    if missing_output:
        errors.append("API output contract is missing subsection(s): " + ", ".join(missing_output))

    evidence_section = section_value(body, "Evidence appendix")
    missing_evidence = sorted(REQUIRED_EVIDENCE_SUBHEADINGS - subheadings(evidence_section))
    if missing_evidence:
        errors.append("Evidence appendix is missing subsection(s): " + ", ".join(missing_evidence))

    misplaced_layers = re.findall(r"^###\s+(L[123]\b.+?)\s*$", input_section + output_section, re.M)
    if misplaced_layers:
        errors.append("L1/L2/L3 sections belong in Evidence appendix, not API input/output contract")

    if "HTTP status" not in output_section:
        errors.append("API output contract must include response outcomes by HTTP status")

    consumer_contract = body.split("## Evidence appendix", 1)[0]
    if EVIDENCE_RE.search(consumer_contract):
        errors.append(
            "consumer-facing contract sections must use statuses; move raw source citations "
            "to Evidence appendix or Evidence index"
        )

    for index, json_text in enumerate(re.findall(r"```json\s*\n(.*?)```", body, re.S), start=1):
        try:
            json.loads(json_text)
        except json.JSONDecodeError as exc:
            errors.append(f"JSON example {index} is invalid: {exc.msg}")

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
                primary_behavior_id = scalar_value(frontmatter, "primary_behavior_id")
                if scalar_value(behavior_frontmatter, "behavior_id") != primary_behavior_id:
                    errors.append("primary_behavior_id does not match linked behavior document")
                for key in ("repository", "source_commit"):
                    if scalar_value(frontmatter, key) != scalar_value(behavior_frontmatter, key):
                        errors.append(f"API contract and behavior must have the same {key}")
                endpoint_id = scalar_value(frontmatter, "endpoint_id")
                if endpoint_id not in list_values(behavior_frontmatter, "endpoint_ids"):
                    errors.append("linked behavior endpoint_ids must contain this endpoint_id")
        if not re.search(rf"\]\({re.escape(behavior_document)}\)", body):
            errors.append("contract body must contain a Markdown link matching behavior_document")

    endpoint_matrix = scalar_value(frontmatter, "endpoint_matrix")
    if not endpoint_matrix or endpoint_matrix.lower() in {"null", "none"}:
        errors.append("endpoint_matrix must point to the endpoint matrix")
    else:
        matrix_path = (args.document.parent / endpoint_matrix).resolve()
        if not matrix_path.is_file():
            errors.append(f"linked endpoint matrix does not exist: {endpoint_matrix}")
        if not re.search(rf"\]\({re.escape(endpoint_matrix)}\)", body):
            errors.append("contract body must contain a Markdown link matching endpoint_matrix")

    citations = list(EVIDENCE_RE.finditer(body))
    if not citations:
        errors.append("no source citations found; use `relative/path.ext:line`")

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
            with source.open(encoding="utf-8", errors="replace") as handle:
                line_count = sum(1 for _ in handle)
        except OSError as exc:
            errors.append(f"cannot read cited file {relative}: {exc}")
            continue
        final_line = end or start
        if start < 1 or final_line > line_count:
            errors.append(
                f"citation outside file bounds: {relative}:{start}" + (f"-{end}" if end else "")
            )

    if any(item in text for item in ("TODO", "path/to/", "repository.behavior-name")):
        errors.append("template placeholders remain in the document")

    claim_errors, claim_warnings = validate_single_document(args.document.resolve(), args.repo.resolve())
    errors.extend("claim provenance: " + error for error in claim_errors)
    warnings.extend("claim provenance: " + warning for warning in claim_warnings)

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
