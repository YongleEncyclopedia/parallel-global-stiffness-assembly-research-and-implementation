#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate Nature-style figures for the Linux Intel CalculiX validation package.

The script intentionally lives inside the dated results directory. It is a
one-off, reproducible figure package generator and does not modify source code.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Iterable

RESULT_ROOT = Path(__file__).resolve().parent
RESULT_ROOT.mkdir(parents=True, exist_ok=True)
MPLCONFIG_ROOT = Path(os.environ.get("TMPDIR", "/tmp")) / "pgsa_nature_figure_mplconfig"
MPLCONFIG_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_ROOT))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Mandatory editable-text rules from the nature-figure skill.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 7.0
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["legend.frameon"] = False
plt.rcParams["xtick.major.width"] = 0.7
plt.rcParams["ytick.major.width"] = 0.7
plt.rcParams["xtick.major.size"] = 2.6
plt.rcParams["ytick.major.size"] = 2.6

CPU_ROOT = RESULT_ROOT.parents[1]
BENCH_ROOT = CPU_ROOT / "results/2026-05-23-linux-intel-linear-elastic-full-host"
VAL_ROOT = CPU_ROOT / "results/validation-export/2026-05-23-linux-intel-calculix"
FIG_DIR = RESULT_ROOT / "figures"
SOURCE_DIR = RESULT_ROOT / "source_data"
FIG_DIR.mkdir(exist_ok=True)
SOURCE_DIR.mkdir(exist_ok=True)

PALETTE = {
    "atomic": "#0F4D92",
    "private": "#9A4D8E",
    "lock": "#B64342",
    "serial": "#767676",
    "parallel": "#42949E",
    "direct": "#D28B32",
    "light": "#CFCECE",
    "mid": "#767676",
    "dark": "#272727",
    "green": "#2E9E44",
    "red": "#E53935",
}

BACKEND_LABELS = {
    "cpu_atomic": "Atomic",
    "cpu_private_csr": "Private CSR",
    "cpu_lock_guard": "Lock guard",
}

BACKEND_COLORS = {
    "cpu_atomic": PALETTE["atomic"],
    "cpu_private_csr": PALETTE["private"],
    "cpu_lock_guard": PALETTE["lock"],
}

BACKEND_HATCHES = {
    "cpu_atomic": "",
    "cpu_private_csr": "///",
    "cpu_lock_guard": "\\\\\\",
}

SYMBOLIC_LABELS = {
    "serial_symbolic_parallel_numeric": "Serial symbolic + parallel numeric",
    "parallel_symbolic_parallel_numeric": "Parallel symbolic reuse",
    "direct_no_symbolic_background": "Direct no-symbolic",
}

SYMBOLIC_COLORS = {
    "serial_symbolic_parallel_numeric": PALETTE["serial"],
    "parallel_symbolic_parallel_numeric": PALETTE["parallel"],
    "direct_no_symbolic_background": PALETTE["direct"],
}

CASE_ORDER = [
    "cantilever_hex8_small",
    "cantilever_tet4_small",
    "cantilever_hex8_medium",
    "cantilever_tet4_medium",
]

CASE_LABELS = {
    "cantilever_hex8_small": "Hex8 small",
    "cantilever_tet4_small": "Tet4 small",
    "cantilever_hex8_medium": "Hex8 medium",
    "cantilever_tet4_medium": "Tet4 medium",
}

PROBE_ORDER = ["root_center", "midspan_center", "free_tip_center"]
PROBE_LABELS = {
    "root_center": "Root",
    "midspan_center": "Midspan",
    "free_tip_center": "Free tip",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(CPU_ROOT))
    except ValueError:
        return str(path)


def as_float(row: dict[str, str], key: str, default: float = math.nan) -> float:
    value = row.get(key, "")
    if value == "":
        return default
    return float(value)


def bytes_to_gib(value: float) -> float:
    return value / (1024.0**3)


def mib_to_gib(value: float) -> float:
    return value / 1024.0


def add_panel_label(ax, label: str, x: float = -0.16, y: float = 1.05) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        fontweight="bold",
        color="black",
    )


def simplify_axes(ax, grid: bool = False) -> None:
    if grid:
        ax.grid(axis="y", color="#E2E2E2", linewidth=0.5, zorder=0)
    ax.tick_params(labelsize=6.5)


def save_figure(fig, stem: str) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for ext, kwargs in {
        "svg": {},
        "pdf": {},
        "tiff": {"dpi": 600},
        "png": {"dpi": 300},
    }.items():
        path = FIG_DIR / f"{stem}.{ext}"
        fig.savefig(path, bbox_inches="tight", facecolor="white", **kwargs)
        outputs[ext] = rel(path)
    plt.close(fig)
    return outputs


def method_legend_handles(methods: Iterable[str]) -> list[Line2D]:
    return [
        Line2D(
            [0],
            [0],
            color=BACKEND_COLORS[m],
            lw=1.8,
            marker="o",
            markersize=3.5,
            label=BACKEND_LABELS[m],
        )
        for m in methods
    ]


