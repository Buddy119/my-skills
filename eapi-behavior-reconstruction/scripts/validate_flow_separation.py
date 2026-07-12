#!/usr/bin/env python3
"""Validate independent Tech/BA flow models and semantic perspective separation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from runtime_guard import run_guarded
from validate_claim_ledger import find_pack_root, pack_format_version


ALLOWED_STATUSES = {"Confirmed", "Inferred", "Conflicting", "Unknown"}
TECH_TYPES = {
    "trigger-adapter", "input-parse", "validation", "authorization", "orchestration",
    "data-read", "data-write", "state-change", "dependency-call", "event-publish",
    "response-map", "failure", "retry", "compensation", "technical-outcome", "other-technical",
}
BA_TYPES = {
    "actor-event", "business-precondition", "business-decision", "business-action",
    "business-state-change", "business-outcome", "business-exception", "recovery",
    "external-participant", "unknown",
}
MODEL_EVIDENCE_RE = re.compile(
    r"^(?P<path>[^:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?$"
)
CLAIM_ID_RE = re.compile(r"^CLM-[A-Za-z0-9][A-Za-z0-9._-]*$")
RAW_CITATION_RE = re.compile(
    r"(?P<path>[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>\d+)(?:-(?P<end>\d+))?"
)
NODE_RE = re.compile(
    r"\b(?P<id>[A-Za-z][A-Za-z0-9_-]*)\s*(?:"
    r"\[(?P<square>[^\]\n]+)\]|"
    r"\{(?P<brace>[^}\n]+)\}|"
    r"\((?P<paren>[^)\n]+)\))"
)
EDGE_RE = re.compile(
    r"\b(?P<from>[A-Za-z][A-Za-z0-9_-]*)"
    r"(?:\s*(?:\[[^\]\n]*\]|\{[^}\n]*\}|\([^\)\n]*\)))?\s*"
    r"(?:(?P<simple>-->|==>|-\.->)|"
    r"--\s*\"(?P<quoted>[^\"\n]*)\"\s*-->|"
    r"-\.\s*\"(?P<dashed>[^\"\n]*)\"\s*\.->)"
    r"\s*(?:\|(?P<pipe>[^|\n]*)\|\s*)?"
    r"(?P<to>[A-Za-z][A-Za-z0-9_-]*)"
)
TECH_SIGNAL_RE = re.compile(
    r"\b(?:parse|deserialize|validate|handler|controller|repository|database|read|write|persist|"
    r"client|http|publish|return|response|status|exception|retry|queue|topic|mapper|transform|"
    r"lambda|dynamodb|sqs|sns|eventbridge|adapter|serialize)\b|"
    r"解析|反序列化|校验|处理器|控制器|仓储|数据库|读取|写入|持久化|调用|发布|返回|重试|队列|映射|转换",
    re.I,
)
BA_FORBIDDEN_RE = re.compile(
    r"\b(?:controller|handler|dto|lambda|dynamodb|sqs|sns|eventbridge|api\s*gateway|class|method|"
    r"parse|serialize|deserialize|mapper|repository|database|table|sql|http|status\s*code|"
    r"[45]\d\d|retry|dlq|queue|topic|json|stack\s*trace)\b|"
    r"控制器|处理器|数据传输对象|数据库表|序列化|反序列化|重试队列|死信队列|状态码",
    re.I,
)
BA_CATEGORY_PATTERNS = (
    re.compile(r"\b(?:customer|user|participant|actor|channel|request|business\s*event|party)\b|客户|用户|参与者|角色|渠道|请求|业务事件", re.I),
    re.compile(r"\b(?:rule|condition|required|eligible|allowed|valid|approval|decision|precondition)\b|规则|条件|必须|资格|允许|审批|决策|前置条件", re.I),
    re.compile(r"\b(?:outcome|result|accept|reject|complete|update|notify|available|unavailable|recovery|exception)\w*\b|结果|完成|接受|拒绝|更新|通知|可用|不可用|恢复|业务异常", re.I),
)


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("document must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("YAML frontmatter is not closed with ---")
    return text[4:end], text[end + 5 :]


def scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.M)
    return match.group(1).strip() if match else None


def section_value(body: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<content>.*?)(?=^##\s+|\Z)",
        body,
        re.M | re.S,
    )
    return match.group("content").strip() if match else ""


def first_narrative_section(body: str) -> str:
    """Return the first H2 section containing prose outside a code fence."""

    for match in re.finditer(r"^##\s+.+?\s*$\n(?P<content>.*?)(?=^##\s+|\Z)", body, re.M | re.S):
        content = match.group("content").strip()
        candidate_lines = []
        for line in re.sub(r"```.*?```", "", content, flags=re.S).splitlines():
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith(("|", "<!--"))
                or re.match(r"^(?:[-+*]|\d+\.)\s+", stripped)
            ):
                continue
            candidate_lines.append(stripped)
        prose = " ".join(candidate_lines)
        prose = re.sub(r"\[[^\]]+\]\([^)]+\)", "", prose)
        prose = re.sub(r"[`*_>#|\s-]+", "", prose)
        if prose:
            return content
    return ""


def long_narrative_paragraphs(body: str) -> set[str]:
    """Return exact long prose blocks; short shared phrases remain legitimate."""

    body = re.sub(r"```.*?```", " ", body, flags=re.S)
    paragraphs: set[str] = set()
    for raw in re.split(r"\n\s*\n", body):
        lines = [
            line.strip()
            for line in raw.splitlines()
            if line.strip()
            and not line.lstrip().startswith(("#", "|", "<!--", "- ", "* ", "+ "))
        ]
        value = " ".join(lines)
        value = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", value)
        normalized = normalize_text(value)
        if len(normalized) >= 100:
            paragraphs.add(normalized)
    return paragraphs


def extract_mermaid(body: str) -> str:
    match = re.search(r"```mermaid\s*\n(?P<code>\s*(?:flowchart|graph)\b.*?)```", body, re.I | re.S)
    return match.group("code").strip() if match else ""


def extract_node_labels(code: str) -> list[str]:
    labels_by_id: dict[str, str] = {}
    for match in NODE_RE.finditer(code):
        label = next(
            value for value in (match.group("square"), match.group("brace"), match.group("paren")) if value is not None
        )
        label = label.strip().strip("\"'").strip("[](){}")
        labels_by_id.setdefault(match.group("id"), label)
    return list(labels_by_id.values())


def normalize_text(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.S)
    value = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", value)
    value = re.sub(r"[`*_>#|]", " ", value)
    value = re.sub(r"\b(?:Confirmed|Inferred|Conflicting|Unknown)\b", " ", value, flags=re.I)
    value = re.sub(r"(?:已确认|推断|冲突|未知)", " ", value)
    value = re.sub(r"[^\w\u3400-\u9fff]+", " ", value.lower(), flags=re.UNICODE)
    return " ".join(value.split())


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def token_jaccard(left: str, right: str) -> float:
    left_tokens = set(normalize_text(left).split())
    right_tokens = set(normalize_text(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def edge_count(code: str) -> int:
    return len(extract_mermaid_edges(code))


def normalize_condition(value: object) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().lower().split())
    return normalized or None


def extract_mermaid_edges(code: str) -> list[tuple[str, str, str | None]]:
    edges: list[tuple[str, str, str | None]] = []
    for match in EDGE_RE.finditer(code):
        condition = match.group("pipe") or match.group("quoted") or match.group("dashed")
        edges.append((match.group("from"), match.group("to"), normalize_condition(condition)))
    return edges


def _flow_pack_root(document: Path) -> Path | None:
    """Locate legacy or v2 packs; legacy flow tests may have no manifest."""

    canonical = find_pack_root(document)
    if canonical is not None:
        return canonical
    return next(
        (
            candidate
            for candidate in (document.parent, *document.parents)
            if (candidate / ".work" / "flow-models").is_dir()
        ),
        None,
    )


def _validate_model(
    document: Path,
    frontmatter: str,
    body: str,
    model_key: str,
    expected_perspective: str,
    summary_heading: str,
    repo: Path | None,
) -> tuple[list[str], list[str], dict[str, object] | None, Path | None, list[str], str, str]:
    errors: list[str] = []
    warnings: list[str] = []
    if repo is not None:
        # Normalize macOS /var -> /private/var and other symlinked roots before
        # containment checks so valid evidence is not reported as escaping.
        repo = repo.expanduser().resolve()
    pack_root = _flow_pack_root(document)
    version = pack_format_version(pack_root) if pack_root is not None else 1
    behavior_id = scalar_value(frontmatter, "behavior_id")
    repository = scalar_value(frontmatter, "repository")
    source_commit = scalar_value(frontmatter, "source_commit")
    perspective = scalar_value(frontmatter, "flow_perspective")
    summary_perspective = scalar_value(frontmatter, "summary_perspective")
    if perspective != expected_perspective:
        errors.append(f"flow_perspective must be {expected_perspective}")
    if summary_perspective != expected_perspective:
        errors.append(f"summary_perspective must be {expected_perspective}")

    mermaid = extract_mermaid(body)
    labels = extract_node_labels(mermaid)
    if not mermaid:
        errors.append("document does not contain a Mermaid flowchart")
    if not labels:
        errors.append("Mermaid flow must contain at least one labeled node")
    elif expected_perspective == "technical" and len(labels) < 2:
        errors.append("Mermaid flow must contain at least two labeled nodes")

    if version >= 2:
        summary_heading = "At a glance" if expected_perspective == "technical" else "Scenario at a glance"
    summary = section_value(body, summary_heading)
    if version >= 2 and not summary:
        summary = first_narrative_section(body)
        if summary:
            warnings.append(
                f"preferred {summary_heading} heading is absent; using the first Narrative section"
            )
    if not summary:
        errors.append(f"{summary_heading} section is empty")

    model_value = scalar_value(frontmatter, model_key)
    model_path: Path | None = None
    model: dict[str, object] | None = None
    if not model_value or model_value.lower() in {"null", "none"}:
        errors.append(f"{model_key} must point to the separate {expected_perspective} model")
    else:
        model_path = (document.parent / model_value).resolve()
        pack_root = _flow_pack_root(document)
        if pack_root is None:
            errors.append("cannot locate canonical .work/flow-models directory for document")
        else:
            canonical_dir = (pack_root / ".work" / "flow-models").resolve()
            try:
                relative_model = model_path.relative_to(canonical_dir)
            except ValueError:
                errors.append(f"{model_key} must stay inside the canonical .work/flow-models directory")
            else:
                expected_suffix = "tech-flow.json" if expected_perspective == "technical" else "ba-flow.json"
                expected_name = f"{behavior_id}.{expected_suffix}" if behavior_id else None
                if len(relative_model.parts) != 1 or relative_model.name != expected_name:
                    errors.append(f"{model_key} must resolve to .work/flow-models/{expected_name}")
        if not model_path.is_file():
            errors.append(f"linked flow model does not exist: {model_value}")
        else:
            try:
                loaded = json.loads(model_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"flow model is not valid JSON: {exc}")
            else:
                if not isinstance(loaded, dict):
                    errors.append("flow model root must be an object")
                else:
                    model = loaded

    if model is not None:
        if "scaffold_state" in model:
            errors.append("flow model still contains scaffold_state")
        caption_key = "diagram_caption" if version >= 2 else "summary"
        caption_claim_key = "diagram_claim_ids" if version >= 2 else "summary_claim_ids"
        required = {
            "behavior_id", "repository", "source_commit", "perspective", caption_key,
            caption_claim_key, "nodes", "edges",
        }
        missing = sorted(required - set(model))
        if missing:
            errors.append("flow model missing key(s): " + ", ".join(missing))
        for key, expected in (
            ("behavior_id", behavior_id),
            ("repository", repository),
            ("source_commit", source_commit),
            ("perspective", expected_perspective),
        ):
            if model.get(key) != expected:
                errors.append(f"flow model {key} does not match document")

        model_summary = model.get(caption_key)
        if not isinstance(model_summary, str) or not model_summary.strip():
            errors.append(f"flow model {caption_key} must be a nonempty string")
        elif version < 2 and normalize_text(model_summary) != normalize_text(summary):
            errors.append(f"{summary_heading} must render the summary from {model_key}")
        summary_claim_ids = model.get(caption_claim_key)
        if (
            not isinstance(summary_claim_ids, list)
            or not summary_claim_ids
            or any(not isinstance(item, str) or not CLAIM_ID_RE.fullmatch(item) for item in summary_claim_ids)
        ):
            errors.append(f"flow model {caption_claim_key} must contain valid CLM- IDs")

        nodes = model.get("nodes")
        edges = model.get("edges")
        minimum_nodes = 2 if expected_perspective == "technical" else 1
        if not isinstance(nodes, list) or len(nodes) < minimum_nodes:
            errors.append(f"flow model nodes must contain at least {minimum_nodes} node(s)")
            nodes = []
        if not isinstance(edges, list):
            errors.append("flow model edges must be a list")
            edges = []

        node_ids: set[str] = set()
        model_labels: list[str] = []
        allowed_types = TECH_TYPES if expected_perspective == "technical" else BA_TYPES
        prefix = "T" if expected_perspective == "technical" else "B"
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"flow model node {index + 1} must be an object")
                continue
            node_id = node.get("node_id")
            semantic_type = node.get("semantic_type")
            label = node.get("label")
            claim_ids = node.get("claim_ids")
            if not isinstance(node_id, str) or not re.fullmatch(rf"{prefix}[A-Za-z0-9_-]+", node_id):
                errors.append(f"{expected_perspective} node IDs must use the {prefix} namespace")
            elif node_id in node_ids:
                errors.append(f"duplicate flow-model node ID: {node_id}")
            else:
                node_ids.add(node_id)
            if semantic_type not in allowed_types:
                errors.append(f"invalid {expected_perspective} semantic_type: {semantic_type}")
            if not isinstance(label, str) or not label.strip():
                errors.append(f"flow model node {node_id or index + 1} label must be nonempty")
            else:
                model_labels.append(label)
            if (
                not isinstance(claim_ids, list)
                or not claim_ids
                or any(not isinstance(item, str) or not CLAIM_ID_RE.fullmatch(item) for item in claim_ids)
            ):
                errors.append(f"flow model node {node_id or index + 1} must contain valid claim_ids")
            if expected_perspective == "technical":
                evidence = node.get("evidence")
                if not isinstance(evidence, list) or not evidence:
                    errors.append(f"technical node {node_id or index + 1} must contain evidence")
                else:
                    for reference in evidence:
                        match = MODEL_EVIDENCE_RE.fullmatch(reference) if isinstance(reference, str) else None
                        if not match:
                            errors.append(f"invalid technical node evidence: {reference}")
                            continue
                        if repo is not None:
                            source = (repo / match.group("path")).resolve()
                            try:
                                source.relative_to(repo)
                            except ValueError:
                                errors.append(f"technical model evidence escapes repository: {reference}")
                                continue
                            if not source.is_file():
                                errors.append(f"technical model evidence file does not exist: {reference}")
                                continue
                            with source.open(encoding="utf-8", errors="replace") as handle:
                                line_count = sum(1 for _ in handle)
                            start = int(match.group("start"))
                            end = int(match.group("end") or start)
                            if start < 1 or end < start or end > line_count:
                                errors.append(f"technical model evidence outside file bounds: {reference}")
            else:
                if node.get("status") not in ALLOWED_STATUSES:
                    errors.append(f"business node {node_id or index + 1} must have a valid status")
                if "evidence" in node:
                    errors.append(f"business node {node_id or index + 1} must not contain source evidence")

        normalized_model = [normalize_text(label) for label in model_labels]
        normalized_document = [normalize_text(label) for label in labels]
        if normalized_model != normalized_document:
            errors.append(f"Mermaid node labels must render {model_key} nodes in model order")
        rendered_edges = extract_mermaid_edges(mermaid)
        if len(edges) != len(rendered_edges):
            errors.append(f"Mermaid edge count must match {model_key} edges")
        model_edges: list[tuple[str, str, str | None]] = []
        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(f"flow model edge {index + 1} must be an object")
                continue
            if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
                errors.append(f"flow model edge {index + 1} references an unknown node")
            if isinstance(edge.get("from"), str) and isinstance(edge.get("to"), str):
                model_edges.append(
                    (
                        str(edge["from"]),
                        str(edge["to"]),
                        normalize_condition(edge.get("condition")),
                    )
                )
            claim_ids = edge.get("claim_ids")
            if (
                not isinstance(claim_ids, list)
                or not claim_ids
                or any(not isinstance(item, str) or not CLAIM_ID_RE.fullmatch(item) for item in claim_ids)
            ):
                errors.append(f"flow model edge {index + 1} must contain valid claim_ids")
        if model_edges != rendered_edges:
            errors.append(
                f"Mermaid edge topology/conditions must exactly render {model_key}: "
                f"model={model_edges}, mermaid={rendered_edges}"
            )

        if expected_perspective == "business":
            model_text = json.dumps(model, ensure_ascii=False)
            if RAW_CITATION_RE.search(model_text):
                errors.append("business flow model must not contain raw source citations")

    return errors, warnings, model, model_path, labels, summary, mermaid


def validate_tech_document(document: Path, repo: Path | None = None) -> tuple[list[str], list[str]]:
    text = document.read_text(encoding="utf-8")
    try:
        frontmatter, body = split_frontmatter(text)
    except ValueError as exc:
        return [str(exc)], []
    errors, warnings, _model, _path, labels, summary, _mermaid = _validate_model(
        document, frontmatter, body, "tech_flow_model", "technical", "Summary", repo
    )
    if labels and not TECH_SIGNAL_RE.search(" ".join(labels) + " " + summary):
        errors.append("Tech flow and summary contain no implementation-execution semantics")
    return errors, warnings


def validate_pair(
    tech_document: Path,
    ba_document: Path,
    repo: Path | None = None,
) -> tuple[list[str], list[str], dict[str, float | int]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        tech_frontmatter, tech_body = split_frontmatter(tech_document.read_text(encoding="utf-8"))
        ba_frontmatter, ba_body = split_frontmatter(ba_document.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read linked Tech/BA pair: {exc}"], [], {}
    pack_root = _flow_pack_root(tech_document)
    version = pack_format_version(pack_root) if pack_root is not None else 1

    tech_result = _validate_model(
        tech_document, tech_frontmatter, tech_body, "tech_flow_model", "technical", "Summary", repo
    )
    ba_result = _validate_model(
        ba_document, ba_frontmatter, ba_body, "ba_flow_model", "business", "Business summary", None
    )
    tech_errors, tech_warnings, tech_model, tech_model_path, tech_labels, tech_summary, tech_mermaid = tech_result
    ba_errors, ba_warnings, ba_model, ba_model_path, ba_labels, ba_summary, ba_mermaid = ba_result
    errors.extend("Tech: " + error for error in tech_errors)
    errors.extend("BA: " + error for error in ba_errors)
    warnings.extend("Tech: " + warning for warning in tech_warnings)
    warnings.extend("BA: " + warning for warning in ba_warnings)

    for identity_key in ("behavior_id", "repository", "source_commit"):
        tech_identity = scalar_value(tech_frontmatter, identity_key)
        ba_identity = scalar_value(ba_frontmatter, identity_key)
        if tech_identity != ba_identity:
            errors.append(f"Tech and BA {identity_key} values do not match")

    if tech_model_path is not None and ba_model_path is not None and tech_model_path == ba_model_path:
        errors.append("Tech and BA must use different flow model files")
    if tech_model is not None and ba_model is not None:
        tech_caption = tech_model.get("diagram_caption", tech_model.get("summary", ""))
        ba_caption = ba_model.get("diagram_caption", ba_model.get("summary", ""))
        if normalize_text(str(tech_caption)) == normalize_text(str(ba_caption)):
            errors.append("Tech and BA model captions are identical")
        tech_model_labels = [normalize_text(str(node.get("label", ""))) for node in tech_model.get("nodes", []) if isinstance(node, dict)]
        ba_model_labels = [normalize_text(str(node.get("label", ""))) for node in ba_model.get("nodes", []) if isinstance(node, dict)]
        if tech_model_labels == ba_model_labels or set(tech_model_labels) == set(ba_model_labels):
            errors.append("Tech and BA flow models reuse the same normalized node labels")

    normalized_tech_labels = [normalize_text(label) for label in tech_labels]
    normalized_ba_labels = [normalize_text(label) for label in ba_labels]
    if tech_mermaid and ba_mermaid and normalize_text(tech_mermaid) == normalize_text(ba_mermaid):
        errors.append("Tech and BA Mermaid flows are identical")
    if normalized_tech_labels and (
        normalized_tech_labels == normalized_ba_labels
        or set(normalized_tech_labels) == set(normalized_ba_labels)
    ):
        errors.append("Tech and BA Mermaid flows use the same normalized node labels")

    joined_tech = " ".join(tech_labels)
    joined_ba = " ".join(ba_labels)
    node_similarity = similarity(joined_tech, joined_ba)
    node_jaccard = token_jaccard(joined_tech, joined_ba)
    summary_similarity = similarity(tech_summary, ba_summary)
    if normalize_text(tech_summary) and normalize_text(tech_summary) == normalize_text(ba_summary):
        errors.append("Tech and BA document summaries are directly reused")
    if version >= 2:
        # Similarity is an editorial signal in v2. Direct reuse remains an
        # error; near similarity stays a Reader Review prompt.
        if len(tech_labels) == len(ba_labels) and node_similarity >= 0.72:
            warnings.append(f"Tech/BA flow node wording is near-identical ({node_similarity:.2f}); review for mechanical rewriting")
        elif node_similarity >= 0.60:
            warnings.append(f"Tech/BA flow node wording has high overlap ({node_similarity:.2f}); review for mechanical rewriting")
        if len(tech_labels) == len(ba_labels) and node_jaccard >= 0.65:
            warnings.append(f"Tech/BA flow token overlap is high ({node_jaccard:.2f}); review perspective separation")
        if summary_similarity >= 0.72:
            warnings.append(f"Tech and BA summaries are near-identical ({summary_similarity:.2f}); review perspective separation")
        elif summary_similarity >= 0.60:
            warnings.append(f"Tech and BA summaries have high overlap ({summary_similarity:.2f}); review perspective separation")
    else:
        if len(tech_labels) == len(ba_labels) and node_similarity >= 0.72:
            errors.append(f"Tech/BA flow node wording is near-identical ({node_similarity:.2f})")
        elif node_similarity >= 0.60:
            warnings.append(f"Tech/BA flow node wording has high overlap ({node_similarity:.2f}); review for mechanical rewriting")
        if len(tech_labels) == len(ba_labels) and node_jaccard >= 0.65:
            errors.append(f"Tech/BA flow token overlap is too high ({node_jaccard:.2f})")
        if summary_similarity >= 0.72:
            errors.append(f"Tech and BA summaries are near-identical ({summary_similarity:.2f})")
        elif summary_similarity >= 0.60:
            warnings.append(f"Tech and BA summaries have high overlap ({summary_similarity:.2f}); review perspective separation")

    if version >= 2 and long_narrative_paragraphs(tech_body) & long_narrative_paragraphs(ba_body):
        errors.append("Tech and BA directly reuse a long Narrative paragraph")

    ba_perspective_text = ba_summary + " " + joined_ba
    forbidden = sorted({match.group(0) for match in BA_FORBIDDEN_RE.finditer(ba_perspective_text)}, key=str.lower)
    if forbidden:
        message = "BA flow/summary contains implementation terminology: " + ", ".join(forbidden)
        (warnings if version >= 2 else errors).append(message)
    category_hits = sum(1 for pattern in BA_CATEGORY_PATTERNS if pattern.search(ba_perspective_text))
    if ba_model is not None and isinstance(ba_model.get("nodes"), list):
        ba_semantic_types = {
            node.get("semantic_type")
            for node in ba_model["nodes"]
            if isinstance(node, dict)
        }
        type_category_hits = sum(
            bool(ba_semantic_types & category)
            for category in (
                {"actor-event", "external-participant"},
                {"business-precondition", "business-decision"},
                {"business-outcome", "business-exception", "recovery"},
            )
        )
        category_hits = max(category_hits, type_category_hits)
    all_ba_unknown = False
    if ba_model is not None and isinstance(ba_model.get("nodes"), list) and ba_model["nodes"]:
        all_ba_unknown = all(
            isinstance(node, dict)
            and node.get("status") == "Unknown"
            and node.get("semantic_type") == "unknown"
            for node in ba_model["nodes"]
        )
    if ba_labels and category_hits < 2 and not all_ba_unknown:
        if version >= 2:
            warnings.append("BA flow/summary has fewer than two business semantic categories; review whether the evidence supports a richer business view")
        else:
            errors.append("BA flow/summary must contain at least two business semantic categories: actor/event, decision/rule, outcome/exception")

    tech_perspective_text = tech_summary + " " + joined_tech
    if tech_labels and not TECH_SIGNAL_RE.search(tech_perspective_text):
        errors.append("Tech flow/summary contains no implementation-execution semantics")
    if (
        len(ba_labels) >= len(tech_labels)
        and edge_count(ba_mermaid) == edge_count(tech_mermaid)
        and node_similarity >= 0.60
    ):
        warnings.append("BA preserves the full Tech node/edge shape with high overlap; review whether it is a mechanical rewrite")
    if len(ba_labels) > len(tech_labels) + 2:
        warnings.append("BA flow is substantially more detailed than Tech flow; review for implementation leakage")

    metrics: dict[str, float | int] = {
        "tech_nodes": len(tech_labels),
        "ba_nodes": len(ba_labels),
        "node_similarity": round(node_similarity, 3),
        "node_token_jaccard": round(node_jaccard, 3),
        "summary_similarity": round(summary_similarity, 3),
    }
    return errors, warnings, metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tech_document", type=Path)
    parser.add_argument("ba_document", type=Path)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve() if args.repo else None

    errors, warnings, metrics = validate_pair(
        args.tech_document.expanduser().resolve(),
        args.ba_document.expanduser().resolve(),
        repo,
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s); metrics={json.dumps(metrics, sort_keys=True)}")
        return 1
    print(f"OK: Tech/BA perspectives are separated; metrics={json.dumps(metrics, sort_keys=True)}, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(run_guarded(main))
