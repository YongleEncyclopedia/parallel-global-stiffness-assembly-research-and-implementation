#!/usr/bin/env python3
"""生成符号组装、数值组装和无符号直接组装的项目级示意图。

本脚本用 Python 后端直接绘制 SVG，并用同一套图元导出 PDF、PNG 和 TIFF。
图的内容锚定当前 C++ 实现中的 CSR、AssemblyPlan::scatter 和 DirectContribution
sort/reduce 路径，不依赖 benchmark 数据。
"""

from __future__ import annotations

import argparse
import html
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    raise SystemExit("Pillow is required for PNG/TIFF export. Use the Codex bundled Python.") from exc

try:
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas as pdf_canvas
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    raise SystemExit("reportlab is required for PDF export. Use the Codex bundled Python.") from exc


W = 1800
H = 1100
SCALE = 2

PALETTE = {
    "ink": "#1f2933",
    "muted": "#667085",
    "grid": "#d7dde4",
    "panel": "#f7f9fb",
    "panel2": "#eef3f8",
    "blue": "#3f7fba",
    "blue2": "#d8e8f7",
    "green": "#4d9a74",
    "green2": "#dff1e8",
    "orange": "#d8843a",
    "orange2": "#f6e3cf",
    "rose": "#b65a6a",
    "rose2": "#f2d9df",
    "yellow": "#f0c95a",
    "white": "#ffffff",
}

FONT_CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_ASCII = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_ASCII_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


@dataclass
class Op:
    kind: str
    args: dict


