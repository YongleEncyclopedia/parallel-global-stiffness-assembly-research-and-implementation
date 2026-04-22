#!/usr/bin/env python3
"""生成 CPU 并行装配结果图表与摘要。

支持一个或多个 CSV 输入。每个 CSV 通常对应一个 case + kernel 组合。
脚本会输出：
- 每个数据集的执行时间、总时间、加速比、并行效率、阶段拆分、额外内存图
- 每个数据集的一张综合 dashboard
- 跨数据集的 case / kernel 对比图（当输入数量 >= 2）
- 一份中文 Markdown 摘要
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Heiti TC",
    "STHeiti",
    "Arial Unicode MS",
    "SimHei",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "#f8fafc"
plt.rcParams["axes.edgecolor"] = "#cbd5e1"
plt.rcParams["grid.color"] = "#cbd5e1"
plt.rcParams["grid.alpha"] = 0.45
plt.rcParams["font.size"] = 10


ALGO_LABELS = {
    "cpu_serial": "串行基线\nSerial",
    "cpu_atomic": "原子直接累加\nAtomic",
    "cpu_private_csr": "线程私有 CSR\nPrivate CSR",
    "cpu_coo_sort_reduce": "私有 COO 排序归并\nCOO Sort+Reduce",
    "cpu_graph_coloring": "图着色\nColoring",
    "cpu_row_owner": "行拥有者\nRow Owner",
}

ALGO_COLORS = {
    "cpu_serial": "#475569",
    "cpu_atomic": "#2563eb",
    "cpu_private_csr": "#0f766e",
    "cpu_coo_sort_reduce": "#ea580c",
    "cpu_graph_coloring": "#7c3aed",
    "cpu_row_owner": "#16a34a",
}

STAGE_KEYS = [
    ("prepare_allocate_ms", "预分配"),
    ("prepare_coloring_ms", "着色预处理"),
    ("prepare_owner_partition_ms", "owner 划分"),
    ("assembly_zero_ms", "装配前清零"),
    ("assembly_generate_ms", "局部贡献生成"),
    ("assembly_numeric_ms", "数值装配"),
    ("assembly_merge_ms", "线程结果合并"),
    ("assembly_sort_ms", "排序"),
    ("assembly_reduce_ms", "归并/规约"),
]


@dataclass
class Record:
    case_name: str
    mesh: str
    kernel: str
    algorithm: str
    threads: int
    effective_threads: int
    run_count: int
    preprocess_ms: float
    assembly_ms: float
    total_ms: float
    speedup: float
    efficiency: float
    preprocess_share: float
    rel_l2: float
    max_abs: float
    extra_memory_bytes: float
    peak_rss_mb: float
    colors: int
    status: str
    skip_reason: str
    diagnostics: str
    stages: dict[str, float]

    @property
    def dataset_key(self) -> tuple[str, str]:
        return (self.case_name, self.kernel)


def parse_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0


def parse_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value not in ("", None) else 0


def load_records(paths: Iterable[Path]) -> list[Record]:
    records: list[Record] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError(f"CSV contains no data: {path}")
        for row in rows:
            stages = {key: parse_float(row, key) for key, _ in STAGE_KEYS}
            records.append(
                Record(
                    case_name=row["case_name"],
                    mesh=row["mesh"],
                    kernel=row["kernel"],
                    algorithm=row["algorithm"],
                    threads=parse_int(row, "threads"),
                    effective_threads=parse_int(row, "effective_threads"),
                    run_count=parse_int(row, "run_count"),
                    preprocess_ms=parse_float(row, "preprocess_ms"),
                    assembly_ms=parse_float(row, "assembly_mean_ms") or parse_float(row, "assembly_ms"),
                    total_ms=parse_float(row, "total_mean_ms") or parse_float(row, "total_ms"),
                    speedup=parse_float(row, "speedup"),
                    efficiency=parse_float(row, "efficiency"),
                    preprocess_share=parse_float(row, "preprocess_share"),
                    rel_l2=parse_float(row, "rel_l2"),
                    max_abs=parse_float(row, "max_abs"),
                    extra_memory_bytes=parse_float(row, "extra_memory_bytes"),
                    peak_rss_mb=parse_float(row, "peak_rss_mb"),
                    colors=parse_int(row, "colors"),
                    status=row["status"],
                    skip_reason=row.get("skip_reason", ""),
                    diagnostics=row.get("diagnostics", ""),
                    stages=stages,
                )
            )
    return records


def pass_records(records: Iterable[Record]) -> list[Record]:
    return [record for record in records if record.status == "PASS"]


def group_by_dataset(records: Iterable[Record]) -> dict[tuple[str, str], list[Record]]:
    grouped: dict[tuple[str, str], list[Record]] = defaultdict(list)
    for record in records:
        grouped[record.dataset_key].append(record)
    return dict(grouped)


def dataset_slug(dataset: tuple[str, str]) -> str:
    case_name, kernel = dataset
    return f"{case_name}_{kernel}".replace("/", "_").replace(" ", "_")


def bytes_to_gib(value: float) -> float:
    return value / (1024.0 ** 3)


def human_algorithm_name(algorithm: str) -> str:
    return ALGO_LABELS.get(algorithm, algorithm)


def annotate_line(ax: plt.Axes, xs: list[int], ys: list[float], color: str, formatter) -> None:
    for x, y in zip(xs, ys):
        if y <= 0:
            continue
        ax.annotate(
            formatter(y),
            xy=(x, y),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=color,
            fontweight="bold",
        )


def save_figure(fig: plt.Figure, out_base: Path) -> None:
    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".png"), dpi=220, bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def case_title(dataset: tuple[str, str]) -> str:
    case_name, kernel = dataset
    return f"{case_name} | kernel={kernel}"


def per_dataset_groups(records: list[Record]) -> dict[str, list[Record]]:
    groups: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        groups[record.algorithm].append(record)
    for algo in groups:
        groups[algo].sort(key=lambda item: item.threads)
    return dict(groups)


def best_rows_by_algorithm(records: list[Record], metric: str = "assembly_ms") -> list[Record]:
    best: list[Record] = []
    by_algo: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        by_algo[record.algorithm].append(record)
    for algo, rows in sorted(by_algo.items()):
        best.append(min(rows, key=lambda row: getattr(row, metric)))
    return best


def plot_metric_vs_threads(records: list[Record], dataset: tuple[str, str], metric: str, ylabel: str,
                           out_dir: Path, title_prefix: str, percent: bool = False,
                           reference_line: float | None = None) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.5))
    for algorithm, rows in sorted(per_dataset_groups(records).items()):
        xs = [row.threads for row in rows]
        ys = [getattr(row, metric) * (100.0 if percent else 1.0) for row in rows]
        color = ALGO_COLORS.get(algorithm, "#334155")
        ax.plot(xs, ys, marker="o", linewidth=2.2, markersize=7, color=color, label=human_algorithm_name(algorithm))
        if metric in {"assembly_ms", "total_ms"}:
            annotate_line(ax, xs, ys, color, lambda value: f"{value:.1f}")
        elif metric == "speedup":
            annotate_line(ax, xs, ys, color, lambda value: f"{value:.2f}x")
        elif metric == "efficiency":
            annotate_line(ax, xs, ys, color, lambda value: f"{value*100.0:.1f}%" if value <= 1.0 else f"{value:.1f}%")
        else:
            annotate_line(ax, xs, ys, color, lambda value: f"{value:.1f}")
    if metric in {"assembly_ms", "total_ms"}:
        ax.set_yscale("log")
    if reference_line is not None:
        ax.axhline(reference_line, linestyle="--", color="#ef4444", linewidth=1.6, alpha=0.7)
    ax.set_xlabel("线程数")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title_prefix}\n{case_title(dataset)}")
    ax.grid(True, axis="both")
    ax.legend(loc="best", framealpha=0.95)
    save_figure(fig, out_dir / f"{dataset_slug(dataset)}_{metric}")


def plot_stage_breakdown(records: list[Record], dataset: tuple[str, str], out_dir: Path) -> None:
    selected = best_rows_by_algorithm(records)
    fig, ax = plt.subplots(figsize=(12, 6.8))
    x = np.arange(len(selected))
    cumulative = np.zeros(len(selected))
    palette = ["#0f766e", "#2563eb", "#7c3aed", "#64748b", "#ea580c", "#16a34a", "#dc2626", "#7c2d12", "#0891b2"]
    for idx, (key, stage_label) in enumerate(STAGE_KEYS):
        heights = np.array([row.stages.get(key, 0.0) for row in selected], dtype=float)
        if np.allclose(heights, 0.0):
            continue
        ax.bar(x, heights, bottom=cumulative, color=palette[idx % len(palette)], label=stage_label, edgecolor="white")
        cumulative += heights
    for xpos, row, total in zip(x, selected, cumulative):
        ax.annotate(f"{row.assembly_ms:.1f} ms\n@ {row.threads}T", (xpos, total), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([human_algorithm_name(row.algorithm) for row in selected])
    ax.set_ylabel("时间 (ms)")
    ax.set_title(f"算法阶段拆分 / Stage Breakdown\n{case_title(dataset)}")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    ax.grid(True, axis="y")
    save_figure(fig, out_dir / f"{dataset_slug(dataset)}_stage_breakdown")


def plot_extra_memory(records: list[Record], dataset: tuple[str, str], out_dir: Path) -> None:
    selected = best_rows_by_algorithm(records)
    fig, ax = plt.subplots(figsize=(11, 6.3))
    xs = np.arange(len(selected))
    values = [bytes_to_gib(row.extra_memory_bytes) for row in selected]
    colors = [ALGO_COLORS.get(row.algorithm, "#334155") for row in selected]
    bars = ax.bar(xs, values, color=colors, edgecolor="white")
    for bar, row, value in zip(bars, selected, values):
        ax.annotate(f"{value:.2f} GiB\n@ {row.threads}T", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")
    ax.set_xticks(xs)
    ax.set_xticklabels([human_algorithm_name(row.algorithm) for row in selected])
    ax.set_ylabel("额外内存 (GiB)")
    ax.set_title(f"额外内存对比 / Extra Memory\n{case_title(dataset)}")
    ax.grid(True, axis="y")
    save_figure(fig, out_dir / f"{dataset_slug(dataset)}_extra_memory")


def plot_dashboard(records: list[Record], dataset: tuple[str, str], out_dir: Path) -> None:
    algo_groups = per_dataset_groups(records)
    algorithms = sorted(algo_groups.keys())
    threads = sorted({row.threads for row in records})
    time_matrix = np.full((len(algorithms), len(threads)), np.nan)
    speedup_matrix = np.full((len(algorithms), len(threads)), np.nan)
    for i, algorithm in enumerate(algorithms):
        lookup = {row.threads: row for row in algo_groups[algorithm]}
        for j, thread in enumerate(threads):
            row = lookup.get(thread)
            if row:
                time_matrix[i, j] = row.assembly_ms
                speedup_matrix[i, j] = row.speedup

    fig = plt.figure(figsize=(15, 12))
    grid = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 0.7])
    ax1 = fig.add_subplot(grid[0, 0])
    ax2 = fig.add_subplot(grid[0, 1])
    ax3 = fig.add_subplot(grid[1, 0])
    ax4 = fig.add_subplot(grid[1, 1])
    ax5 = fig.add_subplot(grid[2, :])

    log_time = np.log10(np.where(np.isnan(time_matrix), np.nan, np.maximum(time_matrix, 1.0e-9)))
    im1 = ax1.imshow(log_time, cmap="YlOrRd", aspect="auto")
    ax1.set_title("执行时间热力图 (log10 ms)")
    ax1.set_xticks(range(len(threads)))
    ax1.set_xticklabels(threads)
    ax1.set_yticks(range(len(algorithms)))
    ax1.set_yticklabels([human_algorithm_name(name) for name in algorithms])
    for i in range(len(algorithms)):
        for j in range(len(threads)):
            value = time_matrix[i, j]
            if math.isnan(value):
                continue
            ax1.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=8, fontweight="bold")
    fig.colorbar(im1, ax=ax1, fraction=0.046)

    im2 = ax2.imshow(speedup_matrix, cmap="YlGn", aspect="auto")
    ax2.set_title("加速比热力图")
    ax2.set_xticks(range(len(threads)))
    ax2.set_xticklabels(threads)
    ax2.set_yticks(range(len(algorithms)))
    ax2.set_yticklabels([human_algorithm_name(name) for name in algorithms])
    for i in range(len(algorithms)):
        for j in range(len(threads)):
            value = speedup_matrix[i, j]
            if math.isnan(value):
                continue
            ax2.text(j, i, f"{value:.2f}x", ha="center", va="center", fontsize=8, fontweight="bold")
    fig.colorbar(im2, ax=ax2, fraction=0.046)

    best_rows = best_rows_by_algorithm(records)
    x = np.arange(len(best_rows))
    ax3.bar(x - 0.16, [row.preprocess_ms for row in best_rows], width=0.32, color="#64748b", label="预处理")
    ax3.bar(x + 0.16, [row.assembly_ms for row in best_rows], width=0.32, color="#2563eb", label="组装")
    for xpos, row in zip(x, best_rows):
        ax3.annotate(f"{row.assembly_ms:.1f}", (xpos + 0.16, row.assembly_ms), xytext=(0, 5), textcoords="offset points",
                     ha="center", fontsize=8)
    ax3.set_xticks(x)
    ax3.set_xticklabels([human_algorithm_name(row.algorithm) for row in best_rows])
    ax3.set_yscale("log")
    ax3.set_title("最佳线程下的预处理/组装耗时")
    ax3.legend()
    ax3.grid(True, axis="y")

    for algorithm, rows in sorted(algo_groups.items()):
        xs = [row.threads for row in rows]
        ys = [row.efficiency * 100.0 for row in rows]
        color = ALGO_COLORS.get(algorithm, "#334155")
        ax4.plot(xs, ys, marker="o", linewidth=2.0, color=color, label=human_algorithm_name(algorithm))
    ax4.axhline(50.0, linestyle="--", linewidth=1.5, color="#ef4444", alpha=0.6, label="50% 阈值")
    ax4.set_title("并行效率曲线")
    ax4.set_xlabel("线程数")
    ax4.set_ylabel("效率 (%)")
    ax4.grid(True)
    ax4.legend(loc="best", framealpha=0.95)

    ax5.axis("off")
    table_rows = [
        [human_algorithm_name(row.algorithm), row.threads, f"{row.assembly_ms:.1f}", f"{row.speedup:.2f}x",
         f"{row.efficiency * 100.0:.1f}%", f"{bytes_to_gib(row.extra_memory_bytes):.2f}"]
        for row in best_rows
    ]
    table = ax5.table(
        cellText=table_rows,
        colLabels=["算法", "最佳线程", "组装时间 (ms)", "加速比", "效率", "额外内存 (GiB)"],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)
    for (row_idx, col_idx), cell in table.get_celld().items():
        if row_idx == 0:
            cell.set_facecolor("#1d4ed8")
            cell.set_text_props(color="white", weight="bold")
        elif row_idx % 2 == 1:
            cell.set_facecolor("#eff6ff")
        else:
            cell.set_facecolor("#f8fafc")

    fig.suptitle(f"CPU 并行装配综合看板 / Benchmark Dashboard\n{case_title(dataset)}", fontsize=16, fontweight="bold")
    save_figure(fig, out_dir / f"{dataset_slug(dataset)}_dashboard")


def plot_case_or_kernel_comparison(records: list[Record], out_dir: Path, mode: str) -> None:
    if mode == "case":
        labels = sorted({record.case_name for record in records})
        title = "不同算例的最佳加速比对比 / Case Comparison"
        selector = lambda record: record.case_name
        filename = "cross_case_best_speedup"
    else:
        labels = sorted({record.kernel for record in records})
        title = "不同 kernel 的最佳加速比对比 / Kernel Comparison"
        selector = lambda record: record.kernel
        filename = "cross_kernel_best_speedup"

    algorithms = sorted({record.algorithm for record in records if record.status == "PASS"})
    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = np.arange(len(labels))
    width = 0.12 if algorithms else 0.2
    for index, algorithm in enumerate(algorithms):
        best_values = []
        for label in labels:
            matched = [record for record in records if record.algorithm == algorithm and selector(record) == label and record.status == "PASS"]
            best_values.append(max((record.speedup for record in matched), default=0.0))
        offset = (index - (len(algorithms) - 1) / 2.0) * width
        bars = ax.bar(x + offset, best_values, width=width, color=ALGO_COLORS.get(algorithm, "#334155"),
                      label=human_algorithm_name(algorithm), edgecolor="white")
        for bar, value in zip(bars, best_values):
            if value <= 0:
                continue
            ax.annotate(f"{value:.2f}x", (bar.get_x() + bar.get_width() / 2, value), xytext=(0, 5),
                        textcoords="offset points", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("最佳加速比")
    ax.set_title(title)
    ax.grid(True, axis="y")
    ax.legend(loc="best", framealpha=0.95)
    save_figure(fig, out_dir / filename)


def write_summary(records: list[Record], out_dir: Path) -> Path:
    out_path = out_dir / "summary.md"
    grouped = group_by_dataset(records)
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write("# CPU 并行整体刚度矩阵组装实验摘要\n\n")
        for dataset, dataset_records in sorted(grouped.items()):
            passed = pass_records(dataset_records)
            handle.write(f"## {dataset[0]} | kernel={dataset[1]}\n\n")
            if not passed:
                handle.write("没有可用的 PASS 结果。\n\n")
                continue
            fastest = min(passed, key=lambda row: row.assembly_ms)
            non_serial = [row for row in passed if row.algorithm != "cpu_serial"]
            best_speedup = max(non_serial, key=lambda row: row.speedup) if non_serial else fastest
            lowest_memory = min(passed, key=lambda row: row.extra_memory_bytes)
            handle.write(f"- 最快组装：`{fastest.algorithm}` @ `{fastest.threads}` 线程，`{fastest.assembly_ms:.3f} ms`\n")
            handle.write(f"- 最高加速比：`{best_speedup.algorithm}` @ `{best_speedup.threads}` 线程，`{best_speedup.speedup:.3f}x`\n")
            handle.write(f"- 最省额外内存：`{lowest_memory.algorithm}`，`{bytes_to_gib(lowest_memory.extra_memory_bytes):.3f} GiB`\n\n")
            handle.write("| 算法 | 线程 | 组装时间 (ms) | 总时间 (ms) | 加速比 | 效率 | 额外内存 (GiB) | 误差 rel_l2 | 状态 |\n")
            handle.write("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |\n")
            for row in sorted(dataset_records, key=lambda item: (item.algorithm, item.threads)):
                handle.write(
                    f"| {row.algorithm} | {row.threads} | {row.assembly_ms:.3f} | {row.total_ms:.3f} | "
                    f"{row.speedup:.3f} | {row.efficiency * 100.0:.1f}% | {bytes_to_gib(row.extra_memory_bytes):.3f} | "
                    f"{row.rel_l2:.3e} | {row.status} |\n"
                )
            skipped = [row for row in dataset_records if row.status != "PASS"]
            if skipped:
                handle.write("\n### 跳过/失败记录\n\n")
                handle.write("| 算法 | 线程 | 状态 | 原因 |\n")
                handle.write("| --- | ---: | --- | --- |\n")
                for row in skipped:
                    handle.write(f"| {row.algorithm} | {row.threads} | {row.status} | {row.skip_reason or row.diagnostics} |\n")
            handle.write("\n")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, nargs="+", help="一个或多个 benchmark CSV 文件")
    parser.add_argument("--out-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args()

    records = load_records(args.csv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    grouped = group_by_dataset(records)

    for dataset, dataset_records in sorted(grouped.items()):
        passed = pass_records(dataset_records)
        if not passed:
            continue
        plot_metric_vs_threads(passed, dataset, "assembly_ms", "组装时间 (ms，log)", args.out_dir,
                               "执行时间对比 / Assembly Time", reference_line=None)
        plot_metric_vs_threads(passed, dataset, "total_ms", "总时间 (ms，log)", args.out_dir,
                               "总时间对比 / Total Time", reference_line=None)
        plot_metric_vs_threads(passed, dataset, "speedup", "相对 1 线程串行基线的加速比", args.out_dir,
                               "加速比曲线 / Speedup", reference_line=1.0)
        plot_metric_vs_threads(passed, dataset, "efficiency", "并行效率 (%)", args.out_dir,
                               "并行效率 / Efficiency", percent=True, reference_line=50.0)
        plot_stage_breakdown(passed, dataset, args.out_dir)
        plot_extra_memory(passed, dataset, args.out_dir)
        plot_dashboard(passed, dataset, args.out_dir)

    if len({record.case_name for record in records}) > 1:
        plot_case_or_kernel_comparison(records, args.out_dir, mode="case")
    if len({record.kernel for record in records}) > 1:
        plot_case_or_kernel_comparison(records, args.out_dir, mode="kernel")

    summary_path = write_summary(records, args.out_dir)
    print(f"[OK] Figures and summary saved to: {args.out_dir}")
    print(f"[OK] Markdown summary: {summary_path}")


if __name__ == "__main__":
    main()
