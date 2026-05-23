#!/usr/bin/env python3
"""Generate presentation-ready CPU benchmark figures and summaries."""
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

from benchmark_figure_style import (
    ALGO_COLORS,
    ALGORITHM_ORDER,
    INK,
    MUTED,
    PANEL,
    STAGE_COLORS,
    add_baseline,
    add_panel_label,
    algo_label,
    annotate_point,
    apply_presentation_style,
    format_gib,
    format_ms,
    format_ratio,
    label_line_end,
    save_figure as save_styled_figure,
    set_slide_title,
    style_axis,
)


apply_presentation_style()


ALGO_LABELS = {
    "cpu_serial": "Serial",
    "cpu_atomic": "Atomic",
    "cpu_lock_guard": "Lock Guard",
    "cpu_private_csr": "Private CSR",
    "cpu_coo_sort_reduce": "COO Sort-Reduce",
    "cpu_graph_coloring": "Coloring",
    "cpu_row_owner": "Row Owner",
}

STAGE_KEYS = [
    ("prepare_allocate_ms", "Allocation"),
    ("prepare_coloring_ms", "Coloring prep"),
    ("prepare_owner_partition_ms", "Owner partition"),
    ("assembly_zero_ms", "Zeroing"),
    ("assembly_generate_ms", "Element generation"),
    ("assembly_numeric_ms", "Numeric assembly"),
    ("assembly_merge_ms", "Thread merge"),
    ("assembly_sort_ms", "Sort"),
    ("assembly_reduce_ms", "Reduce"),
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
                    kernel=row.get("stiffness_model") or row["kernel"],
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
    return ALGO_LABELS.get(algorithm, algo_label(algorithm))


def best_metric_point(rows: list[Record], metric: str, percent: bool = False) -> tuple[int, float]:
    if metric in {"assembly_ms", "total_ms"}:
        best = min(rows, key=lambda row: getattr(row, metric))
    else:
        best = max(rows, key=lambda row: getattr(row, metric))
    value = getattr(best, metric) * (100.0 if percent else 1.0)
    return best.threads, value


def save_figure(fig: plt.Figure, out_base: Path) -> None:
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    save_styled_figure(fig, out_base)
    plt.close(fig)


def case_title(dataset: tuple[str, str]) -> str:
    case_name, kernel = dataset
    return f"{case_name} | stiffness_model={kernel}"


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
    fig, ax = plt.subplots(figsize=(13.4, 7.5))
    ordered_groups = {
        algorithm: per_dataset_groups(records)[algorithm]
        for algorithm in ALGORITHM_ORDER
        if algorithm in per_dataset_groups(records)
    }
    for algorithm, rows in ordered_groups.items():
        xs = [row.threads for row in rows]
        ys = [getattr(row, metric) * (100.0 if percent else 1.0) for row in rows]
        color = ALGO_COLORS.get(algorithm, "#334155")
        ax.plot(xs, ys, marker="o", linewidth=3.0, markersize=7.5, color=color, label=human_algorithm_name(algorithm))
        if xs and ys:
            label_line_end(ax, xs[-1], ys[-1], human_algorithm_name(algorithm), color=color)
            best_x, best_y = best_metric_point(rows, metric, percent)
            if metric in {"assembly_ms", "total_ms"}:
                label = f"best {format_ms(best_y)} @ {best_x}T"
            elif metric == "efficiency":
                label = f"best {best_y:.0f}% @ {best_x}T"
            else:
                label = f"best {format_ratio(best_y)} @ {best_x}T"
            annotate_point(ax, best_x, best_y, label, color=color)
    if metric in {"assembly_ms", "total_ms"}:
        ax.set_yscale("log")
    if reference_line is not None:
        add_baseline(ax, reference_line, "reference")
    ax.set_xlabel("Threads")
    ax.set_ylabel(ylabel)
    style_axis(ax, grid_axis="both", title=title_prefix)
    set_slide_title(fig, f"{title_prefix}: {case_title(dataset)}", "Best points are highlighted; raw values are unchanged.")
    save_figure(fig, out_dir / f"{dataset_slug(dataset)}_{metric}")


def plot_stage_breakdown(records: list[Record], dataset: tuple[str, str], out_dir: Path) -> None:
    selected = best_rows_by_algorithm(records)
    fig, ax = plt.subplots(figsize=(13.4, 7.5))
    y = np.arange(len(selected))
    cumulative = np.zeros(len(selected))
    for idx, (key, stage_label) in enumerate(STAGE_KEYS):
        heights = np.array([row.stages.get(key, 0.0) for row in selected], dtype=float)
        if np.allclose(heights, 0.0):
            continue
        ax.barh(y, heights, left=cumulative, color=STAGE_COLORS[idx % len(STAGE_COLORS)], label=stage_label, edgecolor="white")
        cumulative += heights
    for ypos, row, total in zip(y, selected, cumulative):
        ax.annotate(
            f"{format_ms(row.assembly_ms)} @ {row.threads}T",
            (total, ypos),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels([human_algorithm_name(row.algorithm) for row in selected])
    ax.set_xlabel("Stage time (ms)")
    style_axis(ax, grid_axis="x", title="Best-thread stage composition")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
    set_slide_title(fig, f"Stage Breakdown: {case_title(dataset)}", "Horizontal stacked bars compare each algorithm at its fastest assembly point.")
    save_figure(fig, out_dir / f"{dataset_slug(dataset)}_stage_breakdown")


def plot_extra_memory(records: list[Record], dataset: tuple[str, str], out_dir: Path) -> None:
    selected = best_rows_by_algorithm(records)
    fig, ax = plt.subplots(figsize=(13.4, 7.5))
    y = np.arange(len(selected))
    values = [bytes_to_gib(row.extra_memory_bytes) for row in selected]
    colors = [ALGO_COLORS.get(row.algorithm, "#334155") for row in selected]
    bars = ax.barh(y, values, color=colors, edgecolor="white")
    for bar, row, value in zip(bars, selected, values):
        ax.annotate(
            f"{format_gib(value)} @ {row.threads}T",
            (bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=10,
            fontweight="bold",
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels([human_algorithm_name(row.algorithm) for row in selected])
    ax.set_xlabel("Extra memory (GiB)")
    style_axis(ax, grid_axis="x", title="Extra memory at fastest assembly point")
    set_slide_title(fig, f"Memory Footprint: {case_title(dataset)}", "Bars use each algorithm's fastest PASS row.")
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

    fig = plt.figure(figsize=(15.8, 9.2))
    grid = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 0.7])
    ax1 = fig.add_subplot(grid[0, 0])
    ax2 = fig.add_subplot(grid[0, 1])
    ax3 = fig.add_subplot(grid[1, 0])
    ax4 = fig.add_subplot(grid[1, 1])
    ax5 = fig.add_subplot(grid[2, :])

    log_time = np.log10(np.where(np.isnan(time_matrix), np.nan, np.maximum(time_matrix, 1.0e-9)))
    im1 = ax1.imshow(log_time, cmap="magma_r", aspect="auto")
    style_axis(ax1, grid_axis="none", title="Assembly time heatmap (log10 ms)")
    add_panel_label(ax1, "A")
    ax1.set_xticks(range(len(threads)))
    ax1.set_xticklabels(threads)
    ax1.set_yticks(range(len(algorithms)))
    ax1.set_yticklabels([human_algorithm_name(name) for name in algorithms])
    for i in range(len(algorithms)):
        for j in range(len(threads)):
            value = time_matrix[i, j]
            if math.isnan(value):
                continue
            ax1.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=8, fontweight="bold", color=INK)
    fig.colorbar(im1, ax=ax1, fraction=0.046)

    im2 = ax2.imshow(speedup_matrix, cmap="viridis", aspect="auto")
    style_axis(ax2, grid_axis="none", title="Speedup heatmap")
    add_panel_label(ax2, "B")
    ax2.set_xticks(range(len(threads)))
    ax2.set_xticklabels(threads)
    ax2.set_yticks(range(len(algorithms)))
    ax2.set_yticklabels([human_algorithm_name(name) for name in algorithms])
    for i in range(len(algorithms)):
        for j in range(len(threads)):
            value = speedup_matrix[i, j]
            if math.isnan(value):
                continue
            ax2.text(j, i, f"{value:.2f}x", ha="center", va="center", fontsize=8, fontweight="bold", color="white" if value > np.nanmax(speedup_matrix) * 0.55 else INK)
    fig.colorbar(im2, ax=ax2, fraction=0.046)

    best_rows = best_rows_by_algorithm(records)
    x = np.arange(len(best_rows))
    ax3.bar(x - 0.16, [row.preprocess_ms for row in best_rows], width=0.32, color="#64748b", label="Preprocess")
    ax3.bar(x + 0.16, [row.assembly_ms for row in best_rows], width=0.32, color="#2563eb", label="Assembly")
    for xpos, row in zip(x, best_rows):
        ax3.annotate(format_ms(row.assembly_ms), (xpos + 0.16, row.assembly_ms), xytext=(0, 5), textcoords="offset points",
                     ha="center", fontsize=8.5, fontweight="bold")
    ax3.set_xticks(x)
    ax3.set_xticklabels([human_algorithm_name(row.algorithm) for row in best_rows])
    ax3.set_yscale("log")
    style_axis(ax3, title="Preprocess vs assembly at best thread")
    add_panel_label(ax3, "C")
    ax3.legend(frameon=False)

    for algorithm in [name for name in ALGORITHM_ORDER if name in algo_groups]:
        rows = algo_groups[algorithm]
        xs = [row.threads for row in rows]
        ys = [row.efficiency * 100.0 for row in rows]
        color = ALGO_COLORS.get(algorithm, "#334155")
        ax4.plot(xs, ys, marker="o", linewidth=2.6, color=color, label=human_algorithm_name(algorithm))
    add_baseline(ax4, 50.0, "50%")
    style_axis(ax4, grid_axis="both", title="Parallel efficiency")
    add_panel_label(ax4, "D")
    ax4.set_xlabel("Threads")
    ax4.set_ylabel("Efficiency (%)")
    ax4.legend(loc="lower left", frameon=False)

    ax5.axis("off")
    table_rows = [
        [human_algorithm_name(row.algorithm), row.threads, f"{row.assembly_ms:.1f}", f"{row.speedup:.2f}x",
         f"{row.efficiency * 100.0:.1f}%", f"{bytes_to_gib(row.extra_memory_bytes):.2f}"]
        for row in best_rows
    ]
    table = ax5.table(
        cellText=table_rows,
        colLabels=["Algorithm", "Best thread", "Assembly ms", "Speedup", "Efficiency", "Extra GiB"],
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
            cell.set_facecolor(PANEL)

    set_slide_title(fig, f"Benchmark Dashboard: {case_title(dataset)}", "Time, speedup, efficiency, and memory are drawn from PASS rows only.", y=0.995)
    save_figure(fig, out_dir / f"{dataset_slug(dataset)}_dashboard")


def plot_case_or_kernel_comparison(records: list[Record], out_dir: Path, mode: str) -> None:
    if mode == "case":
        labels = sorted({record.case_name for record in records})
        title = "Best Speedup by Case"
        selector = lambda record: record.case_name
        filename = "cross_case_best_speedup"
    else:
        labels = sorted({record.kernel for record in records})
        title = "Best Speedup by Kernel"
        selector = lambda record: record.kernel
        filename = "cross_kernel_best_speedup"

    algorithms = [algorithm for algorithm in ALGORITHM_ORDER if any(record.algorithm == algorithm and record.status == "PASS" for record in records)]
    fig, ax = plt.subplots(figsize=(13.4, 7.5))
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
            ax.annotate(format_ratio(value), (bar.get_x() + bar.get_width() / 2, value), xytext=(0, 6),
                        textcoords="offset points", ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Best speedup vs serial")
    add_baseline(ax, 1.0, "serial")
    style_axis(ax, title=title)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=min(3, max(1, len(algorithms))), frameon=False)
    set_slide_title(fig, title, "Each bar is the best PASS speedup observed for the group.")
    save_figure(fig, out_dir / filename)


def write_summary(records: list[Record], out_dir: Path) -> Path:
    out_path = out_dir / "summary.md"
    grouped = group_by_dataset(records)
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write("# CPU Stiffness Assembly Benchmark Figure Summary\n\n")
        handle.write("Figures in this directory were redrawn in presentation style from existing CSV benchmark results. No benchmark data was rerun.\n\n")
        for dataset, dataset_records in sorted(grouped.items()):
            passed = pass_records(dataset_records)
            handle.write(f"## {dataset[0]} | stiffness_model={dataset[1]}\n\n")
            if not passed:
                handle.write("No PASS records are available.\n\n")
                continue
            fastest = min(passed, key=lambda row: row.assembly_ms)
            non_serial = [row for row in passed if row.algorithm != "cpu_serial"]
            best_speedup = max(non_serial, key=lambda row: row.speedup) if non_serial else fastest
            lowest_memory = min(passed, key=lambda row: row.extra_memory_bytes)
            handle.write(f"- Fastest assembly: `{fastest.algorithm}` @ `{fastest.threads}` threads, `{fastest.assembly_ms:.3f} ms`\n")
            handle.write(f"- Highest speedup: `{best_speedup.algorithm}` @ `{best_speedup.threads}` threads, `{best_speedup.speedup:.3f}x`\n")
            handle.write(f"- Lowest extra memory: `{lowest_memory.algorithm}`, `{bytes_to_gib(lowest_memory.extra_memory_bytes):.3f} GiB`\n\n")
            handle.write("| Algorithm | Threads | Assembly ms | Total ms | Speedup | Efficiency | Extra GiB | rel_l2 | Status |\n")
            handle.write("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |\n")
            for row in sorted(dataset_records, key=lambda item: (item.algorithm, item.threads)):
                handle.write(
                    f"| {row.algorithm} | {row.threads} | {row.assembly_ms:.3f} | {row.total_ms:.3f} | "
                    f"{row.speedup:.3f} | {row.efficiency * 100.0:.1f}% | {bytes_to_gib(row.extra_memory_bytes):.3f} | "
                    f"{row.rel_l2:.3e} | {row.status} |\n"
                )
            skipped = [row for row in dataset_records if row.status != "PASS"]
            if skipped:
                handle.write("\n### Skipped or failed records\n\n")
                handle.write("| Algorithm | Threads | Status | Reason |\n")
                handle.write("| --- | ---: | --- | --- |\n")
                for row in skipped:
                    handle.write(f"| {row.algorithm} | {row.threads} | {row.status} | {row.skip_reason or row.diagnostics} |\n")
            handle.write("\n")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, nargs="+", help="one or more benchmark CSV files")
    parser.add_argument("--out-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args()

    records = load_records(args.csv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    grouped = group_by_dataset(records)

    for dataset, dataset_records in sorted(grouped.items()):
        passed = pass_records(dataset_records)
        if not passed:
            continue
        plot_metric_vs_threads(passed, dataset, "assembly_ms", "Assembly time (ms, log)", args.out_dir,
                               "Assembly Time", reference_line=None)
        plot_metric_vs_threads(passed, dataset, "total_ms", "Total time (ms, log)", args.out_dir,
                               "Total Time", reference_line=None)
        plot_metric_vs_threads(passed, dataset, "speedup", "Speedup vs serial baseline", args.out_dir,
                               "Speedup", reference_line=1.0)
        plot_metric_vs_threads(passed, dataset, "efficiency", "Parallel efficiency (%)", args.out_dir,
                               "Parallel Efficiency", percent=True, reference_line=50.0)
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