def has_cjk(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def pdf_color(value: str):
    r, g, b = hex_to_rgb(value)
    return colors.Color(r / 255, g / 255, b / 255)


class Figure:
    def __init__(self, title: str, subtitle: str):
        self.title = title
        self.subtitle = subtitle
        self.ops: list[Op] = []

    def rect(self, x, y, w, h, fill="white", stroke="grid", lw=2, rx=18):
        self.ops.append(Op("rect", dict(x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, lw=lw, rx=rx)))

    def line(self, x1, y1, x2, y2, stroke="muted", lw=3, arrow=False, dash: Iterable[int] | None = None):
        self.ops.append(
            Op("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, lw=lw, arrow=arrow, dash=list(dash or [])))
        )

    def circle(self, x, y, r, fill="white", stroke="ink", lw=2):
        self.ops.append(Op("circle", dict(x=x, y=y, r=r, fill=fill, stroke=stroke, lw=lw)))

    def polygon(self, pts, fill="white", stroke="ink", lw=2):
        self.ops.append(Op("polygon", dict(pts=pts, fill=fill, stroke=stroke, lw=lw)))

    def text(self, x, y, text, size=34, fill="ink", weight="regular", anchor="start", mono=False):
        self.ops.append(
            Op("text", dict(x=x, y=y, text=text, size=size, fill=fill, weight=weight, anchor=anchor, mono=mono))
        )

    def multiline(self, x, y, lines, size=30, fill="ink", leading=1.35, weight="regular", mono=False):
        for i, line in enumerate(lines):
            self.text(x, y + i * size * leading, line, size=size, fill=fill, weight=weight, mono=mono)

    def chip(self, x, y, text, fill="panel2", stroke="grid", width=None):
        w = width or max(150, 18 * len(text) + 36)
        self.rect(x, y, w, 48, fill=fill, stroke=stroke, lw=1.5, rx=15)
        self.text(x + w / 2, y + 15, text, size=24, fill="ink", anchor="middle", mono=True)

    def title_block(self):
        self.text(70, 54, self.title, size=48, fill="ink", weight="bold")
        self.text(70, 114, self.subtitle, size=27, fill="muted")
        self.line(70, 150, W - 70, 150, stroke="grid", lw=2)

    def export_svg(self, path: Path):
        marker = """
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#667085"/>
    </marker>
  </defs>"""
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            marker,
            f'<rect width="{W}" height="{H}" fill="{PALETTE["white"]}"/>',
        ]
        for op in self.ops:
            a = op.args
            if op.kind == "rect":
                parts.append(
                    f'<rect x="{a["x"]}" y="{a["y"]}" width="{a["w"]}" height="{a["h"]}" '
                    f'rx="{a["rx"]}" fill="{PALETTE[a["fill"]]}" stroke="{PALETTE[a["stroke"]]}" '
                    f'stroke-width="{a["lw"]}"/>'
                )
            elif op.kind == "line":
                dash = f' stroke-dasharray="{",".join(map(str, a["dash"]))}"' if a["dash"] else ""
                marker_end = ' marker-end="url(#arrow)"' if a["arrow"] else ""
                parts.append(
                    f'<line x1="{a["x1"]}" y1="{a["y1"]}" x2="{a["x2"]}" y2="{a["y2"]}" '
                    f'stroke="{PALETTE[a["stroke"]]}" stroke-width="{a["lw"]}" '
                    f'stroke-linecap="round"{dash}{marker_end}/>'
                )
            elif op.kind == "circle":
                parts.append(
                    f'<circle cx="{a["x"]}" cy="{a["y"]}" r="{a["r"]}" fill="{PALETTE[a["fill"]]}" '
                    f'stroke="{PALETTE[a["stroke"]]}" stroke-width="{a["lw"]}"/>'
                )
            elif op.kind == "polygon":
                pts = " ".join(f"{x},{y}" for x, y in a["pts"])
                parts.append(
                    f'<polygon points="{pts}" fill="{PALETTE[a["fill"]]}" stroke="{PALETTE[a["stroke"]]}" '
                    f'stroke-width="{a["lw"]}" stroke-linejoin="round"/>'
                )
            elif op.kind == "text":
                family = "Menlo, Consolas, monospace" if a["mono"] else "Arial Unicode MS, Hiragino Sans GB, Arial, sans-serif"
                weight = "700" if a["weight"] == "bold" else "400"
                parts.append(
                    f'<text x="{a["x"]}" y="{a["y"] + a["size"]}" fill="{PALETTE[a["fill"]]}" '
                    f'font-family="{family}" font-size="{a["size"]}" font-weight="{weight}" '
                    f'text-anchor="{a["anchor"]}">{html.escape(a["text"])}</text>'
                )
        parts.append("</svg>\n")
        path.write_text("\n".join(parts), encoding="utf-8")

    def export_png_tiff(self, png_path: Path, tiff_path: Path):
        image = Image.new("RGB", (W * SCALE, H * SCALE), PALETTE["white"])
        draw = ImageDraw.Draw(image)

        def sc(v):
            return int(round(v * SCALE))

        def font(size, weight="regular", mono=False):
            if mono:
                source = FONT_ASCII_BOLD if weight == "bold" and Path(FONT_ASCII_BOLD).exists() else FONT_ASCII
            else:
                source = FONT_CJK if Path(FONT_CJK).exists() else FONT_ASCII
            return ImageFont.truetype(source, sc(size))

        for op in self.ops:
            a = op.args
            if op.kind == "rect":
                box = [sc(a["x"]), sc(a["y"]), sc(a["x"] + a["w"]), sc(a["y"] + a["h"])]
                draw.rounded_rectangle(
                    box,
                    radius=sc(a["rx"]),
                    fill=PALETTE[a["fill"]],
                    outline=PALETTE[a["stroke"]],
                    width=max(1, sc(a["lw"])),
                )
            elif op.kind == "line":
                xy = [sc(a["x1"]), sc(a["y1"]), sc(a["x2"]), sc(a["y2"])]
                if a["dash"]:
                    draw_dashed_line(draw, xy, PALETTE[a["stroke"]], max(1, sc(a["lw"])), [sc(d) for d in a["dash"]])
                else:
                    draw.line(xy, fill=PALETTE[a["stroke"]], width=max(1, sc(a["lw"])))
                if a["arrow"]:
                    draw_arrowhead(draw, a["x1"], a["y1"], a["x2"], a["y2"], PALETTE[a["stroke"]], SCALE)
            elif op.kind == "circle":
                box = [sc(a["x"] - a["r"]), sc(a["y"] - a["r"]), sc(a["x"] + a["r"]), sc(a["y"] + a["r"])]
                draw.ellipse(box, fill=PALETTE[a["fill"]], outline=PALETTE[a["stroke"]], width=max(1, sc(a["lw"])))
            elif op.kind == "polygon":
                draw.polygon([(sc(x), sc(y)) for x, y in a["pts"]], fill=PALETTE[a["fill"]], outline=PALETTE[a["stroke"]])
            elif op.kind == "text":
                fnt = font(a["size"], a["weight"], a["mono"])
                x = sc(a["x"])
                y = sc(a["y"])
                if a["anchor"] == "middle":
                    bbox = draw.textbbox((0, 0), a["text"], font=fnt)
                    x -= (bbox[2] - bbox[0]) // 2
                draw.text((x, y), a["text"], font=fnt, fill=PALETTE[a["fill"]])
        image.save(png_path, dpi=(300, 300))
        image.save(tiff_path, dpi=(600, 600), compression="tiff_lzw")

    def export_pdf(self, path: Path):
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        c = pdf_canvas.Canvas(str(path), pagesize=(W, H))

        def yflip(y):
            return H - y

        for op in self.ops:
            a = op.args
            if op.kind == "rect":
                c.setFillColor(pdf_color(PALETTE[a["fill"]]))
                c.setStrokeColor(pdf_color(PALETTE[a["stroke"]]))
                c.setLineWidth(a["lw"])
                c.roundRect(a["x"], yflip(a["y"] + a["h"]), a["w"], a["h"], a["rx"], fill=1, stroke=1)
            elif op.kind == "line":
                c.setStrokeColor(pdf_color(PALETTE[a["stroke"]]))
                c.setLineWidth(a["lw"])
                c.line(a["x1"], yflip(a["y1"]), a["x2"], yflip(a["y2"]))
                if a["arrow"]:
                    draw_pdf_arrowhead(c, a["x1"], yflip(a["y1"]), a["x2"], yflip(a["y2"]), PALETTE[a["stroke"]])
            elif op.kind == "circle":
                c.setFillColor(pdf_color(PALETTE[a["fill"]]))
                c.setStrokeColor(pdf_color(PALETTE[a["stroke"]]))
                c.setLineWidth(a["lw"])
                c.circle(a["x"], yflip(a["y"]), a["r"], fill=1, stroke=1)
            elif op.kind == "polygon":
                p = c.beginPath()
                pts = a["pts"]
                p.moveTo(pts[0][0], yflip(pts[0][1]))
                for x, y in pts[1:]:
                    p.lineTo(x, yflip(y))
                p.close()
                c.setFillColor(pdf_color(PALETTE[a["fill"]]))
                c.setStrokeColor(pdf_color(PALETTE[a["stroke"]]))
                c.setLineWidth(a["lw"])
                c.drawPath(p, fill=1, stroke=1)
            elif op.kind == "text":
                font_name = "STSong-Light" if has_cjk(a["text"]) else ("Helvetica-Bold" if a["weight"] == "bold" else "Helvetica")
                c.setFont(font_name, a["size"])
                c.setFillColor(pdf_color(PALETTE[a["fill"]]))
                x = a["x"]
                if a["anchor"] == "middle":
                    x -= pdfmetrics.stringWidth(a["text"], font_name, a["size"]) / 2
                c.drawString(x, yflip(a["y"] + a["size"]), a["text"])
        c.showPage()
        c.save()


def draw_dashed_line(draw, xy, fill, width, dash):
    x1, y1, x2, y2 = xy
    total = math.hypot(x2 - x1, y2 - y1)
    if total <= 0:
        return
    dx = (x2 - x1) / total
    dy = (y2 - y1) / total
    pos = 0
    draw_on = True
    idx = 0
    while pos < total:
        seg = dash[idx % len(dash)]
        end = min(total, pos + seg)
        if draw_on:
            draw.line([x1 + dx * pos, y1 + dy * pos, x1 + dx * end, y1 + dy * end], fill=fill, width=width)
        draw_on = not draw_on
        pos = end
        idx += 1


def draw_arrowhead(draw, x1, y1, x2, y2, fill, scale):
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 16 * scale
    x2 *= scale
    y2 *= scale
    pts = [
        (x2, y2),
        (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45)),
        (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45)),
    ]
    draw.polygon(pts, fill=fill)


