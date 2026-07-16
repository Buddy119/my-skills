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
PLACEHOLDERS = ("TODO", "path/to/", "repository.behavior-name", "repository.method-route")
ENDPOINT_STATUSES = {"Confirmed", "Conflicting", "Unknown", "Not observed"}
ENDPOINT_HEADERS = [
    "Endpoint or Exposure ID",
    "Application Route",
    "External Entry Declaration",
    "Environment Deployment Intent",
    "Observed Runtime Deployment",
    "External Reachability",
    "Behavior",
    "Contract",
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
    rows = [table_cells(line) for line in summary.splitlines() if line.strip().startswith("|")]
    if not rows:
        errors.append("Endpoint Matrix is missing the Endpoint summary table")
        return
    if rows[0] != ENDPOINT_HEADERS:
        errors.append("Endpoint Matrix summary columns do not match the layered endpoint model")
        return

    data_rows = [row for row in rows[1:] if not is_separator_row(row)]
    if not data_rows:
        errors.append("Endpoint Matrix has no endpoint or exposure rows")
        return

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

        statuses = [endpoint_status(cell) for cell in row[1:6]]
        if any(status is None for status in statuses):
            errors.append(f"Endpoint Matrix {identifier} has an invalid or ambiguous layer status")
            continue
        if statuses[0] == "Confirmed":
            if not re.search(r"\[[^\]]+\]\([^)]+\)", row[6]):
                errors.append(f"confirmed application endpoint lacks a Behavior link: {identifier}")
            if not re.search(r"\[[^\]]+\]\([^)]+\.api-contract\.md\)", row[7]):
                errors.append(f"confirmed application endpoint lacks an API Contract link: {identifier}")

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

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {checked_links} local link(s) checked")
        return 1
    print(f"OK: {len(markdown_files)} Markdown file(s), {checked_links} local link(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
