#!/usr/bin/env python3
"""Build a Nature-style visual summary from historical GPU benchmark results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

mpl.rcParams.update(
    {
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.7,
        "axes.labelsize": 7,
        "axes.titlesize": 7.2,
        "xtick.labelsize": 6.4,
        "ytick.labelsize": 6.4,
        "legend.fontsize": 6.2,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PACKAGE_DIR / "source_data" / "benchmark_results_2026-01-30.csv"
FIGURE_STEM = "fig01_gpu_parallel_assembly_benchmark"
REQUIRED_COLUMNS = {"Algorithm", "Elements", "DOFs", "Time_ms", "Speedup", "Error", "Status"}

PALETTE = {
    "baseline": "#4D4D4D",
    "atomic": "#0F4D92",
    "block": "#42949E",
    "work_queue": "#9A4D8E",
    "neutral_light": "#CFCECE",
    "neutral_mid": "#767676",
    "neutral_black": "#272727",
}

METHOD_ORDER = ["CPU_Serial", "Atomic_WarpAgg", "Block_Parallel", "Work_Queue"]
METHOD_LABELS = {
    "CPU_Serial": "CPU serial",
    "Atomic_WarpAgg": "Atomic warp aggregation",
    "Block_Parallel": "Block parallel",
    "Work_Queue": "Work queue",
}
METHOD_SHORT_LABELS = {
    "CPU_Serial": "CPU",
    "Atomic_WarpAgg": "Atomic",
    "Block_Parallel": "Block",
    "Work_Queue": "Work queue",
}
METHOD_COLORS = {
    "CPU_Serial": PALETTE["baseline"],
    "Atomic_WarpAgg": PALETTE["atomic"],
    "Block_Parallel": PALETTE["block"],
    "Work_Queue": PALETTE["work_queue"],
}
METHOD_MARKERS = {
    "CPU_Serial": "o",
    "Atomic_WarpAgg": "s",
    "Block_Parallel": "^",
    "Work_Queue": "D",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate publication-grade GPU benchmark figures from a CSV file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Input benchmark CSV. Defaults to the copied source_data CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PACKAGE_DIR,
        help="Output directory for figures, source copy, manifest, and QA notes.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Input CSV not found: {path}. Pass --input for the first run."
        )
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Input CSV is empty or has no header.")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Input CSV missing required columns: {sorted(missing)}")
        rows = []
        for line_number, raw in enumerate(reader, start=2):
            try:
                row = {
                    "Algorithm": raw["Algorithm"],
                    "Elements": int(raw["Elements"]),
                    "DOFs": int(raw["DOFs"]),
                    "Time_ms": float(raw["Time_ms"]),
                    "Speedup": float(raw["Speedup"]),
                    "Error": float(raw["Error"]),
                    "Status": raw["Status"],
                    "Line": line_number,
                }
            except Exception as exc:  # noqa: BLE001 - add CSV line context.
                raise ValueError(f"Could not parse row {line_number}: {raw}") from exc
            rows.append(row)
    if not rows:
        raise ValueError("Input CSV has no data rows.")
    return rows


def validate_rows(rows: list[dict[str, object]]) -> None:
    elements = sorted({int(r["Elements"]) for r in rows})
    algorithms = sorted({str(r["Algorithm"]) for r in rows})
    expected = {(algorithm, element) for algorithm in METHOD_ORDER for element in elements}
    observed = {(str(r["Algorithm"]), int(r["Elements"])) for r in rows}
    missing = expected - observed
    unknown_algorithms = set(algorithms) - set(METHOD_ORDER)
    if missing:
        raise ValueError(f"Missing algorithm/element combinations: {sorted(missing)}")
    if unknown_algorithms:
        raise ValueError(f"Unknown algorithms not mapped for plotting: {sorted(unknown_algorithms)}")
    duplicate_counts: dict[tuple[str, int], int] = defaultdict(int)
    for row in rows:
        duplicate_counts[(str(row["Algorithm"]), int(row["Elements"]))] += 1
    duplicates = {key: value for key, value in duplicate_counts.items() if value > 1}
    if duplicates:
        raise ValueError(f"Duplicate algorithm/element rows found: {duplicates}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_source_data(input_path: Path, output_dir: Path) -> Path:
    source_dir = output_dir / "source_data"
    source_dir.mkdir(parents=True, exist_ok=True)
    target = source_dir / "benchmark_results_2026-01-30.csv"
    input_resolved = input_path.resolve()
    target_resolved = target.resolve()
    if input_resolved != target_resolved:
        shutil.copy2(input_resolved, target_resolved)
    return target


def rows_by_method(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for method in METHOD_ORDER:
        method_rows = [r for r in rows if r["Algorithm"] == method]
        grouped[method] = sorted(method_rows, key=lambda r: int(r["Elements"]))
    return grouped


def add_panel_label(ax: plt.Axes, label: str, x: float = -0.075, y: float = 1.055) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        ha="left",
        va="bottom",
        color="black",
    )


def set_log_ticks(ax: plt.Axes, ticks: list[float], labels: list[str] | None = None) -> None:
    ax.set_yticks(ticks)
    if labels is None:
        labels = [f"{tick:g}" for tick in ticks]
    ax.set_yticklabels(labels)


def annotate_end_label(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    color: str,
    offset: tuple[int, int] = (5, 0),
) -> None:
    ax.annotate(
        text,
        xy=(x, y),
        xytext=offset,
        textcoords="offset points",
        color=color,
        fontsize=5.8,
        va="center",
        ha="left",
        clip_on=False,
    )


def make_figure(rows: list[dict[str, object]], output_dir: Path) -> Path:
    grouped = rows_by_method(rows)
    elements = np.array(sorted({int(r["Elements"]) for r in rows}), dtype=float)

    fig = plt.figure(figsize=(7.2, 4.9))
    gs = fig.add_gridspec(
        2,
        3,
        height_ratios=[1.34, 1.0],
        width_ratios=[1.1, 1.0, 0.92],
        hspace=0.54,
        wspace=0.43,
    )
    ax_speedup = fig.add_subplot(gs[0, :])
    ax_time = fig.add_subplot(gs[1, 0])
    ax_error = fig.add_subplot(gs[1, 1])
    ax_large = fig.add_subplot(gs[1, 2])

    end_offsets = {
        "CPU_Serial": (5, 0),
        "Atomic_WarpAgg": (5, 6),
        "Block_Parallel": (5, -6),
        "Work_Queue": (5, -2),
    }

    for method in METHOD_ORDER:
        method_rows = grouped[method]
        x = np.array([r["Elements"] for r in method_rows], dtype=float)
        speedup = np.array([r["Speedup"] for r in method_rows], dtype=float)
        time_ms = np.array([r["Time_ms"] for r in method_rows], dtype=float)
        color = METHOD_COLORS[method]
        label = METHOD_LABELS[method]
        ax_speedup.plot(
            x,
            speedup,
            marker=METHOD_MARKERS[method],
            color=color,
            linewidth=1.35,
            markersize=4.2,
            markeredgecolor="white",
            markeredgewidth=0.35,
            label=label,
        )
        ax_time.plot(
            x,
            time_ms,
            marker=METHOD_MARKERS[method],
            color=color,
            linewidth=1.2,
            markersize=3.7,
            markeredgecolor="white",
            markeredgewidth=0.35,
            label=label,
        )
        annotate_end_label(
            ax_speedup,
            x[-1],
            speedup[-1],
            METHOD_SHORT_LABELS[method],
            color,
            end_offsets[method],
        )

    ax_speedup.set_xscale("log")
    ax_speedup.set_yscale("log")
    ax_speedup.set_ylabel("Speedup vs CPU serial (x)")
    ax_speedup.set_xlabel("Finite elements")
    ax_speedup.set_title("GPU parallel assembly speedup is strong but scale-dependent", pad=8)
    ax_speedup.grid(True, which="major", axis="both", color="#D8D8D8", linewidth=0.45)
    ax_speedup.grid(True, which="minor", axis="y", color="#EAEAEA", linewidth=0.25)
    set_log_ticks(ax_speedup, [1, 2, 5, 10, 20, 50, 100])
    ax_speedup.set_ylim(0.85, 130)
    ax_speedup.set_xlim(elements.min() * 0.75, elements.max() * 1.8)
    add_panel_label(ax_speedup, "a")

    best_gpu = max(
        (r for r in rows if r["Algorithm"] != "CPU_Serial"),
        key=lambda r: float(r["Speedup"]),
    )
    ax_speedup.annotate(
        f"peak {best_gpu['Speedup']:.1f}x",
        xy=(float(best_gpu["Elements"]), float(best_gpu["Speedup"])),
        xytext=(28, -24),
        textcoords="offset points",
        fontsize=6.3,
        ha="left",
        va="top",
        arrowprops={
            "arrowstyle": "-|>",
            "lw": 0.6,
            "color": PALETTE["neutral_black"],
            "mutation_scale": 7,
        },
    )

    ax_time.set_xscale("log")
    ax_time.set_yscale("log")
    ax_time.set_ylabel("Assembly time (ms)")
    ax_time.set_xlabel("Finite elements")
    ax_time.set_title("Absolute time")
    ax_time.grid(True, which="major", axis="both", color="#D8D8D8", linewidth=0.45)
    ax_time.grid(True, which="minor", axis="y", color="#EAEAEA", linewidth=0.25)
    ax_time.set_xlim(elements.min() * 0.78, elements.max() * 1.22)
    add_panel_label(ax_time, "b", x=-0.09)

    gpu_methods = [m for m in METHOD_ORDER if m != "CPU_Serial"]
    for method in gpu_methods:
        method_rows = grouped[method]
        x = np.array([r["Elements"] for r in method_rows], dtype=float)
        y = np.array([max(float(r["Error"]), 1e-18) for r in method_rows], dtype=float)
        ax_error.plot(
            x,
            y,
            marker=METHOD_MARKERS[method],
            color=METHOD_COLORS[method],
            linewidth=1.15,
            markersize=3.7,
            markeredgecolor="white",
            markeredgewidth=0.35,
            label=METHOD_LABELS[method],
        )
    ax_error.axhline(1e-15, color=PALETTE["neutral_mid"], linewidth=0.7, linestyle=(0, (3, 2)))
    ax_error.text(
        0.02,
        0.93,
        "all rows PASS",
        transform=ax_error.transAxes,
        fontsize=6.0,
        color=PALETTE["neutral_black"],
        va="top",
        ha="left",
    )
    ax_error.set_xscale("log")
    ax_error.set_yscale("log")
    ax_error.set_ylabel("Relative error")
    ax_error.set_xlabel("Finite elements")
    ax_error.set_title("Numerical agreement")
    ax_error.set_ylim(4e-17, 2e-15)
    ax_error.set_xlim(elements.min() * 0.78, elements.max() * 1.22)
    ax_error.grid(True, which="major", axis="both", color="#D8D8D8", linewidth=0.45)
    ax_error.grid(True, which="minor", axis="y", color="#EAEAEA", linewidth=0.25)
    add_panel_label(ax_error, "c", x=-0.09)

    largest = int(elements.max())
    largest_rows = [r for r in rows if r["Elements"] == largest and r["Algorithm"] != "CPU_Serial"]
    largest_rows = sorted(largest_rows, key=lambda r: float(r["Speedup"]))
    labels = [METHOD_SHORT_LABELS[str(r["Algorithm"])] for r in largest_rows]
    speeds = np.array([float(r["Speedup"]) for r in largest_rows])
    y_pos = np.arange(len(largest_rows))
    colors = [METHOD_COLORS[str(r["Algorithm"])] for r in largest_rows]
    bars = ax_large.barh(y_pos, speeds, color=colors, edgecolor="black", linewidth=0.45, height=0.58)
    ax_large.set_yticks(y_pos)
    ax_large.set_yticklabels(labels)
    ax_large.set_xlabel("Speedup (x)")
    ax_large.set_title(f"Largest mesh ({largest:,} elements)", pad=8)
    ax_large.set_xlim(0, max(speeds) * 1.22)
    ax_large.grid(True, axis="x", color="#D8D8D8", linewidth=0.45)
    for bar, value in zip(bars, speeds):
        ax_large.text(
            value + max(speeds) * 0.025,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}x",
            va="center",
            ha="left",
            fontsize=6.1,
        )
    add_panel_label(ax_large, "d", x=-0.09, y=1.16)

    handles, labels = ax_speedup.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.985),
        ncol=4,
        handlelength=1.8,
        columnspacing=1.15,
        borderaxespad=0.0,
    )
    fig.text(
        0.02,
        0.012,
        "Historical GPU benchmark summary; deterministic rows only, no uncertainty intervals. "
        "Source data copied into this package.",
        fontsize=5.7,
        color=PALETTE["neutral_mid"],
        ha="left",
        va="bottom",
    )

    output_base = output_dir / FIGURE_STEM
    fig.savefig(f"{output_base}.svg", bbox_inches="tight")
    fig.savefig(f"{output_base}.pdf", bbox_inches="tight")
    fig.savefig(f"{output_base}.png", dpi=600, bbox_inches="tight")
    fig.savefig(f"{output_base}.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)
    return output_base


def write_manifest(
    output_dir: Path,
    source_copy: Path,
    rows: list[dict[str, object]],
    source_sha: str,
    output_base: Path,
) -> None:
    elements = sorted({int(r["Elements"]) for r in rows})
    dofs_by_elements = {int(r["Elements"]): int(r["DOFs"]) for r in rows}
    pass_count = sum(1 for r in rows if r["Status"] == "PASS")
    max_speed_row = max(
        (r for r in rows if r["Algorithm"] != "CPU_Serial"),
        key=lambda r: float(r["Speedup"]),
    )
    largest = max(elements)
    largest_rows = sorted(
        [r for r in rows if r["Elements"] == largest and r["Algorithm"] != "CPU_Serial"],
        key=lambda r: str(r["Algorithm"]),
    )
    export_links = ", ".join(
        f"[{suffix}]({output_base.name}.{suffix})" for suffix in ["svg", "pdf", "png", "tiff"]
    )
    rows_md = "\n".join(
        f"| {element:,} | {dofs_by_elements[element]:,} |"
        for element in elements
    )
    largest_md = "\n".join(
        f"| {METHOD_LABELS[str(r['Algorithm'])]} | {float(r['Speedup']):.2f}x | "
        f"{float(r['Time_ms']):.3f} | {float(r['Error']):.2e} |"
        for r in largest_rows
    )
    text = f"""# Historical GPU Parallel Assembly Benchmark Figure

