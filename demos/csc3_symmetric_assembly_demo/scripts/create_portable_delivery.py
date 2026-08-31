#!/usr/bin/env python3
"""创建并验证 Windows WindHub 自包含源码 ZIP。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence


PACKAGE_SCHEMA_VERSION = "csc3-windhub-windows-package-v2"
PACKAGE_ROOT_NAME = "csc3-windhub-demo"
PACKAGE_MANIFEST_NAME = "PACKAGE_MANIFEST.json"
DEMO_REPOSITORY_PATH = PurePosixPath("demos/csc3_symmetric_assembly_demo")
REPOSITORY_INPUT_PATH = PurePosixPath("examples/3d-WindTurbineHub.inp")
PACKAGE_INPUT_PATH = PurePosixPath("examples/3d-WindTurbineHub.inp")
EXCLUDED_SOURCE_ROOTS = {"build", "reports", "results"}
FORBIDDEN_SEGMENTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}


class PortableDeliveryError(RuntimeError):
    """表示交付包不完整、不可信或无法安全创建。"""


def _canonical_json(value: object) -> bytes:
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_git(repository_root: Path, arguments: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise PortableDeliveryError(
            f"Git 命令失败：git {' '.join(arguments)}\n{detail}"
        )
    return completed.stdout


def _resolve_commit(repository_root: Path, requested: str) -> str:
    value = (
        _run_git(repository_root, ["rev-parse", "--verify", f"{requested}^{{commit}}"])
        .decode("ascii", errors="strict")
        .strip()
        .lower()
    )
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise PortableDeliveryError("无法解析交付源码的完整 commit SHA")
    return value


def _safe_relative_path(text: str) -> PurePosixPath:
    normalized = text.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith("/")
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(part in FORBIDDEN_SEGMENTS for part in path.parts)
        or re.match(r"^[A-Za-z]:", normalized)
    ):
        raise PortableDeliveryError(f"交付包包含不安全路径：{text!r}")
    return path


def _is_source_path(repository_relative: PurePosixPath) -> bool:
    try:
        relative = repository_relative.relative_to(DEMO_REPOSITORY_PATH)
    except ValueError:
        return False
    if not relative.parts:
        return False
    return relative.parts[0] not in EXCLUDED_SOURCE_ROOTS and not any(
        part in FORBIDDEN_SEGMENTS for part in relative.parts
    )


def _committed_source_members(
    repository_root: Path,
    commit_sha: str,
) -> dict[str, bytes]:
    listing = _run_git(
        repository_root,
        [
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            commit_sha,
            "--",
            DEMO_REPOSITORY_PATH.as_posix(),
        ],
    )
    names = [name for name in listing.decode("utf-8").split("\0") if name]
    members: dict[str, bytes] = {}
    for name in names:
        repository_relative = _safe_relative_path(name)
        if not _is_source_path(repository_relative):
            continue
        package_relative = repository_relative.relative_to(DEMO_REPOSITORY_PATH)
        members[package_relative.as_posix()] = _run_git(
            repository_root,
            ["show", f"{commit_sha}:{repository_relative.as_posix()}"],
        )
    required = {
        "README.md",
        "CMakeLists.txt",
        "include/csc3_demo/assembly_helper.h",
        "src/assembly_helper.cpp",
        "tools/src/benchmark_main.cpp",
        "examples/run_windhub.ps1",
        "examples/run_windhub.py",
        "examples/run_windhub_demo.ps1",
        "examples/run_windhub_launcher.ps1",
    }
    missing = sorted(required - members.keys())
    if missing:
        raise PortableDeliveryError(
            "交付源码提交缺少必需文件：" + ", ".join(missing)
        )
    return members


def _lfs_input_facts(
    repository_root: Path,
    commit_sha: str,
) -> tuple[dict[str, object], bytes]:
    pointer = _run_git(
        repository_root,
        ["show", f"{commit_sha}:{REPOSITORY_INPUT_PATH.as_posix()}"],
    ).decode("utf-8", errors="strict")
    lines = pointer.splitlines()
    if (
        len(lines) < 3
        or lines[0] != "version https://git-lfs.github.com/spec/v1"
        or re.fullmatch(r"oid sha256:[0-9a-f]{64}", lines[1]) is None
        or re.fullmatch(r"size [1-9][0-9]*", lines[2]) is None
    ):
        raise PortableDeliveryError("指定提交中的 WindHub 文件不是有效的 Git LFS 指针")
    expected_sha256 = lines[1].removeprefix("oid sha256:")
    expected_size = int(lines[2].removeprefix("size "))
    materialized_path = repository_root / Path(*REPOSITORY_INPUT_PATH.parts)
    if not materialized_path.is_file():
        raise PortableDeliveryError(
            "WindHub Git LFS 实体不存在；请先执行 "
            'git lfs pull --include="examples/3d-WindTurbineHub.inp"'
        )
    actual_size = materialized_path.stat().st_size
    actual_sha256 = _sha256_file(materialized_path)
    if actual_size != expected_size or actual_sha256 != expected_sha256:
        raise PortableDeliveryError("WindHub 实体与指定提交的 Git LFS 指针不一致")
    return (
        {
            "path": PACKAGE_INPUT_PATH.as_posix(),
            "size_bytes": actual_size,
            "sha256": actual_sha256,
            "source_repository_path": REPOSITORY_INPUT_PATH.as_posix(),
            "materialized": True,
        },
        materialized_path.read_bytes(),
    )


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (0o644 & 0xFFFF) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _write_zip(path: Path, members: Mapping[str, bytes]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(
        temporary,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        allowZip64=True,
    ) as archive:
        for relative, data in sorted(members.items()):
            archive.writestr(_zip_info(f"{PACKAGE_ROOT_NAME}/{relative}"), data)
    os.replace(temporary, path)


def create_portable_package(
    repository_root: Path,
    output_dir: Path,
    requested_commit: str = "HEAD",
) -> Path:
    repository_root = repository_root.resolve()
    output_dir = output_dir.resolve()
    commit_sha = _resolve_commit(repository_root, requested_commit)
    members = _committed_source_members(repository_root, commit_sha)
    input_facts, input_bytes = _lfs_input_facts(repository_root, commit_sha)
    members[PACKAGE_INPUT_PATH.as_posix()] = input_bytes
    file_records = [
        {
            "path": name,
            "size_bytes": len(data),
            "sha256": _sha256_bytes(data),
        }
        for name, data in sorted(members.items())
    ]
    manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_root": PACKAGE_ROOT_NAME,
        "source": {
            "commit_sha": commit_sha,
            "repository_subdirectory": DEMO_REPOSITORY_PATH.as_posix(),
            "provenance": "committed Git tree copied into a standalone package",
        },
        "input": input_facts,
        "integrity": {
            "algorithm": "SHA-256",
            "validated_file_count": len(file_records),
            "files": file_records,
        },
        "runtime": {
            "supported_operating_systems": ["Windows x64"],
            "minimum_cmake_version": "3.21",
            "minimum_python_version": "3.10",
            "cpp_standard": "C++17",
            "openmp_required": True,
            "git_required_after_extraction": False,
            "git_lfs_required_after_extraction": False,
        },
        "distribution_notice": "仅供研究院内部技术评估，未经项目负责人许可不得对外发布。",
    }
    members[PACKAGE_MANIFEST_NAME] = _canonical_json(manifest)

    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / f"csc3-windhub-demo-{commit_sha[:12]}.zip"
    if package_path.exists():
        raise PortableDeliveryError(f"输出包已经存在，拒绝覆盖：{package_path}")
    _write_zip(package_path, members)
    verify_portable_archive(package_path)
    return package_path


def _manifest_file_records(
    manifest: Mapping[str, object],
) -> dict[str, tuple[int, str]]:
    integrity = manifest.get("integrity")
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "SHA-256":
        raise PortableDeliveryError("交付包 manifest 缺少 SHA-256 校验定义")
    raw_files = integrity.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise PortableDeliveryError("交付包 manifest 缺少逐文件校验记录")
    records: dict[str, tuple[int, str]] = {}
    for item in raw_files:
        if not isinstance(item, dict):
            raise PortableDeliveryError("交付包逐文件校验记录格式错误")
        name = _safe_relative_path(str(item.get("path", ""))).as_posix()
        size = item.get("size_bytes")
        digest = str(item.get("sha256", ""))
        if (
            name == PACKAGE_MANIFEST_NAME
            or name in records
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise PortableDeliveryError(f"交付包逐文件校验记录无效：{name}")
        records[name] = (size, digest)
    if integrity.get("validated_file_count") != len(records):
        raise PortableDeliveryError("交付包 manifest 的文件计数不正确")
    return records


def _validate_manifest(
    manifest: object,
    member_reader,
    archive_members: set[str] | None = None,
) -> dict[str, object]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        raise PortableDeliveryError("不支持的交付包 manifest schema")
    source = manifest.get("source")
    input_facts = manifest.get("input")
    runtime = manifest.get("runtime")
    if not isinstance(source, dict) or re.fullmatch(
        r"[0-9a-f]{40}", str(source.get("commit_sha", ""))
    ) is None:
        raise PortableDeliveryError("交付包 manifest 缺少完整源码 commit SHA")
    if not isinstance(input_facts, dict):
        raise PortableDeliveryError("交付包 manifest 缺少 WindHub 输入信息")
    if not isinstance(runtime, dict) or runtime.get("supported_operating_systems") != [
        "Windows x64"
    ]:
        raise PortableDeliveryError("交付包不是 Windows x64 自包含包")

    records = _manifest_file_records(manifest)
    if archive_members is not None and archive_members != {
        PACKAGE_MANIFEST_NAME,
        *records.keys(),
    }:
        raise PortableDeliveryError("交付包成员集合与 JSON manifest 不一致")

    for name, (expected_size, expected_hash) in records.items():
        data = member_reader(name)
        if len(data) != expected_size or _sha256_bytes(data) != expected_hash:
            raise PortableDeliveryError(f"交付包文件 SHA-256 不匹配：{name}")

    input_name = _safe_relative_path(str(input_facts.get("path", ""))).as_posix()
    if input_name != PACKAGE_INPUT_PATH.as_posix() or input_name not in records:
        raise PortableDeliveryError("交付包 manifest 中的 WindHub 路径不正确")
    input_bytes = member_reader(input_name)
    if (
        input_facts.get("materialized") is not True
        or input_facts.get("size_bytes") != len(input_bytes)
        or input_facts.get("sha256") != _sha256_bytes(input_bytes)
    ):
        raise PortableDeliveryError("交付包中的 WindHub 输入与 manifest 不一致")
    return manifest


def verify_extracted_package(package_root: Path) -> dict[str, object]:
    """验证已解压包的 JSON manifest；允许之后生成的 build 目录存在。"""

    package_root = package_root.resolve()
    manifest_path = package_root / PACKAGE_MANIFEST_NAME
    if not manifest_path.is_file():
        raise PortableDeliveryError("目录不是完整的 CSC3 WindHub Windows 自包含包")

    def read_member(relative: str) -> bytes:
        candidate = (package_root / Path(*PurePosixPath(relative).parts)).resolve()
        try:
            candidate.relative_to(package_root)
        except ValueError as error:
            raise PortableDeliveryError(f"校验路径越出交付包：{relative}") from error
        if not candidate.is_file():
            raise PortableDeliveryError(f"交付包缺少文件：{relative}")
        return candidate.read_bytes()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return _validate_manifest(manifest, read_member)


def verify_portable_archive(package_path: Path) -> dict[str, object]:
    package_path = package_path.resolve()
    if not package_path.is_file():
        raise PortableDeliveryError(f"交付包不存在：{package_path}")
    with zipfile.ZipFile(package_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise PortableDeliveryError("交付包含有重复成员")
        prefix = f"{PACKAGE_ROOT_NAME}/"
        relative_names: list[str] = []
        for name in names:
            if not name.startswith(prefix) or name.endswith("/"):
                raise PortableDeliveryError(f"交付包成员不在固定根目录内：{name}")
            relative_names.append(_safe_relative_path(name[len(prefix) :]).as_posix())
        data_by_name = {
            relative: archive.read(f"{prefix}{relative}") for relative in relative_names
        }
    if PACKAGE_MANIFEST_NAME not in data_by_name:
        raise PortableDeliveryError("交付包缺少 PACKAGE_MANIFEST.json")
    manifest = json.loads(data_by_name[PACKAGE_MANIFEST_NAME].decode("utf-8"))
    return _validate_manifest(
        manifest,
        data_by_name.__getitem__,
        set(data_by_name),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="从指定 Git commit 创建自包含 ZIP")
    create.add_argument("--repository-root", type=Path, required=True)
    create.add_argument("--output-dir", type=Path, required=True)
    create.add_argument("--commit", default="HEAD")
    verify = subparsers.add_parser("verify", help="独立验证已有自包含 ZIP")
    verify.add_argument("--package", type=Path, required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    options = build_argument_parser().parse_args(arguments)
    try:
        if options.command == "create":
            package = create_portable_package(
                options.repository_root,
                options.output_dir,
                options.commit,
            )
            result = {
                "status": "PASS",
                "package": str(package),
                "sha256": _sha256_file(package),
            }
        else:
            manifest = verify_portable_archive(options.package)
            result = {
                "status": "PASS",
                "package": str(options.package.resolve()),
                "source_commit": manifest["source"]["commit_sha"],
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, PortableDeliveryError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
