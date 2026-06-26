#!/usr/bin/env python3
"""Generate Nature-style free-tip deflection validation figures."""

from __future__ import annotations

import csv
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

mpl.rcParams.update(
    {
        "pdf.fonttype": 42,
        "font.size": 12,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.9,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CPU_ROOT = REPO_ROOT / "parallel_global_stiffness_assembly" / "cpu_parallel_stiffness_assembly"
OUT_ROOT = CPU_ROOT / "reports" / "2026-05-28-solver-validation-case-figures"
ASSET_DIR = OUT_ROOT / "assets"
SOURCE_DIR = OUT_ROOT / "source_data"


PALETTE = {
    "macos": "#7884B4",
    "linux": "#42949E",
    "windows": "#B64342",
    "neutral_dark": "#272727",
    "neutral_mid": "#767676",
    "neutral_light": "#D8D8D8",
    "panel_bg": "#F6F7F9",
    "panel_edge": "#D8DCE2",
    "blue_main": "#0F4D92",
}


@dataclass(frozen=True)
class PlatformDatum:
    case_key: str
    platform: str
    reference_solver: str
    source_metric: str
    rel_fraction: float
    rel_percent: float
    source_file: str
    source_note: str


@dataclass(frozen=True)
class CaseSpec:
    key: str
    title: str
    subtitle: str
    interpretation: str
    nodes: int
    elements: int
    dofs: int
    nnz: int
    sparsity_asset: str
    note: str


DATA = [
    PlatformDatum(
        "hex8",
        "Mac Studio\nCOMSOL",
        "COMSOL 6.2",
        "legacy free-tip probe rel_diff",
        1.962e-4,
        1.962e-2,
        "reports/2026-05-24-current-dialogue-progress/index.html",
        "legacy macOS+COMSOL report table; converted from fraction to percent",
    ),
    PlatformDatum(
        "hex8",
        "Linux Intel\nCalculiX",
        "CalculiX 2.23",
        "free-tip probe rel_diff",
        2.6988530574971226e-7,
        2.6988530574971226e-5,
        "results/validation-export/2026-05-23-linux-intel-calculix/calculix_validation_report.md",
        "report row for cantilever_hex8_medium",
    ),
    PlatformDatum(
        "hex8",
        "Windows AMD\nAbaqus",
        "Abaqus 2025",
        "free_tip_deflection_rel_pct",
        2.9805500991983753e-2,
        2.9805500991983753,
        "results/2026-05-27-windows-amd-abaqus-figures/source_data/validation_free_tip_deflection_summary.csv",
        "canonical free-tip deflection percentage",
    ),
    PlatformDatum(
        "tet4",
        "Mac Studio\nCOMSOL",
        "COMSOL 6.2",
        "legacy free-tip probe rel_diff",
        1.771e-4,
        1.771e-2,
        "reports/2026-05-24-current-dialogue-progress/index.html",
        "legacy macOS+COMSOL report table; converted from fraction to percent",
    ),
    PlatformDatum(
        "tet4",
        "Linux Intel\nCalculiX",
        "CalculiX 2.23",
        "free-tip probe rel_diff",
        2.839421574760008e-7,
        2.839421574760008e-5,
        "results/validation-export/2026-05-23-linux-intel-calculix/calculix_validation_report.md",
        "report row for cantilever_tet4_medium",
    ),
    PlatformDatum(
        "tet4",
        "Windows AMD\nAbaqus",
        "Abaqus 2025",
        "free_tip_deflection_rel_pct",
        4.6765150745229694e-8,
        4.6765150745229694e-6,
        "results/2026-05-27-windows-amd-abaqus-figures/source_data/validation_free_tip_deflection_summary.csv",
        "canonical free-tip deflection percentage",
    ),
]


CASES = {
    "hex8": CaseSpec(
        key="hex8",
        title="Structured Hex8/C3D8 cantilever",
        subtitle="Free-tip deflection discrepancy between MATLAB solve and FE reference",
        interpretation="Abaqus shows a 2.98% Hex8 discrepancy; COMSOL and CalculiX stay below 0.02%.",
        nodes=325,
        elements=192,
        dofs=975,
        nnz=56277,
        sparsity_asset=(
            "results/2026-05-27-macos-matlab-cantilever-topology-sparsity/"
            "cantilever_hex8_medium/cantilever_hex8_medium_stiffness_sparsity_matlab.svg"
        ),
        note="Solver-validation case: cantilever_hex8_medium.",
    ),
    "tet4": CaseSpec(
        key="tet4",
        title="Tet4/C3D4 cantilever",
        subtitle="Free-tip deflection discrepancy between MATLAB solve and FE reference",
        interpretation="All references stay below 0.02%; Abaqus and CalculiX are near probe precision.",
        nodes=325,
        elements=1152,
        dofs=975,
        nnz=33525,
        sparsity_asset=(
            "results/2026-05-27-macos-matlab-cantilever-topology-sparsity/"
            "cantilever_tet4_unstructured_medium/cantilever_tet4_unstructured_medium_stiffness_sparsity_matlab.svg"
        ),
        note="Validation case: cantilever_tet4_medium. Companion sparsity asset: unstructured Tet4 slide topology.",
    ),
}


def format_percent(value: float) -> str:
    if value >= 0.01:
        return f"{value:.5g}%"
    return f"{value:.2e}%"


def ensure_dirs() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)


def write_source_tables() -> None:
    table_path = SOURCE_DIR / "solver_validation_free_tip_deflection_percent.csv"
    with table_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case_key",
                "platform",
                "reference_solver",
                "source_metric",
                "rel_fraction",
                "rel_percent",
                "source_file",
                "source_note",
            ]
        )
        for row in DATA:
            writer.writerow(
                [
                    row.case_key,
                    row.platform.replace("\n", " "),
                    row.reference_solver,
                    row.source_metric,
                    f"{row.rel_fraction:.17g}",
                    f"{row.rel_percent:.17g}",
                    row.source_file,
                    row.source_note,
                ]
            )

    manifest = {
        "metric": "100 * abs(abs(Uz_MATLAB_free_tip) - abs(Uz_FE_free_tip)) / abs(Uz_FE_free_tip)",
        "primary_probe": "free_tip_center",
        "backend": "Python / matplotlib",
        "case_metadata": {key: spec.__dict__ for key, spec in CASES.items()},
        "data_rows": [row.__dict__ for row in DATA],
    }
    (ASSET_DIR / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    figure_contract = """# Figure contract

- Core conclusion: solve-level free-tip deflection comparison is small for Tet4/C3D4 on all three references, while Hex8/C3D8 shows a Windows/Abaqus discrepancy that should be reported as a validation signal.
- Evidence chain: each figure maps the same free-tip percentage metric across macOS+COMSOL, Linux+CalculiX, and Windows+Abaqus; metadata cards define the mesh and stiffness sparsity context.
- Archetype: quantitative grid with a metadata sidecar.
- Backend: Python-only matplotlib export.
- Export contract: SVG primary with editable text, plus PDF, PNG, TIFF, and a source CSV.
- Review risk: macOS+COMSOL values are recovered from a legacy report table, not a current CSV package; Tet4 solver-validation and unstructured-Tet4 sparsity assets are not the same mesh.
"""
    (OUT_ROOT / "figure_contract.md").write_text(figure_contract, encoding="utf-8")


def add_card(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: Iterable[str],
    wrap_width: int = 58,
) -> None:
    rect = mpl.patches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=0.8,
        edgecolor=PALETTE["panel_edge"],
        facecolor=PALETTE["panel_bg"],
        transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(rect)
    ax.text(
        x + 0.035,
        y + h - 0.07,
        title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        fontweight="bold",
        color=PALETTE["neutral_dark"],
    )
    wrapped_lines = []
    for line in lines:
        if line.startswith("$"):
            wrapped_lines.append(line)
        else:
            wrapped_lines.append(textwrap.fill(line, width=wrap_width))

    ax.text(
        x + 0.035,
        y + h - 0.135,
        "\n".join(wrapped_lines),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.3,
        color=PALETTE["neutral_dark"],
        linespacing=1.45,
    )


def plot_case(case_key: str) -> None:
    spec = CASES[case_key]
    rows = [row for row in DATA if row.case_key == case_key]
    values = np.array([row.rel_percent for row in rows], dtype=float)
    labels = [row.platform for row in rows]
    colors = [PALETTE["macos"], PALETTE["linux"], PALETTE["windows"]]
    y_floor = 1e-6

    fig = plt.figure(figsize=(12.8, 7.2), dpi=300)
    grid = fig.add_gridspec(
        1,
        2,
        width_ratios=[1.75, 1.0],
        left=0.085,
        right=0.965,
        bottom=0.14,
        top=0.82,
        wspace=0.22,
    )
    ax = fig.add_subplot(grid[0, 0])
    side = fig.add_subplot(grid[0, 1])
    side.axis("off")

    fig.text(0.085, 0.925, spec.title, fontsize=24, fontweight="bold", color=PALETTE["neutral_dark"])
    fig.text(0.085, 0.885, spec.subtitle, fontsize=13.5, color=PALETTE["neutral_mid"])

    x = np.arange(len(values))
    ax.bar(
        x,
        values - y_floor,
        bottom=y_floor,
        width=0.62,
        color=colors,
        edgecolor=PALETTE["neutral_dark"],
        linewidth=0.7,
        alpha=0.92,
    )
    ax.scatter(x, values, s=46, color=PALETTE["neutral_dark"], zorder=4)

    for xi, yi, color in zip(x, values, colors):
        ax.text(
            xi,
            yi * 1.45,
            format_percent(float(yi)),
            ha="center",
            va="bottom",
            fontsize=10.5,
            fontweight="bold",
            color=color,
        )

    ax.set_yscale("log")
    ax.set_ylim(y_floor, 10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Free-tip deflection discrepancy (%)", fontsize=12)
    ax.set_title("Cross-platform solve-level validation", fontsize=13, loc="left", pad=12)
    ax.yaxis.set_major_locator(mpl.ticker.LogLocator(base=10, numticks=8))
    ax.yaxis.set_minor_locator(mpl.ticker.LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=80))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda y, _: f"{y:g}"))
    ax.grid(True, axis="y", which="major", color="#D8DCE2", linewidth=0.8)
    ax.grid(True, axis="y", which="minor", color="#ECEFF3", linewidth=0.35, alpha=0.6)
    ax.tick_params(axis="x", length=0)

    ax.text(
        -0.05,
        1.07,
        "a",
        transform=ax.transAxes,
        fontsize=15,
        fontweight="bold",
        ha="left",
        va="bottom",
        color=PALETTE["neutral_dark"],
    )
    side.text(
        -0.03,
        1.07,
        "b",
        transform=side.transAxes,
        fontsize=15,
        fontweight="bold",
        ha="left",
        va="bottom",
        color=PALETTE["neutral_dark"],
    )

    metric_lines = [
        r"$100 \times ||U_{z,\mathrm{MATLAB}}| - |U_{z,\mathrm{FE}}|| / |U_{z,\mathrm{FE}}|$",
        "probe: free_tip_center",
        "quantity: vertical displacement Uz",
        "scale: percent, log axis",
    ]
    add_card(side, 0.0, 0.68, 0.98, 0.26, "Metric", metric_lines)

    metadata_lines = [
        f"nodes: {spec.nodes}",
        f"elements: {spec.elements}",
        f"DOFs: {spec.dofs}",
        f"nnz(K): {spec.nnz}",
        "E = 1, nu = 0.3",
        "L = 1, W = 0.2, T = 0.1",
    ]
    add_card(side, 0.0, 0.35, 0.98, 0.27, "Case metadata", metadata_lines)

    add_card(
        side,
        0.0,
        0.03,
        0.98,
        0.25,
        "Interpretation",
        [spec.interpretation, spec.note],
    )

    fig.text(
        0.085,
        0.055,
        "Source data: macOS+COMSOL legacy report table; Linux+CalculiX validation report; "
        "Windows+Abaqus free-tip summary CSV. Sparse-pattern asset recorded in source_manifest.json.",
        fontsize=9.2,
        color=PALETTE["neutral_mid"],
    )

    output_base = ASSET_DIR / f"fig_{case_key}_free_tip_deflection_validation"
    fig.savefig(f"{output_base}.svg")
    fig.savefig(f"{output_base}.pdf")
    fig.savefig(f"{output_base}.png", dpi=300)
    fig.savefig(f"{output_base}.tiff", dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)


def write_readme() -> None:
    readme = """# Solver-validation case figures

This package contains two English Nature-style figures for monthly-report comparison:

- `fig_hex8_free_tip_deflection_validation`: structured Hex8/C3D8 cantilever.
- `fig_tet4_free_tip_deflection_validation`: Tet4/C3D4 cantilever.

The plotted metric is the free-tip vertical-deflection percentage discrepancy:

```text
100 * abs(abs(Uz_MATLAB_free_tip) - abs(Uz_FE_free_tip)) / abs(Uz_FE_free_tip)
```

The macOS+COMSOL values are recovered from the legacy report table, while Windows+Abaqus uses the current canonical `free_tip_deflection_rel_pct` summary. The Tet4 sparsity asset in the monthly slide is the unstructured Tet4 topology and is intentionally tracked separately from the three-platform solver-validation Tet4 case.
"""
    (OUT_ROOT / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    write_source_tables()
    write_readme()
    plot_case("hex8")
    plot_case("tet4")


if __name__ == "__main__":
    main()
