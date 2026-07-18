#!/usr/bin/env python3
"""Build a lightweight, deterministic source-evidence index for one repository."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


TEXT_EXTENSIONS = {
    ".java", ".kt", ".kts", ".groovy", ".scala", ".cs",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".go", ".rs", ".rb", ".php",
    ".yaml", ".yml", ".json", ".xml", ".toml", ".tf",
    ".properties", ".conf", ".env", ".graphql", ".proto",
}

SPECIAL_FILES = {
    "Dockerfile", "Makefile", "build.gradle", "build.gradle.kts",
    "pom.xml", "package.json", "serverless.yml", "serverless.yaml",
    "template.yml", "template.yaml",
}

IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "node_modules", "vendor", "dist",
    "build", "target", "out", "coverage", ".gradle", ".terraform",
    ".serverless", ".aws-sam", "__pycache__", ".pytest_cache",
}

ROLE_PATH_RULES = {
    "test": re.compile(r"(^|/)(test|tests|spec|specs)(/|$)|(^|/)(?:test_.*|.*_(?:test|tests|spec))\.[^/]+$", re.I),
    "shared-controller": re.compile(r"shared.*controller|controller.*shared", re.I),
    "controller": re.compile(r"controller", re.I),
    "handler": re.compile(r"handler|lambda", re.I),
    "service": re.compile(r"service|usecase|use-case", re.I),
    "client": re.compile(r"client|gateway|connector|adapter", re.I),
    "repository": re.compile(r"repository|dao|persistence", re.I),
    "transformer": re.compile(r"mapper|transformer|converter|assembler|serializer", re.I),
    "model-schema": re.compile(r"model|dto|schema|contract|entity|request|response", re.I),
    "infrastructure": re.compile(r"terraform|cloudformation|serverless|template|infrastructure|infra|cdk|sam", re.I),
}

MARKER_RULES = {
    "endpoint": re.compile(
        r"@(Get|Post|Put|Delete|Patch|Request)Mapping\b|"
        r"@(GET|POST|PUT|DELETE|PATCH)\b|"
        r"\b(?:app|router)\.(?:get|post|put|delete|patch)\s*\(|"
        r"@(?:app|router)\.(?:get|post|put|delete|patch)\s*\(",
        re.I,
    ),
    "lambda-entry": re.compile(
        r"\bRequestHandler\b|\bhandleRequest\s*\(|\bexports\.handler\b|"
        r"\bdef\s+(?:lambda_)?handler\s*\(|\bHandler:\s*\S+",
        re.I,
    ),
    "external-http-call": re.compile(
        r"\b(?:fetch|axios\.(?:get|post|put|delete|patch)|requests\.(?:get|post|put|delete|patch))\s*\(|"
        r"\b(?:restTemplate|webClient|httpClient|client)\s*\.\s*(?:get|post|put|delete|patch|exchange|send|execute)\s*\(",
        re.I,
    ),
    "test-declaration": re.compile(
        r"@Test\b|\bdef\s+test_\w+\s*\(|\b(?:it|test|describe)\s*\(",
        re.I,
    ),
    "assertion": re.compile(
        r"\bassert(?:Equals|True|False|Null|NotNull|Throws|That)?\s*\(|"
        r"\bAssertions\.|\bexpect\s*\(|\.should\b|\.isEqualTo\s*\(|"
        r"\bassert\s+\S+",
        re.I,
    ),
}

SYMBOL_RULES = (
    ("class", re.compile(r"^\s*(?:export\s+|public\s+|private\s+|protected\s+|abstract\s+|final\s+)*(?:class|interface|enum|record)\s+([A-Za-z_$][\w$]*)")),
    ("python-class", re.compile(r"^\s*class\s+([A-Za-z_]\w*)")),
    ("python-function", re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(")),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")),
    ("method", re.compile(r"^\s*(?:public|private|protected|static|final|abstract|synchronized|async|override|suspend|open|internal|external|native|\s)+\s*[\w<>,.?\[\]$]+\s+([A-Za-z_$][\w$]*)\s*\(")),
)


def git_commit(repo: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def is_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in SPECIAL_FILES


def role_hints(relative_path: str, content: str) -> list[str]:
    roles = [role for role, pattern in ROLE_PATH_RULES.items() if pattern.search(relative_path)]
    if "test" in roles:
        return ["test"]
    return sorted(set(roles))


def collect_symbols(lines: list[str], limit: int) -> list[dict[str, object]]:
    symbols: list[dict[str, object]] = []
    seen: set[tuple[str, str, int]] = set()
    for line_number, line in enumerate(lines, 1):
        for kind, pattern in SYMBOL_RULES:
            match = pattern.search(line)
            if not match:
                continue
            item = (kind, match.group(1), line_number)
            if item not in seen:
                symbols.append({"kind": kind, "name": match.group(1), "line": line_number})
                seen.add(item)
            break
        if len(symbols) >= limit:
            break
    return symbols


def collect_markers(lines: list[str], limit_per_kind: int) -> dict[str, list[dict[str, object]]]:
    markers: dict[str, list[dict[str, object]]] = {kind: [] for kind in MARKER_RULES}
    for line_number, line in enumerate(lines, 1):
        for kind, pattern in MARKER_RULES.items():
            if len(markers[kind]) >= limit_per_kind or not pattern.search(line):
                continue
            markers[kind].append({"line": line_number, "text": line.strip()[:240]})
    return {kind: values for kind, values in markers.items() if values}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-symbols-per-file", type=int, default=300)
    parser.add_argument("--max-markers-per-kind", type=int, default=300)
    args = parser.parse_args()

    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"ERROR: repository directory does not exist: {repo}", file=sys.stderr)
        return 2

    files: list[dict[str, object]] = []
    role_index: dict[str, list[str]] = defaultdict(list)
    skipped: list[dict[str, str]] = []

    for path in sorted(repo.rglob("*")):
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.relative_to(repo).parts):
            continue
        if not is_candidate(path):
            continue
        relative = path.relative_to(repo).as_posix()
        try:
            if path.stat().st_size > args.max_file_bytes:
                skipped.append({"path": relative, "reason": "file exceeds max-file-bytes"})
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            skipped.append({"path": relative, "reason": str(exc)})
            continue

        lines = content.splitlines()
        roles = role_hints(relative, content)
        for role in roles:
            role_index[role].append(relative)

        files.append(
            {
                "path": relative,
                "extension": path.suffix.lower(),
                "line_count": len(lines),
                "roles": roles,
                "symbols": collect_symbols(lines, args.max_symbols_per_file),
                "markers": collect_markers(lines, args.max_markers_per_kind),
            }
        )

    marker_counts: dict[str, int] = defaultdict(int)
    for item in files:
        for kind, markers in item["markers"].items():
            marker_counts[kind] += len(markers)

    output = {
        "artifact_type": "evidence-index",
        "artifact_schema_version": "1",
        "repository": repo.name,
        "source_commit": git_commit(repo),
        "summary": {
            "indexed_files": len(files),
            "skipped_files": len(skipped),
            "marker_counts": dict(sorted(marker_counts.items())),
        },
        "role_index": {role: sorted(paths) for role, paths in sorted(role_index.items())},
        "files": files,
        "skipped": skipped,
    }

    destination = args.output.expanduser()
    if not destination.is_absolute():
        destination = Path.cwd() / destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"OK: indexed {len(files)} file(s), found {sum(marker_counts.values())} marker(s), "
        f"wrote {destination}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