def load_data() -> dict[str, object]:
    backend_csv = BENCH_ROOT / "windhub_backend_tradeoff.csv"
    symbolic_csv = BENCH_ROOT / "isolated_symbolic_memory/isolated_symbolic_memory.csv"
    validation_export_manifest = VAL_ROOT / "validation_export_manifest.json"
    calculix_manifest = VAL_ROOT / "calculix_validation_manifest.json"

    backend_rows = read_csv(backend_csv)
    symbolic_rows = read_csv(symbolic_csv)
    validation_export = json.loads(validation_export_manifest.read_text())
    calculix_validation = json.loads(calculix_manifest.read_text())

    validation_cases = {case["case"]: case for case in calculix_validation["cases"]}
    validation_probe_rows: list[dict[str, object]] = []
    validation_summary: list[dict[str, object]] = []

    for case_name in CASE_ORDER:
        case = validation_cases[case_name]
        compare_csv = Path(case["files"]["probe_compare_csv"])
        probe_rows = read_csv(compare_csv)
        for row in probe_rows:
            enriched = {
                "case": case_name,
                "case_label": CASE_LABELS[case_name],
                "element_type": case["element_type"],
                "nodes": case["mesh"]["nodes"],
                "elements": case["mesh"]["elements"],
                "probe": row["probe"],
                "probe_label": PROBE_LABELS.get(row["probe"], row["probe"]),
                "matlab_ux": float(row["matlab_ux"]),
                "matlab_uy": float(row["matlab_uy"]),
                "matlab_uz": float(row["matlab_uz"]),
                "calculix_ux": float(row["calculix_ux"]),
                "calculix_uy": float(row["calculix_uy"]),
                "calculix_uz": float(row["calculix_uz"]),
                "abs_diff": float(row["abs_diff"]),
                "rel_diff": float(row["rel_diff"]),
                "status": row["status"],
            }
            validation_probe_rows.append(enriched)
        validation_summary.append(
            {
                "case": case_name,
                "case_label": CASE_LABELS[case_name],
                "element_type": case["element_type"],
                "nodes": case["mesh"]["nodes"],
                "elements": case["mesh"]["elements"],
                "fixed_nodes": case["mesh"]["fixed_nodes"],
                "loaded_nodes": case["mesh"]["loaded_nodes"],
                "max_probe": case["max_probe"],
                "max_probe_abs_diff": case["max_probe_abs_diff"],
                "max_probe_rel_diff": case["max_probe_rel_diff"],
                "status": case["status"],
            }
        )

    write_csv(
        SOURCE_DIR / "validation_probe_rows.csv",
        validation_probe_rows,
        [
            "case",
            "case_label",
            "element_type",
            "nodes",
            "elements",
            "probe",
            "probe_label",
            "matlab_ux",
            "matlab_uy",
            "matlab_uz",
            "calculix_ux",
            "calculix_uy",
            "calculix_uz",
            "abs_diff",
            "rel_diff",
            "status",
        ],
    )
    write_csv(
        SOURCE_DIR / "validation_probe_summary.csv",
        validation_summary,
        [
            "case",
            "case_label",
            "element_type",
            "nodes",
            "elements",
            "fixed_nodes",
            "loaded_nodes",
            "max_probe",
            "max_probe_abs_diff",
            "max_probe_rel_diff",
            "status",
        ],
    )

    backend_20 = [
        {
            "algorithm": r["algorithm"],
            "label": BACKEND_LABELS[r["algorithm"]],
            "threads": int(r["threads"]),
            "assembly_ms": float(r["assembly_ms"]),
            "speedup": float(r["speedup"]),
            "efficiency": float(r["efficiency"]),
            "extra_memory_gib": bytes_to_gib(float(r["extra_memory_bytes"])),
            "peak_rss_gib": mib_to_gib(float(r["peak_rss_mb"])),
            "rel_l2": float(r["rel_l2"]),
            "max_abs": float(r["max_abs"]),
        }
        for r in backend_rows
        if int(r["threads"]) == 20
    ]
    write_csv(
        SOURCE_DIR / "backend_20_thread_summary.csv",
        backend_20,
        [
            "algorithm",
            "label",
            "threads",
            "assembly_ms",
            "speedup",
            "efficiency",
            "extra_memory_gib",
            "peak_rss_gib",
            "rel_l2",
            "max_abs",
        ],
    )

    symbolic_20 = [
        {
            "strategy_label": r["strategy_label"],
            "numeric_backend": r["numeric_backend"],
            "threads": int(r["threads"]),
            "amortized_total_ms": float(r["amortized_total_ms"]),
            "isolated_peak_rss_gib": mib_to_gib(float(r["isolated_peak_rss_mb"])),
            "csr_gib": bytes_to_gib(float(r["csr_bytes"])),
            "plan_gib": bytes_to_gib(float(r["plan_bytes"])),
            "symbolic_persistent_gib": bytes_to_gib(float(r["symbolic_persistent_bytes"])),
            "symbolic_temporary_gib": bytes_to_gib(float(r["symbolic_temporary_bytes"])),
            "backend_extra_gib": bytes_to_gib(float(r["numeric_backend_extra_bytes"])),
            "direct_transient_gib": bytes_to_gib(float(r["direct_transient_bytes"])),
            "estimated_peak_gib": bytes_to_gib(float(r["estimated_peak_bytes"])),
            "rel_l2": float(r["rel_l2"]),
            "max_abs": float(r["max_abs"]),
        }
        for r in symbolic_rows
        if int(r["threads"]) == 20 and r["strategy_label"] in SYMBOLIC_LABELS
    ]
    write_csv(
        SOURCE_DIR / "symbolic_20_thread_memory_summary.csv",
        symbolic_20,
        [
            "strategy_label",
            "numeric_backend",
            "threads",
            "amortized_total_ms",
            "isolated_peak_rss_gib",
            "csr_gib",
            "plan_gib",
            "symbolic_persistent_gib",
            "symbolic_temporary_gib",
            "backend_extra_gib",
            "direct_transient_gib",
            "estimated_peak_gib",
            "rel_l2",
            "max_abs",
        ],
    )

    return {
        "backend_csv": backend_csv,
        "symbolic_csv": symbolic_csv,
        "validation_export_manifest": validation_export_manifest,
        "calculix_manifest": calculix_manifest,
        "backend_rows": backend_rows,
        "symbolic_rows": symbolic_rows,
        "validation_export": validation_export,
        "calculix_validation": calculix_validation,
        "validation_probe_rows": validation_probe_rows,
        "validation_summary": validation_summary,
        "backend_20": backend_20,
        "symbolic_20": symbolic_20,
    }


def backend_by_method(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["algorithm"], []).append(row)
    for method_rows in grouped.values():
        method_rows.sort(key=lambda r: int(r["threads"]))
    return grouped


