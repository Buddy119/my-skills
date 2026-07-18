"""Shared mechanical helpers for BA Journey and Scenario validation."""

from __future__ import annotations

import re
from pathlib import Path


ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
RAW_CITATION_RE = re.compile(
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
    match = re.search(
        rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$",
        frontmatter,
        re.M,
    )
    return match.group(1).strip() if match else None


def yaml_block(frontmatter: str, key: str) -> tuple[str, str]:
    match = re.search(
        rf"^{re.escape(key)}:[ \t]*(?P<inline>[^\n]*)\n"
        rf"(?P<body>(?:[ \t]+[^\n]*(?:\n|$))*)",
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
    documents = re.findall(
        r"^\s+document:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", block, re.M
    )
    return list(zip((item.strip() for item in identifiers), (item.strip() for item in documents)))


def linked_entry_counts(frontmatter: str, block_key: str, id_key: str) -> tuple[int, int]:
    _, block = yaml_block(frontmatter, block_key)
    identifiers = re.findall(rf"^\s*-\s+{re.escape(id_key)}:", block, re.M)
    documents = re.findall(r"^\s+document:", block, re.M)
    return len(identifiers), len(documents)


def semantic_id(identifier: str | None, kind: str) -> bool:
    if not identifier:
        return False
    return bool(
        re.fullmatch(
            rf"[a-z0-9][a-z0-9.-]*\.{re.escape(kind)}\.[a-z0-9][a-z0-9.-]*",
            identifier,
        )
    )


def markdown_link(body: str, target: str) -> bool:
    return bool(re.search(rf"\]\({re.escape(target)}\)", body))


def has_mermaid(body: str) -> bool:
    return bool(re.search(r"```mermaid\s*\n\s*(?:flowchart|graph)\b", body, re.I))


def headings(body: str) -> set[str]:
    return set(re.findall(r"^##\s+(.+?)\s*$", body, re.M))


def resolved(document: Path, target: str) -> Path:
    return (document.parent / target).resolve()


def duplicate_values(entries: list[tuple[str, str]]) -> tuple[set[str], set[str]]:
    identifiers = [item[0] for item in entries]
    documents = [item[1] for item in entries]
    return (
        {value for value in identifiers if identifiers.count(value) > 1},
        {value for value in documents if documents.count(value) > 1},
    )


def has_placeholders(text: str) -> bool:
    placeholders = (
        "TODO",
        "TEMPLATE:",
        "repository-name",
        "git-commit-or-unknown",
        "repository.journey.business-goal",
        "repository.scenario.context-outcome",
        "repository.behavior-name",
        "Business journey title",
        "Business scenario title",
    )
    return any(placeholder in text for placeholder in placeholders)
