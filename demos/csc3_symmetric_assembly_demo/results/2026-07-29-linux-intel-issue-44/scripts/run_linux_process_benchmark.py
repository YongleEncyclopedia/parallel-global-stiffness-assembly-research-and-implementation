#!/usr/bin/env python3
"""按 Windows Issue #54 口径执行 Linux WindHub 独立进程线程扫描。

该脚本是 Issue #44 的一次性实验适配器。它复用已测试的 Windows runner
调度、子样本校验与统计定义，但用 Linux ``wait4().ru_maxrss`` 采集每个
子进程的峰值常驻集。Linux RSS 与 Windows PeakWorkingSetSize 不作绝对横比。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


SCRIPT_PATH = Path(__file__).resolve()
DEMO_ROOT = SCRIPT_PATH.parents[3]
WINDOWS_RUNNER_PATH = DEMO_ROOT / "scripts" / "run_windows_process_benchmark.py"
SPEC = importlib.util.spec_from_file_location(
    "csc3_windows_process_contract", WINDOWS_RUNNER_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"无法加载 Windows 调度契约：{WINDOWS_RUNNER_PATH}")
WINDOWS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = WINDOWS
SPEC.loader.exec_module(WINDOWS)


SCHEMA_VERSION = "csc3-demo-linux-process-benchmark-v1"
MANIFEST_SCHEMA_VERSION = "csc3-demo-linux-process-manifest-v1"
PEAK_RSS_SOURCE = "wait4.ru_maxrss"
UNBOUND_ENVIRONMENT = (
    "OMP_PROC_BIND",
    "OMP_PLACES",
    "GOMP_CPU_AFFINITY",
    "KMP_AFFINITY",
)
PROCESS_CSV_FIELDS = tuple(WINDOWS.PROCESS_CSV_FIELDS) + (
    "symbolic_pattern_ms",
    "symbolic_scatter_ms",
    "symbolic_residual_ms",
    "numeric_reset_ms",
    "numeric_kernel_ms",
    "numeric_residual_ms",
)


class LinuxProcessBenchmarkError(RuntimeError):
    """表示 Linux 镜像实验违反独立进程证据契约。"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict").strip()


def linux_environment() -> dict[str, object]:
    if platform.system() != "Linux" or not hasattr(os, "sched_getaffinity"):
        raise LinuxProcessBenchmarkError("该适配器只允许在 Linux 上运行")
    affinity = sorted(os.sched_getaffinity(0))
    logical = os.cpu_count()
    if logical is None or affinity != list(range(logical)):
        raise LinuxProcessBenchmarkError(
            "镜像实验要求进程 affinity 覆盖全部连续在线逻辑 CPU"
        )
    physical: set[tuple[int, int]] = set()
    capacities: dict[str, int | None] = {}
    maximum_frequencies_khz: dict[str, int | None] = {}
    for cpu in affinity:
        root = Path(f"/sys/devices/system/cpu/cpu{cpu}")
        package = int(read_text(root / "topology" / "physical_package_id"))
        core = int(read_text(root / "topology" / "core_id"))
        physical.add((package, core))
        capacity_path = root / "cpu_capacity"
        maximum_path = root / "cpufreq" / "cpuinfo_max_freq"
        capacities[str(cpu)] = (
            int(read_text(capacity_path)) if capacity_path.is_file() else None
        )
        maximum_frequencies_khz[str(cpu)] = (
            int(read_text(maximum_path)) if maximum_path.is_file() else None
        )
    cpu_model = "unknown"
    for line in Path("/proc/cpuinfo").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        if line.startswith("model name"):
            cpu_model = line.partition(":")[2].strip()
            break
    memory_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    return {
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "cpu_model": cpu_model,
        "physical_core_count": len(physical),
        "logical_processor_count": logical,
        "affinity_cpu_ids": affinity,
        "cpu_capacity": capacities,
        "cpuinfo_max_freq_khz": maximum_frequencies_khz,
        "total_physical_memory_bytes": memory_bytes,
        "python_version": platform.python_version(),
    }