def symbolic_by_strategy(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["strategy_label"] in SYMBOLIC_LABELS:
            grouped.setdefault(row["strategy_label"], []).append(row)
    for method_rows in grouped.values():
        method_rows.sort(key=lambda r: int(r["threads"]))
    return grouped


def plot_solver_validation(data: dict[str, object]) -> dict[str, str]:
    summary = data["validation_summary"]
    probes = data["validation_probe_rows"]

    fig = plt.figure(figsize=(7.2, 5.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.08])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    x = np.arange(len(summary))
    case_labels = [row["case_label"] for row in summary]
    rel_vals = np.array([row["max_probe_rel_diff"] for row in summary], dtype=float)
    abs_vals = np.array([row["max_probe_abs_diff"] for row in summary], dtype=float)
    case_colors = [
        PALETTE["atomic"] if "hex8" in row["case"] else PALETTE["parallel"]
        for row in summary
    ]

    ax_a.bar(x, rel_vals, color=case_colors, edgecolor="black", linewidth=0.6)
    ax_a.set_yscale("log")
    ax_a.set_ylabel("Max relative probe difference")
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(case_labels, rotation=25, ha="right")
    ax_a.axhline(1e-6, color=PALETTE["mid"], linestyle="--", linewidth=0.8)
    ax_a.text(0.02, 0.92, "1e-6 reference", transform=ax_a.transAxes, fontsize=6)
    simplify_axes(ax_a, grid=True)
    add_panel_label(ax_a, "a")

    ax_b.bar(x, abs_vals, color=case_colors, edgecolor="black", linewidth=0.6)
    ax_b.set_ylabel("Max absolute probe difference")
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(case_labels, rotation=25, ha="right")
    simplify_axes(ax_b, grid=True)
    add_panel_label(ax_b, "b")

    heat = np.full((len(PROBE_ORDER), len(CASE_ORDER)), np.nan)
    lookup = {(row["probe"], row["case"]): row for row in probes}
    for i, probe in enumerate(PROBE_ORDER):
        for j, case in enumerate(CASE_ORDER):
            heat[i, j] = float(lookup[(probe, case)]["rel_diff"])
    image = ax_c.imshow(np.log10(np.maximum(heat, 1e-16)), cmap="viridis", aspect="auto")
    ax_c.set_xticks(np.arange(len(CASE_ORDER)))
    ax_c.set_xticklabels([CASE_LABELS[c] for c in CASE_ORDER], rotation=25, ha="right")
    ax_c.set_yticks(np.arange(len(PROBE_ORDER)))
    ax_c.set_yticklabels([PROBE_LABELS[p] for p in PROBE_ORDER])
    cbar = fig.colorbar(image, ax=ax_c, fraction=0.046, pad=0.02)
    cbar.set_label("log10(relative difference)", fontsize=6.5)
    cbar.ax.tick_params(labelsize=6)
    add_panel_label(ax_c, "c")

    for case in CASE_ORDER:
        rows = [r for r in probes if r["case"] == case]
        color = PALETTE["atomic"] if "hex8" in case else PALETTE["parallel"]
        marker = "o" if "small" in case else "s"
        ax_d.scatter(
            [r["matlab_uz"] for r in rows],
            [r["calculix_uz"] for r in rows],
            s=26,
            color=color,
            marker=marker,
            edgecolor="black",
            linewidth=0.4,
            alpha=0.88,
            label=CASE_LABELS[case],
        )
    all_z = np.array([r["matlab_uz"] for r in probes] + [r["calculix_uz"] for r in probes])
    lo, hi = float(np.min(all_z)), float(np.max(all_z))
    pad = (hi - lo) * 0.06 if hi > lo else 1.0
    ax_d.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color=PALETTE["mid"], lw=0.8)
    ax_d.set_xlim(lo - pad, hi + pad)
    ax_d.set_ylim(lo - pad, hi + pad)
    ax_d.set_xlabel("MATLAB uz")
    ax_d.set_ylabel("CalculiX uz")
    ax_d.legend(fontsize=5.7, loc="best")
    simplify_axes(ax_d, grid=True)
    add_panel_label(ax_d, "d")

    return save_figure(fig, "fig01_solver_validation_probe_agreement")


def plot_backend_scaling(data: dict[str, object]) -> dict[str, str]:
    rows = data["backend_rows"]
    grouped = backend_by_method(rows)
    methods = ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]

    fig = plt.figure(figsize=(7.2, 5.1), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    for method in methods:
        method_rows = grouped[method]
        threads = np.array([int(r["threads"]) for r in method_rows])
        assembly = np.array([float(r["assembly_ms"]) for r in method_rows])
        speedup = np.array([float(r["speedup"]) for r in method_rows])
        efficiency = np.array([float(r["efficiency"]) for r in method_rows])
        color = BACKEND_COLORS[method]
        ax_a.plot(threads, assembly, marker="o", ms=3.2, lw=1.4, color=color)
        ax_b.plot(threads, speedup, marker="o", ms=3.2, lw=1.4, color=color)
        ax_c.plot(threads, efficiency, marker="o", ms=3.2, lw=1.4, color=color)

    ax_a.set_ylabel("Assembly time (ms)")
    ax_a.set_xlabel("Threads")
    ax_a.set_yscale("log")
    simplify_axes(ax_a, grid=True)
    add_panel_label(ax_a, "a")

    ax_b.set_ylabel("Speedup vs serial baseline")
    ax_b.set_xlabel("Threads")
    ax_b.axline((1, 1), slope=1, color=PALETTE["light"], lw=0.8, linestyle="--")
    simplify_axes(ax_b, grid=True)
    add_panel_label(ax_b, "b")

    ax_c.set_ylabel("Parallel efficiency")
    ax_c.set_xlabel("Threads")
    ax_c.set_ylim(0, 1.08)
    simplify_axes(ax_c, grid=True)
    add_panel_label(ax_c, "c")

    backend_20 = sorted(data["backend_20"], key=lambda r: ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"].index(r["algorithm"]))
    x = np.arange(len(backend_20))
    bars = ax_d.bar(
        x,
        [r["assembly_ms"] for r in backend_20],
        color=[BACKEND_COLORS[r["algorithm"]] for r in backend_20],
        edgecolor="black",
        linewidth=0.6,
    )
    for bar, row in zip(bars, backend_20):
        bar.set_hatch(BACKEND_HATCHES[row["algorithm"]])
        ax_d.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 16,
            f"{row['assembly_ms']:.0f} ms",
            ha="center",
            va="bottom",
            fontsize=6,
        )
    ax_d.set_ylabel("20-thread assembly time (ms)")
    ax_d.set_xticks(x)
    ax_d.set_xticklabels([r["label"] for r in backend_20], rotation=20, ha="right")
    simplify_axes(ax_d, grid=True)
    add_panel_label(ax_d, "d")

    handles = method_legend_handles(methods)
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.54, 1.02), ncol=3, fontsize=7)
    return save_figure(fig, "fig02_backend_time_scaling")


