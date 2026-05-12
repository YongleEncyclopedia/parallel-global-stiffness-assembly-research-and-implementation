#!/usr/bin/env python3
"""Generate visualizations for physical-core and oversubscription thread scaling."""
from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Heiti TC",
    "STHeiti",
    "Arial Unicode MS",
    "SimHei",
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "WenQuanYi Zen Hei",
    "Droid Sans Fallback",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "#f8fafc"
plt.rcParams["axes.edgecolor"] = "#cbd5e1"
plt.rcParams["grid.color"] = "#cbd5e1"
plt.rcParams["grid.alpha"] = 0.45
plt.rcParams["font.size"] = 10


ALGORITHM_ORDER = [
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
]

ENV_ORDER = ["default", "bound"]

ALGO_LABELS = {
    "cpu_atomic": "原子直接累加\nAtomic",
    "cpu_private_csr": "线程私有 CSR\nPrivate CSR",
    "cpu_row_owner": "行拥有者\nRow Owner",
    "cpu_graph_coloring": "图着色\nColoring",
}

ALGO_SHORT = {
    "cpu_atomic": "Atomic",
    "cpu_private_csr": "Private CSR",
    "cpu_row_owner": "Row Owner",
    "cpu_graph_coloring": "Coloring",
}

ALGO_COLORS = {
    "cpu_atomic": "#2563eb",
    "cpu_private_csr": "#0f766e",
    "cpu_row_owner": "#16a34a",
    "cpu_graph_coloring": "#7c3aed",
}

ENV_COLORS = {
    "default": "#2563eb",
    "bound": "#dc2626",
}

STAGE_KEYS = [
    ("prepare_allocate_ms", "预分配"),
    ("prepare_coloring_ms", "着色预处理"),
    ("prepare_owner_partition_ms", "owner 划分"),
    ("assembly_zero_ms", "清零"),
    ("assembly_generate_ms", "生成"),
    ("assembly_numeric_ms", "数值装配"),
    ("assembly_merge_ms", "合并"),
    ("assembly_sort_ms", "排序"),
    ("assembly_reduce_ms", "规约"),
]

STAGE_COLORS = [
    "#64748b",
    "#7c3aed",
    "#16a34a",
    "#94a3b8",
    "#ea580c",
    "#2563eb",
    "#0891b2",
    "#dc2626",
    "#0f766e",
]


@dataclass
class ThreadScalingRecord:
    env_group: str
    algorithm: str
    threads: int
    thread_region: str
    assembly_ms: float
    total_ms: float
    speedup: float
    efficiency: float
    status: str
    physical_cores: int
    logical_cores: int
    cpu_model: str
    extra_memory_bytes: float
    rel_l2: float
    omp_dynamic: str
    omp_proc_bind: str
    omp_places: str
    stages: dict[str, float]


def parse_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0


def parse_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value not in ("", None) else 0


def load_raw_csv(path: Path, env_group: str) -> list[ThreadScalingRecord]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV contains no records: {path}")
    records: list[ThreadScalingRecord] = []
    for row in rows:
        stages = {key: parse_float(row, key) for key, _ in STAGE_KEYS}
        records.append(
            ThreadScalingRecord(
                env_group=env_group,
                algorithm=row["algorithm"],
                threads=parse_int(row, "threads"),
                thread_region=row.get("thread_region", ""),
                assembly_ms=parse_float(row, "assembly_mean_ms") or parse_float(row, "assembly_ms"),
                total_ms=parse_float(row, "total_mean_ms") or parse_float(row, "total_ms"),
                speedup=parse_float(row, "speedup"),
                efficiency=parse_float(row, "efficiency"),
                status=row["status"],
                physical_cores=parse_int(row, "physical_cores"),
                logical_cores=parse_int(row, "logical_cores"),
                cpu_model=row.get("cpu_model", ""),
                extra_memory_bytes=parse_float(row, "extra_memory_bytes"),
                rel_l2=parse_float(row, "rel_l2"),
                omp_dynamic=row.get("omp_dynamic", ""),
                omp_proc_bind=row.get("omp_proc_bind", ""),
                omp_places=row.get("omp_places", ""),
                stages=stages,
            )
        )
    return records