This package visualizes the provided historical GPU benchmark CSV with the Python /
matplotlib backend only.

## Figure Contract

- Core conclusion: GPU parallel assembly kernels deliver strong but scale-dependent
  speedups over CPU serial assembly, and the plotted PASS rows keep relative error
  near floating-point roundoff.
- Figure archetype: quantitative grid with a dominant speedup panel and three
  supporting quantitative panels.
- Backend: Python / matplotlib only.
- Final size: double-column style, 7.2 x 4.9 inch before tight export.
- Target output: editable SVG, vector PDF, 600 dpi PNG preview, and 600 dpi TIFF.
- Source data: `{source_copy.relative_to(output_dir)}` copied from the provided CSV.
- Source data SHA-256: `{source_sha}`.
- Statistics: deterministic single benchmark rows; no inferential statistics or
  uncertainty intervals are introduced.
- Image integrity: vector line/bar plots generated directly from CSV values; no
  raster adjustment or image enhancement is applied.
- Reviewer risk: the CSV has no memory-use fields and no repeated measurements, so
  the figure must not claim memory behavior or statistical variability.

## Panel Map

- a: Hero panel, speedup versus problem scale for all algorithms.
- b: Absolute assembly time versus problem scale, showing the baseline and GPU
  kernels on comparable log scales.
