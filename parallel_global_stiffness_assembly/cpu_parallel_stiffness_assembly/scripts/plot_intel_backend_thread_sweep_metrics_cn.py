#!/usr/bin/env python3
"""Draw Chinese metric panels from the Intel backend thread-sweep CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "results"
    / "2026-06-26-intel-backend-thread-sweep-raw"
    / "windhub_backend_thread_sweep_intel.csv"
)
DEFAULT_OUT_ROOT = PROJECT_ROOT / "reports" / "2026-06-26-intel-backend-thread-sweep-metrics"

TARGET_ALGORITHMS = (
    "cpu_serial",
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_lock_guard",
    "cpu_graph_coloring",
    "cpu_row_owner",
)
PLOT_ORDER = (
    "cpu_serial",
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_lock_guard",
    "cpu_graph_coloring",
    "cpu_row_owner",
)
LABELS = {
    "cpu_serial": "串行基线",
    "cpu_atomic": "原子累加",
    "cpu_private_csr": "线程私有",
    "cpu_lock_guard": "互斥锁",
    "cpu_graph_coloring": "图着色",
    "cpu_row_owner": "按行分配",
}
XTICK_LABELS = {
    "cpu_serial": "串行\n基线",
    "cpu_atomic": "原子\n累加",
    "cpu_private_csr": "线程\n私有",
    "cpu_lock_guard": "互斥\n锁",
    "cpu_graph_coloring": "图\n着色",
    "cpu_row_owner": "按行\n分配",
}
THREAD_RANGE = range(1, 21)

# Temporary memory estimates until the Intel sweep is rerun with per-backend
# isolated-process memory measurement. The base values come from the earlier
# Intel isolated-memory run on the same WindHub Tet4 case.
SERIAL_BASE_MEMORY_GIB = 2783.062500 / 1024.0
PARALLEL_BASE_MEMORY_GIB = 3356.347656 / 1024.0


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


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require_single(rows: Iterable[dict[str, str]], description: str) -> dict[str, str]:
    matches = list(rows)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one row for {description}, got {len(matches)}")
    return matches[0]


def clean_cpu_model(value: str) -> str:
    return value.replace("(R)", "").replace("(TM)", "").replace("  ", " ").strip()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"No rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def audit_coverage(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    algorithms = sorted({row["algorithm"] for row in rows})
    unexpected = [alg for alg in algorithms if alg not in TARGET_ALGORITHMS]
    if unexpected:
        raise RuntimeError(f"Unexpected algorithms in source CSV: {unexpected}")

    audit_rows: list[dict[str, object]] = []
    for algorithm in TARGET_ALGORITHMS:
        alg_rows = [row for row in rows if row["algorithm"] == algorithm]
        present_threads = sorted({int(row["threads"]) for row in alg_rows})
        missing_threads = [thread for thread in THREAD_RANGE if thread not in present_threads]
        pass_threads = sorted({int(row["threads"]) for row in alg_rows if row["status"] == "PASS"})
        skip_threads = sorted({int(row["threads"]) for row in alg_rows if row["status"] == "SKIP"})
        if algorithm == "cpu_serial":
            complete = not missing_threads and pass_threads == [1] and skip_threads == list(range(2, 21))
            expected = "1线程PASS，2-20线程SKIP审计行"
        else:
            complete = not missing_threads and pass_threads == list(THREAD_RANGE)
            expected = "1-20线程全部PASS"
        audit_rows.append(
            {
                "算法": LABELS[algorithm],
                "原始后端": algorithm,
                "期望覆盖": expected,
                "记录行数": len(alg_rows),
                "现有线程": ",".join(str(thread) for thread in present_threads),
                "PASS线程": ",".join(str(thread) for thread in pass_threads),
                "SKIP线程": ",".join(str(thread) for thread in skip_threads),
                "缺失线程": ",".join(str(thread) for thread in missing_threads),
                "覆盖完整": "是" if complete else "否",
            }
        )
        if not complete:
            raise RuntimeError(f"Incomplete 1-20 coverage for {algorithm}")
    return audit_rows


def select_plot_rows(
    rows: list[dict[str, str]], source_path: Path, target_threads: int
) -> list[dict[str, object]]:
    if target_threads not in THREAD_RANGE:
        raise ValueError("target_threads must be in 1..20")

    baseline_row = require_single(
        (
            row
            for row in rows
            if row["algorithm"] == "cpu_serial"
            and int(row["threads"]) == 1
            and row["status"] == "PASS"
        ),
        "cpu_serial 1-thread baseline",
    )
    baseline_total_ms = float(baseline_row["total_mean_ms"])

    selected: list[dict[str, object]] = []
    for algorithm in PLOT_ORDER:
        thread = 1 if algorithm == "cpu_serial" else target_threads
        row = require_single(
            (
                candidate
                for candidate in rows
                if candidate["algorithm"] == algorithm
                and int(candidate["threads"]) == thread
                and candidate["status"] == "PASS"
            ),
            f"{algorithm} thread {thread}",
        )

        preprocess_ms = float(row["preprocess_ms"])
        assembly_ms = float(row["assembly_mean_ms"])
        total_ms = float(row["total_mean_ms"])
        extra_memory_gib = float(row["extra_memory_bytes"]) / 1024**3
        peak_rss_gib = float(row["peak_rss_mb"]) / 1024
        base_memory_gib = SERIAL_BASE_MEMORY_GIB if algorithm == "cpu_serial" else PARALLEL_BASE_MEMORY_GIB
        peak_memory_gib = base_memory_gib + extra_memory_gib
        estimate_note = (
            "串行基础内存参考既有Intel隔离进程测量"
            if algorithm == "cpu_serial"
            else "并行基础内存参考cpu_atomic 20线程隔离进程测量，叠加当前后端额外内存"
        )
        selected.append(
            {
                "算法": LABELS[algorithm],
                "原始后端": algorithm,
                "线程数": thread,
                "状态": row["status"],
                "准备耗时_ms": preprocess_ms,
                "组装耗时_ms": assembly_ms,
                "总耗时_ms": total_ms,
                "预估峰值内存_GiB": peak_memory_gib,
                "预估基础内存_GiB": base_memory_gib,
                "额外内存_GiB": extra_memory_gib,
                "线程扫描进程峰值RSS_GiB_不用于绘图": peak_rss_gib,
                "内存估算说明": estimate_note,
                "峰值内存_GiB": peak_memory_gib,
                "基础内存_GiB": base_memory_gib,
                "整体加速比_按总耗时": baseline_total_ms / total_ms,
                "CSV原始加速比_按组装耗时": float(row["speedup"]),
                "串行基线总耗时_ms": baseline_total_ms,
                "rel_L2": float(row["rel_l2"]),
                "max_abs": float(row["max_abs"]),
                "重复次数": int(row["run_count"]),
                "CPU型号": row["cpu_model"],
                "平台": row["platform"],
                "源文件": str(source_path),
            }
        )
    return selected


def add_panel_title(ax: plt.Axes, title: str, hint: str) -> None:
    ax.text(
        0.0,
        1.09,
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
        1.09,
        hint,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=11.5,
        color="#667078",
    )


def format_bar_axis(ax: plt.Axes, labels: list[str], ylabel: str) -> None:
    ax.set_ylabel(ylabel, fontsize=13, labelpad=8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=10.4, linespacing=1.15)
    ax.tick_params(axis="y", labelsize=10.5, colors="#667078")
    ax.tick_params(axis="x", length=0, pad=9)
    ax.grid(axis="y", color="#DFDFDF", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["left"].set_linewidth(1.05)
    ax.spines["bottom"].set_linewidth(1.05)


def label_memory(value: float) -> str:
    if value == 0:
        return "0"
    if value < 0.01:
        return "<0.01"
    return f"{value:.2f}"


def draw(rows: list[dict[str, object]], out_root: Path, target_threads: int) -> list[Path]:
    configure_style()
    asset_dir = out_root / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    labels = [str(row["算法"]) for row in rows]
    algorithm_ids = [str(row["原始后端"]) for row in rows]
    threads = [int(row["线程数"]) for row in rows]
    xticks = [f"{XTICK_LABELS[algorithm]}\n{thread}线程" for algorithm, thread in zip(algorithm_ids, threads)]
    x = list(range(len(rows)))

    peak_memory = [float(row["峰值内存_GiB"]) for row in rows]
    base_memory = [float(row["基础内存_GiB"]) for row in rows]
    extra_memory = [float(row["额外内存_GiB"]) for row in rows]
    preprocess = [float(row["准备耗时_ms"]) for row in rows]
    assembly = [float(row["组装耗时_ms"]) for row in rows]
    total = [float(row["总耗时_ms"]) for row in rows]
    speedups = [float(row["整体加速比_按总耗时"]) for row in rows]
    baseline_ms = float(rows[0]["串行基线总耗时_ms"])
    cpu_model = clean_cpu_model(str(rows[0]["CPU型号"]))

    green = "#76B900"
    pale_green = "#C8E88B"
    grey = "#AEB5BA"
    dark_text = "#202020"
    bar_colors = [grey] + [green] * (len(rows) - 1)

    fig = plt.figure(figsize=(12.8, 7.2), dpi=240)
    fig.text(0.055, 0.905, "数值组装算法性能对比", fontsize=24, color=dark_text, ha="left")
    fig.text(
        0.055,
        0.855,
        f"风机轮毂工程网格 · 四面体单元 · {cpu_model}",
        fontsize=16,
        color="#60686F",
        ha="left",
    )

    ax_mem = fig.add_axes((0.07, 0.33, 0.27, 0.43))
    ax_mem.bar(x, base_memory, width=0.62, color="#D9DEE3", edgecolor="none", label="基础内存")
    extra_bars = ax_mem.bar(
        x,
        extra_memory,
        bottom=base_memory,
        width=0.62,
        color=green,
        edgecolor="none",
        label="额外内存",
    )
    ax_mem.set_ylim(0, max(peak_memory) * 1.25 if max(peak_memory) > 0 else 1)
    format_bar_axis(ax_mem, xticks, "吉字节")
    add_panel_title(ax_mem, "预估峰值内存", "越低越好")
    for idx, value in enumerate(peak_memory):
        ax_mem.text(
            idx,
            value + ax_mem.get_ylim()[1] * 0.025,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=11,
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
            fontsize=9.2,
            color="white",
            fontweight="bold",
        )
    ax_mem.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.02),
        frameon=False,
        fontsize=10.5,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )

    ax_time = fig.add_axes((0.385, 0.33, 0.27, 0.43))
    ax_time.bar(x, assembly, width=0.62, color=green, edgecolor="none", label="组装")
    ax_time.bar(x, preprocess, bottom=assembly, width=0.62, color=pale_green, edgecolor="none", label="准备")
    ax_time.set_ylim(0, max(total) * 1.22)
    format_bar_axis(ax_time, xticks, "毫秒")
    add_panel_title(ax_time, "耗时", "越低越好")
    for idx, value in enumerate(total):
        label = f"{value:.0f}" if value < 1000 else f"{value / 1000:.2f}秒"
        ax_time.text(
            idx,
            value + ax_time.get_ylim()[1] * 0.025,
            label,
            ha="center",
            va="bottom",
            fontsize=11,
            color=dark_text,
        )
    ax_time.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.02),
        frameon=False,
        fontsize=10.5,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )

    ax_speed = fig.add_axes((0.70, 0.33, 0.27, 0.43))
    ax_speed.bar(x, speedups, width=0.62, color=bar_colors, edgecolor="none")
    ax_speed.set_ylim(0, max(speedups) * 1.26)
    format_bar_axis(ax_speed, xticks, "倍")
    add_panel_title(ax_speed, "整体加速比", "越高越好")
    for idx, value in enumerate(speedups):
        ax_speed.text(
            idx,
            value + ax_speed.get_ylim()[1] * 0.025,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=11,
            color=dark_text,
        )

    fig.text(
        0.055,
        0.115,
        (
            f"并行后端：{target_threads} 线程；基线：串行 1 线程；"
            "内存：预估基础内存 + 额外内存；耗时：准备 + 组装；"
            f"加速比：{baseline_ms:.0f} 毫秒 ÷ 当前耗时。"
        ),
        fontsize=13.3,
        color="#333333",
        ha="left",
    )
    fig.text(
        0.055,
        0.08,
        "说明：内存为预估值；后续需用各算法单独进程实测替换。",
        fontsize=10.6,
        color="#737A80",
        ha="left",
    )

    base = asset_dir / f"intel_backend_thread_sweep_{target_threads}threads_estimated_memory_cn"
    outputs = [
        base.with_suffix(".svg"),
        base.with_suffix(".pdf"),
        base.with_suffix(".png"),
        base.with_suffix(".tiff"),
    ]
    for output in outputs:
        kwargs = {"facecolor": "white"}
        if output.suffix in {".png", ".tiff"}:
            kwargs["dpi"] = 240 if output.suffix == ".png" else 600
        fig.savefig(output, **kwargs)
    plt.close(fig)
    return outputs


def write_summary(
    out_root: Path,
    selected_rows: list[dict[str, object]],
    coverage_rows: list[dict[str, object]],
    target_threads: int,
) -> Path:
    path = out_root / f"intel_backend_thread_sweep_{target_threads}threads_summary.md"
    out_root.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Intel 数值组装后端线程扫描图件说明\n\n")
        handle.write("## 覆盖性检查\n\n")
        handle.write("- 源 CSV 覆盖目标后端的 1-20 线程记录。\n")
        handle.write("- 串行基线仅 1 线程 PASS，2-20 线程为 SKIP 审计行。\n")
        handle.write("- 并行后端 1-20 线程均为 PASS。\n\n")
        handle.write("## 20 线程图件口径\n\n")
        handle.write(f"- 并行后端筛选 {target_threads} 线程；串行基线筛选 1 线程。\n")
        handle.write("- 内存栏为预估值，不使用本轮线程扫描中的同进程历史峰值 RSS。\n")
        handle.write(f"- 串行基础内存预估为 {SERIAL_BASE_MEMORY_GIB:.3f} GiB；并行基础内存预估为 {PARALLEL_BASE_MEMORY_GIB:.3f} GiB。\n")
        handle.write("- 额外内存来自本轮 CSV 的 `extra_memory_bytes`。\n")
        handle.write("- 耗时栏绘制 `preprocess_ms + assembly_mean_ms`。\n")
        handle.write("- 整体加速比重新计算为 `串行基线总耗时 / 当前总耗时`。\n\n")
        handle.write("## 绘图行\n\n")
        handle.write("| 算法 | 线程 | 预估峰值内存(GiB) | 预估基础内存(GiB) | 额外内存(GiB) | 准备(ms) | 组装(ms) | 总耗时(ms) | 整体加速比 |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in selected_rows:
            handle.write(
                "| {算法} | {线程数} | {预估峰值内存_GiB:.3f} | {预估基础内存_GiB:.3f} | {额外内存_GiB:.3f} | {准备耗时_ms:.3f} | "
                "{组装耗时_ms:.3f} | {总耗时_ms:.3f} | {整体加速比_按总耗时:.3f} |\n".format(**row)
            )
        handle.write("\n## 覆盖审计\n\n")
        handle.write("| 算法 | 记录行数 | 覆盖完整 | 期望覆盖 |\n")
        handle.write("|---|---:|---|---|\n")
        for row in coverage_rows:
            handle.write(
                f"| {row['算法']} | {row['记录行数']} | {row['覆盖完整']} | {row['期望覆盖']} |\n"
            )
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--target-threads", type=int, default=20)
    args = parser.parse_args()

    rows = read_rows(args.input)
    coverage_rows = audit_coverage(rows)
    selected = select_plot_rows(rows, args.input, args.target_threads)

    source_dir = args.out_root / "source_data"
    write_csv(source_dir / "intel_backend_thread_sweep_coverage.csv", coverage_rows)
    write_csv(
        source_dir / f"intel_backend_thread_sweep_{args.target_threads}threads_estimated_memory_rows.csv",
        selected,
    )
    outputs = draw(selected, args.out_root, args.target_threads)
    summary_path = write_summary(args.out_root, selected, coverage_rows, args.target_threads)

    print("Coverage rows:", source_dir / "intel_backend_thread_sweep_coverage.csv")
    print(
        "Source rows:",
        source_dir / f"intel_backend_thread_sweep_{args.target_threads}threads_estimated_memory_rows.csv",
    )
    print("Summary:", summary_path)
    for output in outputs:
        print("Figure:", output)


if __name__ == "__main__":
    main()
