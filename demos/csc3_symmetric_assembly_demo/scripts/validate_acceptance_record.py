#!/usr/bin/env python3
"""Validate one CSC3 formal acceptance record and all evidence it claims."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType, ModuleType
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker


EXPECTED_TESTS = (
    "Csc3DemoTests",
    "Csc3DemoConsumer",
    "Csc3DemoCorrectness",
    "Csc3DemoBenchmarkTiming",
    "Csc3DemoBenchmarkEngine",
    "Csc3DemoBenchmarkIo",
    "Csc3DemoInpCase",
    "Csc3DemoWindHubBenchmark",
    "Csc3DemoBenchmarkRunner",
    "Csc3DemoAtomicContention",
)
MAXIMUM_ABSOLUTE_BASE_TOLERANCE = 1.0e-10
MAXIMUM_ABSOLUTE_SCALE_TOLERANCE = 1.0e-8
SHA256SUMS_LINE = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)\n$")
RFC3339_UTC = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?Z$"
)


class AcceptanceRecordError(RuntimeError):
    """Raised when an acceptance record fails one or more checks."""

    def __init__(self, errors: str | list[str]) -> None:
        self.errors = (errors,) if isinstance(errors, str) else tuple(errors)
        if len(self.errors) == 1:
            message = self.errors[0]
        else:
            message = (
                f"acceptance record validation failed with {len(self.errors)} errors:\n"
                + "\n".join(f"- {error}" for error in self.errors)
            )
        super().__init__(message)


@dataclass(frozen=True)
class ValidatedAcceptanceSnapshot:
    """One validated, private, byte-stable view of all delivery inputs."""

    result: Mapping[str, object]
    record: Mapping[str, object]
    record_content: bytes
    archive_content: bytes | None
    artifact_contents: Mapping[str, bytes]


@dataclass(frozen=True)
class _CapturedAcceptanceSnapshot:
    record: Mapping[str, object]
    record_content: bytes
    source_record_path: Path
    source_run_root: Path
    source_archive_path: Path
    run_root: Path
    archive_path: Path
    artifact_contents: Mapping[str, bytes]
    capture_errors: tuple[str, ...]


def _load_sibling(filename: str, module_name: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    existing = sys.modules.get(module_name)
    if isinstance(existing, ModuleType):
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load required validator helper: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key is forbidden: {key!r}")
        result[key] = value
    return result


def _load_json(path: Path, label: str) -> object:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise AcceptanceRecordError(
            f"{label} is not strict UTF-8 JSON: {error}"
        ) from error
    return _load_json_bytes(content, label)


def _load_json_bytes(content: bytes, label: str) -> object:
    try:
        value = json.loads(
            content.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_object,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise AcceptanceRecordError(f"{label} is not strict UTF-8 JSON: {error}") from error

    _inspect_finite_json(value, label)
    return value


def _inspect_finite_json(value: object, label: str) -> None:
    def inspect(item: object, location: str) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise AcceptanceRecordError(
                f"{label} contains a non-finite JSON number at {location}"
            )
        if isinstance(item, list):
            for index, child in enumerate(item):
                inspect(child, f"{location}[{index}]")
        elif isinstance(item, Mapping):
            for key, child in item.items():
                inspect(child, f"{location}.{key}")

    inspect(value, "$")


def _schema_path(error: Any) -> str:
    return ".".join(str(part) for part in error.absolute_path) or "$"


def _format_checker() -> FormatChecker:
    """Return a fail-closed checker even without jsonschema format extras."""
    checker = FormatChecker()

    @checker.checks("date-time", raises=(TypeError, ValueError))
    def is_date_time(value: object) -> bool:
        return _parse_utc(value) is not None

    @checker.checks("uri", raises=(TypeError, ValueError))
    def is_uri(value: object) -> bool:
        if not isinstance(value, str):
            return False
        parsed = urlsplit(value)
        return bool(parsed.scheme and (parsed.netloc or parsed.scheme == "urn"))

    return checker


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or RFC3339_UTC.fullmatch(value) is None:
        return None
    normalized = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _schema_errors(record: object) -> list[str]:
    schema_path = Path(__file__).resolve().parent.parent / "packaging" / (
        "ACCEPTANCE_RECORD.schema.json"
    )
    schema = _load_json(schema_path, "acceptance-record schema")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=_format_checker())
    return [
        f"schema { _schema_path(error) }: {error.message}"
        for error in sorted(
            validator.iter_errors(record),
            key=lambda item: (list(item.absolute_path), item.message),
        )
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        mode = os.fstat(descriptor).st_mode
        if not stat.S_ISREG(mode):
            raise OSError(f"not a regular file: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _read_regular_file_once(path: Path, label: str) -> bytes:
    """Pin one regular-file descriptor and read its bytes exactly once."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise OSError(f"cannot open {label} {path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError(f"{label} is not a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _safe_artifact_path(root: Path, raw: object) -> tuple[Path | None, str | None]:
    if not isinstance(raw, str) or not raw:
        return None, "path must be a nonempty POSIX relative path"
    pure = PurePosixPath(raw)
    if (
        pure.is_absolute()
        or pure.as_posix() != raw
        or "\\" in raw
        or ":" in raw
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        return None, f"path is unsafe or escapes --run-root: {raw!r}"
    return root.joinpath(*pure.parts), None


def _check_no_symlink_components(root: Path, path: Path) -> str | None:
    current = root
    relative = path.relative_to(root)
    for index, component in enumerate(relative.parts):
        current = current / component
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            return "does not exist"
        except OSError as error:
            return f"cannot be inspected: {error}"
        if stat.S_ISLNK(metadata.st_mode):
            return f"contains a symbolic link component: {component!r}"
        if index + 1 < len(relative.parts) and not stat.S_ISDIR(metadata.st_mode):
            return f"has a non-directory parent component: {component!r}"
        if index + 1 == len(relative.parts) and not stat.S_ISREG(metadata.st_mode):
            return "is not a regular file"
    return None


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _read_run_root_relative(
    run_root: Path,
    root_descriptor: int,
    relative: PurePosixPath,
    label: str,
) -> bytes:
    """Read a confined path through pinned directory descriptors where supported."""
    if os.open not in os.supports_dir_fd:
        candidate = run_root.joinpath(*relative.parts)
        component_error = _check_no_symlink_components(run_root, candidate)
        if component_error is not None:
            raise OSError(f"{label} {component_error}")
        return _read_regular_file_once(candidate, label)

    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    current_descriptor = os.dup(root_descriptor)
    try:
        for component in relative.parts[:-1]:
            next_descriptor = os.open(
                component,
                directory_flags,
                dir_fd=current_descriptor,
            )
            os.close(current_descriptor)
            current_descriptor = next_descriptor
        file_flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(
            relative.parts[-1],
            file_flags,
            dir_fd=current_descriptor,
        )
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise OSError(f"{label} is not a regular file")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        finally:
            os.close(descriptor)
    finally:
        os.close(current_descriptor)


def _write_snapshot_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(content):
            offset += os.write(descriptor, content[offset:])
    finally:
        os.close(descriptor)


@contextmanager
def _capture_acceptance_snapshot(
    record_path: Path,
    run_root: Path,
    archive_path: Path,
) -> Iterator[_CapturedAcceptanceSnapshot]:
    """Capture every source byte once, then expose only a private temp tree."""
    source_record_path = _lexical_absolute(Path(record_path))
    source_run_root = _lexical_absolute(Path(run_root))
    source_archive_path = _lexical_absolute(Path(archive_path))
    try:
        record_content = _read_regular_file_once(
            source_record_path, "acceptance record"
        )
    except OSError as error:
        raise AcceptanceRecordError(str(error)) from error
    record_value = _load_json_bytes(record_content, "acceptance record")
    if not isinstance(record_value, Mapping):
        raise AcceptanceRecordError("acceptance record root must be a JSON object")
    record = record_value

    capture_errors: list[str] = []
    root_descriptor: int | None = None
    try:
        root_metadata = os.lstat(source_run_root)
        if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(
            root_metadata.st_mode
        ):
            capture_errors.append(
                "--run-root must be a real directory, not a symbolic link"
            )
        else:
            root_flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            root_descriptor = os.open(source_run_root, root_flags)
    except OSError as error:
        capture_errors.append(f"--run-root cannot be inspected: {error}")

    relative_contents: dict[str, bytes] = {}
    artifact_relatives: dict[str, str] = {}

    def capture_relative(raw: object, label: str) -> None:
        candidate, path_error = _safe_artifact_path(source_run_root, raw)
        if path_error is not None or candidate is None:
            return
        assert isinstance(raw, str)
        if raw in relative_contents or root_descriptor is None:
            return
        try:
            relative_contents[raw] = _read_run_root_relative(
                source_run_root,
                root_descriptor,
                PurePosixPath(raw),
                label,
            )
        except OSError as error:
            capture_errors.append(f"{label} cannot be snapshotted safely: {error}")

    raw_artifacts = record.get("artifacts")
    if isinstance(raw_artifacts, Mapping):
        for name, raw_binding in raw_artifacts.items():
            if not isinstance(name, str) or not isinstance(raw_binding, Mapping):
                continue
            raw_relative = raw_binding.get("path")
            if isinstance(raw_relative, str):
                artifact_relatives[name] = raw_relative
            capture_relative(raw_relative, f"artifacts.{name}")

    checksum_relative = artifact_relatives.get("sha256sums_file")
    checksum_content = (
        relative_contents.get(checksum_relative)
        if checksum_relative is not None
        else None
    )
    if checksum_content is not None:
        try:
            checksum_text = checksum_content.decode("utf-8")
        except UnicodeError:
            checksum_text = ""
        for line in checksum_text.splitlines(keepends=True):
            match = SHA256SUMS_LINE.fullmatch(line)
            if match is not None:
                capture_relative(match.group(2), "SHA256SUMS entry")

    deterministic_relative = artifact_relatives.get(
        "deterministic_package_record"
    )
    deterministic_content = (
        relative_contents.get(deterministic_relative)
        if deterministic_relative is not None
        else None
    )
    if deterministic_content is not None:
        try:
            deterministic_text = deterministic_content.decode("utf-8")
        except UnicodeError:
            deterministic_text = ""
        for line in deterministic_text.splitlines():
            if line.startswith("zip_b="):
                capture_relative(
                    line.removeprefix("zip_b="), "deterministic-package.zip_b"
                )

    if root_descriptor is not None:
        os.close(root_descriptor)

    delivery_relative = artifact_relatives.get("delivery_zip")
    claimed_candidate, delivery_path_error = _safe_artifact_path(
        source_run_root, delivery_relative
    )
    claimed_archive_path = (
        _lexical_absolute(claimed_candidate)
        if delivery_path_error is None and claimed_candidate is not None
        else None
    )
    archive_matches_delivery = claimed_archive_path == source_archive_path
    supplied_archive_content: bytes | None = None
    if record.get("status") == "PASS" and not archive_matches_delivery:
        try:
            supplied_archive_content = _read_regular_file_once(
                source_archive_path, "--archive"
            )
        except OSError as error:
            capture_errors.append(f"--archive cannot be snapshotted safely: {error}")

    artifact_contents = {
        name: relative_contents[relative]
        for name, relative in artifact_relatives.items()
        if relative in relative_contents
    }

    with tempfile.TemporaryDirectory(prefix="csc3-acceptance-snapshot-") as directory:
        snapshot_base = Path(directory)
        snapshot_root = snapshot_base / "run-root"
        snapshot_root.mkdir(mode=0o700)
        for relative, content in sorted(relative_contents.items()):
            try:
                _write_snapshot_file(
                    snapshot_root.joinpath(*PurePosixPath(relative).parts), content
                )
            except OSError as error:
                capture_errors.append(
                    f"snapshot path {relative!r} cannot be materialized: {error}"
                )
        if (
            archive_matches_delivery
            and delivery_relative is not None
            and delivery_path_error is None
        ):
            snapshot_archive_path = snapshot_root.joinpath(
                *PurePosixPath(delivery_relative).parts
            )
        else:
            snapshot_archive_path = snapshot_base / "supplied-archive.zip"
            if supplied_archive_content is not None:
                _write_snapshot_file(snapshot_archive_path, supplied_archive_content)

        yield _CapturedAcceptanceSnapshot(
            record=record,
            record_content=record_content,
            source_record_path=source_record_path,
            source_run_root=source_run_root,
            source_archive_path=source_archive_path,
            run_root=snapshot_root,
            archive_path=snapshot_archive_path,
            artifact_contents=MappingProxyType(artifact_contents),
            capture_errors=tuple(capture_errors),
        )


def _validate_artifacts(
    record: Mapping[str, object], root: Path, errors: list[str]
) -> dict[str, dict[str, object]]:
    verified: dict[str, dict[str, object]] = {}
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, Mapping):
        return verified
    try:
        root_metadata = os.lstat(root)
    except OSError as error:
        errors.append(f"--run-root cannot be inspected: {error}")
        return verified
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        errors.append("--run-root must be a real directory, not a symbolic link")
        return verified

    seen_paths: dict[str, str] = {}
    for name, raw_record in artifacts.items():
        label = f"artifacts.{name}"
        if not isinstance(name, str) or not isinstance(raw_record, Mapping):
            continue
        raw_path = raw_record.get("path")
        candidate, path_error = _safe_artifact_path(root, raw_path)
        if path_error is not None or candidate is None:
            errors.append(f"{label}.path {path_error}")
            continue
        assert isinstance(raw_path, str)
        previous = seen_paths.get(raw_path)
        if previous is not None:
            errors.append(
                f"duplicate artifact path {raw_path!r}: {previous} and {label}"
            )
            continue
        seen_paths[raw_path] = label
        component_error = _check_no_symlink_components(root, candidate)
        if component_error is not None:
            errors.append(f"{label} {component_error}: {raw_path}")
            continue
        try:
            actual_size = candidate.stat().st_size
            actual_digest = _sha256(candidate)
        except OSError as error:
            errors.append(f"{label} cannot be read safely: {error}")
            continue
        expected_size = raw_record.get("size_bytes")
        expected_digest = raw_record.get("sha256")
        if actual_size != expected_size:
            errors.append(
                f"{label} size mismatch: record={expected_size!r}, actual={actual_size}"
            )
        if actual_digest != expected_digest:
            errors.append(
                f"{label} SHA-256 mismatch: record={expected_digest!r}, "
                f"actual={actual_digest}"
            )
        verified[name] = {
            "path": candidate,
            "relative_path": raw_path,
            "size_bytes": actual_size,
            "sha256": actual_digest,
        }
    return verified


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _equal_number(actual: object, expected: object) -> bool:
    if (
        isinstance(actual, bool)
        or isinstance(expected, bool)
        or not isinstance(actual, (int, float))
        or not isinstance(expected, (int, float))
    ):
        return False
    return math.isclose(float(actual), float(expected), rel_tol=1.0e-12, abs_tol=1.0e-15)


def _expect_equal(
    errors: list[str], label: str, actual: object, expected: object, source: str
) -> None:
    if actual != expected:
        errors.append(f"{label} disagrees with {source}: {actual!r} != {expected!r}")


def _expect_number(
    errors: list[str], label: str, actual: object, expected: object, source: str
) -> None:
    if not _equal_number(actual, expected):
        errors.append(f"{label} disagrees with {source}: {actual!r} != {expected!r}")


def _json_artifact(
    artifact: Mapping[str, object] | None,
    label: str,
    errors: list[str],
) -> Mapping[str, object] | None:
    if artifact is None:
        return None
    try:
        document = _load_json(Path(artifact["path"]), label)
    except AcceptanceRecordError as error:
        errors.extend(error.errors)
        return None
    if not isinstance(document, Mapping):
        errors.append(f"{label} root must be a JSON object")
        return None
    return document


def _tail_json_object(
    artifact: Mapping[str, object] | None,
    label: str,
    errors: list[str],
) -> Mapping[str, object] | None:
    if artifact is None:
        return None
    try:
        text = Path(artifact["path"]).read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(f"{label} is not readable UTF-8: {error}")
        return None
    decoder = json.JSONDecoder(
        parse_constant=_reject_json_constant,
        object_pairs_hook=_reject_duplicate_object,
    )
    for offset in range(len(text) - 1, -1, -1):
        if text[offset] != "{":
            continue
        try:
            document, end = decoder.raw_decode(text, offset)
        except (json.JSONDecodeError, ValueError):
            continue
        if text[end:].strip():
            continue
        if not isinstance(document, Mapping):
            break
        try:
            _inspect_finite_json(document, label)
        except AcceptanceRecordError as error:
            errors.extend(error.errors)
            return None
        return document
    errors.append(f"{label} does not end with one valid JSON object")
    return None


def _validate_verifier_result(
    document: Mapping[str, object] | None,
    *,
    label: str,
    clean_room_executed: bool,
    source_commit: object,
    delivery_zip: Mapping[str, object] | None,
    errors: list[str],
) -> None:
    if document is None:
        return
    expected_fields = {
        "status": "PASS",
        "clean_room_executed": clean_room_executed,
        "source_commit": source_commit,
        "evidence_source_commit": source_commit,
        "evidence_source_matches_package_source": True,
        "distribution": "INTERNAL EVALUATION ONLY",
    }
    for field, expected in expected_fields.items():
        actual = document.get(field)
        if actual != expected:
            rendered_expected = (
                str(expected).lower() if isinstance(expected, bool) else repr(expected)
            )
            source_note = (
                " from the acceptance record"
                if field in {"source_commit", "evidence_source_commit"}
                else ""
            )
            errors.append(
                f"{label}.{field} must be {rendered_expected}{source_note}; "
                f"found {actual!r}"
            )
    if delivery_zip is not None and document.get("archive_sha256") != delivery_zip.get(
        "sha256"
    ):
        errors.append(f"{label}.archive_sha256 does not match the delivery ZIP")


def _validate_sha256sums(
    run_root: Path,
    artifacts: Mapping[str, Mapping[str, object]],
    errors: list[str],
) -> None:
    checksum_artifact = artifacts.get("sha256sums_file")
    if checksum_artifact is None:
        return
    try:
        content = Path(checksum_artifact["path"]).read_bytes()
        text = content.decode("utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(f"SHA256SUMS cannot be read as UTF-8: {error}")
        return
    if not text or "\r" in text or not text.endswith("\n"):
        errors.append("SHA256SUMS must be nonempty canonical LF text")
        return
    entries: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        match = SHA256SUMS_LINE.fullmatch(line)
        if match is None:
            errors.append(
                f"SHA256SUMS line {line_number} is not canonical '<sha>  <relative>'"
            )
            continue
        expected_digest, relative = match.groups()
        if relative in entries:
            errors.append(f"SHA256SUMS has duplicate path {relative!r}")
            continue
        candidate, path_error = _safe_artifact_path(run_root, relative)
        if path_error is not None or candidate is None:
            errors.append(f"SHA256SUMS has unsafe path {relative!r}: {path_error}")
            continue
        component_error = _check_no_symlink_components(run_root, candidate)
        if component_error is not None:
            errors.append(f"SHA256SUMS path {relative!r} {component_error}")
            continue
        try:
            actual_digest = _sha256(candidate)
        except OSError as error:
            errors.append(f"SHA256SUMS path {relative!r} cannot be hashed: {error}")
            continue
        if actual_digest != expected_digest:
            errors.append(
                f"SHA256SUMS path {relative!r} SHA-256 mismatch: "
                f"listed={expected_digest}, actual={actual_digest}"
            )
        entries[relative] = expected_digest

    for name, artifact in artifacts.items():
        if name == "sha256sums_file":
            continue
        relative = artifact.get("relative_path")
        if not isinstance(relative, str):
            continue
        if relative not in entries:
            errors.append(f"SHA256SUMS is missing artifacts.{name} path {relative!r}")
        elif entries[relative] != artifact.get("sha256"):
            errors.append(
                f"SHA256SUMS entry for artifacts.{name} disagrees with its artifact SHA-256"
            )


def _validate_deterministic_package(
    run_root: Path,
    artifact: Mapping[str, object] | None,
    delivery_zip: Mapping[str, object] | None,
    errors: list[str],
) -> None:
    if artifact is None or delivery_zip is None:
        return
    try:
        text = Path(artifact["path"]).read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(f"deterministic-package record is not readable UTF-8: {error}")
        return
    lines = text.splitlines(keepends=True)
    expected_keys = ("status", "zip_a", "zip_b", "sha256")
    values: dict[str, str] = {}
    if len(lines) != len(expected_keys) or any(not line.endswith("\n") for line in lines):
        errors.append("deterministic-package record must contain exactly four LF lines")
        return
    for expected_key, line in zip(expected_keys, lines):
        raw = line[:-1]
        key, separator, value = raw.partition("=")
        if separator != "=" or key != expected_key or not value:
            errors.append(
                "deterministic-package record must use ordered status, zip_a, zip_b, "
                "sha256 fields"
            )
            return
        values[key] = value
    if values["status"] != "PASS":
        errors.append("deterministic-package.status must be PASS")
    delivery_relative = delivery_zip.get("relative_path")
    delivery_digest = delivery_zip.get("sha256")
    if values["zip_a"] != delivery_relative:
        errors.append("deterministic-package.zip_a must equal the delivery ZIP path")
    if values["sha256"] != delivery_digest:
        errors.append("deterministic-package.sha256 must equal the delivery ZIP SHA-256")

    zip_a = PurePosixPath(str(values["zip_a"]))
    expected_zip_b = (
        f"dist-b/{zip_a.name}" if len(zip_a.parts) >= 2 and zip_a.parts[0] == "dist-a" else None
    )
    if expected_zip_b is None or values["zip_b"] != expected_zip_b:
        errors.append(
            "deterministic-package.zip_b must be dist-b/<delivery ZIP filename>"
        )
    zip_b_path, path_error = _safe_artifact_path(run_root, values["zip_b"])
    if path_error is not None or zip_b_path is None:
        errors.append(f"deterministic-package.zip_b is unsafe: {path_error}")
        return
    component_error = _check_no_symlink_components(run_root, zip_b_path)
    if component_error is not None:
        errors.append(f"deterministic-package.zip_b {component_error}")
        return
    try:
        zip_b_digest = _sha256(zip_b_path)
        zip_b_size = zip_b_path.stat().st_size
    except OSError as error:
        errors.append(f"deterministic-package.zip_b cannot be verified: {error}")
        return
    if zip_b_digest != delivery_digest or zip_b_size != delivery_zip.get("size_bytes"):
        errors.append("deterministic-package.zip_b bytes do not equal the delivery ZIP")


def _validate_outcome_record(
    record: Mapping[str, object],
    artifacts: Mapping[str, Mapping[str, object]],
    errors: list[str],
) -> Mapping[str, object] | None:
    outcome = _json_artifact(artifacts.get("outcome_record"), "outcome_record", errors)
    if outcome is None:
        return None
    record_status = record.get("status")
    if record_status == "PASS":
        expected_status = "PACKAGE_CANDIDATE"
        if _parse_utc(outcome.get("candidate_completed_at_utc")) is None:
            errors.append(
                "outcome_record.candidate_completed_at_utc must be a valid UTC "
                "timestamp for PASS"
            )
        if outcome.get("phase") != "automated-candidate-complete":
            errors.append("outcome_record.phase must be automated-candidate-complete")
        exit_code = outcome.get("exit_code")
        if isinstance(exit_code, bool) or exit_code != 0:
            errors.append("outcome_record.exit_code must be zero")
    else:
        expected_status = record_status
        if outcome.get("candidate_completed_at_utc") is not None:
            errors.append(
                "non-PASS outcome_record.candidate_completed_at_utc must be null"
            )
        if outcome.get("phase") == "automated-candidate-complete":
            errors.append(
                "non-PASS outcome_record.phase cannot be automated-candidate-complete"
            )
        exit_code = outcome.get("exit_code")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code == 0:
            errors.append("non-PASS outcome_record.exit_code must be nonzero")
        reason = outcome.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append("non-PASS outcome_record.reason must be nonblank")
    if outcome.get("status") != expected_status:
        errors.append(
            "outcome_record.status disagrees with acceptance record status: "
            f"expected {expected_status!r}, found {outcome.get('status')!r}"
        )
    return outcome


def _validate_candidate_lifecycle(
    record: Mapping[str, object],
    run_root: Path,
    artifacts: Mapping[str, Mapping[str, object]],
    errors: list[str],
) -> Mapping[str, object] | None:
    source_commit = record.get("source_commit")
    delivery_zip = artifacts.get("delivery_zip")

    _validate_sha256sums(run_root, artifacts, errors)
    _validate_deterministic_package(
        run_root,
        artifacts.get("deterministic_package_record"),
        delivery_zip,
        errors,
    )
    manifest_only = _json_artifact(
        artifacts.get("manifest_only_verifier_output"),
        "manifest-only verifier output",
        errors,
    )
    _validate_verifier_result(
        manifest_only,
        label="manifest-only verifier output",
        clean_room_executed=False,
        source_commit=source_commit,
        delivery_zip=delivery_zip,
        errors=errors,
    )
    clean_room = _tail_json_object(
        artifacts.get("clean_room_verifier_log"),
        "clean-room verifier log",
        errors,
    )
    _validate_verifier_result(
        clean_room,
        label="clean-room verifier log",
        clean_room_executed=True,
        source_commit=source_commit,
        delivery_zip=delivery_zip,
        errors=errors,
    )
    return clean_room


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_deviation_status_mapping(
    record: Mapping[str, object], errors: list[str]
) -> None:
    status = record.get("status")
    deviations = record.get("deviations")
    if not isinstance(deviations, list):
        return
    for index, raw_deviation in enumerate(deviations):
        deviation = _mapping(raw_deviation)
        disposition = deviation.get("disposition")
        prefix = f"deviations[{index}]"
        if disposition == "ACCEPTED_INTERNAL_ONLY":
            if not _nonblank(deviation.get("approval_reference")):
                errors.append(
                    f"{prefix}.approval_reference must be nonblank for "
                    "ACCEPTED_INTERNAL_ONLY"
                )
        elif disposition == "REJECTED" and status != "FAIL":
            errors.append(
                f"{prefix}.disposition REJECTED requires overall status FAIL"
            )
        elif disposition == "OPEN_BLOCKER" and status != "BLOCKED":
            errors.append(
                f"{prefix}.disposition OPEN_BLOCKER requires overall status BLOCKED"
            )


def _preflight_sections(
    artifact: Mapping[str, object] | None, errors: list[str]
) -> dict[str, str]:
    if artifact is None:
        return {}
    try:
        text = Path(artifact["path"]).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(f"host-preflight is not readable UTF-8: {error}")
        return {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:]
            if current in sections:
                errors.append(f"host-preflight has duplicate section {current!r}")
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return {
        name: next((line.strip() for line in lines if line.strip()), "")
        for name, lines in sections.items()
    }


def _bind_toolchain_to_preflight(
    record: Mapping[str, object],
    sections: Mapping[str, str],
    errors: list[str],
) -> None:
    toolchain = _mapping(record.get("toolchain"))
    patterns = {
        "compiler_version": ("compiler", r"(?:^|\s)(\d+(?:\.\d+)+)(?:[-\s]|$)"),
        "cmake_version": ("CMake", r"^cmake version (\S+)$"),
        "ninja_version": ("Ninja", r"^(\S+)$"),
        "python_version": ("Python", r"^Python (\S+)$"),
        "git_version": ("Git", r"^git version (\S+)$"),
        "git_lfs_version": ("Git LFS", r"^git-lfs/(\S+?)(?:\s|$)"),
    }
    observed: dict[str, str] = {}
    for field, (section, pattern) in patterns.items():
        line = sections.get(section, "")
        match = re.search(pattern, line)
        if match is None:
            errors.append(
                f"host-preflight section {section!r} does not expose {field}"
            )
            continue
        observed[field] = match.group(1)
        _expect_equal(
            errors,
            f"toolchain.{field}",
            toolchain.get(field),
            observed[field],
            "host-preflight",
        )

    compiler = toolchain.get("compiler")
    if compiler not in {"GCC", "GNU"}:
        errors.append("toolchain.compiler must identify GCC/GNU on the formal Linux host")
    for field, minimum in (
        ("compiler_version", (9, 0)),
        ("cmake_version", (3, 21)),
        ("python_version", (3, 11)),
    ):
        raw = observed.get(field)
        if raw is None:
            continue
        match = re.match(r"^(\d+)\.(\d+)", raw)
        if match is None or tuple(int(value) for value in match.groups()) < minimum:
            errors.append(
                f"toolchain.{field} does not meet the formal minimum "
                f"{minimum[0]}.{minimum[1]}"
            )


def _quiet_checked(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        tail = completed.stdout[-8000:]
        raise RuntimeError(
            "clean-room command failed with exit code "
            f"{completed.returncode}: {command!r}\n{tail}"
        )


def _validate_pass_record(
    record: Mapping[str, object],
    run_root: Path,
    archive_path: Path,
    artifacts: Mapping[str, Mapping[str, object]],
    outcome: Mapping[str, object] | None,
    errors: list[str],
) -> int:
    controlled_host = _mapping(record.get("controlled_host"))
    input_facts = _mapping(record.get("input"))
    execution = _mapping(record.get("execution"))
    correctness = _mapping(record.get("correctness"))
    performance = _mapping(record.get("performance"))
    verifications = _mapping(record.get("verifications"))
    approvals = _mapping(record.get("approvals"))
    source_commit = record.get("source_commit")
    delivery_zip = artifacts.get("delivery_zip")

    if controlled_host.get("cpu_vendor") != "GenuineIntel":
        errors.append("controlled_host.cpu_vendor must be exactly 'GenuineIntel'")
    if input_facts.get("sha256") != input_facts.get("head_lfs_oid_sha256"):
        errors.append("input SHA-256 does not equal the HEAD LFS object SHA-256")
    if input_facts.get("size_bytes") != input_facts.get("head_lfs_size_bytes"):
        errors.append("input size does not equal the HEAD LFS object size")

    for case_name in ("tet4", "hex8"):
        case = _mapping(correctness.get(case_name))
        scale = case.get("maximum_absolute_serial_entry")
        recorded_tolerance = case.get("maximum_absolute_error_tolerance")
        if isinstance(scale, (int, float)) and not isinstance(scale, bool):
            expected_tolerance = (
                MAXIMUM_ABSOLUTE_BASE_TOLERANCE
                + MAXIMUM_ABSOLUTE_SCALE_TOLERANCE * float(scale)
            )
            if not _equal_number(recorded_tolerance, expected_tolerance):
                errors.append(
                    f"correctness.{case_name} maximum-absolute tolerance does not "
                    "equal 1e-10 + 1e-8 * maximum_absolute_serial_entry"
                )
            error_value = case.get("maximum_absolute_error")
            if (
                isinstance(error_value, (int, float))
                and not isinstance(error_value, bool)
                and float(error_value) > expected_tolerance
            ):
                errors.append(
                    f"correctness.{case_name}.maximum_absolute_error exceeds its "
                    "recomputed scale-aware tolerance"
                )

    for name in (
        "operator",
        "technical_reviewer",
        "delivery_approver",
        "recipient_acknowledgement",
    ):
        approval = _mapping(approvals.get(name))
        if approval.get("acknowledgement") != "ACKNOWLEDGED":
            errors.append(f"approvals.{name} must be ACKNOWLEDGED for PASS")
        for field in ("identity_reference", "approval_record_reference"):
            if not _nonblank(approval.get(field)):
                errors.append(f"approvals.{name}.{field} must be nonblank for PASS")
        identity = approval.get("identity_reference")
        approval_reference = approval.get("approval_record_reference")
        if (
            _nonblank(identity)
            and _nonblank(approval_reference)
            and str(identity) not in str(approval_reference)
        ):
            errors.append(
                f"approvals.{name}.approval_record_reference does not bind its "
                "identity_reference"
            )
        expected_candidate_fields = {
            "delivery_id": record.get("delivery_id"),
            "source_commit": source_commit,
            "archive_filename": (
                Path(str(delivery_zip.get("relative_path"))).name
                if delivery_zip is not None
                else None
            ),
            "archive_sha256": (
                delivery_zip.get("sha256") if delivery_zip is not None else None
            ),
            "candidate_status": "PACKAGE_CANDIDATE",
            "clean_room_status": "PASS",
        }
        for field, expected in expected_candidate_fields.items():
            _expect_equal(
                errors,
                f"approvals.{name}.{field}",
                approval.get(field),
                expected,
                "the candidate",
            )
    for party_name in ("recipient", "operator", "technical_reviewer"):
        party_record = _mapping(record.get(party_name))
        for field in ("organization", "department", "identity_reference"):
            if not _nonblank(party_record.get(field)):
                errors.append(f"{party_name}.{field} must be nonblank for PASS")

    execution_ended = _parse_utc(execution.get("ended_at_utc"))
    candidate_completed = _parse_utc(
        outcome.get("candidate_completed_at_utc") if outcome is not None else None
    )
    now = datetime.now(timezone.utc)
    if (
        execution_ended is not None
        and candidate_completed is not None
        and candidate_completed < execution_ended
    ):
        errors.append(
            "outcome_record.candidate_completed_at_utc is before "
            "execution.ended_at_utc"
        )
    if candidate_completed is not None and candidate_completed > now:
        errors.append("outcome_record.candidate_completed_at_utc is in the future")
    for name in (
        "operator",
        "technical_reviewer",
        "delivery_approver",
        "recipient_acknowledgement",
    ):
        acknowledged = _parse_utc(
            _mapping(approvals.get(name)).get("acknowledged_at_utc")
        )
        if (
            acknowledged is not None
            and execution_ended is not None
            and acknowledged < execution_ended
        ):
            errors.append(
                f"approvals.{name}.acknowledged_at_utc is before "
                "execution.ended_at_utc"
            )
        if (
            acknowledged is not None
            and candidate_completed is not None
            and acknowledged <= candidate_completed
        ):
            errors.append(
                f"approvals.{name}.acknowledged_at_utc must be strictly later than "
                "the candidate completion time"
            )
        if acknowledged is not None and acknowledged > now:
            errors.append(f"approvals.{name}.acknowledged_at_utc is in the future")
    for approval_name, party_name in (
        ("operator", "operator"),
        ("technical_reviewer", "technical_reviewer"),
        ("recipient_acknowledgement", "recipient"),
    ):
        approval = _mapping(approvals.get(approval_name))
        party = _mapping(record.get(party_name))
        if approval.get("identity_reference") != party.get("identity_reference"):
            errors.append(
                f"approvals.{approval_name}.identity_reference does not match "
                f"the {party_name} identity_reference"
            )

    ctest = _mapping(verifications.get("ctest"))
    expected_ctest_fields = {
        "status": "PASS",
        "test_count": 10,
        "failed_count": 0,
        "skipped_count": 0,
        "not_run_count": 0,
        "test_names": list(EXPECTED_TESTS),
    }
    for field, expected in expected_ctest_fields.items():
        _expect_equal(
            errors,
            f"verifications.ctest.{field}",
            ctest.get(field),
            expected,
            "the exact ten-test acceptance contract",
        )

    host_preflight = artifacts.get("host_preflight")
    if host_preflight is not None:
        _expect_equal(
            errors,
            "controlled_host.preflight_sha256",
            controlled_host.get("preflight_sha256"),
            host_preflight.get("sha256"),
            "artifacts.host_preflight",
        )
        preflight = _preflight_sections(host_preflight, errors)
        _expect_equal(
            errors,
            "controlled_host.cpu_vendor",
            controlled_host.get("cpu_vendor"),
            preflight.get("observed CPU vendor"),
            "host-preflight",
        )
        _bind_toolchain_to_preflight(record, preflight, errors)

    source_file = artifacts.get("source_commit_file")
    if source_file is not None:
        try:
            source_text = Path(source_file["path"]).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            errors.append(f"artifacts.source_commit_file is unreadable: {error}")
        else:
            if source_text != f"{source_commit}\n":
                errors.append(
                    "artifacts.source_commit_file does not contain exactly the record "
                    "source commit followed by LF"
                )

    delivery_zip = artifacts.get("delivery_zip")
    archive_matches_record = False
    if delivery_zip is not None:
        if archive_path.is_symlink():
            errors.append("--archive must not be a symbolic link")
        try:
            supplied = archive_path.resolve(strict=False)
            claimed = Path(delivery_zip["path"]).resolve(strict=False)
            archive_matches_record = supplied == claimed
        except OSError as error:
            errors.append(f"--archive cannot be resolved safely: {error}")
        if not archive_matches_record:
            errors.append("--archive does not equal artifacts.delivery_zip path")

    recorded_clean_room = _validate_candidate_lifecycle(
        record, run_root, artifacts, errors
    )

    run_manifest = artifacts.get("run_manifest")
    report_artifact = artifacts.get("canonical_markdown_report")
    samples_artifact = artifacts.get("benchmark_samples")
    summary_artifact = artifacts.get("benchmark_summary")
    evidence_bundle: object | None = None
    if run_manifest is not None:
        _json_artifact(run_manifest, "run_manifest", errors)
        _json_artifact(summary_artifact, "benchmark_summary", errors)
        reporter = _load_sibling(
            "generate_test_report.py", "csc3_acceptance_report_evidence"
        )
        try:
            evidence_bundle = reporter.validate_evidence_bundle(
                Path(run_manifest["path"])
            )
        except Exception as error:  # helper translates every evidence defect
            errors.append(f"run_manifest evidence validation failed: {error}")

    ctest_count = 0
    if evidence_bundle is not None:
        bundle = evidence_bundle
        manifest = _mapping(bundle.manifest)
        manifest_source = _mapping(manifest.get("source"))
        manifest_input = _mapping(manifest.get("input"))
        manifest_environment = _mapping(manifest.get("environment"))
        manifest_benchmark = _mapping(manifest.get("benchmark"))
        manifest_toolchain = _mapping(manifest.get("toolchain"))
        manifest_openmp = _mapping(manifest_toolchain.get("openmp"))
        acceptance_toolchain = _mapping(record.get("toolchain"))
        _expect_equal(
            errors,
            "run_manifest source commit",
            manifest_source.get("commit_sha"),
            source_commit,
            "acceptance record source_commit",
        )
        for field in (
            "repository_relative_path",
            "size_bytes",
            "sha256",
            "tracked",
            "materialized",
            "matches_head_lfs",
            "head_lfs_oid_sha256",
            "head_lfs_size_bytes",
        ):
            _expect_equal(
                errors,
                f"input.{field}",
                input_facts.get(field),
                manifest_input.get(field),
                "run_manifest input",
            )
        for field in (
            "system",
            "architecture",
            "hostname",
            "cpu_vendor",
            "cpu_model",
            "physical_core_count",
            "logical_core_count",
            "total_memory_bytes",
            "controlled_host_id",
        ):
            _expect_equal(
                errors,
                f"controlled_host.{field}",
                controlled_host.get(field),
                manifest_environment.get(field),
                "run_manifest environment",
            )
        for record_field, manifest_field in (
            ("warmup_count", "warmup_count"),
            ("repeat_count", "repeat_count"),
            ("amortization_count", "amortization_count"),
            ("requested_thread_counts", "requested_thread_counts"),
        ):
            _expect_equal(
                errors,
                f"execution.{record_field}",
                execution.get(record_field),
                manifest_benchmark.get(manifest_field),
                "run_manifest benchmark",
            )
        for field in ("started_at_utc", "ended_at_utc"):
            _expect_equal(
                errors,
                f"execution.{field}",
                execution.get(field),
                manifest.get(field),
                "run_manifest",
            )
        _expect_equal(
            errors,
            "toolchain.openmp_found",
            acceptance_toolchain.get("openmp_found"),
            manifest_openmp.get("found"),
            "run_manifest toolchain",
        )
        _expect_equal(
            errors,
            "toolchain.openmp_required",
            acceptance_toolchain.get("openmp_required"),
            manifest_openmp.get("require_openmp"),
            "run_manifest toolchain",
        )
        compiler_id = manifest_toolchain.get("compiler_id")
        accepted_compiler_labels = {compiler_id}
        if compiler_id == "GNU":
            accepted_compiler_labels.add("GCC")
        if acceptance_toolchain.get("compiler") not in accepted_compiler_labels:
            errors.append(
                "toolchain.compiler disagrees with run_manifest toolchain: "
                f"{acceptance_toolchain.get('compiler')!r} is not one of "
                f"{sorted(str(value) for value in accepted_compiler_labels)!r}"
            )
        for record_field, manifest_value in (
            ("compiler_version", manifest_toolchain.get("compiler_version")),
            ("cmake_version", manifest_toolchain.get("cmake_version")),
            ("python_version", manifest_environment.get("python_version")),
        ):
            _expect_equal(
                errors,
                f"toolchain.{record_field}",
                acceptance_toolchain.get(record_field),
                manifest_value,
                "run_manifest toolchain/environment",
            )

        reporter_artifacts = bundle.artifact_paths
        for acceptance_name, evidence_name in (
            ("ctest_junit", "ctest.xml"),
            ("benchmark_samples", "benchmark_samples.csv"),
            ("benchmark_summary", "benchmark_summary.json"),
            ("evidence_summary", "summary.md"),
        ):
            acceptance_artifact = artifacts.get(acceptance_name)
            evidence_path = reporter_artifacts.get(evidence_name)
            if acceptance_artifact is not None and evidence_path is not None:
                if Path(acceptance_artifact["path"]).resolve() != evidence_path.resolve():
                    errors.append(
                        f"artifacts.{acceptance_name} is not the artifact bound by "
                        "run_manifest"
                    )

        ctest_count = len(bundle.junit_testcase_names)
        if tuple(bundle.junit_testcase_names) != EXPECTED_TESTS:
            errors.append("ctest.xml does not contain the exact ten ordered CTest names")
        if ctest.get("test_names") != list(bundle.junit_testcase_names):
            errors.append("verifications.ctest.test_names disagrees with ctest.xml")
        if ctest.get("test_count") != ctest_count:
            errors.append("verifications.ctest.test_count disagrees with ctest.xml")

        if report_artifact is not None:
            try:
                expected_report = reporter.render_report(bundle).encode("utf-8")
                actual_report = Path(report_artifact["path"]).read_bytes()
            except (OSError, UnicodeError, RuntimeError, ValueError) as error:
                errors.append(f"canonical Markdown report cannot be recomputed: {error}")
            else:
                if actual_report != expected_report:
                    errors.append(
                        "canonical Markdown report does not equal the report recomputed "
                        "from evidence"
                    )

        if samples_artifact is not None:
            _expect_equal(
                errors,
                "performance.samples_sha256",
                performance.get("samples_sha256"),
                samples_artifact.get("sha256"),
                "artifacts.benchmark_samples",
            )
        if summary_artifact is not None:
            _expect_equal(
                errors,
                "performance.summary_sha256",
                performance.get("summary_sha256"),
                summary_artifact.get("sha256"),
                "artifacts.benchmark_summary",
            )
        _expect_equal(
            errors,
            "performance.raw_sample_count",
            performance.get("raw_sample_count"),
            len(bundle.csv_rows),
            "CSV row count",
        )

        summary = _mapping(bundle.benchmark_summary)
        validation_cases = summary.get("validation_cases")
        if isinstance(validation_cases, list):
            by_type = {
                str(_mapping(case).get("element_type", "")).lower(): _mapping(case)
                for case in validation_cases
            }
            for case_name in ("tet4", "hex8"):
                evidence_case = by_type.get(case_name, {})
                matrix = _mapping(evidence_case.get("matrix"))
                displacement = _mapping(evidence_case.get("displacement"))
                acceptance_case = _mapping(correctness.get(case_name))
                expected_values = {
                    "frobenius_relative_error": matrix.get(
                        "relative_frobenius_error"
                    ),
                    "maximum_absolute_error": matrix.get("max_absolute_error"),
                    "maximum_absolute_serial_entry": matrix.get(
                        "reference_max_absolute_value"
                    ),
                    "maximum_absolute_error_tolerance": matrix.get(
                        "max_absolute_tolerance"
                    ),
                    "displacement_relative_error": displacement.get(
                        "relative_displacement_error"
                    ),
                    "relative_residual": displacement.get(
                        "parallel_relative_residual"
                    ),
                }
                for field, expected in expected_values.items():
                    _expect_number(
                        errors,
                        f"correctness.{case_name}.{field}",
                        acceptance_case.get(field),
                        expected,
                        "benchmark summary",
                    )

        rows = _mapping(bundle.recomputed_statistics).get("per_thread")
        if isinstance(rows, tuple):
            by_thread = {
                _mapping(row).get("thread_count"): _mapping(row) for row in rows
            }
            gate = _mapping(bundle.recomputed_gate)
            for prefix, phase in (
                ("numeric", "numeric_algorithm_ms"),
                ("symbolic", "symbolic_total_ms"),
            ):
                thread = gate.get(f"{prefix}_thread_count")
                row = by_thread.get(thread, {})
                _expect_equal(
                    errors,
                    f"performance.{prefix}_thread_count",
                    performance.get(f"{prefix}_thread_count"),
                    thread,
                    "recomputed performance gate",
                )
                _expect_number(
                    errors,
                    f"performance.{prefix}_speedup",
                    performance.get(f"{prefix}_speedup"),
                    row.get(f"{prefix}_speedup"),
                    "recomputed samples",
                )
                phase_values = _mapping(row.get(phase))
                _expect_number(
                    errors,
                    f"performance.{prefix}_coefficient_of_variation",
                    performance.get(f"{prefix}_coefficient_of_variation"),
                    phase_values.get("coefficient_of_variation"),
                    "recomputed samples",
                )

    if delivery_zip is not None and archive_matches_record:
        verifier = _load_sibling(
            "verify_delivery_package.py", "csc3_acceptance_package_verifier"
        )
        verification_result: Mapping[str, object] | None = None
        try:
            verification_result = verifier.verify_delivery_package(
                archive_path, run_clean_room=False
            )
        except Exception as error:  # archive parser has several precise failure types
            errors.append(f"delivery archive manifest verification failed: {error}")
        if verification_result is not None:
            _expect_equal(
                errors,
                "delivery archive source commit",
                verification_result.get("source_commit"),
                source_commit,
                "acceptance record source_commit",
            )
            _expect_equal(
                errors,
                "delivery archive evidence source commit",
                verification_result.get("evidence_source_commit"),
                source_commit,
                "acceptance record source_commit",
            )
            if verification_result.get("evidence_source_matches_package_source") is not True:
                errors.append(
                    "delivery archive BUILD_INFO does not bind evidence source to "
                    "package source"
                )
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    build_info_members = [
                        name for name in archive.namelist() if name.endswith("/BUILD_INFO.json")
                    ]
                    if len(build_info_members) != 1:
                        raise RuntimeError("archive must contain exactly one BUILD_INFO.json")
                    build_info = json.loads(
                        archive.read(build_info_members[0]).decode("utf-8"),
                        parse_constant=_reject_json_constant,
                        object_pairs_hook=_reject_duplicate_object,
                    )
                    _inspect_finite_json(
                        build_info, "delivery archive BUILD_INFO"
                    )
            except Exception as error:
                errors.append(f"delivery archive BUILD_INFO cannot be read: {error}")
            else:
                if run_manifest is not None:
                    _expect_equal(
                        errors,
                        "delivery archive BUILD_INFO evidence_manifest_sha256",
                        build_info.get("evidence_manifest_sha256"),
                        run_manifest.get("sha256"),
                        "artifacts.run_manifest",
                    )
                if report_artifact is not None:
                    _expect_equal(
                        errors,
                        "delivery archive BUILD_INFO report_sha256",
                        build_info.get("report_sha256"),
                        report_artifact.get("sha256"),
                        "artifacts.canonical_markdown_report",
                    )
        if not errors:
            try:
                clean_room_result = verifier.verify_delivery_package(
                    archive_path,
                    run_clean_room=True,
                    command_runner=_quiet_checked,
                )
            except Exception as error:
                errors.append(f"independent clean-room verification failed: {error}")
            else:
                if recorded_clean_room is None:
                    errors.append(
                        "independent clean-room result has no recorded clean-room "
                        "evidence to cross-check"
                    )
                else:
                    for field in (
                        "status",
                        "archive_sha256",
                        "source_commit",
                        "evidence_source_commit",
                        "evidence_source_matches_package_source",
                        "distribution",
                        "verified_file_count",
                        "clean_room_executed",
                    ):
                        _expect_equal(
                            errors,
                            f"clean-room reexecution.{field}",
                            clean_room_result.get(field),
                            recorded_clean_room.get(field),
                            "recorded clean-room verifier log",
                        )
    return ctest_count


def _validate_captured_acceptance_snapshot(
    snapshot: _CapturedAcceptanceSnapshot,
) -> dict[str, object]:
    record = snapshot.record
    errors = _schema_errors(record) + list(snapshot.capture_errors)
    _validate_deviation_status_mapping(record, errors)
    artifacts = _validate_artifacts(record, snapshot.run_root, errors)
    outcome = _validate_outcome_record(record, artifacts, errors)
    ctest_count = 0
    if record.get("status") == "PASS":
        ctest_count = _validate_pass_record(
            record,
            snapshot.run_root,
            snapshot.archive_path,
            artifacts,
            outcome,
            errors,
        )
    if errors:
        raise AcceptanceRecordError(errors)
    return {
        "status": record["status"],
        "source_commit": record["source_commit"],
        "record": str(snapshot.source_record_path),
        "run_root": str(snapshot.source_run_root),
        "archive": (
            str(snapshot.source_archive_path)
            if record.get("status") == "PASS"
            else None
        ),
        "artifact_count": len(artifacts),
        "ctest_count": ctest_count,
    }


@contextmanager
def validated_acceptance_snapshot(
    record_path: Path,
    run_root: Path,
    archive_path: Path,
) -> Iterator[ValidatedAcceptanceSnapshot]:
    """Yield validated bytes that never need to be read again from source paths."""
    with _capture_acceptance_snapshot(
        Path(record_path), Path(run_root), Path(archive_path)
    ) as captured:
        result = _validate_captured_acceptance_snapshot(captured)
        archive_content = (
            captured.artifact_contents.get("delivery_zip")
            if captured.record.get("status") == "PASS"
            else None
        )
        yield ValidatedAcceptanceSnapshot(
            result=MappingProxyType(result),
            record=captured.record,
            record_content=captured.record_content,
            archive_content=archive_content,
            artifact_contents=captured.artifact_contents,
        )


def validate_acceptance_record(
    record_path: Path,
    run_root: Path,
    archive_path: Path,
) -> dict[str, object]:
    """Validate a record or raise one aggregated :class:`AcceptanceRecordError`."""
    with validated_acceptance_snapshot(record_path, run_root, archive_path) as snapshot:
        return dict(snapshot.result)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = _argument_parser().parse_args(arguments)
    try:
        result = validate_acceptance_record(
            options.record,
            options.run_root,
            options.archive,
        )
    except (AcceptanceRecordError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
