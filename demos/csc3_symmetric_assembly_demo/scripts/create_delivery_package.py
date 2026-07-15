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
from pathlib import Path, PurePosixPath
from typing import Iterable, NamedTuple


DEMO_VERSION = "0.2.0"
PACKAGE_BASENAME = "csc3-symmetric-assembly-demo"
BUILD_INFO_SCHEMA = "csc3-demo-build-info-v1"
DISTRIBUTION_STATUS = "INTERNAL EVALUATION ONLY"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_FILE_MODE = stat.S_IFREG | 0o644
BUNDLE_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
FULL_COMMIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
GIT_OBJECT_OVERRIDE_ENVIRONMENT = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_REPLACE_REF_BASE",
    "GIT_WORK_TREE",
)


class _CreatedArchive(NamedTuple):
    path: Path
    sha256: str


STATIC_EXACT_PATHS = {
    ".clang-format",
    "CMakeLists.txt",
    "CMakePresets.json",
    "README.md",
    "MIGRATION.md",
    "requirements-test.txt",
    "docs/api-and-naming-contract.md",
    "scripts/create_delivery_package.py",
    "scripts/check_ctest_inventory.py",
    "scripts/check_ctest_junit.py",
    "scripts/finalize_delivery.py",
    "scripts/generate_test_report.py",
    "scripts/run_benchmark.py",
    "scripts/validate_acceptance_record.py",
    "scripts/verify_delivery_package.py",
    "packaging/ACCEPTANCE_CHECKLIST.zh-CN.md",
    "packaging/ACCEPTANCE_RECORD.schema.json",
    "packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md",
    "packaging/README.md",
    "packaging/THIRD_PARTY_NOTICES.md",
    "packaging/INTERNAL_EVALUATION_ONLY.md",
    "packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md",
    "packaging/TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md",
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
EXTERNAL_FORMAL_EVIDENCE_FILES = {
    "benchmark_samples.csv",
    "benchmark_summary.json",
    "ctest.xml",
    "run_manifest.json",
    "summary.md",
}
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
        raise DeliveryPackageError(
            f"{label} is not strict UTF-8 JSON: {error}"
        ) from error

    def inspect(item: object, location: str) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise DeliveryPackageError(
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


def _git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in GIT_OBJECT_OVERRIDE_ENVIRONMENT:
        environment.pop(name, None)
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return environment


def _run_git(
    repository_root: Path,
    arguments: Iterable[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=repository_root,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_environment(),
    )


def _git_text(repository_root: Path, arguments: Iterable[str]) -> str:
    return _run_git(repository_root, arguments).stdout.decode("utf-8").strip()


def _discover_repository_root(demo_root: Path) -> Path:
    result = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-C",
            str(demo_root),
            "rev-parse",
            "--show-toplevel",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_git_environment(),
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


def _assert_outside_repository(
    path: Path,
    repository_root: Path,
    description: str,
) -> None:
    try:
        path.relative_to(repository_root)
    except ValueError:
        return
    raise DeliveryPackageError(
        f"{description} must resolve outside the Git repository"
    )


def _file_signature(file_stat: os.stat_result) -> tuple[int, ...]:
    return (
        file_stat.st_dev,
        file_stat.st_ino,
        stat.S_IFMT(file_stat.st_mode),
        file_stat.st_size,
        file_stat.st_mtime_ns,
        file_stat.st_ctime_ns,
    )


def _read_regular_external_file(
    path: Path,
    description: str,
) -> tuple[Path, bytes]:
    requested = Path(path).expanduser()
    try:
        path_stat = requested.lstat()
    except OSError as error:
        raise DeliveryPackageError(
            f"{description} is missing or inaccessible: {requested}"
        ) from error
    if stat.S_ISLNK(path_stat.st_mode) or not stat.S_ISREG(path_stat.st_mode):
        raise DeliveryPackageError(
            f"{description} must be regular and not a symbolic link"
        )

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(requested, flags)
    except OSError as error:
        raise DeliveryPackageError(f"cannot open {description}: {requested}") from error
    try:
        opened_stat = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened_stat.st_mode)
            or _file_signature(opened_stat) != _file_signature(path_stat)
        ):
            raise DeliveryPackageError(f"{description} changed while being opened")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            content = stream.read()
        completed_stat = os.fstat(descriptor)
    except OSError as error:
        raise DeliveryPackageError(f"cannot read {description}: {requested}") from error
    finally:
        os.close(descriptor)

    try:
        final_stat = requested.lstat()
        resolved = requested.resolve(strict=True)
    except OSError as error:
        raise DeliveryPackageError(f"{description} changed while being read") from error
    if (
        stat.S_ISLNK(final_stat.st_mode)
        or not stat.S_ISREG(final_stat.st_mode)
        or len(content) != completed_stat.st_size
        or _file_signature(opened_stat) != _file_signature(completed_stat)
        or _file_signature(completed_stat) != _file_signature(final_stat)
    ):
        raise DeliveryPackageError(f"{description} changed while being read")
    return resolved, content


def _read_external_formal_evidence(
    directory: Path,
    repository_root: Path,
) -> dict[str, bytes]:
    requested = Path(directory).expanduser()
    try:
        directory_stat = requested.lstat()
    except OSError as error:
        raise DeliveryPackageError(
            f"external evidence directory is missing or inaccessible: {requested}"
        ) from error
    if stat.S_ISLNK(directory_stat.st_mode) or not stat.S_ISDIR(
        directory_stat.st_mode
    ):
        raise DeliveryPackageError(
            "external evidence directory must be a regular directory, not a symbolic link"
        )
    try:
        resolved = requested.resolve(strict=True)
        entries = {entry.name: entry for entry in requested.iterdir()}
    except OSError as error:
        raise DeliveryPackageError(
            f"cannot inspect external evidence directory: {requested}"
        ) from error
    _assert_outside_repository(
        resolved,
        repository_root,
        "external evidence directory",
    )
    actual_names = set(entries)
    if actual_names != EXTERNAL_FORMAL_EVIDENCE_FILES:
        missing = sorted(EXTERNAL_FORMAL_EVIDENCE_FILES - actual_names)
        extra = sorted(actual_names - EXTERNAL_FORMAL_EVIDENCE_FILES)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise DeliveryPackageError(
            "external evidence directory must contain exactly the five required files"
            + (" (" + "; ".join(details) + ")" if details else "")
        )

    contents: dict[str, bytes] = {}
    for name in sorted(EXTERNAL_FORMAL_EVIDENCE_FILES):
        _, contents[name] = _read_regular_external_file(
            entries[name],
            f"external evidence file {name}",
        )
    try:
        final_directory_stat = requested.lstat()
    except OSError as error:
        raise DeliveryPackageError(
            "external evidence directory changed while being read"
        ) from error
    if (
        stat.S_ISLNK(final_directory_stat.st_mode)
        or not stat.S_ISDIR(final_directory_stat.st_mode)
        or _file_signature(directory_stat) != _file_signature(final_directory_stat)
    ):
        raise DeliveryPackageError(
            "external evidence directory changed while being read"
        )
    return contents


def _read_external_report(
    report_path: Path,
    repository_root: Path,
) -> bytes:
    resolved, content = _read_regular_external_file(report_path, "external report")
    _assert_outside_repository(resolved, repository_root, "external report")
    return content


def _capture_head_commit(repository_root: Path) -> str:
    try:
        commit_sha = _git_text(
            repository_root,
            ["rev-parse", "--verify", "HEAD^{commit}"],
        )
    except subprocess.CalledProcessError as error:
        raise DeliveryPackageError(
            error.stderr.decode("utf-8", errors="replace").strip()
            or "git could not resolve HEAD to a commit"
        ) from error
    if FULL_COMMIT_SHA_PATTERN.fullmatch(commit_sha) is None:
        raise DeliveryPackageError(
            "git did not resolve HEAD to a full 40-character commit SHA"
        )
    return commit_sha


def _assert_head_matches_commit(repository_root: Path, commit_sha: str) -> None:
    current_commit = _capture_head_commit(repository_root)
    if current_commit != commit_sha:
        raise DeliveryPackageError(
            "repository HEAD changed during packaging: "
            f"expected {commit_sha}, found {current_commit}"
        )


def _assert_canonical_git_object_interpretation(repository_root: Path) -> None:
    overridden = [
        name for name in GIT_OBJECT_OVERRIDE_ENVIRONMENT if os.environ.get(name)
    ]
    if overridden:
        raise DeliveryPackageError(
            "Git object interpretation environment overrides are forbidden: "
            + ", ".join(overridden)
        )

    replace_refs = _git_text(
        repository_root,
        ["for-each-ref", "--format=%(refname)", "refs/replace/"],
    )
    if replace_refs:
        raise DeliveryPackageError(
            "Git replace refs are forbidden during delivery packaging"
        )
    if _git_text(repository_root, ["rev-parse", "--is-shallow-repository"]) != "false":
        raise DeliveryPackageError(
            "a complete non-shallow repository is required for delivery packaging"
        )

    for label, git_path in (
        ("legacy grafts", "info/grafts"),
        ("object alternates", "objects/info/alternates"),
    ):
        configured_path = Path(
            _git_text(repository_root, ["rev-parse", "--git-path", git_path])
        )
        if not configured_path.is_absolute():
            configured_path = repository_root / configured_path
        try:
            configured = configured_path.is_file() and configured_path.stat().st_size > 0
        except OSError as error:
            raise DeliveryPackageError(
                f"cannot inspect Git {label} configuration: {configured_path}"
            ) from error
        if configured:
            raise DeliveryPackageError(
                f"Git {label} are forbidden during delivery packaging"
            )


def _assert_clean_repository(repository_root: Path, commit_sha: str) -> None:
    for arguments, description in (
        (["diff", "--quiet", commit_sha, "--"], "tracked working-tree changes"),
        (["diff", "--cached", "--quiet", commit_sha, "--"], "staged changes"),
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


def _assert_repository_matches_commit(
    repository_root: Path,
    commit_sha: str,
) -> None:
    _assert_canonical_git_object_interpretation(repository_root)
    _assert_head_matches_commit(repository_root, commit_sha)
    _assert_clean_repository(repository_root, commit_sha)
    _assert_head_matches_commit(repository_root, commit_sha)


def _commit_tree(
    repository_root: Path,
    demo_repository_path: str,
    commit_sha: str,
) -> dict[str, tuple[str, str]]:
    raw = _run_git(
        repository_root,
        [
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            commit_sha,
            "--",
            demo_repository_path,
        ],
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


def _validate_selected_git_paths(
    entries: dict[str, tuple[str, str]],
    selected: set[str],
) -> None:
    missing_exact = sorted(path for path in STATIC_EXACT_PATHS if path not in selected)
    if missing_exact:
        raise DeliveryPackageError(
            "required delivery files are absent from the captured commit: "
            + ", ".join(missing_exact)
        )
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


def _select_static_paths(entries: dict[str, tuple[str, str]]) -> list[str]:
    selected = {
        path
        for path in entries
        if path in STATIC_EXACT_PATHS or _matches_any(path, STATIC_GLOB_PATHS)
    }
    _validate_selected_git_paths(entries, selected)
    return sorted(selected)


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
    selected = set(_select_static_paths(entries))
    for name in sorted(REQUIRED_EVIDENCE_FILES | OPTIONAL_EVIDENCE_FILES):
        path = evidence_prefix + name
        if path in entries:
            selected.add(path)
    selected.add(report_path)

    missing_evidence = sorted(
        name
        for name in REQUIRED_EVIDENCE_FILES
        if evidence_prefix + name not in selected
    )
    if missing_evidence:
        raise DeliveryPackageError(
            "required evidence files are absent from the captured commit: "
            + ", ".join(missing_evidence)
        )
    if report_path not in entries:
        raise DeliveryPackageError(
            f"report is absent from the captured commit: {report_path}"
        )
    _validate_selected_git_paths(entries, selected)
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


def _load_trusted_report_generator() -> object:
    path = Path(__file__).resolve().with_name("generate_test_report.py")
    module_name = "csc3_delivery_package_report_contract"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise DeliveryPackageError(f"cannot load trusted report generator: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _load_evidence_manifest(content: bytes) -> dict[str, object]:
    document = _strict_json(content, "evidence run_manifest.json")
    if not isinstance(document, dict):
        raise DeliveryPackageError("evidence run_manifest.json must contain an object")
    return document


def _evidence_source_commit(evidence_manifest: dict[str, object]) -> str | None:
    source = evidence_manifest.get("source")
    if not isinstance(source, dict):
        return None
    candidate = source.get("commit_sha")
    if candidate is None:
        return None
    if (
        not isinstance(candidate, str)
        or len(candidate) != 40
        or any(character not in "0123456789abcdef" for character in candidate)
    ):
        raise DeliveryPackageError(
            "evidence run_manifest.json source.commit_sha is invalid"
        )
    return candidate


def _committed_members(
    repository_root: Path,
    entries: dict[str, tuple[str, str]],
    selected_paths: Iterable[str],
) -> dict[str, bytes]:
    return {
        path: _normalize_text(path, _read_blob(repository_root, entries[path][1]))
        for path in selected_paths
    }


def _prepare_output_directory(path: Path) -> Path:
    """Return a real canonical output directory without following a leaf symlink."""
    absolute = Path(os.path.abspath(path))
    try:
        canonical_parent = absolute.parent.resolve(strict=True)
    except OSError as error:
        raise DeliveryPackageError(
            f"output directory parent cannot be resolved: {absolute.parent}: {error}"
        ) from error
    # The existing parent is an explicit caller-controlled trust boundary.  It
    # is canonicalized before the output leaf is inspected or created so macOS
    # system aliases such as /var -> /private/var remain usable, while a leaf
    # symlink can never redirect archive publication.
    absolute = canonical_parent / absolute.name
    try:
        metadata = absolute.lstat()
    except FileNotFoundError:
        try:
            absolute.mkdir(mode=0o755)
        except OSError as error:
            raise DeliveryPackageError(
                f"cannot create output directory {absolute}: {error}"
            ) from error
        metadata = absolute.lstat()
    except OSError as error:
        raise DeliveryPackageError(
            f"cannot inspect output directory {absolute}: {error}"
        ) from error
    if stat.S_ISLNK(metadata.st_mode):
        raise DeliveryPackageError(
            f"output directory must be a real directory, not a symlink: {absolute}"
        )
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeliveryPackageError(f"output directory is not a directory: {absolute}")
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as error:
        raise DeliveryPackageError(
            f"output directory cannot be resolved: {absolute}: {error}"
        ) from error
    if resolved != absolute:
        raise DeliveryPackageError(f"output directory is not canonical: {absolute}")
    return resolved


def _publish_archive_without_replacement(
    temporary_path: Path, archive_path: Path
) -> None:
    """Atomically publish one same-filesystem archive and never replace a path."""
    try:
        archive_path.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise DeliveryPackageError(
            f"cannot inspect archive destination {archive_path}: {error}"
        ) from error
    else:
        raise DeliveryPackageError(
            f"archive destination already exists and will not be replaced: {archive_path}"
        )
    try:
        os.link(temporary_path, archive_path)
    except FileExistsError as error:
        raise DeliveryPackageError(
            f"archive destination appeared during publication and was not replaced: "
            f"{archive_path}"
        ) from error
    except OSError as error:
        raise DeliveryPackageError(
            f"cannot publish archive without replacement at {archive_path}: {error}"
        ) from error
    os.unlink(temporary_path)


def _finish_delivery_package(
    *,
    members: dict[str, bytes],
    repository_root: Path,
    commit_sha: str,
    source_date_epoch: int,
    evidence_directory: str,
    report_path: str,
    evidence_source_commit: str | None,
    content_source: str,
    output_directory: Path,
) -> _CreatedArchive:
    short_sha = commit_sha[:12]
    archive_stem = f"{PACKAGE_BASENAME}-v{DEMO_VERSION}+{short_sha}"
    archive_name = archive_stem + ".zip"
    evidence_manifest_path = f"{evidence_directory}/run_manifest.json"
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
        "evidence_directory": evidence_directory,
        "evidence_manifest": evidence_manifest_path,
        "evidence_manifest_sha256": hashlib.sha256(
            members[evidence_manifest_path]
        ).hexdigest(),
        "evidence_source_commit": evidence_source_commit,
        "evidence_source_matches_package_source": (
            evidence_source_commit == commit_sha
            if evidence_source_commit is not None
            else None
        ),
        "report": report_path,
        "report_sha256": hashlib.sha256(members[report_path]).hexdigest(),
        "archive_policy": {
            "content_source": content_source,
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

    output_directory = _prepare_output_directory(output_directory)
    archive_path = output_directory / archive_name
    archive_sha256: str | None = None
    with tempfile.TemporaryDirectory(
        prefix=f".{archive_name}.staging-",
        dir=output_directory,
    ) as staging_name:
        staging_directory = Path(staging_name)
        os.chmod(staging_directory, stat.S_IRWXU)
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{archive_name}.",
            suffix=".tmp",
            dir=staging_directory,
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
            temporary_file.seek(0)
            digest = hashlib.sha256()
            for block in iter(lambda: temporary_file.read(1024 * 1024), b""):
                digest.update(block)
            archive_sha256 = digest.hexdigest()
        _assert_repository_matches_commit(repository_root, commit_sha)
        _publish_archive_without_replacement(temporary_path, archive_path)
    assert archive_sha256 is not None
    return _CreatedArchive(path=archive_path, sha256=archive_sha256)


def _create_delivery_package_result(
    demo_root: Path,
    evidence_directory: Path,
    report_path: Path,
    output_directory: Path,
) -> _CreatedArchive:
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

    commit_sha = _capture_head_commit(repository_root)
    _assert_repository_matches_commit(repository_root, commit_sha)
    source_date_epoch = int(
        _git_text(repository_root, ["show", "-s", "--format=%ct", commit_sha])
    )
    entries = _commit_tree(repository_root, demo_repository_path, commit_sha)
    selected_paths = _select_paths(entries, evidence_relative, report_relative)

    members = _committed_members(repository_root, entries, selected_paths)
    evidence_manifest_path = f"{evidence_relative}/run_manifest.json"
    evidence_manifest = _load_evidence_manifest(members[evidence_manifest_path])
    _validate_evidence_artifact_bindings(
        evidence_manifest,
        evidence_relative,
        members,
    )
    return _finish_delivery_package(
        members=members,
        repository_root=repository_root,
        commit_sha=commit_sha,
        source_date_epoch=source_date_epoch,
        evidence_directory=evidence_relative,
        report_path=report_relative,
        evidence_source_commit=_evidence_source_commit(evidence_manifest),
        content_source="committed Git blobs from captured source commit",
        output_directory=output_directory,
    )


def _create_external_formal_package_result(
    demo_root: Path,
    external_evidence_directory: Path,
    external_report_path: Path,
    bundle_id: str,
    output_directory: Path,
) -> _CreatedArchive:
    """Create a deterministic package with externally supplied formal evidence."""
    if not isinstance(bundle_id, str) or BUNDLE_ID_PATTERN.fullmatch(bundle_id) is None:
        raise DeliveryPackageError(
            "external formal bundle ID must match [a-z0-9][a-z0-9._-]{0,127}"
        )
    demo_root = demo_root.resolve()
    if not demo_root.is_dir() or demo_root.is_symlink():
        raise ValueError(f"demo root must be a real directory: {demo_root}")
    repository_root = _discover_repository_root(demo_root)
    demo_repository_path = _repository_relative(demo_root, repository_root, "demo root")
    external_evidence_contents = _read_external_formal_evidence(
        external_evidence_directory,
        repository_root,
    )
    external_report_bytes = _read_external_report(
        external_report_path,
        repository_root,
    )

    commit_sha = _capture_head_commit(repository_root)
    _assert_repository_matches_commit(repository_root, commit_sha)
    source_date_epoch = int(
        _git_text(repository_root, ["show", "-s", "--format=%ct", commit_sha])
    )
    entries = _commit_tree(repository_root, demo_repository_path, commit_sha)
    members = _committed_members(
        repository_root,
        entries,
        _select_static_paths(entries),
    )
    evidence_relative = f"results/{bundle_id}"
    report_relative = f"reports/{bundle_id}-test-report.zh-CN.md"
    for name in sorted(EXTERNAL_FORMAL_EVIDENCE_FILES):
        member_path = f"{evidence_relative}/{name}"
        members[member_path] = _normalize_text(
            member_path,
            external_evidence_contents[name],
        )

    evidence_manifest_path = f"{evidence_relative}/run_manifest.json"
    evidence_manifest = _load_evidence_manifest(members[evidence_manifest_path])
    _validate_evidence_artifact_bindings(
        evidence_manifest,
        evidence_relative,
        members,
    )
    report_generator = _load_trusted_report_generator()
    with tempfile.TemporaryDirectory(
        prefix="csc3-delivery-external-evidence-"
    ) as temporary:
        snapshot_root = Path(temporary) / "evidence"
        snapshot_root.mkdir()
        for name, content in sorted(external_evidence_contents.items()):
            snapshot_root.joinpath(name).write_bytes(content)
        try:
            evidence_bundle = report_generator.validate_evidence_bundle(
                snapshot_root / "run_manifest.json"
            )
        except RuntimeError as error:
            raise DeliveryPackageError(
                f"external formal evidence is invalid: {error}"
            ) from error
        bundle_manifest = evidence_bundle.manifest
        if (
            bundle_manifest.get("evidence_level") != "formal"
            or bundle_manifest.get("report_intent") != "delivery"
            or evidence_bundle.report_status != "PASS"
        ):
            raise DeliveryPackageError(
                "external formal evidence requires evidence_level='formal', "
                "report_intent='delivery', and recomputed report_status='PASS'"
            )
        canonical_report = report_generator.render_report(evidence_bundle).encode(
            "utf-8"
        )

    evidence_source_commit = _evidence_source_commit(evidence_manifest)
    if evidence_source_commit != commit_sha:
        raise DeliveryPackageError(
            "external formal evidence source commit does not match "
            "the captured package commit"
        )
    if external_report_bytes != canonical_report:
        raise DeliveryPackageError(
            "external report is not byte-identical to the canonical report"
        )
    members[report_relative] = canonical_report
    return _finish_delivery_package(
        members=members,
        repository_root=repository_root,
        commit_sha=commit_sha,
        source_date_epoch=source_date_epoch,
        evidence_directory=evidence_relative,
        report_path=report_relative,
        evidence_source_commit=evidence_source_commit,
        content_source=(
            "committed Git blobs from captured source commit plus validated "
            "external formal evidence"
        ),
        output_directory=output_directory,
    )


def create_delivery_package(
    demo_root: Path,
    evidence_directory: Path,
    report_path: Path,
    output_directory: Path,
) -> Path:
    """Create a deterministic ZIP from committed delivery-whitelist blobs."""
    return _create_delivery_package_result(
        demo_root,
        evidence_directory,
        report_path,
        output_directory,
    ).path


def create_external_formal_package(
    demo_root: Path,
    external_evidence_directory: Path,
    external_report_path: Path,
    bundle_id: str,
    output_directory: Path,
) -> Path:
    """Create a deterministic package with externally supplied formal evidence."""
    return _create_external_formal_package_result(
        demo_root,
        external_evidence_directory,
        external_report_path,
        bundle_id,
        output_directory,
    ).path


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--external-evidence-dir", type=Path)
    parser.add_argument("--external-report", type=Path)
    parser.add_argument("--bundle-id")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument(
        "--demo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    return parser


def _validated_cli_mode(
    parser: argparse.ArgumentParser,
    options: argparse.Namespace,
) -> str:
    legacy_values = (options.evidence_dir, options.report)
    external_values = (
        options.external_evidence_dir,
        options.external_report,
        options.bundle_id,
    )
    any_legacy = any(value is not None for value in legacy_values)
    any_external = any(value is not None for value in external_values)
    if any_legacy and any_external:
        parser.error("legacy and external-formal options are mutually exclusive")
    if any_external:
        if not all(value is not None for value in external_values):
            parser.error(
                "the three external options --external-evidence-dir, "
                "--external-report, and --bundle-id must appear together"
            )
        if BUNDLE_ID_PATTERN.fullmatch(options.bundle_id) is None:
            parser.error(
                "external formal bundle ID must match "
                "[a-z0-9][a-z0-9._-]{0,127}"
            )
        return "external-formal"
    if not all(value is not None for value in legacy_values):
        parser.error(
            "legacy options --evidence-dir and --report must appear together"
        )
    return "committed"


def main(arguments: list[str] | None = None) -> int:
    parser = _argument_parser()
    options = parser.parse_args(arguments)
    mode = _validated_cli_mode(parser, options)
    output_directory = options.out_dir or options.demo_root / "dist"
    try:
        if mode == "external-formal":
            created = _create_external_formal_package_result(
                options.demo_root,
                options.external_evidence_dir,
                options.external_report,
                options.bundle_id,
                output_directory,
            )
        else:
            created = _create_delivery_package_result(
                options.demo_root,
                options.evidence_dir,
                options.report,
                output_directory,
            )
    except (DeliveryPackageError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"archive": str(created.path), "sha256": created.sha256},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
