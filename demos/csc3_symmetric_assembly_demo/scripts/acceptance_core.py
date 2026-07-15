#!/usr/bin/env python3
"""Immutable candidate capture and objective fact derivation for CSC3 acceptance."""

from __future__ import annotations

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
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType, ModuleType


MACHINE_FACTS_SCHEMA = "ACCEPTANCE_MACHINE_FACTS.schema.json"
MACHINE_FACTS_VERSION = "csc3-demo-acceptance-machine-facts-v1"
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
SHA256SUMS_LINE = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)\n$")
RFC3339_UTC = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?Z$"
)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
GENERIC_OBJECTIVE_PLACEHOLDERS = {
    "n/a",
    "none",
    "not applicable",
    "not available",
    "placeholder",
    "required before delivery",
    "tbd",
    "todo",
    "unknown",
    "unavailable",
}
OBJECTIVE_PENDING_PREFIX = re.compile(
    r"^(?:tbd|todo|required\ before\ delivery)(?:\s|\()",
    re.IGNORECASE,
)
OBJECTIVE_SENTINEL = re.compile(r"^<[^<>\r\n]+>$")


class AcceptanceCandidateError(RuntimeError):
    """Raised when a package candidate cannot be frozen safely."""


class _FrozenDict(dict):
    """JSON-serializable mapping that rejects every mutation."""

    @staticmethod
    def _immutable(*_args: object, **_kwargs: object) -> None:
        raise TypeError("validated candidate facts are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


@dataclass(frozen=True)
class ValidatedCandidateSnapshot:
    machine_facts: Mapping[str, object]
    machine_facts_content: bytes
    archive_content: bytes
    artifact_contents: Mapping[str, bytes]
    relative_contents: Mapping[str, bytes]


@dataclass(frozen=True)
class _CapturedCandidate:
    source_run_root: Path
    source_archive_path: Path
    run_root: Path
    archive_path: Path
    archive_relative: str
    archive_content: bytes
    zip_b_relative: str
    zip_b_content: bytes
    sha256sums_content: bytes
    relative_contents: Mapping[str, bytes]


def canonical_json_bytes(value: object) -> bytes:
    """Return the one canonical UTF-8 JSON representation used by acceptance."""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _load_sibling(filename: str, module_name: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    existing = sys.modules.get(module_name)
    if isinstance(existing, ModuleType):
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise AcceptanceCandidateError(f"cannot load required helper: {path}")
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


def _strict_json(content: bytes, label: str) -> object:
    try:
        value = json.loads(
            content.decode("utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_object,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise AcceptanceCandidateError(
            f"{label} is not strict UTF-8 JSON: {error}"
        ) from error

    def inspect(item: object, location: str) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise AcceptanceCandidateError(
                f"{label} contains a non-finite number at {location}"
            )
        if isinstance(item, list):
            for index, child in enumerate(item):
                inspect(child, f"{location}[{index}]")
        elif isinstance(item, Mapping):
            for key, child in item.items():
                inspect(child, f"{location}.{key}")

    inspect(value, "$")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AcceptanceCandidateError(f"{label} must be a JSON object")
    return value


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(child) for child in value]
    return value


def _deep_freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return _FrozenDict(
            {str(key): _deep_freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(child) for child in value)
    return value


def _objective_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceCandidateError(f"{label} must be an observed nonblank string")
    normalized = re.sub(r"\s+", " ", value.strip()).casefold()
    if (
        normalized in GENERIC_OBJECTIVE_PLACEHOLDERS
        or OBJECTIVE_PENDING_PREFIX.match(normalized) is not None
        or OBJECTIVE_SENTINEL.fullmatch(normalized) is not None
    ):
        raise AcceptanceCandidateError(
            f"{label} must not use a generic placeholder value"
        )
    return value


def _absolute_posix_path(value: object, label: str) -> str:
    text = _objective_text(value, label)
    path = PurePosixPath(text)
    if (
        not path.is_absolute()
        or text.startswith("//")
        or path.as_posix() != text
        or "\\" in text
        or any(part in {"", ".", ".."} for part in path.parts[1:])
    ):
        raise AcceptanceCandidateError(
            f"{label} must be a canonical absolute POSIX path"
        )
    return text


def _reject_nonobjective_strings(value: object, label: str) -> None:
    if isinstance(value, str):
        _objective_text(value, label)
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_nonobjective_strings(child, f"{label}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_nonobjective_strings(child, f"{label}[{index}]")


def _parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or RFC3339_UTC.fullmatch(value) is None:
        raise AcceptanceCandidateError(f"{label} must be a canonical UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise AcceptanceCandidateError(f"{label} is not a valid UTC timestamp") from error
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise AcceptanceCandidateError(f"{label} must be UTC")
    return parsed


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _safe_relative(raw: object, label: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw:
        raise AcceptanceCandidateError(
            f"{label} path must be a nonempty POSIX relative path"
        )
    relative = PurePosixPath(raw)
    if (
        relative.is_absolute()
        or relative.as_posix() != raw
        or "\\" in raw
        or ":" in raw
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise AcceptanceCandidateError(f"{label} has unsafe path {raw!r}")
    return relative


def _read_regular_file_once(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        detail = "symbolic link" if isinstance(error, OSError) and error.errno == 40 else str(error)
        raise AcceptanceCandidateError(f"{label} cannot be read safely: {detail}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise AcceptanceCandidateError(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _read_relative(
    run_root: Path,
    root_descriptor: int,
    relative: PurePosixPath,
    label: str,
) -> bytes:
    directory_flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    current = os.dup(root_descriptor)
    try:
        for component in relative.parts[:-1]:
            try:
                next_descriptor = os.open(
                    component,
                    directory_flags,
                    dir_fd=current,
                )
            except OSError as error:
                raise AcceptanceCandidateError(
                    f"{label} {relative.as_posix()!r} contains a symbolic link or "
                    f"unreadable directory component: {error}"
                ) from error
            os.close(current)
            current = next_descriptor
        file_flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(relative.parts[-1], file_flags, dir_fd=current)
        except OSError as error:
            raise AcceptanceCandidateError(
                f"{label} {relative.as_posix()!r} is a symbolic link or cannot be "
                f"read safely: {error}"
            ) from error
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise AcceptanceCandidateError(
                    f"{label} {relative.as_posix()!r} is not a regular file"
                )
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        finally:
            os.close(descriptor)
    finally:
        os.close(current)


def _write_private_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        offset = 0
        while offset < len(content):
            offset += os.write(descriptor, content[offset:])
    finally:
        os.close(descriptor)


def _parse_sha256sums(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise AcceptanceCandidateError(f"SHA256SUMS is not UTF-8: {error}") from error
    if not text or not text.endswith("\n") or "\r" in text:
        raise AcceptanceCandidateError("SHA256SUMS must be nonempty canonical LF text")
    entries: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        match = SHA256SUMS_LINE.fullmatch(line)
        if match is None:
            raise AcceptanceCandidateError(
                f"SHA256SUMS line {line_number} is not canonical '<sha>  <relative>'"
            )
        digest, raw_relative = match.groups()
        try:
            relative = _safe_relative(raw_relative, "SHA256SUMS entry")
        except AcceptanceCandidateError as error:
            raise AcceptanceCandidateError(f"SHA256SUMS {error}") from error
        normalized = relative.as_posix()
        if normalized in entries:
            raise AcceptanceCandidateError(
                f"SHA256SUMS has duplicate path {normalized!r}"
            )
        entries[normalized] = digest
    return entries


def _parse_deterministic_package(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise AcceptanceCandidateError(
            f"deterministic-package.txt is not UTF-8: {error}"
        ) from error
    lines = text.splitlines()
    if len(lines) != 4:
        raise AcceptanceCandidateError(
            "deterministic-package.txt must contain exactly four lines"
        )
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise AcceptanceCandidateError("deterministic-package.txt has malformed line")
        key, value = line.split("=", 1)
        if key in values:
            raise AcceptanceCandidateError(
                f"deterministic-package.txt has duplicate key {key!r}"
            )
        values[key] = value
    if tuple(values) != ("status", "zip_a", "zip_b", "sha256"):
        raise AcceptanceCandidateError(
            "deterministic-package.txt keys must be status, zip_a, zip_b, sha256"
        )
    if values["status"] != "PASS" or re.fullmatch(r"[0-9a-f]{64}", values["sha256"]) is None:
        raise AcceptanceCandidateError("deterministic-package.txt does not record PASS")
    _safe_relative(values["zip_a"], "deterministic-package.zip_a")
    _safe_relative(values["zip_b"], "deterministic-package.zip_b")
    return values


@contextmanager
def _capture_candidate(run_root: Path, archive_path: Path) -> Iterator[_CapturedCandidate]:
    source_run_root = _lexical_absolute(Path(run_root))
    source_archive_path = _lexical_absolute(Path(archive_path))
    try:
        root_metadata = os.lstat(source_run_root)
    except OSError as error:
        raise AcceptanceCandidateError(f"--run-root cannot be inspected: {error}") from error
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise AcceptanceCandidateError(
            "--run-root must be a real directory, not a symbolic link"
        )
    try:
        archive_relative_path = source_archive_path.relative_to(source_run_root)
    except ValueError as error:
        raise AcceptanceCandidateError("--archive must be inside --run-root") from error
    archive_relative = _safe_relative(
        PurePosixPath(*archive_relative_path.parts).as_posix(),
        "--archive",
    ).as_posix()

    root_flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    root_descriptor = os.open(source_run_root, root_flags)
    try:
        sha256sums_content = _read_relative(
            source_run_root,
            root_descriptor,
            PurePosixPath("SHA256SUMS"),
            "SHA256SUMS",
        )
        entries = _parse_sha256sums(sha256sums_content)
        relative_contents: dict[str, bytes] = {}
        for relative, expected_digest in entries.items():
            content = _read_relative(
                source_run_root,
                root_descriptor,
                PurePosixPath(relative),
                "SHA256SUMS entry",
            )
            actual_digest = _sha256(content)
            if actual_digest != expected_digest:
                raise AcceptanceCandidateError(
                    f"SHA256SUMS entry {relative!r} SHA-256 mismatch: expected "
                    f"{expected_digest}, found {actual_digest}"
                )
            relative_contents[relative] = content

        if archive_relative not in relative_contents:
            raise AcceptanceCandidateError(
                "SHA256SUMS does not contain the supplied candidate archive"
            )
        required = {
            "acceptance-outcome.json",
            "SOURCE_COMMIT",
            "host-preflight.txt",
            "runbook.log",
            "deterministic-package.txt",
            "evidence/run_manifest.json",
            "evidence/ctest.xml",
            "evidence/benchmark_samples.csv",
            "evidence/benchmark_summary.json",
            "evidence/summary.md",
            "manifest-only-verification.json",
            "clean-room-verification.log",
        }
        missing = sorted(required - relative_contents.keys())
        if missing:
            raise AcceptanceCandidateError(
                "SHA256SUMS is missing required candidate paths: " + ", ".join(missing)
            )

        deterministic = _parse_deterministic_package(
            relative_contents["deterministic-package.txt"]
        )
        if deterministic["zip_a"] != archive_relative:
            raise AcceptanceCandidateError(
                "deterministic-package.zip_a does not equal the supplied archive"
            )
        zip_a_path = PurePosixPath(deterministic["zip_a"])
        expected_zip_b = (
            f"dist-b/{zip_a_path.name}"
            if len(zip_a_path.parts) >= 2 and zip_a_path.parts[0] == "dist-a"
            else None
        )
        if expected_zip_b is None or deterministic["zip_b"] != expected_zip_b:
            raise AcceptanceCandidateError(
                "deterministic-package.zip_b must be the independent "
                "dist-b/<delivery ZIP filename> path"
            )
        zip_b_relative = deterministic["zip_b"]
        if zip_b_relative in relative_contents:
            zip_b_content = relative_contents[zip_b_relative]
        else:
            zip_b_content = _read_relative(
                source_run_root,
                root_descriptor,
                PurePosixPath(zip_b_relative),
                "deterministic-package.zip_b",
            )
    finally:
        os.close(root_descriptor)

    archive_content = relative_contents[archive_relative]
    expected_archive_digest = deterministic["sha256"]
    if _sha256(archive_content) != expected_archive_digest:
        raise AcceptanceCandidateError(
            "deterministic-package.sha256 does not match the candidate archive"
        )
    if zip_b_content != archive_content:
        raise AcceptanceCandidateError(
            "deterministic-package.zip_b is not byte-identical to zip_a"
        )

    with tempfile.TemporaryDirectory(prefix="csc3-candidate-snapshot-") as directory:
        snapshot_root = Path(directory) / "run-root"
        snapshot_root.mkdir(mode=0o700)
        _write_private_file(snapshot_root / "SHA256SUMS", sha256sums_content)
        for relative, content in sorted(relative_contents.items()):
            _write_private_file(
                snapshot_root.joinpath(*PurePosixPath(relative).parts),
                content,
            )
        if zip_b_relative not in relative_contents:
            _write_private_file(
                snapshot_root.joinpath(*PurePosixPath(zip_b_relative).parts),
                zip_b_content,
            )
        yield _CapturedCandidate(
            source_run_root=source_run_root,
            source_archive_path=source_archive_path,
            run_root=snapshot_root,
            archive_path=snapshot_root.joinpath(*PurePosixPath(archive_relative).parts),
            archive_relative=archive_relative,
            archive_content=archive_content,
            zip_b_relative=zip_b_relative,
            zip_b_content=zip_b_content,
            sha256sums_content=sha256sums_content,
            relative_contents=MappingProxyType(relative_contents),
        )


def _tail_json(content: bytes, label: str) -> Mapping[str, object]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise AcceptanceCandidateError(f"{label} is not UTF-8: {error}") from error
    decoder = json.JSONDecoder(
        parse_constant=_reject_json_constant,
        object_pairs_hook=_reject_duplicate_object,
    )
    for offset in range(len(text) - 1, -1, -1):
        if text[offset] != "{":
            continue
        try:
            value, end = decoder.raw_decode(text, offset)
        except (json.JSONDecodeError, ValueError):
            continue
        if text[end:].strip():
            continue
        return _mapping(value, label)
    raise AcceptanceCandidateError(f"{label} does not end with one strict JSON object")


def _stable_verifier_result(value: Mapping[str, object]) -> dict[str, object]:
    fields = (
        "status",
        "archive_sha256",
        "source_commit",
        "evidence_source_commit",
        "evidence_source_matches_package_source",
        "distribution",
        "verified_file_count",
        "clean_room_executed",
    )
    return {field: _plain_json(value.get(field)) for field in fields}


def _quiet_checked(command: list[str], cwd: Path) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _require_verifier_result(
    value: Mapping[str, object],
    *,
    label: str,
    source_commit: str,
    archive_sha256: str,
    clean_room_executed: bool,
) -> dict[str, object]:
    stable = _stable_verifier_result(value)
    expected = {
        "status": "PASS",
        "archive_sha256": archive_sha256,
        "source_commit": source_commit,
        "evidence_source_commit": source_commit,
        "evidence_source_matches_package_source": True,
        "distribution": "INTERNAL EVALUATION ONLY",
        "clean_room_executed": clean_room_executed,
    }
    for field, required in expected.items():
        if stable.get(field) != required:
            raise AcceptanceCandidateError(
                f"{label}.{field} must be {required!r}; found {stable.get(field)!r}"
            )
    count = stable.get("verified_file_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise AcceptanceCandidateError(
            f"{label}.verified_file_count must be a positive integer"
        )
    return stable


def _preflight_sections(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise AcceptanceCandidateError(
            f"host-preflight.txt is not UTF-8: {error}"
        ) from error
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:]
            if current in sections:
                raise AcceptanceCandidateError(
                    f"host-preflight.txt has duplicate section {current!r}"
                )
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _section_first(sections: Mapping[str, str], name: str) -> str | None:
    value = sections.get(name, "")
    return next((line.strip() for line in value.splitlines() if line.strip()), None)


def _section_version(
    sections: Mapping[str, str], name: str, pattern: str
) -> str | None:
    value = _section_first(sections, name)
    if value is None:
        return None
    match = re.search(pattern, value)
    return match.group(1) if match is not None else None


def _lscpu_value(cpu_section: str, label: str) -> str | None:
    match = re.search(r"^" + re.escape(label) + r":\s*(.+)$", cpu_section, re.MULTILINE)
    return match.group(1).strip() if match is not None else None


def _cpuset_value(cpuset_section: str, label: str) -> str | None:
    match = re.search(r"^" + re.escape(label) + r":\s*(.+)$", cpuset_section, re.MULTILINE)
    return match.group(1).strip() if match is not None else None


def _key_value_section(content: str, label: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in content.splitlines():
        if not line.strip():
            continue
        if "=" not in line:
            raise AcceptanceCandidateError(f"{label} has malformed line {line!r}")
        key, value = line.split("=", 1)
        if not key or not value or key in values:
            raise AcceptanceCandidateError(f"{label} has invalid key {key!r}")
        values[key] = value
    return values


def _artifact(path: str, content: bytes) -> dict[str, object]:
    return {
        "path": path,
        "size_bytes": len(content),
        "sha256": _sha256(content),
        "status": "PASS",
    }


def _correctness_case(raw: object) -> dict[str, object]:
    case = _mapping(raw, "benchmark validation case")
    matrix = _mapping(case.get("matrix"), "benchmark validation matrix")
    displacement = _mapping(
        case.get("displacement"), "benchmark validation displacement"
    )
    maximum_error = matrix.get("max_absolute_error")
    tolerance = matrix.get("max_absolute_tolerance")
    return {
        "status": case.get("status"),
        "structure_equal": matrix.get("structure_matches"),
        "values_finite": True,
        "scatter_indices_valid": True,
        "frobenius_relative_error": matrix.get("relative_frobenius_error"),
        "maximum_absolute_error": maximum_error,
        "maximum_absolute_serial_entry": matrix.get("reference_max_absolute_value"),
        "maximum_absolute_error_tolerance": tolerance,
        "maximum_absolute_error_within_tolerance": (
            isinstance(maximum_error, (int, float))
            and not isinstance(maximum_error, bool)
            and isinstance(tolerance, (int, float))
            and not isinstance(tolerance, bool)
            and maximum_error <= tolerance
        ),
        "displacement_relative_error": displacement.get(
            "relative_displacement_error"
        ),
        "relative_residual": displacement.get("parallel_relative_residual"),
        "serial_relative_residual": displacement.get("serial_relative_residual"),
        "evidence_reference": "evidence/benchmark_summary.json",
    }


def _derive_machine_facts(
    captured: _CapturedCandidate,
    frozen_at_utc: str,
) -> tuple[dict[str, object], dict[str, bytes]]:
    contents = captured.relative_contents
    outcome = _mapping(
        _strict_json(contents["acceptance-outcome.json"], "acceptance-outcome.json"),
        "acceptance-outcome.json",
    )
    if outcome.get("status") != "PACKAGE_CANDIDATE":
        raise AcceptanceCandidateError(
            "acceptance-outcome.json.status must be PACKAGE_CANDIDATE"
        )
    candidate_completed_raw = outcome.get("candidate_completed_at_utc")
    candidate_completed = _parse_utc(
        candidate_completed_raw,
        "acceptance-outcome.json.candidate_completed_at_utc",
    )
    frozen = _parse_utc(frozen_at_utc, "frozen_at_utc")
    if frozen <= candidate_completed:
        raise AcceptanceCandidateError(
            "frozen_at_utc must be strictly later than candidate completion"
        )

    source_text = contents["SOURCE_COMMIT"]
    try:
        source_commit = source_text.decode("utf-8").removesuffix("\n")
    except UnicodeError as error:
        raise AcceptanceCandidateError(f"SOURCE_COMMIT is not UTF-8: {error}") from error
    if source_text != (source_commit + "\n").encode("utf-8") or SHA40.fullmatch(
        source_commit
    ) is None:
        raise AcceptanceCandidateError(
            "SOURCE_COMMIT must contain exactly one full lowercase source SHA"
        )

    for label, relative in (
        ("run_manifest.json", "evidence/run_manifest.json"),
        ("benchmark_summary.json", "evidence/benchmark_summary.json"),
        ("manifest-only-verification.json", "manifest-only-verification.json"),
    ):
        _strict_json(contents[relative], label)
    recorded_manifest_only = _mapping(
        _strict_json(
            contents["manifest-only-verification.json"],
            "manifest-only-verification.json",
        ),
        "manifest-only-verification.json",
    )
    recorded_clean_room = _tail_json(
        contents["clean-room-verification.log"],
        "clean-room-verification.log",
    )

    reporter = _load_sibling(
        "generate_test_report.py", "csc3_candidate_report_contract"
    )
    try:
        bundle = reporter.validate_evidence_bundle(
            captured.run_root / "evidence" / "run_manifest.json"
        )
    except Exception as error:
        raise AcceptanceCandidateError(
            f"formal evidence cannot be recomputed: {error}"
        ) from error
    manifest = _mapping(bundle.manifest, "run_manifest.json")
    if (
        manifest.get("status") != "PASS"
        or manifest.get("evidence_level") != "formal"
        or manifest.get("report_intent") != "delivery"
        or bundle.report_status != "PASS"
    ):
        raise AcceptanceCandidateError(
            "candidate evidence requires status=PASS, evidence_level=formal, "
            "report_intent=delivery, and recomputed report PASS"
        )
    manifest_source = _mapping(manifest.get("source"), "run_manifest source")
    if manifest_source.get("commit_sha") != source_commit:
        raise AcceptanceCandidateError(
            "run_manifest source commit does not match SOURCE_COMMIT"
        )
    if manifest_source.get("source_dirty_at_start") is not False:
        raise AcceptanceCandidateError("formal source must be clean at candidate start")
    ended_at = _parse_utc(manifest.get("ended_at_utc"), "run_manifest ended_at_utc")
    if ended_at > candidate_completed:
        raise AcceptanceCandidateError(
            "candidate completion must not precede evidence completion"
        )

    input_facts = _mapping(manifest.get("input"), "run_manifest input")
    if (
        input_facts.get("case") != "windhub"
        or input_facts.get("repository_relative_path")
        != "examples/3d-WindTurbineHub.inp"
        or input_facts.get("tracked") is not True
        or input_facts.get("materialized") is not True
        or input_facts.get("matches_head_lfs") is not True
        or input_facts.get("sha256") != input_facts.get("head_lfs_oid_sha256")
        or input_facts.get("size_bytes") != input_facts.get("head_lfs_size_bytes")
    ):
        raise AcceptanceCandidateError(
            "run_manifest does not prove the materialized WindHub HEAD LFS identity"
        )
    if tuple(bundle.junit_testcase_names) != EXPECTED_TESTS:
        raise AcceptanceCandidateError(
            "ctest.xml does not contain the exact ten ordered CTest names"
        )

    canonical_report = reporter.render_report(bundle).encode("utf-8")
    report_paths = [
        relative
        for relative, content in contents.items()
        if content == canonical_report
        and relative.endswith("-test-report.zh-CN.md")
    ]
    if len(report_paths) != 1:
        raise AcceptanceCandidateError(
            "SHA256SUMS must contain exactly one canonical recomputed Markdown report"
        )
    report_relative = report_paths[0]

    archive_sha256 = _sha256(captured.archive_content)
    recorded_manifest_stable = _require_verifier_result(
        recorded_manifest_only,
        label="manifest-only-verification.json",
        source_commit=source_commit,
        archive_sha256=archive_sha256,
        clean_room_executed=False,
    )
    recorded_clean_stable = _require_verifier_result(
        recorded_clean_room,
        label="clean-room-verification.log",
        source_commit=source_commit,
        archive_sha256=archive_sha256,
        clean_room_executed=True,
    )

    verifier = _load_sibling(
        "verify_delivery_package.py", "csc3_candidate_package_verifier"
    )
    try:
        fresh_manifest_only_raw = verifier.verify_delivery_package(
            captured.archive_path,
            run_clean_room=False,
        )
    except Exception as error:
        raise AcceptanceCandidateError(
            f"candidate archive manifest-only verification failed: {error}"
        ) from error
    fresh_manifest_only = _require_verifier_result(
        fresh_manifest_only_raw,
        label="fresh manifest-only verification",
        source_commit=source_commit,
        archive_sha256=archive_sha256,
        clean_room_executed=False,
    )
    try:
        fresh_clean_room_raw = verifier.verify_delivery_package(
            captured.archive_path,
            run_clean_room=True,
            command_runner=_quiet_checked,
        )
    except Exception as error:
        raise AcceptanceCandidateError(
            f"candidate archive clean-room verification failed: {error}"
        ) from error
    fresh_clean_room = _require_verifier_result(
        fresh_clean_room_raw,
        label="fresh clean-room verification",
        source_commit=source_commit,
        archive_sha256=archive_sha256,
        clean_room_executed=True,
    )
    if fresh_manifest_only != recorded_manifest_stable:
        raise AcceptanceCandidateError(
            "recorded manifest-only verification does not match fresh verification"
        )
    if fresh_clean_room != recorded_clean_stable:
        raise AcceptanceCandidateError(
            "recorded clean-room verification does not match fresh verification"
        )

    benchmark = _mapping(manifest.get("benchmark"), "run_manifest benchmark")
    requested_threads = benchmark.get("requested_thread_counts")
    observed_threads = benchmark.get("observed_thread_counts")
    if (
        requested_threads != observed_threads
        or not isinstance(requested_threads, list)
        or any(thread not in requested_threads for thread in (1, 2, 4, 8, 16))
        or benchmark.get("warmup_count") != 2
        or benchmark.get("repeat_count") != 7
        or benchmark.get("amortization_count") != 1
    ):
        raise AcceptanceCandidateError(
            "formal execution must preserve requested/observed threads and W=2, R=7, m=1"
        )
    binding = _mapping(manifest.get("binding_environment"), "binding environment")
    if binding != {
        "OMP_DYNAMIC": "false",
        "OMP_PROC_BIND": "close",
        "OMP_PLACES": "cores",
    }:
        raise AcceptanceCandidateError("formal OpenMP binding environment is invalid")

    summary = _mapping(bundle.benchmark_summary, "benchmark summary")
    validation_cases = summary.get("validation_cases")
    if not isinstance(validation_cases, list):
        raise AcceptanceCandidateError("benchmark summary lacks validation cases")
    cases_by_type = {
        str(_mapping(case, "validation case").get("element_type", "")).lower(): case
        for case in validation_cases
    }
    if set(cases_by_type) != {"tet4", "hex8"}:
        raise AcceptanceCandidateError(
            "benchmark summary must contain exactly Tet4 and Hex8 validation cases"
        )
    correctness = {
        "status": "PASS",
        "thresholds": {
            "frobenius_relative_error_maximum": 1.0e-8,
            "maximum_absolute_error": {
                "absolute_term": 1.0e-10,
                "scale_term": 1.0e-8,
                "scale_quantity": "max_abs_serial_matrix_entry",
            },
            "displacement_relative_error_maximum": 1.0e-8,
            "relative_residual_maximum": 1.0e-10,
        },
        "overall_matrix": _plain_json(
            _mapping(summary.get("correctness"), "benchmark overall correctness")
        ),
        "tet4": _correctness_case(cases_by_type["tet4"]),
        "hex8": _correctness_case(cases_by_type["hex8"]),
    }
    if any(correctness[name]["status"] != "PASS" for name in ("tet4", "hex8")):
        raise AcceptanceCandidateError("Tet4 and Hex8 correctness must both PASS")

    recomputed_gate = _mapping(bundle.recomputed_gate, "recomputed performance gate")
    if (
        recomputed_gate.get("status") != "PASS"
        or recomputed_gate.get("numeric_requirement_met") is not True
        or recomputed_gate.get("symbolic_requirement_met") is not True
    ):
        raise AcceptanceCandidateError("recomputed formal performance gate did not PASS")
    statistics = _mapping(bundle.recomputed_statistics, "recomputed statistics")
    rows = statistics.get("per_thread")
    if not isinstance(rows, tuple):
        raise AcceptanceCandidateError("recomputed per-thread statistics are unavailable")
    by_thread = {
        _mapping(row, "per-thread statistic").get("thread_count"): _mapping(
            row, "per-thread statistic"
        )
        for row in rows
    }
    numeric_thread = recomputed_gate.get("numeric_thread_count")
    symbolic_thread = recomputed_gate.get("symbolic_thread_count")
    numeric_row = by_thread.get(numeric_thread)
    symbolic_row = by_thread.get(symbolic_thread)
    if numeric_row is None or symbolic_row is None:
        raise AcceptanceCandidateError("performance gate selected an unknown thread count")
    numeric_stats = _mapping(
        numeric_row.get("numeric_algorithm_ms"), "numeric statistics"
    )
    symbolic_stats = _mapping(
        symbolic_row.get("symbolic_total_ms"), "symbolic statistics"
    )
    performance = {
        "status": "PASS",
        "thresholds": {
            "numeric_speedup_minimum": 1.5,
            "symbolic_speedup_exclusive_minimum": 1.0,
            "maximum_coefficient_of_variation": 0.05,
            "thread_count_exclusive_minimum": 1,
        },
        "numeric_thread_count": numeric_thread,
        "numeric_speedup": numeric_row.get("numeric_speedup"),
        "numeric_coefficient_of_variation": numeric_stats.get(
            "coefficient_of_variation"
        ),
        "numeric_sample_count": numeric_stats.get("sample_count"),
        "symbolic_thread_count": symbolic_thread,
        "symbolic_speedup": symbolic_row.get("symbolic_speedup"),
        "symbolic_coefficient_of_variation": symbolic_stats.get(
            "coefficient_of_variation"
        ),
        "symbolic_sample_count": symbolic_stats.get("sample_count"),
        "raw_sample_count": len(bundle.csv_rows),
        "samples_sha256": _sha256(contents["evidence/benchmark_samples.csv"]),
        "summary_sha256": _sha256(contents["evidence/benchmark_summary.json"]),
    }

    environment = _mapping(manifest.get("environment"), "run_manifest environment")
    manifest_toolchain = _mapping(manifest.get("toolchain"), "run_manifest toolchain")
    openmp = _mapping(manifest_toolchain.get("openmp"), "run_manifest OpenMP")
    sections = _preflight_sections(contents["host-preflight.txt"])
    cpu_section = sections.get("CPU", "")
    cpuset_section = sections.get("cpuset", "")
    tool_paths = _key_value_section(
        sections.get("tool paths", ""), "host-preflight tool paths"
    )
    required_tool_paths = {
        "compiler",
        "cmake",
        "ninja",
        "python",
        "git",
        "git_lfs",
    }
    if set(tool_paths) != required_tool_paths:
        raise AcceptanceCandidateError(
            "host-preflight tool paths must record compiler, cmake, ninja, python, "
            "git, and git_lfs"
        )
    tool_paths = {
        name: _absolute_posix_path(value, f"toolchain.{name}_path")
        for name, value in tool_paths.items()
    }
    required_observations = {
        "kernel": _section_first(sections, "kernel"),
        "numa": sections.get("NUMA") or None,
        "smt": _section_first(sections, "SMT"),
        "governor": _section_first(sections, "CPU governor"),
        "intel_no_turbo": _section_first(sections, "Intel turbo"),
        "generic_boost": _section_first(sections, "generic boost"),
        "online_cpus": _lscpu_value(cpu_section, "On-line CPU(s) list"),
        "process_affinity": _section_first(sections, "process affinity"),
        "cpuset_cpus": _cpuset_value(cpuset_section, "cpuset_cpus"),
        "cpuset_mems": _cpuset_value(cpuset_section, "cpuset_mems"),
        "physical_core_topology": cpu_section or None,
        "mainline_identity": _section_first(sections, "mainline identity"),
        "openmp_version": _section_first(sections, "OpenMP version"),
        "openmp_path": _section_first(sections, "OpenMP path"),
    }
    missing_observations = sorted(
        name for name, value in required_observations.items() if not value
    )
    if missing_observations:
        raise AcceptanceCandidateError(
            "host-preflight lacks required objective observations: "
            + ", ".join(missing_observations)
        )
    controlled_host = {
        "controlled_host_id": environment.get("controlled_host_id"),
        "system": environment.get("system"),
        "architecture": environment.get("architecture"),
        "hostname": environment.get("hostname"),
        "kernel": required_observations["kernel"],
        "cpu_vendor": environment.get("cpu_vendor"),
        "cpu_model": environment.get("cpu_model"),
        "physical_core_count": environment.get("physical_core_count"),
        "logical_core_count": environment.get("logical_core_count"),
        "total_memory_bytes": environment.get("total_memory_bytes"),
        "numa": required_observations["numa"],
        "smt": required_observations["smt"],
        "governor": required_observations["governor"],
        "turbo": {
            "intel_no_turbo": required_observations["intel_no_turbo"],
            "generic_boost": required_observations["generic_boost"],
        },
        "preflight_sha256": _sha256(contents["host-preflight.txt"]),
    }
    cpu_scope = {
        "online_cpus": required_observations["online_cpus"],
        "process_affinity": required_observations["process_affinity"],
        "cpuset_cpus": required_observations["cpuset_cpus"],
        "cpuset_mems": required_observations["cpuset_mems"],
        "physical_core_topology": required_observations["physical_core_topology"],
        "observation_source": "host-preflight.txt",
    }
    toolchain = {
        "compiler": manifest_toolchain.get("compiler_id"),
        "compiler_version": manifest_toolchain.get("compiler_version"),
        "compiler_path": tool_paths["compiler"],
        "cmake_version": manifest_toolchain.get("cmake_version"),
        "cmake_path": tool_paths["cmake"],
        "ninja_version": _section_version(sections, "Ninja", r"^(\S+)$"),
        "ninja_path": tool_paths["ninja"],
        "python_version": environment.get("python_version"),
        "python_path": tool_paths["python"],
        "git_version": _section_version(sections, "Git", r"^git version (\S+)$"),
        "git_path": tool_paths["git"],
        "git_lfs_version": _section_version(
            sections, "Git LFS", r"^git-lfs/(\S+?)(?:\s|$)"
        ),
        "git_lfs_path": tool_paths["git_lfs"],
        "openmp": {
            "found": openmp.get("found"),
            "required": openmp.get("require_openmp"),
            "flags": openmp.get("flags"),
            "version": required_observations["openmp_version"],
            "path": _absolute_posix_path(
                required_observations["openmp_path"], "toolchain.openmp.path"
            ),
        },
    }

    named_paths = {
        "run_manifest": "evidence/run_manifest.json",
        "ctest_junit": "evidence/ctest.xml",
        "benchmark_samples": "evidence/benchmark_samples.csv",
        "benchmark_summary": "evidence/benchmark_summary.json",
        "evidence_summary": "evidence/summary.md",
        "canonical_markdown_report": report_relative,
        "host_preflight": "host-preflight.txt",
        "runbook_log": "runbook.log",
        "outcome_record": "acceptance-outcome.json",
        "source_commit_file": "SOURCE_COMMIT",
        "deterministic_package_record": "deterministic-package.txt",
        "manifest_only_verifier_output": "manifest-only-verification.json",
        "clean_room_verifier_log": "clean-room-verification.log",
        "delivery_zip": captured.archive_relative,
    }
    artifact_contents = {
        name: contents[relative] for name, relative in named_paths.items()
    }
    artifact_contents["sha256sums_file"] = captured.sha256sums_content
    artifact_contents["deterministic_zip_b"] = captured.zip_b_content
    artifacts = {
        name: _artifact(relative, artifact_contents[name])
        for name, relative in named_paths.items()
    }
    artifacts["sha256sums_file"] = _artifact(
        "SHA256SUMS", captured.sha256sums_content
    )
    artifacts["deterministic_zip_b"] = _artifact(
        captured.zip_b_relative, captured.zip_b_content
    )
    closure = [
        _artifact(relative, content) for relative, content in sorted(contents.items())
    ]
    deterministic = _parse_deterministic_package(
        contents["deterministic-package.txt"]
    )

    facts: dict[str, object] = {
        "schema_version": MACHINE_FACTS_VERSION,
        "workflow_state": "APPROVAL_INPUT_READY",
        "distribution": "INTERNAL EVALUATION ONLY",
        "source_commit": source_commit,
        "source": {
            "branch": manifest_source.get("branch"),
            "source_dirty_at_start": False,
            "demo_version": manifest_source.get("demo_version"),
            "mainline_identity": required_observations["mainline_identity"],
        },
        "input": _plain_json(input_facts),
        "controlled_host": controlled_host,
        "cpu_scope": cpu_scope,
        "toolchain": toolchain,
        "execution": {
            "status": "PASS",
            "evidence_level": "formal",
            "report_intent": "delivery",
            "preset": "delivery",
            "warmup_count": benchmark.get("warmup_count"),
            "repeat_count": benchmark.get("repeat_count"),
            "amortization_count": benchmark.get("amortization_count"),
            "requested_thread_counts": _plain_json(requested_threads),
            "observed_thread_counts": _plain_json(observed_threads),
            "physical_core_thread_included": environment.get("physical_core_count")
            in requested_threads,
            "omp_dynamic": binding.get("OMP_DYNAMIC"),
            "omp_proc_bind": binding.get("OMP_PROC_BIND"),
            "omp_places": binding.get("OMP_PLACES"),
            "started_at_utc": manifest.get("started_at_utc"),
            "ended_at_utc": manifest.get("ended_at_utc"),
        },
        "ctest": {
            "status": "PASS",
            "test_count": len(bundle.junit_testcase_names),
            "failed_count": 0,
            "skipped_count": 0,
            "disabled_count": 0,
            "not_run_count": 0,
            "test_names": list(bundle.junit_testcase_names),
            "evidence_reference": "evidence/ctest.xml",
        },
        "correctness": correctness,
        "performance": performance,
        "artifacts": artifacts,
        "candidate_closure": closure,
        "verifications": {
            "status": "PASS",
            "source_and_input_identity": {"status": "PASS"},
            "ctest": {"status": "PASS", "test_count": len(EXPECTED_TESTS)},
            "report_recomputation": {"status": "PASS"},
            "sha256sums": {"status": "PASS", "entry_count": len(contents)},
            "deterministic_package": {
                "status": "PASS",
                "zip_a": deterministic["zip_a"],
                "zip_b": deterministic["zip_b"],
                "sha256": deterministic["sha256"],
            },
            "manifest_only": fresh_manifest_only,
            "clean_room": fresh_clean_room,
        },
        "candidate": {
            "status": "PACKAGE_CANDIDATE",
            "completed_at_utc": candidate_completed_raw,
            "frozen_at_utc": frozen_at_utc,
        },
    }
    _reject_nonobjective_strings(facts, "machine_facts")
    machine_facts_content = canonical_json_bytes(facts)
    strict_round_trip = _strict_json(machine_facts_content, "machine facts")
    if strict_round_trip != facts:
        raise AcceptanceCandidateError("machine facts canonical round-trip changed values")
    schema_validator = _load_sibling(
        "validate_acceptance_record.py", "csc3_candidate_schema_validator"
    )
    try:
        schema_validator.validate_schema_document(
            facts,
            MACHINE_FACTS_SCHEMA,
            schema_label="acceptance-machine-facts schema",
        )
    except Exception as error:
        raise AcceptanceCandidateError(f"machine facts schema validation failed: {error}") from error
    return facts, artifact_contents


@contextmanager
def validated_candidate_snapshot(
    run_root: Path,
    archive_path: Path,
    *,
    frozen_at_utc: str,
) -> Iterator[ValidatedCandidateSnapshot]:
    """Yield one validated view whose bytes never need rereading from source paths."""
    with _capture_candidate(Path(run_root), Path(archive_path)) as captured:
        facts, artifact_contents = _derive_machine_facts(captured, frozen_at_utc)
        content = canonical_json_bytes(facts)
        immutable_facts = _deep_freeze(facts)
        if not isinstance(immutable_facts, Mapping):
            raise AcceptanceCandidateError("machine facts did not freeze as a mapping")
        yield ValidatedCandidateSnapshot(
            machine_facts=immutable_facts,
            machine_facts_content=content,
            archive_content=captured.archive_content,
            artifact_contents=MappingProxyType(artifact_contents),
            relative_contents=captured.relative_contents,
        )