def write_process_csv(path: Path, records: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=PROCESS_CSV_FIELDS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(records)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def run_one_sample(
    benchmark_executable: Path,
    input_path: Path,
    output_root: Path,
    specification: Mapping[str, int | str],
) -> dict[str, object]:
    sample_id = WINDOWS._sample_id(specification)
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
    for name in UNBOUND_ENVIRONMENT:
        environment.pop(name, None)
    environment.update(
        {
            "OMP_DYNAMIC": "false",
            "OMP_NUM_THREADS": str(thread_count),
            "OMP_THREAD_LIMIT": str(thread_count),
        }
    )
    started_at = utc_now()
    monotonic_start = time.perf_counter()
    with stdout_log.open("wb") as standard_output, stderr_log.open(
        "wb"
    ) as standard_error:
        process = subprocess.Popen(
            command,
            cwd=output_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=standard_output,
            stderr=standard_error,
        )
        waited_pid, wait_status, usage = os.wait4(process.pid, 0)
        if waited_pid != process.pid:
            raise LinuxProcessBenchmarkError("wait4 返回了错误的子进程 PID")
        exit_code = os.waitstatus_to_exitcode(wait_status)
        process.returncode = exit_code
    ended_at = utc_now()
    wall_time_seconds = time.perf_counter() - monotonic_start
    peak_rss_bytes = int(usage.ru_maxrss) * 1024
    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "sample_id": sample_id,
        **specification,
        "pid": process.pid,
        "started_at_utc": utc_text(started_at),
        "ended_at_utc": utc_text(ended_at),
        "wall_time_seconds": wall_time_seconds,
        "exit_code": exit_code,
        "peak_working_set_bytes": peak_rss_bytes,
        "peak_working_set_source": PEAK_RSS_SOURCE,
        "raw_csv_path": WINDOWS._relative_path(raw_csv, output_root),
        "raw_json_path": WINDOWS._relative_path(raw_json, output_root),
        "stdout_log_path": WINDOWS._relative_path(stdout_log, output_root),
        "stderr_log_path": WINDOWS._relative_path(stderr_log, output_root),
    }
    if peak_rss_bytes <= 0:
        raise LinuxProcessBenchmarkError(f"{sample_id} 未取得 Linux 峰值 RSS")
    if exit_code != 0:
        error_text = stderr_log.read_text(
            encoding="utf-8", errors="replace"
        ).strip()
        raise LinuxProcessBenchmarkError(
            f"{sample_id} 子进程退出码为 {exit_code}：{error_text[-1000:]}"
        )
    validated = WINDOWS._validate_child_outputs(raw_csv, raw_json, thread_count)
    record.update(validated)
    record.pop("case_sizes", None)
    row = WINDOWS._one_csv_row(raw_csv)
    pattern = WINDOWS._finite_nonnegative(
        row.get("symbolic_pattern_ms"), "symbolic_pattern_ms"
    )
    scatter = WINDOWS._finite_nonnegative(
        row.get("symbolic_scatter_ms"), "symbolic_scatter_ms"
    )
    reset = WINDOWS._finite_nonnegative(
        row.get("numeric_reset_ms"), "numeric_reset_ms"
    )
    kernel = WINDOWS._finite_nonnegative(
        row.get("numeric_kernel_ms"), "numeric_kernel_ms"
    )
    symbolic_residual = float(record["parallel_symbolic_ms"]) - pattern - scatter
    numeric_residual = float(record["parallel_numeric_ms"]) - reset - kernel
    if min(symbolic_residual, numeric_residual) < -1.0e-6:
        raise LinuxProcessBenchmarkError("阶段分解得到负的未分项时间")
    record.update(
        {
            "symbolic_pattern_ms": pattern,
            "symbolic_scatter_ms": scatter,
            "symbolic_residual_ms": max(0.0, symbolic_residual),
            "numeric_reset_ms": reset,
            "numeric_kernel_ms": kernel,
            "numeric_residual_ms": max(0.0, numeric_residual),
        }
    )
    return record


