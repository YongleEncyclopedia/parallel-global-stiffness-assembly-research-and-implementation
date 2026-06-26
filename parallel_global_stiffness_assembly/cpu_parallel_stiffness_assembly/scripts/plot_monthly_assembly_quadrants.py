#!/usr/bin/env python3
"""生成月度汇报用的四象限组装策略图和支撑图。

图中主结论锚定 WindHub / Apple M4 Max 的同一份四象限结果：
串行有符号、串行无符号、并行有符号、并行无符号。辅助图拆出
时间构成、线程扩展和内存生命周期，用于解释结论而不是替代原始
benchmark CSV。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import plot_assembly_schematics as vg


CPU_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = CPU_ROOT / "reports" / "2026-05-27-assembly-quadrants"
ASSET_DIR = OUT_ROOT / "assets"
SOURCE_DIR = OUT_ROOT / "source_data"

QUADRANT_CSV = CPU_ROOT / "results" / "2026-05-16-mentor-action-items" / "windhub_parallel_symbolic_direct.csv"
AMORTIZATION_CSV = CPU_ROOT / "results" / "2026-05-11-symbolic-numeric" / "symbolic_numeric_eval.csv"

vg.W = 1920
vg.H = 1080
vg.SCALE = 2
vg.PALETTE.update(
    {
        "sky": "#5F87C8",
        "sky2": "#DCE8F6",
        "teal": "#3C9A7A",
        "teal2": "#DCEFE8",
        "amber": "#D9993A",
        "amber2": "#F5E4C7",
        "red": "#C6605A",
        "red2": "#F2D9D6",
        "violet": "#7E6AAE",
        "violet2": "#E6E0F2",
        "dark": "#17212B",
        "soft": "#F5F7FA",
        "axis": "#A8B3C1",
        "ok": "#2F855A",
    }
)


@dataclass(frozen=True)
class MethodPoint:
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
    csr_bytes: int
    plan_bytes: int
    symbolic_temp_bytes: int
    direct_transient_bytes: int
    rel_l2: float


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in {"", None} else 0.0


def as_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value not in {"", None} else 0


def find_row(rows: list[dict[str, str]], *, mode: str, threads: int, backend: str | None = None) -> dict[str, str]:
    for row in rows:
        if row.get("mode") != mode:
            continue
        if int(row.get("threads", "0")) != threads:
            continue
        if backend is not None and row.get("numeric_backend") != backend:
            continue
        return row
    raise KeyError(f"missing row: mode={mode}, threads={threads}, backend={backend}")


def method_from_row(key: str, label: str, row: dict[str, str]) -> MethodPoint:
    return MethodPoint(
        key=key,
        label=label,
        mode=row["mode"],
        backend=row.get("numeric_backend", "none"),
        threads=as_int(row, "threads"),
        total_ms=as_float(row, "amortized_total_ms"),
        symbolic_ms=as_float(row, "symbolic_total_ms"),
        numeric_ms=as_float(row, "numeric_ms"),
        direct_generate_ms=as_float(row, "direct_generate_ms"),
        direct_bucket_merge_ms=as_float(row, "direct_bucket_merge_ms"),
        direct_sort_reduce_ms=as_float(row, "direct_sort_reduce_ms"),
        csr_bytes=as_int(row, "csr_bytes"),
        plan_bytes=as_int(row, "plan_bytes"),
        symbolic_temp_bytes=as_int(row, "symbolic_temporary_bytes"),
        direct_transient_bytes=as_int(row, "direct_transient_bytes"),
        rel_l2=as_float(row, "rel_l2"),
    )


def load_methods() -> dict[str, MethodPoint]:
    rows = read_csv(QUADRANT_CSV)
    return {
        "serial_direct": method_from_row(
            "serial_direct",
            "串行无符号直接",
            find_row(rows, mode="direct_no_symbolic_serial", threads=1, backend="none"),
        ),
        "serial_symbolic": method_from_row(
            "serial_symbolic",
            "串行有符号+数值",
            find_row(rows, mode="symbolic_reuse_serial", threads=1, backend="cpu_serial"),
        ),
        "parallel_direct": method_from_row(
            "parallel_direct",
            "并行无符号直接",
            find_row(rows, mode="direct_no_symbolic_parallel", threads=14, backend="none"),
        ),
        "parallel_symbolic": method_from_row(
            "parallel_symbolic",
            "并行有符号+数值",
            find_row(rows, mode="parallel_symbolic_reuse", threads=14, backend="cpu_atomic"),
        ),
    }


def fmt_ms(value: float) -> str:
    if value >= 1000:
        return f"{value / 1000:.2f} s"
    return f"{value:.0f} ms"


def fmt_gain(value: float) -> str:
    return f"{value:.2f}x"


def gib(value: int) -> float:
    return value / (1024**3)


def export_all(fig: vg.Figure, stem: str) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fig.export_svg(ASSET_DIR / f"{stem}.svg")
    fig.export_pdf(ASSET_DIR / f"{stem}.pdf")
    fig.export_png_tiff(ASSET_DIR / f"{stem}.png", ASSET_DIR / f"{stem}.tiff")


def total_direct(point: MethodPoint) -> float:
    return point.direct_generate_ms + point.direct_bucket_merge_ms + point.direct_sort_reduce_ms


def draw_metric_card(fig: vg.Figure, x: int, y: int, w: int, h: int, title: str, value: str, lines: list[str], color: str) -> None:
    fig.rect(x, y, w, h, fill=f"{color}2", stroke=color, lw=3, rx=20)
    fig.text(x + 28, y + 22, title, size=30, fill="dark", weight="bold")
    fig.text(x + 28, y + 70, value, size=54, fill=color, weight="bold")
    fig.multiline(x + 30, y + 140, lines, size=24, fill="ink", leading=1.25)


def draw_quadrant_cell(fig: vg.Figure, x: int, y: int, w: int, h: int, point: MethodPoint, fill: str, stroke: str, rank: str) -> None:
    fig.rect(x, y, w, h, fill=fill, stroke=stroke, lw=3, rx=22)
    fig.text(x + 28, y + 24, point.label, size=34, fill="dark", weight="bold")
    fig.text(x + w - 26, y + 25, rank, size=30, fill=stroke, anchor="end", weight="bold")
    fig.text(x + 30, y + 84, fmt_ms(point.total_ms), size=56, fill=stroke, weight="bold")
    backend = point.backend if point.backend != "none" else "sort/reduce"
    fig.text(x + 30, y + 152, f"{point.threads} thread(s), {backend}", size=22, fill="muted", mono=True)
    if point.mode.startswith("direct"):
        fig.multiline(
            x + 30,
            y + 198,
            [
                f"generate {fmt_ms(point.direct_generate_ms)}",
                f"bucket/merge {fmt_ms(point.direct_bucket_merge_ms)}",
                f"sort/reduce {fmt_ms(point.direct_sort_reduce_ms)}",
            ],
            size=22,
            fill="ink",
            leading=1.20,
        )
    else:
        fig.multiline(
            x + 30,
            y + 198,
            [
                f"symbolic {fmt_ms(point.symbolic_ms)}",
                f"numeric {fmt_ms(point.numeric_ms)}",
                f"rel_L2 {point.rel_l2:.1e}",
            ],
            size=22,
            fill="ink",
            leading=1.20,
        )


def draw_quadrant_map(fig: vg.Figure, methods: dict[str, MethodPoint], x0: int, y0: int, w: int, h: int) -> None:
    gap = 86
    cell_w = int((w - 48 - gap) / 2)
    cell_h = int((h - 105 - gap) / 2)
    left = x0 + 24
    top = y0 + 82
    fig.text(x0, y0, "四象限：执行方式 × 符号结构复用", size=36, fill="dark", weight="bold")
    fig.text(x0, y0 + 48, "纵向看并行化，横向看是否复用 CSR/scatter", size=24, fill="muted")

    p_direct = methods["parallel_direct"]
    p_symbolic = methods["parallel_symbolic"]
    s_direct = methods["serial_direct"]
    s_symbolic = methods["serial_symbolic"]
    draw_quadrant_cell(fig, left, top, cell_w, cell_h, p_direct, "amber2", "amber", "Q3")
    draw_quadrant_cell(fig, left + cell_w + gap, top, cell_w, cell_h, p_symbolic, "teal2", "teal", "Q4")
    draw_quadrant_cell(fig, left, top + cell_h + gap, cell_w, cell_h, s_direct, "red2", "red", "Q1")
    draw_quadrant_cell(fig, left + cell_w + gap, top + cell_h + gap, cell_w, cell_h, s_symbolic, "sky2", "sky", "Q2")

    mid_y = top + cell_h + gap + cell_h / 2
    fig.line(left + cell_w + 12, mid_y, left + cell_w + gap - 12, mid_y, stroke="teal", lw=6, arrow=True)
    fig.text(left + cell_w + gap / 2, mid_y - 56, fmt_gain(s_direct.total_ms / s_symbolic.total_ms), size=34, fill="teal", anchor="middle", weight="bold")
    fig.text(left + cell_w + gap / 2, mid_y - 20, "有符号优于无符号", size=20, fill="muted", anchor="middle")

    right_x = left + cell_w + gap + cell_w / 2
    fig.line(right_x, top + cell_h + gap - 8, right_x, top + cell_h + 8, stroke="teal", lw=6, arrow=True)
    fig.text(right_x + 36, top + cell_h + gap / 2 - 20, fmt_gain(s_symbolic.total_ms / p_symbolic.total_ms), size=34, fill="teal", weight="bold")
    fig.text(right_x + 36, top + cell_h + gap / 2 + 18, "并行符号优于串行符号", size=20, fill="muted")

    top_mid_y = top + cell_h / 2
    fig.line(left + cell_w + 12, top_mid_y, left + cell_w + gap - 12, top_mid_y, stroke="teal", lw=4, arrow=True)
    fig.text(left + cell_w + gap / 2, top_mid_y - 50, fmt_gain(p_direct.total_ms / p_symbolic.total_ms), size=28, fill="teal", anchor="middle", weight="bold")
    fig.text(left + cell_w + gap / 2, top_mid_y - 18, "同核数 direct 对照", size=18, fill="muted", anchor="middle")


def figure_summary(methods: dict[str, MethodPoint]) -> vg.Figure:
    fig = vg.Figure(
        "月度汇报主图：四象限证明两条结论",
        "WindHub Tet4, Apple M4 Max, 14 physical cores; total time includes symbolic/direct construction and numeric assembly",
    )
    fig.title_block()
    draw_quadrant_map(fig, methods, 70, 185, 1160, 780)
    s_direct = methods["serial_direct"]
    s_symbolic = methods["serial_symbolic"]
    p_direct = methods["parallel_direct"]
    p_symbolic = methods["parallel_symbolic"]
    draw_metric_card(
        fig,
        1275,
        190,
        560,
        225,
        "结论 1",
        fmt_gain(s_direct.total_ms / s_symbolic.total_ms),
        [f"{fmt_ms(s_direct.total_ms)} → {fmt_ms(s_symbolic.total_ms)}", "CSR/scatter 复用", "抵消符号构建成本。"],
        "sky",
    )
    draw_metric_card(
        fig,
        1275,
        445,
        560,
        225,
        "结论 2",
        fmt_gain(s_symbolic.total_ms / p_symbolic.total_ms),
        [f"{fmt_ms(s_symbolic.total_ms)} → {fmt_ms(p_symbolic.total_ms)}", "并行化的是符号构建，", "不只是后续数值组装。"],
        "teal",
    )
    draw_metric_card(
        fig,
        1275,
        700,
        560,
        225,
        "补充对照",
        fmt_gain(p_direct.total_ms / p_symbolic.total_ms),
        [f"{fmt_ms(p_direct.total_ms)} → {fmt_ms(p_symbolic.total_ms)}", "同为 14 线程，", "有符号路线压低 sort/reduce。"],
        "amber",
    )
    fig.text(70, 1010, "数据源：results/2026-05-16-mentor-action-items/windhub_parallel_symbolic_direct.csv；数值正确性 rel_L2 ≤ 1.6e-16", size=22, fill="muted")
    return fig


def figure_quadrant_only(methods: dict[str, MethodPoint]) -> vg.Figure:
    fig = vg.Figure(
        "四象限组装策略图",
        "同一 WindHub 算例上比较串行/并行、有符号/无符号四条路径；越短越好",
    )
    fig.title_block()
    draw_quadrant_map(fig, methods, 115, 195, 1680, 790)
    return fig


def figure_cost_breakdown(methods: dict[str, MethodPoint]) -> vg.Figure:
    fig = vg.Figure(
        "时间构成解释：direct 路径主要输在贡献生成与排序归并",
        "每条横条为端到端总耗时；颜色区分 symbolic / numeric / direct sort-reduce 阶段",
    )
    fig.title_block()
    order = ["serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic"]
    labels = {
        "csr": ("CSR pattern", "sky"),
        "plan": ("scatter plan", "violet"),
        "numeric": ("numeric", "teal"),
        "generate": ("direct generate", "amber"),
        "bucket": ("bucket/merge", "orange"),
        "sort": ("sort/reduce", "red"),
    }
    max_total = max(methods[k].total_ms for k in order)
    x0, y0, bar_w, bar_h = 430, 275, 1180, 58
    gap = 112
    for i, key in enumerate(order):
        point = methods[key]
        y = y0 + i * gap
        fig.text(90, y + 7, point.label, size=28, fill="dark", weight="bold")
        fig.text(90, y + 45, f"{point.threads} thread(s)", size=20, fill="muted", mono=True)
        if point.mode.startswith("direct"):
            values = [
                ("generate", point.direct_generate_ms),
                ("bucket", point.direct_bucket_merge_ms),
                ("sort", point.direct_sort_reduce_ms),
            ]
        else:
            csr_part = as_float_value(point.symbolic_ms * (point.csr_bytes / max(1, point.csr_bytes + point.plan_bytes)))
            plan_part = max(0.0, point.symbolic_ms - csr_part)
            values = [("csr", csr_part), ("plan", plan_part), ("numeric", point.numeric_ms)]
        running = x0
        for name, value in values:
            width = max(1, bar_w * value / max_total)
            fig.rect(running, y, width, bar_h, fill=labels[name][1] + "2" if labels[name][1] + "2" in vg.PALETTE else labels[name][1], stroke=labels[name][1], lw=1.8, rx=8)
            if width > 110:
                fig.text(running + width / 2, y + 13, fmt_ms(value), size=20, fill="dark", anchor="middle")
            running += width
        fig.text(x0 + bar_w + 34, y + 10, fmt_ms(point.total_ms), size=34, fill="dark", weight="bold")
    lx, ly = 430, 800
    for j, (key, (label, color)) in enumerate(labels.items()):
        x = lx + (j % 3) * 350
        y = ly + (j // 3) * 58
        fig.rect(x, y, 42, 26, fill=color + "2" if color + "2" in vg.PALETTE else color, stroke=color, lw=2, rx=5)
        fig.text(x + 56, y - 2, label, size=23, fill="ink")
    fig.text(90, 965, "注：symbolic 阶段按 CSR/plan 字节比例拆分，仅用于解释构成；端到端总耗时来自原始 CSV。", size=22, fill="muted")
    return fig


def as_float_value(value: float) -> float:
    return float(value)


def as_nonzero(value: float) -> float:
    return max(0.0, float(value))


def figure_thread_scaling(methods: dict[str, MethodPoint]) -> vg.Figure:
    rows = read_csv(QUADRANT_CSV)
    direct = [r for r in rows if r.get("mode") == "direct_no_symbolic_parallel"]
    symbolic = [r for r in rows if r.get("mode") == "parallel_symbolic_reuse" and r.get("numeric_backend") == "cpu_atomic"]
    direct.sort(key=lambda r: int(r["threads"]))
    symbolic.sort(key=lambda r: int(r["threads"]))

    fig = vg.Figure(
        "线程扩展支撑：并行 symbolic 在物理核心范围内压低总耗时",
        "横轴为线程数；纵轴为端到端总耗时，对数尺度；灰线为串行有符号基线",
    )
    fig.title_block()
    x0, y0, w, h = 210, 240, 1420, 650
    fig.rect(x0, y0, w, h, fill="white", stroke="grid", lw=2, rx=8)
    values = [as_float(r, "amortized_total_ms") for r in direct + symbolic] + [methods["serial_symbolic"].total_ms]
    min_log, max_log = math.log10(450), math.log10(max(values) * 1.08)

    def x_map(thread: int) -> float:
        return x0 + 70 + (thread - 1) / 13 * (w - 150)

    def y_map(value: float) -> float:
        return y0 + h - 70 - (math.log10(value) - min_log) / (max_log - min_log) * (h - 135)

    for tick in [500, 1000, 2000, 5000, 10000]:
        if tick > max(values) * 1.2:
            continue
        y = y_map(tick)
        fig.line(x0 + 65, y, x0 + w - 55, y, stroke="grid", lw=1)
        fig.text(x0 + 25, y - 16, fmt_ms(tick), size=20, fill="muted", anchor="end")
    for tick in [1, 4, 7, 10, 14]:
        x = x_map(tick)
        fig.line(x, y0 + h - 74, x, y0 + h - 60, stroke="axis", lw=2)
        fig.text(x, y0 + h - 35, str(tick), size=22, fill="muted", anchor="middle")

    fig.line(x0 + 65, y0 + h - 70, x0 + w - 55, y0 + h - 70, stroke="axis", lw=2)
    fig.line(x0 + 65, y0 + 55, x0 + 65, y0 + h - 70, stroke="axis", lw=2)

    def draw_series(series: list[dict[str, str]], color: str, label: str) -> None:
        pts = [(x_map(int(r["threads"])), y_map(as_float(r, "amortized_total_ms"))) for r in series]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            fig.line(x1, y1, x2, y2, stroke=color, lw=4)
        for x, y in pts:
            fig.circle(x, y, 8, fill="white", stroke=color, lw=3)
        lx, ly = pts[-1]
        fig.text(lx + 18, ly - 18, label, size=24, fill=color, weight="bold")

    serial_y = y_map(methods["serial_symbolic"].total_ms)
    fig.line(x_map(1), serial_y, x_map(14), serial_y, stroke="muted", lw=3, dash=[12, 8])
    fig.text(x_map(14) + 20, serial_y - 18, "串行有符号基线", size=23, fill="muted", weight="bold")
    draw_series(direct, "amber", "并行无符号直接")
    draw_series(symbolic, "teal", "并行有符号+cpu_atomic")
    fig.text(x0 + 600, y0 + h + 12, "threads", size=24, fill="muted", anchor="middle")
    fig.text(92, 525, "total time", size=24, fill="muted")
    fig.text(210, 945, f"14 线程端点：parallel symbolic {fmt_ms(methods['parallel_symbolic'].total_ms)}；direct/no-symbolic {fmt_ms(methods['parallel_direct'].total_ms)}。", size=24, fill="dark")
    return fig


def figure_memory(methods: dict[str, MethodPoint]) -> vg.Figure:
    fig = vg.Figure(
        "内存生命周期支撑：无符号不等于低内存",
        "柱内为可解释数据结构字节数；direct/no-symbolic 的主要代价是 transient contribution buffer",
    )
    fig.title_block()
    order = ["serial_symbolic", "parallel_symbolic", "serial_direct", "parallel_direct"]
    x0, y0, w, h = 230, 275, 1370, 590
    max_gib = max(
        gib(p.csr_bytes + p.plan_bytes + p.symbolic_temp_bytes + p.direct_transient_bytes)
        for p in methods.values()
    )
    y_base = y0 + h
    colors = [("persistent CSR+scatter", "sky"), ("parallel symbolic temp", "violet"), ("direct transient", "red")]
    for i, key in enumerate(order):
        p = methods[key]
        x = x0 + i * 315
        values = [
            ("persistent CSR+scatter", gib(p.csr_bytes + p.plan_bytes), "sky"),
            ("parallel symbolic temp", gib(p.symbolic_temp_bytes), "violet"),
            ("direct transient", gib(p.direct_transient_bytes), "red"),
        ]
        y = y_base
        total = sum(v for _, v, _ in values)
        for _, value, color in values:
            if value <= 0:
                continue
            bh = h * value / (max_gib * 1.18)
            y -= bh
            fig.rect(x, y, 180, bh, fill=color + "2", stroke=color, lw=2, rx=5)
            if bh > 35:
                fig.text(x + 90, y + bh / 2 - 16, f"{value:.2f} GiB", size=22, fill="dark", anchor="middle")
        label_lines = p.label.split("+")
        fig.text(x + 90, y_base + 28, label_lines[0], size=21, fill="dark", anchor="middle")
        if len(label_lines) > 1:
            fig.text(x + 90, y_base + 58, "+" + label_lines[1], size=21, fill="dark", anchor="middle")
        fig.text(x + 90, y - 48, f"{total:.2f} GiB", size=30, fill="dark", anchor="middle", weight="bold")
    for tick in [0, 1, 2, 3]:
        y = y_base - h * tick / (max_gib * 1.18)
        fig.line(x0 - 30, y, x0 + 1210, y, stroke="grid", lw=1)
        fig.text(x0 - 52, y - 15, f"{tick}", size=21, fill="muted", anchor="end")
    fig.text(x0 - 135, y0 + 230, "GiB", size=24, fill="muted")
    lx, ly = 260, 955
    for j, (label, color) in enumerate(colors):
        x = lx + j * 430
        fig.rect(x, ly, 46, 28, fill=color + "2", stroke=color, lw=2, rx=5)
        fig.text(x + 62, ly - 3, label, size=23, fill="ink")
    fig.text(230, 1020, "注：这里不是 OS RSS；它把 persistent symbolic artifacts、parallel temporary 与 direct transient buffer 分开显示。", size=22, fill="muted")
    return fig


def figure_amortization() -> vg.Figure:
    rows = read_csv(AMORTIZATION_CSV)
    symbolic = {as_int(r, "assemblies_per_symbolic"): r for r in rows if r.get("mode") == "symbolic_reuse_serial"}
    direct = {as_int(r, "assemblies_per_symbolic"): r for r in rows if r.get("mode") == "direct_no_symbolic_serial"}
    assemblies = [1, 3, 10, 30]
    fig = vg.Figure(
        "重复组装支撑：symbolic 成本可摊销，direct sort/reduce 每次都重来",
        "同一稀疏结构重复组装时，符号复用收益从单次的 1.64x 增至 30 次的 8.09x",
    )
    fig.title_block()
    x0, y0, w, h = 250, 250, 1350, 620
    max_time = max(as_float(direct[a], "amortized_total_ms") for a in assemblies)
    max_gain = max(as_float(symbolic[a], "symbolic_gain_vs_direct") for a in assemblies)
    for i, a in enumerate(assemblies):
        x = x0 + i * 310
        sym = as_float(symbolic[a], "amortized_total_ms")
        dire = as_float(direct[a], "amortized_total_ms")
        gain = as_float(symbolic[a], "symbolic_gain_vs_direct")
        direct_h = h * dire / (max_time * 1.15)
        sym_h = h * sym / (max_time * 1.15)
        fig.rect(x, y0 + h - direct_h, 94, direct_h, fill="red2", stroke="red", lw=2, rx=8)
        fig.rect(x + 112, y0 + h - sym_h, 94, sym_h, fill="teal2", stroke="teal", lw=2, rx=8)
        fig.text(x + 103, y0 + h + 30, str(a), size=25, fill="dark", anchor="middle", weight="bold")
        fig.text(x + 102, y0 + h - max(direct_h, sym_h) - 52, fmt_gain(gain), size=31, fill="teal", anchor="middle", weight="bold")
        fig.text(x + 47, y0 + h - direct_h - 34, fmt_ms(dire), size=20, fill="red", anchor="middle")
        fig.text(x + 159, y0 + h - sym_h - 34, fmt_ms(sym), size=20, fill="teal", anchor="middle")
    for tick in [0, 2000, 4000, 6000]:
        y = y0 + h - h * tick / (max_time * 1.15)
        fig.line(x0 - 45, y, x0 + w - 120, y, stroke="grid", lw=1)
        fig.text(x0 - 65, y - 13, fmt_ms(tick), size=20, fill="muted", anchor="end")
    fig.text(890, 982, "assemblies per symbolic", size=25, fill="muted", anchor="middle")
    fig.rect(545, 930, 42, 26, fill="red2", stroke="red", lw=2, rx=5)
    fig.text(602, 925, "direct no-symbolic", size=23, fill="ink")
    fig.rect(925, 930, 42, 26, fill="teal2", stroke="teal", lw=2, rx=5)
    fig.text(982, 925, "symbolic reuse", size=23, fill="ink")
    fig.text(250, 1020, "数据源：results/2026-05-11-symbolic-numeric/symbolic_numeric_eval.csv。", size=22, fill="muted")
    return fig


def write_source_tables(methods: dict[str, MethodPoint]) -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    out = SOURCE_DIR / "quadrant_selected_rows.csv"
    fields = [
        "key",
        "label",
        "mode",
        "backend",
        "threads",
        "total_ms",
        "symbolic_ms",
        "numeric_ms",
        "direct_generate_ms",
        "direct_bucket_merge_ms",
        "direct_sort_reduce_ms",
        "csr_gib",
        "plan_gib",
        "symbolic_temp_gib",
        "direct_transient_gib",
        "rel_l2",
    ]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for key, point in methods.items():
            writer.writerow(
                {
                    "key": key,
                    "label": point.label,
                    "mode": point.mode,
                    "backend": point.backend,
                    "threads": point.threads,
                    "total_ms": f"{point.total_ms:.6f}",
                    "symbolic_ms": f"{point.symbolic_ms:.6f}",
                    "numeric_ms": f"{point.numeric_ms:.6f}",
                    "direct_generate_ms": f"{point.direct_generate_ms:.6f}",
                    "direct_bucket_merge_ms": f"{point.direct_bucket_merge_ms:.6f}",
                    "direct_sort_reduce_ms": f"{point.direct_sort_reduce_ms:.6f}",
                    "csr_gib": f"{gib(point.csr_bytes):.6f}",
                    "plan_gib": f"{gib(point.plan_bytes):.6f}",
                    "symbolic_temp_gib": f"{gib(point.symbolic_temp_bytes):.6f}",
                    "direct_transient_gib": f"{gib(point.direct_transient_bytes):.6f}",
                    "rel_l2": f"{point.rel_l2:.6e}",
                }
            )


def write_docs(methods: dict[str, MethodPoint]) -> None:
    serial_gain = methods["serial_direct"].total_ms / methods["serial_symbolic"].total_ms
    parallel_gain = methods["serial_symbolic"].total_ms / methods["parallel_symbolic"].total_ms
    parallel_direct_gain = methods["parallel_direct"].total_ms / methods["parallel_symbolic"].total_ms
    manifest = {
        "figure_contract": {
            "core_conclusion": "符号组装+数值组装优于无符号直接组装；并行符号组装+数值组装优于串行符号组装+数值组装。",
            "archetype": "schematic-led composite + quantitative grid",
            "backend": "Python SVG/PDF/PNG/TIFF using the same Python drawing backend",
            "review_risks": [
                "不要把四象限图解释成跨平台绝对性能排名。",
                "direct/no-symbolic 不是 dense matrix，而是 contribution list -> sort/reduce -> CSR。",
                "内存图显示可解释数据结构字节数，不是 OS RSS。",
            ],
        },
        "source_files": [
            str(QUADRANT_CSV.relative_to(CPU_ROOT)),
            str(AMORTIZATION_CSV.relative_to(CPU_ROOT)),
        ],
        "headline_metrics": {
            "serial_symbolic_vs_serial_direct_speedup": serial_gain,
            "parallel_symbolic_vs_serial_symbolic_speedup": parallel_gain,
            "parallel_symbolic_vs_parallel_direct_speedup": parallel_direct_gain,
        },
        "outputs": {
            "fig00_monthly_report_summary_slide": "主图，一页汇报用",
            "fig01_four_quadrant_strategy_map": "纯四象限图",
            "fig02_cost_breakdown": "端到端时间构成",
            "fig03_thread_scaling": "线程扩展支撑",
            "fig04_memory_lifecycle": "内存生命周期支撑",
            "fig05_symbolic_reuse_amortization": "重复组装摊销支撑",
        },
    }
    (ASSET_DIR / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_ROOT / "figure_contract.md").write_text(
        "\n".join(
            [
                "# 月度汇报四象限图 figure contract",
                "",
                "## 核心结论",
                "",
                "- 符号组装 + 数值组装优于无符号直接组装。",
                "- 并行符号组装 + 数值组装优于串行符号组装 + 数值组装。",
                "",
                "## 证据链",
                "",
                f"- 串行有符号相对串行无符号：{fmt_gain(serial_gain)}。",
                f"- 并行有符号相对串行有符号：{fmt_gain(parallel_gain)}。",
                f"- 同为 14 线程，并行有符号相对并行无符号：{fmt_gain(parallel_direct_gain)}。",
                "",
                "## 边界",
                "",
                "- 主图使用同一 WindHub / Apple M4 Max 结果，不用于宣称 Intel 或 Windows 的绝对时间。",
                "- 内存图显示可解释数据结构字节数，不是操作系统 RSS。",
                "- direct/no-symbolic 路径是 `(row,col,value)` contribution list 排序归并，不是 dense matrix。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (OUT_ROOT / "README.md").write_text(
        "\n".join(
            [
                "# 2026-05-27 月度汇报四象限组装策略图",
                "",
                "本目录保存月度汇报用的四象限图和支撑图。主图锚定同一份 WindHub / Apple M4 Max 结果，辅助图解释时间构成、线程扩展、内存生命周期和重复组装摊销。",
                "",
                "## 主要输出",
                "",
                "- `assets/fig00_monthly_report_summary_slide.*`：一页汇报主图。",
                "- `assets/fig01_four_quadrant_strategy_map.*`：纯四象限图。",
                "- `assets/fig02_cost_breakdown.*`：四类路径的端到端耗时构成。",
                "- `assets/fig03_thread_scaling.*`：并行有符号与并行无符号随线程数变化。",
                "- `assets/fig04_memory_lifecycle.*`：persistent / temporary / transient 内存拆分。",
                "- `assets/fig05_symbolic_reuse_amortization.*`：重复组装时 symbolic reuse 摊销收益。",
                "",
                "## 数据源",
                "",
                f"- `{QUADRANT_CSV.relative_to(CPU_ROOT)}`",
                f"- `{AMORTIZATION_CSV.relative_to(CPU_ROOT)}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    global OUT_ROOT, ASSET_DIR, SOURCE_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()
    OUT_ROOT = args.out_root
    ASSET_DIR = OUT_ROOT / "assets"
    SOURCE_DIR = OUT_ROOT / "source_data"

    methods = load_methods()
    write_source_tables(methods)
    export_all(figure_summary(methods), "fig00_monthly_report_summary_slide")
    export_all(figure_quadrant_only(methods), "fig01_four_quadrant_strategy_map")
    export_all(figure_cost_breakdown(methods), "fig02_cost_breakdown")
    export_all(figure_thread_scaling(methods), "fig03_thread_scaling")
    export_all(figure_memory(methods), "fig04_memory_lifecycle")
    export_all(figure_amortization(), "fig05_symbolic_reuse_amortization")
    write_docs(methods)


if __name__ == "__main__":
    main()