def pass_records(records: Iterable[ThreadScalingRecord]) -> list[ThreadScalingRecord]:
    return [record for record in records if record.status == "PASS" and record.assembly_ms > 0.0]


def records_by_env_algorithm(records: Iterable[ThreadScalingRecord]) -> dict[tuple[str, str], list[ThreadScalingRecord]]:
    grouped: dict[tuple[str, str], list[ThreadScalingRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.env_group, record.algorithm)].append(record)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.threads)
    return dict(grouped)


def records_by_env(records: Iterable[ThreadScalingRecord]) -> dict[str, list[ThreadScalingRecord]]:
    grouped: dict[str, list[ThreadScalingRecord]] = defaultdict(list)
    for record in records:
        grouped[record.env_group].append(record)
    for rows in grouped.values():
        rows.sort(key=lambda item: (item.algorithm, item.threads))
    return dict(grouped)


def best_by_time(records: Iterable[ThreadScalingRecord]) -> ThreadScalingRecord | None:
    passed = pass_records(records)
    return min(passed, key=lambda item: item.assembly_ms) if passed else None


def physical_cores(records: list[ThreadScalingRecord]) -> int:
    for record in records:
        if record.physical_cores > 0:
            return record.physical_cores
    return 0


def memory_gib(record: ThreadScalingRecord) -> float:
    return record.extra_memory_bytes / (1024.0 ** 3)


def save_figure(fig: plt.Figure, out_base: Path) -> None:
    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".png"), dpi=220, bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def shade_thread_regions(ax: plt.Axes, physical: int, max_thread: int) -> None:
    if physical <= 0:
        return
    ax.axvline(physical, color="#ef4444", linestyle="--", linewidth=1.5, alpha=0.8)
    if max_thread > physical:
        ax.axvspan(physical + 0.5, max_thread + 0.5, color="#fee2e2", alpha=0.25, label="oversubscription")
    ax.text(
        physical + 0.15,
        0.95,
        f"{physical} physical cores",
        transform=ax.get_xaxis_transform(),
        color="#b91c1c",
        fontsize=8,
        va="top",
        rotation=90,
    )


def key_rows_for_annotation(rows: list[ThreadScalingRecord], physical: int) -> list[ThreadScalingRecord]:
    lookup = {row.threads: row for row in rows}
    selected: dict[int, ThreadScalingRecord] = {}
    for thread in (1, physical, max(lookup.keys())):
        if thread in lookup:
            selected[thread] = lookup[thread]
    best_physical = best_by_time(row for row in rows if row.threads <= physical)
    best_beyond = best_by_time(row for row in rows if row.threads > physical)
    for row in (best_physical, best_beyond):
        if row:
            selected[row.threads] = row
    return [selected[key] for key in sorted(selected)]


def annotate_key_rows(ax: plt.Axes, rows: list[ThreadScalingRecord], metric: str, physical: int) -> None:
    for row in key_rows_for_annotation(rows, physical):
        if metric == "assembly_ms":
            value = row.assembly_ms
            label = f"{row.threads}T\n{value:.1f} ms"
        elif metric == "speedup":
            value = row.speedup
            label = f"{row.threads}T\n{value:.2f}x"
        elif metric == "efficiency":
            value = row.efficiency * 100.0
            label = f"{row.threads}T\n{value:.1f}%"
        else:
            value = memory_gib(row)
            label = f"{row.threads}T\n{value:.2f} GiB"
        ax.annotate(
            label,
            xy=(row.threads, value),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=7.5,
            fontweight="bold",
            color="#0f172a",
            bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.82},
        )


