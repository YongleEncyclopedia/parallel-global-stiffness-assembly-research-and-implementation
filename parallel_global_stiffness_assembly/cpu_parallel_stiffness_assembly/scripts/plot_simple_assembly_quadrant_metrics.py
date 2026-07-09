#!/usr/bin/env python3
"""Draw compact platform-specific bar charts for assembly quadrant metrics."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[3]
CPU_ROOT = REPO_ROOT / "parallel_global_stiffness_assembly" / "cpu_parallel_stiffness_assembly"
REPORT_DIR = CPU_ROOT / "reports" / "2026-06-16-simple-assembly-quadrant-metrics"
SOURCE_CSV = REPORT_DIR / "source_data" / "assembly_quadrant_metric_rows.csv"
ASSET_DIR = REPORT_DIR / "assets"

PLATFORM_ORDER = ["macos_m4max", "linux_intel", "windows_amd"]

PLATFORM_SUBTITLES = {
    "macos_m4max": "风机轮毂工程网格 · 四面体单元 · macOS · Apple M4 Max",
    "linux_intel": "风机轮毂工程网格 · 四面体单元 · Linux · Intel Core Ultra 7 265KF",
    "windows_amd": "风机轮毂工程网格 · 四面体单元 · Windows · AMD Ryzen 7 9800X3D",
}

PARALLEL_CONFIG = {
    "macos_m4max": "14 线程",
    "linux_intel": "20 线程",
    "windows_amd": "8 线程",
}

MEMORY_NOTE = {
    "macos_m4max": "预估值",
    "linux_intel": "隔离进程实测峰值",
    "windows_amd": "进程实测峰值",
}

STRATEGY_ORDER = [
    "serial_direct",
    "serial_symbolic",
    "parallel_direct",
    "parallel_symbolic",
]

STRATEGY_LABELS = {
    "serial_direct": "Q1\n串行直接",
    "serial_symbolic": "Q2\n串行两阶段",
    "parallel_direct": "Q3\n并行直接",
    "parallel_symbolic": "Q4\n并行两阶段",
}

STRATEGY_COLORS = {
    "serial_direct": "#D92D20",
    "serial_symbolic": "#155CC0",
    "parallel_direct": "#F06A00",
    "parallel_symbolic": "#76B900",
}

TEXT_DARK = "#111111"
TEXT_MID = "#4F565C"
TEXT_AXIS = "#5A6268"
GRID = "#DCDCDC"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": [
            "PingFang SC",
            "Hiragino Sans GB",
            "Heiti SC",
            "Arial Unicode MS",
            "Noto Sans CJK SC",
            "Microsoft YaHei",
            "SimHei",
            "DejaVu Sans",
        ],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": False,
    }
)


def read_rows() -> list[dict[str, str]]:
    with SOURCE_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def strip_dagger(value: str) -> str:
    return value.replace(chr(0x2020), "").strip()


def format_memory(row: dict[str, str]) -> str:
    return f"{float(row['memory_gib']):.2f}"


def add_value_labels(
    ax: plt.Axes,
    bars,
    labels: list[str],
    y_limit: float,
) -> None:
    for bar, label in zip(bars, labels):
        height = bar.get_height()
        y = min(height + y_limit * 0.025, y_limit * 0.96)
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            label,
            ha="center",
            va="bottom",
            fontsize=11.2,
            color=TEXT_DARK,
        )


def make_metric(
    title: str,
    hint: str,
    unit: str,
    values: list[float],
    labels: list[str],
    y_limit: float,
    yticks: list[float],
) -> dict[str, object]:
    return {
        "title": title,
        "hint": hint,
        "unit": unit,
        "values": values,
        "labels": labels,
        "y_limit": y_limit,
        "yticks": yticks,
    }


def format_axis(ax: plt.Axes, xtick_labels: list[str], ylabel: str) -> None:
    ax.set_xticks(range(len(xtick_labels)))
    ax.set_xticklabels(xtick_labels, fontsize=10.6, linespacing=1.15)
    ax.set_ylabel(ylabel, fontsize=13, labelpad=8, fontweight="bold")
    ax.tick_params(axis="x", length=0, pad=9)
    ax.tick_params(axis="y", labelsize=10.5, colors=TEXT_AXIS)
    ax.grid(axis="y", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)


def add_panel_title(ax: plt.Axes, title: str, hint: str) -> None:
    ax.text(
        0.0,
        1.08,
        title,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=16.5,
        fontweight="bold",
        color=TEXT_DARK,
    )
    ax.text(
        1.0,
        1.08,
        hint,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=11,
        color=TEXT_AXIS,
    )


def draw_metric_panel(
    ax: plt.Axes,
    x: list[int],
    colors: list[str],
    x_labels: list[str],
    metric: dict[str, object],
) -> None:
    values = metric["values"]
    bars = ax.bar(x, values, width=0.62, color=colors, edgecolor="none")
    ax.set_ylim(0, metric["y_limit"])
    ax.set_yticks(metric["yticks"])
    format_axis(ax, x_labels, metric["unit"])
    add_panel_title(ax, metric["title"], metric["hint"])
    add_value_labels(ax, bars, metric["labels"], metric["y_limit"])


def draw_platform(platform_key: str, all_rows: list[dict[str, str]]) -> Path:
    rows = [row for row in all_rows if row["platform_key"] == platform_key]
    if len(rows) != 4:
        raise RuntimeError(f"Expected 4 rows for {platform_key}, found {len(rows)}")

    rows_by_strategy = {row["strategy_key"]: row for row in rows}
    ordered = [rows_by_strategy[key] for key in STRATEGY_ORDER]

    x = list(range(len(ordered)))
    colors = [STRATEGY_COLORS[row["strategy_key"]] for row in ordered]
    x_labels = [STRATEGY_LABELS[row["strategy_key"]] for row in ordered]

    metrics = [
        make_metric(
            "组装耗时",
            "越低越好",
            "秒",
            [float(row["time_s"]) for row in ordered],
            [strip_dagger(row["time_display"]) for row in ordered],
            11.2,
            [0, 2.5, 5.0, 7.5, 10.0],
        ),
        make_metric(
            "内存占用",
            "越低越好",
            "吉字节",
            [float(row["memory_gib"]) for row in ordered],
            [format_memory(row) for row in ordered],
            4.2,
            [0, 1, 2, 3, 4],
        ),
        make_metric(
            "相对加速比",
            "越高越好",
            "倍",
            [float(row["speedup_vs_q1"]) for row in ordered],
            [row["speedup_display"] for row in ordered],
            12.0,
            [0, 3, 6, 9, 12],
        ),
    ]

    fig = plt.figure(figsize=(12.8, 7.2), dpi=240)
    axes = [
        fig.add_axes((0.07, 0.30, 0.27, 0.46)),
        fig.add_axes((0.385, 0.30, 0.27, 0.46)),
        fig.add_axes((0.70, 0.30, 0.27, 0.46)),
    ]

    for ax, metric in zip(axes, metrics):
        draw_metric_panel(ax, x, colors, x_labels, metric)

    fig.text(
        0.055,
        0.91,
        "整体刚度矩阵组装方式对比",
        ha="left",
        va="center",
        fontsize=25,
        fontweight="bold",
        color=TEXT_DARK,
    )
    fig.text(
        0.055,
        0.85,
        PLATFORM_SUBTITLES[platform_key],
        ha="left",
        va="center",
        fontsize=16.5,
        color=TEXT_MID,
    )
    fig.text(
        0.055,
        0.10,
        (
            f"内存：{MEMORY_NOTE[platform_key]}；"
            f"并行配置：{PARALLEL_CONFIG[platform_key]}；"
            "加速比：Q1 串行直接为基线。"
        ),
        ha="left",
        va="center",
        fontsize=14.2,
        color="#202020",
    )

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    out_base = ASSET_DIR / f"fig_{platform_key}_simple_assembly_metrics"
    fig.savefig(out_base.with_suffix(".svg"), facecolor="white")
    fig.savefig(out_base.with_suffix(".pdf"), facecolor="white")
    fig.savefig(out_base.with_suffix(".png"), dpi=240, facecolor="white")
    fig.savefig(out_base.with_suffix(".tiff"), dpi=600, facecolor="white")
    plt.close(fig)
    return out_base.with_suffix(".png")


def main() -> None:
    rows = read_rows()
    for platform_key in PLATFORM_ORDER:
        print(draw_platform(platform_key, rows))


if __name__ == "__main__":
    main()
