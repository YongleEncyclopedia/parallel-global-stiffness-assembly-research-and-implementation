#!/usr/bin/env python3
"""Plot CPU benchmark CSV output without requiring pandas."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV contains no data: {path}")
    return [row for row in rows if row.get("status") == "PASS"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args()

    rows = load_rows(args.csv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    by_algorithm: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_algorithm[row["algorithm"]].append(row)

    case_name = Path(rows[0]["mesh"]).stem if rows else args.csv.stem
    for metric, ylabel in [("assembly_ms", "Assembly time (ms)"),
                           ("speedup", "Speedup vs 1-thread serial baseline")]:
        plt.figure()
        for algo, group in sorted(by_algorithm.items()):
            group = sorted(group, key=lambda row: int(row["threads"]))
            xs = [int(row["threads"]) for row in group]
            ys = [float(row[metric]) for row in group]
            plt.plot(xs, ys, marker="o", linewidth=2.0, label=algo)
        plt.xlabel("Threads")
        plt.ylabel(ylabel)
        plt.title(case_name)
        if metric == "speedup":
            plt.axhline(1.0, linestyle="--", linewidth=1.0, color="black", alpha=0.5)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.out_dir / f"{args.csv.stem}_{metric}.png", dpi=180)
        plt.close()

    summary_path = args.out_dir / f"{args.csv.stem}_summary.md"
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("| algorithm | threads | assembly_ms | speedup | rel_l2 | extra_memory_bytes |\n")
        handle.write("| --- | ---: | ---: | ---: | ---: | ---: |\n")
        for row in sorted(rows, key=lambda item: (item["algorithm"], int(item["threads"]))):
            handle.write(
                f"| {row['algorithm']} | {row['threads']} | {float(row['assembly_ms']):.6f} | "
                f"{float(row['speedup']):.6f} | {float(row['rel_l2']):.3e} | "
                f"{int(float(row['extra_memory_bytes']))} |\n"
            )


if __name__ == "__main__":
    main()
