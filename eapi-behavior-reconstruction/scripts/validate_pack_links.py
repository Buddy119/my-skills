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

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {checked_links} local link(s) checked")
        return 1
    print(f"OK: {len(markdown_files)} Markdown file(s), {checked_links} local link(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
