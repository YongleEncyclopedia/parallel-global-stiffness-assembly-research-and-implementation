#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate benchmark CSV properties used by the project report."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


EXPECTED_ALGORITHMS = {"CPU_Serial", "Atomic_WarpAgg", "Block_Parallel", "Work_Queue"}


def default_csv_path() -> Path:
    project_dir = Path(__file__).resolve().parents[1]
    return project_dir / "results" / "benchmark_results_2026-01-30.csv"


def validate(csv_path: Path) -> bool:
    with csv_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"CSV file is empty: {csv_path}")

    errors = [float(row["Error"]) for row in rows]
    speedups = [float(row["Speedup"]) for row in rows]
    dofs = [int(row["DOFs"]) for row in rows]
    algorithms = [row["Algorithm"] for row in rows]

    print("=== Benchmark Property Validation ===\n")
    print(f"CSV: {csv_path}\n")

    max_error = max(errors)
    pbt01 = max_error < 1e-10
    print("PBT-01: all GPU errors < 1e-10")
    print(f"        max error = {max_error:.2e}")
    print(f"        result: {'PASS' if pbt01 else 'FAIL'}\n")

    pbt02 = "Prefix_Scan" not in algorithms and "PrefixScan" not in algorithms
    print("PBT-02: PrefixScan absent from output")
    print(f"        algorithms = {sorted(set(algorithms))}")
    print(f"        result: {'PASS' if pbt02 else 'FAIL'}\n")

    pbt04 = all(speedup > 0 and math.isfinite(speedup) for speedup in speedups)
    print("PBT-04: all speedups are positive and finite")
    print(f"        min = {min(speedups):.2f}, max = {max(speedups):.2f}")
    print(f"        result: {'PASS' if pbt04 else 'FAIL'}\n")

    pbt05 = all(dof % 3 == 0 for dof in dofs)
    print("PBT-05: all DOFs are divisible by 3")
    print(f"        DOFs = {sorted(set(dofs))}")
    print(f"        result: {'PASS' if pbt05 else 'FAIL'}\n")

    actual_algorithms = set(algorithms)
    pbt06 = actual_algorithms == EXPECTED_ALGORITHMS
    print("PBT-06: algorithm names match expected report set")
    print(f"        expected = {sorted(EXPECTED_ALGORITHMS)}")
    print(f"        actual = {sorted(actual_algorithms)}")
    print(f"        result: {'PASS' if pbt06 else 'FAIL'}\n")

    all_passed = all([pbt01, pbt02, pbt04, pbt05, pbt06])
    print("=" * 40)
    print(f"OVERALL: {'ALL PROPERTIES PASS' if all_passed else 'SOME PROPERTIES FAIL'}")
    print("=" * 40)
    return all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv",
        nargs="?",
        type=Path,
        default=default_csv_path(),
        help="Benchmark CSV path. Defaults to results/benchmark_results_2026-01-30.csv.",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        parser.error(f"CSV file not found: {args.csv}")

    return 0 if validate(args.csv) else 1


if __name__ == "__main__":
    raise SystemExit(main())
