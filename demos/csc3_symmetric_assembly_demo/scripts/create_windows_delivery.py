#!/usr/bin/env python3
"""创建并验证 Issue #54 的 Windows 中文交付 ZIP。"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from generate_windows_delivery_report import (  # noqa: E402
    ReportContractError,
    load_and_validate_evidence,
)


DELIVERY_SCHEMA_VERSION = "csc3-demo-windows-delivery-v1"
SOURCE_ROOT_NAME = "csc3_symmetric_assembly_demo"
OUTER_ROOT_NAME = "CSC3对称稀疏组装Demo_Windows_x64_研究院交付"
SOURCE_ZIP_NAME = "csc3_symmetric_assembly_demo_source.zip"
CHECKSUM_NAME = "06_校验/SHA256SUMS.txt"
DELIVERY_MANIFEST_NAME = "06_校验/delivery_manifest.json"
INPUT_CHECKSUM_NAME = "06_校验/INPUT_SHA256.txt"
TEXT_SUFFIXES = {
    ".bat",
    ".cmake",
    ".cpp",
    ".csv",
    ".h",
    ".json",
    ".log",
    ".md",
    ".ps1",
    ".py",
    ".stderr",
    ".stdout",
    ".txt",
    ".yaml",
    ".yml",
}
SOURCE_EXACT_FILES = (
    "CMakeLists.txt",
    "CMakePresets.json",
    "README.md",
    "MIGRATION.md",
    "requirements-test.txt",
    "requirements-windows-delivery.txt",
    "docs/api-and-naming-contract.md",
    "scripts/run_windows_process_benchmark.py",
    "scripts/generate_windows_delivery_report.py",
    "scripts/create_windows_delivery.py",
    "tests/python/test_run_windows_process_benchmark.py",
    "tests/python/test_generate_windows_delivery_report.py",
    "tests/python/test_create_windows_delivery.py",
    "tests/external_consumer/CMakeLists.txt",
    "tests/external_consumer/main.cpp",
)
SOURCE_PREFIXES = (
    "include",
    "src",
    "tools/include",
    "tools/src",
    "tests/consumer",
    "tests/ctest",
)
SOURCE_GLOBS = ("tests/*.cpp",)
FORBIDDEN_SEGMENTS = {
    ".git",
    ".idea",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "cache",
    "cmake-build-debug",
    "cmake-build-release",
    "dist",
    "out",
}
REQUIRED_SOURCE_MEMBERS = {
    f"{SOURCE_ROOT_NAME}/CMakeLists.txt",
    f"{SOURCE_ROOT_NAME}/README.md",
    f"{SOURCE_ROOT_NAME}/include/csc3_demo/assembly_helper.h",
    f"{SOURCE_ROOT_NAME}/src/assembly_helper.cpp",
    f"{SOURCE_ROOT_NAME}/tools/src/benchmark.cpp",
    f"{SOURCE_ROOT_NAME}/tools/src/validation.cpp",
    f"{SOURCE_ROOT_NAME}/tests/external_consumer/CMakeLists.txt",
    f"{SOURCE_ROOT_NAME}/tests/external_consumer/main.cpp",
}


class DeliveryContractError(RuntimeError):
    """交付输入、ZIP 布局或校验和违反验收契约。"""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.flag_bits |= 0x800
    return info


def _write_zip(path: Path, members: Mapping[str, bytes]) -> None:
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(members):
            archive.writestr(_zip_info(name), members[name])


def _write_zip_bytes(members: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(members):
            archive.writestr(_zip_info(name), members[name])
    return buffer.getvalue()


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise DeliveryContractError(f"ZIP 成员路径不安全：{name!r}")
    return path.as_posix()


def _check_forbidden_segments(name: str) -> None:
    parts = {part.lower() for part in PurePosixPath(name).parts}
    forbidden = sorted(parts & FORBIDDEN_SEGMENTS)
    if forbidden:
        raise DeliveryContractError(
            f"ZIP 成员包含禁止目录 {forbidden}：{name}"
        )
    if name.lower().endswith((".pyc", ".pyo", ".pdb", ".obj", ".exe", ".dll")):
        raise DeliveryContractError(f"ZIP 不得包含构建/缓存产物：{name}")


def _decode_text(data: bytes, label: str) -> str:
    encodings = ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    raise DeliveryContractError(f"文本文件不是可识别的 Unicode 编码：{label}")


def _root_variants(root: Path) -> tuple[str, ...]:
    # Windows 的临时目录可能以 8.3 短路径出现；保留调用方传入的绝对别名，
    # 由上层同时提供短路径与 resolve() 后的长路径，才能完整清理日志。
    text = str(root.absolute())
    variants = {
        text,
        text.replace("\\", "/"),
        text.replace("\\", "\\\\"),
        text.replace("/", "\\"),
        text.replace("/", "\\\\"),
    }
    return tuple(sorted(variants, key=len, reverse=True))


def _sanitize_text(
    text: str,
    roots: Sequence[tuple[Path, str]],
) -> str:
    sanitized = text
    for root, replacement in roots:
        for variant in _root_variants(root):
            sanitized = re.sub(
                re.escape(variant),
                replacement,
                sanitized,
                flags=re.IGNORECASE,
            )
    return sanitized.replace("\r\n", "\n").replace("\r", "\n")


def _contains_windows_absolute_path(text: str) -> bool:
    direct = re.search(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])", text)
    json_escaped = re.search(r"(?<![A-Za-z0-9])[A-Za-z]:\\\\(?!\\)", text)
    return direct is not None or json_escaped is not None


def _text_bytes(
    data: bytes,
    label: str,
    roots: Sequence[tuple[Path, str]],
) -> bytes:
    text = _sanitize_text(_decode_text(data, label), roots)
    if _contains_windows_absolute_path(text):
        raise DeliveryContractError(f"文本仍包含 Windows 宿主绝对路径：{label}")
    return text.encode("utf-8")


def _read_member_bytes(
    path: Path,
    member_name: str,
    roots: Sequence[tuple[Path, str]],
) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {
        "CMakeLists.txt",
        "SHA256SUMS",
    }:
        return _text_bytes(data, member_name, roots)
    return data


def _source_paths(demo_root: Path) -> list[Path]:
    candidates: set[Path] = set()
    for relative in SOURCE_EXACT_FILES:
        path = demo_root / relative
        if not path.is_file():
            raise DeliveryContractError(f"源码交付缺少必需文件：{relative}")
        candidates.add(path)
    for prefix in SOURCE_PREFIXES:
        directory = demo_root / prefix
        if not directory.is_dir():
            raise DeliveryContractError(f"源码交付缺少必需目录：{prefix}")
        candidates.update(path for path in directory.rglob("*") if path.is_file())
    for pattern in SOURCE_GLOBS:
        candidates.update(path for path in demo_root.glob(pattern) if path.is_file())
    result = sorted(candidates)
    for path in result:
        relative = path.relative_to(demo_root).as_posix()
        _check_forbidden_segments(relative)
    return result


def create_source_zip(
    demo_root: Path,
    sanitize_roots: Sequence[tuple[Path, str]],
) -> bytes:
    members: dict[str, bytes] = {}
    for path in _source_paths(demo_root):
        relative = path.relative_to(demo_root).as_posix()
        name = f"{SOURCE_ROOT_NAME}/{relative}"
        members[name] = _read_member_bytes(path, name, sanitize_roots)
    missing = REQUIRED_SOURCE_MEMBERS - members.keys()
    if missing:
        raise DeliveryContractError(f"源码 ZIP 缺少必需成员：{sorted(missing)}")
    return _write_zip_bytes(members)


def _run_git_bytes(repository_root: Path, arguments: Sequence[str]) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = ""
        if isinstance(error, subprocess.CalledProcessError):
            detail = error.stderr.decode("utf-8", errors="replace").strip()
        raise DeliveryContractError(
            f"无法从 Git 读取交付源码：{detail or 'git 命令执行失败'}"
        ) from error
    return completed.stdout


def _resolve_commit(repository_root: Path, requested_commit: str) -> str:
    requested = requested_commit.lower()
    if not re.fullmatch(r"[0-9a-f]{40}", requested):
        raise DeliveryContractError("交付源码提交 SHA 必须是 40 位小写十六进制")
    resolved = _run_git_bytes(
        repository_root,
        ["rev-parse", "--verify", f"{requested}^{{commit}}"],
    ).decode("ascii", errors="strict").strip().lower()
    if resolved != requested:
        raise DeliveryContractError("交付源码提交无法解析为指定的完整 Git commit")
    return resolved


def _select_committed_source_paths(
    repository_root: Path,
    demo_relative: str,
    commit_sha: str,
) -> list[str]:
    prefix = demo_relative.rstrip("/") + "/"
    raw_names = _run_git_bytes(
        repository_root,
        ["ls-tree", "-r", "--name-only", "-z", commit_sha, "--", demo_relative],
    )
    available: set[str] = set()
    for raw_name in raw_names.split(b"\0"):
        if not raw_name:
            continue
        repository_relative = raw_name.decode("utf-8", errors="strict")
        if repository_relative.startswith(prefix):
            available.add(repository_relative.removeprefix(prefix))

    selected: set[str] = set()
    for relative in SOURCE_EXACT_FILES:
        if relative not in available:
            raise DeliveryContractError(
                f"交付提交中的源码缺少必需文件：{relative}"
            )
        selected.add(relative)
    for source_prefix in SOURCE_PREFIXES:
        matches = {
            relative
            for relative in available
            if relative.startswith(source_prefix.rstrip("/") + "/")
        }
        if not matches:
            raise DeliveryContractError(
                f"交付提交中的源码缺少必需目录：{source_prefix}"
            )
        selected.update(matches)
    for pattern in SOURCE_GLOBS:
        selected.update(
            relative
            for relative in available
            if PurePosixPath(relative).match(pattern)
        )
    for relative in selected:
        _check_forbidden_segments(relative)
    return sorted(selected)


def create_source_zip_from_commit(
    repository_root: Path,
    demo_root: Path,
    commit_sha: str,
    sanitize_roots: Sequence[tuple[Path, str]],
) -> bytes:
    """只从指定 Git commit 读取源码，避免把工作树漂移伪装成该提交。"""

    repository_root = repository_root.resolve()
    demo_root = demo_root.resolve()
    try:
        demo_relative = demo_root.relative_to(repository_root).as_posix()
    except ValueError as error:
        raise DeliveryContractError("demo-root 必须位于仓库内") from error
    resolved_commit = _resolve_commit(repository_root, commit_sha)
    members: dict[str, bytes] = {}
    for relative in _select_committed_source_paths(
        repository_root,
        demo_relative,
        resolved_commit,
    ):
        repository_relative = f"{demo_relative}/{relative}"
        data = _run_git_bytes(
            repository_root,
            ["show", f"{resolved_commit}:{repository_relative}"],
        )
        member_name = f"{SOURCE_ROOT_NAME}/{relative}"
        suffix = PurePosixPath(relative).suffix.lower()
        if suffix in TEXT_SUFFIXES or PurePosixPath(relative).name == "CMakeLists.txt":
            data = _text_bytes(data, member_name, sanitize_roots)
        members[member_name] = data
    missing = REQUIRED_SOURCE_MEMBERS - members.keys()
    if missing:
        raise DeliveryContractError(f"源码 ZIP 缺少必需成员：{sorted(missing)}")
    return _write_zip_bytes(members)


def _collect_directory(
    directory: Path,
    destination_prefix: str,
    sanitize_roots: Sequence[tuple[Path, str]],
) -> dict[str, bytes]:
    if not directory.is_dir():
        raise DeliveryContractError(f"交付目录不存在：{directory.name}")
    members: dict[str, bytes] = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        name = _safe_member_name(f"{destination_prefix}/{relative}")
        _check_forbidden_segments(name)
        members[name] = _read_member_bytes(path, name, sanitize_roots)
    if not members:
        raise DeliveryContractError(f"交付目录不得为空：{directory.name}")
    return members


def _rewrite_report_links(text: str) -> str:
    replacements = {
        "benchmark_samples.csv": "../03_性能原始证据/benchmark_samples.csv",
        "benchmark_summary.json": "../03_性能原始证据/benchmark_summary.json",
        "run_manifest.json": "../03_性能原始证据/run_manifest.json",
    }
    result = text
    for label, target in replacements.items():
        escaped_label = re.escape(label)
        result = re.sub(
            rf"(\[(?:{escaped_label}|`{escaped_label}`)\])\([^)]+\)",
            rf"\1({target})",
            result,
        )
    return result


def _find_single_report(report_dir: Path) -> Path:
    reports = sorted(report_dir.glob("*.md"))
    if len(reports) != 1:
        raise DeliveryContractError("报告目录必须且只能包含一个顶层 Markdown 报告")
    return reports[0]


def _read_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DeliveryContractError(f"无法读取 {label}") from error
    if not isinstance(value, dict):
        raise DeliveryContractError(f"{label} 顶层必须是对象")
    return value


def _validate_input_evidence(
    performance_dir: Path,
    build_dir: Path,
    internal_evaluation: Path,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    try:
        manifest, summary, _rows, build_evidence = load_and_validate_evidence(
            performance_dir,
            build_dir / "build_evidence.json",
        )
    except ReportContractError as error:
        raise DeliveryContractError(f"正式证据校验失败：{error}") from error
    input_facts = manifest.get("input")
    if not isinstance(input_facts, dict):
        raise DeliveryContractError("manifest 缺少输入追溯")
    sha256 = str(input_facts.get("sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise DeliveryContractError("WindHub 输入 SHA-256 非法")
    if input_facts.get("git_lfs_materialized") is not True:
        raise DeliveryContractError("WindHub Git LFS 实体未确认物化")
    if input_facts.get("matches_head_lfs_pointer") is not True:
        raise DeliveryContractError("WindHub 输入未确认匹配 HEAD LFS 指针")
    if not internal_evaluation.is_file():
        raise DeliveryContractError("缺少内部评估 Markdown")
    evaluation_text = internal_evaluation.read_text(encoding="utf-8")
    if "仅供内部评估" not in evaluation_text or "PASS" not in evaluation_text:
        raise DeliveryContractError("内部评估必须标明用途并给出 PASS/FAIL")
    return manifest, summary, build_evidence


def _delivery_readme(
    source_sha256: str,
    input_facts: Mapping[str, object],
) -> bytes:
    text = f"""# CSC3 对称稀疏组装 Demo Windows x64 交付

