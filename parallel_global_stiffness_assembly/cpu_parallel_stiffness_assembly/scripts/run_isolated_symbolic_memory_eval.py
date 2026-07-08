#!/usr/bin/env python3
"""Run symbolic evaluation modes one process at a time and attach peak RSS."""
from __future__ import annotations

import argparse
import ctypes
import csv
import json
import os
import platform
import shlex
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

if sys.platform != "win32":
    import resource


RSS_PREFIX = "PGSA_ISOLATED_RSS_JSON="
DEFAULT_MODES = "symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel"
PREFERRED_FIELDS = [
    "evaluation_schema_version",
    "metric_contract",
    "case_name",
    "mesh",
    "element_type",
    "stiffness_model",
    "kernel",
    "nodes",
    "elements",
    "dofs",
    "repeat_index",
    "run_status",
    "run_error",
    "mode",
    "numeric_backend",
    "threads",
    "strategy_label",
    "assemblies_per_symbolic",
    "symbolic_builds",
    "symbolic_csr_ms",
    "symbolic_plan_ms",
    "symbolic_total_ms",
    "symbolic_temporary_bytes",
    "backend_prepare_ms",
    "assembly_numeric_ms",
    "legacy_numeric_ms_without_prepare",
    "numeric_ms",
    "direct_generate_ms",
    "direct_bucket_merge_ms",
    "direct_sort_reduce_ms",
    "amortized_total_ms",
    "symbolic_gain_vs_direct",
    "serial_direct_baseline_ms",
    "speedup_vs_serial_direct",
    "rel_l2",
    "max_abs",
    "matrix_correctness_status",
    "matrix_correctness_reference_strategy",
    "csr_bytes",
    "plan_bytes",
    "symbolic_persistent_bytes",
    "common_output_matrix_bytes",
    "numeric_backend_extra_bytes",
    "direct_transient_bytes",
    "estimated_peak_bytes",
    "delta_vs_serial_symbolic_serial_numeric_bytes",
    "delta_vs_serial_direct_bytes",
    "isolated_peak_rss_mb",
    "isolated_memory_metric",
    "isolated_memory_measurement_source",
    "isolated_peak_working_set_mb",
    "isolated_peak_private_bytes_mb",
    "memory_reference_strategy",
    "time_scope",
    "speedup_baseline_strategy",
    "platform",
    "cpu_model",
    "physical_cores",
    "logical_cores",
]


def _bytes_to_mb(value: int) -> float:
    return float(value) / (1024.0 * 1024.0)


def peak_rss_measurement() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    if sys.platform == "darwin":
        peak_mb = float(usage.ru_maxrss) / (1024.0 * 1024.0)
    else:
        peak_mb = float(usage.ru_maxrss) / 1024.0
    return {
        "peak_rss_mb": peak_mb,
        "memory_metric": "process_ru_maxrss",
        "measurement_source": "resource.getrusage(RUSAGE_CHILDREN).ru_maxrss",
        "peak_working_set_mb": "",
        "peak_private_bytes_mb": "",
    }


if sys.platform == "win32":
    DWORD = ctypes.c_ulong
    SIZE_T = ctypes.c_size_t

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", DWORD),
            ("PageFaultCount", DWORD),
            ("PeakWorkingSetSize", SIZE_T),
            ("WorkingSetSize", SIZE_T),
            ("QuotaPeakPagedPoolUsage", SIZE_T),
            ("QuotaPagedPoolUsage", SIZE_T),
            ("QuotaPeakNonPagedPoolUsage", SIZE_T),
            ("QuotaNonPagedPoolUsage", SIZE_T),
            ("PagefileUsage", SIZE_T),
            ("PeakPagefileUsage", SIZE_T),
            ("PrivateUsage", SIZE_T),
        ]

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    kernel32.OpenProcess.argtypes = [DWORD, ctypes.c_int, DWORD]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
        DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int


