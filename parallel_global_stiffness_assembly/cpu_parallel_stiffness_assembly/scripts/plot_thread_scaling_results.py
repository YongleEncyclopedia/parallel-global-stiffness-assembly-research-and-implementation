#!/usr/bin/env python3
"""Generate presentation-ready thread-scaling benchmark figures."""
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

from benchmark_figure_style import (
    ALGO_COLORS,
    ENV_COLORS,
    INK,
    MUTED,
    PANEL,
    STAGE_COLORS,
    THREAD_ALGORITHM_ORDER,
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


ALGORITHM_ORDER = [
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
]

ENV_ORDER = ["default", "bound"]

ALGO_LABELS = {name: algo_label(name) for name in THREAD_ALGORITHM_ORDER}
ALGO_SHORT = ALGO_LABELS

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
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    save_styled_figure(fig, out_base)
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
            label = f"{row.threads}T\n{format_ms(value)}"
        elif metric == "speedup":
            value = row.speedup
            label = f"{row.threads}T\n{format_ratio(value)}"
        elif metric == "efficiency":
            value = row.efficiency * 100.0
            label = f"{row.threads}T\n{value:.1f}%"
        else:
            value = memory_gib(row)
            label = f"{row.threads}T\n{format_gib(value)}"
        annotate_point(ax, row.threads, value, label)


def plot_algorithm_detail(records: list[ThreadScalingRecord], algorithm: str, out_dir: Path) -> Path:
    grouped = records_by_env_algorithm(records)
    algo_records = [record for record in records if record.algorithm == algorithm]
    physical = physical_cores(algo_records)
    max_thread = max(record.threads for record in algo_records)
    fig, axes = plt.subplots(3, 1, figsize=(13.4, 10.2), sharex=True)
    metrics = [
        ("assembly_ms", "Assembly time (ms, log)", "Assembly Time"),
        ("speedup", "Speedup vs serial baseline", "Speedup"),
        ("efficiency", "Parallel efficiency (%)", "Efficiency"),
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
            if xs and ys:
                label_line_end(ax, xs[-1], ys[-1], env_group, color=ENV_COLORS[env_group])
        if metric == "assembly_ms":
            ax.set_yscale("log")
        ax.set_ylabel(ylabel)
        style_axis(ax, grid_axis="both", title=f"{title} | {ALGO_SHORT[algorithm]}")
    axes[-1].set_xlabel("Threads")
    axes[-1].set_xticks(list(range(1, max_thread + 1)))
    set_slide_title(fig, f"Thread Scaling Detail: {ALGO_LABELS[algorithm]}", "Only default and bound environments are compared; key points are annotated.")
    out_base = out_dir / f"thread_scaling_by_algorithm_{algorithm}"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def plot_env_dashboard(records: list[ThreadScalingRecord], env_group: str, out_dir: Path) -> Path:
    env_records = [record for record in records if record.env_group == env_group]
    grouped = records_by_env_algorithm(env_records)
    physical = physical_cores(env_records)
    max_thread = max(record.threads for record in env_records)
    fig = plt.figure(figsize=(16, 9.4))
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
        if xs:
            label_line_end(ax_time, xs[-1], rows[-1].assembly_ms, ALGO_SHORT[algorithm], color=color)
            label_line_end(ax_speedup, xs[-1], rows[-1].speedup, ALGO_SHORT[algorithm], color=color)
            label_line_end(ax_eff, xs[-1], rows[-1].efficiency * 100.0, ALGO_SHORT[algorithm], color=color)
            label_line_end(ax_mem, xs[-1], memory_gib(rows[-1]), ALGO_SHORT[algorithm], color=color)

    ax_time.set_yscale("log")
    ax_time.set_title("Assembly time (log ms)")
    ax_time.set_ylabel("ms")
    ax_speedup.set_title("Speedup")
    ax_speedup.set_ylabel("x")
    ax_eff.set_title("Parallel efficiency")
    ax_eff.set_ylabel("%")
    ax_mem.set_title("Extra memory")
    ax_mem.set_ylabel("GiB")
    for idx, ax in enumerate((ax_time, ax_speedup, ax_eff, ax_mem), start=1):
        style_axis(ax, grid_axis="both")
        add_panel_label(ax, chr(ord("A") + idx - 1))
        ax.set_xlabel("Threads")
        ax.set_xticks(list(range(1, max_thread + 1, 2)))

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
                trend = "faster"
            elif best_beyond.assembly_ms > best_physical.assembly_ms * 1.05:
                trend = "slower"
            else:
                trend = "flat"
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
    ax_bars.bar(x - width / 2, physical_values, width=width, color="#0f766e", label="Best within physical cores")
    ax_bars.bar(x + width / 2, beyond_values, width=width, color="#ea580c", label="Best oversubscription")
    for xpos, physical_value, beyond_value in zip(x, physical_values, beyond_values):
        ax_bars.annotate(format_ms(physical_value), (xpos - width / 2, physical_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8.5)
        ax_bars.annotate(format_ms(beyond_value), (xpos + width / 2, beyond_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8.5)
    ax_bars.set_xticks(x)
    ax_bars.set_xticklabels([ALGO_SHORT[name] for name in ALGORITHM_ORDER], rotation=10)
    ax_bars.set_ylabel("Assembly time (ms)")
    style_axis(ax_bars, title="Physical-core best vs oversubscription best")
    ax_bars.legend(loc="best", frameon=False)

    ax_table.axis("off")
    table = ax_table.table(
        cellText=table_rows,
        colLabels=["Algorithm", "Best thread", "Best ms", "Speedup", "Oversub trend"],
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
            cell.set_facecolor(PANEL)
    ax_table.set_title("Best-point summary")

    set_slide_title(fig, f"Thread Scaling Dashboard: {env_group}", "Large panels show scaling behavior; the lower panels summarize the fastest assembly points.", y=0.995)
    out_base = out_dir / f"thread_scaling_{env_group}_dashboard"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def plot_memory_by_env(records: list[ThreadScalingRecord], out_dir: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13.4, 7.5), sharey=True)
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
            if rows:
                label_line_end(ax, rows[-1].threads, memory_gib(rows[-1]), ALGO_SHORT[algorithm], color=ALGO_COLORS[algorithm])
        style_axis(ax, grid_axis="both", title=f"{env_group}: extra memory by thread")
        ax.set_xlabel("Threads")
        ax.set_xticks(list(range(1, max_thread + 1, 2)))
    axes[0].set_ylabel("Extra memory (GiB)")
    set_slide_title(fig, "Extra Memory by Environment", "Private CSR memory growth is shown directly against thread count.")
    out_base = out_dir / "thread_scaling_memory_by_env"
    save_figure(fig, out_base)
    return out_base.with_suffix(".png")


def plot_physical_vs_oversubscription(records: list[ThreadScalingRecord], out_dir: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13.4, 7.5), sharey=True)
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
                    trend_labels.append("faster")
                elif ratio > 1.05:
                    trend_labels.append("slower")
                else:
                    trend_labels.append("flat")
            else:
                trend_labels.append("n/a")
        ax.bar(x - width / 2, physical_values, width=width, color="#0f766e", label="Best within physical cores")
        ax.bar(x + width / 2, beyond_values, width=width, color="#ea580c", label="Best oversubscription")
        for xpos, physical_value, beyond_value, trend in zip(x, physical_values, beyond_values, trend_labels):
            ax.annotate(format_ms(physical_value), (xpos - width / 2, physical_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")
            ax.annotate(f"{format_ms(beyond_value)}\n{trend}", (xpos + width / 2, beyond_value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([ALGO_SHORT[name] for name in ALGORITHM_ORDER], rotation=10)
        style_axis(ax, title=f"{env_group}: physical-core best vs oversubscription best")
        ax.set_ylabel("Assembly time (ms, lower is better)")
        ax.legend(loc="best", frameon=False)
    set_slide_title(fig, "Physical Cores vs Oversubscription", "Lower bars mean faster assembly; trend labels compare oversubscription to the physical-core best.")
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
    fig, ax = plt.subplots(figsize=(13.4, 7.5))
    y = np.arange(len(selected))
    cumulative = np.zeros(len(selected))
    for idx, (_key, label) in enumerate(STAGE_KEYS):
        heights = np.array([stage_values(row)[idx] for row in selected], dtype=float)
        if np.allclose(heights, 0.0):
            continue
        ax.barh(y, heights, left=cumulative, color=STAGE_COLORS[idx % len(STAGE_COLORS)], edgecolor="white", label=label)
        cumulative += heights
    for ypos, row, total in zip(y, selected, cumulative):
        label_y = total if total > 0 else row.assembly_ms
        ax.annotate(
            f"{row.threads}T, {format_ms(row.assembly_ms)}",
            (label_y, ypos),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=8.8,
            fontweight="bold",
        )
    ax.set_yticks(y)
    ax.set_yticklabels([f"{row.env_group} | {ALGO_SHORT[row.algorithm]}" for row in selected])
    ax.set_xlabel("Stage time (ms)")
    style_axis(ax, grid_axis="x", title="Stage breakdown at best thread")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=3, frameon=False)
    set_slide_title(fig, "Best-Point Stage Breakdown", "Each row uses the fastest PASS thread count for one environment and algorithm.")
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
    fig.suptitle("Thread Scaling Figure Contact Sheet", fontsize=18, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = out_dir / "thread_scaling_contact_sheet.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_figures_summary(out_dir: Path, image_paths: list[Path]) -> Path:
    descriptions = {
        "thread_scaling_default_dashboard": "Default-environment timing, speedup, efficiency, memory, and best-point summary.",
        "thread_scaling_bound_dashboard": "Bound-environment timing, speedup, efficiency, memory, and best-point summary.",
        "thread_scaling_memory_by_env": "Extra memory across thread counts in default and bound environments.",
        "thread_scaling_physical_vs_oversubscription": "Direct comparison of the best physical-core and oversubscription assembly times.",
        "thread_scaling_stage_breakdown_best": "Stage composition at each environment and algorithm best thread count.",
        "thread_scaling_contact_sheet": "Thumbnail overview for visual QA.",
    }
    path = out_dir / "summary.md"
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Thread Scaling Figures Summary\n\n")
        handle.write("Figures in this directory were redrawn in presentation style from existing CSV benchmark results. PNG files are for Markdown viewing; SVG files keep editable text for inspection and slide reuse.\n\n")
        handle.write("| Figure | PNG | SVG | Purpose |\n")
        handle.write("| --- | --- | --- | --- |\n")
        for image_path in image_paths:
            if image_path.name == "thread_scaling_contact_sheet.png":
                stem = image_path.stem
                svg_text = "-"
            else:
                stem = image_path.stem
                svg_text = f"[svg]({stem}.svg)"
            description = descriptions.get(stem, "Single-algorithm default/bound thread-scaling detail.")
            handle.write(f"| `{stem}` | [png]({image_path.name}) | {svg_text} | {description} |\n")
    return path


def figure_block() -> str:
    return """<!-- thread-scaling-figures:start -->
## Presentation Figures

Core benchmark figures are stored in `figures/`. PNG files are embedded for Markdown viewing; SVG files are kept for editable, high-resolution inspection.

### Key Comparisons and Bottlenecks

![physical vs oversubscription](figures/thread_scaling_physical_vs_oversubscription.png)

[physical vs oversubscription SVG](figures/thread_scaling_physical_vs_oversubscription.svg)

![extra memory by environment](figures/thread_scaling_memory_by_env.png)

[extra memory by environment SVG](figures/thread_scaling_memory_by_env.svg)

![stage breakdown best](figures/thread_scaling_stage_breakdown_best.png)

[stage breakdown best SVG](figures/thread_scaling_stage_breakdown_best.svg)

The complete figure index is available at [figures/summary.md](figures/summary.md).

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
