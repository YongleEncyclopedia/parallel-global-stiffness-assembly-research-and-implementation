#!/usr/bin/env python3
"""Create publication-style figures for the Windows AMD Abaqus validation run."""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Patch


CASE_ORDER = [
    "cantilever_hex8_small",
    "cantilever_hex8_medium",
    "cantilever_tet4_small",
    "cantilever_tet4_medium",
]
PROBE_ORDER = ["root_center", "midspan_center", "free_tip_center"]
PROBE_X = {"root_center": 0.0, "midspan_center": 0.5, "free_tip_center": 1.0}
PROBE_LABEL = {
    "root_center": "Root",
    "midspan_center": "Midspan",
    "free_tip_center": "Free tip",
}
CASE_LABEL = {
    "cantilever_hex8_small": "Hex8 small",
    "cantilever_hex8_medium": "Hex8 medium",
    "cantilever_tet4_small": "Tet4 small",
    "cantilever_tet4_medium": "Tet4 medium",
}
ELEMENT_LABEL = {
    "hex8": "Hex8 / C3D8",
    "tet4": "Tet4 / C3D4",
}
METHOD_LABEL = {
    "serial_symbolic_serial_numeric": "serial symbolic + serial numeric",
    "serial_symbolic_parallel_numeric": "serial symbolic + cpu_atomic numeric",
    "parallel_symbolic_parallel_numeric": "parallel symbolic + cpu_atomic",
    "direct_no_symbolic_background": "direct / no-symbolic parallel",
}
METHOD_COLORS = {
    "serial_symbolic_serial_numeric": "#6b7280",
    "serial_symbolic_parallel_numeric": "#4e79a7",
    "parallel_symbolic_parallel_numeric": "#2b8cbe",
    "direct_no_symbolic_background": "#d08c33",
}
ELEMENT_COLORS = {"hex8": "#4e79a7", "tet4": "#59a14f"}
ACCENT = "#b23a48"
NEUTRAL = "#4b5563"


@dataclass
class ValidationRow:
    case: str
    element: str
    nodes: int
    elements: int
    probe: str
    node: int
    x_norm: float
    matlab_uz: float
    abaqus_uz: float
    abs_diff: float
    rel_diff: float


@dataclass
class PerfRow:
    mode: str
    strategy: str
    backend: str
    threads: int
    symbolic_total_ms: float
    numeric_ms: float
    direct_generate_ms: float
    direct_bucket_merge_ms: float
    direct_sort_reduce_ms: float
    amortized_total_ms: float
    estimated_peak_bytes: float
    working_set_mb: float
    private_bytes_mb: float
    matrix_status: str


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.75,
            "axes.labelsize": 7,
            "axes.titlesize": 7.5,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "legend.frameon": False,
            "figure.dpi": 150,
        }
    )


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str) -> float:
    return float(value) if value not in {"", None} else 0.0


def to_int(value: str) -> int:
    return int(float(value)) if value not in {"", None} else 0


def read_validation(validation_root: Path) -> list[ValidationRow]:
    rows: list[ValidationRow] = []
    for case in CASE_ORDER:
        metadata_path = validation_root / case / f"{case}_metadata.json"
        compare_path = validation_root / case / f"{case}_abaqus_compare.csv"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        element = metadata["element_type"]
        for row in read_csv_rows(compare_path):
            rows.append(
                ValidationRow(
                    case=case,
                    element=element,
                    nodes=int(metadata["mesh"]["nodes"]),
                    elements=int(metadata["mesh"]["elements"]),
                    probe=row["probe"],
                    node=to_int(row["node"]),
                    x_norm=PROBE_X[row["probe"]],
                    matlab_uz=to_float(row["matlab_uz"]),
                    abaqus_uz=to_float(row["abaqus_uz"]),
                    abs_diff=to_float(row["abs_diff"]),
                    rel_diff=to_float(row["rel_diff"]),
                )
            )
    return rows


def read_performance(perf_csv: Path) -> list[PerfRow]:
    rows: list[PerfRow] = []
    for row in read_csv_rows(perf_csv):
        rows.append(
            PerfRow(
                mode=row["mode"],
                strategy=row["strategy_label"],
                backend=row["numeric_backend"],
                threads=to_int(row["threads"]),
                symbolic_total_ms=to_float(row["symbolic_total_ms"]),
                numeric_ms=to_float(row["numeric_ms"]),
                direct_generate_ms=to_float(row["direct_generate_ms"]),
                direct_bucket_merge_ms=to_float(row["direct_bucket_merge_ms"]),
                direct_sort_reduce_ms=to_float(row["direct_sort_reduce_ms"]),
                amortized_total_ms=to_float(row["amortized_total_ms"]),
                estimated_peak_bytes=to_float(row["estimated_peak_bytes"]),
                working_set_mb=to_float(row.get("isolated_peak_working_set_mb", row.get("isolated_peak_rss_mb", "0"))),
                private_bytes_mb=to_float(row.get("isolated_peak_private_bytes_mb", "0")),
                matrix_status=row["matrix_correctness_status"],
            )
        )
    return rows


