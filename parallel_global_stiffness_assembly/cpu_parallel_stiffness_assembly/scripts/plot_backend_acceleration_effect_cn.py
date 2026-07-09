#!/usr/bin/env python3
"""Draw a concise Chinese slide chart for backend algorithm metrics.

The source data intentionally uses only the WindHub physics Tet4 rows from the
2026-04-22 CPU benchmark family. Earlier dashboard code merged simplified and
physics rows in the same thread plot; this script collapses the selected
physics rows to one fastest valid row per backend.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "results" / "2026-04-22" / "csv"
OUT_ROOT = PROJECT_ROOT / "reports" / "2026-06-23-backend-acceleration-effect"
ASSET_DIR = OUT_ROOT / "assets"
SOURCE_OUT_DIR = OUT_ROOT / "source_data"

SOURCE_FILES = (
    SOURCE_DIR / "windhub_physics_tet4.csv",
    SOURCE_DIR / "windhub_physics_tet4_coo_sort_reduce.csv",
)

ALGORITHM_ORDER = (
    "cpu_serial",
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_graph_coloring",
    "cpu_row_owner",
)

LABELS = {
    "cpu_serial": "串行组装",
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


def read_source_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source_file in SOURCE_FILES:
        with source_file.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("status") != "PASS":
                    continue
                if row.get("case_name") != "3d-WindTurbineHub":
                    continue
                if row.get("kernel") != "physics_tet4":
                    continue
                row["source_file"] = source_file.name
                rows.append(row)
    return rows


def best_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for algorithm in ALGORITHM_ORDER:
        candidates = [row for row in rows if row.get("algorithm") == algorithm]
        if not candidates:
            continue
        best = min(candidates, key=lambda row: float(row["assembly_mean_ms"]))
        result.append(
            {
                "算法": LABELS[algorithm],
                "原始后端": algorithm,
                "线程数": int(best["threads"]),
                "组装耗时_ms": float(best["assembly_mean_ms"]),
                "内存_吉字节": float(best["peak_rss_mb"]) / 1024,
                "加速比": float(best["speedup"]),
                "源文件": best["source_file"],
            }
        )
    return result


def write_source_data(rows: list[dict[str, object]]) -> Path:
    SOURCE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SOURCE_OUT_DIR / "backend_algorithm_metrics_rows.csv"
    with out_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def draw(rows: list[dict[str, object]]) -> list[Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    configure_style()

    labels = [str(row["算法"]) for row in rows]
    threads = [int(row["线程数"]) for row in rows]
    time_ms = [float(row["组装耗时_ms"]) for row in rows]
    memory_gib = [float(row["内存_吉字节"]) for row in rows]
    speedups = [float(row["加速比"]) for row in rows]

    fig = plt.figure(figsize=(12.8, 7.2), dpi=240)
    green = "#76B900"
    grey = "#A3A8AE"
    colors = [grey] + [green] * (len(rows) - 1)
    x = list(range(len(rows)))

    panel_specs = [
        {
            "rect": (0.07, 0.30, 0.27, 0.46),
            "title": "内存",
            "hint": "越低越好",
            "values": memory_gib,
            "ylim": (0, max(memory_gib) * 1.22),
            "ylabel": "吉字节",
            "formatter": lambda value: f"{value:.2f}",
        },
        {
            "rect": (0.385, 0.30, 0.27, 0.46),
            "title": "组装耗时",
            "hint": "越低越好",
            "values": time_ms,
            "ylim": (0, max(time_ms) * 1.23),
            "ylabel": "毫秒",
            "formatter": lambda value: f"{value:.0f}",
        },
        {
            "rect": (0.70, 0.30, 0.27, 0.46),
            "title": "加速比",
            "hint": "越高越好",
            "values": speedups,
            "ylim": (0, max(speedups) * 1.20),
            "ylabel": "倍",
            "formatter": lambda value: f"{value:.2f}",
        },
    ]

    xtick_labels = [f"{label}\n{thread}线程" for label, thread in zip(labels, threads)]
    for spec in panel_specs:
        ax = fig.add_axes(spec["rect"])
        bars = ax.bar(x, spec["values"], width=0.64, color=colors, edgecolor="none")
        ax.set_ylim(*spec["ylim"])
        ax.set_ylabel(spec["ylabel"], fontsize=13, labelpad=8, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(xtick_labels, fontsize=10.5, linespacing=1.15)
        ax.tick_params(axis="y", labelsize=10.5, colors="#5A6268")
        ax.tick_params(axis="x", length=0, pad=9)
        ax.grid(axis="y", color="#DCDCDC", linewidth=0.9)
        ax.set_axisbelow(True)
        ax.spines["left"].set_linewidth(1.0)
        ax.spines["bottom"].set_linewidth(1.0)
        ax.text(
            0.0,
            1.08,
            spec["title"],
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
            spec["hint"],
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=11.5,
            color="#5A6268",
        )
        y_span = spec["ylim"][1] - spec["ylim"][0]
        for bar, value in zip(bars, spec["values"]):
            x_pos = bar.get_x() + bar.get_width() / 2
            y_pos = value + y_span * 0.025
            ax.text(
                x_pos,
                y_pos,
                spec["formatter"](value),
                ha="center",
                va="bottom",
                fontsize=10.8,
                color="#202020",
            )

    fig.text(
        0.055,
        0.91,
        "不同数值组装算法的内存、耗时与加速比",
        ha="left",
        va="center",
        fontsize=25,
        fontweight="bold",
        color="#111111",
    )
    fig.text(
        0.055,
        0.85,
        "风机轮毂工程网格 · 四面体单元",
        ha="left",
        va="center",
        fontsize=17,
        color="#4F565C",
    )
    fig.text(
        0.055,
        0.10,
        "每种算法取通过测试中的最短组装耗时；内存为同一次测试记录的最大占用；加速比相对串行组装。",
        ha="left",
        va="center",
        fontsize=14.5,
        color="#202020",
    )

    base = ASSET_DIR / "backend_algorithm_metrics_cn"
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
    rows = best_rows(read_source_rows())
    if len(rows) != len(ALGORITHM_ORDER):
        raise RuntimeError(f"Expected {len(ALGORITHM_ORDER)} algorithms, got {len(rows)}")
    source_data = write_source_data(rows)
    outputs = draw(rows)
    print("source_data", source_data)
    for output in outputs:
        print("figure", output)


if __name__ == "__main__":
    main()
