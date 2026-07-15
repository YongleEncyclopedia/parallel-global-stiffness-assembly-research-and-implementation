#!/usr/bin/env python3
"""Verify a CSC3 demo delivery archive and optionally run clean-room tests."""

from __future__ import annotations

import argparse
import hashlib
import io
import importlib.metadata
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
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any


BUILD_INFO_SCHEMA = "csc3-demo-build-info-v1"
DISTRIBUTION_STATUS = "INTERNAL EVALUATION ONLY"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)$")
URI_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
FORBIDDEN_PARTS = {".DS_Store", "__MACOSX", "__pycache__", "build"}
FORBIDDEN_SUFFIXES = {".pyc", ".tif", ".tiff"}
REQUIRED_EVIDENCE_FILENAMES = {
    "benchmark_samples.csv",
    "benchmark_summary.json",
    "ctest.xml",
    "run_manifest.json",
}
REQUIRED_ARTIFACT_BINDINGS = REQUIRED_EVIDENCE_FILENAMES - {"run_manifest.json"}
REQUIRED_FORMAL_EVIDENCE_FILENAMES = REQUIRED_EVIDENCE_FILENAMES | {"summary.md"}
BUNDLE_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
REQUIRED_DELIVERY_PATHS = {
    ".clang-format",
    "BUILD_INFO.json",
    "CMakeLists.txt",
    "CMakePresets.json",
    "MIGRATION.md",
    "README.md",
    "requirements-test.txt",
    "docs/api-and-naming-contract.md",
    "packaging/ACCEPTANCE_CHECKLIST.zh-CN.md",
    "packaging/ACCEPTANCE_DECISION.schema.json",
    "packaging/ACCEPTANCE_MACHINE_FACTS.schema.json",
    "packaging/ACCEPTANCE_RECORD.schema.json",
    "packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md",
    "packaging/INTERNAL_EVALUATION_ONLY.md",
    "packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md",
    "packaging/README.md",
    "packaging/THIRD_PARTY_NOTICES.md",
    "packaging/TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md",
    "scripts/check_ctest_inventory.py",
    "scripts/check_ctest_junit.py",
    "scripts/acceptance_core.py",
    "scripts/acceptance_publication.py",
    "scripts/acceptance_rendering.py",
    "scripts/create_delivery_package.py",
    "scripts/finalize_delivery.py",
    "scripts/generate_test_report.py",
    "scripts/run_benchmark.py",
    "scripts/prepare_acceptance_materials.py",
    "scripts/validate_acceptance_record.py",
    "scripts/verify_delivery_package.py",
    "tests/ctest/expected-ci-tests.txt",
    "tests/external_consumer/CMakeLists.txt",
    "tests/external_consumer/main.cpp",
}


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
        raise RuntimeError(f"{label} is not strict UTF-8 JSON: {error}") from error

    def inspect(item: object, location: str) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise RuntimeError(
                f"{label} contains a non-finite JSON number at {location}"
            )
        if isinstance(item, list):
            for index, child in enumerate(item):
                inspect(child, f"{location}[{index}]")
        elif isinstance(item, dict):
            for key, child in item.items():
                inspect(child, f"{location}.{key}")

    inspect(value, "$")
    return value

CommandRunner = Callable[[list[str], Path], None]


def _require_clean_room_python_dependencies() -> None:
    """Fail before extraction when the clean-room test runtime is incomplete."""
    requirement = "jsonschema>=4.23,<5"
    requirements_path = Path(__file__).resolve().parents[1] / "requirements-test.txt"
    install_command = f"{sys.executable} -m pip install -r {requirements_path}"
    try:
        raw_version = importlib.metadata.version("jsonschema")
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError(
            "full clean-room verification requires "
            f"{requirement}; install it with: {install_command}"
        ) from error
    match = re.match(r"^(\d+)\.(\d+)", raw_version)
    if match is None:
        raise RuntimeError(
            "full clean-room verification cannot interpret installed "
            f"jsonschema version {raw_version!r}; required {requirement}; "
            f"install it with: {install_command}"
        )
    major, minor = (int(value) for value in match.groups())
    if (major, minor) < (4, 23) or major >= 5:
        raise RuntimeError(
            "full clean-room verification found "
            f"jsonschema {raw_version}, but requires {requirement}; "
            f"install it with: {install_command}"
        )
    if importlib.util.find_spec("jsonschema") is None:
        raise RuntimeError(
            "full clean-room verification found jsonschema metadata but no "
            f"importable module; required {requirement}; install it with: "
            f"{install_command}"
        )