def _open_windows_process(pid: int) -> int:
    for access in (
        PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ,
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
    ):
        handle = kernel32.OpenProcess(access, 0, pid)
        if handle:
            return int(handle)
    raise ctypes.WinError(ctypes.get_last_error())


def _query_windows_process_memory(handle: int) -> dict[str, float]:
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "working_set_mb": _bytes_to_mb(int(counters.WorkingSetSize)),
        "peak_working_set_mb": _bytes_to_mb(int(counters.PeakWorkingSetSize)),
        "private_bytes_mb": _bytes_to_mb(int(counters.PrivateUsage)),
        "peak_private_bytes_mb": _bytes_to_mb(int(counters.PeakPagefileUsage)),
    }


def run_windows_measured_command(command: list[str]) -> tuple[int, dict[str, Any]]:
    process = subprocess.Popen(command)
    handle = _open_windows_process(process.pid)
    peak_working_set_mb = 0.0
    peak_private_bytes_mb = 0.0
    try:
        while True:
            memory = _query_windows_process_memory(handle)
            peak_working_set_mb = max(
                peak_working_set_mb,
                memory["peak_working_set_mb"],
                memory["working_set_mb"],
            )
            peak_private_bytes_mb = max(
                peak_private_bytes_mb,
                memory["peak_private_bytes_mb"],
                memory["private_bytes_mb"],
            )
            if process.poll() is not None:
                break
            time.sleep(0.02)
    finally:
        kernel32.CloseHandle(handle)
    return process.returncode, {
        "peak_rss_mb": peak_working_set_mb,
        "memory_metric": "windows_peak_working_set",
        "measurement_source": "GetProcessMemoryInfo.PeakWorkingSetSize",
        "peak_working_set_mb": peak_working_set_mb,
        "peak_private_bytes_mb": peak_private_bytes_mb,
    }


def run_measure_child(command: list[str]) -> int:
    if sys.platform == "win32":
        returncode, payload = run_windows_measured_command(command)
    else:
        completed = subprocess.run(command)
        returncode = completed.returncode
        payload = peak_rss_measurement()
    print(RSS_PREFIX + json.dumps(payload, sort_keys=True))
    return returncode