def plot_memory_lifecycle(data: dict[str, object]) -> dict[str, str]:
    symbolic_20 = [
        row
        for row in data["symbolic_20"]
        if row["strategy_label"] in SYMBOLIC_LABELS
        and (
            row["strategy_label"] != "direct_no_symbolic_background"
            or row["numeric_backend"] == "none"
        )
        and (
            row["strategy_label"] == "direct_no_symbolic_background"
            or row["numeric_backend"] == "cpu_atomic"
        )
    ]
    symbolic_20.sort(
        key=lambda r: [
            "serial_symbolic_parallel_numeric",
            "parallel_symbolic_parallel_numeric",
            "direct_no_symbolic_background",
        ].index(r["strategy_label"])
    )
    symbolic_grouped = symbolic_by_strategy(data["symbolic_rows"])
    strategies = [
        "serial_symbolic_parallel_numeric",
        "parallel_symbolic_parallel_numeric",
        "direct_no_symbolic_background",
    ]

    fig = plt.figure(figsize=(7.2, 5.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0])
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])

    x = np.arange(len(symbolic_20))
    bottoms = np.zeros(len(symbolic_20))
    components = [
        ("csr_gib", "CSR persistent", "#B4C0E4", ""),
        ("plan_gib", "AssemblyPlan persistent", "#7884B4", ""),
        ("symbolic_temporary_gib", "Symbolic temporary", "#42949E", "///"),
        ("backend_extra_gib", "Backend extra", "#9A4D8E", "\\\\\\"),
        ("direct_transient_gib", "Direct/no-symbolic transient", "#D28B32", "..."),
    ]
    for key, label, color, hatch in components:
        values = np.array([float(row[key]) for row in symbolic_20])
        bars = ax_a.bar(
            x,
            values,
            bottom=bottoms,
            label=label,
            color=color,
            edgecolor="black",
            linewidth=0.45,
        )
        for bar in bars:
            bar.set_hatch(hatch)
        bottoms += values
    rss = np.array([float(row["isolated_peak_rss_gib"]) for row in symbolic_20])
    ax_a.scatter(x, rss, marker="D", s=34, color=PALETTE["dark"], label="Measured isolated RSS", zorder=5)
    for xi, yi in zip(x, rss):
        ax_a.text(xi, yi + 0.12, f"{yi:.2f}", ha="center", va="bottom", fontsize=6)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels([SYMBOLIC_LABELS[row["strategy_label"]] for row in symbolic_20], rotation=12, ha="right")
    ax_a.set_ylabel("Memory at 20 threads (GiB)")
    ax_a.legend(ncol=3, fontsize=6.2, loc="upper left")
    simplify_axes(ax_a, grid=True)
    add_panel_label(ax_a, "a", x=-0.07)

    for strategy in strategies:
        rows = [
            row
            for row in symbolic_grouped[strategy]
            if (
                strategy == "direct_no_symbolic_background"
                and row["numeric_backend"] == "none"
            )
            or (
                strategy != "direct_no_symbolic_background"
                and row["numeric_backend"] == "cpu_atomic"
            )
        ]
        threads = np.array([int(r["threads"]) for r in rows])
        rss_values = np.array([mib_to_gib(float(r["isolated_peak_rss_mb"])) for r in rows])
        ax_b.plot(
            threads,
            rss_values,
            marker="o",
            ms=3.0,
            lw=1.3,
            color=SYMBOLIC_COLORS[strategy],
            label=SYMBOLIC_LABELS[strategy],
        )
    ax_b.set_xlabel("Threads")
    ax_b.set_ylabel("Measured isolated RSS (GiB)")
    simplify_axes(ax_b, grid=True)
    add_panel_label(ax_b, "b")

    for strategy in strategies:
        rows = [
            row
            for row in symbolic_grouped[strategy]
            if (
                strategy == "direct_no_symbolic_background"
                and row["numeric_backend"] == "none"
            )
            or (
                strategy != "direct_no_symbolic_background"
                and row["numeric_backend"] == "cpu_atomic"
            )
        ]
        threads = np.array([int(r["threads"]) for r in rows])
        estimated = np.array([bytes_to_gib(float(r["estimated_peak_bytes"])) for r in rows])
        ax_c.plot(
            threads,
            estimated,
            marker="o",
            ms=3.0,
            lw=1.3,
            color=SYMBOLIC_COLORS[strategy],
        )
    ax_c.set_xlabel("Threads")
    ax_c.set_ylabel("Estimated peak fields (GiB)")
    simplify_axes(ax_c, grid=True)
    add_panel_label(ax_c, "c")
    fig.legend(loc="upper center", bbox_to_anchor=(0.54, 1.02), ncol=3, fontsize=6.3)
    return save_figure(fig, "fig03_memory_lifecycle")


def plot_symbolic_tradeoff(data: dict[str, object]) -> dict[str, str]:
    grouped = symbolic_by_strategy(data["symbolic_rows"])
    strategies = [
        "serial_symbolic_parallel_numeric",
        "parallel_symbolic_parallel_numeric",
        "direct_no_symbolic_background",
    ]

    fig = plt.figure(figsize=(7.2, 4.3), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.1, 0.95])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    selected_20: list[dict[str, str]] = []
    for strategy in strategies:
        rows = [
            r
            for r in grouped[strategy]
            if (
                strategy == "direct_no_symbolic_background"
                and r["numeric_backend"] == "none"
            )
            or (
                strategy != "direct_no_symbolic_background"
                and r["numeric_backend"] == "cpu_atomic"
            )
        ]
        threads = np.array([int(r["threads"]) for r in rows])
        total = np.array([float(r["amortized_total_ms"]) for r in rows])
        numeric = np.array([float(r["numeric_ms"]) for r in rows])
        color = SYMBOLIC_COLORS[strategy]
        ax_a.plot(threads, total, marker="o", ms=3.1, lw=1.4, color=color, label=SYMBOLIC_LABELS[strategy])
        ax_b.plot(threads, numeric, marker="o", ms=3.1, lw=1.4, color=color)
        selected_20.extend([r for r in rows if int(r["threads"]) == 20])

    ax_a.set_xlabel("Threads")
    ax_a.set_ylabel("Total time per assembly (ms)")
    ax_a.set_yscale("log")
    simplify_axes(ax_a, grid=True)
    add_panel_label(ax_a, "a")

    ax_b.set_xlabel("Threads")
    ax_b.set_ylabel("Numeric assembly time (ms)")
    ax_b.set_yscale("log")
    simplify_axes(ax_b, grid=True)
    add_panel_label(ax_b, "b")

    selected_20.sort(key=lambda r: strategies.index(r["strategy_label"]))
    x = np.arange(len(selected_20))
    total_20 = np.array([float(r["amortized_total_ms"]) for r in selected_20])
    bars = ax_c.bar(
        x,
        total_20,
        color=[SYMBOLIC_COLORS[r["strategy_label"]] for r in selected_20],
        edgecolor="black",
        linewidth=0.6,
    )
    for bar, row in zip(bars, selected_20):
        ax_c.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 90,
            f"{float(row['amortized_total_ms']):.0f}",
            ha="center",
            va="bottom",
            fontsize=6,
        )
    ax_c.set_xticks(x)
    ax_c.set_xticklabels([SYMBOLIC_LABELS[r["strategy_label"]] for r in selected_20], rotation=25, ha="right")
    ax_c.set_ylabel("20-thread total time (ms)")
    simplify_axes(ax_c, grid=True)
    add_panel_label(ax_c, "c")

    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.04), ncol=3, fontsize=6.2)
    return save_figure(fig, "fig04_symbolic_mode_tradeoff")


