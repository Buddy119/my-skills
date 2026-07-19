#!/usr/bin/env python3
"""Mechanical checks for execution-stage wording in reader-facing artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


RULES_SCHEMA_VERSION = "1"
DETAIL_LIMIT = 50
PER_RULE_LIMIT = 10


class PublicationMaturityError(ValueError):
    """Raised when the bundled publication-maturity contract is invalid."""


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]
    message: str | None = None


@dataclass(frozen=True)
class Rules:
    version: str
    blocking: tuple[Rule, ...]
    review: tuple[Rule, ...]


def default_rules_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "publication-maturity-rules.json"


def _compile_rules(items: Any, *, blocking: bool) -> tuple[Rule, ...]:
    if not isinstance(items, list) or not items:
        raise PublicationMaturityError("rule list must be a non-empty array")
    rules: list[Rule] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise PublicationMaturityError("each rule must be an object")
        rule_id = item.get("rule_id")
        pattern = item.get("pattern")
        message = item.get("message")
        if not isinstance(rule_id, str) or not rule_id:
            raise PublicationMaturityError("each rule requires a non-empty rule_id")
        if rule_id in seen:
            raise PublicationMaturityError(f"duplicate rule_id: {rule_id}")
        seen.add(rule_id)
        if not isinstance(pattern, str) or not pattern:
            raise PublicationMaturityError(f"rule {rule_id} requires a regex pattern")
        if blocking and (not isinstance(message, str) or not message):
            raise PublicationMaturityError(f"blocking rule {rule_id} requires a message")
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise PublicationMaturityError(f"invalid regex for {rule_id}: {exc}") from exc
        rules.append(Rule(rule_id, compiled, message if isinstance(message, str) else None))
    return tuple(rules)


def load_rules(path: Path | None = None) -> Rules:
    source = path or default_rules_path()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationMaturityError(f"cannot read publication maturity rules: {exc}") from exc
    if not isinstance(payload, dict):
        raise PublicationMaturityError("publication maturity rules must be an object")
    schema_version = payload.get("publication_maturity_rules_schema_version")
    if schema_version != RULES_SCHEMA_VERSION:
        raise PublicationMaturityError(
            f"unsupported publication maturity rules schema: {schema_version!r}"
        )
    validation_version = payload.get("publication_maturity_validation_version")
    if not isinstance(validation_version, str) or not validation_version:
        raise PublicationMaturityError(
            "publication maturity rules require a validation version"
        )
    return Rules(
        version=validation_version,
        blocking=_compile_rules(payload.get("blocking_rules"), blocking=True),
        review=_compile_rules(payload.get("review_terms"), blocking=False),
    )


def reader_artifacts(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for directory in (root / "tech-pack", root / "ba-pack"):
        if not directory.is_dir():
            continue
        for pattern in ("*.md", "*.yaml", "*.yml"):
            paths.update(path for path in directory.rglob(pattern) if path.is_file())
    return sorted(paths)


def _mask_inline_markdown(text: str) -> str:
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^\n)]*\)", r"\1", text)
    return re.sub(r"<[^>]*>", "", text)


def visible_lines(path: Path) -> Iterable[tuple[int, str, str]]:
    """Yield line number, searchable text, and compact original context."""

    is_markdown = path.suffix.lower() == ".md"
    in_fence = False
    fence_marker: str | None = None
    in_template_comment = False
    in_frontmatter = False
    for line_number, original in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        stripped = original.lstrip()
        if is_markdown:
            if line_number == 1 and original.strip() == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if original.strip() == "---":
                    in_frontmatter = False
                continue
            fence = re.match(r"^\s*(`{3,}|~{3,})", original)
            if fence:
                marker = fence.group(1)[0]
                if not in_fence:
                    in_fence = True
                    fence_marker = marker
                elif marker == fence_marker:
                    in_fence = False
                    fence_marker = None
                continue
            if in_fence:
                continue
            if in_template_comment:
                if "-->" in original:
                    in_template_comment = False
                continue
            if re.search(r"<!--\s*TEMPLATE:", original, re.IGNORECASE):
                if "-->" not in original:
                    in_template_comment = True
                continue
            if re.match(r"^\s*\[[^]]+\]:\s*\S+", original):
                continue
            searchable = _mask_inline_markdown(original)
        else:
            if re.match(r"^\s*#\s*TEMPLATE:", original, re.IGNORECASE):
                continue
            key_match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*", original)
            if key_match and key_match.group(1).lower() in {
                "document",
                "path",
                "source",
                "evidence",
                "repository",
                "source_commit",
                "entry_point",
                "endpoint_matrix",
                "behavior_document",
            }:
                searchable = key_match.group(1)
            else:
                searchable = original
        context = " ".join(stripped.split())
        if searchable.strip():
            yield line_number, searchable, context[:240]


def _compact(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    visible: list[dict[str, Any]] = []
    per_rule: dict[str, int] = {}
    for item in items:
        rule_id = str(item["rule_id"])
        if len(visible) >= DETAIL_LIMIT or per_rule.get(rule_id, 0) >= PER_RULE_LIMIT:
            continue
        visible.append(item)
        per_rule[rule_id] = per_rule.get(rule_id, 0) + 1
    return visible, max(0, len(items) - len(visible))


def validate_reader_artifacts(root: Path, rules: Rules | None = None) -> dict[str, Any]:
    rules = rules or load_rules()
    blocking: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    checked_files = 0
    for path in reader_artifacts(root):
        checked_files += 1
        relative = path.relative_to(root).as_posix()
        for line_number, searchable, context in visible_lines(path):
            line_has_blocker = False
            for rule in rules.blocking:
                if rule.pattern.search(searchable):
                    line_has_blocker = True
                    blocking.append(
                        {
                            "code": "DOC-PUBLICATION-RESIDUE",
                            "rule_id": rule.rule_id,
                            "path": relative,
                            "line": line_number,
                            "message": rule.message,
                            "context": context,
                        }
                    )
            if line_has_blocker:
                continue
            for rule in rules.review:
                if rule.pattern.search(searchable):
                    review.append(
                        {
                            "code": "DOC-PUBLICATION-TERM",
                            "rule_id": rule.rule_id,
                            "path": relative,
                            "line": line_number,
                            "message": "review whether this term describes a real domain state or stale publication lifecycle",
                            "context": context,
                        }
                    )
    visible_blocking, blocking_suppressed = _compact(blocking)
    visible_review, review_suppressed = _compact(review)
    return {
        "publication_maturity_validation_version": rules.version,
        "result": "invalid" if blocking else "valid",
        "checked_files": checked_files,
        "blocking_count": len(blocking),
        "review_count": len(review),
        "blocking_residues": visible_blocking,
        "blocking_suppressed_count": blocking_suppressed,
        "review_terms": visible_review,
        "review_suppressed_count": review_suppressed,
    }