本包面向研究院接收方，包含可独立构建的源码 ZIP、中文测试报告、Windows 原始性能证据、MSVC/MinGW/CTest/consumer/clean-room 日志、内部评估和逐文件 SHA-256。

## 快速入口

- 源码：`01_源代码/{SOURCE_ZIP_NAME}`
- 中文报告：`02_测试报告/测试报告.md`
- 原始性能 CSV：`03_性能原始证据/benchmark_samples.csv`
- 性能汇总与进程 manifest：`03_性能原始证据/benchmark_summary.json`、`03_性能原始证据/run_manifest.json`
- 构建证据：`04_构建与CleanRoom证据/build_evidence.json`
- 内部评估：`05_内部评估/内部评估.md`
- 校验和：`06_校验/SHA256SUMS.txt`

## 校验

源码 ZIP SHA-256：`{source_sha256}`

WindHub 输入：`{input_facts.get("repository_relative_path")}`<br>
输入大小：`{input_facts.get("size_bytes")} bytes`
输入 SHA-256：`{input_facts.get("sha256")}`

使用任意 SHA-256 工具核对 `06_校验/SHA256SUMS.txt`。外层 ZIP 自身的 SHA-256 位于同目录的 `.sha256` 侧车文件；该侧车文件不在 ZIP 内，避免自引用。

