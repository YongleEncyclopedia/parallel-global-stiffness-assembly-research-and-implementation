#!/usr/bin/env python3
"""Run physical-core and over-physical thread-scaling evaluation."""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


ALGORITHMS = "atomic,private_csr,row_owner,coloring"
BOUND_ENV = {
    "OMP_DYNAMIC": "FALSE",
    "OMP_PROC_BIND": "close",
    "OMP_PLACES": "cores",
}
OMP_KEYS = ("OMP_DYNAMIC", "OMP_PROC_BIND", "OMP_PLACES")


@dataclass
class ScalingRow:
    env_group: str
    algorithm: str
    threads: int
    region: str
    assembly_ms: float
    speedup: float
    efficiency: float
    status: str
    skip_reason: str
    diagnostics: str
    physical_cores: int
    logical_cores: int
    cpu_model: str
    omp_dynamic: str
    omp_proc_bind: str
    omp_places: str
    extra_memory_bytes: float
    rel_l2: float


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def benchmark_exe(build_dir: Path) -> Path:
    exe_name = "benchmark_assembly.exe" if os.name == "nt" else "benchmark_assembly"
    return build_dir / "bin" / exe_name


def parse_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0


def parse_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value not in ("", None) else 0


def load_rows(csv_path: Path, env_group: str) -> list[ScalingRow]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    rows: list[ScalingRow] = []
    for raw in raw_rows:
        rows.append(
            ScalingRow(
                env_group=env_group,
                algorithm=raw["algorithm"],
                threads=parse_int(raw, "threads"),
                region=raw.get("thread_region", ""),
                assembly_ms=parse_float(raw, "assembly_mean_ms") or parse_float(raw, "assembly_ms"),
                speedup=parse_float(raw, "speedup"),
                efficiency=parse_float(raw, "efficiency"),
                status=raw["status"],
                skip_reason=raw.get("skip_reason", ""),
                diagnostics=raw.get("diagnostics", ""),
                physical_cores=parse_int(raw, "physical_cores"),
                logical_cores=parse_int(raw, "logical_cores"),
                cpu_model=raw.get("cpu_model", ""),
                omp_dynamic=raw.get("omp_dynamic", ""),
                omp_proc_bind=raw.get("omp_proc_bind", ""),
                omp_places=raw.get("omp_places", ""),
                extra_memory_bytes=parse_float(raw, "extra_memory_bytes"),
                rel_l2=parse_float(raw, "rel_l2"),
            )
        )
    return rows


def pass_rows(rows: Iterable[ScalingRow]) -> list[ScalingRow]:
    return [row for row in rows if row.status == "PASS" and row.assembly_ms > 0.0]


def best_by_time(rows: Iterable[ScalingRow]) -> ScalingRow | None:
    passed = pass_rows(rows)
    return min(passed, key=lambda row: row.assembly_ms) if passed else None


def classify_change(reference_ms: float, candidate_ms: float) -> str:
    if candidate_ms < reference_ms * 0.95:
        return "继续加速"
    if candidate_ms > reference_ms * 1.05:
        return "变慢"
    return "基本持平"


def bottleneck_note(algorithm: str) -> str:
    notes = {
        "cpu_atomic": "主要瓶颈是共享 CSR value 上的 atomic update、缓存一致性流量和热点写入竞争；线程超过物理核后，同一批写热点会被更多软件线程竞争。",
        "cpu_private_csr": "主要瓶颈是每线程一份 CSR values 带来的内存容量、清零和 reduction 成本；线程越多，额外内存和归并带宽压力越明显。",
        "cpu_row_owner": "主要瓶颈是 owner 划分后的负载均衡、任务列表内存，以及跨 owner 单元重复计算局部刚度矩阵；超过物理核后重复计算更难换来真实执行资源。",
        "cpu_graph_coloring": "主要瓶颈是颜色组之间的串行屏障、颜色桶负载不均和每个颜色内部可并行元素数量不足；线程增加后容易受同步和短任务调度限制。",
    }
    return notes.get(algorithm, "该算法没有专门瓶颈说明。")


def fmt_ms(value: float) -> str:
    return f"{value:.3f}"


def fmt_speedup(value: float) -> str:
    return f"{value:.3f}x"


def write_combined_csv(rows: list[ScalingRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "env_group",
                "algorithm",
                "threads",
                "thread_region",
                "assembly_ms",
                "speedup",
                "efficiency",
                "status",
                "skip_reason",
                "diagnostics",
                "physical_cores",
                "logical_cores",
                "cpu_model",
                "omp_dynamic",
                "omp_proc_bind",
                "omp_places",
                "extra_memory_bytes",
                "rel_l2",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.env_group,
                    row.algorithm,
                    row.threads,
                    row.region,
                    row.assembly_ms,
                    row.speedup,
                    row.efficiency,
                    row.status,
                    row.skip_reason,
                    row.diagnostics,
                    row.physical_cores,
                    row.logical_cores,
                    row.cpu_model,
                    row.omp_dynamic,
                    row.omp_proc_bind,
                    row.omp_places,
                    row.extra_memory_bytes,
                    row.rel_l2,
                ]
            )


