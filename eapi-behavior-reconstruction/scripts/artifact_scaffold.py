#!/usr/bin/env python3
"""Deterministically scaffold versioned artifacts without generating knowledge content."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from artifact_schema import ArtifactDefinition, ArtifactRegistry, artifact_metadata


DEFAULT_SCAFFOLD_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "artifact-scaffold-schema.json"
)
SCAFFOLD_SCHEMA_VERSION = "2"
PORTABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
IDENTITY_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ArtifactScaffoldError(RuntimeError):
    """The Scaffold contract or a requested deterministic render is invalid."""


@dataclass(frozen=True)
class ScaffoldDefinition:
    artifact_type: str
    path_identity_field: str | None
    identity_fields: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ScaffoldSchema:
    version: str
    definitions: dict[str, ScaffoldDefinition]


@dataclass(frozen=True)
class RenderedArtifact:
    artifact_type: str
    artifact_schema_version: str
    relative_path: str
    content: str
    identity: dict[str, str]


def _json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactScaffoldError(f"cannot read Scaffold Schema {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactScaffoldError(f"Scaffold Schema must be a JSON object: {path}")
    return payload


def _header(text: str, suffix: str) -> str:
    if suffix.lower() == ".md":
        if not text.startswith("---\n"):
            raise ArtifactScaffoldError("Markdown scaffold template has no YAML Frontmatter")
        end = text.find("\n---\n", 4)
        if end == -1:
            raise ArtifactScaffoldError("Markdown scaffold template has unclosed YAML Frontmatter")
        return text[4:end]
    return text


def _scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(?P<value>[^\n#]+?)\s*$", text, re.M)
    if not match:
        return None
    value = match.group("value").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        if value[0] == '"':
            try:
                decoded = json.loads(value)
                return decoded if isinstance(decoded, str) else str(decoded)
            except json.JSONDecodeError:
                pass
        return value[1:-1]
    return value


def _set_header_scalar(text: str, suffix: str, key: str, value: str) -> str:
    line = f"{key}: {json.dumps(value, ensure_ascii=False)}"

    def replace(header: str) -> str:
        pattern = re.compile(rf"^{re.escape(key)}:\s*[^\n]*(?:\n|$)", re.M)
        if not pattern.search(header):
            raise ArtifactScaffoldError(f"scaffold template is missing identity field: {key}")
        return pattern.sub(line + "\n", header, count=1).rstrip("\n")

    if suffix.lower() == ".md":
        end = text.find("\n---\n", 4)
        if not text.startswith("---\n") or end == -1:
            raise ArtifactScaffoldError("Markdown scaffold template has invalid YAML Frontmatter")
        return "---\n" + replace(text[4:end]) + text[end:]
    return replace(text) + ("\n" if text.endswith("\n") else "")


def load_scaffold_schema(
    registry: ArtifactRegistry,
    path: Path = DEFAULT_SCAFFOLD_SCHEMA_PATH,
    assets_root: Path | None = None,
) -> ScaffoldSchema:
    payload = _json_object(path)
    version = payload.get("artifact_scaffold_schema_version")
    if version != SCAFFOLD_SCHEMA_VERSION:
        raise ArtifactScaffoldError(
            "artifact_scaffold_schema_version must be " + SCAFFOLD_SCHEMA_VERSION
        )
    raw_definitions = payload.get("artifact_types")
    if not isinstance(raw_definitions, dict) or not raw_definitions:
        raise ArtifactScaffoldError("Scaffold Schema must define artifact_types")
    root = assets_root or path.parent
    definitions: dict[str, ScaffoldDefinition] = {}
    for artifact_type, raw in raw_definitions.items():
        if not isinstance(artifact_type, str) or not isinstance(raw, dict):
            raise ArtifactScaffoldError("each Scaffold Artifact must be a named object")
        artifact = registry.definitions.get(artifact_type)
        if artifact is None:
            raise ArtifactScaffoldError(
                f"Scaffold Artifact is absent from Artifact Registry: {artifact_type}"
            )
        if not artifact.template:
            raise ArtifactScaffoldError(f"Scaffold Artifact has no template: {artifact_type}")
        if artifact.producing_stage in {"init", "stage-executor", "resume-audit", "finalization"}:
            raise ArtifactScaffoldError(
                f"Scaffold Artifact has an executor-owned producing stage: {artifact_type}"
            )
        if len(artifact.paths) != 1:
            raise ArtifactScaffoldError(
                f"Scaffold Artifact must have exactly one Registry path: {artifact_type}"
            )
        pattern = artifact.paths[0]
        wildcard_count = pattern.count("*")
        if wildcard_count > 1:
            raise ArtifactScaffoldError(
                f"Scaffold Artifact path may contain at most one wildcard: {artifact_type}"
            )
        path_identity = raw.get("path_identity_field")
        if path_identity is not None and not isinstance(path_identity, str):
            raise ArtifactScaffoldError(
                f"path_identity_field must be a string or null: {artifact_type}"
            )
        raw_fields = raw.get("identity_fields")
        if not isinstance(raw_fields, dict):
            raise ArtifactScaffoldError(f"identity_fields must be an object: {artifact_type}")
        identity_fields: dict[str, tuple[str, ...]] = {}
        for field, raw_tokens in raw_fields.items():
            if not isinstance(field, str) or not IDENTITY_KEY.fullmatch(field):
                raise ArtifactScaffoldError(
                    f"Scaffold identity field is invalid for {artifact_type}: {field}"
                )
            if isinstance(raw_tokens, str):
                tokens = (raw_tokens,)
            elif (
                isinstance(raw_tokens, list)
                and raw_tokens
                and all(isinstance(token, str) and token for token in raw_tokens)
            ):
                tokens = tuple(raw_tokens)
            else:
                raise ArtifactScaffoldError(
                    f"Scaffold identity tokens are invalid for {artifact_type}.{field}"
                )
            if len(set(tokens)) != len(tokens):
                raise ArtifactScaffoldError(
                    f"Scaffold identity tokens contain duplicates for {artifact_type}.{field}"
                )
            identity_fields[field] = tokens
        all_tokens = [token for tokens in identity_fields.values() for token in tokens]
        if len(set(all_tokens)) != len(all_tokens):
            raise ArtifactScaffoldError(
                f"Scaffold identity tokens must be unique: {artifact_type}"
            )
        if wildcard_count == 1 and path_identity not in identity_fields:
            raise ArtifactScaffoldError(
                f"wildcard Scaffold path requires a declared path identity: {artifact_type}"
            )
        if wildcard_count == 0 and path_identity is not None:
            raise ArtifactScaffoldError(
                f"singleton Scaffold path cannot declare a path identity: {artifact_type}"
            )
        template = root / artifact.template
        try:
            template_text = template.read_text(encoding="utf-8")
        except OSError as exc:
            raise ArtifactScaffoldError(
                f"cannot read Scaffold template {artifact.template}: {exc}"
            ) from exc
        if "repository-name" not in template_text or "git-commit-or-unknown" not in template_text:
            raise ArtifactScaffoldError(
                f"Scaffold template lacks repository or commit token: {artifact.template}"
            )
        header = _header(template_text, template.suffix)
        for field, tokens in identity_fields.items():
            if _scalar(header, field) is None:
                raise ArtifactScaffoldError(
                    f"Scaffold template lacks identity field {field}: {artifact.template}"
                )
            for token in tokens:
                if token not in template_text:
                    raise ArtifactScaffoldError(
                        f"Scaffold template lacks identity token {token}: {artifact.template}"
                    )
        definitions[artifact_type] = ScaffoldDefinition(
            artifact_type=artifact_type,
            path_identity_field=path_identity,
            identity_fields=identity_fields,
        )
    return ScaffoldSchema(version=version, definitions=definitions)


def parse_identity_arguments(values: list[str]) -> dict[str, str]:
    identity: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ArtifactScaffoldError(
                f"--identity must use key=value syntax: {value}"
            )
        key, item = value.split("=", 1)
        if not key or not item:
            raise ArtifactScaffoldError(
                f"--identity must contain a non-empty key and value: {value}"
            )
        if key in identity:
            raise ArtifactScaffoldError(f"duplicate --identity field: {key}")
        if not IDENTITY_KEY.fullmatch(key):
            raise ArtifactScaffoldError(f"invalid --identity field: {key}")
        if item in {".", ".."} or not PORTABLE_ID.fullmatch(item):
            raise ArtifactScaffoldError(
                f"identity value uses unsupported portable characters: {key}={item}"
            )
        identity[key] = item
    return identity


def render_artifact(
    registry: ArtifactRegistry,
    schema: ScaffoldSchema,
    assets_root: Path,
    artifact_type: str,
    repository: str,
    source_commit: str,
    identity: dict[str, str],
) -> RenderedArtifact:
    scaffold = schema.definitions.get(artifact_type)
    if scaffold is None:
        raise ArtifactScaffoldError(f"Artifact type is not scaffoldable: {artifact_type}")
    artifact: ArtifactDefinition = registry.definitions[artifact_type]
    expected = set(scaffold.identity_fields)
    observed = set(identity)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise ArtifactScaffoldError(
            f"Artifact {artifact_type} is missing identity field(s): " + ", ".join(missing)
        )
    if unknown:
        raise ArtifactScaffoldError(
            f"Artifact {artifact_type} has unknown identity field(s): " + ", ".join(unknown)
        )
    pattern = artifact.paths[0]
    relative = pattern
    if scaffold.path_identity_field is not None:
        relative = pattern.replace("*", identity[scaffold.path_identity_field])
    template = assets_root / str(artifact.template)
    try:
        text = template.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactScaffoldError(f"cannot read Scaffold template {template}: {exc}") from exc
    text = text.replace("repository-name", repository)
    text = text.replace("git-commit-or-unknown", source_commit)
    for field, tokens in scaffold.identity_fields.items():
        for token in tokens:
            text = text.replace(token, identity[field])
    for key, value in (
        ("artifact_type", artifact_type),
        ("artifact_schema_version", artifact.current_version),
        ("repository", repository),
        ("source_commit", source_commit),
        *tuple(identity.items()),
    ):
        text = _set_header_scalar(text, template.suffix, key, value)
    return RenderedArtifact(
        artifact_type=artifact_type,
        artifact_schema_version=artifact.current_version,
        relative_path=relative,
        content=text,
        identity=dict(identity),
    )


def existing_artifact_matches(
    path: Path,
    rendered: RenderedArtifact,
    repository: str,
    source_commit: str,
) -> tuple[bool, list[str]]:
    observed_type, observed_version = artifact_metadata(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactScaffoldError(f"cannot read existing Artifact {path}: {exc}") from exc
    header = _header(text, path.suffix)
    expected = {
        "artifact_type": rendered.artifact_type,
        "artifact_schema_version": rendered.artifact_schema_version,
        "repository": repository,
        "source_commit": source_commit,
        **rendered.identity,
    }
    observed = {
        "artifact_type": observed_type,
        "artifact_schema_version": observed_version,
        "repository": _scalar(header, "repository"),
        "source_commit": _scalar(header, "source_commit"),
        **{key: _scalar(header, key) for key in rendered.identity},
    }
    mismatches = [
        f"{key}: expected {expected[key]!r}, observed {observed.get(key)!r}"
        for key in expected
        if observed.get(key) != expected[key]
    ]
    return not mismatches, mismatches