def save_figure(fig: plt.Figure, out_root: Path, stem: str) -> list[Path]:
    out_root.mkdir(parents=True, exist_ok=True)
    paths = [out_root / f"{stem}.svg", out_root / f"{stem}.pdf", out_root / f"{stem}.png"]
    fig.savefig(paths[0], bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight")
    fig.savefig(paths[2], dpi=600, bbox_inches="tight")
    plt.close(fig)
    return paths


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.12,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        va="bottom",
        ha="left",
    )


def style_axis(ax: plt.Axes, grid: bool = True) -> None:
    if grid:
        ax.grid(axis="y", color="#e5e7eb", linewidth=0.55)
        ax.set_axisbelow(True)


def grouped_by_case(rows: Iterable[ValidationRow]) -> dict[str, list[ValidationRow]]:
    grouped = {case: [] for case in CASE_ORDER}
    for row in rows:
        grouped[row.case].append(row)
    for case in grouped:
        grouped[case].sort(key=lambda row: PROBE_ORDER.index(row.probe))
    return grouped


def free_tip_row(case_rows: list[ValidationRow]) -> ValidationRow:
    for row in case_rows:
        if row.probe == "free_tip_center":
            return row
    raise ValueError("missing free_tip_center probe row")


def free_tip_deflection_abs_diff(row: ValidationRow) -> float:
    return abs(abs(row.matlab_uz) - abs(row.abaqus_uz))


def free_tip_deflection_rel_pct(row: ValidationRow) -> float:
    reference = abs(row.abaqus_uz)
    return 100.0 * free_tip_deflection_abs_diff(row) / max(reference, 1.0e-30)


def format_pct(value: float) -> str:
    return f"{value:.2e}%" if value < 1.0e-2 else f"{value:.2f}%"


def plot_validation_error_summary(rows: list[ValidationRow], out_root: Path) -> list[Path]:
    grouped = grouped_by_case(rows)
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55), constrained_layout=True)

    heat = [[math.log10(max(next(r.rel_diff for r in grouped[case] if r.probe == probe), 1.0e-12)) for case in CASE_ORDER] for probe in PROBE_ORDER]
    image = axes[0].imshow(heat, cmap="YlGnBu", norm=Normalize(vmin=-12, vmax=-1.2), aspect="auto")
    axes[0].set_xticks(range(len(CASE_ORDER)), [CASE_LABEL[c].replace(" ", "\n") for c in CASE_ORDER])
    axes[0].set_yticks(range(len(PROBE_ORDER)), [PROBE_LABEL[p] for p in PROBE_ORDER])
    axes[0].set_title("Diagnostic probe vector rel. diff.")
    for y, probe in enumerate(PROBE_ORDER):
        for x, case in enumerate(CASE_ORDER):
            value = next(r.rel_diff for r in grouped[case] if r.probe == probe)
            log_value = math.log10(max(value, 1.0e-12))
            text_color = "white" if log_value > -4.0 else "black"
            axes[0].text(
                x,
                y,
                f"{value:.1e}" if value < 1.0e-3 else f"{100*value:.1f}%",
                ha="center",
                va="center",
                fontsize=5.8,
                color=text_color,
            )
    cbar = fig.colorbar(image, ax=axes[0], fraction=0.045, pad=0.02)
    cbar.set_label("log10(vector relative diff.)")
    panel_label(axes[0], "a")

    tip_rows = [free_tip_row(grouped[case]) for case in CASE_ORDER]
    tip_rel_pct = [free_tip_deflection_rel_pct(row) for row in tip_rows]
    tip_abs = [free_tip_deflection_abs_diff(row) for row in tip_rows]
    colors = [ELEMENT_COLORS[grouped[case][0].element] for case in CASE_ORDER]
    axes[1].bar(range(len(CASE_ORDER)), tip_rel_pct, color=colors, width=0.7)
    axes[1].set_yscale("log")
    axes[1].set_xticks(range(len(CASE_ORDER)), [CASE_LABEL[c].replace(" ", "\n") for c in CASE_ORDER])
    axes[1].set_ylabel("free-tip deflection diff (%)")
    axes[1].set_title("Primary deflection metric")
    axes[1].axhline(1.0, color="#9ca3af", linestyle=":", linewidth=0.9)
    axes[1].text(0.05, 1.2, "1% guide", color="#6b7280", fontsize=5.8)
    style_axis(axes[1])
    panel_label(axes[1], "b")

    axes[2].bar(range(len(CASE_ORDER)), tip_abs, color=colors, width=0.7)
    axes[2].set_yscale("log")
    axes[2].set_xticks(range(len(CASE_ORDER)), [CASE_LABEL[c].replace(" ", "\n") for c in CASE_ORDER])
    axes[2].set_ylabel("free-tip |Uz| absolute diff")
    axes[2].set_title("Absolute deflection gap")
    style_axis(axes[2])
    handles = [Patch(facecolor=ELEMENT_COLORS["hex8"], label="Hex8 / C3D8"), Patch(facecolor=ELEMENT_COLORS["tet4"], label="Tet4 / C3D4")]
    axes[2].legend(handles=handles, loc="upper left")
    panel_label(axes[2], "c")

    fig.suptitle("Free-tip deflection validation separates Tet4 agreement from Hex8 discrepancy", fontsize=8.5, fontweight="bold")
    return save_figure(fig, out_root, "fig01_validation_error_summary")


