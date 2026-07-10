#!/usr/bin/env python3
"""Run backend thread sweep with one fresh process per algorithm/thread repeat."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from process_memory import run_child_with_memory, write_captured_text

RSS_PREFIX = "PGSA_ISOLATED_RSS_JSON="
RUNNABLE_ALGORITHMS = {
    "serial": "cpu_serial",
    "cpu_serial": "cpu_serial",
    "atomic": "cpu_atomic",
    "cpu_atomic": "cpu_atomic",
    "private_csr": "cpu_private_csr",
    "cpu_private_csr": "cpu_private_csr",
    "lock_guard": "cpu_lock_guard",
    "cpu_lock_guard": "cpu_lock_guard",
    "coloring": "cpu_graph_coloring",
    "graph_coloring": "cpu_graph_coloring",
    "cpu_graph_coloring": "cpu_graph_coloring",
    "row_owner": "cpu_row_owner",
    "cpu_row_owner": "cpu_row_owner",
}
CLI_ALGORITHM = {
    "cpu_serial": "serial",
    "cpu_atomic": "atomic",
    "cpu_private_csr": "private_csr",
    "cpu_lock_guard": "lock_guard",
    "cpu_graph_coloring": "coloring",
    "cpu_row_owner": "row_owner",
}
REPEAT_FILENAME = "windhub_backend_thread_sweep_intel_isolated_repeats.csv"
SUMMARY_FILENAME = "windhub_backend_thread_sweep_intel_isolated_summary.csv"
JSON_FILENAME = "windhub_backend_thread_sweep_intel_isolated.json"
MD_FILENAME = "windhub_backend_thread_sweep_intel_isolated.md"


def split_csv(text: str) -> list[str]:
    return [token.strip() for token in text.split(",") if token.strip()]


def canonical_algorithms(text: str) -> list[str]:
    out: list[str] = []
    for token in split_csv(text):
        key = token.lower().replace("-", "_")
        if key in {"coo", "coo_sort", "coo_sort_reduce", "cpu_coo_sort_reduce"}:
            raise ValueError("cpu_coo_sort_reduce is intentionally excluded from this isolated backend sweep")
        try:
            canonical = RUNNABLE_ALGORITHMS[key]
        except KeyError as exc:
            raise ValueError(f"unsupported algorithm for isolated backend sweep: {token}") from exc
        if canonical not in out:
            out.append(canonical)
    if not out:
        raise ValueError("--algorithms cannot be empty")
    return out


def parse_threads(args: argparse.Namespace) -> list[int]:
    if args.threads_list:
        values = [int(token) for token in split_csv(args.threads_list)]
    else:
        parts = args.threads_range.split(":")
        if len(parts) not in {2, 3}:
            raise ValueError("--threads-range must be start:end[:step]")
        start = int(parts[0])
        end = int(parts[1])
        step = int(parts[2]) if len(parts) == 3 else 1
        if start <= 0 or end < start or step <= 0:
            raise ValueError("--threads-range values are invalid")
        values = list(range(start, end + 1, step))
    if any(value <= 0 for value in values):
        raise ValueError("thread counts must be positive")
    return sorted(set(values))


def run_measure_child(command: list[str]) -> int:
    returncode, measurement = run_child_with_memory(command)
    payload = {
        key: measurement[key]
        for key in ("peak_rss_mb", "memory_metric", "measurement_source")
    }
    print(RSS_PREFIX + json.dumps(payload, sort_keys=True))
    return returncode


def measure_command(command: list[str]) -> dict[str, Any]:
    wrapper = [sys.executable, str(Path(__file__).resolve()), "--measure-child", *command]
    completed = subprocess.run(wrapper, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        if completed.stdout:
            write_captured_text(sys.stdout, completed.stdout)
        if completed.stderr:
            write_captured_text(sys.stderr, completed.stderr)
        raise subprocess.CalledProcessError(completed.returncode, command)
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(RSS_PREFIX):
            payload = json.loads(line[len(RSS_PREFIX):])
            payload["peak_rss_mb"] = float(payload["peak_rss_mb"])
            return payload
    raise RuntimeError("measured command did not emit peak RSS metadata")


def base_benchmark_args(args: argparse.Namespace) -> list[str]:
    cmd = [
        str(args.benchmark_exe),
        "--mesh",
        args.mesh,
        "--stiffness-model",
        args.stiffness_model,
    ]
    if args.case_name:
        cmd.extend(["--case-name", args.case_name])
    if args.mesh == "inp":
        cmd.extend(["--inp", args.inp])
    else:
        cmd.extend(["--element", args.element, "--nx", str(args.nx), "--ny", str(args.ny), "--nz", str(args.nz)])
    cmd.extend(["--max-memory-gb", str(args.max_memory_gb)])
    return cmd


def read_single_row(csv_path: Path) -> dict[str, str]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"expected one benchmark row in {csv_path}, got {len(rows)}")
    return dict(rows[0])


def run_isolated_repeat(args: argparse.Namespace,
                        tmp_root: Path,
                        algorithm: str,
                        threads: int,
                        repeat_index: int) -> tuple[dict[str, str], dict[str, Any]]:
    run_dir = tmp_root / f"measure-{algorithm}-t{threads}-r{repeat_index}"
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "row.csv"
    json_path = run_dir / "row.json"
    md_path = run_dir / "row.md"
    cmd = base_benchmark_args(args)
    cmd.extend([
        "--measurement-mode", "isolated",
        "--algo", CLI_ALGORITHM[algorithm],
        "--threads", str(threads),
        "--warmup", str(args.warmup),
        "--repeat", "1",
        "--csv", str(csv_path),
        "--json", str(json_path),
        "--summary-md", str(md_path),
    ])
    measurement = measure_command(cmd)
    row = read_single_row(csv_path)
    row["process_repeat_index"] = str(repeat_index)
    row["isolated_peak_rss_mb"] = f"{float(measurement['peak_rss_mb']):.6f}"
    row["isolated_memory_metric"] = str(measurement.get("memory_metric", ""))
    row["isolated_memory_measurement_source"] = str(measurement.get("measurement_source", ""))
    return row, {"algorithm": algorithm, "threads": threads, "repeat_index": repeat_index, "command": cmd, **measurement}


def run_correctness_check(args: argparse.Namespace,
                          tmp_root: Path,
                          algorithm: str,
                          threads: int) -> dict[str, str]:
    run_dir = tmp_root / f"check-{algorithm}-t{threads}"
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "check.csv"
    cmd = base_benchmark_args(args)
    cmd.extend([
        "--algo", CLI_ALGORITHM[algorithm],
        "--threads", str(threads),
        "--warmup", "0",
        "--repeat", "1",
        "--check",
        "--csv", str(csv_path),
    ])
    subprocess.run(cmd, check=True, text=True, stdout=subprocess.DEVNULL)
    return read_single_row(csv_path)


def fvalues(rows: list[dict[str, str]], field: str) -> list[float]:
    return [float(row[field]) for row in rows]


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def stdev(values: list[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def summarize_measured(algorithm: str,
                       threads: int,
                       rows: list[dict[str, str]],
                       correctness: dict[str, str]) -> dict[str, str]:
    first = rows[0]
    summary = {
        "case_name": first.get("case_name", ""),
        "mesh": first.get("mesh", ""),
        "element_type": first.get("element_type", ""),
        "stiffness_model": first.get("stiffness_model", ""),
        "kernel": first.get("kernel", ""),
        "algorithm": algorithm,
        "threads": str(threads),
        "status": correctness.get("status", "UNKNOWN"),
        "skip_reason": correctness.get("skip_reason", ""),
        "repeat_count": str(len(rows)),
        "rel_l2": correctness.get("rel_l2", ""),
        "max_abs": correctness.get("max_abs", ""),
        "measurement_mode": "isolated",
    }
    for field in ("symbolic_ms", "numeric_ms", "symbolic_numeric_total_ms", "isolated_peak_rss_mb"):
        values = fvalues(rows, field)
        summary[f"{field}_mean"] = f"{mean(values):.10g}"
        summary[f"{field}_min"] = f"{min(values):.10g}"
        summary[f"{field}_max"] = f"{max(values):.10g}"
        summary[f"{field}_std"] = f"{stdev(values):.10g}"
    return summary


def skip_summary(args: argparse.Namespace, algorithm: str, threads: int) -> dict[str, str]:
    return {
        "case_name": args.case_name,
        "mesh": args.case_name,
        "element_type": "",
        "stiffness_model": args.stiffness_model,
        "kernel": args.stiffness_model,
        "algorithm": algorithm,
        "threads": str(threads),
        "status": "SKIP",
        "skip_reason": "NOT_APPLICABLE",
        "repeat_count": "0",
        "rel_l2": "",
        "max_abs": "",
        "measurement_mode": "isolated",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary_rows: list[dict[str, str]]) -> None:
    lines = [
        "# Intel isolated backend thread sweep raw summary",
        "",
        "Each PASS row summarizes independent subprocess measurements for one algorithm/thread combination.",
        "`symbolic_numeric_total_ms` is defined as `symbolic_ms + numeric_ms`; RSS comes from the isolated measurement subprocess.",
        "",
        "| algorithm | threads | status | repeats | symbolic mean ms | numeric mean ms | total mean ms | isolated RSS mean MB |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{row.get('algorithm', '')}` | {row.get('threads', '')} | {row.get('status', '')} | "
            f"{row.get('repeat_count', '')} | {row.get('symbolic_ms_mean', '')} | "
            f"{row.get('numeric_ms_mean', '')} | {row.get('symbolic_numeric_total_ms_mean', '')} | "
            f"{row.get('isolated_peak_rss_mb_mean', '')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_repeat_row(row: dict[str, str]) -> None:
    symbolic = float(row["symbolic_ms"])
    numeric = float(row["numeric_ms"])
    total = float(row["symbolic_numeric_total_ms"])
    if not math.isfinite(symbolic + numeric + total):
        raise ValueError("non-finite timing value")
    if abs((symbolic + numeric) - total) > 1.0e-6:
        raise ValueError(f"symbolic+numeric total mismatch for {row.get('algorithm')} t{row.get('threads')}")
    if float(row["isolated_peak_rss_mb"]) <= 0.0:
        raise ValueError("isolated_peak_rss_mb must be positive")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--measure-child":
        return run_measure_child(argv[1:])

    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-exe", required=True, type=Path)
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
    parser.add_argument("--algorithms", default="serial,atomic,private_csr,lock_guard,coloring,row_owner")
    parser.add_argument("--threads-list", default="")
    parser.add_argument("--threads-range", default="1:20")
    parser.add_argument("--process-repeat", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--max-memory-gb", type=float, default=8.0)
    args = parser.parse_args(argv)

    if args.process_repeat <= 0:
        raise ValueError("--process-repeat must be positive")
    args.out_root.mkdir(parents=True, exist_ok=True)
    algorithms = canonical_algorithms(args.algorithms)
    threads = parse_threads(args)

    repeat_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    commands: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="pgsa-backend-iso-") as tmp:
        tmp_root = Path(tmp)
        for algorithm in algorithms:
            for thread_count in threads:
                if algorithm == "cpu_serial" and thread_count != 1:
                    summary_rows.append(skip_summary(args, algorithm, thread_count))
                    continue
                combo_rows: list[dict[str, str]] = []
                for repeat_index in range(1, args.process_repeat + 1):
                    row, command = run_isolated_repeat(args, tmp_root, algorithm, thread_count, repeat_index)
                    validate_repeat_row(row)
                    combo_rows.append(row)
                    repeat_rows.append(row)
                    commands.append(command)
                correctness = run_correctness_check(args, tmp_root, algorithm, thread_count)
                summary_rows.append(summarize_measured(algorithm, thread_count, combo_rows, correctness))

    write_csv(args.out_root / REPEAT_FILENAME, repeat_rows)
    write_csv(args.out_root / SUMMARY_FILENAME, summary_rows)
    (args.out_root / JSON_FILENAME).write_text(
        json.dumps({"repeat_records": repeat_rows, "summary_records": summary_rows, "commands": commands}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_markdown(args.out_root / MD_FILENAME, summary_rows)
    print(f"[OK] isolated backend thread sweep output: {args.out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
