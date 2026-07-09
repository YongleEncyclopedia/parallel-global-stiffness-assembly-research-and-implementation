#!/usr/bin/env python3
"""Draw a Chinese chart from Intel isolated-process memory measurements."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = (
    PROJECT_ROOT
    / "results"
    / "2026-05-23-linux-intel-linear-elastic-full-host"
    / "isolated_symbolic_memory"
    / "isolated_symbolic_memory.csv"
)
OUT_ROOT = PROJECT_ROOT / "reports" / "2026-06-25-intel-isolated-memory-metrics"
ASSET_DIR = OUT_ROOT / "assets"
SOURCE_OUT_DIR = OUT_ROOT / "source_data"

SELECTED_ROWS = (
    ("serial_symbolic_serial_numeric", "cpu_serial", 1, "串行基线"),
    ("direct_no_symbolic_background", "none", 20, "直接组装"),
    ("parallel_symbolic_parallel_numeric", "cpu_atomic", 20, "原子累加"),
    ("parallel_symbolic_parallel_numeric", "cpu_private_csr", 20, "线程私有"),
    ("parallel_symbolic_parallel_numeric", "cpu_lock_guard", 20, "互斥锁"),
)


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


def read_selected_rows() -> list[dict[str, object]]:
    with SOURCE_FILE.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))

    selected: list[dict[str, object]] = []
    for strategy, backend, threads, label in SELECTED_ROWS:
        matches = [
            row
            for row in source_rows
            if row["strategy_label"] == strategy
            and row["numeric_backend"] == backend
            and int(row["threads"]) == threads
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one row for {strategy}/{backend}/{threads}, got {len(matches)}")
        row = matches[0]
        selected.append(
            {
                "算法": label,
                "原始策略": strategy,
                "原始后端": backend,
                "线程数": threads,
                "估算峰值内存_GiB": float(row["estimated_peak_bytes"]) / 1024**3,
                "实测峰值内存_GiB": float(row["isolated_peak_rss_mb"]) / 1024,
                "额外内存_GiB": (
                    float(row["numeric_backend_extra_bytes"]) + float(row["direct_transient_bytes"])
                )
                / 1024**3,
                "基础内存_GiB": max(
                    0.0,
                    float(row["isolated_peak_rss_mb"]) / 1024
                    - (
                        float(row["numeric_backend_extra_bytes"]) + float(row["direct_transient_bytes"])
                    )
                    / 1024**3,
                ),
                "符号预处理耗时_ms": float(row["symbolic_total_ms"]),
                "组装耗时_ms": float(row["amortized_total_ms"]) - float(row["symbolic_total_ms"]),
                "统计耗时_ms": float(row["amortized_total_ms"]),
                "源文件": SOURCE_FILE.name,
            }
        )

    baseline_ms = float(selected[0]["统计耗时_ms"])
    for row in selected:
        row["整体加速比"] = baseline_ms / float(row["统计耗时_ms"])
        row["串行基线统计耗时_ms"] = baseline_ms
    return selected


def write_source_data(rows: list[dict[str, object]]) -> Path:
    SOURCE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SOURCE_OUT_DIR / "intel_isolated_memory_metrics_rows.csv"
    with out_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def format_axis(ax, xtick_labels: list[str], ylabel: str) -> None:
    ax.set_xticks(range(len(xtick_labels)))
    ax.set_xticklabels(xtick_labels, fontsize=10.6, linespacing=1.15)
    ax.set_ylabel(ylabel, fontsize=13, labelpad=8, fontweight="bold")
    ax.tick_params(axis="x", length=0, pad=9)
    ax.tick_params(axis="y", labelsize=10.5, colors="#5A6268")
    ax.grid(axis="y", color="#DCDCDC", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)


def add_title(ax, title: str, hint: str) -> None:
    ax.text(
        0.0,
        1.08,
        title,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=16.5,
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
        fontsize=11,
        color="#5A6268",
    )


def draw(rows: list[dict[str, object]]) -> list[Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    configure_style()

    labels = [str(row["算法"]) for row in rows]
    threads = [int(row["线程数"]) for row in rows]
    peak_memory = [float(row["实测峰值内存_GiB"]) for row in rows]
    base_memory = [float(row["基础内存_GiB"]) for row in rows]
    extra_memory = [float(row["额外内存_GiB"]) for row in rows]
    assembly_ms = [float(row["组装耗时_ms"]) for row in rows]
    preprocess_ms = [float(row["符号预处理耗时_ms"]) for row in rows]
    total_ms = [float(row["统计耗时_ms"]) for row in rows]
    speedups = [float(row["整体加速比"]) for row in rows]

    fig = plt.figure(figsize=(12.8, 7.2), dpi=240)
    green = "#76B900"
    pale_green = "#C8E88B"
    grey = "#A3A8AE"
    base_grey = "#D9DEE3"
    dark_text = "#202020"
    colors = [grey] + [green] * (len(rows) - 1)
    x = list(range(len(rows)))
    xtick_labels = [f"{label}\n{thread}线程" for label, thread in zip(labels, threads)]

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
    ax_mem.set_ylim(0, max(peak_memory) * 1.22)
    format_axis(ax_mem, xtick_labels, "吉字节")
    add_title(ax_mem, "实测峰值内存", "越低越好")
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
            fontsize=9.6,
            color="white",
            fontweight="bold",
        )
    ax_mem.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.01),
        frameon=False,
        fontsize=10.2,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )

    ax_time = fig.add_axes((0.385, 0.30, 0.27, 0.46))
    ax_time.bar(x, assembly_ms, width=0.64, color=green, edgecolor="none", label="组装")
    ax_time.bar(
        x,
        preprocess_ms,
        bottom=assembly_ms,
        width=0.64,
        color=pale_green,
        edgecolor="none",
        label="符号预处理",
    )
    ax_time.set_ylim(0, max(total_ms) * 1.22)
    format_axis(ax_time, xtick_labels, "毫秒")
    add_title(ax_time, "耗时", "越低越好")
    for idx, value in enumerate(total_ms):
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
        fontsize=10.2,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )

    ax_speed = fig.add_axes((0.70, 0.30, 0.27, 0.46))
    speed_bars = ax_speed.bar(x, speedups, width=0.64, color=colors, edgecolor="none")
    ax_speed.set_ylim(0, max(speedups) * 1.22)
    format_axis(ax_speed, xtick_labels, "倍")
    add_title(ax_speed, "整体加速比", "越高越好")
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

    baseline_ms = float(rows[0]["串行基线统计耗时_ms"])
    fig.text(
        0.055,
        0.91,
        "数值组装算法性能对比",
        ha="left",
        va="center",
        fontsize=25,
        fontweight="bold",
        color="#111111",
    )
    fig.text(
        0.055,
        0.85,
        "风机轮毂工程网格 · 四面体单元 · Intel Core Ultra 7 265KF",
        ha="left",
        va="center",
        fontsize=16.5,
        color="#4F565C",
    )
    fig.text(
        0.055,
        0.10,
        f"内存：隔离实测峰值，深色为额外内存；耗时：符号预处理 + 组装，不含后端准备；加速比：{baseline_ms:.0f} 毫秒 ÷ 当前耗时。",
        ha="left",
        va="center",
        fontsize=14.2,
        color=dark_text,
    )

    base = ASSET_DIR / "intel_isolated_memory_metrics_cn"
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
    rows = read_selected_rows()
    source_data = write_source_data(rows)
    outputs = draw(rows)
    print("source_data", source_data)
    for output in outputs:
        print("figure", output)


if __name__ == "__main__":
    main()
