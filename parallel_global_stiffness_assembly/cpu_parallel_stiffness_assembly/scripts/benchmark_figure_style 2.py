#!/usr/bin/env python3
"""Shared presentation style helpers for benchmark figures."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


INK = "#111827"
MUTED = "#64748b"
GRID = "#d6dde8"
PAPER = "#fbfbf8"
PANEL = "#ffffff"
BLUE = "#2563eb"
TEAL = "#0f766e"
GREEN = "#16a34a"
ORANGE = "#f97316"
PURPLE = "#7c3aed"
RED = "#dc2626"
SLATE = "#475569"

ALGORITHM_ORDER = [
    "cpu_serial",
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_coo_sort_reduce",
    "cpu_row_owner",
    "cpu_graph_coloring",
]

THREAD_ALGORITHM_ORDER = [
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
]

ALGO_LABELS = {
    "cpu_serial": "Serial",
    "cpu_atomic": "Atomic",
    "cpu_private_csr": "Private CSR",
    "cpu_coo_sort_reduce": "COO Sort-Reduce",
    "cpu_row_owner": "Row Owner",
    "cpu_graph_coloring": "Coloring",
}

ALGO_COLORS = {
    "cpu_serial": SLATE,
    "cpu_atomic": BLUE,
    "cpu_private_csr": TEAL,
    "cpu_coo_sort_reduce": ORANGE,
    "cpu_row_owner": GREEN,
    "cpu_graph_coloring": PURPLE,
}

PROFILE_COLORS = {
    "full_host": BLUE,
    "performance_core_only": TEAL,
    "efficiency_core_only": RED,
}

ENV_COLORS = {
    "default": BLUE,
    "bound": RED,
}

STAGE_COLORS = [
    SLATE,
    PURPLE,
    GREEN,
    "#94a3b8",
    ORANGE,
    BLUE,
    "#0891b2",
    RED,
    TEAL,
]

_CJK_RE = re.compile(r"[\u3400-\u9fff\uac00-\ud7af\u3040-\u30ff]")


def contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def assert_english_text(texts: Iterable[str]) -> None:
    offenders = [text for text in texts if contains_cjk(text)]
    if offenders:
        raise ValueError("Non-English figure text detected: " + "; ".join(offenders[:5]))


def apply_presentation_style() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.sans-serif": ["Inter", "Aptos", "Helvetica Neue", "Arial", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.facecolor": PAPER,
            "axes.facecolor": PANEL,
            "axes.edgecolor": "#cbd5e1",
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "grid.color": GRID,
            "grid.alpha": 0.55,
            "font.size": 11,
            "axes.titlesize": 15,
            "axes.labelsize": 12,
            "legend.fontsize": 10,
            "svg.fonttype": "none",
        }
    )


def algo_label(algorithm: str) -> str:
    return ALGO_LABELS.get(algorithm, algorithm.replace("cpu_", "").replace("_", " ").title())


def set_slide_title(fig, title: str, subtitle: str | None = None, *, y: float = 0.985) -> None:
    fig.suptitle(title, x=0.02, y=y, ha="left", va="top", fontsize=23, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.02, y - 0.055, subtitle, ha="left", va="top", fontsize=12.5, color=MUTED)


def style_axis(ax, *, grid_axis: str = "y", title: str | None = None) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    if grid_axis != "none":
        ax.grid(True, axis=grid_axis)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, loc="left", pad=12, fontweight="bold")


def add_panel_label(ax, label: str) -> None:
    ax.text(
        0.0,
        1.04,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        color=MUTED,
    )


def add_baseline(ax, y: float = 1.0, label: str = "baseline") -> None:
    ax.axhline(y, color=MUTED, linestyle=(0, (5, 4)), linewidth=1.25, alpha=0.85)
    ax.text(
        0.995,
        y,
        label,
        transform=ax.get_yaxis_transform(),
        ha="right",
        va="bottom",
        fontsize=9,
        color=MUTED,
    )


def annotate_point(ax, x: float, y: float, text: str, *, color: str = INK, dy: int = 9) -> None:
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(0, dy),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color=color,
        bbox={"boxstyle": "round,pad=0.24", "facecolor": "white", "edgecolor": "#d1d5db", "alpha": 0.94},
    )


def label_line_end(ax, x: float, y: float, text: str, *, color: str) -> None:
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(8, 0),
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize=9.5,
        fontweight="bold",
        color=color,
    )


def format_ms(value: float) -> str:
    if value >= 100:
        return f"{value:.0f} ms"
    if value >= 10:
        return f"{value:.1f} ms"
    return f"{value:.2f} ms"


def format_ratio(value: float) -> str:
    return f"{value:.2f}x"


def format_gib(value: float) -> str:
    return f"{value:.2f} GiB"


def save_figure(fig, out_base: Path, *, dpi: int = 260) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_base.with_suffix(".png"), dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(out_base.with_suffix(".svg"), bbox_inches="tight", facecolor=fig.get_facecolor())
    png = out_base.with_suffix(".png")
    svg = out_base.with_suffix(".svg")
    if png.stat().st_size == 0 or svg.stat().st_size == 0:
        raise RuntimeError(f"Empty figure output for {out_base}")
