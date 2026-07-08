#!/usr/bin/env python3
"""Draw a Chinese pseudocode-style schematic for the CSC3 assembly demo."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon


DEMO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = DEMO_ROOT / "figures"


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
        }
    )


def rounded_box(ax, xy, wh, face, edge, lw=1.4, radius=0.014):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.010,rounding_size={radius}",
        linewidth=lw,
        edgecolor=edge,
        facecolor=face,
        transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def arrow(ax, x0, y0, x1, y1, color="#5A6268", lw=1.6):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        xycoords=ax.transAxes,
        textcoords=ax.transAxes,
        arrowprops=dict(arrowstyle="-|>", lw=lw, color=color, shrinkA=0, shrinkB=0),
    )


def add_wrapped(ax, x, y, text, width, *, size=12, color="#202020", weight="normal", lineheight=0.030):
    lines = []
    for part in text.split("\n"):
        lines.extend(wrap(part, width=width) or [""])
    for idx, line in enumerate(lines):
        ax.text(
            x,
            y - idx * lineheight,
            line,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=size,
            color=color,
            fontweight=weight,
        )
    return y - len(lines) * lineheight


def draw_matrix_icon(ax, x, y, size):
    cell = size / 4
    for r in range(4):
        for c in range(4):
            face = "#E9F6D7" if r <= c else "#F2F4F7"
            edge = "#AAB2BA"
            ax.add_patch(
                plt.Rectangle(
                    (x + c * cell, y - (r + 1) * cell),
                    cell,
                    cell,
                    transform=ax.transAxes,
                    facecolor=face,
                    edgecolor=edge,
                    linewidth=0.8,
                )
            )
    tri = Polygon(
        [
            (x, y),
            (x + size, y),
            (x + size, y - size),
        ],
        closed=True,
        transform=ax.transAxes,
        facecolor="none",
        edgecolor="#76B900",
        linewidth=2.0,
    )
    ax.add_patch(tri)


def draw() -> list[Path]:
    configure_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(12.8, 7.2), dpi=240)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()

    dark = "#111111"
    mid = "#4F565C"
    axis = "#5A6268"
    green = "#76B900"
    pale_green = "#E9F6D7"
    blue = "#1F6FEB"
    pale_blue = "#EAF2FF"
    grey_fill = "#F5F7FA"
    grey_edge = "#D7DCE2"
    amber = "#F06A00"
    pale_amber = "#FFF3E5"

    fig.text(0.055, 0.91, "C++ Demo 逻辑示意", ha="left", va="center", fontsize=25, fontweight="bold", color=dark)
    fig.text(
        0.055,
        0.85,
        "从网格连接关系和自由度编号出发，先确定矩阵位置，再并行填入单元贡献",
        ha="left",
        va="center",
        fontsize=16.5,
        color=mid,
    )

    # Main pseudocode panel.
    rounded_box(ax, (0.055, 0.18), (0.56, 0.60), "white", "#C9D1D9", lw=1.2)
    ax.text(0.083, 0.735, "伪代码", transform=ax.transAxes, fontsize=16.5, fontweight="bold", color=dark)
    ax.text(0.56, 0.735, "核心流程", transform=ax.transAxes, fontsize=11, color=axis, ha="right")

    code_lines = [
        ("输入", "DofCodingInfo, 单元刚度矩阵 Ke"),
        ("1", "symbolic(info)"),
        ("", "检查节点、自由度编号和输入合法性"),
        ("", "按单元收集整体矩阵会出现的位置"),
        ("", "只保留对称矩阵的上三角位置"),
        ("2", "生成 CSC3 和 scatter"),
        ("", "CSC3 = col_ptr / row_idx / values"),
        ("", "scatter: 单元局部项 -> values 下标"),
        ("3", "add_parallel(Ke, threads)"),
        ("", "并行遍历所有单元"),
        ("", "p = scatter[局部项]"),
        ("", "atomic  values[p] += Ke[i, j]"),
        ("输出", "整体刚度矩阵 K"),
    ]

    y = 0.682
    for tag, line in code_lines:
        if tag in {"输入", "输出"}:
            tag_color = amber if tag == "输入" else green
            tag_face = pale_amber if tag == "输入" else pale_green
            rounded_box(ax, (0.085, y - 0.020), (0.055, 0.034), tag_face, tag_color, lw=1.0, radius=0.008)
            ax.text(0.1125, y - 0.003, tag, transform=ax.transAxes, ha="center", va="center", fontsize=10.2, fontweight="bold", color=tag_color)
            ax.text(0.155, y - 0.003, line, transform=ax.transAxes, ha="left", va="center", fontsize=13.5, fontweight="bold", color=dark)
            y -= 0.048
        elif tag:
            rounded_box(ax, (0.085, y - 0.020), (0.035, 0.034), pale_blue, blue, lw=1.0, radius=0.008)
            ax.text(0.1025, y - 0.003, tag, transform=ax.transAxes, ha="center", va="center", fontsize=10.2, fontweight="bold", color=blue)
            ax.text(0.155, y - 0.003, line, transform=ax.transAxes, ha="left", va="center", fontsize=13.5, fontweight="bold", color=dark)
            y -= 0.044
        else:
            ax.text(0.168, y - 0.003, "• " + line, transform=ax.transAxes, ha="left", va="center", fontsize=12.2, color=mid)
            y -= 0.037

    # Right data-flow cards.
    cards = [
        ((0.665, 0.62), (0.27, 0.16), "输入信息", "单元连接关系\n节点自由度编号", pale_amber, amber),
        ((0.665, 0.39), (0.27, 0.17), "确定矩阵位置", "生成上三角 CSC3\n生成 scatter 写入地址", pale_blue, blue),
        ((0.665, 0.18), (0.27, 0.15), "并行填数值", "atomic 写入 values\n得到整体刚度矩阵 K", pale_green, green),
    ]
    for (xy, wh, title, body, face, edge) in cards:
        rounded_box(ax, xy, wh, face, edge, lw=1.5)
        ax.text(xy[0] + 0.020, xy[1] + wh[1] - 0.035, title, transform=ax.transAxes, ha="left", va="center", fontsize=14.2, fontweight="bold", color=edge)
        add_wrapped(ax, xy[0] + 0.020, xy[1] + wh[1] - 0.070, body, 16, size=11.8, color=dark, lineheight=0.030)
    arrow(ax, 0.80, 0.615, 0.80, 0.565, color=axis)
    arrow(ax, 0.80, 0.385, 0.80, 0.335, color=axis)

    # Matrix icon and CSC arrays.
    draw_matrix_icon(ax, 0.845, 0.535, 0.060)
    # Validation strip.
    rounded_box(ax, (0.055, 0.075), (0.88, 0.060), grey_fill, grey_edge, lw=1.0, radius=0.012)
    ax.text(0.077, 0.105, "验证闭环", transform=ax.transAxes, fontsize=12.5, fontweight="bold", color=dark, va="center")
    ax.text(
        0.165,
        0.105,
        "手算样例  ·  乱序自由度  ·  高冲突并行  ·  错误输入拦截",
        transform=ax.transAxes,
        fontsize=12.2,
        color=mid,
        va="center",
    )

    base = OUT_DIR / "csc3_demo_logic_cn"
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
    for path in draw():
        print(path)


if __name__ == "__main__":
    main()