def _validate_member_name(name: str) -> PurePosixPath:
    if "\\" in name or name.startswith("/") or name.endswith("/"):
        raise ValueError(f"unsafe ZIP member path: {name!r}")
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or len(path.parts) < 2
        or ".." in path.parts
        or "." in path.parts
        or any(":" in part for part in path.parts)
        or path.as_posix() != name
    ):
        raise ValueError(f"unsafe ZIP member path: {name!r}")
    return path


def _parse_manifest(content: bytes) -> dict[str, str]:
    if b"\r" in content:
        raise RuntimeError("MANIFEST.sha256 contains a carriage return")
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise RuntimeError("MANIFEST.sha256 is not UTF-8") from error
    if not lines:
        raise RuntimeError("MANIFEST.sha256 is empty")
    entries: dict[str, str] = {}
    ordered_paths: list[str] = []
    for line in lines:
        match = MANIFEST_LINE.fullmatch(line)
        if match is None:
            raise RuntimeError(f"malformed MANIFEST.sha256 line: {line!r}")
        digest, relative = match.groups()
        path = PurePosixPath(relative)
        if (
            path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or "." in path.parts
            or "\\" in relative
            or path.as_posix() != relative
        ):
            raise RuntimeError(f"unsafe manifest path: {relative!r}")
        if relative == "MANIFEST.sha256":
            raise RuntimeError("MANIFEST.sha256 must not hash itself")
        if relative in entries:
            raise RuntimeError(f"duplicate manifest path: {relative}")
        entries[relative] = digest
        ordered_paths.append(relative)
    if ordered_paths != sorted(ordered_paths):
        raise RuntimeError("manifest paths are not in lexicographic order")
    return entries


def _validate_no_path_prefix_collisions(
    archive_members: set[str],
    manifest_paths: set[str],
) -> None:
    origins: dict[PurePosixPath, set[str]] = {}
    for origin, paths in (
        ("ZIP member", archive_members),
        ("MANIFEST.sha256 entry", manifest_paths),
    ):
        for relative in paths:
            origins.setdefault(PurePosixPath(relative), set()).add(origin)

    for descendant in sorted(origins, key=lambda path: path.as_posix()):
        for parent in descendant.parents:
            if not parent.parts:
                break
            if parent not in origins:
                continue
            parent_origins = " and ".join(sorted(origins[parent]))
            descendant_origins = " and ".join(sorted(origins[descendant]))
            raise RuntimeError(
                "archive path prefix collision: file path "
                f"{parent.as_posix()!r} declared by {parent_origins} is an exact "
                f"parent of {descendant.as_posix()!r} declared by "
                f"{descendant_origins}"
            )


def _validate_fixed_metadata(info: zipfile.ZipInfo) -> None:
    if info.date_time != FIXED_ZIP_TIMESTAMP:
        raise RuntimeError(f"non-deterministic ZIP timestamp: {info.filename}")
    if info.compress_type != zipfile.ZIP_STORED:
        raise RuntimeError(f"non-deterministic ZIP compression: {info.filename}")
    if info.create_system != 3:
        raise RuntimeError(f"ZIP member must use the Unix metadata platform: {info.filename}")
    unix_mode = info.external_attr >> 16
    if stat.S_ISLNK(unix_mode):
        raise RuntimeError(f"symbolic links are forbidden: {info.filename}")
    if not stat.S_ISREG(unix_mode):
        raise RuntimeError(f"ZIP member must be a regular file: {info.filename}")
    if unix_mode & 0o777 != 0o644:
        raise RuntimeError(f"unexpected ZIP permission mode: {info.filename}")