def plot_accuracy_guardrails(data: dict[str, object]) -> dict[str, str]:
    backend_grouped = backend_by_method(data["backend_rows"])
    symbolic_grouped = symbolic_by_strategy(data["symbolic_rows"])
    methods = ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]
    strategies = [
        "serial_symbolic_parallel_numeric",
        "parallel_symbolic_parallel_numeric",
        "direct_no_symbolic_background",
    ]

    fig = plt.figure(figsize=(7.2, 4.3), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.05, 0.9])
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    for method in methods:
        rows = backend_grouped[method]
        threads = np.array([int(r["threads"]) for r in rows])
        rel = np.maximum(np.array([float(r["rel_l2"]) for r in rows]), 1e-18)
        ax_a.plot(threads, rel, marker="o", ms=3, lw=1.3, color=BACKEND_COLORS[method], label=BACKEND_LABELS[method])
    ax_a.axhspan(1e-18, 1e-12, color="#EEF2F7", zorder=0)
    ax_a.set_xlabel("Threads")
    ax_a.set_ylabel("Backend rel_l2 vs reference")
    ax_a.set_yscale("log")
    ax_a.set_ylim(1e-18, 1e-10)
    simplify_axes(ax_a, grid=True)
    add_panel_label(ax_a, "a")

    for strategy in strategies:
        rows = [
            r
            for r in symbolic_grouped[strategy]
            if (
                strategy == "direct_no_symbolic_background"
                and r["numeric_backend"] == "none"
            )
            or (
                strategy != "direct_no_symbolic_background"
                and r["numeric_backend"] == "cpu_atomic"
            )
        ]
        threads = np.array([int(r["threads"]) for r in rows])
        rel = np.maximum(np.array([float(r["rel_l2"]) for r in rows]), 1e-18)
        ax_b.plot(threads, rel, marker="o", ms=3, lw=1.3, color=SYMBOLIC_COLORS[strategy], label=SYMBOLIC_LABELS[strategy])
    ax_b.axhspan(1e-18, 1e-12, color="#EEF2F7", zorder=0)
    ax_b.set_xlabel("Threads")
    ax_b.set_ylabel("Symbolic rel_l2 vs reference")
    ax_b.set_yscale("log")
    ax_b.set_ylim(1e-18, 1e-10)
    simplify_axes(ax_b, grid=True)
    add_panel_label(ax_b, "b")

    max_rows = [
        ("Backend", max(float(r["rel_l2"]) for r in data["backend_rows"])),
        ("Symbolic/RSS", max(float(r["rel_l2"]) for r in data["symbolic_rows"])),
        (
            "CalculiX probe",
            max(float(r["rel_diff"]) for r in data["validation_probe_rows"]),
        ),
    ]
    x = np.arange(len(max_rows))
    colors = [PALETTE["atomic"], PALETTE["parallel"], PALETTE["direct"]]
    ax_c.bar(x, [max(v, 1e-18) for _, v in max_rows], color=colors, edgecolor="black", linewidth=0.6)
    ax_c.set_yscale("log")
    ax_c.set_ylabel("Worst reported relative difference")
    ax_c.set_xticks(x)
    ax_c.set_xticklabels([label for label, _ in max_rows], rotation=25, ha="right")
    for xi, (_, value) in zip(x, max_rows):
        ax_c.text(xi, max(value, 1e-18) * 1.55, f"{value:.2e}", ha="center", va="bottom", fontsize=5.8)
    simplify_axes(ax_c, grid=True)
    add_panel_label(ax_c, "c")

    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.05), ncol=3, fontsize=5.8)
    return save_figure(fig, "fig05_accuracy_guardrails")


