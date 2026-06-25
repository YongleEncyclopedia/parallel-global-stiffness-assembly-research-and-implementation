#!/usr/bin/env python3
"""Build a Nature-style visual summary from CPU parallel assembly benchmarks."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
        "legend.fontsize": 6.0,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


PACKAGE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PACKAGE_DIR.parent
DEFAULT_SOURCE_DIR = RESULTS_DIR / "2026-04-28-12charts-repeat3-threads1to14" / "csv"
MAIN_SOURCE_NAME = "04_windhub_physics_tet4.csv"
FIGURE_STEM = "fig01_cpu_parallel_assembly_benchmark"
REQUIRED_COLUMNS = {
    "case_name",
    "kernel",
    "nodes",
    "elements",
    "dofs",
    "nnz",
    "algorithm",
    "threads",
    "assembly_ms",
    "assembly_mean_ms",
    "assembly_std_ms",
    "speedup",
    "rel_l2",
    "max_abs",
    "extra_memory_bytes",
    "status",
    "run_count",
    "platform",
}

SOURCE_FILES = [
    "01_cube_tet4_8x8x8_simplified.csv",
    "02_cube_tet4_8x8x8_physics_tet4.csv",
    "03_windhub_simplified.csv",
    "04_windhub_physics_tet4.csv",
]

METHOD_ORDER = [
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
    "cpu_coo_sort_reduce",
]
METHOD_LABELS = {
    "cpu_serial": "CPU serial",
    "cpu_atomic": "Atomic",
    "cpu_private_csr": "Private CSR",
    "cpu_row_owner": "Row owner",
    "cpu_graph_coloring": "Graph coloring",
    "cpu_coo_sort_reduce": "COO sort-reduce",
}
METHOD_COLORS = {
    "cpu_serial": "#4D4D4D",
    "cpu_atomic": "#0F4D92",
    "cpu_private_csr": "#42949E",
    "cpu_row_owner": "#9A4D8E",
    "cpu_graph_coloring": "#8BCF8B",
    "cpu_coo_sort_reduce": "#B89B4D",
}
METHOD_MARKERS = {
    "cpu_atomic": "s",
    "cpu_private_csr": "^",
    "cpu_row_owner": "D",
    "cpu_graph_coloring": "o",
    "cpu_coo_sort_reduce": "v",
}
PALETTE = {
    "neutral_light": "#CFCECE",
    "neutral_mid": "#767676",
    "neutral_dark": "#4D4D4D",
    "neutral_black": "#272727",
}
SCENARIO_LABELS = {
    "01_cube_tet4_8x8x8_simplified.csv": "Cube\nsimplified",
    "02_cube_tet4_8x8x8_physics_tet4.csv": "Cube\nphysics",
    "03_windhub_simplified.csv": "WindHub\nsimplified",
    "04_windhub_physics_tet4.csv": "WindHub\nphysics",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate publication-grade CPU benchmark figures from PGSA CSV files."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory containing the four 2026-04-28 CPU benchmark CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PACKAGE_DIR,
        help="Output directory for figures, copied source data, manifest, and QA notes.",
    )
    return parser.parse_args()


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def read_csv(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"Source CSV not found: {path}")
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Source CSV has no header: {path}")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path.name} missing required columns: {sorted(missing)}")
        rows = []
        for line_number, raw in enumerate(reader, start=2):
            try:
                rows.append(
                    {
                        "source_name": path.name,
                        "case_name": raw["case_name"],
                        "kernel": raw["kernel"],
                        "nodes": int(raw["nodes"]),
                        "elements": int(raw["elements"]),
                        "dofs": int(raw["dofs"]),
                        "nnz": int(raw["nnz"]),
                        "algorithm": raw["algorithm"],
                        "threads": int(raw["threads"]),
                        "assembly_ms": parse_float(raw["assembly_ms"]),
                        "assembly_mean_ms": parse_float(raw["assembly_mean_ms"]),
                        "assembly_std_ms": parse_float(raw["assembly_std_ms"]),
                        "speedup": parse_float(raw["speedup"]),
                        "rel_l2": parse_float(raw["rel_l2"]),
                        "max_abs": parse_float(raw["max_abs"]),
                        "extra_memory_bytes": parse_float(raw["extra_memory_bytes"]),
                        "status": raw["status"],
                        "run_count": int(raw["run_count"]),
                        "platform": raw["platform"],
                        "line": line_number,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - preserve CSV line context.
                raise ValueError(f"Could not parse {path.name}:{line_number}") from exc
    if not rows:
        raise ValueError(f"Source CSV has no data rows: {path}")
    return rows


def read_sources(source_dir: Path) -> dict[str, list[dict[str, object]]]:
    datasets = {}
    for source_name in SOURCE_FILES:
        datasets[source_name] = read_csv(source_dir / source_name)
    return datasets


def validate_datasets(datasets: dict[str, list[dict[str, object]]]) -> None:
    expected_algorithms = set(METHOD_ORDER) | {"cpu_serial"}
    for source_name, rows in datasets.items():
        algorithms = {str(r["algorithm"]) for r in rows}
        missing_algorithms = expected_algorithms - algorithms
        unknown_algorithms = algorithms - expected_algorithms
        if missing_algorithms:
            raise ValueError(f"{source_name} missing algorithms: {sorted(missing_algorithms)}")
        if unknown_algorithms:
            raise ValueError(f"{source_name} has unknown algorithms: {sorted(unknown_algorithms)}")
        pass_rows = [r for r in rows if r["status"] == "PASS"]
        if len(pass_rows) != len(rows):
            raise ValueError(f"{source_name} has non-PASS rows; inspect before plotting.")

        duplicate_counts: dict[tuple[str, int], int] = defaultdict(int)
        for row in rows:
            duplicate_counts[(str(row["algorithm"]), int(row["threads"]))] += 1
        duplicates = {
            key: count
            for key, count in duplicate_counts.items()
            if count > 1 and key[0] != "cpu_serial"
        }
        if duplicates:
            raise ValueError(f"{source_name} duplicate algorithm/thread rows: {duplicates}")
        serial_threads = sorted(
            int(r["threads"]) for r in rows if r["algorithm"] == "cpu_serial"
        )
        if serial_threads != [1]:
            raise ValueError(f"{source_name} expected one serial baseline at thread 1.")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_source_data(source_dir: Path, output_dir: Path) -> dict[str, Path]:
    target_dir = output_dir / "source_data"
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = {}
    for source_name in SOURCE_FILES:
        source = (source_dir / source_name).resolve()
        target = (target_dir / source_name).resolve()
        if source != target:
            shutil.copy2(source, target)
        copied[source_name] = target
    return copied


def rows_for_algorithm(rows: list[dict[str, object]], algorithm: str) -> list[dict[str, object]]:
    return sorted(
        [r for r in rows if r["algorithm"] == algorithm],
        key=lambda r: int(r["threads"]),
    )


def best_row(rows: list[dict[str, object]], algorithm: str | None = None) -> dict[str, object]:
    candidates = rows if algorithm is None else [r for r in rows if r["algorithm"] == algorithm]
    if not candidates:
        raise ValueError(f"No rows found for algorithm={algorithm}")
    return max(candidates, key=lambda r: float(r["speedup"]))


def add_panel_label(
    ax: plt.Axes,
    label: str,
    x: float = -0.075,
    y: float = 1.055,
) -> None:
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


def set_clean_thread_ticks(ax: plt.Axes) -> None:
    ax.set_xticks([1, 2, 4, 8, 12, 14])
    ax.set_xlim(0.75, 14.8)


def make_figure(
    datasets: dict[str, list[dict[str, object]]],
    output_dir: Path,
) -> Path:
    main_rows = datasets[MAIN_SOURCE_NAME]
    serial_row = next(r for r in main_rows if r["algorithm"] == "cpu_serial")
    serial_time = float(serial_row["assembly_ms"])
    best_overall = best_row([r for r in main_rows if r["algorithm"] != "cpu_serial"])

    fig = plt.figure(figsize=(7.2, 4.9))
    gs = fig.add_gridspec(
        2,
        3,
        height_ratios=[1.34, 1.0],
        width_ratios=[1.08, 1.0, 0.95],
        hspace=0.54,
        wspace=0.46,
    )
    ax_speedup = fig.add_subplot(gs[0, :])
    ax_time = fig.add_subplot(gs[1, 0])
    ax_error = fig.add_subplot(gs[1, 1])
    ax_tradeoff = fig.add_subplot(gs[1, 2])

    speedup_end_offsets = {
        "cpu_atomic": (5, 8),
        "cpu_private_csr": (5, 0),
        "cpu_row_owner": (5, -8),
        "cpu_graph_coloring": (5, -2),
        "cpu_coo_sort_reduce": (5, 0),
    }
    for method in METHOD_ORDER:
        method_rows = rows_for_algorithm(main_rows, method)
        threads = np.array([r["threads"] for r in method_rows], dtype=float)
        speedup = np.array([r["speedup"] for r in method_rows], dtype=float)
        assembly = np.array([r["assembly_ms"] for r in method_rows], dtype=float)
        rel_l2 = np.array([max(float(r["rel_l2"]), 1e-18) for r in method_rows])
        color = METHOD_COLORS[method]
        label = METHOD_LABELS[method]
        marker = METHOD_MARKERS[method]

        ax_speedup.plot(
            threads,
            speedup,
            marker=marker,
            color=color,
            linewidth=1.35,
            markersize=4.0,
            markeredgecolor="white",
            markeredgewidth=0.35,
            label=label,
        )
        ax_time.plot(
            threads,
            assembly,
            marker=marker,
            color=color,
            linewidth=1.15,
            markersize=3.5,
            markeredgecolor="white",
            markeredgewidth=0.35,
        )
        ax_error.plot(
            threads,
            rel_l2,
            marker=marker,
            color=color,
            linewidth=1.1,
            markersize=3.5,
            markeredgecolor="white",
            markeredgewidth=0.35,
        )
        annotate_end_label(
            ax_speedup,
            threads[-1],
            speedup[-1],
            label,
            color,
            speedup_end_offsets[method],
        )

    ax_speedup.axhline(
        1,
        color=METHOD_COLORS["cpu_serial"],
        linewidth=1.0,
        linestyle=(0, (3, 2)),
    )
    ax_speedup.text(
        14.3,
        1.03,
        "CPU serial",
        fontsize=5.8,
        color=METHOD_COLORS["cpu_serial"],
        ha="right",
        va="bottom",
    )
    ax_speedup.set_title("CPU parallel assembly accelerates WindHub physics Tet4 within memory tradeoffs", pad=8)
    ax_speedup.set_ylabel("Speedup vs CPU serial (x)")
    ax_speedup.set_xlabel("Threads")
    ax_speedup.set_ylim(0, max(6.2, float(best_overall["speedup"]) * 1.18))
    set_clean_thread_ticks(ax_speedup)
    ax_speedup.grid(True, axis="both", color="#D8D8D8", linewidth=0.45)
    add_panel_label(ax_speedup, "a")
    ax_speedup.annotate(
        f"peak {float(best_overall['speedup']):.2f}x",
        xy=(float(best_overall["threads"]), float(best_overall["speedup"])),
        xytext=(-36, 18),
        textcoords="offset points",
        fontsize=6.3,
        ha="right",
        va="bottom",
        arrowprops={
            "arrowstyle": "-|>",
            "lw": 0.6,
            "color": PALETTE["neutral_black"],
            "mutation_scale": 7,
        },
    )

    ax_time.axhline(
        serial_time,
        color=METHOD_COLORS["cpu_serial"],
        linewidth=1.0,
        linestyle=(0, (3, 2)),
    )
    ax_time.text(
        1.0,
        serial_time * 1.07,
        "serial",
        color=METHOD_COLORS["cpu_serial"],
        fontsize=5.8,
        ha="left",
        va="bottom",
    )
    ax_time.set_yscale("log")
    ax_time.set_ylabel("Assembly time (ms)")
    ax_time.set_xlabel("Threads")
    ax_time.set_title("Absolute time")
    set_clean_thread_ticks(ax_time)
    ax_time.grid(True, which="major", axis="both", color="#D8D8D8", linewidth=0.45)
    ax_time.grid(True, which="minor", axis="y", color="#EAEAEA", linewidth=0.25)
    add_panel_label(ax_time, "b", x=-0.09)

    ax_error.axhline(
        1e-15,
        color=PALETTE["neutral_mid"],
        linewidth=0.7,
        linestyle=(0, (3, 2)),
    )
    ax_error.text(
        0.03,
        0.93,
        "all rows PASS",
        transform=ax_error.transAxes,
        fontsize=6.0,
        color=PALETTE["neutral_black"],
        va="top",
        ha="left",
    )
    ax_error.set_yscale("log")
    ax_error.set_ylabel("Relative L2 error")
    ax_error.set_xlabel("Threads")
    ax_error.set_title("Numerical agreement")
    ax_error.set_ylim(4e-19, 4e-15)
    set_clean_thread_ticks(ax_error)
    ax_error.grid(True, which="major", axis="both", color="#D8D8D8", linewidth=0.45)
    ax_error.grid(True, which="minor", axis="y", color="#EAEAEA", linewidth=0.25)
    add_panel_label(ax_error, "c", x=-0.09)

    tradeoff_rows = [best_row(main_rows, method) for method in METHOD_ORDER]
    for row in tradeoff_rows:
        method = str(row["algorithm"])
        mem_gib = float(row["extra_memory_bytes"]) / (1024**3)
        speed = float(row["speedup"])
        ax_tradeoff.scatter(
            mem_gib,
            speed,
            s=42,
            marker=METHOD_MARKERS[method],
            color=METHOD_COLORS[method],
            edgecolor="white",
            linewidth=0.45,
            zorder=3,
        )
        label_offset = {
            "cpu_atomic": (5, 4),
            "cpu_private_csr": (5, -4),
            "cpu_row_owner": (5, 3),
            "cpu_graph_coloring": (5, -8),
            "cpu_coo_sort_reduce": (5, 2),
        }[method]
        ax_tradeoff.annotate(
            METHOD_LABELS[method],
            xy=(mem_gib, speed),
            xytext=label_offset,
            textcoords="offset points",
            fontsize=5.6,
            color=METHOD_COLORS[method],
            ha="left",
            va="center",
            clip_on=False,
        )
    ax_tradeoff.set_xlabel("Extra memory at method peak (GiB)")
    ax_tradeoff.set_ylabel("Peak speedup (x)")
    ax_tradeoff.set_title("Memory-speed tradeoff")
    max_mem = max(float(r["extra_memory_bytes"]) for r in tradeoff_rows) / (1024**3)
    ax_tradeoff.set_xlim(-0.12, max_mem * 1.35)
    ax_tradeoff.set_ylim(0, max(float(r["speedup"]) for r in tradeoff_rows) * 1.24)
    ax_tradeoff.grid(True, axis="both", color="#D8D8D8", linewidth=0.45)
    add_panel_label(ax_tradeoff, "d", x=-0.09)

    handles, labels = ax_speedup.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.985),
        ncol=5,
        handlelength=1.6,
        columnspacing=0.9,
        borderaxespad=0.0,
    )
    fig.text(
        0.02,
        0.012,
        "CPU benchmark summary; mean assembly time from repeat-3 rows where available. "
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


def summarize_sources(datasets: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    summary = []
    for source_name, rows in datasets.items():
        best = best_row([r for r in rows if r["algorithm"] != "cpu_serial"])
        max_rel_l2 = max(float(r["rel_l2"]) for r in rows)
        max_abs = max(float(r["max_abs"]) for r in rows)
        max_mem_gib = max(float(r["extra_memory_bytes"]) for r in rows) / (1024**3)
        serial = next(r for r in rows if r["algorithm"] == "cpu_serial")
        summary.append(
            {
                "source_name": source_name,
                "label": SCENARIO_LABELS[source_name].replace("\n", " "),
                "rows": len(rows),
                "best_algorithm": str(best["algorithm"]),
                "best_label": METHOD_LABELS[str(best["algorithm"])],
                "best_threads": int(best["threads"]),
                "best_speedup": float(best["speedup"]),
                "best_time_ms": float(best["assembly_ms"]),
                "serial_time_ms": float(serial["assembly_ms"]),
                "max_rel_l2": max_rel_l2,
                "max_abs": max_abs,
                "max_extra_memory_gib": max_mem_gib,
                "run_count": sorted({int(r["run_count"]) for r in rows}),
                "platform": str(serial["platform"]),
            }
        )
    return summary


def write_manifest(
    output_dir: Path,
    copied_sources: dict[str, Path],
    datasets: dict[str, list[dict[str, object]]],
    output_base: Path,
) -> None:
    summary = summarize_sources(datasets)
    main_rows = datasets[MAIN_SOURCE_NAME]
    main_serial = next(r for r in main_rows if r["algorithm"] == "cpu_serial")
    best_main = best_row([r for r in main_rows if r["algorithm"] != "cpu_serial"])
    export_links = ", ".join(
        f"[{suffix}]({output_base.name}.{suffix})"
        for suffix in ["svg", "pdf", "png", "tiff"]
    )
    source_rows = "\n".join(
        f"| `{name}` | `{path.relative_to(output_dir)}` | `{sha256_file(path)}` |"
        for name, path in copied_sources.items()
    )
    scenario_rows = "\n".join(
        f"| {item['label']} | {item['rows']} | {item['best_label']} | "
        f"{item['best_threads']} | {item['best_speedup']:.2f}x | "
        f"{item['best_time_ms']:.3f} | {item['max_extra_memory_gib']:.2f} | "
        f"{item['max_rel_l2']:.2e} | {item['max_abs']:.2e} |"
        for item in summary
    )
    text = f"""# CPU Parallel Assembly Benchmark Figure