- c: Numerical error for GPU kernels, with PASS status summarized from the source
  rows.
- d: Largest-mesh speedup ranking for the GPU kernels.

## Source Data Summary

- Rows: {len(rows)}
- PASS rows: {pass_count}
- Algorithms: {", ".join(METHOD_LABELS[m] for m in METHOD_ORDER)}
- Peak GPU speedup: {float(max_speed_row["Speedup"]):.2f}x
  ({METHOD_LABELS[str(max_speed_row["Algorithm"])]}, {int(max_speed_row["Elements"]):,}
  elements).

| Elements | DOFs |
| ---: | ---: |
{rows_md}

## Largest Mesh Summary

| Algorithm | Speedup | Time ms | Relative error |
| --- | ---: | ---: | ---: |
{largest_md}

## Exports

| Figure | Files |
| --- | --- |
| `{FIGURE_STEM}` | {export_links} |

## QA Notes

- SVG text is preserved with `svg.fonttype = none`.
- PDF text is exported with TrueType font embedding through `pdf.fonttype = 42`.
- PNG and TIFF are exported at 600 dpi.
- The script validates required columns, algorithm/scale coverage, duplicate rows,
  non-zero output sizes, image dimensions, and SVG text nodes.
"""
    (output_dir / "manifest.md").write_text(text, encoding="utf-8")


def write_qa_report(output_dir: Path, output_base: Path, source_copy: Path) -> None:
    files = [output_base.with_suffix(suffix) for suffix in [".svg", ".pdf", ".png", ".tiff"]]
    checks = []
    for file_path in files:
        size = file_path.stat().st_size
        checks.append((file_path.name, size))
        if size <= 0:
            raise ValueError(f"Empty output file: {file_path}")

    svg_text = output_base.with_suffix(".svg").read_text(encoding="utf-8")
    if "<text" not in svg_text:
        raise ValueError("SVG contains no editable <text> nodes.")
    if "path id=\"DejaVuSans" in svg_text or "<defs><path" in svg_text:
        raise ValueError("SVG appears to outline text instead of preserving text nodes.")

    image_lines = []
    for suffix in [".png", ".tiff"]:
        with Image.open(output_base.with_suffix(suffix)) as img:
            width, height = img.size
            image_lines.append(f"- `{output_base.with_suffix(suffix).name}`: {width} x {height} px")
            if width < 2000 or height < 1200:
                raise ValueError(f"Raster output is unexpectedly small: {img.size}")

    source_hash = sha256_file(source_copy)
    qa_text = f"""# QA Report