def draw_pdf_arrowhead(c, x1, y1, x2, y2, fill):
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 16
    pts = [
        (x2, y2),
        (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45)),
        (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45)),
    ]
    p = c.beginPath()
    p.moveTo(*pts[0])
    p.lineTo(*pts[1])
    p.lineTo(*pts[2])
    p.close()
    c.setFillColor(pdf_color(fill))
    c.drawPath(p, fill=1, stroke=0)


def panel(fig: Figure, x, y, w, h, title, color="blue"):
    fig.rect(x, y, w, h, fill="panel", stroke="grid", lw=2, rx=24)
    fig.rect(x + 18, y + 18, w - 36, 52, fill=f"{color}2", stroke=f"{color}2", lw=0, rx=16)
    fig.text(x + 34, y + 29, title, size=28, fill="ink", weight="bold")


def draw_mesh(fig: Figure, x, y):
    fig.polygon([(x + 60, y + 230), (x + 150, y + 70), (x + 260, y + 230)], fill="blue2", stroke="blue", lw=3)
    fig.polygon([(x + 260, y + 230), (x + 150, y + 70), (x + 360, y + 80), (x + 430, y + 230)], fill="panel2", stroke="blue", lw=3)
    nodes = [(x + 60, y + 230, "n0"), (x + 150, y + 70, "n1"), (x + 260, y + 230, "n2"), (x + 360, y + 80, "n3"), (x + 430, y + 230, "n4")]
    for nx, ny, label in nodes:
        fig.circle(nx, ny, 18, fill="white", stroke="blue", lw=3)
        fig.text(nx, ny + 24, label, size=20, fill="muted", anchor="middle", mono=True)
    fig.multiline(
        x + 28,
        y + 300,
        ["element_dofs(e)", "每节点 3 DOF", "dofs = [u_x,u_y,u_z]"],
        size=26,
        fill="ink",
        mono=False,
    )


