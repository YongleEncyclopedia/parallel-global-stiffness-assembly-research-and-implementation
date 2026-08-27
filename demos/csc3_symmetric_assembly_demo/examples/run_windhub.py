#!/usr/bin/env python3
"""构建 Release benchmark，并按 Windows 正式口径运行 WindHub。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
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
ISSUE_NUMBER = 72


class ExampleError(RuntimeError):
    """表示一键示例尚未满足运行条件。"""


@dataclass(frozen=True)
class ExamplePaths:
    """一键入口从脚本位置推导出的仓库路径。"""

    demo_root: Path
    repository_root: Path
    build_root: Path
    input_path: Path


def discover_paths(script_path: Path | None = None) -> ExamplePaths:
    resolved_script = (script_path or Path(__file__)).resolve()
    demo_root = resolved_script.parents[1]
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
        raise ExampleError(f"无法加载 Windows 性能脚本：{path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _cache_entries(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ExampleError(
            "没有找到 build/CMakeCache.txt。请先按 README 的五行命令完成 MSVC 编译。"
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
        r'set\(CMAKE_CXX_COMPILER_ARCHITECTURE_ID "([^"]+)"\)',
        text,
    )
    if identifier is None or version is None or architecture is None:
        raise ExampleError("无法从 CMake 构建目录读取编译器名称、版本和架构。")
    return identifier.group(1), version.group(1), architecture.group(1)


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
    print("正在构建 Release 性能程序……", flush=True)
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
    if output:
        print(output, flush=True)
    if completed.returncode != 0:
        raise ExampleError("Release 性能程序构建失败，请从上面的第一条错误开始检查。")
    return output


def _openmp_runtime_text(cache: Mapping[str, str], build_root: Path) -> str:
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


def _build_tool_text(build_output: str, generator: str) -> str:
    line = next(
        (item.strip() for item in build_output.splitlines() if "MSBuild" in item),
        "",
    )
    return line or f"cmake --build（{generator}）"


def _toolchain_facts(
    cache: Mapping[str, str],
    build_root: Path,
    demo_root: Path,
    build_output: str,
) -> dict[str, str]:
    generator = cache.get("CMAKE_GENERATOR", "").strip()
    compiler_id, compiler_version, compiler_architecture = _compiler_facts(build_root)
    cmake_banner = _run_text(["cmake", "--version"], demo_root).splitlines()[0]
    return {
        "compiler": f"{compiler_id} {compiler_version} ({compiler_architecture})",
        "cmake": cmake_banner,
        "cmake_generator": generator,
        "build_tool": _build_tool_text(build_output, generator),
        "openmp_runtime": _openmp_runtime_text(cache, build_root),
        "benchmark_build_type": "Release",
    }


def _output_root(build_root: Path, now: datetime | None = None) -> Path:
    value = now or datetime.now()
    timestamp = value.strftime("%Y%m%d-%H%M%S-%f")
    return build_root / "example-results" / timestamp


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
    if (
        memory_definition.get("peak_working_set")
        != "GetProcessMemoryInfo.PeakWorkingSetSize"
        or memory_definition.get("peak_working_set_is_os_measured") is not True
    ):
        raise ExampleError("峰值内存不是 Windows 进程接口的实测值。")

    raw_rows = summary.get("per_thread")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ExampleError("汇总结果中没有线程数据。")
    rows: list[dict[str, float | int]] = []
    for item in raw_rows:
        if not isinstance(item, Mapping):
            raise ExampleError("汇总结果中的线程数据格式不正确。")
        total = item.get("parallel_total_ms")
        peak = item.get("peak_working_set_bytes")
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
                    "peak_working_set_bytes.median",
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
    case = summary.get("case_sizes")
    correctness = summary.get("correctness")
    configuration = summary.get("configuration")
    source = manifest.get("source")
    environment = manifest.get("environment")
    toolchain = manifest.get("toolchain")
    for value, label in (
        (case, "算例规模"),
        (correctness, "正确性"),
        (configuration, "实验配置"),
        (source, "源码信息"),
        (environment, "Windows 环境"),
        (toolchain, "工具链"),
    ):
        if not isinstance(value, Mapping):
            raise ExampleError(f"运行记录缺少{label}。")
    if summary.get("status") != "PASS" or manifest.get("status") != "PASS":
        raise ExampleError("运行记录尚未通过，不能生成结果报告。")

    rows = _summary_rows(summary)
    maximum_relative_error = _number(
        correctness.get("relative_frobenius_error_maximum"),
        "relative_frobenius_error_maximum",
    )
    lines = [
        "# WindHub Windows 全线程运行结果",
        "",
        f"- 状态：`{summary.get('status')}`",
        f"- 源码提交：`{source.get('commit_sha')}`",
        (
            f"- 系统：{environment.get('caption')} {environment.get('version')}，"
            f"{environment.get('architecture')}"
        ),
        f"- 处理器：{environment.get('cpu_model')}",
        f"- 编译器：{toolchain.get('compiler')}，Release",
        (
            f"- 构建：{toolchain.get('cmake')} / "
            f"{toolchain.get('cmake_generator')} / {toolchain.get('build_tool')}"
        ),
        f"- OpenMP：{toolchain.get('openmp_runtime')}",
        "",
        "## 算例与正确性",
        "",
        f"WindHub 包含 {case.get('node_count')} 个节点、{case.get('element_count')} 个 Tet4 单元、"
        f"{case.get('dof_count')} 个自由度，CSC3 非零项数为 {case.get('nnz')}。",
        "",
        (
            f"矩阵正确性：`{correctness.get('status')}`；最大相对 Frobenius 误差为 "
            f"{maximum_relative_error:.6e}。"
        ),
        "",
        "## 测量方法",
        "",
        (
            f"线程数覆盖 $p=1,2,\\ldots,{configuration.get('maximum_threads')}$。"
            "每档先预热 "
            f"$W={configuration.get('warmup_count')}$ 次，再正式测量 "
            f"$R={configuration.get('repeat_count')}$ 次。每个样本都在新的进程中运行，"
            "样本之间不并发。峰值内存为 Windows 记录的进程峰值工作集。"
        ),
        "",
        "## 各线程结果",
        "",
        (
            "| 线程数 $p$ | 符号组装中位数（ms） | 原子累加数值组装中位数（ms） | "
            "总时间中位数（ms） | 总时间 $CV$ | 整体加速比 | 峰值内存中位数（GiB） |"
        ),
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['thread_count']} | {row['symbolic_ms']:.3f} | {row['numeric_ms']:.3f} | "
            f"{row['total_ms']:.3f} | {100.0 * row['total_cv']:.2f}% | "
            f"{row['speedup']:.4f} | {row['peak_gib']:.4f} |"
        )
    lines.extend(
        [
            "",
            "不同电脑的时间和内存会有差异；结果只代表本机、本次提交和本次运行，"
            "不要求与历史报告数值相同。",
            "",
        ]
    )
    return "\n".join(lines)


def print_console_summary(
    summary: Mapping[str, object],
    output_root: Path,
) -> None:
    case = summary.get("case_sizes")
    correctness = summary.get("correctness")
    if not isinstance(case, Mapping) or not isinstance(correctness, Mapping):
        raise ExampleError("运行结果缺少算例或正确性信息。")
    print("\nWindHub 运行完成")
    print(f"节点：{case.get('node_count')}")
    print(f"单元：{case.get('element_count')}")
    print(f"自由度：{case.get('dof_count')}")
    print(f"矩阵正确性：{correctness.get('status')}")
    print("\n线程  总时间中位数(ms)  CV(%)  整体加速比  峰值内存中位数(GiB)")
    for row in _summary_rows(summary):
        print(
            f"{row['thread_count']:>4}  {row['total_ms']:>16.3f}  "
            f"{100.0 * row['total_cv']:>5.2f}  {row['speedup']:>10.4f}  "
            f"{row['peak_gib']:>19.4f}"
        )
    print(f"\n结果目录：{output_root}")


def run_example(
    paths: ExamplePaths | None = None,
    output_root: Path | None = None,
) -> int:
    if os.name != "nt":
        raise ExampleError("这个一键示例必须在 Windows 上运行。")
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
    result_root = output_root or _output_root(build_root)
    cache = _cache_entries(build_root / "CMakeCache.txt")
    generator = cache.get("CMAKE_GENERATOR", "")
    if generator != "Visual Studio 17 2022":
        raise ExampleError(
            "build 不是 README 创建的 Visual Studio 2022 构建目录。"
            "请删除错误的 build 后重新执行 README 五行命令。"
        )
    compiler_id, _, compiler_architecture = _compiler_facts(build_root)
    if compiler_id != "MSVC" or compiler_architecture != "x64":
        raise ExampleError("WindHub 报告复现入口要求使用 README 的 MSVC x64 build。")

    source_tools = _git_tools(repository_root)
    runner = _load_runner(demo_root)
    try:
        runner._source_provenance(repository_root)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        if "工作树干净" in str(error):
            raise ExampleError(
                f"{error}\n请先提交或还原已跟踪文件的修改，再重新运行。"
            ) from error
        raise ExampleError(
            f"无法读取 Git 源码状态：{error}\n"
            "这个入口需要完整的 Git 仓库，不能使用单独的 Demo 源码 ZIP。"
        ) from error
    try:
        runner._input_provenance(input_path, repository_root)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise ExampleError(
            f"{error}\n请在仓库根目录执行：\n"
            "git lfs install\n"
            'git lfs pull --include="examples/3d-WindTurbineHub.inp"'
        ) from error

    build_output = _build_release(build_root, demo_root)
    benchmark_executable = build_root / "bin" / "csc3_demo_benchmark.exe"
    if not benchmark_executable.is_file():
        raise ExampleError(f"Release 构建后没有找到性能程序：{benchmark_executable}")

    environment = runner._windows_environment()
    maximum_threads = int(environment["logical_processor_count"])
    toolchain = _toolchain_facts(
        cache,
        build_root,
        demo_root,
        build_output,
    )
    sample_count = maximum_threads * (runner.WARMUP_COUNT + runner.REPEAT_COUNT)
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
        warmup=runner.WARMUP_COUNT,
        repeat=runner.REPEAT_COUNT,
        toolchain=toolchain,
        source_tools=source_tools,
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
        print_console_summary(summary, result_root)
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
    parser.parse_args(arguments)
    paths = discover_paths()
    output_root = _output_root(paths.build_root)
    try:
        return run_example(paths, output_root)
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