def plot_overview_composite(data: dict[str, object]) -> dict[str, str]:
    summary = data["validation_summary"]
    backend_grouped = backend_by_method(data["backend_rows"])
    symbolic_grouped = symbolic_by_strategy(data["symbolic_rows"])
    backend_20 = sorted(
        data["backend_20"],
        key=lambda r: ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"].index(r["algorithm"]),
    )

    symbolic_20 = [
        row
        for row in data["symbolic_20"]
        if row["strategy_label"] in SYMBOLIC_LABELS
        and (
            row["strategy_label"] == "direct_no_symbolic_background"
            and row["numeric_backend"] == "none"
            or row["strategy_label"] != "direct_no_symbolic_background"
            and row["numeric_backend"] == "cpu_atomic"
        )
    ]
    symbolic_20.sort(
        key=lambda r: [
            "serial_symbolic_parallel_numeric",
            "parallel_symbolic_parallel_numeric",
            "direct_no_symbolic_background",
        ].index(r["strategy_label"])
    )

    fig = plt.figure(figsize=(7.3, 6.5), constrained_layout=True)
    gs = fig.add_gridspec(3, 4, height_ratios=[0.9, 1.05, 1.05], width_ratios=[1.0, 1.0, 1.0, 0.92])
    ax_a = fig.add_subplot(gs[0, 0:2])
    ax_b = fig.add_subplot(gs[0, 2:4])
    ax_c = fig.add_subplot(gs[1, 0:2])
    ax_d = fig.add_subplot(gs[1, 2:4])
    ax_e = fig.add_subplot(gs[2, 0:2])
    ax_f = fig.add_subplot(gs[2, 2:4])

    # a: solver validation maximum relative difference.
    x = np.arange(len(summary))
    colors = [PALETTE["atomic"] if "hex8" in r["case"] else PALETTE["parallel"] for r in summary]
    ax_a.bar(x, [r["max_probe_rel_diff"] for r in summary], color=colors, edgecolor="black", linewidth=0.5)
    ax_a.set_yscale("log")
    ax_a.set_ylabel("Max probe rel. diff.")
    ax_a.set_xticks(x)
    ax_a.set_xticklabels([r["case_label"] for r in summary], rotation=20, ha="right")
    simplify_axes(ax_a, grid=True)
    add_panel_label(ax_a, "a")

    # b: backend 20-thread ranking.
    x = np.arange(len(backend_20))
    bars = ax_b.bar(
        x,
        [r["assembly_ms"] for r in backend_20],
        color=[BACKEND_COLORS[r["algorithm"]] for r in backend_20],
        edgecolor="black",
        linewidth=0.5,
    )
    for bar, row in zip(bars, backend_20):
        bar.set_hatch(BACKEND_HATCHES[row["algorithm"]])
        ax_b.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 18, f"{row['assembly_ms']:.0f}", ha="center", va="bottom", fontsize=6)
    ax_b.set_ylabel("20-thread assembly (ms)")
    ax_b.set_xticks(x)
    ax_b.set_xticklabels([r["label"] for r in backend_20], rotation=20, ha="right")
    simplify_axes(ax_b, grid=True)
    add_panel_label(ax_b, "b")

    # c: assembly scaling.
    for method in ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]:
        rows = backend_grouped[method]
        ax_c.plot(
            [int(r["threads"]) for r in rows],
            [float(r["assembly_ms"]) for r in rows],
            marker="o",
            ms=2.8,
            lw=1.25,
            color=BACKEND_COLORS[method],
            label=BACKEND_LABELS[method],
        )
    ax_c.set_yscale("log")
    ax_c.set_xlabel("Threads")
    ax_c.set_ylabel("Assembly time (ms)")
    simplify_axes(ax_c, grid=True)
    add_panel_label(ax_c, "c")

    # d: symbolic mode total time.
    for strategy in [
        "serial_symbolic_parallel_numeric",
        "parallel_symbolic_parallel_numeric",
        "direct_no_symbolic_background",
    ]:
        rows = [
            r
            for r in symbolic_grouped[strategy]
            if (
                strategy == "direct_no_symbolic_background"
                and r["numeric_backend"] == "none"
            )
            or (
                strategy != "direct_no_symbolic_background"
                and r["numeric_backend"] == "cpu_atomic"
            )
        ]
        ax_d.plot(
            [int(r["threads"]) for r in rows],
            [float(r["amortized_total_ms"]) for r in rows],
            marker="o",
            ms=2.8,
            lw=1.25,
            color=SYMBOLIC_COLORS[strategy],
            label=SYMBOLIC_LABELS[strategy],
        )
    ax_d.set_yscale("log")
    ax_d.set_xlabel("Threads")
    ax_d.set_ylabel("Total time (ms)")
    simplify_axes(ax_d, grid=True)
    add_panel_label(ax_d, "d")

    # e: memory lifecycle.
    x = np.arange(len(symbolic_20))
    bottoms = np.zeros(len(symbolic_20))
    components = [
        ("csr_gib", "CSR persistent", "#B4C0E4"),
        ("plan_gib", "AssemblyPlan persistent", "#7884B4"),
        ("symbolic_temporary_gib", "Symbolic temporary", "#42949E"),
        ("backend_extra_gib", "Backend extra", "#9A4D8E"),
        ("direct_transient_gib", "Direct transient", "#D28B32"),
    ]
    for key, label, color in components:
        values = np.array([float(row[key]) for row in symbolic_20])
        ax_e.bar(x, values, bottom=bottoms, color=color, edgecolor="black", linewidth=0.35, label=label)
        bottoms += values
    ax_e.scatter(x, [r["isolated_peak_rss_gib"] for r in symbolic_20], marker="D", s=24, color=PALETTE["dark"], label="Measured RSS", zorder=4)
    ax_e.set_ylabel("20-thread memory (GiB)")
    ax_e.set_xticks(x)
    ax_e.set_xticklabels([SYMBOLIC_LABELS[r["strategy_label"]] for r in symbolic_20], rotation=18, ha="right")
    simplify_axes(ax_e, grid=True)
    add_panel_label(ax_e, "e")

    # f: one-axis summary of relative correctness.
    max_rows = [
        ("Backend", max(float(r["rel_l2"]) for r in data["backend_rows"])),
        ("Symbolic/RSS", max(float(r["rel_l2"]) for r in data["symbolic_rows"])),
        ("CalculiX probe", max(float(r["rel_diff"]) for r in data["validation_probe_rows"])),
    ]
    x = np.arange(len(max_rows))
    ax_f.bar(x, [max(v, 1e-18) for _, v in max_rows], color=[PALETTE["atomic"], PALETTE["parallel"], PALETTE["direct"]], edgecolor="black", linewidth=0.5)
    ax_f.set_yscale("log")
    ax_f.set_ylabel("Worst relative difference")
    ax_f.set_xticks(x)
    ax_f.set_xticklabels([label for label, _ in max_rows], rotation=20, ha="right")
    for xi, (_, value) in zip(x, max_rows):
        ax_f.text(xi, max(value, 1e-18) * 1.55, f"{value:.1e}", ha="center", va="bottom", fontsize=5.8)
    simplify_axes(ax_f, grid=True)
    add_panel_label(ax_f, "f")

    handles = [
        Line2D([0], [0], color=BACKEND_COLORS[m], lw=1.5, marker="o", ms=3, label=BACKEND_LABELS[m])
        for m in ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]
    ] + [
        Line2D([0], [0], color=SYMBOLIC_COLORS[s], lw=1.5, marker="o", ms=3, label=SYMBOLIC_LABELS[s])
        for s in [
            "serial_symbolic_parallel_numeric",
            "parallel_symbolic_parallel_numeric",
            "direct_no_symbolic_background",
        ]
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.03), ncol=3, fontsize=5.8)
    return save_figure(fig, "fig00_overview_composite")


