#!/usr/bin/env python3
"""构建 Release benchmark，并运行 WindHub 单次演示或完整线程扫描。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Mapping, Sequence


FAILURE_SCHEMA_VERSION = "csc3-windhub-example-failure-v1"
DEMO_SCHEMA_VERSION = "csc3-windhub-demo-v1"
ISSUE_NUMBER = 72
FULL_MODE = "full"
DEMO_MODE = "demo"
SUPPORTED_MODES = (FULL_MODE, DEMO_MODE)
FULL_WARMUP_COUNT = 0
FULL_REPEAT_COUNT = 1


class ExampleError(RuntimeError):
    """表示一键示例尚未满足运行条件。"""


@dataclass(frozen=True)
class ExamplePaths:
    """一键入口从脚本位置推导出的源码与输入路径。"""

    demo_root: Path
    repository_root: Path
    build_root: Path
    input_path: Path
    package_manifest_path: Path | None = None


def discover_paths(script_path: Path | None = None) -> ExamplePaths:
    resolved_script = (script_path or Path(__file__)).resolve()
    demo_root = resolved_script.parents[1]
    package_manifest = demo_root / "PACKAGE_MANIFEST.json"
    if package_manifest.is_file():
        return ExamplePaths(
            demo_root=demo_root,
            repository_root=demo_root,
            build_root=demo_root / "build",
            input_path=demo_root / "examples" / "3d-WindTurbineHub.inp",
            package_manifest_path=package_manifest,
        )
    repository_root = resolved_script.parents[3]
    return ExamplePaths(
        demo_root=demo_root,
        repository_root=repository_root,
        build_root=demo_root / "build",
        input_path=repository_root / "examples" / "3d-WindTurbineHub.inp",
    )


def _load_runner(demo_root: Path) -> ModuleType:
    path = demo_root / "scripts" / "run_windows_process_benchmark.py"
    specification = importlib.util.spec_from_file_location(
        "csc3_windows_process_runner_example",
        path,
    )
    if specification is None or specification.loader is None:
        raise ExampleError(f"无法加载性能脚本：{path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _load_portable_packager(demo_root: Path) -> ModuleType:
    path = demo_root / "scripts" / "create_portable_delivery.py"
    specification = importlib.util.spec_from_file_location(
        "csc3_portable_delivery_runtime",
        path,
    )
    if specification is None or specification.loader is None:
        raise ExampleError(f"无法加载交付包校验脚本：{path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _cache_entries(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ExampleError(
            "没有找到 build/CMakeCache.txt。请先执行 README 对应平台的配置与构建命令。"
        )
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith(("#", "//")) or "=" not in line:
            continue
        key_and_type, value = line.split("=", 1)
        key = key_and_type.split(":", 1)[0]
        entries[key] = value.strip()
    return entries


def _compiler_facts(build_root: Path) -> tuple[str, str, str]:
    compiler_files = sorted(
        (build_root / "CMakeFiles").glob("*/CMakeCXXCompiler.cmake")
    )
    if not compiler_files:
        raise ExampleError("CMake 构建目录中缺少编译器记录，请重新执行 cmake ..。")
    text = compiler_files[-1].read_text(encoding="utf-8", errors="replace")
    identifier = re.search(r'set\(CMAKE_CXX_COMPILER_ID "([^"]+)"\)', text)
    version = re.search(r'set\(CMAKE_CXX_COMPILER_VERSION "([^"]+)"\)', text)
    architecture = re.search(
        r'set\(CMAKE_CXX_COMPILER_ARCHITECTURE_ID "([^"]*)"\)',
        text,
    )
    if identifier is None or version is None:
        raise ExampleError("无法从 CMake 构建目录读取编译器名称和版本。")
    architecture_text = (
        architecture.group(1).strip() if architecture is not None else ""
    ) or platform.machine()
    return identifier.group(1), version.group(1), architecture_text


def _compiler_pointer_size(build_root: Path) -> int:
    compiler_files = sorted(
        (build_root / "CMakeFiles").glob("*/CMakeCXXCompiler.cmake")
    )
    if not compiler_files:
        raise ExampleError("CMake 构建目录中缺少编译器记录，请重新执行 cmake 配置。")
    text = compiler_files[-1].read_text(encoding="utf-8", errors="replace")
    match = re.search(r'set\(CMAKE_CXX_SIZEOF_DATA_PTR "([0-9]+)"\)', text)
    if match is None:
        raise ExampleError("无法从 CMake 构建目录读取 C++ 指针宽度。")
    return int(match.group(1))


def _run_text(command: Sequence[str], cwd: Path) -> str:
    completed = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ExampleError(f"命令执行失败：{' '.join(command)}\n{detail}")
    return completed.stdout.strip()


def _git_tools(repository_root: Path) -> dict[str, str]:
    if shutil.which("git.exe") is None and shutil.which("git") is None:
        raise ExampleError(
            "没有找到 Git。请先安装 Git for Windows，并重新打开 PowerShell。"
        )
    git_version = _run_text(["git", "--version"], repository_root)
    try:
        git_lfs_version = _run_text(["git", "lfs", "version"], repository_root)
    except (ExampleError, OSError) as error:
        raise ExampleError(
            "没有找到可用的 Git LFS。请先安装 Git LFS，重新打开 PowerShell，"
            "再执行 git lfs install。"
        ) from error
    return {
        "git": git_version,
        "git_lfs": git_lfs_version,
    }


def _package_source_context(
    paths: ExamplePaths,
    runner: ModuleType,
) -> tuple[dict[str, object], dict[str, str], dict[str, object]]:
    packager = _load_portable_packager(paths.demo_root)
    try:
        package_manifest = packager.verify_extracted_package(paths.demo_root)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        raise ExampleError(f"自包含交付包校验失败：{error}") from error
    source_record = package_manifest.get("source")
    input_record = package_manifest.get("input")
    if not isinstance(source_record, Mapping) or not isinstance(input_record, Mapping):
        raise ExampleError("自包含交付包 manifest 缺少源码或输入记录。")
    commit_sha = str(source_record.get("commit_sha", ""))
    source = {
        "commit_sha": commit_sha,
        "branch": "portable-package",
        "tracked_worktree_clean_at_start": None,
        "provenance_mode": "portable-package",
        "package_schema_version": package_manifest.get("schema_version"),
    }
    source_tools = {
        "package_manifest": "PACKAGE_MANIFEST.json (SHA-256 verified)",
        "git": "not required after extraction",
        "git_lfs": "not required after extraction",
    }
    input_facts = dict(input_record)
    input_facts.update(
        {
            "repository_relative_path": str(input_record.get("path", "")),
            "git_lfs_materialized": True,
            "matches_package_manifest": True,
            "provenance_mode": "portable-package",
        }
    )
    if paths.input_path.stat().st_size != int(input_facts.get("size_bytes", 0)):
        raise ExampleError("包内 WindHub 输入大小在校验后发生变化。")
    if runner._sha256_file(paths.input_path) != input_facts.get("sha256"):
        raise ExampleError("包内 WindHub 输入 SHA-256 在校验后发生变化。")
    return source, source_tools, input_facts


def _repository_source_context(
    paths: ExamplePaths,
    runner: ModuleType,
) -> tuple[dict[str, object], dict[str, str], dict[str, object]]:
    source_tools = _git_tools(paths.repository_root)
    try:
        source = runner._source_provenance(paths.repository_root)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        if "工作树干净" in str(error):
            raise ExampleError(
                f"{error}\n请先提交或还原已跟踪文件的修改，再重新运行。"
            ) from error
        raise ExampleError(
            f"无法读取 Git 源码状态：{error}\n"
            "请使用完整 Git 仓库，或者使用 create_portable_delivery.py 创建的自包含交付包。"
        ) from error
    try:
        input_facts = runner._input_provenance(
            paths.input_path,
            paths.repository_root,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise ExampleError(
            f"{error}\n请在仓库根目录执行：\n"
            "git lfs install\n"
            'git lfs pull --include="examples/3d-WindTurbineHub.inp"'
        ) from error
    return source, source_tools, input_facts


def _source_context(
    paths: ExamplePaths,
    runner: ModuleType,
) -> tuple[dict[str, object], dict[str, str], dict[str, object]]:
    if paths.package_manifest_path is not None:
        return _package_source_context(paths, runner)
    return _repository_source_context(paths, runner)


def _build_release(build_root: Path, demo_root: Path) -> str:
    command = [
        "cmake",
        "--build",
        str(build_root),
        "--config",
        "Release",
        "--target",
        "csc3_demo_benchmark",
    ]
    completed = subprocess.run(
        command,
        cwd=demo_root,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = completed.stdout.strip()
    if completed.returncode != 0:
        detail = output[-2000:] if output else "CMake 未返回错误详情。"
        raise ExampleError(f"Release 构建失败：\n{detail}")
    return output


def _openmp_runtime_text(
    cache: Mapping[str, str],
    build_root: Path,
    benchmark_executable: Path,
) -> str:
    flags = cache.get("OpenMP_CXX_FLAGS", "").strip()
    candidates = [
        build_root / "bin" / "vcomp140.dll",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "vcomp140.dll",
    ]
    runtime = next((path for path in candidates if path.is_file()), None)
    if runtime is None:
        raise ExampleError("没有找到 MSVC OpenMP 运行时 vcomp140.dll。")
    script = (
        "$item=Get-Item -LiteralPath '"
        + str(runtime).replace("'", "''")
        + "';$item.VersionInfo.FileVersion"
    )
    version = _run_text(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        build_root,
    )
    flag_text = flags or "CMake 未记录 OpenMP 编译参数"
    return f"{runtime.name} {version}（{flag_text}）"


def _build_tool_text(
    build_output: str,
    generator: str,
    cache: Mapping[str, str],
) -> str:
    line = next(
        (item.strip() for item in build_output.splitlines() if "MSBuild" in item),
        "",
    )
    if line:
        return line
    make_program = cache.get("CMAKE_MAKE_PROGRAM", "").strip()
    return make_program or f"cmake --build（{generator}）"


def _toolchain_facts(
    cache: Mapping[str, str],
    build_root: Path,
    demo_root: Path,
    build_output: str,
    benchmark_executable: Path,
) -> dict[str, str]:
    generator = cache.get("CMAKE_GENERATOR", "").strip()
    compiler_id, compiler_version, compiler_architecture = _compiler_facts(build_root)
    cmake_banner = _run_text(["cmake", "--version"], demo_root).splitlines()[0]
    return {
        "compiler": f"{compiler_id} {compiler_version} ({compiler_architecture})",
        "cmake": cmake_banner,
        "cmake_generator": generator,
        "build_tool": _build_tool_text(build_output, generator, cache),
        "openmp_runtime": _openmp_runtime_text(
            cache,
            build_root,
            benchmark_executable,
        ),
        "benchmark_build_type": "Release",
    }


def _output_root(
    build_root: Path,
    now: datetime | None = None,
    *,
    mode: str = FULL_MODE,
) -> Path:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"不支持的 WindHub 运行模式：{mode}")
    value = now or datetime.now()
    timestamp = value.strftime("%Y%m%d-%H%M%S-%f")
    directory = "example-results" if mode == FULL_MODE else "demo-results"
    return build_root / directory / timestamp


def _failure_root(paths: ExamplePaths, proposed_output_root: Path) -> Path:
    if paths.build_root.is_dir():
        return proposed_output_root
    return (
        Path(tempfile.gettempdir())
        / "csc3-windhub-example-failures"
        / proposed_output_root.name
    )


def _write_failure_record(output_root: Path, error: BaseException) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "failure.json"
    temporary = path.with_name(path.name + ".tmp")
    record = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "status": "FAIL",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "error_type": type(error).__name__,
        "message": str(error),
    }
    temporary.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExampleError(f"汇总结果缺少数值字段：{label}")
    return float(value)


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExampleError(f"汇总结果缺少整数字段：{label}")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ExampleError(f"运行记录缺少{label}。")
    return value


def _memory_contract(
    memory_definition: Mapping[str, object],
) -> tuple[str, str, str]:
    if (
        memory_definition.get("peak_working_set")
        == "GetProcessMemoryInfo.PeakWorkingSetSize"
        and memory_definition.get("peak_working_set_is_os_measured") is True
    ):
        return "peak_working_set_bytes", "Windows", "进程峰值工作集"
    raise ExampleError("峰值内存没有使用 Windows 实测工作集口径。")


def _summary_rows(summary: Mapping[str, object]) -> list[dict[str, float | int]]:
    configuration = summary.get("configuration")
    integrity = summary.get("process_integrity")
    memory_definition = summary.get("memory_definition")
    if not isinstance(configuration, Mapping):
        raise ExampleError("汇总结果缺少实验配置。")
    if not isinstance(integrity, Mapping):
        raise ExampleError("汇总结果缺少样本完整性记录。")
    if not isinstance(memory_definition, Mapping):
        raise ExampleError("汇总结果缺少峰值内存测量说明。")

    maximum_threads = int(
        _number(configuration.get("maximum_threads"), "maximum_threads")
    )
    warmup_count = int(_number(configuration.get("warmup_count"), "warmup_count"))
    repeat_count = int(_number(configuration.get("repeat_count"), "repeat_count"))
    expected_threads = list(range(1, maximum_threads + 1))
    if maximum_threads <= 0 or configuration.get("thread_counts") != expected_threads:
        raise ExampleError("汇总结果中的线程范围不完整。")
    if configuration.get("sample_process_model") != "one_fresh_child_process_per_sample":
        raise ExampleError("汇总结果没有确认每个样本使用新进程。")
    if configuration.get("samples_are_serialized") is not True:
        raise ExampleError("汇总结果没有确认样本串行执行。")
    if configuration.get("measured_round_order") != "alternating_ascending_descending":
        raise ExampleError("汇总结果中的正式轮次顺序不符合协议。")

    expected_sample_count = maximum_threads * (warmup_count + repeat_count)
    if (
        int(_number(integrity.get("expected_sample_count"), "expected_sample_count"))
        != expected_sample_count
        or int(_number(integrity.get("observed_sample_count"), "observed_sample_count"))
        != expected_sample_count
        or int(
            _number(
                integrity.get("measured_sample_count_per_thread"),
                "measured_sample_count_per_thread",
            )
        )
        != repeat_count
        or integrity.get("unique_sample_ids") is not True
        or integrity.get("samples_overlap") is not False
        or integrity.get("all_exit_codes_zero") is not True
        or integrity.get("all_observed_team_sizes_match") is not True
    ):
        raise ExampleError("汇总结果中的样本数量、顺序或实际线程数不符合协议。")
    memory_key, _, _ = _memory_contract(memory_definition)

    raw_rows = summary.get("per_thread")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ExampleError("汇总结果中没有线程数据。")
    rows: list[dict[str, float | int]] = []
    for item in raw_rows:
        if not isinstance(item, Mapping):
            raise ExampleError("汇总结果中的线程数据格式不正确。")
        total = item.get("parallel_total_ms")
        peak = item.get(memory_key)
        if not isinstance(total, Mapping) or not isinstance(peak, Mapping):
            raise ExampleError("汇总结果缺少时间或峰值内存统计。")
        rows.append(
            {
                "thread_count": int(_number(item.get("thread_count"), "thread_count")),
                "symbolic_ms": _number(
                    (item.get("parallel_symbolic_ms") or {}).get("median")
                    if isinstance(item.get("parallel_symbolic_ms"), Mapping)
                    else None,
                    "parallel_symbolic_ms.median",
                ),
                "numeric_ms": _number(
                    (item.get("parallel_numeric_ms") or {}).get("median")
                    if isinstance(item.get("parallel_numeric_ms"), Mapping)
                    else None,
                    "parallel_numeric_ms.median",
                ),
                "total_ms": _number(total.get("median"), "parallel_total_ms.median"),
                "total_cv": _number(
                    total.get("coefficient_of_variation"),
                    "parallel_total_ms.coefficient_of_variation",
                ),
                "speedup": _number(item.get("overall_speedup"), "overall_speedup"),
                "peak_gib": _number(
                    peak.get("median"),
                    f"{memory_key}.median",
                )
                / (1024.0**3),
            }
        )
    if [int(row["thread_count"]) for row in rows] != expected_threads:
        raise ExampleError("汇总结果中的线程表不完整。")
    return rows


def render_summary_markdown(
    summary: Mapping[str, object],
    manifest: Mapping[str, object],
) -> str:
    case = _mapping(summary.get("case_sizes"), "算例规模")
    correctness = _mapping(summary.get("correctness"), "正确性")
    configuration = _mapping(summary.get("configuration"), "测试配置")
    if summary.get("status") != "PASS" or manifest.get("status") != "PASS":
        raise ExampleError("运行记录尚未通过，不能生成结果报告。")

    rows = _summary_rows(summary)
    maximum_threads = _integer(
        configuration.get("maximum_threads"),
        "maximum_threads",
    )
    maximum_relative_error = _number(
        correctness.get("relative_frobenius_error_maximum"),
        "relative_frobenius_error_maximum",
    )
    lines = [
        "# WindHub 全线程单轮测试结果",
        "",
        (
            f"节点 {case.get('node_count')} | 单元 {case.get('element_count')} | "
            f"自由度 {case.get('dof_count')}"
        ),
        "",
        (
            f"测试范围：$p=1,\\ldots,{maximum_threads}$，每个线程数测量 1 次，"
            "各样本串行执行。"
        ),
        (
            f"正确性：{correctness.get('status')}；最大相对 Frobenius 误差 "
            f"{maximum_relative_error:.6e}。"
        ),
        "",
        "| 线程 | 符号（ms） | 数值（ms） | 总时间（ms） | 加速比 | 峰值内存（GiB） |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['thread_count']} | {row['symbolic_ms']:.3f} | "
            f"{row['numeric_ms']:.3f} | {row['total_ms']:.3f} | "
            f"{row['speedup']:.3f}× | {row['peak_gib']:.3f} |"
        )
    lines.extend(
        [
            "",
            "加速比以 $p=1$ 样本中的直接串行组装时间为基准。",
            "",
        ]
    )
    return "\n".join(lines)


def print_console_summary(
    summary: Mapping[str, object],
    output_root: Path,
    demo_root: Path,
) -> None:
    case = _mapping(summary.get("case_sizes"), "算例规模")
    correctness = _mapping(summary.get("correctness"), "正确性")
    try:
        result_path = output_root.resolve().relative_to(demo_root.resolve()).as_posix()
    except ValueError as error:
        raise ExampleError("全线程结果目录不在 Demo 构建目录内。") from error

    print("\nWindHub 全线程测试完成")
    print(
        f"节点 {case.get('node_count')} | 单元 {case.get('element_count')} | "
        f"自由度 {case.get('dof_count')}"
    )
    print()
    print("线程  符号(ms)  数值(ms)  总时间(ms)  加速比  峰值内存(GiB)")
    for row in _summary_rows(summary):
        print(
            f"{int(row['thread_count']):>4}  {row['symbolic_ms']:>8.3f}  "
            f"{row['numeric_ms']:>8.3f}  {row['total_ms']:>10.3f}  "
            f"{row['speedup']:>6.3f}×  {row['peak_gib']:>13.3f}"
        )
    print()
    print(f"正确性 {correctness.get('status')}")
    print(f"结果：{result_path}")


def _demo_metrics(
    manifest: Mapping[str, object],
) -> dict[str, object]:
    if manifest.get("schema_version") != DEMO_SCHEMA_VERSION:
        raise ExampleError("演示 manifest schema 不受支持。")
    if manifest.get("status") != "PASS":
        raise ExampleError("演示尚未通过，不能生成结果报告。")
    if manifest.get("mode") != DEMO_MODE:
        raise ExampleError("演示 manifest 的运行模式不正确。")
    if manifest.get("formal_evidence") is not False:
        raise ExampleError("单次演示不能标记为正式性能证据。")

    configuration = _mapping(manifest.get("configuration"), "演示配置")
    case = _mapping(manifest.get("case_sizes"), "算例规模")
    correctness = _mapping(manifest.get("correctness"), "正确性")
    sample = _mapping(manifest.get("sample"), "单进程样本")
    source = _mapping(manifest.get("source"), "源码信息")
    input_facts = _mapping(manifest.get("input"), "输入信息")
    environment = _mapping(manifest.get("environment"), "运行环境")
    toolchain = _mapping(manifest.get("toolchain"), "工具链")
    memory_definition = _mapping(manifest.get("memory_definition"), "内存口径")

    thread_count = _integer(configuration.get("thread_count"), "thread_count")
    if thread_count <= 0:
        raise ExampleError("演示线程数必须为正整数。")
    physical_core_count = _integer(
        environment.get("physical_core_count"), "physical_core_count"
    )
    logical_processor_count = _integer(
        environment.get("logical_processor_count"), "logical_processor_count"
    )
    if (
        physical_core_count <= 0
        or logical_processor_count < physical_core_count
        or logical_processor_count != thread_count
    ):
        raise ExampleError("演示必须请求本机全部逻辑处理器。")
    for key in ("node_count", "element_count", "dof_count", "nnz"):
        if _integer(case.get(key), f"case_sizes.{key}") <= 0:
            raise ExampleError(f"演示算例规模必须为正整数：{key}。")
    expected_configuration = {
        "thread_count": thread_count,
        "warmup_count": 0,
        "repeat_count": 1,
        "amortization_count": 1,
        "performance_evidence_level": "local-smoke",
        "sample_process_model": "one_fresh_child_process",
        "benchmark_process_count": 1,
        "benchmark_processes_are_concurrent": False,
        "time_definition": {
            "serial_total_ms": "serial_direct_ms",
            "serial_direct_ms": (
                "direct contribution generation, sort, and reduction without a "
                "prebuilt CSC3 structure or scatter"
            ),
            "serial_symbolic_ms": "two-stage phase diagnostic only",
            "serial_numeric_ms": "two-stage phase diagnostic only",
            "parallel_total_ms": "parallel_symbolic_ms + parallel_numeric_ms",
        },
    }
    if dict(configuration) != expected_configuration:
        raise ExampleError("演示配置必须是单个满线程、新进程、无预热样本。")
    if (
        sample.get("sample_kind") != "measured"
        or _integer(sample.get("round"), "sample.round") != 1
        or _integer(sample.get("order_position"), "sample.order_position") != 1
        or _integer(sample.get("thread_count"), "sample.thread_count")
        != thread_count
        or _integer(sample.get("exit_code"), "sample.exit_code") != 0
    ):
        raise ExampleError("演示必须且只能包含一个满线程正式样本。")

    symbolic_team = _integer(
        sample.get("symbolic_team_size_observed"),
        "symbolic_team_size_observed",
    )
    numeric_team = _integer(
        sample.get("numeric_team_size_observed"),
        "numeric_team_size_observed",
    )
    if symbolic_team != thread_count or numeric_team != thread_count:
        raise ExampleError(
            "演示实际 OpenMP 线程组与请求不符："
            f"请求 {thread_count}，符号 {symbolic_team}，数值 {numeric_team}。"
        )

    threshold = _number(
        correctness.get("relative_frobenius_error_threshold"),
        "relative_frobenius_error_threshold",
    )
    relative_error = _number(
        correctness.get("relative_frobenius_error"),
        "relative_frobenius_error",
    )
    max_absolute_error = _number(
        correctness.get("max_absolute_error"),
        "max_absolute_error",
    )
    if (
        correctness.get("status") != "PASS"
        or correctness.get("structure_matches") is not True
        or correctness.get("scatter_status") != "PASS"
        or correctness.get("symbolic_plan_matches_serial") is not True
        or correctness.get("numeric_setup_plan_matches_serial") is not True
        or threshold < 0.0
        or relative_error < 0.0
        or relative_error > threshold
        or max_absolute_error < 0.0
    ):
        raise ExampleError("演示的矩阵、scatter 或直接串行参考检查未通过。")

    serial_direct_ms = _number(
        sample.get("serial_direct_ms"), "serial_direct_ms"
    )
    serial_symbolic_ms = _number(
        sample.get("serial_symbolic_ms"), "serial_symbolic_ms"
    )
    serial_numeric_ms = _number(
        sample.get("serial_numeric_ms"), "serial_numeric_ms"
    )
    serial_total_ms = _number(sample.get("serial_total_ms"), "serial_total_ms")
    parallel_symbolic_ms = _number(
        sample.get("parallel_symbolic_ms"), "parallel_symbolic_ms"
    )
    parallel_numeric_ms = _number(
        sample.get("parallel_numeric_ms"), "parallel_numeric_ms"
    )
    parallel_total_ms = _number(
        sample.get("parallel_total_ms"), "parallel_total_ms"
    )
    input_prepare_ms = _number(sample.get("input_prepare_ms"), "input_prepare_ms")
    wall_time_seconds = _number(
        sample.get("wall_time_seconds"), "wall_time_seconds"
    )
    for value, label in (
        (serial_direct_ms, "serial_direct_ms"),
        (serial_symbolic_ms, "serial_symbolic_ms"),
        (serial_numeric_ms, "serial_numeric_ms"),
        (serial_total_ms, "serial_total_ms"),
        (parallel_symbolic_ms, "parallel_symbolic_ms"),
        (parallel_numeric_ms, "parallel_numeric_ms"),
        (parallel_total_ms, "parallel_total_ms"),
    ):
        if value < 0.0:
            raise ExampleError(f"演示时间必须非负：{label}。")
    if input_prepare_ms < 0.0 or wall_time_seconds <= 0.0:
        raise ExampleError("演示的输入准备时间必须非负，子进程墙钟时间必须为正。")
    if serial_total_ms <= 0.0 or parallel_total_ms <= 0.0:
        raise ExampleError("演示的串行参考和并行组装总时间必须为正。")
    serial_tolerance = 1.0e-9 * max(1.0, serial_total_ms)
    parallel_tolerance = 1.0e-9 * max(1.0, parallel_total_ms)
    if abs(serial_total_ms - serial_direct_ms) > serial_tolerance:
        raise ExampleError("演示串行总时间不等于直接串行组装时间。")
    if (
        abs(parallel_total_ms - parallel_symbolic_ms - parallel_numeric_ms)
        > parallel_tolerance
    ):
        raise ExampleError("演示并行总时间与符号、数值阶段之和不一致。")

    peak_memory_bytes = _integer(
        sample.get("peak_working_set_bytes"), "peak_working_set_bytes"
    )
    peak_memory_source = sample.get("peak_working_set_source")
    expected_source = "GetProcessMemoryInfo.PeakWorkingSetSize"
    definition_source = memory_definition.get("peak_working_set")
    definition_measured = memory_definition.get("peak_working_set_is_os_measured")
    estimated_persistent_bytes = _integer(
        sample.get("estimated_persistent_bytes"), "estimated_persistent_bytes"
    )
    if peak_memory_bytes <= 0:
        raise ExampleError("演示缺少 Windows 实测进程峰值工作集。")
    if estimated_persistent_bytes <= 0:
        raise ExampleError("演示缺少算法持久向量容量估计。")
    if (
        peak_memory_source != expected_source
        or definition_source != expected_source
        or definition_measured is not True
        or memory_definition.get("estimated_persistent_bytes")
        != "owned vector payload capacity estimate; not RSS or peak memory"
    ):
        raise ExampleError("演示内存数字没有使用约定口径。")

    overall_speedup = serial_total_ms / parallel_total_ms
    recorded_speedup = _number(
        manifest.get("overall_speedup"), "overall_speedup"
    )
    if abs(recorded_speedup - overall_speedup) > 1.0e-12 * max(
        1.0, overall_speedup
    ):
        raise ExampleError("演示的整体加速比计算不一致。")

    return {
        "configuration": configuration,
        "case": case,
        "correctness": correctness,
        "sample": sample,
        "source": source,
        "input": input_facts,
        "environment": environment,
        "toolchain": toolchain,
        "thread_count": thread_count,
        "physical_core_count": physical_core_count,
        "logical_processor_count": logical_processor_count,
        "symbolic_team": symbolic_team,
        "numeric_team": numeric_team,
        "serial_direct_ms": serial_direct_ms,
        "serial_symbolic_ms": serial_symbolic_ms,
        "serial_numeric_ms": serial_numeric_ms,
        "serial_total_ms": serial_total_ms,
        "parallel_symbolic_ms": parallel_symbolic_ms,
        "parallel_numeric_ms": parallel_numeric_ms,
        "parallel_total_ms": parallel_total_ms,
        "overall_speedup": overall_speedup,
        "peak_memory_bytes": peak_memory_bytes,
        "peak_memory_source": peak_memory_source,
        "estimated_persistent_bytes": estimated_persistent_bytes,
        "relative_error": relative_error,
        "max_absolute_error": max_absolute_error,
        "input_prepare_ms": input_prepare_ms,
        "wall_time_seconds": wall_time_seconds,
    }


def render_demo_markdown(manifest: Mapping[str, object]) -> str:
    metrics = _demo_metrics(manifest)
    case = metrics["case"]
    assert isinstance(case, Mapping)
    peak_gib = float(metrics["peak_memory_bytes"]) / (1024.0**3)
    lines = [
        "# WindHub 单次满线程组装结果",
        "",
        (
            f"节点 {case.get('node_count')} | 单元 {case.get('element_count')} | "
            f"自由度 {case.get('dof_count')}"
        ),
        "",
        "| 路径 | 线程 | 符号（ms） | 数值（ms） | 总时间（ms） |",
        "|---|---:|---:|---:|---:|",
        (
            f"| 直接串行 | 1 | — | — | "
            f"{float(metrics['serial_total_ms']):.3f} |"
        ),
        (
            f"| CSC3 并行 | {metrics['thread_count']} | "
            f"{float(metrics['parallel_symbolic_ms']):.3f} | "
            f"{float(metrics['parallel_numeric_ms']):.3f} | "
            f"{float(metrics['parallel_total_ms']):.3f} |"
        ),
        "",
        (
            f"加速比 {float(metrics['overall_speedup']):.2f}× | "
            f"正确性 PASS | 峰值内存 {peak_gib:.3f} GiB"
        ),
        "",
    ]
    return "\n".join(lines)


def print_demo_summary(
    manifest: Mapping[str, object],
    output_root: Path,
    demo_root: Path,
) -> None:
    metrics = _demo_metrics(manifest)
    case = metrics["case"]
    assert isinstance(case, Mapping)
    try:
        result_path = output_root.resolve().relative_to(demo_root.resolve()).as_posix()
    except ValueError as error:
        raise ExampleError("演示结果目录不在 Demo 构建目录内。") from error

    print("\nWindHub 组装完成")
    print(
        f"节点 {case.get('node_count')} | 单元 {case.get('element_count')} | "
        f"自由度 {case.get('dof_count')}"
    )
    print()
    print("路径          线程  符号(ms)  数值(ms)  总时间(ms)")
    print(
        f"直接串行         1          —          —    "
        f"{float(metrics['serial_total_ms']):.3f}"
    )
    print(
        f"CSC3 并行       {int(metrics['thread_count']):>2}   "
        f"{float(metrics['parallel_symbolic_ms']):>8.3f}   "
        f"{float(metrics['parallel_numeric_ms']):>8.3f}    "
        f"{float(metrics['parallel_total_ms']):.3f}"
    )
    print()
    print(
        f"加速比 {float(metrics['overall_speedup']):.2f}× | 正确性 PASS | "
        f"峰值内存 {float(metrics['peak_memory_bytes']) / (1024.0**3):.3f} GiB"
    )
    print(f"结果：{result_path}")


def _run_demo(
    *,
    runner: ModuleType,
    demo_root: Path,
    benchmark_executable: Path,
    input_path: Path,
    result_root: Path,
    maximum_threads: int,
    source: Mapping[str, object],
    source_tools: Mapping[str, str],
    input_facts: Mapping[str, object],
    environment: Mapping[str, object],
    toolchain: Mapping[str, str],
) -> int:
    if result_root.exists():
        raise ExampleError(f"演示输出目录已经存在：{result_root}")
    result_root.mkdir(parents=True)
    recorded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    memory_definition = {
        "peak_working_set": "GetProcessMemoryInfo.PeakWorkingSetSize",
        "peak_working_set_is_os_measured": True,
        "estimated_persistent_bytes": (
            "owned vector payload capacity estimate; not RSS or peak memory"
        ),
    }
    manifest: dict[str, object] = {
        "schema_version": DEMO_SCHEMA_VERSION,
        "status": "RUNNING",
        "mode": DEMO_MODE,
        "formal_evidence": False,
        "evidence_level": "local-smoke",
        "issue": ISSUE_NUMBER,
        "started_at_utc": recorded_at,
        "ended_at_utc": None,
        "source": dict(source),
        "source_tools": dict(source_tools),
        "input": dict(input_facts),
        "environment": dict(environment),
        "toolchain": dict(toolchain),
        "benchmark_executable": str(benchmark_executable.resolve()),
        "configuration": {
            "thread_count": maximum_threads,
            "warmup_count": 0,
            "repeat_count": 1,
            "amortization_count": 1,
            "performance_evidence_level": "local-smoke",
            "sample_process_model": "one_fresh_child_process",
            "benchmark_process_count": 1,
            "benchmark_processes_are_concurrent": False,
            "time_definition": {
                "serial_total_ms": "serial_direct_ms",
                "serial_direct_ms": (
                    "direct contribution generation, sort, and reduction without a "
                    "prebuilt CSC3 structure or scatter"
                ),
                "serial_symbolic_ms": "two-stage phase diagnostic only",
                "serial_numeric_ms": "two-stage phase diagnostic only",
                "parallel_total_ms": (
                    "parallel_symbolic_ms + parallel_numeric_ms"
                ),
            },
        },
        "case_sizes": None,
        "correctness": None,
        "sample": None,
        "overall_speedup": None,
        "memory_definition": memory_definition,
        "artifacts": [],
        "failure": None,
    }
    manifest_path = result_root / "run_manifest.json"
    runner._atomic_write_text(manifest_path, runner._canonical_json(manifest))
    specification = {
        "sample_kind": "measured",
        "round": 1,
        "order_position": 1,
        "thread_count": maximum_threads,
    }
    try:
        sample = runner._run_one_sample(
            benchmark_executable,
            input_path,
            result_root,
            specification,
        )
        raw_json_path = result_root / str(sample["raw_json_path"])
        child_summary = json.loads(raw_json_path.read_text(encoding="utf-8"))
        case_sizes = child_summary.get("case_sizes")
        if not isinstance(case_sizes, Mapping):
            raise ExampleError("演示子进程结果缺少算例规模。")
        serial_total_ms = _number(sample.get("serial_total_ms"), "serial_total_ms")
        parallel_total_ms = _number(
            sample.get("parallel_total_ms"), "parallel_total_ms"
        )
        if serial_total_ms <= 0.0 or parallel_total_ms <= 0.0:
            raise ExampleError("演示无法从非正时间计算加速比。")
        manifest.update(
            {
                "status": "PASS",
                "ended_at_utc": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "case_sizes": dict(case_sizes),
                "correctness": {
                    "status": sample.get("matrix_correctness_status"),
                    "structure_matches": sample.get("structure_matches"),
                    "scatter_status": sample.get("scatter_correctness_status"),
                    "symbolic_plan_matches_serial": sample.get(
                        "symbolic_plan_matches_serial"
                    ),
                    "numeric_setup_plan_matches_serial": sample.get(
                        "numeric_setup_plan_matches_serial"
                    ),
                    "relative_frobenius_error": sample.get(
                        "relative_frobenius_error"
                    ),
                    "relative_frobenius_error_threshold": (
                        runner.RELATIVE_FROBENIUS_TOLERANCE
                    ),
                    "max_absolute_error": sample.get("max_absolute_error"),
                },
                "sample": sample,
                "overall_speedup": serial_total_ms / parallel_total_ms,
            }
        )
        markdown = render_demo_markdown(manifest)
        runner._atomic_write_text(result_root / "summary.md", markdown)
        manifest["artifacts"] = runner._artifact_records(result_root)
        runner._atomic_write_text(manifest_path, runner._canonical_json(manifest))
        print_demo_summary(manifest, result_root, demo_root)
    except (Exception, KeyboardInterrupt) as error:
        manifest["status"] = "FAIL"
        manifest["ended_at_utc"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        manifest["failure"] = f"{type(error).__name__}: {error}"
        manifest["artifacts"] = runner._artifact_records(result_root)
        runner._atomic_write_text(manifest_path, runner._canonical_json(manifest))
        raise
    return 0


def run_example(
    paths: ExamplePaths | None = None,
    output_root: Path | None = None,
    *,
    mode: str = FULL_MODE,
) -> int:
    if mode not in SUPPORTED_MODES:
        raise ExampleError(f"不支持的 WindHub 运行模式：{mode}")
    if os.name != "nt":
        raise ExampleError("WindHub 一键入口只支持 Windows x64。")
    if sys.version_info < (3, 10):
        raise ExampleError("需要 Python 3.10 或更高版本。")
    if struct.calcsize("P") != 8:
        raise ExampleError(
            "峰值内存采集需要 64 位 Python，请安装 64 位 Python 3.10 以上版本。"
        )

    resolved_paths = paths or discover_paths()
    demo_root = resolved_paths.demo_root
    repository_root = resolved_paths.repository_root
    build_root = resolved_paths.build_root
    input_path = resolved_paths.input_path
    result_root = output_root or _output_root(build_root, mode=mode)

    print("[1/3] 校验环境与输入", flush=True)
    cache = _cache_entries(build_root / "CMakeCache.txt")
    generator = cache.get("CMAKE_GENERATOR", "")
    compiler_id, _, compiler_architecture = _compiler_facts(build_root)
    if _compiler_pointer_size(build_root) != 8:
        raise ExampleError("WindHub 演示要求 64 位 C++ 构建。")
    if generator != "Visual Studio 17 2022":
        raise ExampleError(
            "build 不是 Visual Studio 2022 构建目录；请按 README 在空 build 中重新配置。"
        )
    if compiler_id != "MSVC" or compiler_architecture.lower() != "x64":
        raise ExampleError("当前 build 不是 MSVC x64；请按 README 重新配置。")

    runner = _load_runner(demo_root)
    source, source_tools, input_facts = _source_context(resolved_paths, runner)
    environment = runner._host_environment()
    maximum_threads = int(environment["logical_processor_count"])

    print("[2/3] 构建 Release", flush=True)
    build_output = _build_release(build_root, demo_root)
    benchmark_executable = build_root / "bin" / "csc3_demo_benchmark.exe"
    if not benchmark_executable.is_file():
        raise ExampleError(f"Release 构建后没有找到性能程序：{benchmark_executable}")

    toolchain = _toolchain_facts(
        cache,
        build_root,
        demo_root,
        build_output,
        benchmark_executable,
    )
    if mode == DEMO_MODE:
        print(f"[3/3] 运行 WindHub（{maximum_threads} 线程）", flush=True)
        return _run_demo(
            runner=runner,
            demo_root=demo_root,
            benchmark_executable=benchmark_executable,
            input_path=input_path,
            result_root=result_root,
            maximum_threads=maximum_threads,
            source=source,
            source_tools=source_tools,
            input_facts=input_facts,
            environment=environment,
            toolchain=toolchain,
        )

    print(f"[3/3] 运行完整线程扫描（1–{maximum_threads} 线程）", flush=True)
    sample_count = maximum_threads * (FULL_WARMUP_COUNT + FULL_REPEAT_COUNT)
    print(
        f"将按 1 到 {maximum_threads} 个线程运行 {sample_count} 个独立进程样本。"
        "运行期间不会并发启动样本。",
        flush=True,
    )

    options = argparse.Namespace(
        repository_root=repository_root,
        benchmark_executable=benchmark_executable,
        input=input_path,
        out_dir=result_root,
        maximum_threads=maximum_threads,
        warmup=FULL_WARMUP_COUNT,
        repeat=FULL_REPEAT_COUNT,
        toolchain=toolchain,
        source_tools=source_tools,
        source=source,
        input_facts=input_facts,
        environment=environment,
        issue=ISSUE_NUMBER,
        progress=True,
        result_stream=None,
    )
    runner.run_benchmark(options)

    summary_path = result_root / "benchmark_summary.json"
    manifest_path = result_root / "run_manifest.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        markdown = render_summary_markdown(summary, manifest)
        runner._atomic_write_text(result_root / "summary.md", markdown)
        manifest["artifacts"] = runner._artifact_records(result_root)
        runner._atomic_write_text(manifest_path, runner._canonical_json(manifest))
        print_console_summary(summary, result_root, demo_root)
    except (Exception, KeyboardInterrupt) as error:
        manifest["status"] = "FAIL"
        manifest["failure"] = f"{type(error).__name__}: {error}"
        manifest["artifacts"] = runner._artifact_records(result_root)
        runner._atomic_write_text(manifest_path, runner._canonical_json(manifest))
        raise
    return 0


def _report_failure(
    paths: ExamplePaths,
    output_root: Path,
    error: BaseException,
) -> None:
    print(f"错误：{error}", file=sys.stderr)
    try:
        failure_path = _write_failure_record(
            _failure_root(paths, output_root),
            error,
        )
        print(f"失败记录：{failure_path}", file=sys.stderr)
    except OSError as record_error:
        print(f"另有错误：无法保存失败记录：{record_error}", file=sys.stderr)


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default=FULL_MODE,
        help="full 运行完整线程扫描；demo 运行单次满线程演示",
    )
    options = parser.parse_args(arguments)
    paths = discover_paths()
    output_root = _output_root(paths.build_root, mode=options.mode)
    try:
        return run_example(paths, output_root, mode=options.mode)
    except KeyboardInterrupt:
        error = ExampleError("运行已由用户中断，当前样本子进程已经停止。")
        _report_failure(paths, output_root, error)
        return 130
    except (
        ExampleError,
        OSError,
        RuntimeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        _report_failure(paths, output_root, error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