This package visualizes CPU parallel assembly benchmark results with the Python /
matplotlib backend only.

## Figure Contract

- Core conclusion: CPU parallel assembly accelerates the WindHub physics Tet4
  benchmark, but the fastest backend must be interpreted together with numerical
  agreement and extra-memory cost.
- Figure archetype: quantitative grid with a dominant speedup panel and three
  supporting quantitative panels.
- Backend: Python / matplotlib only.
- Final size: double-column style, 7.2 x 4.9 inch before tight export.
- Target output: editable SVG, vector PDF, 600 dpi PNG preview, and 600 dpi TIFF.
- Source data: four repeat-3 CPU benchmark CSV files copied into `source_data/`.
- Statistics: plotted assembly values are deterministic CSV summaries; the source
  rows report `run_count=3`, means, minima, maxima, and standard deviations, but
  this figure introduces no inferential statistics.
- Image integrity: vector line and scatter plots generated directly from CSV values;
  no raster adjustment or image enhancement is applied.
- Reviewer risk: the figure is a platform-specific CPU benchmark snapshot
  ({main_serial['platform']}); it should not be read as cross-platform performance
  without the separate platform-profile figures.

## Panel Map

- a: Hero panel, WindHub physics Tet4 speedup versus thread count.
- b: Absolute assembly time for the same benchmark, with CPU serial shown as a
  dashed baseline.