def write_report(rows: list[ScalingRow], out_path: Path, case_label: str, kernel: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    first = rows[0] if rows else None
    physical = first.physical_cores if first else 0
    logical = first.logical_cores if first else 0
    cpu_model = first.cpu_model if first else "Unknown CPU"
    max_thread = max((row.threads for row in rows), default=0)
    oversub_start = physical + 1 if physical > 0 else 0

    by_env_algo: dict[tuple[str, str], list[ScalingRow]] = defaultdict(list)
    for row in rows:
        by_env_algo[(row.env_group, row.algorithm)].append(row)

    present_envs = {row.env_group for row in rows}
    env_groups = [name for name in ("default", "bound") if name in present_envs]
    algorithms = ["cpu_atomic", "cpu_private_csr", "cpu_row_owner", "cpu_graph_coloring"]

    with out_path.open("w", encoding="utf-8") as handle:
        handle.write("# 物理核/超物理线程扩展评估报告\n\n")
        handle.write("## 实验设置\n\n")
        handle.write(f"- case: `{case_label}`\n")
        handle.write(f"- kernel: `{kernel}`\n")
        handle.write(f"- CPU: `{cpu_model}`，physical_cores={physical}，logical_cores={logical}\n")
        handle.write(f"- 线程范围: `1..{max_thread}`\n")
        handle.write("- 算法范围: `atomic`, `private_csr`, `row_owner`, `coloring`\n")
        handle.write("- 判定阈值: 超过物理核后的最佳组装时间相对物理核内最佳值改善/退化超过 `5%`，分别判为继续加速/变慢；否则判为基本持平。\n\n")

        handle.write("## 核区间定义\n\n")
        if physical > 0:
            handle.write(f"- 物理核内扩展区间: `1..{physical}`。\n")
        if logical > physical:
            handle.write(f"- 逻辑核区间: `{physical + 1}..{logical}`。\n")
        else:
            handle.write(
                f"- 当前平台 `physical_cores == logical_cores == {physical}`，没有 SMT/超线程暴露出来的真实逻辑核区间。\n"
            )
        if oversub_start > 0 and max_thread >= oversub_start:
            handle.write(f"- 超过物理核后的区间: `{oversub_start}..{max_thread}`，在本机语义上是 oversubscription，不是真实逻辑核加速。\n")
        handle.write("\n")

        handle.write("## 主结论\n\n")
        for env_group in env_groups:
            handle.write(f"### 环境组 `{env_group}`\n\n")
            if env_group == "bound":
                handle.write("- OpenMP 设置: `OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=close`, `OMP_PLACES=cores`。\n")
            else:
                handle.write("- OpenMP 设置: 默认调度，脚本运行时清空 `OMP_DYNAMIC` / `OMP_PROC_BIND` / `OMP_PLACES`。\n")
            handle.write("\n")
            handle.write("| 算法 | 物理核内最佳 | 物理核内自扩展 | 超过物理核后最佳 | 趋势 | 主要瓶颈 |\n")
            handle.write("| --- | --- | ---: | --- | --- | --- |\n")
            for algorithm in algorithms:
                algo_rows = by_env_algo.get((env_group, algorithm), [])
                physical_rows = [row for row in algo_rows if row.status == "PASS" and row.threads <= physical]
                beyond_rows = [row for row in algo_rows if row.status == "PASS" and row.threads > physical]
                one_thread = next((row for row in physical_rows if row.threads == 1), None)
                best_physical = best_by_time(physical_rows)
                best_beyond = best_by_time(beyond_rows)
                if not best_physical:
                    handle.write(f"| `{algorithm}` | 无 PASS 数据 | - | 无 PASS 数据 | 无法判定 | {bottleneck_note(algorithm)} |\n")
                    continue
                self_scaling = one_thread.assembly_ms / best_physical.assembly_ms if one_thread else 0.0
                physical_text = (
                    f"`{best_physical.threads}T`, {fmt_ms(best_physical.assembly_ms)} ms, "
                    f"serial speedup {fmt_speedup(best_physical.speedup)}"
                )
                if best_beyond:
                    beyond_text = (
                        f"`{best_beyond.threads}T`, {fmt_ms(best_beyond.assembly_ms)} ms, "
                        f"serial speedup {fmt_speedup(best_beyond.speedup)}"
                    )
                    trend = classify_change(best_physical.assembly_ms, best_beyond.assembly_ms)
                else:
                    beyond_text = "无 PASS 数据"
                    trend = "无法判定"
                handle.write(
                    f"| `{algorithm}` | {physical_text} | {self_scaling:.3f}x | {beyond_text} | {trend} | {bottleneck_note(algorithm)} |\n"
                )
            handle.write("\n")

        skipped = [row for row in rows if row.status != "PASS"]
        if skipped:
            handle.write("## 跳过/失败记录\n\n")
            handle.write("| 环境组 | 算法 | 线程 | 状态 | 原因 |\n")
            handle.write("| --- | --- | ---: | --- | --- |\n")
            for row in skipped:
                reason = row.skip_reason or row.diagnostics
                handle.write(f"| `{row.env_group}` | `{row.algorithm}` | {row.threads} | {row.status} | {reason} |\n")
            handle.write("\n")

        handle.write("## 解释边界\n\n")
        handle.write(
            "本报告只回答 CPU 并行组装算法在物理核内和超过物理核后的线程扩展表现；"
            "它不重开符号/无符号组装主线，也不把 `coo_sort_reduce` 纳入本次 full matrix。"
        )
        if logical > physical:
            handle.write(
                f"在当前 `{cpu_model}` 上，`{physical + 1}..{logical}` 线程代表 SMT/逻辑核区间，"
                f"`{logical + 1}..{max_thread}` 线程代表 oversubscription。\n"
            )
        else:
            handle.write(
                f"在当前 `{cpu_model}` 上，`physical_cores == logical_cores == {physical}`，"
                f"超过 {physical} 线程代表软件线程过量订阅，不能被解读为 SMT 逻辑核收益。\n"
            )


def env_for_group(name: str) -> dict[str, str]:
    env = os.environ.copy()
    if name == "default":
        for key in OMP_KEYS:
            env.pop(key, None)
    elif name == "bound":
        env.update(BOUND_ENV)
    else:
        raise ValueError(f"Unknown env group: {name}")
    return env


def benchmark_command(args: argparse.Namespace, exe: Path, csv_path: Path, json_path: Path, summary_path: Path) -> list[str]:
    kernel = args.kernel
    cmd = [
        str(exe),
        "--algo",
        ALGORITHMS,
        "--threads-range",
        args.threads_range,
        "--kernel",
        kernel,
        "--warmup",
        str(args.warmup),
        "--repeat",
        str(args.repeat),
        "--check",
        "--max-memory-gb",
        str(args.max_memory_gb),
        "--csv",
        str(csv_path),
        "--json",
        str(json_path),
        "--summary-md",
        str(summary_path),
    ]
    if args.case == "windhub":
        cmd.extend(
            [
                "--mesh",
                "inp",
                "--inp",
                "../../examples/3d-WindTurbineHub.inp",
                "--case-name",
                "3d-WindTurbineHub",
            ]
        )
    else:
        cmd.extend(
            [
                "--mesh",
                "cube",
                "--element",
                "tet4",
                "--nx",
                str(args.nx),
                "--ny",
                str(args.ny),
                "--nz",
                str(args.nz),
                "--case-name",
                f"thread_scaling_smoke_tet4_{args.nx}x{args.ny}x{args.nz}",
            ]
        )
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build/cpu-release")
    parser.add_argument("--out-root", default=None, help="default: results/YYYY-MM-DD-thread-scaling")
    parser.add_argument("--threads-range", default="1:28")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--max-memory-gb", type=float, default=32.0)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--case", choices=("windhub", "cube"), default="windhub")
    parser.add_argument("--kernel", default=None)
    parser.add_argument("--nx", type=int, default=4)
    parser.add_argument("--ny", type=int, default=4)
    parser.add_argument("--nz", type=int, default=4)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    build_dir = root / args.build_dir
    if args.kernel is None:
        args.kernel = "physics_tet4" if args.case == "windhub" else "simplified"

    if not args.skip_build:
        run(
            [
                "cmake",
                "-S",
                ".",
                "-B",
                str(build_dir),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DBUILD_TESTS=ON",
                "-DBUILD_BENCHMARKS=ON",
            ],
            root,
        )
        run(["cmake", "--build", str(build_dir), "--target", "benchmark_assembly", "-j"], root)

    exe = benchmark_exe(build_dir)
    if not exe.exists():
        raise FileNotFoundError(f"benchmark executable not found: {exe}")

    out_root = (
        root / "results" / f"{date.today().isoformat()}-thread-scaling"
        if args.out_root is None
        else Path(args.out_root)
    )
    out_root.mkdir(parents=True, exist_ok=True)

    all_rows: list[ScalingRow] = []
    for env_group in ("default", "bound"):
        group_dir = out_root / env_group
        group_dir.mkdir(parents=True, exist_ok=True)
        csv_path = group_dir / f"thread_scaling_{env_group}.csv"
        json_path = group_dir / f"thread_scaling_{env_group}.json"
        summary_path = group_dir / f"benchmark_summary_{env_group}.md"
        cmd = benchmark_command(args, exe, csv_path, json_path, summary_path)
        run(cmd, root, env=env_for_group(env_group))
        all_rows.extend(load_rows(csv_path, env_group))

    combined_csv = out_root / "thread_scaling_combined.csv"
    report_path = out_root / "thread_scaling_report.md"
    write_combined_csv(all_rows, combined_csv)
    case_label = "3d-WindTurbineHub" if args.case == "windhub" else f"cube_tet4_{args.nx}x{args.ny}x{args.nz}"
    write_report(all_rows, report_path, case_label, args.kernel)

    print(f"[OK] combined CSV: {combined_csv}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