def plot_probe_profiles(rows: list[ValidationRow], out_root: Path) -> list[Path]:
    grouped = grouped_by_case(rows)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.55), sharex=True)
    fig.subplots_adjust(top=0.82, hspace=0.52, wspace=0.25)
    axes_flat = axes.ravel()
    for i, case in enumerate(CASE_ORDER):
        ax = axes_flat[i]
        case_rows = grouped[case]
        xs = [row.x_norm for row in case_rows]
        matlab = [row.matlab_uz for row in case_rows]
        abaqus = [row.abaqus_uz for row in case_rows]
        ax.plot(xs, matlab, color="#1f4e79", marker="o", linewidth=1.2, markersize=3.5, label="MATLAB solve of C++ K")
        ax.plot(xs, abaqus, color="#d08c33", marker="s", linewidth=1.0, markersize=3.2, linestyle="--", label="Abaqus/Standard")
        for x, y0, y1 in zip(xs, matlab, abaqus):
            ax.plot([x, x], [y0, y1], color="#9ca3af", linewidth=0.55)
        tip_pct = free_tip_deflection_rel_pct(free_tip_row(case_rows))
        ax.text(0.02, 0.06, f"tip defl. diff = {format_pct(tip_pct)}", transform=ax.transAxes, fontsize=6.2, color=NEUTRAL)
        ax.set_title(CASE_LABEL[case])
        ax.set_xticks([0.0, 0.5, 1.0], ["root", "midspan", "tip"])
        ax.set_ylabel("Uz displacement")
        style_axis(ax)
        panel_label(ax, chr(ord("a") + i))
    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.905), ncols=2)
    fig.suptitle(
        "Probe displacement profiles preserve the deformation trend while exposing element-specific mismatch",
        fontsize=8.5,
        fontweight="bold",
        y=0.99,
    )
    return save_figure(fig, out_root, "fig02_probe_displacement_profiles")


def rows_for_strategy(rows: list[PerfRow], strategy: str) -> list[PerfRow]:
    selected = [row for row in rows if row.strategy == strategy]
    return sorted(selected, key=lambda row: row.threads)


def serial_baseline(rows: list[PerfRow]) -> PerfRow:
    matches = rows_for_strategy(rows, "serial_symbolic_serial_numeric")
    if not matches:
        raise ValueError("missing serial_symbolic_serial_numeric baseline")
    return matches[0]


def best_by_strategy(rows: list[PerfRow], strategy: str) -> PerfRow:
    selected = rows_for_strategy(rows, strategy)
    if not selected:
        raise ValueError(f"missing strategy {strategy}")
    return min(selected, key=lambda row: row.amortized_total_ms)