- c: Relative L2 numerical error for parallel backends; all plotted rows are PASS.
- d: Per-backend peak speedup against extra memory at that backend's peak record.

## Main Benchmark Summary

- Mesh: {main_serial['case_name']}
- Elements: {int(main_serial['elements']):,}
- DOFs: {int(main_serial['dofs']):,}
- Nonzeros: {int(main_serial['nnz']):,}
- Serial assembly time: {float(main_serial['assembly_ms']):.3f} ms
- Peak CPU parallel speedup: {float(best_main['speedup']):.2f}x
  ({METHOD_LABELS[str(best_main['algorithm'])]}, {int(best_main['threads'])} threads,
  {float(best_main['assembly_ms']):.3f} ms).

## Scenario Audit

| Scenario | Rows | Best backend | Threads | Best speedup | Time ms | Max extra memory GiB | Max rel L2 | Max abs |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{scenario_rows}

## Source Data

| Source | Copied file | SHA-256 |
| --- | --- | --- |
{source_rows}

## Exports

| Figure | Files |
| --- | --- |
| `{FIGURE_STEM}` | {export_links} |

## QA Notes

- SVG text is preserved with `svg.fonttype = none`.
- PDF text is exported with TrueType font embedding through `pdf.fonttype = 42`.
- PNG and TIFF are exported at 600 dpi.
- The script validates required columns, expected algorithms, duplicate thread rows,
  PASS-only source status, non-zero output sizes, image dimensions, and SVG text nodes.
