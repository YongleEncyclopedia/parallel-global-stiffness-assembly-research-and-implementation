#!/usr/bin/env python3
"""Draw simplified free-tip maximum-deflection validation charts."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedFormatter, FixedLocator, NullFormatter, NullLocator
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
CPU_ROOT = REPO_ROOT / "parallel_global_stiffness_assembly" / "cpu_parallel_stiffness_assembly"
REPORT_DIR = CPU_ROOT / "reports" / "2026-06-16-simple-deflection-validation-figures"
SOURCE_CSV = REPORT_DIR / "source_data" / "free_tip_max_deflection_relative_difference.csv"
ASSET_DIR = REPORT_DIR / "assets"

NVIDIA_GREEN = "#76B900"
TEXT_DARK = "#111111"
TEXT_MID = "#5F6368"
GRID = "#D6D6D6"

ORDERED_PLATFORMS = [
    "Mac Studio macOS",
    "Linux Intel",
    "Windows AMD",
]


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": [
            "PingFang SC",
            "Heiti SC",
            "STHeiti",
            "Arial Unicode MS",
            "Arial",
            "Helvetica",
            "DejaVu Sans",
            "sans-serif",
        ],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.bbox": None,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 1.0,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0,
    }
)


def read_rows() -> list[dict[str, str]]:
    with SOURCE_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt_percent(value: float) -> str:
    if value >= 0.001:
        return f"{value:.5f}".rstrip("0").rstrip(".") + "%"
    return f"{value:.9f}".rstrip("0").rstrip(".") + "%"


def draw_case(case_key: str, rows: list[dict[str, str]]) -> Path:
    case_rows = [row for row in rows if row["case_key"] == case_key]
    case_rows.sort(key=lambda row: ORDERED_PLATFORMS.index(row["platform"]))
    case_label = case_rows[0]["case_label"]

    values = np.array([float(row["rel_percent"]) for row in case_rows], dtype=float)
    labels = [f"{row['platform']}\n{row['reference_solver']}" for row in case_rows]
    x = np.arange(len(case_rows))

    fig, ax = plt.subplots(figsize=(10.24, 5.76))
    fig.subplots_adjust(left=0.18, right=0.95, top=0.82, bottom=0.30)

    ymin = 1e-6
    ymax = 3e-2
    heights = np.maximum(values - ymin, ymin * 0.15)
    ax.bar(
        x,
        heights,
        bottom=ymin,
        width=0.58,
        color=NVIDIA_GREEN,
        edgecolor=NVIDIA_GREEN,
        linewidth=0,
    )

    ax.set_yscale("log")
    ax.set_ylim(ymin, ymax)
    ax.set_xlim(-0.55, len(case_rows) - 0.45)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=14, color=TEXT_DARK)
    ax.tick_params(axis="x", length=0, pad=10)
    ticks = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(FixedFormatter([fmt_percent(tick) for tick in ticks]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="y", labelsize=12, colors=TEXT_MID)
    ax.grid(axis="y", which="major", color=GRID, linewidth=0.8, alpha=0.75)
    ax.grid(axis="y", which="minor", visible=False)
    ax.set_ylabel("最大挠度相对差异", fontsize=14, color=TEXT_DARK, labelpad=12)

    for xi, value in zip(x, values):
        large_bar = value > 5e-3
        y_text = value / 1.7 if large_bar else value * 1.35
        ax.text(
            xi,
            y_text,
            fmt_percent(value),
            va="center" if large_bar else "bottom",
            ha="center",
            fontsize=14,
            fontweight="bold",
            color="white" if large_bar else TEXT_DARK,
        )

    fig.text(0.055, 0.88, case_label, ha="left", va="center", fontsize=23, fontweight="bold", color=TEXT_DARK)
    fig.text(
        0.055,
        0.12,
        "相对差异 (%) = 100 × abs(abs(Uz_MATLAB,max) - abs(Uz_FE,max)) / abs(Uz_FE,max)",
        ha="left",
        va="center",
        fontsize=14,
        color=TEXT_DARK,
    )

    out_base = ASSET_DIR / f"fig_{case_key}_simple_deflection_validation"
    fig.savefig(out_base.with_suffix(".svg"), bbox_inches=None)
    fig.savefig(out_base.with_suffix(".pdf"), bbox_inches=None)
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches=None)
    fig.savefig(out_base.with_suffix(".tiff"), dpi=600, bbox_inches=None)
    plt.close(fig)
    return out_base.with_suffix(".png")


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    for case_key in ("tet4", "hex8"):
        out = draw_case(case_key, rows)
        print(out)


if __name__ == "__main__":
    main()