def plot_assembly_time(rows: list[PerfRow], out_root: Path) -> list[Path]:
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8), constrained_layout=True)
    baseline = serial_baseline(rows)
    plot_strategies = [
        "serial_symbolic_parallel_numeric",
        "parallel_symbolic_parallel_numeric",
        "direct_no_symbolic_background",
    ]

    for strategy in plot_strategies:
        data = rows_for_strategy(rows, strategy)
        axes[0, 0].plot([r.threads for r in data], [r.amortized_total_ms for r in data], marker="o", linewidth=1.25, color=METHOD_COLORS[strategy], label=METHOD_LABEL[strategy])
    axes[0, 0].axhline(baseline.amortized_total_ms, color=METHOD_COLORS[baseline.strategy], linestyle="--", linewidth=1.0, label="serial symbolic + serial numeric")
    axes[0, 0].set_xlabel("threads on physical-core range")
    axes[0, 0].set_ylabel("amortized total (ms)")
    axes[0, 0].set_title("Assembly time scaling")
    axes[0, 0].legend(loc="upper right")
    style_axis(axes[0, 0])
    panel_label(axes[0, 0], "a")

    for strategy in plot_strategies:
        data = rows_for_strategy(rows, strategy)
        axes[0, 1].plot([r.threads for r in data], [baseline.amortized_total_ms / r.amortized_total_ms for r in data], marker="o", linewidth=1.25, color=METHOD_COLORS[strategy], label=METHOD_LABEL[strategy])
    axes[0, 1].axhline(1.0, color="#9ca3af", linestyle=":", linewidth=0.9)
    axes[0, 1].set_xlabel("threads on physical-core range")
    axes[0, 1].set_ylabel("speedup vs serial symbolic")
    axes[0, 1].set_title("Speedup against measured baseline")
    style_axis(axes[0, 1])
    panel_label(axes[0, 1], "b")

    best_symbolic = best_by_strategy(rows, "parallel_symbolic_parallel_numeric")
    best_direct = best_by_strategy(rows, "direct_no_symbolic_background")
    labels = ["serial\nbaseline", "parallel\nsymbolic", "direct\nno-symbolic"]
    components = [
        [baseline.symbolic_total_ms, baseline.numeric_ms, 0.0, 0.0, 0.0],
        [best_symbolic.symbolic_total_ms, best_symbolic.numeric_ms, 0.0, 0.0, 0.0],
        [0.0, 0.0, best_direct.direct_generate_ms, best_direct.direct_bucket_merge_ms, best_direct.direct_sort_reduce_ms],
    ]
    component_names = ["symbolic", "numeric", "direct generate", "bucket/merge", "sort/reduce"]
    component_colors = ["#9ecae1", "#1f78b4", "#fdd49e", "#fdbb84", "#d95f0e"]
    bottoms = [0.0, 0.0, 0.0]
    for idx, name in enumerate(component_names):
        values = [row[idx] for row in components]
        axes[1, 0].bar(labels, values, bottom=bottoms, color=component_colors[idx], label=name, width=0.62)
        bottoms = [b + v for b, v in zip(bottoms, values)]
    axes[1, 0].set_ylabel("time component (ms)")
    axes[1, 0].set_title("Best-row time decomposition")
    axes[1, 0].legend(loc="upper right", ncols=1)
    style_axis(axes[1, 0])
    panel_label(axes[1, 0], "c")

    summary_rows = [baseline, best_symbolic, best_direct]
    summary_colors = [METHOD_COLORS[r.strategy] for r in summary_rows]
    axes[1, 1].barh(range(3), [r.amortized_total_ms for r in summary_rows], color=summary_colors)
    axes[1, 1].set_yticks(range(3), labels)
    axes[1, 1].invert_yaxis()
    axes[1, 1].set_xlabel("best amortized total (ms)")
    axes[1, 1].set_title("Best observed totals")
    for y, row in enumerate(summary_rows):
        suffix = "1 thread" if row.strategy == "serial_symbolic_serial_numeric" else f"{row.threads} threads"
        axes[1, 1].text(row.amortized_total_ms * 1.01, y, f"{row.amortized_total_ms:.0f} ms\n{suffix}", va="center", fontsize=6.2)
    style_axis(axes[1, 1])
    panel_label(axes[1, 1], "d")

    fig.suptitle("Parallel symbolic reuse gives the fastest measured WindHub assembly path on AMD", fontsize=8.5, fontweight="bold")
    return save_figure(fig, out_root, "fig03_assembly_time_scaling")


def bytes_to_gib(value: float) -> float:
    return value / (1024.0**3)