def write_explanations(data: dict[str, object], figures: dict[str, dict[str, str]]) -> None:
    validation_summary = data["validation_summary"]
    backend_20 = sorted(
        data["backend_20"],
        key=lambda r: ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"].index(r["algorithm"]),
    )
    symbolic_20 = [
        row
        for row in data["symbolic_20"]
        if row["strategy_label"] in SYMBOLIC_LABELS
        and (
            row["strategy_label"] == "direct_no_symbolic_background"
            and row["numeric_backend"] == "none"
            or row["strategy_label"] != "direct_no_symbolic_background"
            and row["numeric_backend"] == "cpu_atomic"
        )
    ]
    symbolic_20.sort(
        key=lambda r: [
            "serial_symbolic_parallel_numeric",
            "parallel_symbolic_parallel_numeric",
            "direct_no_symbolic_background",
        ].index(r["strategy_label"])
    )

    max_probe_rel = max(float(row["max_probe_rel_diff"]) for row in validation_summary)
    max_probe_abs = max(float(row["max_probe_abs_diff"]) for row in validation_summary)
    atomic_20 = next(row for row in backend_20 if row["algorithm"] == "cpu_atomic")
    private_20 = next(row for row in backend_20 if row["algorithm"] == "cpu_private_csr")
    lock_20 = next(row for row in backend_20 if row["algorithm"] == "cpu_lock_guard")
    parallel_sym_20 = next(row for row in symbolic_20 if row["strategy_label"] == "parallel_symbolic_parallel_numeric")
    serial_sym_20 = next(row for row in symbolic_20 if row["strategy_label"] == "serial_symbolic_parallel_numeric")
    direct_20 = next(row for row in symbolic_20 if row["strategy_label"] == "direct_no_symbolic_background")

    files_block = "\n".join(
        f"- `{name}`: "
        + ", ".join(f"`{ext}` `{path}`" for ext, path in sorted(outputs.items()))
        for name, outputs in figures.items()
    )

    md = f"""# Linux Intel CalculiX Validation and CPU Assembly Figure Package

## Figure Contract

- Core conclusion: Linux Intel full-host results support a solver-correct, CPU-atomic-first assembly path: MATLAB and CalculiX probe displacements agree within {max_probe_rel:.3e} relative difference, `cpu_atomic` gives the best 20-thread assembly time, and `parallel_symbolic_reuse` reduces total time with an explicit RSS cost.
- Figure archetype: quantitative grid with one overview composite plus focused evidence figures.
- Target journal/output: Nature-style double-column computational methods figures; primary SVG with editable text, PDF and 600 dpi TIFF for submission-style export, PNG for quick preview.
- Backend: Python only (`csv/json` + `numpy/matplotlib`; no R and no pandas dependency).
- Final size: overview 7.3 x 6.5 in; focused figures 7.2 in wide.
- Panel map: solver agreement, backend scaling, symbolic-mode tradeoff, memory lifecycle, and accuracy guardrails.
- Evidence hierarchy: correctness is shown first; performance ranking and scaling are the main Intel CPU evidence; memory fields and isolated RSS are separated as validation/control evidence.
- Statistics needed: deterministic benchmark/probe summaries only; no inferential statistics because the source benchmark sweep used `repeat=1`.
- Source data needed: validation manifests and probe CSVs, backend tradeoff CSV, isolated symbolic memory CSV.
- Image-integrity notes: all panels are generated line art from numeric CSV/JSON; no image manipulation or raster-only annotations.
- Reviewer risk: benchmark timings are single-run measurements, so the figures should be read as host evidence rather than population-level timing statistics.

## Why These Charts

1. **Overview composite**: gives a single manuscript-ready page linking solver correctness to the Intel performance and memory story, so the reader does not have to reconcile separate reports.
2. **Solver validation probe agreement**: validates the required `validation_export -> MATLAB solve -> CalculiX displacement CSV -> comparison report` chain before any performance claim is interpreted.
3. **Backend time scaling**: shows why Intel CPU assembly should be led by `cpu_atomic`, and makes the weaker scaling of `private_csr` and `lock_guard` visible instead of only reporting a 20-thread endpoint.
4. **Memory lifecycle**: separates CSR/AssemblyPlan persistent memory, symbolic temporary memory, direct/no-symbolic transient memory, backend extra memory, and measured isolated RSS, matching the required evidence vocabulary.
5. **Symbolic mode tradeoff**: compares total time and numeric time for symbolic reuse and direct no-symbolic paths, which explains why parallel symbolic reuse is useful but not free.
6. **Accuracy guardrails**: confirms the performance and memory comparisons did not trade away matrix-level numerical agreement, and places solver-level probe differences beside assembly-level `rel_l2`.

## Shared Parameters and Source Data

- Solver validation source: `{rel(data['validation_export_manifest'])}`, `{rel(data['calculix_manifest'])}`, and each case-level `*_calculix_probe_compare.csv`.
- Solver validation parameters: `L=1`, `W=0.2`, `T=0.1`, `E=1`, `nu=0.3`, `x=0` fixed, total `z` load `-1` on `x=L`.
- Solver versions: MATLAB `{data['validation_export'].get('matlab', {}).get('version', 'recorded in manifest')}`; CalculiX `{data['calculix_validation']['calculix_version']}`.
- Performance source: `{rel(data['backend_csv'])}`.
- Memory source: `{rel(data['symbolic_csv'])}`.
- Performance parameters: mesh `3d-WindTurbineHub`, `Tet4`, `228384` nodes, `1113684` elements, `685152` DOFs, `27502200` nonzeros, `kernel=linear_elastic_solid`, 1..20 threads on Intel Core Ultra 7 265KF.
- Derived source-data summaries written by this script: `{rel(SOURCE_DIR / 'validation_probe_rows.csv')}`, `{rel(SOURCE_DIR / 'validation_probe_summary.csv')}`, `{rel(SOURCE_DIR / 'backend_20_thread_summary.csv')}`, `{rel(SOURCE_DIR / 'symbolic_20_thread_memory_summary.csv')}`.

## Figure Files

{files_block}

## Figure 00: Overview Composite

- Files: {", ".join(f"`{path}`" for path in figures['fig00_overview_composite'].values())}
- Data source: validation probe summaries, backend timing CSV, isolated symbolic memory CSV.
- Parameters: all panels use `linear_elastic_solid`; performance panels use the 3d-WindTurbineHub Tet4 mesh and 1..20 Intel physical-core sweep.
- Conclusion: the full evidence chain is internally consistent: the worst CalculiX-vs-MATLAB probe relative difference is {max_probe_rel:.3e}, the 20-thread `cpu_atomic` assembly time is {atomic_20['assembly_ms']:.1f} ms, and `parallel_symbolic_reuse` reaches {parallel_sym_20['amortized_total_ms']:.1f} ms total time with {parallel_sym_20['isolated_peak_rss_gib']:.2f} GiB measured RSS.
- Interpretation: the validation panel establishes that the exported `K/F/BC` solve agrees with an external open solver at selected physical probes; the backend panels show that atomic updates are faster than private CSR or lock guarding on this host; the memory panel prevents conflating estimated component bytes with measured isolated RSS.

## Figure 01: Solver Validation Probe Agreement

- Files: {", ".join(f"`{path}`" for path in figures['fig01_solver_validation_probe_agreement'].values())}
- Data source: `{rel(data['calculix_manifest'])}` plus four case-level `*_calculix_probe_compare.csv` files.
- Parameters: four cases are `cantilever_hex8_small`, `cantilever_hex8_medium`, `cantilever_tet4_small`, and `cantilever_tet4_medium`; fixed/load/material settings are the shared validation parameters above.
- Conclusion: all four validation cases report sub-micro relative probe differences, with worst relative difference {max_probe_rel:.3e} and worst absolute difference {max_probe_abs:.6g}.
- Interpretation: the largest absolute difference occurs on the larger meshes because displacements are larger in magnitude, while the relative differences remain close across Hex8/Tet4 and small/medium cases. This supports using CalculiX as the Linux open-source solver probe without fabricating commercial-solver evidence.

## Figure 02: Backend Time Scaling

- Files: {", ".join(f"`{path}`" for path in figures['fig02_backend_time_scaling'].values())}
- Data source: `{rel(data['backend_csv'])}`.
- Parameters: algorithms `cpu_atomic`, `cpu_private_csr`, and `cpu_lock_guard`; thread range 1..20; `repeat=1`; `kernel=linear_elastic_solid`.
- Conclusion: at 20 threads, `cpu_atomic` is fastest ({atomic_20['assembly_ms']:.1f} ms), ahead of `cpu_private_csr` ({private_20['assembly_ms']:.1f} ms) and `cpu_lock_guard` ({lock_20['assembly_ms']:.1f} ms).
- Interpretation: `private_csr` starts with a strong 1-thread baseline but its per-thread private storage and merge overhead dominate at high thread counts; `lock_guard` avoids atomics but lock contention keeps it slower; `cpu_atomic` gives the best observed speed/memory tradeoff on this Intel host.

## Figure 03: Memory Lifecycle

- Files: {", ".join(f"`{path}`" for path in figures['fig03_memory_lifecycle'].values())}
- Data source: `{rel(data['symbolic_csv'])}` and derived `{rel(SOURCE_DIR / 'symbolic_20_thread_memory_summary.csv')}`.
- Parameters: selected 20-thread comparison uses serial symbolic + atomic numeric, parallel symbolic reuse + atomic numeric, and direct no-symbolic mode.
- Conclusion: 20-thread measured isolated RSS is {serial_sym_20['isolated_peak_rss_gib']:.2f} GiB for serial symbolic + parallel numeric, {parallel_sym_20['isolated_peak_rss_gib']:.2f} GiB for parallel symbolic reuse, and {direct_20['isolated_peak_rss_gib']:.2f} GiB for direct no-symbolic.
- Interpretation: CSR and AssemblyPlan are persistent symbolic assets; parallel symbolic adds a smaller symbolic temporary allocation; direct no-symbolic avoids symbolic persistence but pays a large transient memory component. The isolated RSS markers are kept separate because allocator/runtime overhead makes measured resident memory different from simple byte-field sums.

## Figure 04: Symbolic Mode Tradeoff

- Files: {", ".join(f"`{path}`" for path in figures['fig04_symbolic_mode_tradeoff'].values())}
- Data source: `{rel(data['symbolic_csv'])}`.
- Parameters: modes `serial_symbolic_parallel_numeric`, `parallel_symbolic_parallel_numeric`, and `direct_no_symbolic_background`; atomic backend for symbolic reuse rows; no backend for direct no-symbolic rows.
- Conclusion: at 20 threads, parallel symbolic reuse ({parallel_sym_20['amortized_total_ms']:.1f} ms) is much faster than serial symbolic + parallel numeric ({serial_sym_20['amortized_total_ms']:.1f} ms) and direct no-symbolic ({direct_20['amortized_total_ms']:.1f} ms).
- Interpretation: the speedup comes from parallelizing the symbolic construction/reuse path while preserving the sparse output structure; direct no-symbolic remains competitive only relative to serial symbolic at low thread counts, but its transient memory and total time are worse at the 20-thread endpoint.

## Figure 05: Accuracy Guardrails

- Files: {", ".join(f"`{path}`" for path in figures['fig05_accuracy_guardrails'].values())}
- Data source: `{rel(data['backend_csv'])}`, `{rel(data['symbolic_csv'])}`, and validation probe CSVs.
- Parameters: backend and symbolic panels use the same `linear_elastic_solid` WindHub benchmark; validation bar uses the four CalculiX probe cases.
- Conclusion: backend and symbolic matrix-level `rel_l2` stay around floating-point noise, with maxima {max(float(r['rel_l2']) for r in data['backend_rows']):.3e} and {max(float(r['rel_l2']) for r in data['symbolic_rows']):.3e}; solver probe relative differences are larger but still below {max_probe_rel:.3e}.
- Interpretation: the assembly implementation variants produce numerically equivalent matrices relative to their references, while the solver probe comparison includes independent solver I/O and displacement extraction effects. Keeping both scales visible prevents overclaiming bitwise equality at the solver level.
"""
    (RESULT_ROOT / "figure_explanations.md").write_text(md, encoding="utf-8")