def draw_csr_grid(fig: Figure, x, y, cell=43, mode="pattern"):
    pattern = {(0, 0), (0, 1), (0, 3), (1, 0), (1, 1), (1, 2), (2, 1), (2, 2), (2, 5), (3, 0), (3, 3), (3, 4), (4, 3), (4, 4), (5, 2), (5, 5)}
    for r in range(6):
        for c in range(6):
            fill = "white"
            if (r, c) in pattern:
                fill = "blue2" if mode == "pattern" else "green2"
            fig.rect(x + c * cell, y + r * cell, cell, cell, fill=fill, stroke="grid", lw=1, rx=0)
            if (r, c) in pattern and mode == "values":
                label = f"{(r + c + 1) / 10:.1f}"
                fig.text(x + c * cell + cell / 2, y + r * cell + 8, label, size=18, fill="green", anchor="middle", mono=True)
            elif (r, c) in pattern and mode == "pattern":
                fig.circle(x + c * cell + cell / 2, y + r * cell + cell / 2, 7, fill="blue", stroke="blue", lw=1)
    fig.text(x - 25, y - 8, "row", size=18, fill="muted", mono=True)
    fig.text(x + 6 * cell + 8, y + 6 * cell - 5, "col", size=18, fill="muted", mono=True)


def draw_ke_grid(fig: Figure, x, y, cell=42):
    for r in range(4):
        for c in range(4):
            fill = "green2" if r == c else "white"
            fig.rect(x + c * cell, y + r * cell, cell, cell, fill=fill, stroke="grid", lw=1, rx=0)
            fig.text(x + c * cell + cell / 2, y + r * cell + 8, f"k{r}{c}", size=17, fill="green", anchor="middle", mono=True)


