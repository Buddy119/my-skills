#!/usr/bin/env python3
"""Fail-closed runtime and write-boundary checks for the bundled Skill tools."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable


MINIMUM_PYTHON = (3, 9)
LOCK_RELATIVE_PATH = Path("integrity/runtime-lock.json")
RELEASE_DIRECTORIES = ("agents", "assets", "bin", "references", "scripts")
IGNORED_RELEASE_NAMES = {".DS_Store"}
IGNORED_RELEASE_SUFFIXES = {".pyc", ".pyo"}
RUNTIME_ERROR_EXIT = 70


class RuntimeGuardError(RuntimeError):
    """The immutable bundled runtime cannot be used safely."""


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def discover_release_files(root: Path) -> dict[str, Path]:
    root = root.expanduser().resolve()
    discovered: dict[str, Path] = {}
    candidates = [root / "SKILL.md"]
    for directory_name in RELEASE_DIRECTORIES:
        directory = root / directory_name
        if directory.is_symlink():
            raise RuntimeGuardError(f"release directories must not be symbolic links: {directory_name}/")
        if not directory.is_dir():
            raise RuntimeGuardError(f"required release directory is missing: {directory_name}/")
        candidates.extend(sorted(directory.rglob("*")))

    for path in candidates:
        if path.is_symlink():
            relative = path.relative_to(root).as_posix()
            raise RuntimeGuardError(f"release artifacts must not be symbolic links: {relative}")
        if "__pycache__" in path.parts or path.suffix in IGNORED_RELEASE_SUFFIXES:
            relative = path.relative_to(root).as_posix()
            raise RuntimeGuardError(f"compiled Python artifacts are forbidden in the release: {relative}")
        if not path.is_file():
            continue
        if path.name in IGNORED_RELEASE_NAMES:
            continue
        relative = path.relative_to(root).as_posix()
        discovered[relative] = path
    return discovered


def bundle_sha256(file_hashes: dict[str, str]) -> str:
    canonical = "\n".join(f"{path}:{file_hashes[path]}" for path in sorted(file_hashes)) + "\n"
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_lock(root: Path) -> tuple[Path, dict[str, object]]:
    lock_path = root / LOCK_RELATIVE_PATH
    if lock_path.parent.is_symlink() or lock_path.is_symlink():
        raise RuntimeGuardError(f"integrity lock must not be reached through a symbolic link: {LOCK_RELATIVE_PATH}")
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeGuardError(f"integrity lock is missing: {LOCK_RELATIVE_PATH}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeGuardError(f"integrity lock cannot be read: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeGuardError("integrity lock root must be an object")
    return lock_path, data


def verify_integrity(root: Path | None = None) -> dict[str, object]:
    root = (root or skill_root()).expanduser().resolve()
    lock_path, lock = _load_lock(root)
    errors: list[str] = []

    if lock.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if lock.get("algorithm") != "sha256":
        errors.append("algorithm must be sha256")
    runtime = lock.get("runtime")
    if runtime != {
        "python_minimum": "3.9",
        "isolated_flags": ["-E", "-S", "-B", "-X utf8"],
        "third_party_dependencies": [],
    }:
        errors.append("runtime contract is missing or has changed")

    locked_files = lock.get("files")
    if not isinstance(locked_files, dict) or not all(
        isinstance(path, str) and isinstance(digest, str)
        for path, digest in locked_files.items()
    ):
        errors.append("files must be a path-to-sha256 object")
        locked_files = {}

    discovered = discover_release_files(root)
    locked_paths = set(locked_files)
    discovered_paths = set(discovered)
    for relative in sorted(locked_paths - discovered_paths):
        errors.append(f"locked artifact is missing: {relative}")
    for relative in sorted(discovered_paths - locked_paths):
        errors.append(f"unlocked release artifact exists: {relative}")

    actual_hashes: dict[str, str] = {}
    for relative in sorted(locked_paths & discovered_paths):
        actual = sha256_file(discovered[relative])
        actual_hashes[relative] = actual
        if locked_files[relative] != actual:
            errors.append(f"artifact digest mismatch: {relative}")

    expected_bundle = lock.get("bundle_sha256")
    locked_bundle = bundle_sha256(dict(locked_files)) if locked_files else None
    if expected_bundle != locked_bundle:
        errors.append("bundle_sha256 does not match the locked file table")

    if errors:
        detail = "\n  - ".join(errors)
        raise RuntimeGuardError(
            "immutable runtime integrity verification failed:\n  - "
            + detail
            + "\nDo not edit bundled files or regenerate the lock during repository analysis."
        )

    return {
        "root": str(root),
        "lock": str(lock_path),
        "lock_sha256": sha256_file(lock_path),
        "bundle_sha256": expected_bundle,
        "file_count": len(locked_files),
    }


def verify_isolated_interpreter() -> None:
    if sys.version_info < MINIMUM_PYTHON:
        actual = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raise RuntimeGuardError(f"Python 3.9 or newer is required; found {actual}")

    missing: list[str] = []
    if not sys.flags.ignore_environment:
        missing.append("-E")
    if not sys.flags.no_site:
        missing.append("-S")
    if not sys.flags.dont_write_bytecode:
        missing.append("-B")
    if not sys.flags.utf8_mode:
        missing.append("-X utf8")
    if missing:
        raise RuntimeGuardError(
            "isolated interpreter flags are required: "
            + " ".join(missing)
            + ". Invoke only with: python3 -E -S -B -X utf8 <SKILL_ROOT>/bin/eapi-pack ..."
        )


def verify_runtime(root: Path | None = None) -> dict[str, object]:
    verify_isolated_interpreter()
    return verify_integrity(root)


def resolve_outside_skill(
    target: Path,
    *,
    label: str = "output",
    root: Path | None = None,
) -> Path:
    release_root = (root or skill_root()).expanduser().resolve()
    candidate = target.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    candidate = candidate.resolve(strict=False)
    if _is_within(candidate, release_root) or _is_within(release_root, candidate):
        raise RuntimeGuardError(
            f"write boundary violation: {label} overlaps immutable SKILL_ROOT: {candidate}"
        )
    return candidate


def reject_descendant(
    target: Path,
    protected_root: Path,
    *,
    label: str,
    protected_label: str,
) -> Path:
    candidate = target.expanduser().resolve(strict=False)
    protected = protected_root.expanduser().resolve(strict=False)
    if _is_within(candidate, protected):
        raise RuntimeGuardError(
            f"write boundary violation: {label} resolves inside {protected_label}: {candidate}"
        )
    return candidate


def reject_tree_overlap(
    target: Path,
    protected_root: Path,
    *,
    label: str,
    protected_label: str,
) -> Path:
    candidate = target.expanduser().resolve(strict=False)
    protected = protected_root.expanduser().resolve(strict=False)
    if _is_within(candidate, protected) or _is_within(protected, candidate):
        raise RuntimeGuardError(
            f"write boundary violation: {label} overlaps {protected_label}: {candidate}"
        )
    return candidate


def _validated_output_target(target: Path, output_root: Path, label: str) -> tuple[Path, Path]:
    raw_root = output_root.expanduser()
    if not raw_root.is_absolute():
        raw_root = Path.cwd() / raw_root
    raw_root = raw_root.absolute()
    root = resolve_outside_skill(raw_root, label="output root")

    raw_candidate = target.expanduser()
    if not raw_candidate.is_absolute():
        raw_candidate = Path.cwd() / raw_candidate
    raw_candidate = raw_candidate.absolute()

    try:
        relative = raw_candidate.relative_to(raw_root)
    except ValueError as exc:
        raise RuntimeGuardError(
            f"write boundary violation: {label} is outside output root: {raw_candidate}"
        ) from exc

    current = raw_root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise RuntimeGuardError(f"write boundary violation: {label} uses a symbolic link: {current}")

    resolved = raw_candidate.resolve(strict=False)
    if not _is_within(resolved, root):
        raise RuntimeGuardError(f"write boundary violation: {label} escapes output root: {resolved}")
    resolve_outside_skill(resolved, label=label)
    return root, resolved


def validate_output_target(target: Path, output_root: Path, *, label: str = "output") -> Path:
    """Validate one target and every in-pack path component without writing."""

    _root, resolved = _validated_output_target(target, output_root, label)
    return resolved


def ensure_output_directory(directory: Path, output_root: Path, *, label: str = "output directory") -> Path:
    root, target = _validated_output_target(directory, output_root, label)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise RuntimeGuardError(f"output root is not a directory: {root}")

    relative = target.relative_to(root)
    current = root
    for component in relative.parts:
        current = current / component
        if current.exists():
            if current.is_symlink() or not current.is_dir():
                raise RuntimeGuardError(f"unsafe output directory component: {current}")
        else:
            current.mkdir()
    return target


def atomic_write_text(
    destination: Path,
    content: str,
    *,
    output_root: Path,
    label: str = "output file",
) -> Path:
    """Write without following an existing destination symlink or hardlink."""

    root, target = _validated_output_target(destination, output_root, label)
    ensure_output_directory(target.parent, root, label=f"{label} parent")
    if target.exists() and target.is_dir():
        raise RuntimeGuardError(f"output file is an existing directory: {target}")
    if target.is_symlink():
        raise RuntimeGuardError(f"write boundary violation: {label} is a symbolic link: {target}")

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return target


def run_guarded(main: Callable[[], int]) -> int:
    """Run a bundled CLI only after and while the release remains intact."""

    try:
        verify_runtime()
        result = main()
        verify_integrity()
        return result
    except RuntimeGuardError as exc:
        print(f"FATAL_RUNTIME: {exc}", file=sys.stderr)
        return RUNTIME_ERROR_EXIT