def measure_command(command: list[str]) -> dict[str, Any]:
    wrapper = [sys.executable, str(Path(__file__).resolve()), "--measure-child", *command]
    completed = subprocess.run(wrapper, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(RSS_PREFIX):
            payload = json.loads(line[len(RSS_PREFIX):])
            payload["peak_rss_mb"] = float(payload["peak_rss_mb"])
            return payload
    raise RuntimeError("measured command did not emit peak RSS metadata")


def split_csv(text: str) -> list[str]:
    return [token for token in text.split(",") if token]


def backend_name(token: str) -> str:
    return token if token.startswith("cpu_") else f"cpu_{token}"


def strategy_label(mode: str, backend: str) -> str:
    if mode == "symbolic_reuse_serial":
        return "serial_symbolic_serial_numeric"
    if mode == "symbolic_rebuild_serial":
        return "serial_symbolic_rebuild_numeric"
    if mode == "direct_no_symbolic_serial":
        return "serial_direct_no_symbolic"
    if mode == "direct_no_symbolic_parallel":
        return "parallel_direct_no_symbolic"
    if mode == "serial_symbolic_parallel_numeric":
        return "serial_symbolic_parallel_numeric"
    if mode == "parallel_symbolic_reuse":
        return "parallel_symbolic_parallel_numeric"
    return f"{mode}_{backend}"


def parse_threads(args: argparse.Namespace) -> list[int]:
    if args.threads_list:
        return [int(token) for token in split_csv(args.threads_list)]
    parts = args.threads_range.split(":")
    if len(parts) not in {2, 3}:
        raise ValueError("--threads-range must be start:end[:step]")
    start = int(parts[0])
    end = int(parts[1])
    step = int(parts[2]) if len(parts) == 3 else 1
    if start <= 0 or end < start or step <= 0:
        raise ValueError("--threads-range values are invalid")
    return list(range(start, end + 1, step))


def symbolic_args(args: argparse.Namespace, csv_path: Path, json_path: Path, md_path: Path) -> list[str]:
    cmd = [
        str(args.symbolic_exe),
        "--mesh",
        args.mesh,
        "--stiffness-model",
        args.stiffness_model,
        "--max-memory-gb",
        str(args.max_memory_gb),
        "--csv",
        str(csv_path),
        "--json",
        str(json_path),
        "--summary-md",
        str(md_path),
    ]
    if args.case_name:
        cmd.extend(["--case-name", args.case_name])
    if args.mesh == "inp":
        cmd.extend(["--inp", args.inp])
    else:
        cmd.extend(["--element", args.element, "--nx", str(args.nx), "--ny", str(args.ny), "--nz", str(args.nz)])
    return cmd


def run_one(args: argparse.Namespace,
            tmp_root: Path,
            label: str,
            mode: str,
            assemblies: int,
            threads: int,
            backend: str,
            repeat_index: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    run_dir = tmp_root / label
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "row.csv"
    json_path = run_dir / "row.json"
    md_path = run_dir / "row.md"
    cmd = symbolic_args(args, csv_path, json_path, md_path)
    cmd.extend([
        "--assemblies-list",
        str(assemblies),
        "--threads-list",
        str(threads),
        "--backend-list",
        backend,
        "--mode-list",
        mode,
    ])
    measurement = measure_command(cmd)
    rss = float(measurement["peak_rss_mb"])
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    for row in rows:
        row["repeat_index"] = str(repeat_index)
        row["run_status"] = "PASS"
        row["run_error"] = ""
        row["isolated_peak_rss_mb"] = f"{rss:.6f}"
        row["isolated_memory_metric"] = str(measurement.get("memory_metric", ""))
        row["isolated_memory_measurement_source"] = str(measurement.get("measurement_source", ""))
        if measurement.get("peak_working_set_mb") != "":
            row["isolated_peak_working_set_mb"] = f"{float(measurement['peak_working_set_mb']):.6f}"
        if measurement.get("peak_private_bytes_mb") != "":
            row["isolated_peak_private_bytes_mb"] = f"{float(measurement['peak_private_bytes_mb']):.6f}"
    return rows, {
        "label": label,
        "mode": mode,
        "assemblies": assemblies,
        "threads": threads,
        "backend": backend,
        "repeat_index": repeat_index,
        "peak_rss_mb": rss,
        "memory_metric": measurement.get("memory_metric", ""),
        "measurement_source": measurement.get("measurement_source", ""),
        "peak_working_set_mb": measurement.get("peak_working_set_mb", ""),
        "peak_private_bytes_mb": measurement.get("peak_private_bytes_mb", ""),
        "command": cmd,
    }


def failure_row(args: argparse.Namespace,
                label: str,
                mode: str,
                assemblies: int,
                threads: int,
                backend: str,
                repeat_index: int,
                error: BaseException) -> dict[str, str]:
    return {
        "evaluation_schema_version": "isolated-runner-failure-v1",
        "case_name": args.case_name,
        "mesh": args.mesh,
        "element_type": args.element if args.mesh != "inp" else "",
        "stiffness_model": args.stiffness_model,
        "repeat_index": str(repeat_index),
        "run_status": "FAIL",
        "run_error": f"{type(error).__name__}: {error}",
        "mode": mode,
        "numeric_backend": backend_name(backend),
        "threads": str(threads),
        "strategy_label": strategy_label(mode, backend),
        "assemblies_per_symbolic": str(assemblies),
        "matrix_correctness_status": "FAIL",
        "isolated_memory_metric": "",
        "isolated_memory_measurement_source": "",
        "isolated_peak_rss_mb": "",
        "isolated_peak_working_set_mb": "",
        "isolated_peak_private_bytes_mb": "",
    }


def recompute_deltas(rows: list[dict[str, str]]) -> None:
    symbolic_baselines: dict[str, int] = {}
    direct_baselines: dict[str, int] = {}
    for row in rows:
        if row.get("run_status", "PASS") != "PASS":
            continue
        if row.get("strategy_label") == "serial_symbolic_serial_numeric":
            assemblies = row.get("assemblies_per_symbolic", "1")
            symbolic_baselines[assemblies] = int(float(row.get("estimated_peak_bytes", "0") or 0))
        if row.get("mode") == "direct_no_symbolic_serial":
            assemblies = row.get("assemblies_per_symbolic", "1")
            direct_baselines[assemblies] = int(float(row.get("estimated_peak_bytes", "0") or 0))
    for row in rows:
        if row.get("run_status", "PASS") != "PASS":
            row["delta_vs_serial_symbolic_serial_numeric_bytes"] = ""
            row["delta_vs_serial_direct_bytes"] = ""
            continue
        assemblies = row.get("assemblies_per_symbolic", "1")
        symbolic_baseline = symbolic_baselines.get(assemblies)
        if symbolic_baseline is None:
            row["delta_vs_serial_symbolic_serial_numeric_bytes"] = "0"
        else:
            current = int(float(row.get("estimated_peak_bytes", "0") or 0))
            row["delta_vs_serial_symbolic_serial_numeric_bytes"] = str(current - symbolic_baseline)
        direct_baseline = direct_baselines.get(assemblies)
        if direct_baseline is None:
            row["delta_vs_serial_direct_bytes"] = "0"
        else:
            current = int(float(row.get("estimated_peak_bytes", "0") or 0))
            row["delta_vs_serial_direct_bytes"] = str(current - direct_baseline)


def write_combined_csv(rows: list[dict[str, str]], path: Path) -> None:
    fields = list(PREFERRED_FIELDS)
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def group_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row.get("mode", ""),
        row.get("numeric_backend", ""),
        row.get("threads", ""),
        row.get("assemblies_per_symbolic", ""),
        row.get("strategy_label", ""),
    )


def parse_number(value: str) -> float | None:
    try:
        if value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.12g}"