def draw_contribution_table(fig: Figure, x, y, color="orange"):
    rows = ["(r0,c0,v0)", "(r0,c1,v1)", "(r0,c0,v2)", "...", "(rn,cm,vq)"]
    fig.rect(x, y, 270, 245, fill="white", stroke=f"{color}", lw=2, rx=18)
    fig.text(x + 22, y + 20, "DirectContribution[]", size=24, fill="ink", weight="bold", mono=True)
    for i, row in enumerate(rows):
        fig.rect(x + 24, y + 65 + i * 32, 220, 27, fill=f"{color}2", stroke="white", lw=1, rx=8)
        fig.text(x + 38, y + 66 + i * 32, row, size=19, fill="ink", mono=True)


def make_symbolic() -> Figure:
    fig = Figure(
        "符号组装 / Symbolic assembly",
        "Topology and DOF analysis freeze CSR structure and scatter addresses; no Ke values are computed.",
    )
    fig.title_block()
    panel(fig, 70, 190, 410, 780, "1  Mesh topology + DofMap", "blue")
    draw_mesh(fig, 85, 255)
    fig.chip(110, 800, "Mesh::elements", fill="blue2", stroke="blue", width=210)
    fig.chip(112, 862, "constants::DOFS_PER_NODE = 3", fill="blue2", stroke="blue", width=330)

    fig.line(492, 420, 595, 360, stroke="blue", lw=4, arrow=True)
    fig.line(492, 740, 595, 710, stroke="blue", lw=4, arrow=True)

    panel(fig, 590, 210, 505, 360, "2  CsrMatrix::build_sparsity()", "blue")
    draw_csr_grid(fig, 640, 315, 38, mode="pattern")
    fig.multiline(
        905,
        312,
        ["rows: sorted unique DOFs", "row_offsets + col_indices", "values.assign(nnz, 0)"],
        size=25,
        fill="ink",
        mono=False,
    )
    fig.chip(905, 455, "CSR pattern only", fill="blue2", stroke="blue", width=245)

    panel(fig, 590, 620, 505, 310, "3  build_assembly_plan()", "blue")
    fig.multiline(
        625,
        705,
        ["plan.dofs caches element_dofs(e)", "plan.scatter maps Ke(i,j) -> CSR value index", "scatter uses csr.find_position(r,c)"],
        size=25,
        fill="ink",
    )
    fig.rect(924, 718, 122, 116, fill="white", stroke="blue", lw=2, rx=12)
    for i, label in enumerate(["(0,0)->p8", "(0,1)->p9", "(1,0)->p15"]):
        fig.text(938, 735 + i * 31, label, size=19, fill="blue", mono=True)

    fig.line(1110, 410, 1260, 510, stroke="blue", lw=4, arrow=True)
    fig.line(1110, 760, 1260, 640, stroke="blue", lw=4, arrow=True)
    panel(fig, 1265, 340, 465, 390, "Output: SymbolicArtifacts", "blue")
    fig.multiline(
        1305,
        435,
        ["csr: row_offsets, col_indices, zero values", "plan: element_offsets, dofs, scatter", "mode, threads, csr_ms, plan_ms"],
        size=27,
        fill="ink",
    )
    fig.rect(1325, 625, 260, 58, fill="rose2", stroke="rose", lw=2, rx=18)
    fig.text(1455, 640, "No Ke here", size=27, fill="rose", anchor="middle", weight="bold")
    fig.line(1338, 682, 1570, 630, stroke="rose", lw=3, dash=[12, 8])
    fig.text(70, 1028, "Code anchors: CsrMatrix::build_sparsity*, AssemblyPlan::scatter, values.assign(col_indices.size(), 0)", size=22, fill="muted", mono=True)
    return fig