def plot_algorithm_detail(records: list[ThreadScalingRecord], algorithm: str, out_dir: Path) -> Path:
    grouped = records_by_env_algorithm(records)
    algo_records = [record for record in records if record.algorithm == algorithm]
    physical = physical_cores(algo_records)
    max_thread = max(record.threads for record in algo_records)
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    metrics = [
        ("assembly_ms", "组装时间 (ms, log)", "Assembly Time"),
        ("speedup", "相对串行基线加速比", "Speedup"),
        ("efficiency", "并行效率 (%)", "Efficiency"),
    ]
    for ax, (metric, ylabel, title) in zip(axes, metrics):
        shade_thread_regions(ax, physical, max_thread)
        for env_group in ENV_ORDER:
            rows = grouped.get((env_group, algorithm), [])
            if not rows:
                continue
            xs = [row.threads for row in rows]
            if metric == "assembly_ms":
                ys = [row.assembly_ms for row in rows]
            elif metric == "speedup":
                ys = [row.speedup for row in rows]
            else:
                ys = [row.efficiency * 100.0 for row in rows]
            ax.plot(
                xs,
                ys,
                marker="o",
                linewidth=2.1,
                markersize=5.5,
                color=ENV_COLORS[env_group],
                label=env_group,
            )
            annotate_key_rows(ax, rows, metric, physical)
        if metric == "assembly_ms":
            ax.set_yscale("log")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{title} | {ALGO_SHORT[algorithm]}")
        ax.grid(True, axis="both")
        ax.legend(loc="best", framealpha=0.95)
    axes[-1].set_xlabel("线程数")
    axes[-1].set_xticks(list(range(1, max_thread + 1)))
    fig.suptitle(
        f"线程扩展详细曲线 / Thread Scaling Detail\n{ALGO_LABELS[algorithm].replace(chr(10), ' ')}",
        fontsize=16,
        fontweight="bold",
    )
    out_base = out_dir / f"thread_scaling_by_algorithm_{algorithm}"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def plot_env_dashboard(records: list[ThreadScalingRecord], env_group: str, out_dir: Path) -> Path:
    env_records = [record for record in records if record.env_group == env_group]
    grouped = records_by_env_algorithm(env_records)
    physical = physical_cores(env_records)
    max_thread = max(record.threads for record in env_records)
    fig = plt.figure(figsize=(17, 13))
    grid = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 0.82])
    ax_time = fig.add_subplot(grid[0, 0])
    ax_speedup = fig.add_subplot(grid[0, 1])
    ax_eff = fig.add_subplot(grid[1, 0])
    ax_mem = fig.add_subplot(grid[1, 1])
    ax_bars = fig.add_subplot(grid[2, 0])
    ax_table = fig.add_subplot(grid[2, 1])

    for ax in (ax_time, ax_speedup, ax_eff, ax_mem):
        shade_thread_regions(ax, physical, max_thread)

    for algorithm in ALGORITHM_ORDER:
        rows = grouped.get((env_group, algorithm), [])
        if not rows:
            continue
        xs = [row.threads for row in rows]
        color = ALGO_COLORS[algorithm]
        ax_time.plot(xs, [row.assembly_ms for row in rows], marker="o", linewidth=2.0, color=color, label=ALGO_SHORT[algorithm])
        ax_speedup.plot(xs, [row.speedup for row in rows], marker="o", linewidth=2.0, color=color, label=ALGO_SHORT[algorithm])
        ax_eff.plot(xs, [row.efficiency * 100.0 for row in rows], marker="o", linewidth=2.0, color=color, label=ALGO_SHORT[algorithm])
        ax_mem.plot(xs, [memory_gib(row) for row in rows], marker="o", linewidth=2.0, color=color, label=ALGO_SHORT[algorithm])
        annotate_key_rows(ax_time, rows, "assembly_ms", physical)
        annotate_key_rows(ax_speedup, rows, "speedup", physical)

    ax_time.set_yscale("log")
    ax_time.set_title("组装时间曲线 (log ms)")
    ax_time.set_ylabel("ms")
    ax_speedup.set_title("加速比曲线")
    ax_speedup.set_ylabel("x")
    ax_eff.set_title("并行效率曲线")
    ax_eff.set_ylabel("%")
    ax_mem.set_title("额外内存曲线")
    ax_mem.set_ylabel("GiB")
    for ax in (ax_time, ax_speedup, ax_eff, ax_mem):
        ax.grid(True)
        ax.set_xlabel("线程数")
        ax.set_xticks(list(range(1, max_thread + 1, 2)))
        ax.legend(loc="best", framealpha=0.95)

    x = np.arange(len(ALGORITHM_ORDER))
    width = 0.36
    physical_values = []
    beyond_values = []
    table_rows = []
    for algorithm in ALGORITHM_ORDER:
        rows = grouped.get((env_group, algorithm), [])
        best_physical = best_by_time(row for row in rows if row.threads <= physical)
        best_beyond = best_by_time(row for row in rows if row.threads > physical)
        physical_values.append(best_physical.assembly_ms if best_physical else 0.0)
        beyond_values.append(best_beyond.assembly_ms if best_beyond else 0.0)
        trend = "n/a"
        if best_physical and best_beyond:
            if best_beyond.assembly_ms < best_physical.assembly_ms * 0.95:
                trend = "继续加速"
            elif best_beyond.assembly_ms > best_physical.assembly_ms * 1.05:
                trend = "变慢"
            else:
                trend = "持平"
        best_overall = best_by_time(rows)
        table_rows.append(
            [
                ALGO_SHORT[algorithm],
                f"{best_overall.threads}T" if best_overall else "-",
                f"{best_overall.assembly_ms:.1f}" if best_overall else "-",
                f"{best_overall.speedup:.2f}x" if best_overall else "-",
                trend,
            ]
        )
    ax_bars.bar(x - width / 2, physical_values, width=width, color="#0f766e", label="物理核内最佳")
    ax_bars.bar(x + width / 2, beyond_values, width=width, color="#ea580c", label="超物理最佳")
    for xpos, physical_value, beyond_value in zip(x, physical_values, beyond_values):
        ax_bars.annotate(f"{physical_value:.1f}", (xpos - width / 2, physical_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8)
        ax_bars.annotate(f"{beyond_value:.1f}", (xpos + width / 2, beyond_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8)
    ax_bars.set_xticks(x)
    ax_bars.set_xticklabels([ALGO_SHORT[name] for name in ALGORITHM_ORDER], rotation=10)
    ax_bars.set_ylabel("组装时间 (ms)")
    ax_bars.set_title("物理核内最佳 vs 超物理最佳")
    ax_bars.grid(True, axis="y")
    ax_bars.legend(loc="best", framealpha=0.95)

    ax_table.axis("off")
    table = ax_table.table(
        cellText=table_rows,
        colLabels=["算法", "最佳线程", "最佳 ms", "加速比", "超物理趋势"],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.35)
    for (row_idx, _col_idx), cell in table.get_celld().items():
        if row_idx == 0:
            cell.set_facecolor("#1d4ed8")
            cell.set_text_props(color="white", weight="bold")
        elif row_idx % 2 == 1:
            cell.set_facecolor("#eff6ff")
        else:
            cell.set_facecolor("#f8fafc")
    ax_table.set_title("最佳点摘要")

    fig.suptitle(f"线程扩展总览 / Thread Scaling Dashboard\n环境组: {env_group}", fontsize=16, fontweight="bold")
    out_base = out_dir / f"thread_scaling_{env_group}_dashboard"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def plot_memory_by_env(records: list[ThreadScalingRecord], out_dir: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.8), sharey=True)
    for ax, env_group in zip(axes, ENV_ORDER):
        env_records = [record for record in records if record.env_group == env_group]
        grouped = records_by_env_algorithm(env_records)
        physical = physical_cores(env_records)
        max_thread = max(record.threads for record in env_records)
        shade_thread_regions(ax, physical, max_thread)
        for algorithm in ALGORITHM_ORDER:
            rows = grouped.get((env_group, algorithm), [])
            if not rows:
                continue
            ax.plot(
                [row.threads for row in rows],
                [memory_gib(row) for row in rows],
                marker="o",
                linewidth=2.0,
                color=ALGO_COLORS[algorithm],
                label=ALGO_SHORT[algorithm],
            )
            annotate_key_rows(ax, rows, "memory", physical)
        ax.set_title(f"{env_group}: 额外内存随线程变化")
        ax.set_xlabel("线程数")
        ax.set_xticks(list(range(1, max_thread + 1, 2)))
        ax.grid(True)
        ax.legend(loc="best", framealpha=0.95)
    axes[0].set_ylabel("额外内存 (GiB)")
    fig.suptitle("资源视角 / Extra Memory by Environment", fontsize=16, fontweight="bold")
    out_base = out_dir / "thread_scaling_memory_by_env"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def plot_physical_vs_oversubscription(records: list[ThreadScalingRecord], out_dir: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.8), sharey=True)
    for ax, env_group in zip(axes, ENV_ORDER):
        env_records = [record for record in records if record.env_group == env_group]
        grouped = records_by_env_algorithm(env_records)
        physical = physical_cores(env_records)
        x = np.arange(len(ALGORITHM_ORDER))
        width = 0.34
        physical_values = []
        beyond_values = []
        trend_labels = []
        for algorithm in ALGORITHM_ORDER:
            rows = grouped.get((env_group, algorithm), [])
            best_physical = best_by_time(row for row in rows if row.threads <= physical)
            best_beyond = best_by_time(row for row in rows if row.threads > physical)
            physical_values.append(best_physical.assembly_ms if best_physical else 0.0)
            beyond_values.append(best_beyond.assembly_ms if best_beyond else 0.0)
            if best_physical and best_beyond:
                ratio = best_beyond.assembly_ms / best_physical.assembly_ms
                if ratio < 0.95:
                    trend_labels.append("继续加速")
                elif ratio > 1.05:
                    trend_labels.append("变慢")
                else:
                    trend_labels.append("持平")
            else:
                trend_labels.append("n/a")
        ax.bar(x - width / 2, physical_values, width=width, color="#0f766e", label="physical best")
        ax.bar(x + width / 2, beyond_values, width=width, color="#ea580c", label="oversub best")
        for xpos, physical_value, beyond_value, trend in zip(x, physical_values, beyond_values, trend_labels):
            ax.annotate(f"{physical_value:.1f}", (xpos - width / 2, physical_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")
            ax.annotate(f"{beyond_value:.1f}\n{trend}", (xpos + width / 2, beyond_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([ALGO_SHORT[name] for name in ALGORITHM_ORDER], rotation=10)
        ax.set_title(f"{env_group}: 物理核内最佳 vs 超物理最佳")
        ax.set_ylabel("组装时间 (ms, lower is better)")
        ax.grid(True, axis="y")
        ax.legend(loc="best", framealpha=0.95)
    fig.suptitle("超物理线程是否继续加速 / Physical vs Oversubscription", fontsize=16, fontweight="bold")
    out_base = out_dir / "thread_scaling_physical_vs_oversubscription"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def stage_values(row: ThreadScalingRecord) -> list[float]:
    values = [row.stages.get(key, 0.0) for key, _ in STAGE_KEYS]
    if all(abs(value) < 1.0e-12 for value in values):
        return [row.assembly_ms if idx == 5 else 0.0 for idx, _ in enumerate(STAGE_KEYS)]
    return values


def plot_stage_breakdown_best(records: list[ThreadScalingRecord], out_dir: Path) -> Path:
    selected: list[ThreadScalingRecord] = []
    grouped = records_by_env_algorithm(records)
    for env_group in ENV_ORDER:
        for algorithm in ALGORITHM_ORDER:
            best = best_by_time(grouped.get((env_group, algorithm), []))
            if best:
                selected.append(best)
    fig, ax = plt.subplots(figsize=(16, 7.5))
    x = np.arange(len(selected))
    cumulative = np.zeros(len(selected))
    for idx, (_key, label) in enumerate(STAGE_KEYS):
        heights = np.array([stage_values(row)[idx] for row in selected], dtype=float)
        if np.allclose(heights, 0.0):
            continue
        ax.bar(x, heights, bottom=cumulative, color=STAGE_COLORS[idx % len(STAGE_COLORS)], edgecolor="white", label=label)
        cumulative += heights
    for xpos, row, total in zip(x, selected, cumulative):
        label_y = total if total > 0 else row.assembly_ms
        ax.annotate(
            f"{row.env_group}\n{ALGO_SHORT[row.algorithm]}\n{row.threads}T, {row.assembly_ms:.1f} ms",
            (xpos, label_y),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            fontsize=7.8,
            fontweight="bold",
        )
    ax.set_xticks(x)
    ax.set_xticklabels([f"{row.env_group}\n{ALGO_SHORT[row.algorithm]}" for row in selected], rotation=12)
    ax.set_ylabel("阶段时间 (ms)")
    ax.set_title("最佳线程点阶段拆分 / Stage Breakdown at Best Thread")
    ax.grid(True, axis="y")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    out_base = out_dir / "thread_scaling_stage_breakdown_best"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def make_contact_sheet(image_paths: list[Path], out_dir: Path) -> Path:
    cols = 2
    rows = math.ceil(len(image_paths) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(16, rows * 5.1))
    axes_array = np.atleast_1d(axes).ravel()
    for ax, image_path in zip(axes_array, image_paths):
        ax.imshow(mpimg.imread(image_path))
        ax.set_title(image_path.stem, fontsize=11, fontweight="bold")
        ax.axis("off")
    for ax in axes_array[len(image_paths):]:
        ax.axis("off")
    fig.suptitle("线程扩展核心图总览 / Thread Scaling Contact Sheet", fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = out_dir / "thread_scaling_contact_sheet.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_figures_summary(out_dir: Path, image_paths: list[Path]) -> Path:
    descriptions = {
        "thread_scaling_default_dashboard": "default 环境下四算法的时间、加速比、效率、内存和物理/超物理最佳对比。",
        "thread_scaling_bound_dashboard": "bound 环境下四算法的时间、加速比、效率、内存和物理/超物理最佳对比。",
        "thread_scaling_memory_by_env": "两组环境下额外内存随线程数变化，突出 private_csr 的内存压力。",
        "thread_scaling_physical_vs_oversubscription": "物理核内最佳与超物理最佳直接对比，支撑继续加速/持平/变慢判断。",
        "thread_scaling_stage_breakdown_best": "各环境/算法最佳线程点的阶段拆分，用于解释瓶颈。",
        "thread_scaling_contact_sheet": "核心图缩略总览。",
    }
    path = out_dir / "summary.md"
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Thread Scaling Figures Summary\n\n")
        handle.write("本目录图表与 `plot_cpu_results.py` 的 benchmark 风格保持一致，PNG 用于 Markdown 浏览，SVG 用于放大或后续编辑。\n\n")
        handle.write("| 图表 | PNG | SVG | 用途 |\n")
        handle.write("| --- | --- | --- | --- |\n")
        for image_path in image_paths:
            if image_path.name == "thread_scaling_contact_sheet.png":
                stem = image_path.stem
                svg_text = "-"
            else:
                stem = image_path.stem
                svg_text = f"[svg]({stem}.svg)"
            description = descriptions.get(stem, "单算法 default/bound 详细线程扩展曲线。")
            handle.write(f"| `{stem}` | [png]({image_path.name}) | {svg_text} | {description} |\n")
    return path


def figure_block() -> str:
    return """<!-- thread-scaling-figures:start -->
## 可视化图表

核心图表已生成到 `figures/`。Markdown 中嵌入 PNG 以保证 GitHub、本地预览和普通浏览器都能直接显示；每张图同时提供 SVG 版本用于放大检查。

### 关键对比与瓶颈总览

![physical vs oversubscription](figures/thread_scaling_physical_vs_oversubscription.png)

[physical vs oversubscription SVG](figures/thread_scaling_physical_vs_oversubscription.svg)

![extra memory by environment](figures/thread_scaling_memory_by_env.png)

[extra memory by environment SVG](figures/thread_scaling_memory_by_env.svg)

![stage breakdown best](figures/thread_scaling_stage_breakdown_best.png)

[stage breakdown best SVG](figures/thread_scaling_stage_breakdown_best.svg)

完整图表索引见 [figures/summary.md](figures/summary.md)。

<!-- thread-scaling-figures:end -->
"""


def env_dashboard_block(env_group: str) -> str:
    return f"""<!-- thread-scaling-{env_group}-dashboard:start -->

![{env_group} dashboard](figures/thread_scaling_{env_group}_dashboard.png)

[{env_group} dashboard SVG](figures/thread_scaling_{env_group}_dashboard.svg)

<!-- thread-scaling-{env_group}-dashboard:end -->

"""


def replace_env_dashboard(text: str, env_group: str) -> str:
    block = env_dashboard_block(env_group)
    pattern = re.compile(
        rf"<!-- thread-scaling-{env_group}-dashboard:start -->.*?<!-- thread-scaling-{env_group}-dashboard:end -->\n?",
        re.S,
    )
    if pattern.search(text):
        return pattern.sub(block, text)

    heading = f"### 环境组 `{env_group}`"
    start = text.find(heading)
    if start < 0:
        raise ValueError(f"Cannot find environment section in report: {env_group}")
    next_heading = text.find("\n### 环境组 `", start + len(heading))
    search_end = next_heading if next_heading >= 0 else len(text)
    paragraph_end = text.find("\n\n", start, search_end)
    if paragraph_end < 0:
        raise ValueError(f"Cannot find insertion point for environment section: {env_group}")
    return text[: paragraph_end + 2] + block + text[paragraph_end + 2 :]


def update_report(report_path: Path) -> None:
    text = report_path.read_text(encoding="utf-8")
    block = figure_block()
    pattern = re.compile(r"<!-- thread-scaling-figures:start -->.*?<!-- thread-scaling-figures:end -->\n?", re.S)
    if pattern.search(text):
        text = pattern.sub(block, text)
    else:
        marker = "## 主结论\n"
        if marker not in text:
            raise ValueError(f"Cannot find insertion marker in report: {report_path}")
        text = text.replace(marker, block + "\n" + marker, 1)
    for env_group in ENV_ORDER:
        text = replace_env_dashboard(text, env_group)
    report_path.write_text(text, encoding="utf-8")


def validate_outputs(out_dir: Path, report_path: Path, expected_pngs: list[str]) -> None:
    missing: list[str] = []
    for png in expected_pngs:
        path = out_dir / png
        if not path.exists() or path.stat().st_size == 0:
            missing.append(str(path))
        if png != "thread_scaling_contact_sheet.png":
            svg = path.with_suffix(".svg")
            if not svg.exists() or svg.stat().st_size == 0:
                missing.append(str(svg))
    if missing:
        raise RuntimeError("Missing or empty figure files:\n" + "\n".join(missing))

    report_text = report_path.read_text(encoding="utf-8")
    linked = re.findall(r"(?:!\[[^\]]*\]|\[[^\]]+\])\((figures/[^)\s]+)\)", report_text)
    unresolved = [link for link in linked if not (report_path.parent / link).exists()]
    if unresolved:
        raise RuntimeError("Unresolved report figure links:\n" + "\n".join(unresolved))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=Path("results/2026-05-11-thread-scaling"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--skip-report-update", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_root = args.results_root
    out_dir = args.out_dir or results_root / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_paths = {
        "default": results_root / "default" / "thread_scaling_default.csv",
        "bound": results_root / "bound" / "thread_scaling_bound.csv",
    }
    records: list[ThreadScalingRecord] = []
    for env_group in ENV_ORDER:
        records.extend(load_raw_csv(raw_paths[env_group], env_group))

    image_paths: list[Path] = []
    for env_group in ENV_ORDER:
        image_paths.append(plot_env_dashboard(records, env_group, out_dir))
    for algorithm in ALGORITHM_ORDER:
        image_paths.append(plot_algorithm_detail(records, algorithm, out_dir))
    image_paths.append(plot_memory_by_env(records, out_dir))
    image_paths.append(plot_physical_vs_oversubscription(records, out_dir))
    image_paths.append(plot_stage_breakdown_best(records, out_dir))
    contact_sheet = make_contact_sheet(image_paths, out_dir)
    image_paths.append(contact_sheet)
    write_figures_summary(out_dir, image_paths)

    report_path = results_root / "thread_scaling_report.md"
    if not args.skip_report_update:
        update_report(report_path)

    expected_pngs = [path.name for path in image_paths]
    validate_outputs(out_dir, report_path, expected_pngs)
    print(f"[OK] figures: {out_dir}")
    print(f"[OK] report updated: {report_path}")


if __name__ == "__main__":
    main()