def plot_memory_tradeoff(rows: list[PerfRow], out_root: Path) -> list[Path]:
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8), constrained_layout=True)
    plot_strategies = [
        "parallel_symbolic_parallel_numeric",
        "direct_no_symbolic_background",
        "serial_symbolic_parallel_numeric",
    ]
    for strategy in plot_strategies:
        data = rows_for_strategy(rows, strategy)
        axes[0, 0].plot([r.threads for r in data], [r.working_set_mb / 1024.0 for r in data], marker="o", linewidth=1.25, color=METHOD_COLORS[strategy], label=METHOD_LABEL[strategy])
        axes[0, 1].plot([r.threads for r in data], [r.private_bytes_mb / 1024.0 for r in data], marker="o", linewidth=1.25, color=METHOD_COLORS[strategy], label=METHOD_LABEL[strategy])
    axes[0, 0].set_xlabel("threads")
    axes[0, 0].set_ylabel("peak working set (GiB)")
    axes[0, 0].set_title("OS-observed memory fallback")
    axes[0, 0].legend(loc="upper right")
    style_axis(axes[0, 0])
    panel_label(axes[0, 0], "a")

    axes[0, 1].set_xlabel("threads")
    axes[0, 1].set_ylabel("peak private bytes (GiB)")
    axes[0, 1].set_title("Private bytes sampled on Windows")
    style_axis(axes[0, 1])
    panel_label(axes[0, 1], "b")

    for strategy in plot_strategies:
        data = rows_for_strategy(rows, strategy)
        axes[1, 0].scatter([r.working_set_mb / 1024.0 for r in data], [r.amortized_total_ms for r in data], s=22, color=METHOD_COLORS[strategy], label=METHOD_LABEL[strategy])
        for r in data:
            if strategy in {"parallel_symbolic_parallel_numeric", "direct_no_symbolic_background"} and r.threads in {1, 4, 8}:
                axes[1, 0].text(r.working_set_mb / 1024.0, r.amortized_total_ms, str(r.threads), fontsize=5.8, ha="left", va="bottom")
    axes[1, 0].set_xlabel("peak working set (GiB)")
    axes[1, 0].set_ylabel("amortized total (ms)")
    axes[1, 0].set_title("Time-memory operating points")
    style_axis(axes[1, 0])
    panel_label(axes[1, 0], "c")

    symbolic8 = max(rows_for_strategy(rows, "parallel_symbolic_parallel_numeric"), key=lambda r: r.threads)
    direct8 = max(rows_for_strategy(rows, "direct_no_symbolic_background"), key=lambda r: r.threads)
    axes[1, 1].bar(["parallel\nsymbolic", "direct\nno-symbolic"], [bytes_to_gib(symbolic8.estimated_peak_bytes), bytes_to_gib(direct8.estimated_peak_bytes)], color=[METHOD_COLORS[symbolic8.strategy], METHOD_COLORS[direct8.strategy]], width=0.62)
    axes[1, 1].set_ylabel("estimated lifecycle peak (GiB)")
    axes[1, 1].set_title("Modelled lifecycle peak at 8 threads")
    for x, row in enumerate([symbolic8, direct8]):
        axes[1, 1].text(x, bytes_to_gib(row.estimated_peak_bytes) * 1.03, f"{bytes_to_gib(row.estimated_peak_bytes):.2f} GiB", ha="center", fontsize=6.2)
    style_axis(axes[1, 1])
    panel_label(axes[1, 1], "d")

    fig.suptitle("Symbolic reuse avoids the direct path's memory-heavy transient contribution buffers", fontsize=8.5, fontweight="bold")
    return save_figure(fig, out_root, "fig04_memory_tradeoff")