def make_numeric() -> Figure:
    fig = Figure(
        "数值组装 / Numeric assembly",
        "Given CSR/scatter from symbolic assembly, compute element Ke and accumulate into fixed CSR values.",
    )
    fig.title_block()
    panel(fig, 70, 250, 420, 560, "1  Reuse symbolic artifacts", "green")
    draw_csr_grid(fig, 120, 360, 38, mode="pattern")
    fig.multiline(
        120,
        650,
        ["CSR structure is fixed", "values are zeroed, not resized", "scatter gives write positions"],
        size=27,
        fill="ink",
    )
    fig.chip(125, 755, "prepare() + zero_values()", fill="green2", stroke="green", width=300)

    fig.line(505, 530, 640, 530, stroke="green", lw=4, arrow=True)
    panel(fig, 640, 230, 470, 610, "2  Element loop", "green")
    fig.chip(685, 320, "compute_element_matrix(mesh,e)", fill="green2", stroke="green", width=380)
    draw_ke_grid(fig, 755, 410, 48)
    fig.multiline(
        690,
        640,
        ["linear_elastic_solid", "Tet4: constant-strain", "Hex8: 2x2x2 Gauss"],
        size=27,
        fill="ink",
    )
    fig.line(870, 610, 870, 690, stroke="green", lw=3, arrow=True)

    fig.line(1122, 530, 1265, 530, stroke="green", lw=4, arrow=True)
    panel(fig, 1265, 205, 465, 700, "3  Scatter-add to CSR values", "green")
    draw_csr_grid(fig, 1320, 330, 42, mode="values")
    fig.multiline(
        1305,
        630,
        ["p = scatter[i*edofs + j]", "values[p] += Ke[i,j]", "row_ptr / col_idx unchanged"],
        size=27,
        fill="ink",
    )
    fig.chip(1305, 755, "cpu_serial", fill="green2", stroke="green", width=180)
    fig.chip(1502, 755, "cpu_atomic", fill="green2", stroke="green", width=180)
    fig.chip(1305, 820, "private_csr", fill="panel2", stroke="grid", width=190)
    fig.chip(1510, 820, "lock_guard", fill="panel2", stroke="grid", width=175)
    fig.text(70, 1028, "Code anchors: SerialAssembler::assemble(), AtomicAssembler::assemble(), add_element_to_result(), plan.element_scatter_ptr(e)", size=22, fill="muted", mono=True)
    return fig


def make_direct() -> Figure:
    fig = Figure(
        "无符号直接组装 / Direct no-symbolic assembly",
        "Each run emits element contributions, then sort/reduces them into CSR; no precomputed CSR pattern or scatter plan is reused.",
    )
    fig.title_block()
    panel(fig, 70, 230, 425, 610, "1  Per-element generation", "orange")
    draw_mesh(fig, 85, 295)
    fig.chip(110, 660, "element_dofs(e)", fill="orange2", stroke="orange", width=230)
    fig.chip(110, 725, "compute Ke", fill="orange2", stroke="orange", width=180)
    fig.text(120, 802, "No input CSR / scatter", size=27, fill="rose", weight="bold")

    fig.line(508, 535, 620, 535, stroke="orange", lw=4, arrow=True)
    panel(fig, 620, 220, 485, 650, "2  Transient contribution buffer", "orange")
    draw_contribution_table(fig, 690, 335)
    fig.multiline(
        690,
        635,
        ["parallel path: per-thread lists", "bucket by row range", "memory: direct_transient_bytes"],
        size=27,
        fill="ink",
    )
    fig.chip(695, 770, "not dense K[n][n]", fill="rose2", stroke="rose", width=265)

    fig.line(1120, 535, 1265, 535, stroke="orange", lw=4, arrow=True)
    panel(fig, 1265, 195, 465, 735, "3  Sort / reduce / build CSR", "orange")
    fig.rect(1310, 300, 365, 85, fill="orange2", stroke="orange", lw=2, rx=18)
    fig.text(1492, 325, "sort by (row, col)", size=28, fill="ink", anchor="middle", weight="bold")
    fig.line(1492, 390, 1492, 455, stroke="orange", lw=4, arrow=True)
    fig.rect(1310, 455, 365, 90, fill="orange2", stroke="orange", lw=2, rx=18)
    fig.text(1492, 484, "reduce duplicates", size=28, fill="ink", anchor="middle", weight="bold")
    fig.line(1492, 550, 1492, 615, stroke="orange", lw=4, arrow=True)
    draw_csr_grid(fig, 1335, 630, 39, mode="values")
    fig.multiline(
        1310,
        890,
        ["final row_offsets, col_indices, values", "timed as generate + bucket + sort/reduce"],
        size=23,
        fill="ink",
    )
    fig.text(70, 1028, "Code anchors: assemble_direct_no_symbolic_once/parallel(), DirectContribution, reduce_direct_contributions(), bucket_merge_ms, sort_reduce_ms", size=22, fill="muted", mono=True)
    return fig


