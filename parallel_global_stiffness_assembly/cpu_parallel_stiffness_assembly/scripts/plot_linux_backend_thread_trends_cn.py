#!/usr/bin/env python3
"""Draw per-backend Chinese thread-scaling figures from Linux isolated raw CSV."""

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
    / "2026-06-26-linux-intel-symbolic-parallel-backends-raw"
    / "isolated_symbolic_memory"
    / "isolated_symbolic_memory.csv"
)
DEFAULT_OUT_ROOT = (
    PROJECT_ROOT / "reports" / "2026-06-26-linux-symbolic-parallel-backend-metrics"
)

BACKENDS = (
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_lock_guard",
    "cpu_graph_coloring",
    "cpu_row_owner",
)
LABELS = {
    "cpu_atomic": "原子累加",
    "cpu_private_csr": "线程私有",
    "cpu_lock_guard": "互斥锁",
    "cpu_graph_coloring": "图着色",
    "cpu_row_owner": "按行分配",
}
FILE_LABELS = {
    "cpu_atomic": "cpu_atomic",
    "cpu_private_csr": "cpu_private_csr",
    "cpu_lock_guard": "cpu_lock_guard",
    "cpu_graph_coloring": "cpu_graph_coloring",
    "cpu_row_owner": "cpu_row_owner",
}
THREADS = tuple(range(1, 21))


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


def validate_raw_rows(rows: list[dict[str, str]]) -> dict[str, object]:
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

    baseline = [
        row
        for row in rows
        if row.get("mode") == "symbolic_reuse_serial"
        and row.get("numeric_backend") == "cpu_serial"
        and row.get("threads") == "1"
    ]
    if len(baseline) != 1:
        raise RuntimeError(f"expected one serial baseline row, got {len(baseline)}")

    for row in rows:
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
        expected_total = f(row, "symbolic_total_ms") + f(row, "numeric_ms")
        if abs(total - expected_total) > max(1e-6, 1e-9 * max(1.0, total)):
            raise RuntimeError(
                f"amortized_total_ms mismatch for {row.get('numeric_backend')} threads={row.get('threads')}"
            )
        if f(row, "isolated_peak_rss_mb") <= 0:
            raise RuntimeError(
                f"isolated_peak_rss_mb must be positive for {row.get('numeric_backend')}"
            )

    coverage_rows = []
    for backend in BACKENDS:
        backend_rows = [
            row
            for row in rows
            if row.get("mode") == "parallel_symbolic_reuse"
            and row.get("numeric_backend") == backend
        ]
        present_threads = sorted({int(row["threads"]) for row in backend_rows})
        complete = present_threads == list(THREADS)
        coverage_rows.append(
            {
                "算法": LABELS[backend],
                "原始后端": backend,
                "记录数": len(backend_rows),
                "现有线程": ",".join(str(thread) for thread in present_threads),
                "覆盖完整": "是" if complete else "否",
            }
        )
        if not complete:
            raise RuntimeError(f"incomplete 1..20 coverage for {backend}")

    return {"baseline": baseline[0], "coverage_rows": coverage_rows}