def run_benchmark(options: argparse.Namespace) -> int:
    if options.warmup != WINDOWS.WARMUP_COUNT or options.repeat != WINDOWS.REPEAT_COUNT:
        raise LinuxProcessBenchmarkError("镜像实验固定要求 W=2、R=7")
    repository_root = options.repository_root.resolve()
    benchmark_executable = options.benchmark_executable.resolve()
    input_path = options.input.resolve()
    output_root = options.out_dir.resolve()
    if output_root.exists():
        raise LinuxProcessBenchmarkError("输出目录必须不存在")
    environment = linux_environment()
    logical_processors = int(environment["logical_processor_count"])
    if options.maximum_threads != logical_processors:
        raise LinuxProcessBenchmarkError(
            "--maximum-threads 必须等于完整 affinity 的逻辑 CPU 数"
        )
    if not benchmark_executable.is_file():
        raise LinuxProcessBenchmarkError("benchmark 可执行文件不存在")
    output_root.mkdir(parents=True)
    started_at = utc_now()
    source = WINDOWS._source_provenance(repository_root)
    input_facts = WINDOWS._input_provenance(input_path, repository_root)
    schedule = WINDOWS.build_schedule(
        options.maximum_threads, options.warmup, options.repeat
    )
    manifest: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "status": "RUNNING",
        "issue": 44,
        "source": source,
        "adapter": {
            "path": str(SCRIPT_PATH),
            "sha256": WINDOWS._sha256_file(SCRIPT_PATH),
            "windows_contract_path": str(WINDOWS_RUNNER_PATH),
            "windows_contract_sha256": WINDOWS._sha256_file(WINDOWS_RUNNER_PATH),
        },
        "environment": environment,
        "toolchain": {
            "compiler": options.compiler,
            "cmake": options.cmake,
            "ninja": options.ninja,
            "openmp_runtime": options.openmp_runtime,
            "benchmark_build_type": "Release",
        },
        "input": input_facts,
        "configuration": {
            "maximum_threads": options.maximum_threads,
            "maximum_threads_basis": "Linux full-host logical CPU count",
            "thread_counts": list(range(1, options.maximum_threads + 1)),
            "warmup_count": options.warmup,
            "repeat_count": options.repeat,
            "sample_process_model": "one_fresh_child_process_per_sample",
            "samples_are_serialized": True,
            "measured_round_order": "alternating_ascending_descending",
            "binding_profile": "windows-mirror-unbound",
            "schedule": schedule,
            "child_environment": {
                "OMP_DYNAMIC": "false",
                "OMP_NUM_THREADS": "<thread_count>",
                "OMP_THREAD_LIMIT": "<thread_count>",
                "cleared": list(UNBOUND_ENVIRONMENT),
            },
        },
        "samples": [],
        "artifacts": [],
        "started_at_utc": utc_text(started_at),
        "ended_at_utc": None,
        "failure": None,
    }
    manifest_path = output_root / "run_manifest.json"
    process_csv_path = output_root / "benchmark_samples.csv"
    WINDOWS._atomic_write_text(manifest_path, WINDOWS._canonical_json(manifest))
    records: list[dict[str, object]] = []
    try:
        for index, specification in enumerate(schedule, start=1):
            record = run_one_sample(
                benchmark_executable, input_path, output_root, specification
            )
            records.append(record)
            write_process_csv(process_csv_path, records)
            manifest["samples"] = [
                {
                    key: item[key]
                    for key in (
                        "sample_id",
                        "sample_kind",
                        "round",
                        "order_position",
                        "thread_count",
                        "pid",
                        "started_at_utc",
                        "ended_at_utc",
                        "exit_code",
                        "peak_working_set_bytes",
                        "symbolic_team_size_observed",
                        "numeric_team_size_observed",
                        "raw_csv_path",
                        "raw_json_path",
                    )
                }
                for item in records
            ]
            WINDOWS._atomic_write_text(
                manifest_path, WINDOWS._canonical_json(manifest)
            )
            print(
                f"completed={index}/{len(schedule)} sample={record['sample_id']} "
                f"wall_seconds={float(record['wall_time_seconds']):.3f}",
                flush=True,
            )
        summary = WINDOWS.summarize_records(
            records, options.maximum_threads, options.warmup, options.repeat
        )
        summary["schema_version"] = SCHEMA_VERSION
        summary["memory_definition"]["peak_working_set"] = PEAK_RSS_SOURCE
        summary["memory_definition"]["peak_working_set_is_os_measured"] = True
        summary["memory_definition"]["cross_platform_comparability"] = (
            "Linux ru_maxrss and Windows PeakWorkingSetSize are not compared absolutely"
        )
        first_summary = json.loads(
            (output_root / str(records[0]["raw_json_path"])).read_text(
                encoding="utf-8"
            )
        )
        summary["case_sizes"] = first_summary["case_sizes"]
        summary["input"] = input_facts
        summary_path = output_root / "benchmark_summary.json"
        WINDOWS._atomic_write_text(summary_path, WINDOWS._canonical_json(summary))
        manifest["status"] = "PASS"
        manifest["ended_at_utc"] = utc_text(utc_now())
        manifest["summary_status"] = summary["status"]
        manifest["artifacts"] = WINDOWS._artifact_records(output_root)
        WINDOWS._atomic_write_text(manifest_path, WINDOWS._canonical_json(manifest))
    except Exception as error:
        manifest["status"] = "FAIL"
        manifest["ended_at_utc"] = utc_text(utc_now())
        manifest["failure"] = f"{type(error).__name__}: {error}"
        manifest["artifacts"] = WINDOWS._artifact_records(output_root)
        WINDOWS._atomic_write_text(manifest_path, WINDOWS._canonical_json(manifest))
        raise
    print(
        WINDOWS._canonical_json(
            {
                "status": "PASS",
                "manifest": str(manifest_path),
                "samples_csv": str(process_csv_path),
                "summary_json": str(summary_path),
                "sample_count": len(records),
            }
        ),
        end="",
    )
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--benchmark-executable", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--maximum-threads", type=int, required=True)
    parser.add_argument("--warmup", type=int, default=WINDOWS.WARMUP_COUNT)
    parser.add_argument("--repeat", type=int, default=WINDOWS.REPEAT_COUNT)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--cmake", required=True)
    parser.add_argument("--ninja", required=True)
    parser.add_argument("--openmp-runtime", required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        return run_benchmark(build_argument_parser().parse_args(arguments))
    except (
        LinuxProcessBenchmarkError,
        WINDOWS.BenchmarkContractError,
        OSError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
