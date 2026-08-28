#!/usr/bin/env python3
r"""在 Windows 上逐线程、逐进程运行 WindHub 性能实验。

脚本覆盖 $p=1,\ldots,P_{\max}$，每个预热或正式样本都使用新的子进程；它通过
GetProcessMemoryInfo 记录峰值工作集，并输出 CSV、JSON 和 manifest。样本调度与
正确性协议保持不变；结果 schema 随直接串行基线升级。
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO


SCHEMA_VERSION = "csc3-demo-windows-process-benchmark-v2"
MANIFEST_SCHEMA_VERSION = "csc3-demo-windows-process-manifest-v1"
GENERIC_TOOLCHAIN_MANIFEST_SCHEMA_VERSION = "csc3-demo-windows-process-manifest-v2"
PORTABLE_MANIFEST_SCHEMA_VERSION = "csc3-demo-process-manifest-v1"
WARMUP_COUNT = 2
REPEAT_COUNT = 7
RELATIVE_FROBENIUS_TOLERANCE = 1.0e-8
PEAK_WORKING_SET_SOURCE = "GetProcessMemoryInfo.PeakWorkingSetSize"

PROCESS_CSV_FIELDS = (
    "schema_version",
    "sample_id",
    "sample_kind",
    "round",
    "order_position",
    "thread_count",
    "pid",
    "started_at_utc",
    "ended_at_utc",
    "wall_time_seconds",
    "exit_code",
    "peak_working_set_bytes",
    "peak_working_set_source",
    "symbolic_team_size_observed",
    "numeric_team_size_observed",
    "input_prepare_ms",
    "serial_direct_ms",
    "serial_symbolic_ms",
    "serial_numeric_ms",
    "serial_total_ms",
    "parallel_symbolic_ms",
    "parallel_numeric_ms",
    "parallel_total_ms",
    "estimated_persistent_bytes",
    "relative_frobenius_error",
    "max_absolute_error",
    "structure_matches",
    "matrix_correctness_status",
    "scatter_correctness_status",
    "symbolic_plan_matches_serial",
    "numeric_setup_plan_matches_serial",
    "raw_csv_path",
    "raw_json_path",
    "stdout_log_path",
    "stderr_log_path",
)

class BenchmarkContractError(RuntimeError):
    """表示样本、调度或证据违反交付契约。"""


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_json(value: object) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_text(command: Sequence[str], cwd: Path) -> str:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise BenchmarkContractError(f"证据路径不在输出目录内：{path}") from error


def build_schedule(
    maximum_threads: int,
    warmup_count: int = WARMUP_COUNT,
    repeat_count: int = REPEAT_COUNT,
) -> list[dict[str, int | str]]:
    """生成预热及正式轮次；每一轮交替升序和降序。"""

    if maximum_threads <= 0:
        raise ValueError("maximum_threads 必须为正整数")
    if warmup_count < 0 or repeat_count <= 0:
        raise ValueError("预热轮数必须非负，正式轮数必须为正")

    schedule: list[dict[str, int | str]] = []
    for sample_kind, round_count in (
        ("warmup", warmup_count),
        ("measured", repeat_count),
    ):
        for round_number in range(1, round_count + 1):
            thread_order: Iterable[int]
            if round_number % 2 == 1:
                thread_order = range(1, maximum_threads + 1)
            else:
                thread_order = range(maximum_threads, 0, -1)
            for order_position, thread_count in enumerate(thread_order, start=1):
                schedule.append(
                    {
                        "sample_kind": sample_kind,
                        "round": round_number,
                        "order_position": order_position,
                        "thread_count": thread_count,
                    }
                )
    return schedule


def _sample_id(specification: Mapping[str, int | str]) -> str:
    return (
        f"{specification['sample_kind']}-"
        f"r{int(specification['round']):02d}-"
        f"o{int(specification['order_position']):02d}-"
        f"p{int(specification['thread_count']):02d}"
    )


def _statistics(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise BenchmarkContractError("统计量至少需要一个样本")
    normalized = [float(value) for value in values]
    if any(not math.isfinite(value) or value < 0.0 for value in normalized):
        raise BenchmarkContractError("统计样本必须为有限非负数")
    mean = statistics.fmean(normalized)
    standard_deviation = statistics.pstdev(normalized)
    coefficient = 0.0 if mean == 0.0 else standard_deviation / mean
    return {
        "sample_count": len(normalized),
        "median": statistics.median(normalized),
        "mean": mean,
        "population_standard_deviation": standard_deviation,
        "minimum": min(normalized),
        "maximum": max(normalized),
        "coefficient_of_variation": coefficient,
    }


def _windows_environment() -> dict[str, object]:
    if os.name != "nt":
        raise BenchmarkContractError("该 runner 只允许在 Windows 上生成交付证据")
    script = (
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();"
        "$os=Get-CimInstance Win32_OperatingSystem;"
        "$cpu=@(Get-CimInstance Win32_Processor);"
        "$cs=Get-CimInstance Win32_ComputerSystem;"
        "[pscustomobject]@{"
        "caption=$os.Caption;"
        "version=$os.Version;"
        "build_number=$os.BuildNumber;"
        "architecture=$os.OSArchitecture;"
        "cpu_model=($cpu.Name -join '; ');"
        "physical_core_count=(($cpu.NumberOfCores|Measure-Object -Sum).Sum);"
        "logical_processor_count=(($cpu.NumberOfLogicalProcessors|Measure-Object -Sum).Sum);"
        "total_physical_memory_bytes=[uint64]$cs.TotalPhysicalMemory"
        "}|ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    facts = json.loads(completed.stdout)
    if not isinstance(facts, dict):
        raise BenchmarkContractError("无法读取 Windows 主机信息")
    facts["python_version"] = sys.version.split()[0]
    return facts


def _host_environment() -> dict[str, object]:
    return _windows_environment()


def _source_provenance(repository_root: Path) -> dict[str, object]:
    repository_root = repository_root.resolve()
    commit_sha = _run_text(["git", "rev-parse", "HEAD"], repository_root)
    branch = _run_text(["git", "branch", "--show-current"], repository_root)
    dirty = _run_text(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        repository_root,
    )
    if len(commit_sha) != 40 or any(character not in "0123456789abcdef" for character in commit_sha):
        raise BenchmarkContractError("无法取得完整的源码提交 SHA")
    if dirty:
        raise BenchmarkContractError("正式性能实验要求已跟踪文件工作树干净")
    return {
        "commit_sha": commit_sha,
        "branch": branch,
        "tracked_worktree_clean_at_start": True,
    }


def _input_provenance(input_path: Path, repository_root: Path) -> dict[str, object]:
    input_path = input_path.resolve()
    repository_root = repository_root.resolve()
    try:
        relative = input_path.relative_to(repository_root).as_posix()
    except ValueError as error:
        raise BenchmarkContractError("WindHub 输入必须位于当前 Git 仓库内") from error

    _run_text(["git", "ls-files", "--error-unmatch", "--", relative], repository_root)
    pointer = _run_text(["git", "show", f"HEAD:{relative}"], repository_root)
    pointer_lines = pointer.splitlines()
    if (
        len(pointer_lines) < 3
        or pointer_lines[0] != "version https://git-lfs.github.com/spec/v1"
        or not pointer_lines[1].startswith("oid sha256:")
        or not pointer_lines[2].startswith("size ")
    ):
        raise BenchmarkContractError("WindHub 在 HEAD 中不是有效的 Git LFS 指针")
    expected_sha256 = pointer_lines[1].removeprefix("oid sha256:")
    expected_size = int(pointer_lines[2].removeprefix("size "))
    actual_size = input_path.stat().st_size
    actual_sha256 = _sha256_file(input_path)
    if actual_size != expected_size or actual_sha256 != expected_sha256:
        raise BenchmarkContractError("WindHub Git LFS 实体与 HEAD 指针不一致")
    return {
        "repository_relative_path": relative,
        "sha256": actual_sha256,
        "size_bytes": actual_size,
        "git_lfs_materialized": True,
        "matches_head_lfs_pointer": True,
    }


def _query_peak_working_set(process_handle: int) -> int:
    if os.name != "nt":
        raise BenchmarkContractError("峰值内存占用只能由 Windows 接口采集")
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    function = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    function.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    function.restype = wintypes.BOOL
    if not function(
        wintypes.HANDLE(process_handle),
        ctypes.byref(counters),
        counters.cb,
    ):
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GetProcessMemoryInfo 调用失败")
    return int(counters.PeakWorkingSetSize)


def _wait_windows_process(process: subprocess.Popen[bytes]) -> tuple[int, int]:
    process_handle = int(getattr(process, "_handle"))
    peak_working_set = 0
    successful_queries = 0
    while True:
        try:
            peak_working_set = max(
                peak_working_set,
                _query_peak_working_set(process_handle),
            )
            successful_queries += 1
        except OSError:
            if process.poll() is None:
                process.kill()
                process.wait()
                raise
        if process.poll() is not None:
            break
        time.sleep(0.01)
    try:
        peak_working_set = max(
            peak_working_set,
            _query_peak_working_set(process_handle),
        )
        successful_queries += 1
    except OSError:
        pass
    exit_code = process.wait()
    if successful_queries == 0 or peak_working_set <= 0:
        raise BenchmarkContractError("未取得 Windows 峰值工作集")
    return exit_code, peak_working_set


def _one_csv_row(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise BenchmarkContractError(f"子进程 CSV 必须恰好包含一条样本：{path}")
    return rows[0]


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or value is None:
        raise BenchmarkContractError(f"{label} 必须是数值")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as error:
        raise BenchmarkContractError(f"{label} 必须是数值") from error
    if not math.isfinite(normalized) or normalized < 0.0:
        raise BenchmarkContractError(f"{label} 必须为有限非负数")
    return normalized


def _validate_child_outputs(
    raw_csv: Path,
    raw_json: Path,
    thread_count: int,
) -> dict[str, object]:
    row = _one_csv_row(raw_csv)
    summary = json.loads(raw_json.read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or summary.get("schema_version") != "csc3-demo-benchmark-v3":
        raise BenchmarkContractError("子进程 JSON schema 不受支持")
    if row.get("schema_version") != "csc3-demo-benchmark-v3":
        raise BenchmarkContractError("子进程 CSV schema 不受支持")
    configuration = summary.get("configuration")
    if not isinstance(configuration, dict) or configuration != {
        "case": "windhub",
        "nx": 0,
        "ny": 0,
        "nz": 0,
        "thread_counts": [thread_count],
        "warmup_count": 0,
        "repeat_count": 1,
        "amortization_count": 1,
        "performance_evidence_level": "local-smoke",
    }:
        raise BenchmarkContractError("子进程配置与独立单样本契约不一致")
    if row.get("thread_count") != str(thread_count) or row.get("sample_kind") != "measured":
        raise BenchmarkContractError("子进程 CSV 样本身份不一致")

    correctness = summary.get("correctness")
    scatter = summary.get("scatter_correctness")
    per_thread = summary.get("per_thread_measured_statistics")
    validation_cases = summary.get("validation_cases")
    if not isinstance(correctness, dict) or not isinstance(scatter, dict):
        raise BenchmarkContractError("子进程正确性字段缺失")
    if not isinstance(per_thread, list) or len(per_thread) != 1 or not isinstance(per_thread[0], dict):
        raise BenchmarkContractError("子进程线程统计字段缺失")
    if not isinstance(validation_cases, list) or not validation_cases:
        raise BenchmarkContractError("子进程独立验证用例缺失")
    thread_summary = per_thread[0]
    symbolic_team = int(thread_summary.get("symbolic_thread_count_observed", 0))
    numeric_team = int(thread_summary.get("numeric_thread_count_observed", 0))
    if symbolic_team != thread_count or numeric_team != thread_count:
        raise BenchmarkContractError(
            f"实际 OpenMP team size 与请求不符：请求 {thread_count}，"
            f"符号 {symbolic_team}，数值 {numeric_team}"
        )
    relative_error = _finite_nonnegative(
        correctness.get("relative_frobenius_error"),
        "relative_frobenius_error",
    )
    if (
        correctness.get("status") != "PASS"
        or correctness.get("structure_matches") is not True
        or relative_error > RELATIVE_FROBENIUS_TOLERANCE
        or scatter.get("status") != "PASS"
        or any(
            not isinstance(case, dict) or case.get("status") != "PASS"
            for case in validation_cases
        )
    ):
        raise BenchmarkContractError("子进程矩阵或 scatter 正确性未通过")

    serial_direct = _finite_nonnegative(row.get("serial_direct_ms"), "serial_direct_ms")
    serial_symbolic = _finite_nonnegative(row.get("serial_symbolic_ms"), "serial_symbolic_ms")
    serial_numeric = _finite_nonnegative(row.get("serial_numeric_ms"), "serial_numeric_ms")
    if serial_direct <= 0.0:
        raise BenchmarkContractError("直接串行组装时间必须为正数")
    if summary.get("serial_reference_definition") != (
        "direct contribution generation, sort, and reduction; "
        "no prebuilt CSC3 or scatter"
    ):
        raise BenchmarkContractError("子进程没有声明约定的无符号直接串行参考")
    direct_statistics = summary.get("serial_direct_measured_statistics")
    phase_statistics = summary.get("serial_two_stage_phase_measured_statistics")
    if not isinstance(direct_statistics, dict) or not isinstance(phase_statistics, dict):
        raise BenchmarkContractError("子进程缺少直接串行或两阶段诊断统计")

    def require_single_sample_median(
        statistics: object,
        expected: float,
        label: str,
    ) -> None:
        if not isinstance(statistics, dict) or statistics.get("sample_count") != 1:
            raise BenchmarkContractError(f"{label} 必须是单样本统计")
        median = _finite_nonnegative(statistics.get("median_ms"), f"{label}.median_ms")
        tolerance = 1.0e-12 * max(1.0, abs(expected))
        if abs(median - expected) > tolerance:
            raise BenchmarkContractError(f"{label} 与子进程 CSV 不一致")

    require_single_sample_median(
        direct_statistics.get("total_ms"), serial_direct, "直接串行统计"
    )
    require_single_sample_median(
        phase_statistics.get("symbolic_total_ms"),
        serial_symbolic,
        "两阶段串行符号诊断",
    )
    require_single_sample_median(
        phase_statistics.get("numeric_total_ms"),
        serial_numeric,
        "两阶段串行数值诊断",
    )
    parallel_symbolic = _finite_nonnegative(row.get("symbolic_total_ms"), "symbolic_total_ms")
    parallel_numeric = _finite_nonnegative(row.get("numeric_total_ms"), "numeric_total_ms")
    parallel_total = parallel_symbolic + parallel_numeric
    recorded_total = _finite_nonnegative(row.get("amortized_total_ms"), "amortized_total_ms")
    tolerance = 1.0e-9 * max(1.0, parallel_total)
    if abs(recorded_total - parallel_total) > tolerance:
        raise BenchmarkContractError("子进程总时间不等于符号总时间加数值总时间")
    estimated_persistent_bytes = int(row["estimated_persistent_bytes"])
    if estimated_persistent_bytes <= 0:
        raise BenchmarkContractError("estimated_persistent_bytes 必须为正整数")

    return {
        "symbolic_team_size_observed": symbolic_team,
        "numeric_team_size_observed": numeric_team,
        "input_prepare_ms": _finite_nonnegative(row.get("input_prepare_ms"), "input_prepare_ms"),
        "serial_direct_ms": serial_direct,
        "serial_symbolic_ms": serial_symbolic,
        "serial_numeric_ms": serial_numeric,
        "serial_total_ms": serial_direct,
        "parallel_symbolic_ms": parallel_symbolic,
        "parallel_numeric_ms": parallel_numeric,
        "parallel_total_ms": parallel_total,
        "estimated_persistent_bytes": estimated_persistent_bytes,
        "relative_frobenius_error": relative_error,
        "max_absolute_error": _finite_nonnegative(
            correctness.get("max_absolute_error"),
            "max_absolute_error",
        ),
        "structure_matches": True,
        "matrix_correctness_status": "PASS",
        "scatter_correctness_status": "PASS",
        "symbolic_plan_matches_serial": row.get("symbolic_plan_matches_serial") == "true",
        "numeric_setup_plan_matches_serial": (
            row.get("numeric_setup_plan_matches_serial") == "true"
        ),
        "case_sizes": summary.get("case_sizes"),
    }


def _write_process_csv(path: Path, records: Sequence[Mapping[str, object]]) -> None:
    if not records:
        raise BenchmarkContractError("进程 CSV 至少需要一条记录")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=PROCESS_CSV_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _run_one_sample(
    benchmark_executable: Path,
    input_path: Path,
    output_root: Path,
    specification: Mapping[str, int | str],
) -> dict[str, object]:
    sample_id = _sample_id(specification)
    sample_root = output_root / "raw" / sample_id
    sample_root.mkdir(parents=True, exist_ok=False)
    raw_csv = sample_root / "benchmark_samples.csv"
    raw_json = sample_root / "benchmark_summary.json"
    stdout_log = sample_root / "stdout.txt"
    stderr_log = sample_root / "stderr.txt"
    thread_count = int(specification["thread_count"])
    command = [
        str(benchmark_executable),
        "--case",
        "windhub",
        "--input",
        str(input_path),
        "--threads-list",
        str(thread_count),
        "--warmup",
        "0",
        "--repeat",
        "1",
        "--amortization-count",
        "1",
        "--evidence-level",
        "local-smoke",
        "--samples-csv",
        str(raw_csv),
        "--summary-json",
        str(raw_json),
    ]
    environment = dict(os.environ)
    environment.update(
        {
            "OMP_DYNAMIC": "false",
            "OMP_NUM_THREADS": str(thread_count),
            "OMP_THREAD_LIMIT": str(thread_count),
        }
    )
    started_at = _utc_now()
    monotonic_start = time.perf_counter()
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with stdout_log.open("wb") as standard_output, stderr_log.open("wb") as standard_error:
        process = subprocess.Popen(
            command,
            cwd=output_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=standard_output,
            stderr=standard_error,
            creationflags=creation_flags,
        )
        try:
            exit_code, peak_working_set = _wait_windows_process(process)
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
    ended_at = _utc_now()
    wall_time_seconds = time.perf_counter() - monotonic_start
    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "sample_id": sample_id,
        **specification,
        "pid": process.pid,
        "started_at_utc": _utc_text(started_at),
        "ended_at_utc": _utc_text(ended_at),
        "wall_time_seconds": wall_time_seconds,
        "exit_code": exit_code,
        "peak_working_set_bytes": peak_working_set,
        "peak_working_set_source": PEAK_WORKING_SET_SOURCE,
        "raw_csv_path": _relative_path(raw_csv, output_root),
        "raw_json_path": _relative_path(raw_json, output_root),
        "stdout_log_path": _relative_path(stdout_log, output_root),
        "stderr_log_path": _relative_path(stderr_log, output_root),
    }
    if exit_code != 0:
        error_text = stderr_log.read_text(encoding="utf-8", errors="replace").strip()
        raise BenchmarkContractError(
            f"{sample_id} 子进程退出码为 {exit_code}：{error_text[-1000:]}"
        )
    record.update(_validate_child_outputs(raw_csv, raw_json, thread_count))
    record.pop("case_sizes", None)
    return record


def summarize_records(
    records: Sequence[Mapping[str, object]],
    maximum_threads: int,
    warmup_count: int = WARMUP_COUNT,
    repeat_count: int = REPEAT_COUNT,
) -> dict[str, object]:
    expected_count = maximum_threads * (warmup_count + repeat_count)
    if len(records) != expected_count:
        raise BenchmarkContractError(
            f"样本数不完整：期望 {expected_count}，实际 {len(records)}"
        )
    identities = [str(record["sample_id"]) for record in records]
    if len(set(identities)) != len(identities):
        raise BenchmarkContractError("样本身份重复")
    expected_schedule = build_schedule(
        maximum_threads,
        warmup_count,
        repeat_count,
    )
    for record, expected in zip(records, expected_schedule):
        for field in ("sample_kind", "round", "order_position", "thread_count"):
            if record[field] != expected[field]:
                raise BenchmarkContractError(
                    "样本执行顺序不符合升序/降序交替调度"
                )
        if str(record["sample_id"]) != _sample_id(expected):
            raise BenchmarkContractError("样本身份与调度字段不一致")

    previous_end: datetime | None = None
    measured_by_thread: dict[int, list[Mapping[str, object]]] = {
        thread: [] for thread in range(1, maximum_threads + 1)
    }
    for record in records:
        started_at = datetime.fromisoformat(
            str(record["started_at_utc"]).replace("Z", "+00:00")
        )
        ended_at = datetime.fromisoformat(
            str(record["ended_at_utc"]).replace("Z", "+00:00")
        )
        if ended_at < started_at:
            raise BenchmarkContractError("样本结束时间早于开始时间")
        if previous_end is not None and started_at < previous_end:
            raise BenchmarkContractError("检测到 benchmark 样本重叠")
        previous_end = ended_at
        thread_count = int(record["thread_count"])
        if int(record["exit_code"]) != 0:
            raise BenchmarkContractError("存在退出失败的样本")
        if (
            int(record["symbolic_team_size_observed"]) != thread_count
            or int(record["numeric_team_size_observed"]) != thread_count
        ):
            raise BenchmarkContractError("存在实际 team size 不符的样本")
        if record["sample_kind"] == "measured":
            measured_by_thread[thread_count].append(record)

    for thread_count, samples in measured_by_thread.items():
        if len(samples) != repeat_count:
            raise BenchmarkContractError(
                f"线程 {thread_count} 的正式样本数不是 {repeat_count}"
            )

    if not all("peak_working_set_bytes" in record for record in records):
        raise BenchmarkContractError("样本缺少 Windows 峰值工作集")

    canonical_serial = [
        float(record["serial_total_ms"]) for record in measured_by_thread[1]
    ]
    canonical_serial_statistics = _statistics(canonical_serial)
    serial_median = float(canonical_serial_statistics["median"])
    per_thread: list[dict[str, object]] = []
    for thread_count in range(1, maximum_threads + 1):
        samples = measured_by_thread[thread_count]
        parallel_total = [float(record["parallel_total_ms"]) for record in samples]
        total_statistics = _statistics(parallel_total)
        candidate_median = float(total_statistics["median"])
        speedup = serial_median / candidate_median
        thread_summary = {
                "thread_count": thread_count,
                "observed_team_sizes": sorted(
                    {
                        int(record["symbolic_team_size_observed"])
                        for record in samples
                    }
                    | {
                        int(record["numeric_team_size_observed"])
                        for record in samples
                    }
                ),
                "serial_total_ms": _statistics(
                    [float(record["serial_total_ms"]) for record in samples]
                ),
                "parallel_symbolic_ms": _statistics(
                    [float(record["parallel_symbolic_ms"]) for record in samples]
                ),
                "parallel_numeric_ms": _statistics(
                    [float(record["parallel_numeric_ms"]) for record in samples]
                ),
                "parallel_total_ms": total_statistics,
                "overall_speedup": speedup,
                "estimated_persistent_bytes": _statistics(
                    [float(record["estimated_persistent_bytes"]) for record in samples]
                ),
            }
        thread_summary["peak_working_set_bytes"] = _statistics(
            [float(record["peak_working_set_bytes"]) for record in samples]
        )
        per_thread.append(thread_summary)

    relative_errors = [
        float(record["relative_frobenius_error"]) for record in records
    ]
    maximum_relative_error = max(relative_errors)
    correctness_passed = (
        maximum_relative_error <= RELATIVE_FROBENIUS_TOLERANCE
        and all(record["structure_matches"] is True for record in records)
        and all(record["matrix_correctness_status"] == "PASS" for record in records)
        and all(record["scatter_correctness_status"] == "PASS" for record in records)
        and all(record["symbolic_plan_matches_serial"] is True for record in records)
        and all(
            record["numeric_setup_plan_matches_serial"] is True
            for record in records
        )
    )
    if not correctness_passed:
        raise BenchmarkContractError("矩阵或 scatter 正确性汇总未通过")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "configuration": {
            "thread_counts": list(range(1, maximum_threads + 1)),
            "maximum_threads": maximum_threads,
            "warmup_count": warmup_count,
            "repeat_count": repeat_count,
            "sample_process_model": "one_fresh_child_process_per_sample",
            "measured_round_order": "alternating_ascending_descending",
            "samples_are_serialized": True,
            "time_definition": {
                "serial_total_ms": "serial_direct_ms",
                "serial_direct_ms": (
                    "direct contribution generation, sort, and reduction without a "
                    "prebuilt CSC3 structure or scatter"
                ),
                "serial_symbolic_ms": "two-stage phase diagnostic only",
                "serial_numeric_ms": "two-stage phase diagnostic only",
                "parallel_total_ms": "parallel_symbolic_ms + parallel_numeric_ms",
                "overall_speedup": (
                    "median(serial_total_ms from measured p=1 child processes) / "
                    "median(parallel_total_ms for p)"
                ),
            },
        },
        "process_integrity": {
            "expected_sample_count": expected_count,
            "observed_sample_count": len(records),
            "measured_sample_count_per_thread": repeat_count,
            "unique_sample_ids": True,
            "samples_overlap": False,
            "all_exit_codes_zero": True,
            "all_observed_team_sizes_match": True,
        },
        "correctness": {
            "status": "PASS",
            "all_csc3_structures_match": True,
            "all_values_finite": True,
            "all_scatter_indices_legal": True,
            "all_scatter_plans_match_independent_serial": True,
            "relative_frobenius_error_maximum": maximum_relative_error,
            "relative_frobenius_error_threshold": RELATIVE_FROBENIUS_TOLERANCE,
        },
        "memory_definition": {
            "peak_working_set": PEAK_WORKING_SET_SOURCE,
            "peak_working_set_is_os_measured": True,
            "estimated_persistent_bytes": (
                "owned vector payload capacity estimate; not RSS or peak memory"
            ),
        },
        "serial_baseline_source": (
            "direct serial assembly from seven measured p=1 child processes"
        ),
        "serial_baseline_total_ms": canonical_serial_statistics,
        "per_thread": per_thread,
    }


def _artifact_records(output_root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name == "run_manifest.json":
            continue
        records.append(
            {
                "path": _relative_path(path, output_root),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return records


def _required_text(value: object, label: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise BenchmarkContractError(f"{label} 不能为空")
    return text


def _toolchain_provenance(
    options: argparse.Namespace,
) -> tuple[str, dict[str, object]]:
    """兼容旧 Ninja 参数，并允许上层入口记录实际使用的构建工具。"""

    generic = getattr(options, "toolchain", None)
    if generic is None:
        return (
            MANIFEST_SCHEMA_VERSION,
            {
                "compiler": _required_text(options.compiler, "编译器信息"),
                "cmake": _required_text(options.cmake, "CMake 信息"),
                "ninja": _required_text(options.ninja, "Ninja 信息"),
                "openmp_runtime": _required_text(
                    options.openmp_runtime,
                    "OpenMP 运行时信息",
                ),
                "benchmark_build_type": "Release",
            },
        )

    if not isinstance(generic, Mapping):
        raise BenchmarkContractError("工具链信息必须为键值映射")
    build_type = _required_text(generic.get("benchmark_build_type"), "构建类型")
    if build_type != "Release":
        raise BenchmarkContractError("性能实验只接受 Release 构建")
    return (
        GENERIC_TOOLCHAIN_MANIFEST_SCHEMA_VERSION,
        {
            "compiler": _required_text(generic.get("compiler"), "编译器信息"),
            "cmake": _required_text(generic.get("cmake"), "CMake 信息"),
            "cmake_generator": _required_text(
                generic.get("cmake_generator"),
                "CMake 生成器信息",
            ),
            "build_tool": _required_text(generic.get("build_tool"), "构建工具信息"),
            "openmp_runtime": _required_text(
                generic.get("openmp_runtime"),
                "OpenMP 运行时信息",
            ),
            "benchmark_build_type": build_type,
        },
    )


def _emit_progress(
    options: argparse.Namespace,
    completed_count: int,
    total_count: int,
    specification: Mapping[str, int | str],
) -> None:
    stream: TextIO | None = getattr(options, "progress_stream", None)
    if stream is None and getattr(options, "progress", False):
        stream = sys.stderr
    if stream is None:
        return
    sample_kind = "预热" if specification["sample_kind"] == "warmup" else "正式测量"
    print(
        f"[{completed_count}/{total_count}] {sample_kind}第 {specification['round']} 轮，"
        f"线程数 {specification['thread_count']}：完成",
        file=stream,
        flush=True,
    )


def run_benchmark(options: argparse.Namespace) -> int:
    if os.name != "nt":
        raise BenchmarkContractError("该性能实验只支持 Windows")
    if ctypes.sizeof(ctypes.c_size_t) != 8:
        raise BenchmarkContractError("Windows 峰值内存采集要求使用 64 位 Python")
    if options.warmup != WARMUP_COUNT or options.repeat != REPEAT_COUNT:
        raise BenchmarkContractError("性能实验固定使用 W=2、R=7")
    if options.maximum_threads <= 0:
        raise BenchmarkContractError("--maximum-threads 必须为正整数")

    repository_root = options.repository_root.resolve()
    benchmark_executable = options.benchmark_executable.resolve()
    input_path = options.input.resolve()
    output_root = options.out_dir.resolve()
    if output_root.exists():
        raise BenchmarkContractError("输出目录必须不存在，避免覆盖或混入旧样本")

    started_at = _utc_now()
    supplied_source = getattr(options, "source", None)
    supplied_input = getattr(options, "input_facts", None)
    supplied_environment = getattr(options, "environment", None)
    source = (
        dict(supplied_source)
        if isinstance(supplied_source, Mapping)
        else _source_provenance(repository_root)
    )
    input_facts = (
        dict(supplied_input)
        if isinstance(supplied_input, Mapping)
        else _input_provenance(input_path, repository_root)
    )
    environment = (
        dict(supplied_environment)
        if isinstance(supplied_environment, Mapping)
        else _host_environment()
    )
    logical_processors = int(environment["logical_processor_count"])
    if options.maximum_threads != logical_processors:
        raise BenchmarkContractError(
            "--maximum-threads 必须等于当前进程可用逻辑处理器数，"
            f"当前为 {logical_processors}"
        )
    if not benchmark_executable.is_file():
        raise BenchmarkContractError("benchmark 可执行文件不存在")
    manifest_schema_version, toolchain = _toolchain_provenance(options)
    portable_source = source.get("provenance_mode") == "portable-package"
    if portable_source:
        manifest_schema_version = PORTABLE_MANIFEST_SCHEMA_VERSION
    output_root.mkdir(parents=True)

    schedule = build_schedule(
        options.maximum_threads,
        options.warmup,
        options.repeat,
    )
    manifest: dict[str, object] = {
        "schema_version": manifest_schema_version,
        "status": "RUNNING",
        "issue": int(getattr(options, "issue", 54)),
        "source": source,
        "environment": environment,
        "toolchain": toolchain,
        "input": input_facts,
        "configuration": {
            "maximum_threads": options.maximum_threads,
            "maximum_threads_basis": (
                "available logical processor count; every requested team is verified"
            ),
            "thread_counts": list(range(1, options.maximum_threads + 1)),
            "warmup_count": options.warmup,
            "repeat_count": options.repeat,
            "sample_process_model": "one_fresh_child_process_per_sample",
            "samples_are_serialized": True,
            "schedule": schedule,
            "child_environment": {
                "OMP_DYNAMIC": "false",
                "OMP_NUM_THREADS": "<thread_count>",
                "OMP_THREAD_LIMIT": "<thread_count>",
            },
        },
        "samples": [],
        "artifacts": [],
        "started_at_utc": _utc_text(started_at),
        "ended_at_utc": None,
        "failure": None,
    }
    if portable_source:
        manifest["formal_evidence"] = False
        manifest["evidence_notice"] = (
            "portable reproduction; not the repository-bound Windows formal evidence schema"
        )
    source_tools = getattr(options, "source_tools", None)
    if source_tools is not None:
        if not isinstance(source_tools, Mapping):
            raise BenchmarkContractError("来源工具信息必须为键值映射")
        manifest["source_tools"] = {
            str(name): _required_text(value, f"来源工具 {name}")
            for name, value in source_tools.items()
        }
        if not manifest["source_tools"]:
            raise BenchmarkContractError("来源工具信息不能为空")
    manifest_path = output_root / "run_manifest.json"
    process_csv_path = output_root / "benchmark_samples.csv"
    _atomic_write_text(manifest_path, _canonical_json(manifest))

    records: list[dict[str, object]] = []
    try:
        for completed_count, specification in enumerate(schedule, start=1):
            record = _run_one_sample(
                benchmark_executable,
                input_path,
                output_root,
                specification,
            )
            records.append(record)
            _write_process_csv(process_csv_path, records)
            manifest_samples: list[dict[str, object]] = []
            for item in records:
                sample_record = {
                    "sample_id": item["sample_id"],
                    "sample_kind": item["sample_kind"],
                    "round": item["round"],
                    "order_position": item["order_position"],
                    "thread_count": item["thread_count"],
                    "pid": item["pid"],
                    "started_at_utc": item["started_at_utc"],
                    "ended_at_utc": item["ended_at_utc"],
                    "exit_code": item["exit_code"],
                    "symbolic_team_size_observed": item[
                        "symbolic_team_size_observed"
                    ],
                    "numeric_team_size_observed": item[
                        "numeric_team_size_observed"
                    ],
                    "raw_csv_path": item["raw_csv_path"],
                    "raw_json_path": item["raw_json_path"],
                }
                sample_record["peak_working_set_bytes"] = item[
                    "peak_working_set_bytes"
                ]
                manifest_samples.append(sample_record)
            manifest["samples"] = manifest_samples
            _atomic_write_text(manifest_path, _canonical_json(manifest))
            _emit_progress(
                options,
                completed_count,
                len(schedule),
                specification,
            )

        summary = summarize_records(
            records,
            options.maximum_threads,
            options.warmup,
            options.repeat,
        )
        first_summary_path = output_root / str(records[0]["raw_json_path"])
        first_summary = json.loads(first_summary_path.read_text(encoding="utf-8"))
        summary["case_sizes"] = first_summary["case_sizes"]
        summary["input"] = input_facts
        summary_path = output_root / "benchmark_summary.json"
        _atomic_write_text(summary_path, _canonical_json(summary))
        manifest["status"] = "PASS"
        manifest["ended_at_utc"] = _utc_text(_utc_now())
        manifest["summary_status"] = summary["status"]
        manifest["artifacts"] = _artifact_records(output_root)
        _atomic_write_text(manifest_path, _canonical_json(manifest))
    except (Exception, KeyboardInterrupt) as error:
        manifest["status"] = "FAIL"
        manifest["ended_at_utc"] = _utc_text(_utc_now())
        manifest["failure"] = f"{type(error).__name__}: {error}"
        manifest["artifacts"] = _artifact_records(output_root)
        _atomic_write_text(manifest_path, _canonical_json(manifest))
        raise

    result_stream: TextIO | None = getattr(options, "result_stream", sys.stdout)
    if result_stream is not None:
        print(
            _canonical_json(
                {
                    "status": "PASS",
                    "manifest": str(manifest_path),
                    "samples_csv": str(process_csv_path),
                    "summary_json": str(summary_path),
                    "sample_count": len(records),
                }
            ),
            end="",
            file=result_stream,
        )
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--benchmark-executable", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--maximum-threads", type=int, required=True)
    parser.add_argument("--warmup", type=int, default=WARMUP_COUNT)
    parser.add_argument("--repeat", type=int, default=REPEAT_COUNT)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--cmake", required=True)
    parser.add_argument("--ninja", required=True)
    parser.add_argument("--openmp-runtime", required=True)
    parser.add_argument(
        "--progress",
        action="store_true",
        help="逐个显示已完成的独立进程样本",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    parsed_arguments = list(sys.argv[1:] if arguments is None else arguments)
    if not parsed_arguments:
        print(
            "error: 这是维护者使用的底层脚本。普通用户请在 build 目录运行 "
            r"powershell -NoProfile -ExecutionPolicy Bypass -File "
            r"..\examples\run_windhub.ps1",
            file=sys.stderr,
        )
        return 2
    try:
        options = build_argument_parser().parse_args(parsed_arguments)
        return run_benchmark(options)
    except (BenchmarkContractError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