def select_backend_rows(
    rows: list[dict[str, str]],
    backend: str,
    baseline: dict[str, str],
) -> list[dict[str, object]]:
    baseline_total_ms = f(baseline, "amortized_total_ms")
    baseline_rss_gib = f(baseline, "isolated_peak_rss_mb") / 1024.0
    selected: list[dict[str, object]] = []
    for thread in THREADS:
        matches = [
            row
            for row in rows
            if row.get("mode") == "parallel_symbolic_reuse"
            and row.get("numeric_backend") == backend
            and int(row["threads"]) == thread
        ]
        if len(matches) != 1:
            raise RuntimeError(f"expected one row for {backend} thread {thread}, got {len(matches)}")
        row = matches[0]
        rss_gib = f(row, "isolated_peak_rss_mb") / 1024.0
        extra_gib = max(0.0, rss_gib - baseline_rss_gib)
        base_gib = rss_gib - extra_gib
        total_ms = f(row, "amortized_total_ms")
        selected.append(
            {
                "算法": LABELS[backend],
                "原始后端": backend,
                "线程数": thread,
                "峰值内存_GiB": rss_gib,
                "基础内存_GiB": base_gib,
                "额外内存_GiB": extra_gib,
                "符号预处理_ms": f(row, "symbolic_total_ms"),
                "数值组装_ms": f(row, "numeric_ms"),
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
        fontsize=16.5,
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
        fontsize=11.2,
        color="#667078",
    )


def format_axis(ax: plt.Axes, ylabel: str) -> None:
    ax.set_ylabel(ylabel, fontsize=12.5, labelpad=8)
    ax.set_xlabel("线程数", fontsize=11.5, labelpad=7)
    ax.set_xticks([1, 4, 8, 12, 16, 20])
    ax.tick_params(axis="y", labelsize=10.3, colors="#667078")
    ax.tick_params(axis="x", labelsize=10.3, length=0, pad=6)
    ax.grid(axis="y", color="#DFDFDF", linewidth=0.9)
    ax.set_axisbelow(True)
    ax.spines["left"].set_linewidth(1.05)
    ax.spines["bottom"].set_linewidth(1.05)


def annotate_key_point(
    ax: plt.Axes,
    x: float,
    y: float,
    label: str,
    color: str,
    dy_fraction: float = 0.06,
) -> None:
    ymin, ymax = ax.get_ylim()
    dy = (ymax - ymin) * dy_fraction
    ax.scatter([x], [y], s=42, color=color, edgecolor="white", linewidth=0.9, zorder=5)
    ax.text(
        x,
        y + dy,
        label,
        ha="center",
        va="bottom",
        fontsize=10.0,
        color="#202020",
    )


def draw_backend(rows: list[dict[str, object]], out_root: Path, backend: str) -> list[Path]:
    configure_style()
    asset_dir = out_root / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    threads = [int(row["线程数"]) for row in rows]
    peak_memory = [float(row["峰值内存_GiB"]) for row in rows]
    base_memory = [float(row["基础内存_GiB"]) for row in rows]
    extra_memory = [float(row["额外内存_GiB"]) for row in rows]
    symbolic = [float(row["符号预处理_ms"]) for row in rows]
    numeric = [float(row["数值组装_ms"]) for row in rows]
    total = [float(row["总耗时_ms"]) for row in rows]
    speedup = [float(row["整体加速比"]) for row in rows]
    baseline_ms = float(rows[0]["串行基线总耗时_ms"])
    cpu_model = str(rows[0]["CPU型号"])
    label = LABELS[backend]

    green = "#76B900"
    pale_green = "#C8E88B"
    base_grey = "#D9DEE3"
    dark_text = "#202020"

    fig = plt.figure(figsize=(12.8, 7.2), dpi=240)
    fig.text(0.055, 0.905, f"{label}算法线程扩展效果", fontsize=24, color=dark_text, ha="left")
    fig.text(
        0.055,
        0.855,
        f"风机轮毂工程网格 · 四面体单元 · {cpu_model}",
        fontsize=16,
        color="#60686F",
        ha="left",
    )

    ax_mem = fig.add_axes((0.07, 0.33, 0.27, 0.43))
    ax_mem.bar(threads, base_memory, width=0.72, color=base_grey, edgecolor="none", label="基础内存")
    ax_mem.bar(
        threads,
        extra_memory,
        bottom=base_memory,
        width=0.72,
        color=green,
        edgecolor="none",
        label="额外内存",
    )
    ax_mem.set_xlim(0.3, 20.7)
    ax_mem.set_ylim(0, max(peak_memory) * 1.18)
    format_axis(ax_mem, "吉字节")
    add_panel_title(ax_mem, "实测峰值内存", "越低越好")
    ax_mem.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.02),
        frameon=False,
        fontsize=10.2,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )
    peak_idx = max(range(len(peak_memory)), key=lambda idx: peak_memory[idx])
    annotate_key_point(
        ax_mem,
        threads[peak_idx],
        peak_memory[peak_idx],
        f"峰值 {peak_memory[peak_idx]:.2f}",
        green,
        0.045,
    )

    ax_time = fig.add_axes((0.385, 0.33, 0.27, 0.43))
    ax_time.bar(threads, numeric, width=0.72, color=green, edgecolor="none", label="组装")
    ax_time.bar(
        threads,
        symbolic,
        bottom=numeric,
        width=0.72,
        color=pale_green,
        edgecolor="none",
        label="符号预处理",
    )
    ax_time.set_xlim(0.3, 20.7)
    ax_time.set_ylim(0, max(total) * 1.18)
    format_axis(ax_time, "毫秒")
    add_panel_title(ax_time, "耗时", "越低越好")
    ax_time.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.02),
        frameon=False,
        fontsize=10.2,
        ncol=2,
        handlelength=1.1,
        columnspacing=1.0,
    )
    min_time_idx = min(range(len(total)), key=lambda idx: total[idx])
    annotate_key_point(
        ax_time,
        threads[min_time_idx],
        total[min_time_idx],
        f"最低 {total[min_time_idx]:.0f}",
        green,
        0.045,
    )

    ax_speed = fig.add_axes((0.70, 0.33, 0.27, 0.43))
    ax_speed.plot(threads, speedup, color=green, linewidth=2.4, marker="o", markersize=4.2)
    ax_speed.fill_between(threads, speedup, color=green, alpha=0.10)
    ax_speed.set_xlim(0.7, 20.3)
    ax_speed.set_ylim(0, max(speedup) * 1.24)
    format_axis(ax_speed, "倍")
    add_panel_title(ax_speed, "整体加速比", "越高越好")
    max_speed_idx = max(range(len(speedup)), key=lambda idx: speedup[idx])
    annotate_key_point(
        ax_speed,
        threads[max_speed_idx],
        speedup[max_speed_idx],
        f"最高 {speedup[max_speed_idx]:.2f}x\n{threads[max_speed_idx]}线程",
        green,
        0.055,
    )

    fig.text(
        0.055,
        0.115,
        "基线：串行 1 线程；内存：隔离实测峰值，深色为相对串行基线新增峰值。",
        fontsize=12.7,
        color="#333333",
        ha="left",
    )
    fig.text(
        0.055,
        0.079,
        (
            "耗时：符号预处理 + 组装；"
            f"加速比：{baseline_ms:.0f} 毫秒 ÷ 当前耗时；"
            "本轮为 1 次快速隔离实测，不含网格读取。"
        ),
        fontsize=11.2,
        color="#737A80",
        ha="left",
    )

    base = asset_dir / f"linux_thread_trend_{FILE_LABELS[backend]}_cn"
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
    all_rows: dict[str, list[dict[str, object]]],
    coverage_rows: list[dict[str, object]],
    source_csv: Path,
) -> Path:
    path = out_root / "linux_backend_thread_trends_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Linux 五类数值组装算法线程趋势图说明\n\n")
        handle.write("## 数据物理含义\n\n")
        handle.write("- 每张图只展示一种并行数值后端在 1..20 线程下的趋势。\n")
        handle.write("- 基线为 `symbolic_reuse_serial / cpu_serial / 1线程`。\n")
        handle.write("- 并行行均为 `parallel_symbolic_reuse`，即并行符号组装 + 对应并行数值后端。\n")
        handle.write("- `总耗时 = symbolic_total_ms + numeric_ms`；加速比为串行基线总耗时除以当前总耗时。\n")
        handle.write("- 内存使用 `isolated_peak_rss_mb`，图中额外内存为相对串行基线峰值 RSS 的新增部分。\n\n")

        handle.write("## 趋势摘要\n\n")
        handle.write("| 算法 | 最低耗时线程 | 最低耗时(ms) | 最高加速比线程 | 最高加速比 | 峰值内存(GiB) |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for backend in BACKENDS:
            rows = all_rows[backend]
            min_time = min(rows, key=lambda row: float(row["总耗时_ms"]))
            max_speed = max(rows, key=lambda row: float(row["整体加速比"]))
            max_mem = max(rows, key=lambda row: float(row["峰值内存_GiB"]))
            handle.write(
                f"| {LABELS[backend]} | {min_time['线程数']} | {float(min_time['总耗时_ms']):.3f} | "
                f"{max_speed['线程数']} | {float(max_speed['整体加速比']):.3f} | "
                f"{float(max_mem['峰值内存_GiB']):.3f} |\n"
            )

        handle.write("\n## 覆盖审计\n\n")
        handle.write("| 算法 | 记录数 | 覆盖完整 | 现有线程 |\n")
        handle.write("|---|---:|---|---|\n")
        for row in coverage_rows:
            handle.write(
                f"| {row['算法']} | {row['记录数']} | {row['覆盖完整']} | {row['现有线程']} |\n"
            )
        handle.write(f"\nsource_csv: `{source_csv}`\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    args = parser.parse_args()

    rows = read_csv(args.input)
    validation = validate_raw_rows(rows)
    baseline = validation["baseline"]
    coverage_rows = validation["coverage_rows"]

    source_dir = args.out_root / "source_data"
    all_backend_rows: dict[str, list[dict[str, object]]] = {}
    all_outputs: list[Path] = []
    for backend in BACKENDS:
        backend_rows = select_backend_rows(rows, backend, baseline)  # type: ignore[arg-type]
        all_backend_rows[backend] = backend_rows
        write_csv(source_dir / f"linux_thread_trend_{FILE_LABELS[backend]}_rows.csv", backend_rows)
        all_outputs.extend(draw_backend(backend_rows, args.out_root, backend))

    write_csv(source_dir / "linux_thread_trend_coverage.csv", coverage_rows)  # type: ignore[arg-type]
    summary = write_summary(args.out_root, all_backend_rows, coverage_rows, args.input)  # type: ignore[arg-type]

    print("Coverage rows:", source_dir / "linux_thread_trend_coverage.csv")
    for backend in BACKENDS:
        print("Source rows:", source_dir / f"linux_thread_trend_{FILE_LABELS[backend]}_rows.csv")
    print("Summary:", summary)
    for output in all_outputs:
        print("Figure:", output)


if __name__ == "__main__":
    main()
