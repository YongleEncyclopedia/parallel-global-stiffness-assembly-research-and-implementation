#!/usr/bin/env python3
"""CPU 工作流脚本共享的命令、构建与输入检查辅助函数。"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence, Union


Command = Sequence[Union[str, Path]]


class WorkflowCommandError(RuntimeError):
    """保留失败命令上下文的工作流异常。"""

    def __init__(self, command: Command, cwd: Path, returncode: int) -> None:
        self.command = tuple(str(part) for part in command)
        self.cwd = cwd.resolve()
        self.returncode = returncode
        super().__init__(
            f"command failed with exit code {returncode} in {self.cwd}: "
            f"{shlex.join(self.command)}"
        )


def run_checked(command: Command, cwd: Path) -> subprocess.CompletedProcess[str]:
    """运行命令；失败时保留命令、工作目录和退出码。"""

    argv = [str(part) for part in command]
    resolved_cwd = cwd.resolve()
    print("+", shlex.join(argv), f"(cwd={resolved_cwd})", flush=True)
    result = subprocess.run(argv, cwd=resolved_cwd, check=False, text=True)
    if result.returncode != 0:
        raise WorkflowCommandError(argv, resolved_cwd, result.returncode)
    return result


def resolve_executable(build_dir: Path, name: str) -> Path:
    """解析单配置及 Windows 多配置生成器中的可执行文件。"""

    root = build_dir.expanduser().resolve()
    candidates = (
        root / "bin" / name,
        root / "bin" / f"{name}.exe",
        root / "bin" / "Release" / f"{name}.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    checked = "\n  - ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"executable {name!r} not found; checked:\n  - {checked}")


def cmake_configuration_for_preset(preset: str) -> str:
    """将仓库 preset 名称映射为 multi-config 生成器的显式配置。"""

    lowered = preset.lower()
    if "relwithdebinfo" in lowered:
        return "RelWithDebInfo"
    if "minsizerel" in lowered:
        return "MinSizeRel"
    if "debug" in lowered:
        return "Debug"
    return "Release"


def configure_and_build(source_dir: Path, preset: str) -> Path:
    """使用同一个 CMake preset 完成配置和构建。"""

    source = source_dir.expanduser().resolve()
    run_checked(["cmake", "--preset", preset], source)
    run_checked(
        [
            "cmake",
            "--build",
            "--preset",
            preset,
            "--config",
            cmake_configuration_for_preset(preset),
        ],
        source,
    )
    return source / "build" / preset


def assert_lfs_materialized(path: Path) -> Path:
    """确认输入存在且不是尚未 materialize 的 Git LFS pointer。"""

    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"required input does not exist: {resolved}")
    with resolved.open("rb") as handle:
        prefix = handle.read(512).decode("utf-8", errors="replace")
    lines = prefix.splitlines()
    if (
        len(lines) >= 2
        and lines[0].startswith("version https://git-lfs.github.com/spec/v1")
        and lines[1].startswith("oid sha256:")
    ):
        raise RuntimeError(
            f"input is still a Git LFS pointer: {resolved}; run `git lfs pull` first"
        )
    return resolved


def prepare_output_root(
    path: Path,
    overwrite: bool,
    source_root: Path,
    owned_entries: Sequence[str],
) -> Path:
    """准备输出根目录；覆盖时只清理当前工作流拥有的条目。"""

    root = path.expanduser().resolve()
    protected: set[Path] = set()
    for base in (
        source_root.expanduser().resolve(),
        Path.cwd().resolve(),
        Path.home().resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ):
        protected.add(base)
        protected.update(base.parents)
    if root.anchor:
        protected.add(Path(root.anchor).resolve())
    if root in protected:
        raise ValueError(f"refusing to use protected directory as output root: {root}")

    if root.exists():
        if not root.is_dir():
            raise ValueError(f"output root exists but is not a directory: {root}")
        if not overwrite:
            raise FileExistsError(
                f"output directory already exists: {root}; pass --overwrite to replace workflow outputs"
            )
        for entry in owned_entries:
            relative = Path(entry)
            if relative.is_absolute() or not relative.parts or ".." in relative.parts:
                raise ValueError(f"invalid workflow-owned output entry: {entry!r}")
            target = root / relative
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
    else:
        root.mkdir(parents=True)
    return root
