#!/usr/bin/env python3
"""Draw Chinese metric panels from the isolated Intel backend sweep."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "results" / "2026-06-26-intel-backend-thread-sweep-isolated-raw"
DEFAULT_SUMMARY = DEFAULT_DATA_ROOT / "windhub_backend_thread_sweep_intel_isolated_summary.csv"
DEFAULT_REPEATS = DEFAULT_DATA_ROOT / "windhub_backend_thread_sweep_intel_isolated_repeats.csv"
DEFAULT_OUT_ROOT = PROJECT_ROOT / "reports" / "2026-06-26-intel-isolated-backend-metrics"

TARGET_ALGORITHMS = (
    "cpu_serial",
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_lock_guard",
    "cpu_graph_coloring",
    "cpu_row_owner",
)
PLOT_ORDER = TARGET_ALGORITHMS
THREAD_RANGE = range(1, 21)

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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"No rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def require_single(rows: list[dict[str, str]], description: str) -> dict[str, str]:
    if len(rows) != 1:
        raise RuntimeError(f"Expected one row for {description}, got {len(rows)}")
    return rows[0]


def clean_cpu_model(value: str) -> str:
    return value.replace("(R)", "").replace("(TM)", "").replace("  ", " ").strip()


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def audit_coverage(summary_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    algorithms = sorted({row["algorithm"] for row in summary_rows})
    unexpected = [algorithm for algorithm in algorithms if algorithm not in TARGET_ALGORITHMS]
    if unexpected:
        raise RuntimeError(f"Unexpected algorithms in source CSV: {unexpected}")

    audit_rows: list[dict[str, object]] = []
    for algorithm in TARGET_ALGORITHMS:
        rows = [row for row in summary_rows if row["algorithm"] == algorithm]
        present_threads = sorted({int(row["threads"]) for row in rows})
        pass_threads = sorted({int(row["threads"]) for row in rows if row["status"] == "PASS"})
        skip_threads = sorted({int(row["threads"]) for row in rows if row["status"] == "SKIP"})
        missing_threads = [thread for thread in THREAD_RANGE if thread not in present_threads]
        if algorithm == "cpu_serial":
            expected = "1线程PASS，2-20线程SKIP审计行"
            complete = (
                not missing_threads
                and pass_threads == [1]
                and skip_threads == list(range(2, 21))
            )
        else:
            expected = "1-20线程全部PASS"
            complete = not missing_threads and pass_threads == list(THREAD_RANGE)

        audit_rows.append(
            {
                "算法": LABELS[algorithm],
                "原始后端": algorithm,
                "期望覆盖": expected,
                "记录行数": len(rows),
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


def repeat_means(
    repeat_rows: list[dict[str, str]], algorithm: str, threads: int
) -> dict[str, float]:
    rows = [
        row
        for row in repeat_rows
        if row["algorithm"] == algorithm
        and int(row["threads"]) == threads
        and row["status"] == "PASS"
    ]
    if not rows:
        raise RuntimeError(f"Missing repeat rows for {algorithm} thread {threads}")

    def m(field: str) -> float:
        values = [float(row[field]) for row in rows if row.get(field, "") != ""]
        return mean(values)

    return {
        "extra_memory_gib": m("extra_memory_bytes") / 1024**3,
        "symbolic_csr_ms": m("symbolic_csr_ms"),
        "symbolic_plan_ms": m("symbolic_plan_ms"),
        "backend_prepare_ms": m("backend_prepare_ms"),
        "mesh_load_ms": m("mesh_load_ms"),
        "prepare_allocate_ms": m("prepare_allocate_ms"),
        "prepare_coloring_ms": m("prepare_coloring_ms"),
        "prepare_owner_partition_ms": m("prepare_owner_partition_ms"),
        "assembly_zero_ms": m("assembly_zero_ms"),
        "assembly_numeric_ms": m("assembly_numeric_ms"),
        "isolated_peak_rss_mb_repeat_mean": m("isolated_peak_rss_mb"),
    }


def select_plot_rows(
    summary_rows: list[dict[str, str]],
    repeat_rows: list[dict[str, str]],
    target_threads: int,
    summary_path: Path,
    repeats_path: Path,
) -> list[dict[str, object]]:
    baseline = require_single(
        [
            row
            for row in summary_rows
            if row["algorithm"] == "cpu_serial"
            and int(row["threads"]) == 1
            and row["status"] == "PASS"
        ],
        "cpu_serial 1-thread baseline",
    )
    baseline_total_ms = float(baseline["symbolic_numeric_total_ms_mean"])

    selected: list[dict[str, object]] = []
    for algorithm in PLOT_ORDER:
        threads = 1 if algorithm == "cpu_serial" else target_threads
        row = require_single(
            [
                candidate
                for candidate in summary_rows
                if candidate["algorithm"] == algorithm
                and int(candidate["threads"]) == threads
                and candidate["status"] == "PASS"
            ],
            f"{algorithm} thread {threads}",
        )
        details = repeat_means(repeat_rows, algorithm, threads)
        peak_memory_gib = float(row["isolated_peak_rss_mb_mean"]) / 1024
        extra_memory_gib = details["extra_memory_gib"]
        base_memory_gib = max(0.0, peak_memory_gib - extra_memory_gib)
        symbolic_ms = float(row["symbolic_ms_mean"])
        numeric_ms = float(row["numeric_ms_mean"])
        total_ms = float(row["symbolic_numeric_total_ms_mean"])
        speedup = baseline_total_ms / total_ms

        selected.append(
            {
                "算法": LABELS[algorithm],
                "原始后端": algorithm,
                "线程数": threads,
                "状态": row["status"],
                "峰值内存_GiB": peak_memory_gib,
                "基础内存_GiB": base_memory_gib,
                "额外内存_GiB": extra_memory_gib,
                "符号预处理_ms": symbolic_ms,
                "数值组装_ms": numeric_ms,
                "总耗时_ms": total_ms,
                "整体加速比": speedup,
                "串行基线总耗时_ms": baseline_total_ms,
                "symbolic_csr_ms": details["symbolic_csr_ms"],
                "symbolic_plan_ms": details["symbolic_plan_ms"],
                "backend_prepare_ms": details["backend_prepare_ms"],
                "mesh_load_ms_未计入": details["mesh_load_ms"],
                "prepare_allocate_ms": details["prepare_allocate_ms"],
                "prepare_coloring_ms": details["prepare_coloring_ms"],
                "prepare_owner_partition_ms": details["prepare_owner_partition_ms"],
                "assembly_zero_ms": details["assembly_zero_ms"],
                "assembly_numeric_ms": details["assembly_numeric_ms"],
                "isolated_peak_rss_mb_mean": float(row["isolated_peak_rss_mb_mean"]),
                "isolated_peak_rss_mb_repeat_mean": details["isolated_peak_rss_mb_repeat_mean"],
                "rel_L2": float(row["rel_l2"] or 0.0),
                "max_abs": float(row["max_abs"] or 0.0),
                "重复次数": int(row["repeat_count"]),
                "measurement_mode": row["measurement_mode"],
                "CPU型号": row["algorithm"] and clean_cpu_model(
                    next(
                        repeat["cpu_model"]
                        for repeat in repeat_rows
                        if repeat["algorithm"] == algorithm
                        and int(repeat["threads"]) == threads
                        and repeat["status"] == "PASS"
                    )
                ),
                "平台": next(
                    repeat["platform"]
                    for repeat in repeat_rows
                    if repeat["algorithm"] == algorithm
                    and int(repeat["threads"]) == threads
                    and repeat["status"] == "PASS"
                ),
                "summary_source": str(summary_path),
                "repeats_source": str(repeats_path),
            }
        )
    return selected


def add_panel_title(ax: plt.Axes, title: str, hint: str) -> None:
    ax.text(
        0.0,
        1.095,
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
        1.095,
        hint,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=11.5,
        color="#667078",
    )


def format_axis(ax: plt.Axes, labels: list[str], ylabel: str) -> None:
    ax.set_ylabel(ylabel, fontsize=13, labelpad=8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=10.0, linespacing=1.12)
    ax.tick_params(axis="y", labelsize=10.5, colors="#667078")
    ax.tick_params(axis="x", length=0, pad=9)
    ax.grid(axis="y", color="#DFDFDF", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["left"].set_linewidth(1.05)
    ax.spines["bottom"].set_linewidth(1.05)


def draw(rows: list[dict[str, object]], out_root: Path, target_threads: int) -> list[Path]:
    configure_style()
    asset_dir = out_root / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    x = list(range(len(rows)))
    algorithms = [str(row["原始后端"]) for row in rows]
    threads = [int(row["线程数"]) for row in rows]
    xticks = [f"{XTICK_LABELS[algorithm]}\n{thread}线程" for algorithm, thread in zip(algorithms, threads)]
    peak_memory = [float(row["峰值内存_GiB"]) for row in rows]
    base_memory = [float(row["基础内存_GiB"]) for row in rows]
    extra_memory = [float(row["额外内存_GiB"]) for row in rows]
    symbolic = [float(row["符号预处理_ms"]) for row in rows]
    numeric = [float(row["数值组装_ms"]) for row in rows]
    total = [float(row["总耗时_ms"]) for row in rows]
    speedups = [float(row["整体加速比"]) for row in rows]
    baseline_ms = float(rows[0]["串行基线总耗时_ms"])
    cpu_model = str(rows[0]["CPU型号"])

    green = "#76B900"
    pale_green = "#C8E88B"
    base_grey = "#D9DEE3"
    baseline_grey = "#AEB5BA"
    dark_text = "#202020"
    speed_colors = [baseline_grey] + [green] * (len(rows) - 1)

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
    ax_mem.bar(x, base_memory, width=0.62, color=base_grey, edgecolor="none", label="基础内存")
    extra_bars = ax_mem.bar(
        x, extra_memory, bottom=base_memory, width=0.62, color=green, edgecolor="none", label="额外内存"
    )
    ax_mem.set_ylim(0, max(peak_memory) * 1.25)
    format_axis(ax_mem, xticks, "吉字节")
    add_panel_title(ax_mem, "实测峰值内存", "越低越好")
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
    ax_time.bar(x, numeric, width=0.62, color=green, edgecolor="none", label="组装")
    ax_time.bar(
        x,
        symbolic,
        bottom=numeric,
        width=0.62,
        color=pale_green,
        edgecolor="none",
        label="符号预处理",
    )
    ax_time.set_ylim(0, max(total) * 1.22)
    format_axis(ax_time, xticks, "毫秒")
    add_panel_title(ax_time, "耗时", "越低越好")
    for idx, value in enumerate(total):
        ax_time.text(
            idx,
            value + ax_time.get_ylim()[1] * 0.025,
            f"{value:.0f}",
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
    ax_speed.bar(x, speedups, width=0.62, color=speed_colors, edgecolor="none")
    ax_speed.set_ylim(0, max(speedups) * 1.32)
    format_axis(ax_speed, xticks, "倍")
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
            "内存：隔离实测峰值，深色为额外内存；"
            "耗时：符号预处理 + 组装；"
            f"加速比：{baseline_ms:.0f} 毫秒 ÷ 当前耗时。"
        ),
        fontsize=13.1,
        color="#333333",
        ha="left",
    )
    fig.text(
        0.055,
        0.079,
        "说明：本轮符号预处理包含稀疏结构、写入位置表和后端准备；不包含网格读取。",
        fontsize=10.8,
        color="#737A80",
        ha="left",
    )

    base = asset_dir / f"intel_isolated_backend_metrics_{target_threads}threads_cn"
    outputs = [
        base.with_suffix(".svg"),
        base.with_suffix(".pdf"),
        base.with_suffix(".png"),
        base.with_suffix(".tiff"),
    ]
    for output in outputs:
        kwargs = {"facecolor": "white"}
        if output.suffix == ".png":
            kwargs["dpi"] = 240
        elif output.suffix == ".tiff":
            kwargs["dpi"] = 600
        fig.savefig(output, **kwargs)
    plt.close(fig)
    return outputs


def write_summary(
    out_root: Path,
    selected_rows: list[dict[str, object]],
    coverage_rows: list[dict[str, object]],
    target_threads: int,
) -> Path:
    path = out_root / f"intel_isolated_backend_metrics_{target_threads}threads_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    baseline_ms = float(selected_rows[0]["串行基线总耗时_ms"])
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Intel 隔离进程数值组装后端图件说明\n\n")
        handle.write("## 数据物理含义\n\n")
        handle.write("- 本轮每个算法、线程数、重复次数都在独立子进程中测量。\n")
        handle.write("- `isolated_peak_rss_mb` 是该子进程的峰值 RSS，可用于算法间内存对比。\n")
        handle.write("- `符号预处理_ms = symbolic_ms_mean`，包含稀疏结构、写入位置表和后端准备。\n")
        handle.write("- `数值组装_ms = numeric_ms_mean`，表示真正向全局矩阵 values 写入数值的耗时。\n")
        handle.write("- `总耗时_ms = symbolic_numeric_total_ms_mean = 符号预处理 + 数值组装`。\n")
        handle.write(f"- 整体加速比以串行 1 线程总耗时 {baseline_ms:.3f} ms 为基线。\n\n")

        handle.write("## 覆盖性检查\n\n")
        handle.write("- 串行基线为 1 线程 PASS，2-20 线程为 SKIP 审计行。\n")
        handle.write("- 其余后端均覆盖 1-20 线程 PASS 记录。\n")
        handle.write("- 输入不含 direct assembly，也不含 `cpu_coo_sort_reduce`。\n\n")

        handle.write("## 20 线程绘图行\n\n")
        handle.write("| 算法 | 线程 | 峰值内存(GiB) | 基础内存(GiB) | 额外内存(GiB) | 符号预处理(ms) | 组装(ms) | 总耗时(ms) | 加速比 | rel_L2 |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in selected_rows:
            handle.write(
                "| {算法} | {线程数} | {峰值内存_GiB:.3f} | {基础内存_GiB:.3f} | {额外内存_GiB:.3f} | "
                "{符号预处理_ms:.3f} | {数值组装_ms:.3f} | {总耗时_ms:.3f} | {整体加速比:.3f} | {rel_L2:.3e} |\n".format(**row)
            )

        handle.write("\n## 覆盖审计\n\n")
        handle.write("| 算法 | 记录行数 | 覆盖完整 | 期望覆盖 |\n")
        handle.write("|---|---:|---|---|\n")
        for row in coverage_rows:
            handle.write(f"| {row['算法']} | {row['记录行数']} | {row['覆盖完整']} | {row['期望覆盖']} |\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--repeats", type=Path, default=DEFAULT_REPEATS)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--target-threads", type=int, default=20)
    args = parser.parse_args()

    if args.target_threads not in THREAD_RANGE:
        raise ValueError("--target-threads must be in 1..20")

    summary_rows = read_csv(args.summary)
    repeat_rows = read_csv(args.repeats)
    coverage_rows = audit_coverage(summary_rows)
    selected_rows = select_plot_rows(
        summary_rows,
        repeat_rows,
        args.target_threads,
        args.summary,
        args.repeats,
    )

    source_dir = args.out_root / "source_data"
    write_csv(source_dir / "intel_isolated_backend_metrics_coverage.csv", coverage_rows)
    write_csv(
        source_dir / f"intel_isolated_backend_metrics_{args.target_threads}threads_rows.csv",
        selected_rows,
    )
    outputs = draw(selected_rows, args.out_root, args.target_threads)
    summary = write_summary(args.out_root, selected_rows, coverage_rows, args.target_threads)

    print("Coverage rows:", source_dir / "intel_isolated_backend_metrics_coverage.csv")
    print(
        "Source rows:",
        source_dir / f"intel_isolated_backend_metrics_{args.target_threads}threads_rows.csv",
    )
    print("Summary:", summary)
    for output in outputs:
        print("Figure:", output)


if __name__ == "__main__":
    main()