def _validate_forbidden_path(
    relative: str,
    *,
    canonical_evidence_directory: str | None = None,
) -> None:
    path = PurePosixPath(relative)
    evidence_parts = (
        PurePosixPath(canonical_evidence_directory).parts
        if canonical_evidence_directory is not None
        else ()
    )
    for index, part in enumerate(path.parts):
        if part not in FORBIDDEN_PARTS:
            continue
        if (
            len(evidence_parts) == 2
            and len(path.parts) > len(evidence_parts)
            and index == 1
            and path.parts[:2] == evidence_parts
        ):
            continue
        raise RuntimeError(f"forbidden delivery path: {relative}")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise RuntimeError(f"forbidden delivery suffix: {relative}")


def _validate_evidence_artifact_bindings(
    contents: dict[str, bytes],
    evidence_directory: str,
) -> tuple[str | None, dict[str, Any]]:
    manifest_path = f"{evidence_directory}/run_manifest.json"
    document = _strict_json(
        contents[manifest_path], "evidence run_manifest.json"
    )
    if not isinstance(document, dict):
        raise RuntimeError("evidence run_manifest.json must contain an object")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise RuntimeError("evidence run_manifest.json artifacts must be a list")

    seen: set[str] = set()
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise RuntimeError(f"evidence artifact record {index} must be an object")
        relative = record.get("path")
        if not isinstance(relative, str):
            raise RuntimeError(f"evidence artifact record {index} has no path")
        path = PurePosixPath(relative)
        if (
            path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or "." in path.parts
            or "\\" in relative
            or path.as_posix() != relative
        ):
            raise RuntimeError(f"unsafe evidence artifact path: {relative!r}")
        if relative in seen:
            raise RuntimeError(f"duplicate evidence artifact binding: {relative}")
        seen.add(relative)

        member_path = f"{evidence_directory}/{relative}"
        if member_path not in contents:
            raise RuntimeError(f"evidence artifact is not packaged: {relative}")
        expected_size = record.get("size_bytes")
        expected_digest = record.get("sha256")
        if (
            isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
            or expected_size < 0
        ):
            raise RuntimeError(f"evidence artifact {relative} has invalid size_bytes")
        if (
            not isinstance(expected_digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None
        ):
            raise RuntimeError(f"evidence artifact {relative} has invalid SHA-256")
        content = contents[member_path]
        if len(content) != expected_size:
            raise RuntimeError(
                f"evidence artifact {relative} size mismatch: expected "
                f"{expected_size}, found {len(content)}"
            )
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != expected_digest:
            raise RuntimeError(
                f"evidence artifact {relative} SHA-256 mismatch: expected "
                f"{expected_digest}, found {actual_digest}"
            )

    missing = sorted(REQUIRED_ARTIFACT_BINDINGS - seen)
    if missing:
        raise RuntimeError(
            "evidence run_manifest.json is missing required artifact bindings: "
            + ", ".join(missing)
        )

    source = document.get("source")
    if not isinstance(source, dict):
        return None, document
    source_commit = source.get("commit_sha")
    if source_commit is None:
        return None, document
    if (
        not isinstance(source_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
    ):
        raise RuntimeError("evidence run_manifest.json source commit is invalid")
    return source_commit, document


def _validate_packaging_readme_links(contents: dict[str, bytes]) -> None:
    """Validate only inline relative links in the packaged delivery README."""
    try:
        readme = contents["packaging/README.md"].decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError("packaging/README.md is not UTF-8") from error

    readme_parent = PurePosixPath("packaging")
    search_from = 0
    while True:
        marker = readme.find("](", search_from)
        if marker < 0:
            break
        search_from = marker + 2
        opening = readme.rfind("[", 0, marker)
        if opening < 0:
            continue
        if opening > 0 and readme[opening - 1] == "!":
            backslash_count = 0
            cursor = opening - 2
            while cursor >= 0 and readme[cursor] == "\\":
                backslash_count += 1
                cursor -= 1
            if backslash_count % 2 == 0:
                continue
        closing = readme.find(")", marker + 2)
        if closing < 0:
            raise RuntimeError(
                "unsupported inline Markdown link syntax in packaging/README.md"
            )
        label = readme[opening + 1 : marker]
        target = readme[marker + 2 : closing]
        if not label or "\n" in label or "\r" in label or "]" in label:
            raise RuntimeError(
                "unsupported inline Markdown link syntax in "
                f"packaging/README.md: {label!r}"
            )
        if (
            not target
            or target != target.strip()
            or any(character.isspace() for character in target)
            or any(character in target for character in "<>()\"'")
        ):
            raise RuntimeError(
                "unsupported inline Markdown link syntax in "
                f"packaging/README.md: {target!r}"
            )
        if target.startswith(("#", "/")) or URI_SCHEME.match(target) is not None:
            continue
        relative_target = target.split("#", 1)[0]
        path = PurePosixPath(relative_target)
        if (
            not relative_target
            or path.is_absolute()
            or ".." in path.parts
            or "." in path.parts
            or "\\" in relative_target
            or path.as_posix() != relative_target
        ):
            raise RuntimeError(
                f"unsafe relative Markdown link in packaging/README.md: {target!r}"
            )
        resolved = (readme_parent / path).as_posix()
        if resolved not in contents:
            raise RuntimeError(
                "broken relative Markdown link in packaging/README.md: "
                f"{target!r}"
            )


def _read_archive_snapshot(archive_path: Path) -> tuple[bytes, str]:
    """Read one regular ZIP inode once without following the final symlink."""
    try:
        path_metadata = os.lstat(archive_path)
    except OSError as error:
        raise OSError(f"cannot inspect delivery archive {archive_path}: {error}") from error
    if stat.S_ISLNK(path_metadata.st_mode):
        raise OSError(f"delivery archive must not be a symbolic link: {archive_path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(archive_path, flags)
    except OSError as error:
        raise OSError(f"cannot open delivery archive {archive_path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError(f"delivery archive is not a regular file: {archive_path}")
        chunks: list[bytes] = []
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks), digest.hexdigest()
            chunks.append(chunk)
            digest.update(chunk)
    finally:
        os.close(descriptor)


def _read_and_validate_archive(
    archive_path: Path,
    archive_content: bytes,
) -> tuple[str, dict[str, bytes], dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(archive_content)) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise RuntimeError("delivery archive contains duplicate member names")
        if names != sorted(names):
            raise RuntimeError("ZIP members are not in lexicographic path order")
        parsed = [_validate_member_name(name) for name in names]
        roots = {path.parts[0] for path in parsed}
        if len(roots) != 1:
            raise RuntimeError("delivery archive must contain exactly one root directory")
        archive_root = roots.pop()
        if archive_root != archive_path.stem:
            raise RuntimeError(
                f"archive root {archive_root!r} does not match filename {archive_path.name!r}"
            )
        by_relative = {
            path.relative_to(archive_root).as_posix(): info
            for path, info in zip(parsed, infos)
        }
        if "MANIFEST.sha256" not in by_relative:
            raise RuntimeError("delivery archive is missing MANIFEST.sha256")
        manifest = _parse_manifest(archive.read(by_relative["MANIFEST.sha256"]))
        _validate_no_path_prefix_collisions(set(by_relative), set(manifest))
        archive_members = set(by_relative) - {"MANIFEST.sha256"}
        listed_members = set(manifest)
        missing = sorted(listed_members - archive_members)
        unlisted = sorted(archive_members - listed_members)
        if missing:
            raise RuntimeError("manifest paths missing from archive: " + ", ".join(missing))
        if unlisted:
            raise RuntimeError("unlisted archive members: " + ", ".join(unlisted))

        contents: dict[str, bytes] = {}
        for relative, expected_digest in sorted(manifest.items()):
            info = by_relative[relative]
            _validate_fixed_metadata(info)
            content = archive.read(info)
            actual_digest = hashlib.sha256(content).hexdigest()
            if actual_digest != expected_digest:
                raise RuntimeError(
                    f"SHA-256 mismatch for {relative}: expected {expected_digest}, "
                    f"found {actual_digest}"
                )
            if b"\r" in content:
                raise RuntimeError(f"non-LF line ending found in {relative}")
            contents[relative] = content
        _validate_fixed_metadata(by_relative["MANIFEST.sha256"])

    missing_required = sorted(REQUIRED_DELIVERY_PATHS - set(contents))
    if missing_required:
        raise RuntimeError(
            "delivery archive is missing required paths: " + ", ".join(missing_required)
        )
    _validate_packaging_readme_links(contents)
    build_info = _strict_json(contents["BUILD_INFO.json"], "BUILD_INFO.json")
    if not isinstance(build_info, dict):
        raise RuntimeError("BUILD_INFO.json must contain an object")
    expected_fields = {
        "schema_version": BUILD_INFO_SCHEMA,
        "version": "0.2.0",
        "source_tree_dirty": False,
        "package_filename": archive_path.name,
        "archive_root": archive_root,
        "distribution": DISTRIBUTION_STATUS,
    }
    for key, expected in expected_fields.items():
        if build_info.get(key) != expected:
            raise RuntimeError(
                f"BUILD_INFO.json field {key!r} must be {expected!r}, "
                f"found {build_info.get(key)!r}"
            )
    source_commit = build_info.get("source_commit")
    source_commit_short = build_info.get("source_commit_short")
    if (
        not isinstance(source_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
        or source_commit_short != source_commit[:12]
        or not archive_root.endswith("+" + source_commit[:12])
    ):
        raise RuntimeError("BUILD_INFO.json source commit identity is inconsistent")
    for path_field, digest_field in (
        ("evidence_manifest", "evidence_manifest_sha256"),
        ("report", "report_sha256"),
    ):
        relative = build_info.get(path_field)
        if not isinstance(relative, str) or relative not in contents:
            raise RuntimeError(f"BUILD_INFO.json {path_field!r} does not name a packaged file")
        if hashlib.sha256(contents[relative]).hexdigest() != build_info.get(digest_field):
            raise RuntimeError(f"BUILD_INFO.json {digest_field!r} is inconsistent")
    evidence_directory = build_info.get("evidence_directory")
    if (
        not isinstance(evidence_directory, str)
        or not evidence_directory.startswith("results/")
        or PurePosixPath(evidence_directory).as_posix() != evidence_directory
        or ".." in PurePosixPath(evidence_directory).parts
    ):
        raise RuntimeError("BUILD_INFO.json evidence_directory is invalid")
    expected_evidence_manifest = f"{evidence_directory}/run_manifest.json"
    if build_info.get("evidence_manifest") != expected_evidence_manifest:
        raise RuntimeError("BUILD_INFO.json evidence manifest is outside its evidence directory")
    missing_evidence = sorted(
        filename
        for filename in REQUIRED_EVIDENCE_FILENAMES
        if f"{evidence_directory}/{filename}" not in contents
    )
    if missing_evidence:
        raise RuntimeError(
            "evidence directory is missing required files: " + ", ".join(missing_evidence)
        )
    report_path = build_info.get("report")
    if (
        not isinstance(report_path, str)
        or not report_path.startswith("reports/")
        or not report_path.endswith(".md")
        or PurePosixPath(report_path).as_posix() != report_path
        or ".." in PurePosixPath(report_path).parts
    ):
        raise RuntimeError("BUILD_INFO.json report path is invalid")
    evidence_source_commit = build_info.get("evidence_source_commit")
    evidence_source_matches = build_info.get("evidence_source_matches_package_source")
    manifest_source_commit, evidence_manifest = _validate_evidence_artifact_bindings(
        contents,
        evidence_directory,
    )
    if evidence_source_commit != manifest_source_commit:
        raise RuntimeError(
            "BUILD_INFO.json evidence source does not match run_manifest.json"
        )
    if evidence_source_commit is None:
        if evidence_source_matches is not None:
            raise RuntimeError("BUILD_INFO.json evidence-source match state is inconsistent")
    elif (
        not isinstance(evidence_source_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", evidence_source_commit) is None
        or evidence_source_matches != (evidence_source_commit == source_commit)
    ):
        raise RuntimeError("BUILD_INFO.json evidence source commit is inconsistent")
    if evidence_manifest.get("evidence_level") == "formal":
        if evidence_manifest.get("report_intent") != "delivery":
            raise RuntimeError("formal evidence requires report_intent='delivery'")
        if (
            evidence_source_commit != source_commit
            or evidence_source_matches is not True
        ):
            raise RuntimeError(
                "formal evidence source binding must match the package source commit"
            )
        evidence_parts = PurePosixPath(evidence_directory).parts
        canonical_evidence_directory = (
            evidence_directory
            if (
                len(evidence_parts) == 2
                and evidence_parts[0] == "results"
                and BUNDLE_ID_PATTERN.fullmatch(evidence_parts[1]) is not None
            )
            else None
        )
    else:
        canonical_evidence_directory = None
    for relative in contents:
        _validate_forbidden_path(
            relative,
            canonical_evidence_directory=canonical_evidence_directory,
        )
    declaration = contents["packaging/INTERNAL_EVALUATION_ONLY.md"].decode("utf-8")
    if DISTRIBUTION_STATUS not in declaration:
        raise RuntimeError("internal-evaluation declaration is missing its required status")
    return archive_root, contents, build_info


def _extract_contents(destination: Path, archive_root: str, contents: dict[str, bytes]) -> Path:
    root = destination / archive_root
    root.mkdir(parents=True)
    for relative, content in sorted(contents.items()):
        target = root.joinpath(*PurePosixPath(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o644)
    manifest_content = "".join(
        f"{hashlib.sha256(content).hexdigest()}  {relative}\n"
        for relative, content in sorted(contents.items())
    ).encode("utf-8")
    manifest_path = root / "MANIFEST.sha256"
    manifest_path.write_bytes(manifest_content)
    manifest_path.chmod(0o644)
    return root


def _load_trusted_report_generator() -> object:
    path = Path(__file__).resolve().with_name("generate_test_report.py")
    module_name = "csc3_delivery_verifier_report_contract"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load trusted report generator: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _validate_formal_package_semantics(
    contents: dict[str, bytes],
    build_info: dict[str, Any],
) -> None:
    manifest_path = build_info["evidence_manifest"]
    manifest = _strict_json(contents[manifest_path], "evidence run_manifest.json")
    if not isinstance(manifest, dict):
        raise RuntimeError("evidence run_manifest.json must contain an object")
    if manifest.get("evidence_level") != "formal":
        return
    if manifest.get("report_intent") != "delivery":
        raise RuntimeError("formal evidence requires report_intent='delivery'")

    evidence_directory = build_info["evidence_directory"]
    evidence_parts = PurePosixPath(evidence_directory).parts
    if (
        len(evidence_parts) != 2
        or evidence_parts[0] != "results"
        or BUNDLE_ID_PATTERN.fullmatch(evidence_parts[1]) is None
    ):
        raise RuntimeError("formal evidence directory does not use the canonical mapping")
    bundle_id = evidence_parts[1]
    expected_report = f"reports/{bundle_id}-test-report.zh-CN.md"
    if build_info["report"] != expected_report:
        raise RuntimeError("formal report does not use the canonical archive mapping")

    evidence_prefix = evidence_directory + "/"
    packaged_evidence = {
        relative[len(evidence_prefix) :]
        for relative in contents
        if relative.startswith(evidence_prefix)
    }
    if packaged_evidence != REQUIRED_FORMAL_EVIDENCE_FILENAMES:
        raise RuntimeError(
            "formal evidence directory must contain exactly the five required files"
        )

    with tempfile.TemporaryDirectory(
        prefix="csc3-delivery-formal-evidence-"
    ) as temporary:
        evidence_root = Path(temporary) / "evidence"
        evidence_root.mkdir()
        for name in sorted(REQUIRED_FORMAL_EVIDENCE_FILENAMES):
            evidence_root.joinpath(name).write_bytes(
                contents[f"{evidence_prefix}{name}"]
            )
        report_generator = _load_trusted_report_generator()
        try:
            bundle = report_generator.validate_evidence_bundle(
                evidence_root / "run_manifest.json"
            )
        except RuntimeError as error:
            raise RuntimeError(
                f"formal evidence semantic validation failed: {error}"
            ) from error
        if bundle.report_status != "PASS":
            raise RuntimeError("formal evidence did not recompute to report status PASS")
        canonical_report = report_generator.render_report(bundle).encode("utf-8")
    if contents[expected_report] != canonical_report:
        raise RuntimeError("formal package report is not byte-identical to canonical report")


def run_checked(command: list[str], cwd: Path) -> None:
    """Run one clean-room command, preserving its command and working directory."""
    print(f"+ cwd={cwd} command={json.dumps(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def run_clean_room_checks(
    package_root: Path,
    *,
    cmake: str = "cmake",
    ctest: str = "ctest",
    command_runner: CommandRunner = run_checked,
) -> None:
    """Configure, build, and test the demo and its external consumer."""
    command_runner([cmake, "--preset", "delivery"], package_root)
    command_runner(
        [cmake, "--build", "--preset", "delivery", "--config", "Release", "--parallel"],
        package_root,
    )
    delivery_build = package_root / "build" / "delivery"
    inventory_script = package_root / "scripts" / "check_ctest_inventory.py"
    junit_script = package_root / "scripts" / "check_ctest_junit.py"
    expected_tests = package_root / "tests" / "ctest" / "expected-ci-tests.txt"
    delivery_junit = delivery_build / "ctest.xml"
    command_runner(
        [
            sys.executable,
            str(inventory_script),
            "--build-dir",
            str(delivery_build),
            "--expected",
            str(expected_tests),
            "--label",
            "ci",
            "--ctest",
            ctest,
        ],
        package_root,
    )
    command_runner(
        [
            ctest,
            "--preset",
            "delivery",
            "-C",
            "Release",
            "--label-regex",
            "^ci$",
            "--output-on-failure",
            "--no-tests=error",
            "--output-junit",
            str(delivery_junit),
        ],
        package_root,
    )
    command_runner(
        [
            sys.executable,
            str(junit_script),
            "--junit",
            str(delivery_junit),
            "--expected-tests",
            "10",
        ],
        package_root,
    )

    consumer_source = package_root / "tests" / "external_consumer"
    consumer_build = package_root.parent / "external-consumer-build"
    command_runner(
        [
            cmake,
            "-S",
            str(consumer_source),
            "-B",
            str(consumer_build),
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCSC3_DEMO_REQUIRE_OPENMP=ON",
            "-DCSC3_DEMO_WARNINGS_AS_ERRORS=ON",
        ],
        package_root.parent,
    )
    command_runner(
        [cmake, "--build", str(consumer_build), "--config", "Release", "--parallel"],
        package_root.parent,
    )
    consumer_junit = consumer_build / "ctest.xml"
    command_runner(
        [
            ctest,
            "--test-dir",
            str(consumer_build),
            "-C",
            "Release",
            "-R",
            "^Csc3DemoExternalConsumer$",
            "--output-on-failure",
            "--no-tests=error",
            "--output-junit",
            str(consumer_junit),
        ],
        package_root.parent,
    )
    command_runner(
        [
            sys.executable,
            str(junit_script),
            "--junit",
            str(consumer_junit),
            "--expected-tests",
            "1",
        ],
        package_root.parent,
    )


def verify_delivery_package(
    archive_path: Path,
    *,
    run_clean_room: bool = True,
    cmake: str = "cmake",
    ctest: str = "ctest",
    command_runner: CommandRunner = run_checked,
) -> dict[str, Any]:
    """Verify archive integrity and optionally execute clean-room integration."""
    archive_path = Path(archive_path).absolute()
    archive_content, archive_sha256 = _read_archive_snapshot(archive_path)
    archive_root, contents, build_info = _read_and_validate_archive(
        archive_path, archive_content
    )
    _validate_formal_package_semantics(contents, build_info)
    if run_clean_room:
        _require_clean_room_python_dependencies()
        with tempfile.TemporaryDirectory(prefix="csc3-delivery-clean-room-") as temporary:
            package_root = _extract_contents(Path(temporary), archive_root, contents)
            run_clean_room_checks(
                package_root,
                cmake=cmake,
                ctest=ctest,
                command_runner=command_runner,
            )
    return {
        "status": "PASS",
        "archive": str(archive_path),
        "archive_sha256": archive_sha256,
        "source_commit": build_info["source_commit"],
        "evidence_source_commit": build_info["evidence_source_commit"],
        "evidence_source_matches_package_source": build_info[
            "evidence_source_matches_package_source"
        ],
        "distribution": build_info["distribution"],
        "verified_file_count": len(contents),
        "clean_room_executed": run_clean_room,
    }


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="verify paths, metadata, build information, and SHA-256 without building",
    )
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--ctest", default="ctest")
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = _argument_parser().parse_args(arguments)
    try:
        result = verify_delivery_package(
            options.archive,
            run_clean_room=not options.manifest_only,
            cmake=options.cmake,
            ctest=options.ctest,
        )
    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        ValueError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
