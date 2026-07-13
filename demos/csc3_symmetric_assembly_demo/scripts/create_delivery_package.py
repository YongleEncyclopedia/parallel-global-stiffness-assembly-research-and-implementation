#!/usr/bin/env python3
"""Create the reproducible CSC3 demo source-delivery archive.

Only committed blobs selected by the explicit delivery whitelist are read.
This prevents working-tree line-ending conversion, generated files, and local
edits from silently changing a delivery artifact.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable


DEMO_VERSION = "0.2.0"
PACKAGE_BASENAME = "csc3-symmetric-assembly-demo"
BUILD_INFO_SCHEMA = "csc3-demo-build-info-v1"
DISTRIBUTION_STATUS = "INTERNAL EVALUATION ONLY"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_FILE_MODE = stat.S_IFREG | 0o644

STATIC_EXACT_PATHS = {
    ".clang-format",
    "CMakeLists.txt",
    "CMakePresets.json",
    "README.md",
    "MIGRATION.md",
    "docs/api-and-naming-contract.md",
    "scripts/create_delivery_package.py",
    "scripts/check_ctest_inventory.py",
    "scripts/check_ctest_junit.py",
    "scripts/generate_test_report.py",
    "scripts/run_benchmark.py",
    "scripts/verify_delivery_package.py",
    "packaging/README.md",
    "packaging/THIRD_PARTY_NOTICES.md",
    "packaging/INTERNAL_EVALUATION_ONLY.md",
    "tests/ctest/expected-ci-tests.txt",
    "tests/external_consumer/CMakeLists.txt",
}
STATIC_GLOB_PATHS = (
    "include/**/*.h",
    "include/**/*.hpp",
    "src/*.cc",
    "src/*.cpp",
    "src/**/*.cc",
    "src/**/*.cpp",
    "tools/include/**/*.h",
    "tools/include/**/*.hpp",
    "tools/src/*.cc",
    "tools/src/*.cpp",
    "tools/src/**/*.cc",
    "tools/src/**/*.cpp",
    "tests/*.cc",
    "tests/*.cpp",
    "tests/**/*.cc",
    "tests/**/*.cpp",
    "tests/**/*.py",
)
REQUIRED_GROUPS = (
    ("public header", ("include/**/*.h", "include/**/*.hpp")),
    ("implementation source", ("src/*.cc", "src/*.cpp", "src/**/*.cc", "src/**/*.cpp")),
    ("CTest source", ("tests/*.cc", "tests/*.cpp", "tests/**/*.cc", "tests/**/*.cpp")),
    ("Python contract test", ("tests/**/*.py",)),
)
REQUIRED_EVIDENCE_FILES = {
    "benchmark_samples.csv",
    "benchmark_summary.json",
    "ctest.xml",
    "run_manifest.json",
}
REQUIRED_ARTIFACT_BINDINGS = REQUIRED_EVIDENCE_FILES - {"run_manifest.json"}
OPTIONAL_EVIDENCE_FILES = {"README.md", "summary.md"}
TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cmake",
    ".cpp",
    ".csv",
    ".h",
    ".hpp",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".xml",
}


class DeliveryPackageError(RuntimeError):
    """A deterministic delivery package cannot be created."""


def _run_git(
    repository_root: Path,
    arguments: Iterable[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_text(repository_root: Path, arguments: Iterable[str]) -> str:
    return _run_git(repository_root, arguments).stdout.decode("utf-8").strip()


def _discover_repository_root(demo_root: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(demo_root), "rev-parse", "--show-toplevel"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def _repository_relative(path: Path, repository_root: Path, description: str) -> str:
    try:
        relative = path.resolve().relative_to(repository_root)
    except ValueError as error:
        raise ValueError(f"{description} must be inside the repository") from error
    return relative.as_posix()


def _demo_relative(path: Path, demo_root: Path, description: str) -> str:
    try:
        relative = path.resolve().relative_to(demo_root)
    except ValueError as error:
        raise ValueError(f"{description} must be inside the demo") from error
    if relative == Path("."):
        raise ValueError(f"{description} must identify content inside the demo")
    return relative.as_posix()


def _assert_clean_repository(repository_root: Path) -> None:
    for arguments, description in (
        (["diff", "--quiet", "HEAD", "--"], "tracked working-tree changes"),
        (["diff", "--cached", "--quiet", "--"], "staged changes"),
    ):
        result = _run_git(repository_root, arguments, check=False)
        if result.returncode == 1:
            raise DeliveryPackageError(
                f"repository is dirty: {description} must be committed first"
            )
        if result.returncode != 0:
            raise DeliveryPackageError(
                result.stderr.decode("utf-8", errors="replace").strip()
                or "git could not inspect repository state"
            )

    untracked = _run_git(
        repository_root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ).stdout
    names = [name.decode("utf-8") for name in untracked.split(b"\0") if name]
    if names:
        preview = ", ".join(names[:3])
        if len(names) > 3:
            preview += ", ..."
        raise DeliveryPackageError(
            f"repository has untracked files; commit, ignore, or remove them: {preview}"
        )


def _head_tree(repository_root: Path, demo_repository_path: str) -> dict[str, tuple[str, str]]:
    raw = _run_git(
        repository_root,
        ["ls-tree", "-r", "-z", "--full-tree", "HEAD", "--", demo_repository_path],
    ).stdout
    prefix = f"{demo_repository_path}/"
    entries: dict[str, tuple[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split()
        repository_path = encoded_path.decode("utf-8")
        if not repository_path.startswith(prefix):
            continue
        relative = repository_path[len(prefix):]
        if object_type != "blob":
            raise DeliveryPackageError(f"unsupported Git object in demo: {relative}")
        entries[relative] = (mode, object_id)
    return entries


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _select_paths(
    entries: dict[str, tuple[str, str]],
    evidence_directory: str,
    report_path: str,
) -> list[str]:
    if not evidence_directory.startswith("results/"):
        raise ValueError("evidence directory must be below the demo results/ directory")
    if not report_path.startswith("reports/") or not report_path.endswith(".md"):
        raise ValueError("report must be a Markdown file below the demo reports/ directory")

    evidence_prefix = evidence_directory.rstrip("/") + "/"
    selected = {
        path
        for path in entries
        if path in STATIC_EXACT_PATHS or _matches_any(path, STATIC_GLOB_PATHS)
    }
    for name in sorted(REQUIRED_EVIDENCE_FILES | OPTIONAL_EVIDENCE_FILES):
        path = evidence_prefix + name
        if path in entries:
            selected.add(path)
    selected.add(report_path)

    missing_exact = sorted(path for path in STATIC_EXACT_PATHS if path not in selected)
    if missing_exact:
        raise DeliveryPackageError(
            "required delivery files are not committed at HEAD: " + ", ".join(missing_exact)
        )
    missing_evidence = sorted(
        name
        for name in REQUIRED_EVIDENCE_FILES
        if evidence_prefix + name not in selected
    )
    if missing_evidence:
        raise DeliveryPackageError(
            "required evidence files are not committed at HEAD: "
            + ", ".join(missing_evidence)
        )
    if report_path not in entries:
        raise DeliveryPackageError(f"report is not committed at HEAD: {report_path}")
    for description, patterns in REQUIRED_GROUPS:
        if not any(_matches_any(path, patterns) for path in selected):
            raise DeliveryPackageError(f"delivery whitelist has no {description}")

    for path in selected:
        mode, _ = entries[path]
        if mode not in {"100644", "100755"}:
            raise DeliveryPackageError(
                f"delivery path must be a regular Git file, not mode {mode}: {path}"
            )
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in path:
            raise DeliveryPackageError(f"unsafe delivery path: {path}")
    return sorted(selected)


def _read_blob(repository_root: Path, object_id: str) -> bytes:
    return _run_git(repository_root, ["cat-file", "blob", object_id]).stdout


def _normalize_text(path: str, content: bytes) -> bytes:
    pure = PurePosixPath(path)
    if pure.name in {"CMakeLists.txt", ".clang-format"} or pure.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DeliveryPackageError(f"delivery text is not UTF-8: {path}") from error
        if "\x00" in text:
            raise DeliveryPackageError(f"delivery text contains NUL: {path}")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    raise DeliveryPackageError(f"non-text file is outside the source-package contract: {path}")


def _validate_evidence_artifact_bindings(
    evidence_manifest: object,
    evidence_directory: str,
    members: dict[str, bytes],
) -> None:
    if not isinstance(evidence_manifest, dict):
        raise DeliveryPackageError("evidence run_manifest.json must contain an object")
    artifacts = evidence_manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise DeliveryPackageError("evidence run_manifest.json artifacts must be a list")

    seen: set[str] = set()
    for index, record in enumerate(artifacts):
        if not isinstance(record, dict):
            raise DeliveryPackageError(
                f"evidence artifact record {index} must contain an object"
            )
        relative = record.get("path")
        if not isinstance(relative, str):
            raise DeliveryPackageError(f"evidence artifact record {index} has no path")
        path = PurePosixPath(relative)
        if (
            path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or "." in path.parts
            or "\\" in relative
            or path.as_posix() != relative
        ):
            raise DeliveryPackageError(f"unsafe evidence artifact path: {relative!r}")
        if relative in seen:
            raise DeliveryPackageError(f"duplicate evidence artifact binding: {relative}")
        seen.add(relative)

        member_path = f"{evidence_directory.rstrip('/')}/{relative}"
        if member_path not in members:
            raise DeliveryPackageError(
                f"evidence artifact is not selected for delivery: {relative}"
            )
        expected_size = record.get("size_bytes")
        expected_digest = record.get("sha256")
        if (
            isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
            or expected_size < 0
        ):
            raise DeliveryPackageError(
                f"evidence artifact {relative} has an invalid size_bytes"
            )
        if (
            not isinstance(expected_digest, str)
            or len(expected_digest) != 64
            or any(character not in "0123456789abcdef" for character in expected_digest)
        ):
            raise DeliveryPackageError(
                f"evidence artifact {relative} has an invalid SHA-256"
            )
        content = members[member_path]
        if len(content) != expected_size:
            raise DeliveryPackageError(
                f"evidence artifact {relative} normalized size differs from "
                f"run_manifest.json: expected {expected_size}, found {len(content)}"
            )
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != expected_digest:
            raise DeliveryPackageError(
                f"evidence artifact {relative} normalized SHA-256 differs from "
                f"run_manifest.json: expected {expected_digest}, found {actual_digest}"
            )

    missing = sorted(REQUIRED_ARTIFACT_BINDINGS - seen)
    if missing:
        raise DeliveryPackageError(
            "evidence run_manifest.json is missing required artifact bindings: "
            + ", ".join(missing)
        )


def _manifest_bytes(members: dict[str, bytes]) -> bytes:
    lines = [
        f"{hashlib.sha256(content).hexdigest()}  {path}\n"
        for path, content in sorted(members.items())
    ]
    return "".join(lines).encode("utf-8")


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = FIXED_FILE_MODE << 16
    info.flag_bits = 0x800
    return info


def create_delivery_package(
    demo_root: Path,
    evidence_directory: Path,
    report_path: Path,
    output_directory: Path,
) -> Path:
    """Create a deterministic ZIP from committed delivery-whitelist blobs."""
    demo_root = demo_root.resolve()
    if not demo_root.is_dir() or demo_root.is_symlink():
        raise ValueError(f"demo root must be a real directory: {demo_root}")
    repository_root = _discover_repository_root(demo_root)
    demo_repository_path = _repository_relative(demo_root, repository_root, "demo root")
    evidence_relative = _demo_relative(
        evidence_directory, demo_root, "evidence directory"
    )
    report_relative = _demo_relative(report_path, demo_root, "report")

    _assert_clean_repository(repository_root)
    commit_sha = _git_text(repository_root, ["rev-parse", "HEAD"])
    source_date_epoch = int(_git_text(repository_root, ["show", "-s", "--format=%ct", "HEAD"]))
    entries = _head_tree(repository_root, demo_repository_path)
    selected_paths = _select_paths(entries, evidence_relative, report_relative)

    short_sha = commit_sha[:12]
    archive_stem = f"{PACKAGE_BASENAME}-v{DEMO_VERSION}+{short_sha}"
    archive_name = archive_stem + ".zip"
    members = {
        path: _normalize_text(path, _read_blob(repository_root, entries[path][1]))
        for path in selected_paths
    }
    evidence_manifest_path = f"{evidence_relative}/run_manifest.json"
    try:
        evidence_manifest = json.loads(members[evidence_manifest_path])
    except json.JSONDecodeError as error:
        raise DeliveryPackageError("evidence run_manifest.json is invalid JSON") from error
    _validate_evidence_artifact_bindings(
        evidence_manifest,
        evidence_relative,
        members,
    )
    evidence_source_commit = None
    if isinstance(evidence_manifest, dict):
        source = evidence_manifest.get("source")
        if isinstance(source, dict):
            candidate = source.get("commit_sha")
            if candidate is not None:
                if (
                    not isinstance(candidate, str)
                    or len(candidate) != 40
                    or any(character not in "0123456789abcdef" for character in candidate)
                ):
                    raise DeliveryPackageError(
                        "evidence run_manifest.json source.commit_sha is invalid"
                    )
                evidence_source_commit = candidate
    build_info = {
        "schema_version": BUILD_INFO_SCHEMA,
        "version": DEMO_VERSION,
        "source_commit": commit_sha,
        "source_commit_short": short_sha,
        "source_tree_dirty": False,
        "source_date_epoch": source_date_epoch,
        "package_filename": archive_name,
        "archive_root": archive_stem,
        "distribution": DISTRIBUTION_STATUS,
        "evidence_directory": evidence_relative,
        "evidence_manifest": evidence_manifest_path,
        "evidence_manifest_sha256": hashlib.sha256(
            members[evidence_manifest_path]
        ).hexdigest(),
        "evidence_source_commit": evidence_source_commit,
        "evidence_source_matches_package_source": (
            evidence_source_commit == commit_sha if evidence_source_commit is not None else None
        ),
        "report": report_relative,
        "report_sha256": hashlib.sha256(members[report_relative]).hexdigest(),
        "archive_policy": {
            "content_source": "committed Git blobs from HEAD",
            "file_order": "lexicographic UTF-8 path order",
            "file_mode": "0644",
            "line_endings": "LF for every packaged text file",
            "timestamp": "1980-01-01T00:00:00 ZIP epoch",
            "compression": "stored",
        },
    }
    members["BUILD_INFO.json"] = (
        json.dumps(build_info, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    members["MANIFEST.sha256"] = _manifest_bytes(members)

    output_directory = output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    archive_path = output_directory / archive_name
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{archive_name}.",
            suffix=".tmp",
            dir=output_directory,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            with zipfile.ZipFile(
                temporary_file, "w", compression=zipfile.ZIP_STORED
            ) as archive:
                for relative, content in sorted(members.items()):
                    archive.writestr(_zip_info(f"{archive_stem}/{relative}"), content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, archive_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return archive_path


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument(
        "--demo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = _argument_parser().parse_args(arguments)
    output_directory = options.out_dir or options.demo_root / "dist"
    try:
        archive_path = create_delivery_package(
            options.demo_root,
            options.evidence_dir,
            options.report,
            output_directory,
        )
    except (DeliveryPackageError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    print(json.dumps({"archive": str(archive_path), "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
