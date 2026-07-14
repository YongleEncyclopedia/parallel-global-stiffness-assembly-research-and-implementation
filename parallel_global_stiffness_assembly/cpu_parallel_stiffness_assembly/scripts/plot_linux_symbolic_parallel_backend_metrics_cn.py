#!/usr/bin/env python3
"""Draw the Chinese monthly-report figure from Linux isolated raw CSV data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "results"
    / "2026-07-08-linux-intel-symbolic-parallel-backends-raw"
    / "isolated_symbolic_memory"
    / "isolated_symbolic_memory_summary.csv"
)
DEFAULT_OUT_ROOT = (
    PROJECT_ROOT / "reports" / "2026-07-10-linux-symbolic-parallel-backend-metrics"
)

BACKENDS = (
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_lock_guard",
    "cpu_graph_coloring",
    "cpu_row_owner",
)
PLOT_ORDER = ("cpu_serial",) + BACKENDS

LABELS = {
    "cpu_serial": "串行基线",
    "cpu_atomic": "原子累加",
    "cpu_private_csr": "线程私有",
    "cpu_lock_guard": "互斥锁",
    "cpu_graph_coloring": "图着色",
    "cpu_row_owner": "按行分配",
}
XTICKS = {
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
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows to write: {path}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "":
        raise RuntimeError(f"missing field {key}")
    return float(value)


def clean_cpu_model(value: str) -> str:
    return value.replace("(R)", "").replace("(TM)", "").replace("  ", " ").strip()


def require_one(rows: list[dict[str, str]], label: str) -> dict[str, str]:
    if len(rows) != 1:
        raise RuntimeError(f"expected one row for {label}, got {len(rows)}")
    return rows[0]


def validate_raw_rows(rows: list[dict[str, str]], target_threads: int) -> list[dict[str, object]]:
    if not rows:
        raise RuntimeError("input CSV is empty")
    forbidden = [
        row
        for row in rows
        if "direct_no_symbolic" in row.get("mode", "")
        or row.get("numeric_backend") == "cpu_coo_sort_reduce"
    ]
    if forbidden:
        raise RuntimeError("input contains direct/no-symbolic or COO sort-reduce rows")

    coverage: list[dict[str, object]] = []
    baseline = [
        row
        for row in rows
        if row.get("mode") == "symbolic_reuse_serial"
        and row.get("numeric_backend") == "cpu_serial"
        and row.get("threads") == "1"
    ]
    coverage.append(
        {
            "算法": "串行基线",
            "原始后端": "cpu_serial",
            "期望": "symbolic_reuse_serial, 1线程, PASS",
            "记录数": len(baseline),
            "覆盖完整": "是" if len(baseline) == 1 else "否",
        }
    )
    if len(baseline) != 1:
        raise RuntimeError("missing serial baseline row")

    for backend in BACKENDS:
        backend_rows = [
            row
            for row in rows
            if row.get("mode") == "parallel_symbolic_reuse"
            and row.get("numeric_backend") == backend
        ]
        threads = sorted({int(row["threads"]) for row in backend_rows})
        complete = threads == list(range(1, 21))
        target_present = any(int(row["threads"]) == target_threads for row in backend_rows)
        coverage.append(
            {
                "算法": LABELS[backend],
                "原始后端": backend,
                "期望": f"parallel_symbolic_reuse, 1..20线程, PASS；绘图取{target_threads}线程",
                "记录数": len(backend_rows),
                "现有线程": ",".join(str(thread) for thread in threads),
                "覆盖完整": "是" if complete and target_present else "否",
            }
        )
        if not complete or not target_present:
            raise RuntimeError(f"incomplete coverage for {backend}")

    for row in rows:
        if row.get("run_status") != "PASS":
            raise RuntimeError(
                f"summary row is not PASS for {row.get('mode')} / "
                f"{row.get('numeric_backend')} / threads={row.get('threads')}"
            )
        if int(float(row.get("repeat_count", "0") or 0)) != 3:
            raise RuntimeError(
                f"expected three repeats for {row.get('numeric_backend')} "
                f"threads={row.get('threads')}"
            )
        if int(float(row.get("pass_count", "0") or 0)) != 3 or int(
            float(row.get("fail_count", "0") or 0)
        ) != 0:
            raise RuntimeError(
                f"repeat coverage is incomplete for {row.get('numeric_backend')} "
                f"threads={row.get('threads')}"
            )
        if row.get("matrix_correctness_status") != "PASS":
            raise RuntimeError(
                f"matrix correctness failed for {row.get('mode')} / "
                f"{row.get('numeric_backend')} / threads={row.get('threads')}"
            )
        rel_l2 = f(row, "rel_l2")
        if rel_l2 > 1e-10:
            raise RuntimeError(
                f"rel_l2 too large for {row.get('numeric_backend')} threads={row.get('threads')}: {rel_l2}"
            )
        total = f(row, "amortized_total_ms")
        numeric = f(row, "numeric_ms")
        expected_numeric = f(row, "backend_prepare_ms") + f(row, "assembly_numeric_ms")
        if abs(numeric - expected_numeric) > max(1e-6, 1e-9 * max(1.0, numeric)):
            raise RuntimeError(
                f"numeric_ms mismatch for {row.get('numeric_backend')} threads={row.get('threads')}"
            )
        expected_total = f(row, "symbolic_total_ms") + numeric
        if abs(total - expected_total) > max(1e-6, 1e-9 * max(1.0, total)):
            raise RuntimeError(
                f"amortized_total_ms mismatch for {row.get('numeric_backend')} threads={row.get('threads')}"
            )
        if f(row, "isolated_peak_rss_mb") <= 0:
            raise RuntimeError(
                f"isolated_peak_rss_mb must be positive for {row.get('numeric_backend')}"
            )
    return coverage


def select_rows(rows: list[dict[str, str]], target_threads: int) -> list[dict[str, object]]:
    baseline = require_one(
        [
            row
            for row in rows
            if row.get("mode") == "symbolic_reuse_serial"
            and row.get("numeric_backend") == "cpu_serial"
            and row.get("threads") == "1"
        ],
        "serial baseline",
    )
    baseline_total_ms = f(baseline, "amortized_total_ms")
    baseline_rss_gib = f(baseline, "isolated_peak_rss_mb") / 1024.0

    selected_raw: list[dict[str, str]] = [baseline]
    for backend in BACKENDS:
        selected_raw.append(
            require_one(
                [
                    row
                    for row in rows
                    if row.get("mode") == "parallel_symbolic_reuse"
                    and row.get("numeric_backend") == backend
                    and int(row["threads"]) == target_threads
                ],
                f"{backend} {target_threads} threads",
            )
        )

    selected: list[dict[str, object]] = []
    for row in selected_raw:
        backend = row["numeric_backend"]
        rss_gib = f(row, "isolated_peak_rss_mb") / 1024.0
        extra_gib = max(0.0, rss_gib - baseline_rss_gib)
        base_gib = rss_gib - extra_gib
        total_ms = f(row, "amortized_total_ms")
        selected.append(
            {
                "算法": LABELS[backend],
                "原始后端": backend,
                "模式": row["mode"],
                "线程数": int(row["threads"]),
                "峰值内存_GiB": rss_gib,
                "基础内存_GiB": base_gib,
                "额外内存_GiB": extra_gib,
                "符号组装_ms": f(row, "symbolic_total_ms"),
                "数值组装_ms": f(row, "numeric_ms"),
                "后端准备_ms": f(row, "backend_prepare_ms"),
                "实际累加_ms": f(row, "assembly_numeric_ms"),
                "总耗时_ms": total_ms,
                "整体加速比": baseline_total_ms / total_ms,
                "串行基线总耗时_ms": baseline_total_ms,
                "rel_L2": f(row, "rel_l2"),
                "isolated_peak_rss_mb": f(row, "isolated_peak_rss_mb"),
                "symbolic_csr_ms": f(row, "symbolic_csr_ms"),
                "symbolic_plan_ms": f(row, "symbolic_plan_ms"),
                "symbolic_temporary_GiB": f(row, "symbolic_temporary_bytes") / 1024**3,
                "numeric_backend_extra_bytes_GiB": f(row, "numeric_backend_extra_bytes")
                / 1024**3,
                "CPU型号": clean_cpu_model(row["cpu_model"]),
                "平台": row["platform"],
                "数据口径": row["time_scope"],
                "内存口径": row["isolated_memory_metric"],
                "内存测量来源": row["isolated_memory_measurement_source"],
                "重复次数": int(float(row["repeat_count"])),
                "成功次数": int(float(row["pass_count"])),
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
    ax.set_xticklabels(labels, fontsize=9.6, linespacing=1.08)
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
    xticks = [f"{XTICKS[algorithm]}\n{thread}线程" for algorithm, thread in zip(algorithms, threads)]
    peak_memory = [float(row["峰值内存_GiB"]) for row in rows]
    base_memory = [float(row["基础内存_GiB"]) for row in rows]
    extra_memory = [float(row["额外内存_GiB"]) for row in rows]
    symbolic = [float(row["符号组装_ms"]) for row in rows]
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
    ax_mem.bar(x, base_memory, width=0.60, color=base_grey, edgecolor="none", label="基础内存")
    extra_bars = ax_mem.bar(
        x,
        extra_memory,
        bottom=base_memory,
        width=0.60,
        color=green,
        edgecolor="none",
        label="额外内存",
    )
    ax_mem.set_ylim(0, max(peak_memory) * 1.22)
    format_axis(ax_mem, xticks, "吉字节")
    add_panel_title(ax_mem, "实测峰值内存", "越低越好")
    for idx, value in enumerate(peak_memory):
        ax_mem.text(
            idx,
            value + ax_mem.get_ylim()[1] * 0.025,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=10.8,
            color=dark_text,
        )
    for bar, value in zip(extra_bars, extra_memory):
        if value < 0.18:
            continue
        ax_mem.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_y() + bar.get_height() / 2,
            f"+{value:.2f}",
            ha="center",
            va="center",
            fontsize=8.8,
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
    ax_time.bar(x, numeric, width=0.60, color=green, edgecolor="none", label="数值组装")
    ax_time.bar(
        x,
        symbolic,
        bottom=numeric,
        width=0.60,
        color=pale_green,
        edgecolor="none",
        label="符号组装",
    )
    ax_time.set_ylim(0, max(total) * 1.20)
    format_axis(ax_time, xticks, "毫秒")
    add_panel_title(ax_time, "耗时", "越低越好")
    for idx, value in enumerate(total):
        ax_time.text(
            idx,
            value + ax_time.get_ylim()[1] * 0.025,
            f"{value:.0f}",
            ha="center",
            va="bottom",
            fontsize=10.8,
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
    ax_speed.bar(x, speedups, width=0.60, color=speed_colors, edgecolor="none")
    ax_speed.set_ylim(0, max(speedups) * 1.30)
    format_axis(ax_speed, xticks, "倍")
    add_panel_title(ax_speed, "整体加速比", "越高越好")
    for idx, value in enumerate(speedups):
        ax_speed.text(
            idx,
            value + ax_speed.get_ylim()[1] * 0.025,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=10.8,
            color=dark_text,
        )

    fig.text(
        0.055,
        0.115,
        (
            f"并行后端：{target_threads} 线程；基线：串行 1 线程；"
            "内存：隔离实测峰值，深色为相对串行基线新增峰值。"
        ),
        fontsize=12.7,
        color="#333333",
        ha="left",
    )
    fig.text(
        0.055,
        0.079,
        (
            "耗时：符号组装 + 数值组装（含后端准备）；"
            f"加速比：{baseline_ms:.0f} 毫秒 ÷ 当前耗时；"
            "数据为 3 次独立进程测试的中位数，不含网格读取。"
        ),
        fontsize=11.2,
        color="#737A80",
        ha="left",
    )

    base = asset_dir / f"linux_symbolic_parallel_backend_metrics_{target_threads}threads_cn"
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
    rows: list[dict[str, object]],
    coverage_rows: list[dict[str, object]],
    target_threads: int,
    source_csv: Path,
) -> Path:
    path = out_root / f"linux_symbolic_parallel_backend_metrics_{target_threads}threads_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    baseline_ms = float(rows[0]["串行基线总耗时_ms"])
    try:
        source_display = source_csv.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        source_display = source_csv.name
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Linux 隔离进程数值组装后端图件说明\n\n")
        handle.write("## 图表目标\n\n")
        handle.write(
            f"在同一 {target_threads} 线程条件下，用完整总耗时和隔离峰值内存公平比较五类数值组装后端。\n\n"
        )
        handle.write("## 数据物理含义\n\n")
        handle.write("- 本图只使用 Linux 端重新实跑后的三次重复中位数汇总 CSV，不重跑 benchmark。\n")
        handle.write("- 基线为 `symbolic_reuse_serial / cpu_serial / 1线程`，即串行符号组装 + 串行数值组装。\n")
        handle.write("- 并行行均为 `parallel_symbolic_reuse`，即并行符号组装 + 对应并行数值后端。\n")
        handle.write("- `numeric_ms = backend_prepare_ms + assembly_numeric_ms`；图中仍统一显示为“数值组装”。\n")
        handle.write("- `amortized_total_ms = symbolic_total_ms + numeric_ms`，图中总耗时只拆成“符号组装 + 数值组装”两部分。\n")
        handle.write("- `isolated_peak_rss_mb` 是每一行单独子进程运行时的峰值 RSS，反映实测进程峰值内存。\n")
        handle.write("- 图中“额外内存”定义为当前峰值 RSS 相对串行基线峰值 RSS 的新增部分；不是 `numeric_backend_extra_bytes` 理论字段。\n")
        handle.write(f"- 整体加速比以串行 1 线程总耗时 {baseline_ms:.3f} ms 为基线。\n")
        handle.write(f"- 绘图取并行后端 {target_threads} 线程；每个数据点来自 3 次独立进程测试的中位数。\n\n")

        handle.write("## 绘图行\n\n")
        handle.write(
            "| 算法 | 后端 | 线程 | 峰值内存(GiB) | 基础内存(GiB) | 额外内存(GiB) | "
            "符号组装(ms) | 数值组装(ms) | 后端准备(ms) | 实际累加(ms) | 总耗时(ms) | 加速比 | rel_L2 |\n"
        )
        handle.write("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in rows:
            handle.write(
                "| {算法} | {原始后端} | {线程数} | {峰值内存_GiB:.3f} | {基础内存_GiB:.3f} | "
                "{额外内存_GiB:.3f} | {符号组装_ms:.3f} | {数值组装_ms:.3f} | "
                "{后端准备_ms:.3f} | {实际累加_ms:.3f} | {总耗时_ms:.3f} | "
                "{整体加速比:.3f} | {rel_L2:.3e} |\n".format(**row)
            )

        handle.write("\n## 覆盖审计\n\n")
        handle.write("| 算法 | 记录数 | 覆盖完整 | 期望 |\n")
        handle.write("|---|---:|---|---|\n")
        for row in coverage_rows:
            handle.write(f"| {row['算法']} | {row['记录数']} | {row['覆盖完整']} | {row['期望']} |\n")
        handle.write(f"\nsource_csv: `{source_display}`\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--target-threads", type=int, default=16)
    args = parser.parse_args()

    if args.target_threads < 1 or args.target_threads > 20:
        raise ValueError("--target-threads must be in 1..20")

    rows = read_csv(args.input)
    coverage_rows = validate_raw_rows(rows, args.target_threads)
    selected_rows = select_rows(rows, args.target_threads)

    source_dir = args.out_root / "source_data"
    write_csv(source_dir / "linux_symbolic_parallel_backend_metrics_coverage.csv", coverage_rows)
    write_csv(
        source_dir / f"linux_symbolic_parallel_backend_metrics_{args.target_threads}threads_rows.csv",
        selected_rows,
    )
    outputs = draw(selected_rows, args.out_root, args.target_threads)
    summary = write_summary(args.out_root, selected_rows, coverage_rows, args.target_threads, args.input)

    print("Coverage rows:", source_dir / "linux_symbolic_parallel_backend_metrics_coverage.csv")
    print(
        "Source rows:",
        source_dir / f"linux_symbolic_parallel_backend_metrics_{args.target_threads}threads_rows.csv",
    )
    print("Summary:", summary)
    for output in outputs:
        print("Figure:", output)


if __name__ == "__main__":
    main()
