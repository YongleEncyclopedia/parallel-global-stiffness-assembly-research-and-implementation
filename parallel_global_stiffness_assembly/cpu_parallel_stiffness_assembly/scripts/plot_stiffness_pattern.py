#!/usr/bin/env python3
"""Generate MATLAB-spy-style sparse stiffness pattern figures from row,col CSV."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmark_figure_style import INK, MUTED, apply_presentation_style, save_figure, style_axis


apply_presentation_style()


def infer_dimension(paths: list[Path]) -> int:
    n = 0
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                n = max(n, int(row["row"]) + 1, int(row["col"]) + 1)
    if n <= 0:
        raise ValueError("pattern CSV is empty")
    return n


def load_pattern_image(path: Path, n: int, bins: int) -> tuple[np.ndarray, int]:
    image = np.zeros((bins, bins), dtype=np.uint8)
    count = 0
    denom = max(1, n - 1)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            r = int(row["row"])
            c = int(row["col"])
            rb = min(bins - 1, (r * bins) // denom)
            cb = min(bins - 1, (c * bins) // denom)
            image[rb, cb] = 1
            count += 1
    if count == 0:
        raise ValueError(f"pattern CSV is empty: {path}")
    return image, count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-csv", required=True)
    parser.add_argument("--parallel-csv", required=True)
    parser.add_argument("--metadata", default=None)
    parser.add_argument("--out-base", required=True, help="output path without extension")
    parser.add_argument("--title", default="WindHub stiffness sparse pattern")
    parser.add_argument("--bins", type=int, default=1800, help="raster bins per matrix axis")
    args = parser.parse_args()

    metadata = {}
    if args.metadata:
        metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    n = int(metadata.get("mesh", {}).get("dofs", 0)) if metadata else 0
    if n <= 0:
        n = infer_dimension([Path(args.serial_csv), Path(args.parallel_csv)])
    bins = min(max(64, args.bins), n)
    serial_image, serial_nnz = load_pattern_image(Path(args.serial_csv), n, bins)
    parallel_image, parallel_nnz = load_pattern_image(Path(args.parallel_csv), n, bins)

    fig, axes = plt.subplots(1, 2, figsize=(13.4, 6.9), sharex=True, sharey=True)
    panels = [
        (axes[0], serial_image, serial_nnz, "Serial CSR pattern"),
        (axes[1], parallel_image, parallel_nnz, "Parallel assembled pattern"),
    ]
    for ax, image, nnz, panel_title in panels:
        ax.imshow(
            image,
            cmap="Greys",
            origin="upper",
            interpolation="nearest",
            extent=(0, n, n, 0),
            rasterized=True,
        )
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(0, n)
        ax.set_ylim(n, 0)
        ax.set_xlabel("column")
        ax.set_ylabel("row")
        style_axis(ax, grid_axis="none", title=panel_title)
        ax.text(
            0.02,
            0.98,
            f"n={n:,}\nnnz={nnz:,}\nraster={bins}x{bins}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            color=MUTED,
            bbox={"boxstyle": "round,pad=0.28", "facecolor": "white", "edgecolor": "#d1d5db", "alpha": 0.92},
        )

    subtitle = ""
    if metadata:
        parallel = metadata.get("parallel", {})
        correctness = metadata.get("correctness", {})
        subtitle = (
            f"{metadata.get('case_name', '')} | {metadata.get('kernel', '')} | "
            f"{parallel.get('algorithm', '')} @ {parallel.get('threads', '')}T | "
            f"rel_l2={correctness.get('relative_l2', 0):.3e}, max_abs={correctness.get('max_abs', 0):.3e}"
        )
    fig.suptitle(args.title, x=0.02, y=0.985, ha="left", va="top", fontsize=22, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.02, 0.925, subtitle, ha="left", va="top", fontsize=11.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.0, 1, 0.9))
    save_figure(fig, Path(args.out_base))
    plt.close(fig)
    print(f"[OK] wrote {Path(args.out_base).with_suffix('.png')} and .svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