## 构建边界

源码 ZIP 不包含 WindHub 大型 Git LFS 实体、构建目录、编译产物、缓存或宿主绝对路径。CTest 与最小 consumer 不依赖 WindHub 输入；如需复现实测，须从仓库 Git LFS 取得与上述 SHA-256 一致的实体文件。
"""
    return text.encode("utf-8")


def _checksum_file(members: Mapping[str, bytes]) -> bytes:
    lines = [
        f"{_sha256_bytes(data)}  {name}"
        for name, data in sorted(members.items())
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def create_delivery(options: argparse.Namespace) -> int:
    repository_root_alias = options.repository_root.absolute()
    performance_dir_alias = options.performance_evidence_dir.absolute()
    report_dir_alias = options.report_dir.absolute()
    build_dir_alias = options.build_evidence_dir.absolute()
    output_dir_alias = options.output_dir.absolute()
    repository_root = options.repository_root.resolve()
    demo_root = options.demo_root.resolve()
    performance_dir = options.performance_evidence_dir.resolve()
    report_dir = options.report_dir.resolve()
    build_dir = options.build_evidence_dir.resolve()
    internal_evaluation = options.internal_evaluation.resolve()
    output_dir = options.output_dir.resolve()
    if not (repository_root / ".git").exists():
        raise DeliveryContractError("repository-root 不是 Git 工作树根目录")
    try:
        demo_root.relative_to(repository_root)
    except ValueError as error:
        raise DeliveryContractError("demo-root 必须位于仓库内") from error

    manifest, summary, build_evidence = _validate_input_evidence(
        performance_dir,
        build_dir,
        internal_evaluation,
    )
    input_facts = manifest["input"]
    if not isinstance(input_facts, dict):
        raise DeliveryContractError("输入追溯必须是对象")
    source = manifest.get("source")
    if not isinstance(source, dict) or not re.fullmatch(
        r"[0-9a-f]{40}",
        str(source.get("commit_sha", "")),
    ):
        raise DeliveryContractError("性能 manifest 缺少完整源码提交 SHA")
    delivery_source_commit = _resolve_commit(
        repository_root,
        str(options.delivery_source_commit),
    )
    if build_evidence.get("source_performance_commit") != source.get("commit_sha"):
        raise DeliveryContractError("构建证据与性能实验源码提交不一致")
    if build_evidence.get("delivery_source_commit") != delivery_source_commit:
        raise DeliveryContractError("构建证据与交付源码提交不一致")

    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / (
        f"CSC3对称稀疏组装Demo_Windows_x64_研究院交付_{options.delivery_date}.zip"
    )
    sidecar_path = package_path.with_suffix(package_path.suffix + ".sha256")
    if package_path.exists() or sidecar_path.exists():
        raise DeliveryContractError("交付 ZIP 或侧车校验文件已存在，拒绝覆盖")

    sanitize_roots: list[tuple[Path, str]] = [
        (repository_root, "<REPOSITORY_ROOT>"),
        (repository_root_alias, "<REPOSITORY_ROOT>"),
        (performance_dir, "<PERFORMANCE_EVIDENCE_ROOT>"),
        (performance_dir_alias, "<PERFORMANCE_EVIDENCE_ROOT>"),
        (report_dir, "<REPORT_ROOT>"),
        (report_dir_alias, "<REPORT_ROOT>"),
        (build_dir, "<BUILD_EVIDENCE_ROOT>"),
        (build_dir_alias, "<BUILD_EVIDENCE_ROOT>"),
        (output_dir, "<DELIVERY_OUTPUT_ROOT>"),
        (output_dir_alias, "<DELIVERY_OUTPUT_ROOT>"),
    ]
    for index, root in enumerate(options.sanitize_root, start=1):
        sanitize_roots.append((root.absolute(), f"<HOST_ROOT_{index}>"))
        sanitize_roots.append((root.resolve(), f"<HOST_ROOT_{index}>"))

    source_zip = create_source_zip_from_commit(
        repository_root,
        demo_root,
        delivery_source_commit,
        sanitize_roots,
    )
    source_sha256 = _sha256_bytes(source_zip)
    if build_evidence.get("source_zip_sha256") != source_sha256:
        raise DeliveryContractError("构建证据中的源码 ZIP SHA-256 与实际交付源码不一致")
    root = OUTER_ROOT_NAME
    members: dict[str, bytes] = {
        f"{root}/00_交付说明/README.md": _delivery_readme(
            source_sha256,
            input_facts,
        ),
        f"{root}/01_源代码/{SOURCE_ZIP_NAME}": source_zip,
    }

    report_members = _collect_directory(
        report_dir,
        f"{root}/02_测试报告",
        sanitize_roots,
    )
    report_path = _find_single_report(report_dir)
    report_member_name = (
        f"{root}/02_测试报告/{report_path.relative_to(report_dir).as_posix()}"
    )
    report_text = _decode_text(report_members[report_member_name], report_member_name)
    report_members[report_member_name] = _rewrite_report_links(report_text).encode(
        "utf-8"
    )
    desired_report_name = f"{root}/02_测试报告/测试报告.md"
    if report_member_name != desired_report_name:
        report_members[desired_report_name] = report_members.pop(report_member_name)
    members.update(report_members)
    members.update(
        _collect_directory(
            performance_dir,
            f"{root}/03_性能原始证据",
            sanitize_roots,
        )
    )
    members.update(
        _collect_directory(
            build_dir,
            f"{root}/04_构建与CleanRoom证据",
            sanitize_roots,
        )
    )
    members[f"{root}/05_内部评估/内部评估.md"] = _read_member_bytes(
        internal_evaluation,
        "内部评估.md",
        sanitize_roots,
    )
    members[f"{root}/{INPUT_CHECKSUM_NAME}"] = (
        "WindHub input\n"
        f"path: {input_facts.get('repository_relative_path')}\n"
        f"size_bytes: {input_facts.get('size_bytes')}\n"
        f"sha256: {input_facts.get('sha256')}\n"
        "git_lfs_materialized: true\n"
        "matches_head_lfs_pointer: true\n"
    ).encode("utf-8")

    delivery_manifest = {
        "schema_version": DELIVERY_SCHEMA_VERSION,
        "status": "PASS",
        "issue": 54,
        "delivery_date": options.delivery_date,
        "source": {
            "branch": source.get("branch"),
            "commit_sha": delivery_source_commit,
            "performance_commit_sha": source.get("commit_sha"),
            "source_zip": f"01_源代码/{SOURCE_ZIP_NAME}",
            "source_zip_sha256": source_sha256,
        },
        "input": input_facts,
        "performance": {
            "status": summary.get("status"),
            "maximum_threads": (
                summary.get("configuration", {}).get("maximum_threads")
                if isinstance(summary.get("configuration"), dict)
                else None
            ),
            "warmup_count": 2,
            "repeat_count": 7,
            "sample_process_model": "one_fresh_child_process_per_sample",
            "samples_are_serialized": True,
            "peak_memory_source": "GetProcessMemoryInfo.PeakWorkingSetSize",
        },
        "build_validation": {
            "status": build_evidence.get("status"),
            "toolchains": ["MSVC + Ninja", "MinGW-w64 + Ninja"],
            "includes_ctest_consumer_clean_room": True,
        },
        "package_policy": {
            "contains_build_directories": False,
            "contains_cache_files": False,
            "contains_host_absolute_paths": False,
            "contains_windhub_lfs_entity": False,
        },
        "packaged_files_excluding_checksums": [
            {
                "path": name.removeprefix(f"{root}/"),
                "size_bytes": len(data),
                "sha256": _sha256_bytes(data),
            }
            for name, data in sorted(members.items())
        ],
    }
    members[f"{root}/{DELIVERY_MANIFEST_NAME}"] = _canonical_json(
        delivery_manifest
    )
    members[f"{root}/{CHECKSUM_NAME}"] = _checksum_file(members)

    with tempfile.TemporaryDirectory(dir=output_dir) as temporary_directory:
        candidate = Path(temporary_directory) / package_path.name
        _write_zip(candidate, members)
        verification = verify_delivery_file(candidate, check_sidecar=False)
        candidate.replace(package_path)

    package_sha256 = _sha256_file(package_path)
    sidecar_path.write_text(
        f"{package_sha256}  {package_path.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    verification = verify_delivery_file(package_path, check_sidecar=True)
    print(
        json.dumps(
            {
                "schema_version": DELIVERY_SCHEMA_VERSION,
                "status": "PASS",
                "package": str(package_path),
                "package_size_bytes": package_path.stat().st_size,
                "package_sha256": package_sha256,
                "sidecar": str(sidecar_path),
                "verification": verification,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _parse_checksums(data: bytes) -> dict[str, str]:
    checksums: dict[str, str] = {}
    text = _decode_text(data, CHECKSUM_NAME)
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise DeliveryContractError("SHA256SUMS.txt 行格式非法")
        sha256, path = match.groups()
        if path in checksums:
            raise DeliveryContractError("SHA256SUMS.txt 包含重复路径")
        checksums[path] = sha256
    return checksums


def _verify_source_zip(data: bytes) -> dict[str, object]:
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise DeliveryContractError("源码 ZIP 包含重复成员")
        normalized = {_safe_member_name(name) for name in names}
        for name in normalized:
            _check_forbidden_segments(name)
            payload = archive.read(name)
            suffix = Path(name).suffix.lower()
            if suffix in TEXT_SUFFIXES or Path(name).name == "CMakeLists.txt":
                text = _decode_text(payload, name)
                if _contains_windows_absolute_path(text):
                    raise DeliveryContractError(f"源码 ZIP 包含宿主绝对路径：{name}")
        missing = REQUIRED_SOURCE_MEMBERS - normalized
        if missing:
            raise DeliveryContractError(f"源码 ZIP 缺少成员：{sorted(missing)}")
        roots = {PurePosixPath(name).parts[0] for name in normalized}
        if roots != {SOURCE_ROOT_NAME}:
            raise DeliveryContractError("源码 ZIP 顶层目录不唯一")
        return {
            "status": "PASS",
            "member_count": len(normalized),
            "required_members_present": True,
            "forbidden_content_absent": True,
        }


def verify_delivery_file(
    package_path: Path,
    *,
    check_sidecar: bool,
) -> dict[str, object]:
    package_path = package_path.resolve()
    if not package_path.is_file():
        raise DeliveryContractError("交付 ZIP 不存在")
    if all(ord(character) < 128 for character in package_path.name):
        raise DeliveryContractError("外层 ZIP 文件名必须包含中文")
    with zipfile.ZipFile(package_path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise DeliveryContractError("外层 ZIP 包含重复成员")
        normalized = [_safe_member_name(name) for name in names]
        for name in normalized:
            _check_forbidden_segments(name)
        roots = {PurePosixPath(name).parts[0] for name in normalized}
        if roots != {OUTER_ROOT_NAME}:
            raise DeliveryContractError("外层 ZIP 必须只有一个中文顶层目录")

        checksum_member = f"{OUTER_ROOT_NAME}/{CHECKSUM_NAME}"
        manifest_member = f"{OUTER_ROOT_NAME}/{DELIVERY_MANIFEST_NAME}"
        source_member = (
            f"{OUTER_ROOT_NAME}/01_源代码/{SOURCE_ZIP_NAME}"
        )
        required = {
            f"{OUTER_ROOT_NAME}/00_交付说明/README.md",
            source_member,
            f"{OUTER_ROOT_NAME}/02_测试报告/测试报告.md",
            f"{OUTER_ROOT_NAME}/03_性能原始证据/benchmark_samples.csv",
            f"{OUTER_ROOT_NAME}/03_性能原始证据/benchmark_summary.json",
            f"{OUTER_ROOT_NAME}/03_性能原始证据/run_manifest.json",
            f"{OUTER_ROOT_NAME}/04_构建与CleanRoom证据/build_evidence.json",
            f"{OUTER_ROOT_NAME}/05_内部评估/内部评估.md",
            f"{OUTER_ROOT_NAME}/{INPUT_CHECKSUM_NAME}",
            manifest_member,
            checksum_member,
        }
        missing = required - set(normalized)
        if missing:
            raise DeliveryContractError(f"外层 ZIP 缺少成员：{sorted(missing)}")

        checksums = _parse_checksums(archive.read(checksum_member))
        expected_checksum_paths = set(normalized) - {checksum_member}
        if set(checksums) != expected_checksum_paths:
            raise DeliveryContractError("SHA256SUMS.txt 未完整覆盖全部非自引用成员")
        for name, expected in checksums.items():
            actual = _sha256_bytes(archive.read(name))
            if actual != expected:
                raise DeliveryContractError(f"成员 SHA-256 不匹配：{name}")

        delivery_manifest = json.loads(archive.read(manifest_member))
        if (
            not isinstance(delivery_manifest, dict)
            or delivery_manifest.get("schema_version") != DELIVERY_SCHEMA_VERSION
            or delivery_manifest.get("status") != "PASS"
        ):
            raise DeliveryContractError("delivery_manifest.json 非法")
        source_sha256 = _sha256_bytes(archive.read(source_member))
        source_facts = delivery_manifest.get("source")
        if (
            not isinstance(source_facts, dict)
            or not re.fullmatch(
                r"[0-9a-f]{40}",
                str(source_facts.get("commit_sha", "")),
            )
            or not re.fullmatch(
                r"[0-9a-f]{40}",
                str(source_facts.get("performance_commit_sha", "")),
            )
            or source_facts.get("source_zip_sha256") != source_sha256
        ):
            raise DeliveryContractError("源码提交或 ZIP SHA-256 与 manifest 不一致")

        for name in normalized:
            suffix = Path(name).suffix.lower()
            if suffix in TEXT_SUFFIXES or Path(name).name == "CMakeLists.txt":
                text = _decode_text(archive.read(name), name)
                if _contains_windows_absolute_path(text):
                    raise DeliveryContractError(f"交付文本包含宿主绝对路径：{name}")
        source_verification = _verify_source_zip(archive.read(source_member))

    package_sha256 = _sha256_file(package_path)
    if check_sidecar:
        sidecar = package_path.with_suffix(package_path.suffix + ".sha256")
        if not sidecar.is_file():
            raise DeliveryContractError("缺少外层 ZIP SHA-256 侧车文件")
        match = re.fullmatch(
            rf"([0-9a-f]{{64}})  {re.escape(package_path.name)}\n?",
            sidecar.read_text(encoding="utf-8"),
        )
        if match is None or match.group(1) != package_sha256:
            raise DeliveryContractError("外层 ZIP SHA-256 侧车校验失败")
    return {
        "status": "PASS",
        "package_sha256": package_sha256,
        "member_count": len(normalized),
        "all_member_checksums_match": True,
        "host_absolute_paths_absent": True,
        "forbidden_build_and_cache_content_absent": True,
        "source_zip": source_verification,
        "sidecar_checked": check_sidecar,
    }


def verify_delivery(options: argparse.Namespace) -> int:
    result = verify_delivery_file(
        options.package,
        check_sidecar=not options.skip_sidecar,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="创建并验证交付 ZIP")
    create.add_argument("--repository-root", type=Path, required=True)
    create.add_argument("--demo-root", type=Path, required=True)
    create.add_argument("--performance-evidence-dir", type=Path, required=True)
    create.add_argument("--report-dir", type=Path, required=True)
    create.add_argument("--build-evidence-dir", type=Path, required=True)
    create.add_argument("--internal-evaluation", type=Path, required=True)
    create.add_argument("--output-dir", type=Path, required=True)
    create.add_argument("--delivery-date", required=True)
    create.add_argument(
        "--delivery-source-commit",
        required=True,
        help="源码 ZIP 对应的已提交 Git SHA；性能提交另从 run_manifest 记录",
    )
    create.add_argument(
        "--sanitize-root",
        action="append",
        type=Path,
        default=[],
        help="需要从日志中替换的其他 Windows 宿主根路径，可重复指定",
    )
    create.set_defaults(handler=create_delivery)

    verify = subparsers.add_parser("verify", help="独立验证已有交付 ZIP")
    verify.add_argument("--package", type=Path, required=True)
    verify.add_argument("--skip-sidecar", action="store_true")
    verify.set_defaults(handler=verify_delivery)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        options = build_argument_parser().parse_args(arguments)
        return options.handler(options)
    except (
        DeliveryContractError,
        OSError,
        UnicodeError,
        ValueError,
        zipfile.BadZipFile,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
