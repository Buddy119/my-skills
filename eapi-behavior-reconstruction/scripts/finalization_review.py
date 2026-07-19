#!/usr/bin/env python3
"""Structural lifecycle support for Finalization review records.

This module validates review bookkeeping, references, hashes, and coverage.  It
does not decide whether a fact is true, a sample is representative, or prose is
useful.  Those judgments remain with the reviewing AI.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "finalization-review-schema.json"
)
FINALIZATION_REVIEW_VALIDATION_VERSION = "2"
REVIEW_TYPES = ("mechanical", "semantic-fact", "reader")
REVIEW_LEDGER_NAME = "finalization-review.json"
REVIEW_BASELINE_NAME = "finalization-review-baseline.json"
CONTENT_EXCLUDES = {
    ".work/analysis-state.yaml",
    ".work/artifact-manifest.json",
    ".work/migration-plan.yaml",
}
CONTENT_EXCLUDE_PREFIXES = (
    ".work/legacy-artifacts/",
    ".work/legacy-ba-pack/",
)
PORTABLE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class FinalizationReviewError(RuntimeError):
    """A structural or lifecycle error in a Finalization review record."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FinalizationReviewError(f"review file is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalizationReviewError(f"review file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise FinalizationReviewError(f"review file must contain a JSON object: {path}")
    return payload


def load_review_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or DEFAULT_SCHEMA_PATH
    payload = read_json(schema_path)
    if payload.get("finalization_review_schema_version") != "2":
        raise FinalizationReviewError("unsupported Finalization Review Schema version")
    if payload.get("validation_version") != FINALIZATION_REVIEW_VALIDATION_VERSION:
        raise FinalizationReviewError("Finalization Review validation version mismatch")
    reviews = payload.get("reviews")
    if not isinstance(reviews, dict) or set(reviews) != set(REVIEW_TYPES):
        raise FinalizationReviewError("Finalization Review Schema must define three review types")
    for review_type in REVIEW_TYPES:
        definition = reviews.get(review_type)
        if not isinstance(definition, dict):
            raise FinalizationReviewError(f"Review Schema definition is invalid: {review_type}")
        categories = definition.get("categories")
        if not isinstance(categories, list) or not categories or not all(
            isinstance(item, str) and item for item in categories
        ):
            raise FinalizationReviewError(f"Review Schema categories are invalid: {review_type}")
        if len(categories) != len(set(categories)):
            raise FinalizationReviewError(f"Review Schema has duplicate categories: {review_type}")
    return payload


def review_content_manifest(root: Path) -> dict[str, dict[str, Any]]:
    """Hash knowledge content while excluding executor-owned lifecycle metadata."""

    manifest: dict[str, dict[str, Any]] = {}
    if not root.is_dir():
        return manifest
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if (
            relative.startswith(".work/execution/")
            or relative.startswith(CONTENT_EXCLUDE_PREFIXES)
            or relative in CONTENT_EXCLUDES
        ):
            continue
        if not relative.startswith((".work/", "tech-pack/", "ba-pack/")):
            continue
        manifest[relative] = {"size": path.stat().st_size, "sha256": sha256_file(path)}
    return manifest


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(manifest).encode("utf-8"))


def review_content_sha256(root: Path) -> str:
    return manifest_sha256(review_content_manifest(root))


def initialize_review_baseline(transaction_dir: Path, candidate: Path) -> Path:
    path = transaction_dir / REVIEW_BASELINE_NAME
    atomic_write_json(
        path,
        {
            "finalization_review_baseline_schema_version": "1",
            "candidate_content_manifest": review_content_manifest(candidate),
            "candidate_content_manifest_sha256": review_content_sha256(candidate),
            "created_at": now_utc(),
        },
    )
    return path


def ledger_path(transaction_dir: Path) -> Path:
    return transaction_dir / REVIEW_LEDGER_NAME


def _safe_relative(path_value: Any, label: str) -> str:
    if not isinstance(path_value, str) or not path_value.strip():
        raise FinalizationReviewError(f"{label} path is required")
    relative = Path(path_value)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in {".", ""}:
        raise FinalizationReviewError(f"{label} path is unsafe: {path_value}")
    return relative.as_posix()


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FinalizationReviewError(f"{label} is required")
    return value.strip()