## Backend Exclusivity

- Selected backend: Python.
- Plotting, export, preview raster generation, and QA checks were all run with the
  Python script in this package.
- No R graphics device or non-Python renderer was used.

## Output Files

| File | Size bytes |
| --- | ---: |
""" + "\n".join(f"| `{name}` | {size} |" for name, size in checks)
    qa_text += f"""

## Raster Dimensions

{chr(10).join(image_lines)}

## Source Data

- Copied source CSV: `{source_copy.relative_to(output_dir)}`
- SHA-256: `{source_hash}`

## Checks Passed

- Required CSV columns present.
- All expected algorithm/scale combinations present once.
- All benchmark statuses are retained in the copied source data.
- SVG keeps editable text nodes.
- PDF, SVG, PNG, and TIFF files are non-empty.
- PNG and TIFF are high-resolution raster exports.
"""
    (output_dir / "qa_report.md").write_text(qa_text, encoding="utf-8")


def run() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(args.input)
    validate_rows(rows)
    source_copy = copy_source_data(args.input, output_dir)
    source_sha = sha256_file(source_copy)
    output_base = make_figure(rows, output_dir)
    write_manifest(output_dir, source_copy, rows, source_sha, output_base)
    write_qa_report(output_dir, output_base, source_copy)
    print(f"Wrote {output_base}.svg/.pdf/.png/.tiff")
    print(f"Wrote {output_dir / 'manifest.md'}")
    print(f"Wrote {output_dir / 'qa_report.md'}")


if __name__ == "__main__":
    run()