def normalize_timing_fields(row: dict[str, str]) -> None:
    backend_prepare = parse_number(row.get("backend_prepare_ms", ""))
    assembly_numeric = parse_number(row.get("assembly_numeric_ms", ""))
    symbolic_total = parse_number(row.get("symbolic_total_ms", ""))
    assemblies = parse_number(row.get("assemblies_per_symbolic", ""))
    if backend_prepare is not None and assembly_numeric is not None:
        numeric = backend_prepare + assembly_numeric
        row["numeric_ms"] = format_number(numeric)
        row["legacy_numeric_ms_without_prepare"] = format_number(assembly_numeric)
        if symbolic_total is not None and assemblies not in (None, 0.0):
            row["amortized_total_ms"] = format_number(symbolic_total / assemblies + numeric)


def build_summary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(group_key(row), []).append(row)

    summary_rows: list[dict[str, str]] = []
    for key in sorted(grouped):
        group = grouped[key]
        pass_rows = [row for row in group if row.get("run_status", "PASS") == "PASS"]
        base = dict(pass_rows[0] if pass_rows else group[0])
        base["repeat_index"] = ""
        base["repeat_count"] = str(len(group))
        base["pass_count"] = str(len(pass_rows))
        base["fail_count"] = str(len(group) - len(pass_rows))
        if not pass_rows:
            base["run_status"] = "FAIL"
        elif len(pass_rows) == len(group):
            base["run_status"] = "PASS"
        else:
            base["run_status"] = "PARTIAL"
        fail_errors = sorted({row.get("run_error", "") for row in group if row.get("run_error")})
        base["run_error"] = "; ".join(fail_errors)

        for field in sorted({field for row in pass_rows for field in row}):
            if field in {"repeat_index", "run_status", "run_error"}:
                continue
            values = [parse_number(row.get(field, "")) for row in pass_rows]
            numeric_values = [value for value in values if value is not None]
            if numeric_values and len(numeric_values) == len(pass_rows):
                median = statistics.median(numeric_values)
                base[field] = format_number(median)
        normalize_timing_fields(base)
        summary_rows.append(base)
    return summary_rows