def _validate_evidence(evidence: Any, repository: Path) -> list[dict[str, Any]]:
    if evidence is None:
        return []
    if not isinstance(evidence, list):
        raise FinalizationReviewError("evidence must be a list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            raise FinalizationReviewError(f"evidence item {index} must be an object")
        relative = _safe_relative(item.get("path"), f"evidence item {index}")
        target = repository / relative
        if not target.is_file():
            raise FinalizationReviewError(f"evidence file does not exist: {relative}")
        start = item.get("start_line")
        end = item.get("end_line", start)
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            raise FinalizationReviewError(f"evidence line range is invalid: {relative}")
        with target.open("r", encoding="utf-8", errors="replace") as handle:
            line_count = sum(1 for _ in handle)
        if end > line_count:
            raise FinalizationReviewError(
                f"evidence line range exceeds file length: {relative}:{start}-{end}"
            )
        normalized.append(
            {
                "path": relative,
                "start_line": start,
                "end_line": end,
                "sha256": sha256_file(target),
            }
        )
    return normalized


def _validate_corrections(
    corrections: Any,
    candidate: Path,
    baseline: dict[str, Any],
) -> list[dict[str, Any]]:
    if corrections is None:
        return []
    if not isinstance(corrections, list):
        raise FinalizationReviewError("corrections must be a list")
    baseline_manifest = baseline.get("candidate_content_manifest")
    if not isinstance(baseline_manifest, dict):
        raise FinalizationReviewError("Finalization review baseline is invalid")
    current = review_content_manifest(candidate)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(corrections, start=1):
        if not isinstance(item, dict):
            raise FinalizationReviewError(f"correction {index} must be an object")
        relative = _safe_relative(item.get("path"), f"correction {index}")
        if relative in seen:
            raise FinalizationReviewError(f"duplicate correction path: {relative}")
        seen.add(relative)
        summary = _nonempty(item.get("summary"), f"correction {index} summary")
        before = baseline_manifest.get(relative)
        after = current.get(relative)
        before_hash = before.get("sha256") if isinstance(before, dict) else None
        after_hash = after.get("sha256") if isinstance(after, dict) else None
        if before_hash == after_hash:
            raise FinalizationReviewError(
                f"correction path did not change during Finalization: {relative}"
            )
        normalized.append(
            {
                "path": relative,
                "summary": summary,
                "before_sha256": before_hash,
                "after_sha256": after_hash,
            }
        )
    return normalized


def _normalize_review(
    *,
    schema: dict[str, Any],
    review_type: str,
    raw: dict[str, Any],
    candidate: Path,
    repository: Path,
    baseline: dict[str, Any],
    mechanical_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    if review_type not in REVIEW_TYPES:
        raise FinalizationReviewError(f"unsupported review type: {review_type}")
    conclusion = raw.get("overall_conclusion")
    allowed_conclusions = set(schema.get("overall_conclusions", []))
    if conclusion not in allowed_conclusions:
        raise FinalizationReviewError(
            f"overall_conclusion must be one of {sorted(allowed_conclusions)}"
        )
    summary = _nonempty(raw.get("summary"), "review summary")
    required_categories = list(schema["reviews"][review_type]["categories"])
    coverage = raw.get("coverage")
    if not isinstance(coverage, list):
        raise FinalizationReviewError("coverage must be a list")
    coverage_by_category: dict[str, dict[str, Any]] = {}
    for entry in coverage:
        if not isinstance(entry, dict):
            raise FinalizationReviewError("coverage entries must be objects")
        category = entry.get("category")
        if category not in required_categories:
            raise FinalizationReviewError(f"unknown coverage category: {category}")
        if category in coverage_by_category:
            raise FinalizationReviewError(f"duplicate coverage category: {category}")
        status = entry.get("status")
        if status not in set(schema.get("coverage_statuses", [])):
            raise FinalizationReviewError(f"invalid coverage status for {category}: {status}")
        reason = entry.get("reason")
        if status == "not-applicable":
            reason = _nonempty(reason, f"not-applicable reason for {category}")
        elif reason is not None and not isinstance(reason, str):
            raise FinalizationReviewError(f"coverage reason must be text: {category}")
        coverage_by_category[category] = {
            "category": category,
            "status": status,
            "reason": reason.strip() if isinstance(reason, str) and reason.strip() else None,
        }
    missing = [item for item in required_categories if item not in coverage_by_category]
    if missing:
        raise FinalizationReviewError("missing coverage categories: " + ", ".join(missing))

    raw_items = raw.get("items")
    if not isinstance(raw_items, list):
        raise FinalizationReviewError("items must be a list")
    outcomes = set(schema.get("outcomes", []))
    normalized_items: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    reviewed_categories: set[str] = set()
    unresolved = 0
    correction_count = 0
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise FinalizationReviewError(f"review item {index} must be an object")
        sample_id = _nonempty(item.get("sample_id"), f"review item {index} sample_id")
        if not PORTABLE_ID.fullmatch(sample_id) or sample_id in sample_ids:
            raise FinalizationReviewError(f"review item has invalid or duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        category = item.get("category")
        if category not in required_categories:
            raise FinalizationReviewError(f"review item has unknown category: {category}")
        if coverage_by_category[category]["status"] != "reviewed":
            raise FinalizationReviewError(
                f"review item cannot use a not-applicable category: {category}"
            )
        reviewed_categories.add(str(category))
        subject = item.get("subject")
        if not isinstance(subject, dict):
            raise FinalizationReviewError(f"review item {sample_id} subject must be an object")
        relative = _safe_relative(subject.get("path"), f"review item {sample_id} subject")
        target = candidate / relative
        if not target.is_file():
            raise FinalizationReviewError(f"review subject does not exist: {relative}")
        identity = subject.get("identity")
        if identity is not None and (not isinstance(identity, str) or not identity.strip()):
            raise FinalizationReviewError(f"review subject identity is invalid: {sample_id}")
        outcome = item.get("outcome")
        if outcome not in outcomes:
            raise FinalizationReviewError(f"review item has invalid outcome: {sample_id}")
        question = _nonempty(item.get("question"), f"review item {sample_id} question")
        item_conclusion = _nonempty(
            item.get("conclusion"), f"review item {sample_id} conclusion"
        )
        findings = item.get("findings", [])
        if not isinstance(findings, list) or not all(
            isinstance(value, str) and value.strip() for value in findings
        ):
            raise FinalizationReviewError(f"review item findings are invalid: {sample_id}")
        corrections = _validate_corrections(
            item.get("corrections", []), candidate, baseline
        )
        if outcome == "corrected" and not corrections:
            raise FinalizationReviewError(
                f"corrected review item must record a changed Candidate path: {sample_id}"
            )
        if outcome == "corrected" and not findings:
            raise FinalizationReviewError(
                f"corrected review item must record the finding that was fixed: {sample_id}"
            )
        if outcome != "corrected" and corrections:
            raise FinalizationReviewError(
                f"only corrected review items may contain corrections: {sample_id}"
            )
        if outcome == "unresolved":
            unresolved += 1
            if not findings:
                raise FinalizationReviewError(
                    f"unresolved review item must record a finding: {sample_id}"
                )
        correction_count += len(corrections)
        normalized_evidence = _validate_evidence(item.get("evidence", []), repository)
        if review_type == "semantic-fact" and not normalized_evidence:
            raise FinalizationReviewError(
                f"Semantic Fact Review item must cite repository evidence: {sample_id}"
            )
        normalized_items.append(
            {
                "sample_id": sample_id,
                "category": category,
                "subject": {
                    "path": relative,
                    "identity": identity.strip() if isinstance(identity, str) else None,
                    "sha256": sha256_file(target),
                },
                "question": question,
                "outcome": outcome,
                "conclusion": item_conclusion,
                "findings": [value.strip() for value in findings],
                "corrections": corrections,
                "evidence": normalized_evidence,
            }
        )
    uncovered = [
        category
        for category, entry in coverage_by_category.items()
        if entry["status"] == "reviewed" and category not in reviewed_categories
    ]
    if uncovered:
        raise FinalizationReviewError(
            "reviewed coverage categories need at least one sample: " + ", ".join(uncovered)
        )
    if unresolved and conclusion != "blocked":
        raise FinalizationReviewError("unresolved findings require overall_conclusion blocked")
    if not unresolved and conclusion == "blocked":
        raise FinalizationReviewError("blocked conclusion requires an unresolved finding")
    if correction_count and conclusion not in {"passed-with-corrections", "blocked"}:
        raise FinalizationReviewError(
            "recorded corrections require passed-with-corrections or blocked conclusion"
        )

    warning_dispositions = raw.get("warning_dispositions", [])
    if not isinstance(warning_dispositions, list):
        raise FinalizationReviewError("warning_dispositions must be a list")
    normalized_warnings: list[dict[str, str]] = []
    for index, item in enumerate(warning_dispositions, start=1):
        if not isinstance(item, dict):
            raise FinalizationReviewError(f"warning disposition {index} must be an object")
        normalized_warnings.append(
            {
                "warning": _nonempty(item.get("warning"), f"warning disposition {index}"),
                "decision": _nonempty(item.get("decision"), f"warning disposition {index} decision"),
                "reason": _nonempty(item.get("reason"), f"warning disposition {index} reason"),
            }
        )
    if review_type == "mechanical":
        if mechanical_summary is None:
            raise FinalizationReviewError("Mechanical Review requires executor validation results")
        warning_count = mechanical_summary.get("warning_count")
        expected_warnings = {
            str(value)
            for value in mechanical_summary.get("warnings", [])
            if isinstance(value, str) and value
        }
        observed_warnings = {item["warning"] for item in normalized_warnings}
        if isinstance(warning_count, int) and warning_count > 0 and not normalized_warnings:
            raise FinalizationReviewError(
                "Mechanical Review must adjudicate retained Validator warnings"
            )
        if expected_warnings != observed_warnings:
            missing_warnings = sorted(expected_warnings - observed_warnings)
            extra_warnings = sorted(observed_warnings - expected_warnings)
            details: list[str] = []
            if missing_warnings:
                details.append("missing: " + " | ".join(missing_warnings))
            if extra_warnings:
                details.append("unknown: " + " | ".join(extra_warnings))
            raise FinalizationReviewError(
                "Mechanical Review warning dispositions do not match Validator warnings: "
                + "; ".join(details)
            )

    content_hash = review_content_sha256(candidate)
    return {
        "review_type": review_type,
        "status": "blocked" if unresolved else "current",
        "candidate_knowledge_manifest_sha256": content_hash,
        "overall_conclusion": conclusion,
        "summary": summary,
        "coverage": [coverage_by_category[item] for item in required_categories],
        "items": normalized_items,
        "warning_dispositions": normalized_warnings,
        "mechanical_validation": mechanical_summary,
        "sample_count": len(normalized_items),
        "finding_count": sum(len(item["findings"]) for item in normalized_items),
        "correction_count": correction_count,
        "unresolved_count": unresolved,
        "recorded_at": now_utc(),
    }


def record_review(
    *,
    transaction_dir: Path,
    candidate: Path,
    repository: Path,
    transaction_id: str,
    generation_id: str,
    source_commit: str,
    review_type: str,
    input_payload: dict[str, Any],
    mechanical_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    schema = load_review_schema()
    baseline = read_json(transaction_dir / REVIEW_BASELINE_NAME)
    normalized = _normalize_review(
        schema=schema,
        review_type=review_type,
        raw=input_payload,
        candidate=candidate,
        repository=repository,
        baseline=baseline,
        mechanical_summary=mechanical_summary,
    )
    path = ledger_path(transaction_dir)
    if path.is_file():
        ledger = read_json(path)
    else:
        ledger = {
            "finalization_review_schema_version": "2",
            "validation_version": FINALIZATION_REVIEW_VALIDATION_VERSION,
            "transaction_id": transaction_id,
            "generation_id": generation_id,
            "repository": str(repository),
            "source_commit": source_commit,
            "reviews": {},
            "created_at": now_utc(),
        }
    if (
        ledger.get("finalization_review_schema_version") != "2"
        or ledger.get("validation_version") != FINALIZATION_REVIEW_VALIDATION_VERSION
        or ledger.get("transaction_id") != transaction_id
        or ledger.get("generation_id") != generation_id
        or ledger.get("repository") != str(repository)
        or ledger.get("source_commit") != source_commit
        or not isinstance(ledger.get("reviews"), dict)
    ):
        raise FinalizationReviewError("Finalization Review Ledger identity is invalid")
    ledger["reviews"][review_type] = normalized
    ledger["candidate_knowledge_manifest_sha256"] = normalized[
        "candidate_knowledge_manifest_sha256"
    ]
    ledger["updated_at"] = now_utc()
    atomic_write_json(path, ledger)
    return ledger


def evaluate_reviews(
    *,
    transaction_dir: Path,
    candidate: Path,
    transaction_id: str,
    generation_id: str,
    repository: Path,
    source_commit: str,
) -> dict[str, Any]:
    schema = load_review_schema()
    path = ledger_path(transaction_dir)
    statuses = {review_type: "missing" for review_type in REVIEW_TYPES}
    semantic_errors: list[str] = []
    blocking_errors: list[str] = []
    counts = {"samples": 0, "findings": 0, "corrections": 0, "unresolved": 0, "stale": 0}
    if not path.is_file():
        semantic_errors.append("Finalization Review Ledger is missing")
        return {
            "validation_version": FINALIZATION_REVIEW_VALIDATION_VERSION,
            "statuses": statuses,
            "semantic_errors": semantic_errors,
            "blocking_errors": blocking_errors,
            "counts": counts,
            "ledger": None,
            "ledger_path": str(path),
        }
    try:
        ledger = read_json(path)
    except FinalizationReviewError as exc:
        blocking_errors.append(str(exc))
        return {
            "validation_version": FINALIZATION_REVIEW_VALIDATION_VERSION,
            "statuses": statuses,
            "semantic_errors": semantic_errors,
            "blocking_errors": blocking_errors,
            "counts": counts,
            "ledger": None,
            "ledger_path": str(path),
        }
    if ledger.get("finalization_review_schema_version") != "2" or ledger.get(
        "validation_version"
    ) != FINALIZATION_REVIEW_VALIDATION_VERSION:
        blocking_errors.append("Finalization Review Ledger Schema is unsupported")
    for key, expected in (
        ("transaction_id", transaction_id),
        ("generation_id", generation_id),
        ("repository", str(repository)),
        ("source_commit", source_commit),
    ):
        if ledger.get(key) != expected:
            blocking_errors.append(f"Finalization Review Ledger {key} does not match transaction")
    reviews = ledger.get("reviews")
    if not isinstance(reviews, dict):
        blocking_errors.append("Finalization Review Ledger reviews must be an object")
        reviews = {}
    current_hash = review_content_sha256(candidate)
    for review_type in REVIEW_TYPES:
        review = reviews.get(review_type)
        if not isinstance(review, dict):
            semantic_errors.append(f"Finalization {review_type} Review is missing")
            continue
        recorded_hash = review.get("candidate_knowledge_manifest_sha256")
        if recorded_hash != current_hash:
            statuses[review_type] = "stale"
            counts["stale"] += 1
            semantic_errors.append(
                f"Finalization {review_type} Review is stale because Candidate content changed"
            )
            continue
        unresolved = review.get("unresolved_count")
        if not isinstance(unresolved, int) or unresolved < 0:
            blocking_errors.append(f"Finalization {review_type} Review counts are invalid")
            statuses[review_type] = "invalid"
            continue
        statuses[review_type] = "blocked" if unresolved else "current"
        for source, target in (
            ("sample_count", "samples"),
            ("finding_count", "findings"),
            ("correction_count", "corrections"),
            ("unresolved_count", "unresolved"),
        ):
            value = review.get(source)
            if isinstance(value, int) and value >= 0:
                counts[target] += value
            else:
                blocking_errors.append(f"Finalization {review_type} Review {source} is invalid")
        if unresolved:
            semantic_errors.append(
                f"Finalization {review_type} Review has {unresolved} unresolved finding(s)"
            )
        declared_categories = {
            item.get("category")
            for item in review.get("coverage", [])
            if isinstance(item, dict)
        }
        required_categories = set(schema["reviews"][review_type]["categories"])
        if declared_categories != required_categories:
            blocking_errors.append(
                f"Finalization {review_type} Review coverage no longer matches the bundled Schema"
            )
            statuses[review_type] = "invalid"
    distinct_hashes = {
        review.get("candidate_knowledge_manifest_sha256")
        for review in reviews.values()
        if isinstance(review, dict)
    }
    if len(distinct_hashes) > 1:
        semantic_errors.append("Finalization Reviews do not bind the same Candidate content")
    return {
        "validation_version": FINALIZATION_REVIEW_VALIDATION_VERSION,
        "statuses": statuses,
        "semantic_errors": sorted(set(semantic_errors)),
        "blocking_errors": sorted(set(blocking_errors)),
        "counts": counts,
        "candidate_knowledge_manifest_sha256": current_hash,
        "ledger": ledger,
        "ledger_path": str(path),
    }


def receipt_review_summary(evaluation: dict[str, Any]) -> dict[str, Any]:
    counts = evaluation.get("counts", {})
    statuses = evaluation.get("statuses", {})
    return {
        "finalization_review_validation_version": evaluation.get("validation_version"),
        "mechanical_pass_status": (
            "passed" if statuses.get("mechanical") == "current" else statuses.get("mechanical")
        ),
        "semantic_fact_review_status": statuses.get("semantic-fact"),
        "reader_review_status": statuses.get("reader"),
        "finalization_review_candidate_manifest_sha256": evaluation.get(
            "candidate_knowledge_manifest_sha256"
        ),
        "finalization_review_sample_count": counts.get("samples", 0),
        "finalization_review_finding_count": counts.get("findings", 0),
        "finalization_review_correction_count": counts.get("corrections", 0),
        "finalization_review_unresolved_count": counts.get("unresolved", 0),
        "finalization_review_stale_count": counts.get("stale", 0),
    }


def persist_review_sidecar(
    *, transaction_dir: Path, output: Path, sequence: int, generation_id: str
) -> tuple[Path, str]:
    source = ledger_path(transaction_dir)
    ledger = read_json(source)
    destination = (
        output
        / ".work"
        / "execution"
        / "reviews"
        / f"{sequence:03d}-{generation_id}.finalization-review.json"
    )
    if destination.exists():
        raise FinalizationReviewError(f"Finalization Review sidecar already exists: {destination}")
    atomic_write_json(destination, ledger)
    return destination, sha256_file(destination)


def persisted_review_status(
    *, output: Path, receipt: dict[str, Any], repository: str, source_commit: str
) -> dict[str, Any]:
    expected = FINALIZATION_REVIEW_VALIDATION_VERSION
    observed = receipt.get("finalization_review_validation_version")
    base = {
        "expected_version": expected,
        "observed_version": observed if isinstance(observed, str) else None,
        "mechanical_pass_status": receipt.get("mechanical_pass_status"),
        "semantic_fact_review_status": receipt.get("semantic_fact_review_status"),
        "reader_review_status": receipt.get("reader_review_status"),
        "sample_count": receipt.get("finalization_review_sample_count"),
        "finding_count": receipt.get("finalization_review_finding_count"),
        "correction_count": receipt.get("finalization_review_correction_count"),
        "unresolved_count": receipt.get("finalization_review_unresolved_count"),
        "stale_count": receipt.get("finalization_review_stale_count"),
        "record": receipt.get("finalization_review_record"),
        "record_sha256": receipt.get("finalization_review_record_sha256"),
        "errors": [],
    }
    if observed != expected:
        return {"status": "revalidation-required", **base}
    relative = receipt.get("finalization_review_record")
    if not isinstance(relative, str):
        base["errors"].append("Finalization Review Receipt has no record path")
        return {"status": "invalid", **base}
    record_path = Path(relative)
    expected_prefix = Path(".work/execution/reviews")
    if record_path.is_absolute() or ".." in record_path.parts or expected_prefix not in record_path.parents:
        base["errors"].append("Finalization Review Receipt record path is unsafe")
        return {"status": "invalid", **base}
    target = output / record_path
    if not target.is_file():
        base["errors"].append("Finalization Review record is missing")
        return {"status": "invalid", **base}
    if receipt.get("finalization_review_record_sha256") != sha256_file(target):
        base["errors"].append("Finalization Review record checksum does not match Receipt")
        return {"status": "invalid", **base}
    try:
        ledger = read_json(target)
    except FinalizationReviewError as exc:
        base["errors"].append(str(exc))
        return {"status": "invalid", **base}
    for key, expected_value in (
        ("generation_id", receipt.get("generation_id")),
        ("repository", repository),
        ("source_commit", source_commit),
        ("transaction_id", receipt.get("transaction_id")),
    ):
        if ledger.get(key) != expected_value:
            base["errors"].append(f"Finalization Review record {key} does not match Receipt")
    content_hash = review_content_sha256(output)
    if receipt.get("finalization_review_candidate_manifest_sha256") != content_hash:
        base["errors"].append("Published Pack no longer matches the reviewed Candidate content")
    current = (
        base["mechanical_pass_status"] == "passed"
        and base["semantic_fact_review_status"] == "current"
        and base["reader_review_status"] == "current"
        and base["unresolved_count"] == 0
        and base["stale_count"] == 0
        and not base["errors"]
    )
    return {"status": "current" if current else "invalid", **base}
