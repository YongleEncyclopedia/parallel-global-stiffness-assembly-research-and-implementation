#!/usr/bin/env python3
"""Run symbolic evaluation modes one process at a time and attach peak RSS."""
from __future__ import annotations

import argparse
import csv
import json
import resource
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


RSS_PREFIX = "PGSA_ISOLATED_RSS_JSON="
DEFAULT_MODES = "symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel"
PREFERRED_FIELDS = [
    "case_name",
    "mesh",
    "element_type",
    "kernel",
    "nodes",
    "elements",
    "dofs",
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
    "numeric_ms",
    "direct_generate_ms",
    "direct_bucket_merge_ms",
    "direct_sort_reduce_ms",
    "amortized_total_ms",
    "symbolic_gain_vs_direct",
    "rel_l2",
    "max_abs",
    "csr_bytes",
    "plan_bytes",
    "symbolic_persistent_bytes",
    "common_output_matrix_bytes",
    "numeric_backend_extra_bytes",
    "direct_transient_bytes",
    "estimated_peak_bytes",
    "delta_vs_serial_symbolic_serial_numeric_bytes",
    "isolated_peak_rss_mb",
    "platform",
    "cpu_model",
    "physical_cores",
    "logical_cores",
]


def peak_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    if sys.platform == "darwin":
        return float(usage.ru_maxrss) / (1024.0 * 1024.0)
    return float(usage.ru_maxrss) / 1024.0


def run_measure_child(command: list[str]) -> int:
    completed = subprocess.run(command)
    payload = {"peak_rss_mb": peak_rss_mb()}
    print(RSS_PREFIX + json.dumps(payload, sort_keys=True))
    return completed.returncode


def measure_command(command: list[str]) -> float:
    wrapper = [sys.executable, str(Path(__file__).resolve()), "--measure-child", *command]
    completed = subprocess.run(wrapper, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith(RSS_PREFIX):
            return float(json.loads(line[len(RSS_PREFIX):])["peak_rss_mb"])
    raise RuntimeError("measured command did not emit peak RSS metadata")


def split_csv(text: str) -> list[str]:
    return [token for token in text.split(",") if token]


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
        "--kernel",
        args.kernel,
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
            backend: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
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
    rss = measure_command(cmd)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    for row in rows:
        row["isolated_peak_rss_mb"] = f"{rss:.6f}"
    return rows, {"label": label, "mode": mode, "assemblies": assemblies, "threads": threads, "backend": backend, "peak_rss_mb": rss, "command": cmd}


def recompute_deltas(rows: list[dict[str, str]]) -> None:
    baselines: dict[str, int] = {}
    for row in rows:
        if row.get("strategy_label") == "serial_symbolic_serial_numeric":
            assemblies = row.get("assemblies_per_symbolic", "1")
            baselines[assemblies] = int(float(row.get("estimated_peak_bytes", "0") or 0))
    for row in rows:
        assemblies = row.get("assemblies_per_symbolic", "1")
        baseline = baselines.get(assemblies)
        if baseline is None:
            row["delta_vs_serial_symbolic_serial_numeric_bytes"] = "0"
            continue
        current = int(float(row.get("estimated_peak_bytes", "0") or 0))
        row["delta_vs_serial_symbolic_serial_numeric_bytes"] = str(current - baseline)


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


def write_markdown(rows: list[dict[str, str]], commands: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# Isolated Symbolic Memory Evaluation",
        "",
        "Each row was measured in a fresh subprocess. `isolated_peak_rss_mb` is the OS-observed peak RSS for that single command.",
        "",
        "## Rows",
        "",
        "| strategy | mode | backend | threads | assemblies | estimated peak bytes | delta bytes | isolated peak RSS MB |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row.get('strategy_label', '')}` | `{row.get('mode', '')}` | "
            f"`{row.get('numeric_backend', '')}` | {row.get('threads', '')} | "
            f"{row.get('assemblies_per_symbolic', '')} | {row.get('estimated_peak_bytes', '')} | "
            f"{row.get('delta_vs_serial_symbolic_serial_numeric_bytes', '')} | "
            f"{float(row.get('isolated_peak_rss_mb', '0') or 0.0):.3f} |"
        )
    lines.extend(["", "## Commands", ""])
    for command in commands:
        lines.append(f"- `{command['label']}`: peak RSS `{command['peak_rss_mb']:.3f}` MB")
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
    parser.add_argument("--kernel", default="physics_tet4")
    parser.add_argument("--assemblies-list", default="1")
    parser.add_argument("--threads-list", default="")
    parser.add_argument("--threads-range", default="1:1")
    parser.add_argument("--backend-list", default="atomic,private_csr,lock_guard")
    parser.add_argument("--mode-list", default=DEFAULT_MODES)
    parser.add_argument("--max-memory-gb", type=float, default=8.0)
    args = parser.parse_args(argv)

    args.out_root.mkdir(parents=True, exist_ok=True)
    assemblies_values = [int(token) for token in split_csv(args.assemblies_list)]
    threads_values = parse_threads(args)
    backends = split_csv(args.backend_list)
    modes = set(split_csv(args.mode_list))

    all_rows: list[dict[str, str]] = []
    commands: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="isolated-symbolic-", dir=args.out_root) as tmp:
        tmp_root = Path(tmp)
        for assemblies in assemblies_values:
            for mode in ("symbolic_reuse_serial", "symbolic_rebuild_serial", "direct_no_symbolic_serial"):
                if mode not in modes:
                    continue
                rows, command = run_one(args, tmp_root, f"{mode}-a{assemblies}", mode, assemblies, 1, backends[0])
                all_rows.extend(rows)
                commands.append(command)

            for threads in threads_values:
                if "direct_no_symbolic_parallel" in modes:
                    rows, command = run_one(
                        args,
                        tmp_root,
                        f"direct-parallel-a{assemblies}-t{threads}",
                        "direct_no_symbolic_parallel",
                        assemblies,
                        threads,
                        backends[0],
                    )
                    all_rows.extend(rows)
                    commands.append(command)
                for backend in backends:
                    for mode in ("serial_symbolic_parallel_numeric", "parallel_symbolic_reuse"):
                        if mode not in modes:
                            continue
                        rows, command = run_one(
                            args,
                            tmp_root,
                            f"{mode}-a{assemblies}-t{threads}-{backend}",
                            mode,
                            assemblies,
                            threads,
                            backend,
                        )
                        all_rows.extend(rows)
                        commands.append(command)

    recompute_deltas(all_rows)
    write_combined_csv(all_rows, args.out_root / "isolated_symbolic_memory.csv")
    (args.out_root / "isolated_symbolic_memory.json").write_text(
        json.dumps({"records": all_rows, "commands": commands}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_markdown(all_rows, commands, args.out_root / "isolated_symbolic_memory.md")
    print(f"[OK] isolated symbolic memory output: {args.out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