def write_run_commands(commands: list[dict[str, Any]], path: Path) -> None:
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    for command in commands:
        quoted = " ".join(shlex.quote(str(token)) for token in command["command"])
        lines.append(f"# {command['label']}")
        lines.append(quoted)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o755)


def write_platform_info(path: Path) -> None:
    lines = [
        "# Isolated symbolic memory runner platform",
        f"python={sys.version.split()[0]}",
        f"python_executable={sys.executable}",
        f"platform={platform.platform()}",
        f"machine={platform.machine()}",
        f"processor={platform.processor()}",
        f"omp_dynamic={os.environ.get('OMP_DYNAMIC', '')}",
        f"omp_proc_bind={os.environ.get('OMP_PROC_BIND', '')}",
        f"omp_places={os.environ.get('OMP_PLACES', '')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown(rows: list[dict[str, str]], commands: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# Isolated Symbolic Memory Evaluation",
        "",
        "Each row was measured in a fresh subprocess. On POSIX, `isolated_peak_rss_mb` is `ru_maxrss`; on Windows, it is the OS-observed peak working set fallback and `isolated_memory_metric` records that distinction.",
        "The legacy report label `isolated peak RSS` is retained for schema continuity, but Windows rows must be read with the metric field.",
        "`numeric_ms = backend_prepare_ms + assembly_numeric_ms`; `legacy_numeric_ms_without_prepare` is retained only to explain older plots.",
        "When `--repeat-count` is greater than 1, `isolated_symbolic_memory.csv` keeps all raw repeats and `isolated_symbolic_memory_summary.csv` stores median rows.",
        "",
        "## Rows",
        "",
        "| strategy | mode | backend | threads | repeat | status | assemblies | total ms | numeric ms | isolated peak MB | metric |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        peak = row.get("isolated_peak_rss_mb", "")
        peak_text = f"{float(peak or 0.0):.3f}" if peak else ""
        lines.append(
            f"| `{row.get('strategy_label', '')}` | `{row.get('mode', '')}` | "
            f"`{row.get('numeric_backend', '')}` | {row.get('threads', '')} | "
            f"{row.get('repeat_index', '')} | {row.get('run_status', '')} | "
            f"{row.get('assemblies_per_symbolic', '')} | {row.get('amortized_total_ms', '')} | "
            f"{row.get('numeric_ms', '')} | {peak_text} | "
            f"`{row.get('isolated_memory_metric', '')}` |"
        )
    lines.extend(["", "## Commands", ""])
    for command in commands:
        lines.append(
            f"- `{command['label']}`: peak `{command['peak_rss_mb']:.3f}` MB "
            f"via `{command.get('memory_metric', '')}`"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--measure-child":
        return run_measure_child(argv[1:])

    parser = argparse.ArgumentParser()
    parser.add_argument("--symbolic-exe", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--mesh", default="inp", choices=["cube", "inp"])
    parser.add_argument("--inp", default="../../examples/3d-WindTurbineHub.inp")
    parser.add_argument("--case-name", default="")
    parser.add_argument("--element", default="tet4")
    parser.add_argument("--nx", type=int, default=8)
    parser.add_argument("--ny", type=int, default=8)
    parser.add_argument("--nz", type=int, default=8)
    parser.add_argument("--stiffness-model", dest="stiffness_model", default="linear_elastic_solid")
    parser.add_argument("--kernel", dest="stiffness_model", help="deprecated alias for --stiffness-model")
    parser.add_argument("--assemblies-list", default="1")
    parser.add_argument("--threads-list", default="")
    parser.add_argument("--threads-range", default="1:1")
    parser.add_argument("--backend-list", default="atomic,private_csr,lock_guard")
    parser.add_argument("--mode-list", default=DEFAULT_MODES)
    parser.add_argument("--max-memory-gb", type=float, default=8.0)
    parser.add_argument("--repeat-count", type=int, default=1)
    args = parser.parse_args(argv)

    if args.repeat_count <= 0:
        raise ValueError("--repeat-count must be positive")
    args.out_root.mkdir(parents=True, exist_ok=True)
    assemblies_values = [int(token) for token in split_csv(args.assemblies_list)]
    threads_values = parse_threads(args)
    backends = split_csv(args.backend_list)
    modes = set(split_csv(args.mode_list))

    all_rows: list[dict[str, str]] = []
    commands: list[dict[str, Any]] = []
    # Keep per-command scratch paths short on Windows, where long paths may be disabled.
    with tempfile.TemporaryDirectory(prefix="pgsa-iso-") as tmp:
        tmp_root = Path(tmp)
        for assemblies in assemblies_values:
            for mode in ("symbolic_reuse_serial", "symbolic_rebuild_serial", "direct_no_symbolic_serial"):
                if mode not in modes:
                    continue
                for repeat_index in range(1, args.repeat_count + 1):
                    label = f"{mode}-a{assemblies}-r{repeat_index}"
                    try:
                        rows, command = run_one(
                            args,
                            tmp_root,
                            label,
                            mode,
                            assemblies,
                            1,
                            backends[0],
                            repeat_index,
                        )
                    except Exception as exc:
                        all_rows.append(failure_row(args, label, mode, assemblies, 1, backends[0], repeat_index, exc))
                        continue
                    all_rows.extend(rows)
                    commands.append(command)

            for threads in threads_values:
                if "direct_no_symbolic_parallel" in modes:
                    for repeat_index in range(1, args.repeat_count + 1):
                        label = f"direct-parallel-a{assemblies}-t{threads}-r{repeat_index}"
                        try:
                            rows, command = run_one(
                                args,
                                tmp_root,
                                label,
                                "direct_no_symbolic_parallel",
                                assemblies,
                                threads,
                                backends[0],
                                repeat_index,
                            )
                        except Exception as exc:
                            all_rows.append(
                                failure_row(
                                    args,
                                    label,
                                    "direct_no_symbolic_parallel",
                                    assemblies,
                                    threads,
                                    backends[0],
                                    repeat_index,
                                    exc,
                                )
                            )
                            continue
                        all_rows.extend(rows)
                        commands.append(command)
                for backend in backends:
                    for mode in ("serial_symbolic_parallel_numeric", "parallel_symbolic_reuse"):
                        if mode not in modes:
                            continue
                        for repeat_index in range(1, args.repeat_count + 1):
                            label = f"{mode}-a{assemblies}-t{threads}-{backend}-r{repeat_index}"
                            try:
                                rows, command = run_one(
                                    args,
                                    tmp_root,
                                    label,
                                    mode,
                                    assemblies,
                                    threads,
                                    backend,
                                    repeat_index,
                                )
                            except Exception as exc:
                                all_rows.append(
                                    failure_row(
                                        args,
                                        label,
                                        mode,
                                        assemblies,
                                        threads,
                                        backend,
                                        repeat_index,
                                        exc,
                                    )
                                )
                                continue
                            all_rows.extend(rows)
                            commands.append(command)

    recompute_deltas(all_rows)
    write_combined_csv(all_rows, args.out_root / "isolated_symbolic_memory.csv")
    summary_rows = build_summary_rows(all_rows)
    recompute_deltas(summary_rows)
    write_combined_csv(summary_rows, args.out_root / "isolated_symbolic_memory_summary.csv")
    (args.out_root / "isolated_symbolic_memory.json").write_text(
        json.dumps(
            {"records": all_rows, "summary_records": summary_rows, "commands": commands},
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    write_run_commands(commands, args.out_root / "run_commands.sh")
    write_platform_info(args.out_root / "platform_info.txt")
    write_markdown(all_rows, commands, args.out_root / "isolated_symbolic_memory.md")
    print(f"[OK] isolated symbolic memory output: {args.out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