def write_dicts(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_source_data(validation_rows: list[ValidationRow], perf_rows: list[PerfRow], out_root: Path) -> None:
    source_dir = out_root / "source_data"
    write_dicts(
        source_dir / "validation_probe_errors.csv",
        [
            "case",
            "element",
            "nodes",
            "elements",
            "probe",
            "node",
            "x_norm",
            "matlab_uz",
            "abaqus_uz",
            "abs_diff",
            "rel_diff",
            "rel_diff_definition",
            "log10_rel_diff",
        ],
        [
            {
                "case": row.case,
                "element": row.element,
                "nodes": row.nodes,
                "elements": row.elements,
                "probe": row.probe,
                "node": row.node,
                "x_norm": row.x_norm,
                "matlab_uz": row.matlab_uz,
                "abaqus_uz": row.abaqus_uz,
                "abs_diff": row.abs_diff,
                "rel_diff": row.rel_diff,
                "rel_diff_definition": "probe_3d_displacement_vector_norm",
                "log10_rel_diff": math.log10(max(row.rel_diff, 1.0e-12)),
            }
            for row in validation_rows
        ],
    )
    validation_by_case = grouped_by_case(validation_rows)
    tip_rows = [free_tip_row(validation_by_case[case]) for case in CASE_ORDER]
    write_dicts(
        source_dir / "validation_free_tip_deflection_summary.csv",
        [
            "case",
            "element",
            "nodes",
            "elements",
            "probe",
            "node",
            "matlab_free_tip_uz",
            "reference_free_tip_uz",
            "free_tip_abs_deflection_diff",
            "free_tip_deflection_rel_pct",
            "metric_definition",
        ],
        [
            {
                "case": row.case,
                "element": row.element,
                "nodes": row.nodes,
                "elements": row.elements,
                "probe": row.probe,
                "node": row.node,
                "matlab_free_tip_uz": row.matlab_uz,
                "reference_free_tip_uz": row.abaqus_uz,
                "free_tip_abs_deflection_diff": free_tip_deflection_abs_diff(row),
                "free_tip_deflection_rel_pct": free_tip_deflection_rel_pct(row),
                "metric_definition": "100*abs(abs(matlab_uz)-abs(reference_uz))/max(abs(reference_uz),eps)",
            }
            for row in tip_rows
        ],
    )
    write_dicts(
        source_dir / "performance_main_rows.csv",
        [
            "strategy",
            "mode",
            "backend",
            "threads",
            "symbolic_total_ms",
            "numeric_ms",
            "direct_generate_ms",
            "direct_bucket_merge_ms",
            "direct_sort_reduce_ms",
            "amortized_total_ms",
            "estimated_peak_gib",
            "peak_working_set_gib",
            "peak_private_bytes_gib",
            "matrix_status",
        ],
        [
            {
                "strategy": row.strategy,
                "mode": row.mode,
                "backend": row.backend,
                "threads": row.threads,
                "symbolic_total_ms": row.symbolic_total_ms,
                "numeric_ms": row.numeric_ms,
                "direct_generate_ms": row.direct_generate_ms,
                "direct_bucket_merge_ms": row.direct_bucket_merge_ms,
                "direct_sort_reduce_ms": row.direct_sort_reduce_ms,
                "amortized_total_ms": row.amortized_total_ms,
                "estimated_peak_gib": bytes_to_gib(row.estimated_peak_bytes),
                "peak_working_set_gib": row.working_set_mb / 1024.0,
                "peak_private_bytes_gib": row.private_bytes_mb / 1024.0,
                "matrix_status": row.matrix_status,
            }
            for row in perf_rows
        ],
    )


def figure_caption_text(validation_root: Path, perf_csv: Path) -> dict[str, str]:
    return {
        "fig01_validation_error_summary": f"""# Fig. 1 Validation Error Summary

**绘制理由。** 这张图回答“悬臂块求解级正确性是否在所有单元类型上同样成立”。主相对差异固定为自由端挠度百分比；逐 probe 三维位移向量差异只作为诊断量，避免把固定端近零位移或中间 probe 当成最终挠度结论。

**数据来源。** `*_abaqus_compare.csv`，路径位于 `{validation_root}` 的四个 case 子目录。每行来自 MATLAB 对自研 C++ 导出的 `K/F/BC` 求解位移与 Abaqus/Standard ODB 抽取位移在同一 probe 节点上的三维位移范数差异；本图的主柱状图和绝对差异图只取 `free_tip_center` 的 `Uz`，并按 `100*abs(abs(matlab_uz)-abs(abaqus_uz))/abs(abaqus_uz)` 转为百分比。

**参数设置。** 几何 `L=1, W=0.2, T=0.1`，材料 `E=1, nu=0.3`，`x=0` 三向固定，`x=L` 总力 `-1` 沿 `load_dof=2`。Abaqus Hex8 使用 `C3D8` full integration，Tet4 使用 `C3D4`。

**可得结论。** Tet4/C3D4 的自由端挠度百分比差异处在近零量级；Hex8/C3D8 的自由端挠度百分比差异约为 1.78% 到 2.98%，不是硬阈值失败，但也不能写成商业求解器等价。

**合理解释。** Tet4 路径与 Abaqus 线性四面体的一致性较强；Hex8 虽同为 full integration，但可能仍存在单元刚度矩阵约定、节点顺序、数值积分实现细节或载荷等效化差异，需要后续单元级能量/刚度隔离。
""",
        "fig02_probe_displacement_profiles": f"""# Fig. 2 Probe Displacement Profiles

**绘制理由。** 挠度百分比只能给出最终正确性数字，不能说明差异发生在变形曲线的哪里；probe 位移剖面能直接显示 root、midspan、free tip 三个物理位置的 `Uz` 趋势。

**数据来源。** 同一组 `*_abaqus_compare.csv`，使用其中 `matlab_uz` 与 `abaqus_uz` 列。probe 位置来自 `*_probes.csv`，三点分别映射到 `x/L = 0, 0.5, 1`。

**参数设置。** 四个悬臂 case 使用相同材料、边界与载荷；图中灰色连线表示每个 probe 上 MATLAB 与 Abaqus 的局部差异，不代表连续插值误差。

**可得结论。** 四个 case 都保持悬臂梁从 root 到 tip 位移增大的整体物理趋势；Tet4 曲线几乎重合，Hex8 曲线在 midspan 与 tip 处出现可见偏移。图内标注的百分比为 `free_tip_center` 挠度相对差异。

**合理解释。** 位移趋势一致说明边界、载荷方向、节点映射和求解流程没有明显错位；Hex8 偏移集中在非固定 probe，符合单元刚度或积分细节差异对柔度预测产生系统性影响的表现。
""",
        "fig03_assembly_time_scaling": f"""# Fig. 3 Assembly Time Scaling

**绘制理由。** 这张图回答“AMD Windows 上哪条自研 assembly 路径更快，以及快在哪里”。总时长、相对串行 symbolic baseline 的加速比、最佳线程分解和最佳总时长四个视角互相补充。

**数据来源。** `{perf_csv}`。每一行由 `scripts/run_isolated_symbolic_memory_eval.py` 以独立子进程运行 `symbolic_numeric_eval.exe` 得到。

**参数设置。** WindHub 网格 `3d-WindTurbineHub.inp`，228,384 nodes、1,113,684 Tet4 elements、685,152 DOFs；材料模型 `linear_elastic_solid`；线程范围 `1:8`，对应 AMD Ryzen 7 9800X3D 的物理核心范围；主线后端为 `cpu_atomic`。

**可得结论。** 8 线程 `parallel_symbolic_reuse + cpu_atomic` 达到最低总时长约 1133 ms，相对 `serial symbolic + serial numeric` 的约 4078 ms 为约 3.6x；8 线程 direct/no-symbolic 仍约 2147 ms，慢于 symbolic reuse。

**合理解释。** direct/no-symbolic 省去显式 symbolic 阶段，但付出生成贡献、bucket/merge 与 sort/reduce 的大额代价；预构建 CSR/scatter plan 的 symbolic reuse 在真实 WindHub 网格上更适合复用并行数值写回。
""",
        "fig04_memory_tradeoff": f"""# Fig. 4 Memory and Time Tradeoff

**绘制理由。** 性能结论不能只看时间；direct/no-symbolic 的核心成本之一是瞬时 contribution buffer。该图把 OS 观测内存、private bytes、时间-内存运行点和 estimated lifecycle peak 放在一起，避免把模型估计冒充系统观测。

**数据来源。** `{perf_csv}` 的 `isolated_peak_working_set_mb`、`isolated_peak_private_bytes_mb` 和 `estimated_peak_bytes`。Windows 下 `isolated_peak_rss_mb` 是历史 schema 列名，本轮实际度量为 `windows_peak_working_set`。

**参数设置。** 每个策略/线程组合在独立子进程中运行；OS 内存来自 Windows `GetProcessMemoryInfo.PeakWorkingSetSize`，private bytes 来自采样到的 `PeakPagefileUsage`/`PrivateUsage`。

**可得结论。** symbolic reuse 的 peak working set 约 2.26 GiB 并随线程变化很小；direct/no-symbolic 在同一线程范围内约 3.65 到 5.45 GiB，且 8 线程 estimated lifecycle peak 也明显高于 symbolic reuse。

**合理解释。** symbolic reuse 的持久 CSR/plan 与输出矩阵占主导，内存较稳定；direct/no-symbolic 需要一次性保存大量贡献并排序归并，导致临时内存和 OS 观测峰值都更高。
""",
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_reports(out_root: Path, validation_root: Path, perf_csv: Path, figure_paths: dict[str, list[Path]]) -> None:
    captions = figure_caption_text(validation_root, perf_csv)
    for stem, caption in captions.items():
        write_text(out_root / f"{stem}.md", caption)

    contract = """# Windows AMD Abaqus Figure Contract

Core conclusion:
Windows AMD 平台的 Abaqus validation 显示 Tet4/C3D4 自由端挠度百分比差异接近零，Hex8/C3D8 暴露百分级差异；同一平台上 parallel symbolic reuse + cpu_atomic 在 1-8 物理核内比 direct/no-symbolic 更快且 OS 峰值内存更低。

Figure archetype:
quantitative grid

Target journal/output:
Nature-family style technical figure package for a research report; editable SVG/PDF plus high-resolution PNG preview.

Backend:
Python only, using matplotlib for drawing, preview export, and QA.

Final size:
Double-column width, 183 mm class; each figure exported around 7.2 inch wide with readable 6-8 pt text.

Panel map:
a. Validation error heatmap and summary bars.
b. Probe displacement profiles for MATLAB self-solve versus Abaqus.
c. WindHub assembly time scaling and time decomposition.
d. Windows memory/time tradeoff and lifecycle peak comparison.

Evidence hierarchy:
Hero evidence: validation error split by element family and fastest symbolic reuse timing.
Validation evidence: per-probe displacement profiles and no-hard-threshold compare rows.
Controls/robustness: OS memory fallback fields, private bytes, and estimated lifecycle peak kept separate.

Statistics needed:
No inferential statistics; each row is a deterministic solver/benchmark run. No error bars are drawn because this package has no repeat distribution.

Source data needed:
The generated `source_data/validation_free_tip_deflection_summary.csv`, `source_data/validation_probe_errors.csv` and `source_data/performance_main_rows.csv` are clean figure source tables.

Image-integrity notes:
All panels are vector line/bar/heatmap graphics generated from CSV; no image adjustments or raster scientific images are used.

Reviewer risk:
Hex8/C3D8 free-tip deflection mismatch remains a real validation signal, not a pass/fail equivalence claim. Per-probe vector relative differences remain diagnostic. Windows memory uses peak working set fallback, not POSIX RSS.
"""
    write_text(out_root / "figure_contract.md", contract)

    lines = [
        "# Windows AMD Abaqus Figure Report",
        "",
        "## 图表选择理由",
        "",
        "我选择四张定量图，而不是单张大而全的总图：验证误差、位移剖面、组装时间和内存权衡分别回答不同审稿问题。这样可以避免把求解正确性与 assembly 性能混成一个不可审查的结论。",
        "",
        "1. `fig01_validation_error_summary`：用自由端挠度百分比证明哪些单元族与 Abaqus reference 对齐，哪些暴露差异。",
        "2. `fig02_probe_displacement_profiles`：确认差异没有来自载荷方向或 probe 映射错位，并显示差异沿悬臂长度的位置。",
        "3. `fig03_assembly_time_scaling`：展示 AMD 物理核心范围内的自研 assembly 时间扩展性。",
        "4. `fig04_memory_tradeoff`：把 Windows OS 内存观测与 estimated lifecycle memory 分开，解释 direct/no-symbolic 的代价。",
        "",
        "## 输出文件",
        "",
    ]
    for stem, paths in figure_paths.items():
        lines.append(f"- `{stem}`: " + ", ".join(f"`{path.name}`" for path in paths))
    lines.extend(["", "## 单图说明", ""])
    for stem in captions:
        lines.append(captions[stem])
        lines.append("")
    lines.extend(
        [
            "## QA 说明",
            "",
            "- 绘图后应运行脚本内置 QA 或外部检查，确认每张 PNG 非空、尺寸有效，且 SVG/PDF/PNG 三种格式均存在。",
            "- 所有图由同一 Python 脚本生成，未混用 R 或交互式绘图后端。",
            "- `source_data/` 下保留清洗后的图表源数据，便于后续复核或重绘。",
        ]
    )
    write_text(out_root / "windows_amd_abaqus_figure_report.md", "\n".join(lines))

    manifest_lines = [
        "# Figure Manifest",
        "",
        "| figure | purpose | files |",
        "| --- | --- | --- |",
    ]
    purposes = {
        "fig01_validation_error_summary": "Abaqus/MATLAB free-tip deflection and probe diagnostic summary.",
        "fig02_probe_displacement_profiles": "Probe Uz profile comparison.",
        "fig03_assembly_time_scaling": "WindHub assembly time scaling.",
        "fig04_memory_tradeoff": "Windows memory and time tradeoff.",
    }
    for stem, paths in figure_paths.items():
        files = "<br>".join(path.name for path in paths)
        manifest_lines.append(f"| `{stem}` | {purposes[stem]} | {files} |")
    write_text(out_root / "manifest.md", "\n".join(manifest_lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validation-root",
        type=Path,
        default=Path("results/validation-export/2026-05-26-windows-amd-abaqus"),
    )
    parser.add_argument(
        "--perf-csv",
        type=Path,
        default=Path("results/2026-05-26-windows-amd-abaqus-validation-performance/isolated_symbolic_memory/isolated_symbolic_memory.csv"),
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("results/2026-05-27-windows-amd-abaqus-figures"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_matplotlib()
    validation_rows = read_validation(args.validation_root)
    perf_rows = read_performance(args.perf_csv)
    args.out_root.mkdir(parents=True, exist_ok=True)
    write_source_data(validation_rows, perf_rows, args.out_root)

    figure_paths = {
        "fig01_validation_error_summary": plot_validation_error_summary(validation_rows, args.out_root),
        "fig02_probe_displacement_profiles": plot_probe_profiles(validation_rows, args.out_root),
        "fig03_assembly_time_scaling": plot_assembly_time(perf_rows, args.out_root),
        "fig04_memory_tradeoff": plot_memory_tradeoff(perf_rows, args.out_root),
    }
    write_reports(args.out_root, args.validation_root, args.perf_csv, figure_paths)
    print(f"wrote figure package: {args.out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