def write_manifest(data: dict[str, object], figures: dict[str, dict[str, str]]) -> None:
    manifest = {
        "schema_version": "pgsa-nature-figure-package-v1",
        "created_by": "generate_nature_figures.py",
        "backend": "python-matplotlib",
        "python_only": True,
        "figure_contract": {
            "core_conclusion": "Linux Intel full-host results support a solver-correct, CPU-atomic-first assembly path with explicit symbolic-memory tradeoffs.",
            "archetype": "quantitative_grid_with_overview_composite",
            "target_output": ["svg", "pdf", "tiff", "png"],
            "statistics": "deterministic single-run benchmark summaries; no inferential statistics",
        },
        "source_files": {
            "backend_csv": rel(data["backend_csv"]),
            "symbolic_csv": rel(data["symbolic_csv"]),
            "validation_export_manifest": rel(data["validation_export_manifest"]),
            "calculix_manifest": rel(data["calculix_manifest"]),
            "derived_source_data": [
                rel(SOURCE_DIR / "validation_probe_rows.csv"),
                rel(SOURCE_DIR / "validation_probe_summary.csv"),
                rel(SOURCE_DIR / "backend_20_thread_summary.csv"),
                rel(SOURCE_DIR / "symbolic_20_thread_memory_summary.csv"),
            ],
        },
        "figures": figures,
        "key_numbers": {
            "validation_max_probe_rel_diff": max(float(r["max_probe_rel_diff"]) for r in data["validation_summary"]),
            "validation_max_probe_abs_diff": max(float(r["max_probe_abs_diff"]) for r in data["validation_summary"]),
            "backend_max_rel_l2": max(float(r["rel_l2"]) for r in data["backend_rows"]),
            "symbolic_max_rel_l2": max(float(r["rel_l2"]) for r in data["symbolic_rows"]),
        },
    }
    (RESULT_ROOT / "figure_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    data = load_data()
    figures = {
        "fig00_overview_composite": plot_overview_composite(data),
        "fig01_solver_validation_probe_agreement": plot_solver_validation(data),
        "fig02_backend_time_scaling": plot_backend_scaling(data),
        "fig03_memory_lifecycle": plot_memory_lifecycle(data),
        "fig04_symbolic_mode_tradeoff": plot_symbolic_tradeoff(data),
        "fig05_accuracy_guardrails": plot_accuracy_guardrails(data),
    }
    write_explanations(data, figures)
    write_manifest(data, figures)
    print(json.dumps({"result_root": rel(RESULT_ROOT), "figures": figures}, indent=2))


if __name__ == "__main__":
    main()
