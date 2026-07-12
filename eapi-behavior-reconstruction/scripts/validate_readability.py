#!/usr/bin/env python3
"""Emit non-blocking readability diagnostics for v2 Narrative documents."""

from __future__ import annotations

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from runtime_guard import run_guarded
from validate_claim_ledger import (
    CLAIM_MARKER_RE,
    document_profile,
    find_pack_root,
    list_values,
    pack_format_version,
    split_frontmatter,
    validate_claim_artifacts,
)


FENCE_RE = re.compile(r"```.*?```", re.S)
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+|(?<=[。！？])")
TECH_JARGON_RE = re.compile(
    r"\b(?:controller|handler|dto|lambda|dynamodb|eventbridge|class|method|"
    r"repository|status\s*code|stack\s*trace)\b|控制器|处理器|数据传输对象|状态码",
    re.I,
)


def normalize(value: str) -> str:
    value = CLAIM_MARKER_RE.sub(" ", value)
    value = LINK_RE.sub(r"\1", value)
    value = re.sub(r"[`*_>#|]", " ", value)
    value = re.sub(r"[^\w\u3400-\u9fff]+", " ", value.lower(), flags=re.UNICODE)
    return " ".join(value.split())


def prose_paragraphs(body: str) -> list[str]:
    body = FENCE_RE.sub("\n", body)
    paragraphs: list[str] = []
    for raw in re.split(r"\n\s*\n", body):
        value = raw.strip()
        if not value or value.startswith(("#", "|", "<!--")):
            continue
        if all(line.lstrip().startswith(("- ", "* ", "+ ")) for line in value.splitlines()):
            continue
        paragraphs.append(" ".join(line.strip() for line in value.splitlines()))
    return paragraphs


def readability_diagnostics(
    document: Path,
    claims: dict[str, dict[str, object]],
) -> list[str]:
    frontmatter, body = split_frontmatter(document.read_text(encoding="utf-8"))
    declared = list_values(frontmatter, "claim_ids")
    claim_statements = [
        normalize(str(claims[claim_id].get("statement", "")))
        for claim_id in declared
        if claim_id in claims
    ]
    paragraphs = prose_paragraphs(body)
    sentences = [
        sentence.strip()
        for paragraph in paragraphs
        for sentence in SENTENCE_RE.split(paragraph)
        if normalize(sentence)
    ]
    warnings: list[str] = []

    near_claim = 0
    for sentence in sentences:
        normalized = normalize(sentence)
        if len(normalized) < 20:
            continue
        if any(SequenceMatcher(None, normalized, claim).ratio() >= 0.90 for claim in claim_statements):
            near_claim += 1
    if near_claim >= 2:
        warnings.append(
            f"Narrative contains {near_claim} sentence(s) very close to Claim statements; "
            "review for Claim-dump prose"
        )

    one_sentence_streak = 0
    longest_streak = 0
    for paragraph in paragraphs:
        count = len([item for item in SENTENCE_RE.split(paragraph) if normalize(item)])
        if count <= 1:
            one_sentence_streak += 1
            longest_streak = max(longest_streak, one_sentence_streak)
        else:
            one_sentence_streak = 0
    if longest_streak >= 3:
        warnings.append(
            f"Narrative has {longest_streak} consecutive one-sentence paragraphs; "
            "review whether related facts should be synthesized"
        )

    nonempty_lines = [line for line in body.splitlines() if line.strip()]
    table_lines = [line for line in nonempty_lines if line.lstrip().startswith("|")]
    if nonempty_lines and len(table_lines) / len(nonempty_lines) > 0.50 and len(paragraphs) < 2:
        warnings.append("Narrative is dominated by tables and has little explanatory prose")

    relative = document.as_posix()
    if "/ba-pack/" in relative or relative.endswith("/ba-pack"):
        jargon = sorted({match.group(0) for match in TECH_JARGON_RE.finditer(body)}, key=str.lower)
        if jargon:
            warnings.append("BA Narrative contains developer terminology: " + ", ".join(jargon))
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()

    document = args.document.expanduser().resolve()
    repo = args.repo.expanduser().resolve()
    if not document.is_file():
        print(f"ERROR: document does not exist: {document}")
        return 2
    pack = find_pack_root(document)
    if pack is None:
        print("ERROR: document is not inside a knowledge pack")
        return 2
    if pack_format_version(pack) < 2 or document_profile(document, pack) != "narrative":
        print("OK: readability diagnostics are not applicable to this legacy/reference document")
        return 0

    try:
        frontmatter, _body = split_frontmatter(document.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot read Narrative document: {exc}")
        return 1
    repository = re.search(r'^repository:\s*["\']?([^"\'\n]+)', frontmatter, re.M)
    source_commit = re.search(r'^source_commit:\s*["\']?([^"\'\n]+)', frontmatter, re.M)
    errors, artifact_warnings, claims = validate_claim_artifacts(
        pack / ".work" / "claim-ledger.json",
        pack / ".work" / "claim-audit.json",
        repo,
        repository.group(1).strip() if repository else None,
        source_commit.group(1).strip() if source_commit else None,
    )
    for warning in artifact_warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} Claim artifact error(s)")
        return 1
    diagnostics = readability_diagnostics(document, claims)
    for diagnostic in diagnostics:
        print(f"WARNING: {diagnostic}")
    print(f"OK: readability review completed with {len(diagnostics)} diagnostic(s)")
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
