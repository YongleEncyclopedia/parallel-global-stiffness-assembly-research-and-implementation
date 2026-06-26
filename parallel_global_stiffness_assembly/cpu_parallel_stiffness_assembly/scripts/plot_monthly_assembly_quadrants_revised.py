#!/usr/bin/env python3
"""Draw the revised monthly assembly quadrant figure with matplotlib.

The figure uses the already curated four-route CSV, not the screenshot.  It
keeps the old quadrant package intact and writes candidate outputs under a
date-stamped revision directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib as mpl
import matplotlib.font_manager as font_manager
import matplotlib.patches as patches
import matplotlib.pyplot as plt


CPU_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CSV = (
    CPU_ROOT
    / "reports"
    / "2026-05-27-assembly-quadrants"
    / "source_data"
    / "quadrant_selected_rows.csv"
)
DEFAULT_OUT_ROOT = CPU_ROOT / "reports" / "2026-06-12-assembly-quadrants-revision"
DEFAULT_FORMATS = ("svg", "pdf", "png")

BACKENDS = ("python", "r", "matlab")
FIGURE_STEMS = (
    "assembly_quadrants_revised",
    "direct_assembly_schematic",
    "two_stage_assembly_schematic",
)

COLORS = {
    "ink": "#17212B",
    "muted": "#667085",
    "grid": "#D7DDE4",
    "panel": "#F7F9FB",
    "direct": "#D8843A",
    "generate": "#E9B85E",
    "bucket": "#D8843A",
    "sort": "#C6605A",
    "symbolic": "#5F87C8",
    "scatter": "#7E6AAE",
    "numeric": "#3C9A7A",
    "gain": "#2F855A",
    "light_direct": "#F7E4CC",
    "light_sort": "#F2D9D6",
    "light_symbolic": "#DCE8F6",
    "light_scatter": "#E6E0F2",
    "light_numeric": "#DCEFE8",
}


@dataclass(frozen=True)
class RouteRow:
    key: str
    label: str
    mode: str
    backend: str
    threads: int
    total_ms: float
    symbolic_ms: float
    numeric_ms: float
    direct_generate_ms: float
    direct_bucket_merge_ms: float
    direct_sort_reduce_ms: float
    csr_gib: float
    plan_gib: float
    symbolic_temp_gib: float
    direct_transient_gib: float
    rel_l2: float

    @property
    def persistent_symbolic_gib(self) -> float:
        return self.csr_gib + self.plan_gib


def _float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in {"", None} else 0.0


def load_rows(source_csv: Path = DEFAULT_SOURCE_CSV) -> dict[str, RouteRow]:
    with source_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    result: dict[str, RouteRow] = {}
    for row in rows:
        key = row["key"]
        result[key] = RouteRow(
            key=key,
            label=row["label"],
            mode=row["mode"],
            backend=row["backend"],
            threads=int(row["threads"]),
            total_ms=_float(row, "total_ms"),
            symbolic_ms=_float(row, "symbolic_ms"),
            numeric_ms=_float(row, "numeric_ms"),
            direct_generate_ms=_float(row, "direct_generate_ms"),
            direct_bucket_merge_ms=_float(row, "direct_bucket_merge_ms"),
            direct_sort_reduce_ms=_float(row, "direct_sort_reduce_ms"),
            csr_gib=_float(row, "csr_gib"),
            plan_gib=_float(row, "plan_gib"),
            symbolic_temp_gib=_float(row, "symbolic_temp_gib"),
            direct_transient_gib=_float(row, "direct_transient_gib"),
            rel_l2=_float(row, "rel_l2"),
        )
    required = {"serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic"}
    missing = required.difference(result)
    if missing:
        raise ValueError(f"missing required route rows: {sorted(missing)}")
    return result


def compute_metrics(rows: dict[str, RouteRow]) -> dict[str, float]:
    metrics = {
        "serial_symbolic_vs_serial_direct": rows["serial_direct"].total_ms / rows["serial_symbolic"].total_ms,
        "parallel_symbolic_vs_serial_symbolic": rows["serial_symbolic"].total_ms / rows["parallel_symbolic"].total_ms,
        "parallel_symbolic_vs_parallel_direct": rows["parallel_direct"].total_ms / rows["parallel_symbolic"].total_ms,
        "parallel_symbolic_vs_serial_direct": rows["serial_direct"].total_ms / rows["parallel_symbolic"].total_ms,
    }
    assert abs(metrics["serial_symbolic_vs_serial_direct"] - 1.6826022961518814) < 1e-9
    assert abs(metrics["parallel_symbolic_vs_serial_symbolic"] - 4.668155618564831) < 1e-9
    assert abs(metrics["parallel_symbolic_vs_parallel_direct"] - 2.520166069480942) < 1e-9
    assert abs(metrics["parallel_symbolic_vs_serial_direct"] - 7.85464936259149) < 1e-9
    return metrics


def planned_output_files(out_root: Path, formats: Sequence[str] = DEFAULT_FORMATS) -> list[Path]:
    files: list[Path] = []
    for backend in BACKENDS:
        for stem in FIGURE_STEMS:
            for fmt in formats:
                files.append(out_root / backend / f"{stem}.{backend}.{fmt}")
    files.append(out_root / "source_data" / "quadrant_selected_rows.csv")
    files.append(out_root / "source_manifest.json")
    files.append(out_root / "qa_notes.md")
    return files


def normalize_formats(raw: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(raw, str):
        values = [item.strip().lower().lstrip(".") for item in raw.split(",")]
    else:
        values = [str(item).strip().lower().lstrip(".") for item in raw]
    formats = tuple(item for item in values if item)
    allowed = set(DEFAULT_FORMATS)
    unknown = set(formats).difference(allowed)
    if unknown:
        raise ValueError(f"unsupported output formats: {sorted(unknown)}")
    return formats or DEFAULT_FORMATS


def fmt_time(ms: float) -> str:
    return f"{ms / 1000:.2f} s" if ms >= 1000 else f"{ms:.0f} ms"


def fmt_gain(value: float) -> str:
    return f"{value:.2f}x"


def setup_style() -> font_manager.FontProperties:
    mpl.rcParams.update(
        {
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "font.size": 9,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return font_manager.FontProperties(fname=str(path))
    return font_manager.FontProperties(family="DejaVu Sans")


FONT = setup_style()


def text(ax, x, y, label, size=10, weight="regular", color="ink", ha="left", va="center", **kwargs):
    ax.text(
        x,
        y,
        label,
        fontsize=size,
        fontweight=weight,
        color=COLORS.get(color, color),
        ha=ha,
        va=va,
        fontproperties=FONT,
        **kwargs,
    )


def box(ax, x, y, w, h, label, *, fill="panel", edge="grid", size=9, weight="regular"):
    ax.add_patch(
        patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=COLORS[fill],
            edgecolor=COLORS[edge],
            linewidth=1.4,
        )
    )
    text(ax, x + w / 2, y + h / 2, label, size=size, weight=weight, color="ink", ha="center")


def arrow(ax, x1, y1, x2, y2, color="muted", lw=1.8, style="-"):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={
            "arrowstyle": "-|>",
            "lw": lw,
            "color": COLORS[color],
            "linestyle": style,
            "mutation_scale": 12,
        },
    )


def draw_sparse_matrix(ax, x, y, w, h, color="symbolic", values=False):
    for i in range(6):
        ax.plot([x + w * i / 5, x + w * i / 5], [y, y + h], color=COLORS["grid"], lw=0.6)
        ax.plot([x, x + w], [y + h * i / 5, y + h * i / 5], color=COLORS["grid"], lw=0.6)
    ax.add_patch(patches.Rectangle((x, y), w, h, fill=False, edgecolor=COLORS[color], lw=1.2))
    pts = [(0.15, 0.82), (0.36, 0.65), (0.58, 0.48), (0.78, 0.30), (0.78, 0.12)]
    for px, py in pts:
        ax.scatter([x + w * px], [y + h * py], s=38, color=COLORS["numeric" if values else color], zorder=3)


def draw_direct_schematic(ax, title="直接组装算法", subtitle="贡献三元组每次生成、合并、排序归并"):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(
        patches.FancyBboxPatch(
            (0.01, 0.03),
            0.98,
            0.94,
            boxstyle="round,pad=0.018,rounding_size=0.035",
            facecolor="#FFF9F1",
            edgecolor=COLORS["direct"],
            linewidth=1.4,
        )
    )
    text(ax, 0.05, 0.88, title, size=14, weight="bold", color="direct")
    text(ax, 0.05, 0.78, subtitle, size=8.8, color="muted")
    box(ax, 0.05, 0.48, 0.18, 0.18, "element\ncontrib.", fill="light_direct", edge="direct", size=8)
    box(ax, 0.31, 0.45, 0.18, 0.24, "(row,col,value)\ntriples", fill="panel", edge="direct", size=8.2)
    box(ax, 0.57, 0.59, 0.19, 0.12, "bucket/merge", fill="light_direct", edge="bucket", size=8.5, weight="bold")
    box(ax, 0.57, 0.37, 0.19, 0.12, "sort/reduce", fill="light_sort", edge="sort", size=8.5, weight="bold")
    draw_sparse_matrix(ax, 0.83, 0.38, 0.12, 0.25, color="sort", values=False)
    text(ax, 0.89, 0.30, "CSR", size=8, color="muted", ha="center")
    arrow(ax, 0.23, 0.57, 0.31, 0.57, color="direct")
    arrow(ax, 0.49, 0.57, 0.57, 0.65, color="direct")
    arrow(ax, 0.665, 0.59, 0.665, 0.49, color="sort")
    arrow(ax, 0.76, 0.43, 0.83, 0.50, color="sort")
    text(ax, 0.05, 0.17, "每轮保留 transient buffer；无法复用 CSR/scatter。", size=8.5, color="muted")


def draw_two_stage_schematic(ax, title="两阶段组装算法", subtitle="symbolic 先建立结构；numeric 重复写 values"):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(
        patches.FancyBboxPatch(
            (0.01, 0.03),
            0.98,
            0.94,
            boxstyle="round,pad=0.018,rounding_size=0.035",
            facecolor="#F4FAF7",
            edgecolor=COLORS["numeric"],
            linewidth=1.4,
        )
    )
    text(ax, 0.05, 0.88, title, size=14, weight="bold", color="numeric")
    text(ax, 0.05, 0.78, subtitle, size=8.8, color="muted")
    box(ax, 0.05, 0.48, 0.18, 0.18, "element\nconnectivity", fill="light_symbolic", edge="symbolic", size=8)
    box(ax, 0.31, 0.51, 0.17, 0.12, "symbolic", fill="light_symbolic", edge="symbolic", size=9, weight="bold")
    draw_sparse_matrix(ax, 0.55, 0.40, 0.17, 0.28, color="symbolic", values=False)
    text(ax, 0.635, 0.32, "CSR + scatter\nreusable", size=8, color="muted", ha="center")
    box(ax, 0.80, 0.43, 0.12, 0.22, "values", fill="light_numeric", edge="numeric", size=8.5)
    arrow(ax, 0.23, 0.57, 0.31, 0.57, color="symbolic")
    arrow(ax, 0.48, 0.57, 0.55, 0.55, color="symbolic")
    for yy in (0.62, 0.55, 0.48, 0.41):
        arrow(ax, 0.72, yy, 0.80, yy - 0.02, color="numeric", lw=1.2, style="--")
    text(ax, 0.05, 0.17, "symbolic 可并行且可复用；numeric 只 scatter 到 values。", size=8.5, color="muted")


def draw_header(fig):
    fig.text(
        0.055,
        0.965,
        "四类刚度组装路线：时间优先，内存为辅",
        fontsize=22,
        fontweight="bold",
        color=COLORS["ink"],
        fontproperties=FONT,
        ha="left",
        va="top",
    )
    fig.text(
        0.055,
        0.925,
        "WindHub Tet4 / Apple M4 Max；total time includes symbolic/direct construction and numeric assembly",
        fontsize=10.5,
        color=COLORS["muted"],
        fontproperties=FONT,
        ha="left",
        va="top",
    )
    fig.lines.append(
        mpl.lines.Line2D([0.055, 0.945], [0.905, 0.905], transform=fig.transFigure, color=COLORS["grid"], lw=0.8)
    )


def symbolic_stage_parts(route: RouteRow) -> list[tuple[str, float, str, str]]:
    total = route.persistent_symbolic_gib
    csr_part = route.symbolic_ms * (route.csr_gib / total) if total else 0.0
    plan_part = max(route.symbolic_ms - csr_part, 0.0)
    return [
        ("CSR pattern", csr_part, "symbolic", "light_symbolic"),
        ("scatter plan", plan_part, "scatter", "light_scatter"),
        ("numeric", route.numeric_ms, "numeric", "light_numeric"),
    ]


def direct_stage_parts(route: RouteRow) -> list[tuple[str, float, str, str]]:
    return [
        ("generate", route.direct_generate_ms, "generate", "light_direct"),
        ("bucket/merge", route.direct_bucket_merge_ms, "bucket", "light_direct"),
        ("sort/reduce", route.direct_sort_reduce_ms, "sort", "light_sort"),
    ]


def draw_timing_panel(ax, rows: dict[str, RouteRow]):
    order = ["serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic"]
    max_total_s = max(rows[key].total_ms for key in order) / 1000
    y_positions = list(range(len(order)))[::-1]
    ax.set_xlim(0, max_total_s * 1.22)
    ax.set_ylim(-0.7, len(order) - 0.15)
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.6)
    ax.set_title("四类路线端到端耗时构成", loc="left", fontsize=14, fontproperties=FONT, fontweight="bold", color=COLORS["ink"])
    for key, y in zip(order, y_positions):
        route = rows[key]
        parts = direct_stage_parts(route) if route.mode.startswith("direct") else symbolic_stage_parts(route)
        left = 0.0
        for name, value_ms, edge, face in parts:
            width = value_ms / 1000
            ax.barh(y, width, left=left, height=0.46, color=COLORS[face], edgecolor=COLORS[edge], linewidth=1.0)
            if width > 0.35:
                text(ax, left + width / 2, y, fmt_time(value_ms), size=8.2, color="ink", ha="center")
            left += width
        label = f"{route.label}\n{route.threads} thread(s)"
        text(ax, -0.18, y, label, size=9.5, color="ink", ha="right")
        text(ax, left + 0.10, y, fmt_time(route.total_ms), size=12.5, weight="bold", color="ink")
    legend_items = [
        ("direct generate", "light_direct", "generate"),
        ("bucket/merge", "light_direct", "bucket"),
        ("sort/reduce", "light_sort", "sort"),
        ("CSR pattern", "light_symbolic", "symbolic"),
        ("scatter plan", "light_scatter", "scatter"),
        ("numeric", "light_numeric", "numeric"),
    ]
    x0, y0 = 0.01, -0.17
    for i, (label, face, edge) in enumerate(legend_items):
        x = x0 + i * 0.155
        y = y0
        ax.add_patch(
            patches.Rectangle(
                (x, y),
                0.024,
                0.042,
                transform=ax.transAxes,
                facecolor=COLORS[face],
                edgecolor=COLORS[edge],
                linewidth=1.0,
                clip_on=False,
            )
        )
        ax.text(
            x + 0.030,
            y + 0.021,
            label,
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=7.4,
            color=COLORS["ink"],
            fontproperties=FONT,
            clip_on=False,
        )


def draw_badges(ax, rows: dict[str, RouteRow], metrics: dict[str, float]):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    text(ax, 0.02, 0.93, "对比结论", size=14, weight="bold", color="ink")
    badges = [
        ("1.68x", "串行：有符号优于无符号", "5.20 s → 3.09 s"),
        ("4.67x", "并行符号优于串行符号", "3.09 s → 662 ms"),
        ("2.52x", "同为 14 线程：有符号优于 direct", "1.67 s → 662 ms"),
        ("7.85x", "最佳路线相对串行 direct", "5.20 s → 662 ms"),
    ]
    for i, (value, title, detail) in enumerate(badges):
        y = 0.74 - i * 0.205
        ax.add_patch(
            patches.FancyBboxPatch(
                (0.02, y),
                0.94,
                0.155,
                boxstyle="round,pad=0.018,rounding_size=0.035",
                facecolor="#F6FAF7",
                edgecolor=COLORS["gain"],
                linewidth=1.1,
            )
        )
        text(ax, 0.08, y + 0.083, value, size=19, weight="bold", color="gain")
        text(ax, 0.36, y + 0.103, title, size=9.5, weight="bold", color="ink")
        text(ax, 0.36, y + 0.052, detail, size=9, color="muted")
    best = rows["parallel_symbolic"]
    text(ax, 0.02, 0.02, f"最佳路线 rel_L2 = {best.rel_l2:.1e}", size=8.5, color="muted")


def memory_parts(route: RouteRow) -> list[tuple[str, float, str, str]]:
    return [
        ("CSR + scatter", route.persistent_symbolic_gib, "symbolic", "light_symbolic"),
        ("symbolic temp", route.symbolic_temp_gib, "scatter", "light_scatter"),
        ("direct transient", route.direct_transient_gib, "sort", "light_sort"),
    ]


def draw_memory_panel(ax, rows: dict[str, RouteRow]):
    order = ["serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic"]
    y_positions = list(range(len(order)))[::-1]
    max_mem = max(sum(value for _, value, _, _ in memory_parts(rows[key])) for key in order)
    ax.set_xlim(0, max_mem * 1.22)
    ax.set_ylim(-0.65, len(order) - 0.15)
    ax.set_yticks([])
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.6)
    ax.set_xlabel("可解释数据结构内存 / GiB", fontproperties=FONT, fontsize=8.5, color=COLORS["muted"])
    ax.set_title("内存占用（辅证）", loc="left", fontsize=12, fontproperties=FONT, fontweight="bold", color=COLORS["ink"])
    for key, y in zip(order, y_positions):
        route = rows[key]
        left = 0.0
        total = 0.0
        for component, value, edge, face in memory_parts(route):
            if value <= 0:
                continue
            ax.barh(y, value, left=left, height=0.40, color=COLORS[face], edgecolor=COLORS[edge], linewidth=1.0)
            if value > 0.18:
                text(ax, left + value / 2, y, f"{value:.2f}", size=8, color="ink", ha="center")
            elif key == "parallel_symbolic" and component == "symbolic temp":
                text(ax, left + value + 0.04, y + 0.23, f"+{value:.2f} temp", size=7.5, color="scatter")
            left += value
            total += value
        text(ax, -0.08, y, route.label, size=8.5, color="ink", ha="right")
        text(ax, total + 0.05, y, f"{total:.2f} GiB", size=9.5, weight="bold", color="ink")
    text(
        ax,
        0.01,
        -0.47,
        "注：不是 OS RSS；direct 主要是 transient contribution buffer，symbolic 主要是可复用 CSR/scatter。",
        size=7.6,
        color="muted",
        transform=ax.transAxes,
    )


def draw_main_figure(rows: dict[str, RouteRow], metrics: dict[str, float]) -> plt.Figure:
    fig = plt.figure(figsize=(16, 9), constrained_layout=False)
    draw_header(fig)
    ax_direct = fig.add_axes([0.055, 0.69, 0.43, 0.20])
    ax_two = fig.add_axes([0.515, 0.69, 0.43, 0.20])
    draw_direct_schematic(ax_direct)
    draw_two_stage_schematic(ax_two)
    ax_time = fig.add_axes([0.09, 0.31, 0.58, 0.30])
    ax_badges = fig.add_axes([0.715, 0.29, 0.23, 0.34])
    ax_memory = fig.add_axes([0.09, 0.075, 0.82, 0.15])
    draw_timing_panel(ax_time, rows)
    draw_badges(ax_badges, rows, metrics)
    draw_memory_panel(ax_memory, rows)
    fig.text(
        0.055,
        0.018,
        "Source: curated WindHub / Apple M4 Max quadrant rows; direct/no-symbolic is contribution-list sort/reduce, not a dense matrix.",
        fontsize=8.5,
        color=COLORS["muted"],
        fontproperties=FONT,
    )
    return fig


def draw_standalone_schematic(kind: str) -> plt.Figure:
    fig = plt.figure(figsize=(8, 3.6), constrained_layout=False)
    ax = fig.add_axes([0.02, 0.03, 0.96, 0.94])
    if kind == "direct":
        draw_direct_schematic(ax)
    elif kind == "two_stage":
        draw_two_stage_schematic(ax)
    else:
        raise ValueError(f"unknown schematic kind: {kind}")
    return fig


def save_figure(fig: plt.Figure, out_base: Path, formats: Sequence[str]) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        target = out_base.parent / f"{out_base.name}.{fmt}"
        if fmt == "png":
            fig.savefig(target, dpi=300, facecolor="white")
        else:
            fig.savefig(target, facecolor="white")
    plt.close(fig)


def write_source_copy(source_csv: Path, out_root: Path) -> None:
    source_dir = out_root / "source_data"
    source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_csv, source_dir / "quadrant_selected_rows.csv")


def write_manifest(source_csv: Path, out_root: Path, formats: Sequence[str], metrics: dict[str, float]) -> None:
    manifest = {
        "figure_contract": {
            "core_conclusion": "符号组装+数值组装压低 direct/no-symbolic 的排序归并成本；并行 symbolic + numeric 是四条路线中最快方案。",
            "archetype": "schematic-led composite + quantitative grid",
            "primary_evidence": "four-route stacked timing bars",
            "secondary_evidence": "memory occupancy bars and speedup badges",
        },
        "source_csv": str(source_csv.relative_to(CPU_ROOT)),
        "formats": list(formats),
        "backends": list(BACKENDS),
        "headline_metrics": metrics,
    }
    (out_root / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def write_qa_notes(out_root: Path, formats: Sequence[str], metrics: dict[str, float]) -> None:
    rscript = shutil.which("Rscript")
    matlab = shutil.which("matlab") or ("/Applications/MATLAB_R2026a.app/bin/matlab" if Path("/Applications/MATLAB_R2026a.app/bin/matlab").exists() else None)
    notes = [
        "# 四象限组装图 revision QA",
        "",
        "## Figure contract",
        "",
        "- Core conclusion: symbolic + numeric assembly is faster than direct/no-symbolic sorting, and parallel symbolic reuse is the best of the four routes.",
        "- Archetype: schematic-led composite + quantitative grid.",
        "- Source data: `source_data/quadrant_selected_rows.csv` copied from the existing curated quadrant package.",
        "",
        "## Numeric checks",
        "",
        f"- Serial symbolic vs serial direct: `{fmt_gain(metrics['serial_symbolic_vs_serial_direct'])}`.",
        f"- Parallel symbolic vs serial symbolic: `{fmt_gain(metrics['parallel_symbolic_vs_serial_symbolic'])}`.",
        f"- Parallel symbolic vs parallel direct: `{fmt_gain(metrics['parallel_symbolic_vs_parallel_direct'])}`.",
        f"- Parallel symbolic vs serial direct: `{fmt_gain(metrics['parallel_symbolic_vs_serial_direct'])}`.",
        "",
        "## Runtime availability",
        "",
        "- Python/matplotlib: available in this environment.",
        f"- Rscript: `{rscript or 'not found'}`.",
        f"- MATLAB: `{matlab or 'not found'}`.",
        "",
        "## Expected outputs",
        "",
    ]
    for path in planned_output_files(out_root, formats):
        notes.append(f"- `{path.relative_to(out_root).as_posix()}`")
    notes.append("")
    (out_root / "qa_notes.md").write_text("\n".join(notes), encoding="utf-8")


def render_python(source_csv: Path, out_root: Path, formats: Sequence[str]) -> None:
    rows = load_rows(source_csv)
    metrics = compute_metrics(rows)
    backend_dir = out_root / "python"
    save_figure(draw_main_figure(rows, metrics), backend_dir / "assembly_quadrants_revised.python", formats)
    save_figure(draw_standalone_schematic("direct"), backend_dir / "direct_assembly_schematic.python", formats)
    save_figure(draw_standalone_schematic("two_stage"), backend_dir / "two_stage_assembly_schematic.python", formats)
    write_source_copy(source_csv, out_root)
    write_manifest(source_csv, out_root, formats, metrics)
    write_qa_notes(out_root, formats, metrics)


def verify_python_outputs(out_root: Path, formats: Sequence[str]) -> dict[str, object]:
    expected = [path for path in planned_output_files(out_root, formats) if "/python/" in path.as_posix()]
    existing = [path for path in expected if path.exists() and path.stat().st_size > 0]
    svg_text_nodes = {}
    for path in expected:
        if path.suffix == ".svg" and path.exists():
            svg_text_nodes[path.name] = path.read_text(encoding="utf-8").count("<text")
    png_dimensions = {}
    try:
        from PIL import Image

        for path in expected:
            if path.suffix == ".png" and path.exists():
                with Image.open(path) as image:
                    png_dimensions[path.name] = image.size
    except ModuleNotFoundError:
        png_dimensions["error"] = "Pillow unavailable"
    return {
        "expected_python_files": len(expected),
        "existing_python_files": len(existing),
        "svg_text_nodes": svg_text_nodes,
        "png_dimensions": png_dimensions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--format", default=",".join(DEFAULT_FORMATS), help="Comma-separated output formats: svg,pdf,png.")
    parser.add_argument("--verify", action="store_true", help="Print a JSON summary of generated Python outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    formats = normalize_formats(args.format)
    render_python(args.source_csv, args.out_root, formats)
    payload = {
        "out_root": str(args.out_root),
        "formats": list(formats),
        "python": verify_python_outputs(args.out_root, formats),
    }
    if args.verify:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"out_root": str(args.out_root)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
