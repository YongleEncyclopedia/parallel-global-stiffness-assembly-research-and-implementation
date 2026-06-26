#!/usr/bin/env python3
"""Draw a fixed-thread Chinese comparison chart for numeric assembly backends."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = (
    PROJECT_ROOT
    / "results"
    / "2026-04-28-12charts-repeat3-threads1to14"
    / "csv"
    / "04_windhub_physics_tet4.csv"
)
OUT_ROOT = PROJECT_ROOT / "reports" / "2026-06-24-backend-fixed-thread-metrics"
ASSET_DIR = OUT_ROOT / "assets"
SOURCE_OUT_DIR = OUT_ROOT / "source_data"

FIXED_THREADS = 14
ALGORITHM_ORDER = (
    "cpu_serial",
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_graph_coloring",
    "cpu_row_owner",
)

LABELS = {
    "cpu_serial": "串行基线",
    "cpu_atomic": "原子累加",
    "cpu_private_csr": "线程私有",
    "cpu_graph_coloring": "图着色",
    "cpu_row_owner": "按行分配",
}


def configure_style() -> None:
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
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def read_rows() -> list[dict[str, str]]:
    with SOURCE_FILE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        row
        for row in rows
        if row.get("status") == "PASS"
        and row.get("case_name") == "3d-WindTurbineHub"
        and row.get("kernel") == "physics_tet4"
    ]


def selected_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    serial_rows = [row for row in rows if row.get("algorithm") == "cpu_serial"]
    if not serial_rows:
        raise RuntimeError("Missing serial baseline row")
    serial_row = serial_rows[0]
    serial_total_ms = float(serial_row["total_mean_ms"])

    result: list[dict[str, object]] = []
    for algorithm in ALGORITHM_ORDER:
        if algorithm == "cpu_serial":
            matches = [serial_row]
        else:
            matches = [
                row
                for row in rows
                if row.get("algorithm") == algorithm and int(row["threads"]) == FIXED_THREADS
            ]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one selected {algorithm} row, got {len(matches)}")
        row = matches[0]
        preprocess_ms = float(row["preprocess_ms"])
        numeric_ms = float(row["assembly_mean_ms"])
        total_ms = float(row["total_mean_ms"])
        peak_memory_gib = float(row["peak_rss_mb"]) / 1024
        extra_memory_gib = float(row["extra_memory_bytes"]) / 1024**3
        base_memory_gib = max(0.0, peak_memory_gib - extra_memory_gib)
        result.append(
            {
                "算法": LABELS[algorithm],
                "原始后端": algorithm,
                "线程数": int(row["threads"]),
                "预处理耗时_ms": preprocess_ms,
                "数值组装耗时_ms": numeric_ms,
                "总耗时_ms": total_ms,
                "峰值内存_GiB": peak_memory_gib,
                "基础内存_GiB": base_memory_gib,
                "额外内存_GiB": extra_memory_gib,
                "整体加速比": serial_total_ms / total_ms,
                "串行基线总耗时_ms": serial_total_ms,
                "重复次数": int(row["run_count"]),
                "源文件": SOURCE_FILE.name,
            }
        )
    return result


def write_source_data(rows: list[dict[str, object]]) -> Path:
    SOURCE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SOURCE_OUT_DIR / "backend_fixed_thread_metrics_rows.csv"
    with out_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def add_panel_title(ax, title: str, hint: str) -> None:
    ax.text(
        0.0,
        1.08,
        title,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=17,
        fontweight="bold",
        color="#111111",
    )
    ax.text(
        1.0,
        1.08,
        hint,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=11.5,
        color="#5A6268",
    )


def format_bar_axis(ax, labels: list[str], ylabel: str) -> None:
    ax.set_ylabel(ylabel, fontsize=13, labelpad=8, fontweight="bold")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=11.2, linespacing=1.15)
    ax.tick_params(axis="y", labelsize=10.5, colors="#5A6268")
    ax.tick_params(axis="x", length=0, pad=9)
    ax.grid(axis="y", color="#DCDCDC", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)


def draw(rows: list[dict[str, object]]) -> list[Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    configure_style()

    labels = [str(row["算法"]) for row in rows]
    threads = [int(row["线程数"]) for row in rows]
    peak_memory = [float(row["峰值内存_GiB"]) for row in rows]
    base_memory = [float(row["基础内存_GiB"]) for row in rows]
    extra_memory = [float(row["额外内存_GiB"]) for row in rows]
    preprocess = [float(row["预处理耗时_ms"]) for row in rows]
    numeric = [float(row["数值组装耗时_ms"]) for row in rows]
    total = [float(row["总耗时_ms"]) for row in rows]
    speedups = [float(row["整体加速比"]) for row in rows]

    fig = plt.figure(figsize=(12.8, 7.2), dpi=240)
    green = "#76B900"
    pale_green = "#C8E88B"
    base_grey = "#D9DEE3"
    dark_text = "#202020"

    x = list(range(len(rows)))
    xticks = [f"{label}\n{thread}线程" for label, thread in zip(labels, threads)]

    ax_mem = fig.add_axes((0.07, 0.30, 0.27, 0.46))
    ax_mem.bar(x, base_memory, width=0.64, color=base_grey, edgecolor="none", label="基础内存")
    extra_bars = ax_mem.bar(
        x,
        extra_memory,
        bottom=base_memory,
        width=0.64,
        color=green,
        edgecolor="none",
        label="额外内存",
    )
    ax_mem.set_ylim(0, max(peak_memory) * 1.24 if max(peak_memory) > 0 else 1)
    format_bar_axis(ax_mem, xticks, "吉字节")
    add_panel_title(ax_mem, "峰值内存", "越低越好")
    for idx, value in enumerate(peak_memory):
        ax_mem.text(
            idx,
            value + ax_mem.get_ylim()[1] * 0.025,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=11.2,
            color=dark_text,
        )
    for bar, value in zip(extra_bars, extra_memory):
        if value < 0.12:
            continue
        ax_mem.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_y() + bar.get_height() / 2,
            f"+{value:.2f}",
            ha="center",
            va="center",
            fontsize=9.8,
            color="white",
            fontweight="bold",
        )
    ax_mem.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.01),
        frameon=False,
        fontsize=10.5,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )

    ax_time = fig.add_axes((0.385, 0.30, 0.27, 0.46))
    ax_time.bar(x, numeric, width=0.64, color=green, edgecolor="none", label="数值组装")
    ax_time.bar(x, preprocess, bottom=numeric, width=0.64, color=pale_green, edgecolor="none", label="预处理")
    ax_time.set_ylim(0, max(total) * 1.23)
    format_bar_axis(ax_time, xticks, "毫秒")
    add_panel_title(ax_time, "总耗时", "越低越好")
    for idx, value in enumerate(total):
        ax_time.text(
            idx,
            value + ax_time.get_ylim()[1] * 0.025,
            f"{value:.0f}",
            ha="center",
            va="bottom",
            fontsize=11.2,
            color=dark_text,
        )
    ax_time.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.01),
        frameon=False,
        fontsize=10.5,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )

    ax_speed = fig.add_axes((0.70, 0.30, 0.27, 0.46))
    speed_colors = ["#A3A8AE"] + [green] * (len(rows) - 1)
    speed_bars = ax_speed.bar(x, speedups, width=0.64, color=speed_colors, edgecolor="none")
    ax_speed.set_ylim(0, max(speedups) * 1.22)
    format_bar_axis(ax_speed, xticks, "倍")
    add_panel_title(ax_speed, "整体加速比", "越高越好")
    for bar, value in zip(speed_bars, speedups):
        ax_speed.text(
            bar.get_x() + bar.get_width() / 2,
            value + ax_speed.get_ylim()[1] * 0.025,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=11.2,
            color=dark_text,
        )

    serial_ms = float(rows[0]["串行基线总耗时_ms"])
    fig.text(
        0.055,
        0.91,
        "数值组装后端的内存、耗时与加速比",
        ha="left",
        va="center",
        fontsize=26,
        fontweight="bold",
        color="#111111",
    )
    fig.text(
        0.055,
        0.85,
        f"风机轮毂工程网格 · 四面体单元 · 并行后端 {FIXED_THREADS}线程",
        ha="left",
        va="center",
        fontsize=17,
        color="#4F565C",
    )
    fig.text(
        0.055,
        0.10,
        f"内存柱高为峰值内存，深色段为其中的额外内存；总耗时 = 预处理 + 数值组装；整体加速比 = 串行基线 {serial_ms:.0f} 毫秒 ÷ 当前总耗时。",
        ha="left",
        va="center",
        fontsize=14.5,
        color=dark_text,
    )

    base = ASSET_DIR / "backend_fixed_thread_metrics_cn"
    outputs = [
        base.with_suffix(".svg"),
        base.with_suffix(".pdf"),
        base.with_suffix(".png"),
        base.with_suffix(".tiff"),
    ]
    for output in outputs:
        if output.suffix == ".png":
            fig.savefig(output, dpi=240, facecolor="white")
        elif output.suffix == ".tiff":
            fig.savefig(output, dpi=600, facecolor="white")
        else:
            fig.savefig(output, facecolor="white")
    plt.close(fig)
    return outputs


def main() -> None:
    rows = selected_rows(read_rows())
    source_data = write_source_data(rows)
    outputs = draw(rows)
    print("source_data", source_data)
    for output in outputs:
        print("figure", output)


if __name__ == "__main__":
    main()