"""
    (output_dir / "manifest.md").write_text(text, encoding="utf-8")


def write_qa_report(
    output_dir: Path,
    output_base: Path,
    copied_sources: dict[str, Path],
) -> None:
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
    if "Speedup vs CPU serial" not in svg_text:
        raise ValueError("SVG missing expected y-axis label.")

    image_lines = []
    for suffix in [".png", ".tiff"]:
        with Image.open(output_base.with_suffix(suffix)) as img:
            width, height = img.size
            image_lines.append(f"- `{output_base.with_suffix(suffix).name}`: {width} x {height} px")
            if width < 2000 or height < 1200:
                raise ValueError(f"Raster output is unexpectedly small: {img.size}")

    source_lines = "\n".join(
        f"- `{path.relative_to(output_dir)}`: `{sha256_file(path)}`"
        for path in copied_sources.values()
    )
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

## Source Data Hashes

{source_lines}

## Checks Passed

- Required CSV columns present.
- Expected CPU algorithms present in every source CSV.
- All source rows have `status=PASS`.
- No duplicate parallel algorithm/thread rows.
- SVG keeps editable text nodes.
- PDF, SVG, PNG, and TIFF files are non-empty.
- PNG and TIFF are high-resolution raster exports.
"""
    (output_dir / "qa_report.md").write_text(qa_text, encoding="utf-8")


def run() -> None:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = read_sources(source_dir)
    validate_datasets(datasets)
    copied_sources = copy_source_data(source_dir, output_dir)
    output_base = make_figure(datasets, output_dir)
    write_manifest(output_dir, copied_sources, datasets, output_base)
    write_qa_report(output_dir, output_base, copied_sources)
    print(f"Wrote {output_base}.svg/.pdf/.png/.tiff")
    print(f"Wrote {output_dir / 'manifest.md'}")
    print(f"Wrote {output_dir / 'qa_report.md'}")


if __name__ == "__main__":
    run()