def export_all(fig: Figure, out_dir: Path, stem: str):
    fig.export_svg(out_dir / f"{stem}.svg")
    fig.export_pdf(out_dir / f"{stem}.pdf")
    fig.export_png_tiff(out_dir / f"{stem}.png", out_dir / f"{stem}.tiff")


def qa_outputs(out_dir: Path, stems: list[str]) -> dict:
    checks = {}
    for stem in stems:
        svg = out_dir / f"{stem}.svg"
        png = out_dir / f"{stem}.png"
        tiff = out_dir / f"{stem}.tiff"
        pdf = out_dir / f"{stem}.pdf"
        image = Image.open(png).convert("RGB")
        bbox = Image.eval(image, lambda px: 255 - px).getbbox()
        checks[stem] = {
            "svg_exists": svg.exists(),
            "svg_has_editable_text": "<text " in svg.read_text(encoding="utf-8"),
            "svg_has_no_embedded_raster": "<image" not in svg.read_text(encoding="utf-8"),
            "pdf_exists": pdf.exists() and pdf.stat().st_size > 1000,
            "png_size": image.size,
            "png_nonblank": bbox is not None,
            "tiff_exists": tiff.exists() and tiff.stat().st_size > 1000,
        }
    return checks


def write_manifest(out_dir: Path, qa: dict):
    manifest = {
        "backend": "Python",
        "drawing_stack": ["Python stdlib SVG writer", "reportlab PDF", "Pillow PNG/TIFF"],
        "figure_contract": {
            "core_conclusion": "The project separates topology/address construction, value accumulation, and direct contribution sort/reduce into distinct assembly paths.",
            "archetype": "schematic-led composite",
            "target_output": "SVG with editable text plus PDF, PNG, and TIFF exports",
            "statistics_needed": "none; schematic only",
            "source_data_needed": "current C++ implementation and docs, not benchmark measurements",
            "image_integrity_notes": "No raster data in SVG; diagrams are conceptual, not quantitative plots.",
            "reviewer_risk": "Do not read the direct no-symbolic path as dense-matrix assembly; it is contribution-list sort/reduce to CSR.",
        },
        "source_anchors": [
            "docs/cpu/symbolic_numeric_assembly.md lines 11-14",
            "src/core/csr_matrix.cpp values.assign(col_indices.size(), 0) and build_sparsity*",
            "src/assembly/assembly_plan.cpp build_assembly_plan* and scatter via csr.find_position",
            "src/backends/cpu/serial_assembler.cpp compute_element_matrix + add_element_to_result",
            "src/backends/cpu/atomic_assembler.cpp scatter-based atomic values update",
            "src/assembly/symbolic_numeric_eval.cpp DirectContribution generation, bucket, sort/reduce, CSR build",
        ],
        "qa": qa,
    }
    (out_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    default_out = Path(__file__).resolve().parents[1] / "reports" / "2026-05-27-assembly-schematics" / "assets"
    parser.add_argument("--out-dir", type=Path, default=default_out, help="Directory for SVG/PDF/PNG/TIFF outputs.")
    parser.add_argument("--qa-json", type=Path, default=None, help="Optional path for QA JSON summary.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    figures = {
        "symbolic_assembly_schematic": make_symbolic(),
        "numeric_assembly_schematic": make_numeric(),
        "direct_no_symbolic_assembly_schematic": make_direct(),
    }
    for stem, fig in figures.items():
        export_all(fig, out_dir, stem)
    qa = qa_outputs(out_dir, list(figures))
    write_manifest(out_dir, qa)
    if args.qa_json:
        args.qa_json.write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps({"out_dir": str(out_dir), "qa": qa}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
