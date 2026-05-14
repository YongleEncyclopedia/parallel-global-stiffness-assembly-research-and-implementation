#!/usr/bin/env python3
"""Unit tests for core-profile acceleration comparison helpers."""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from plot_core_profile_comparison import (  # noqa: E402
    ProfileInput,
    best_bound_records,
    platform_rows,
)


def write_combined_csv(root: Path, rows: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "env_group",
        "algorithm",
        "threads",
        "assembly_ms",
        "speedup",
        "status",
    ]
    with (root / "thread_scaling_combined.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class CoreProfileComparisonTests(unittest.TestCase):
    def test_best_bound_records_ignore_default_failed_and_slower_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_combined_csv(
                root,
                [
                    {"env_group": "default", "algorithm": "cpu_atomic", "threads": 8, "assembly_ms": 10.0, "speedup": 5.0, "status": "PASS"},
                    {"env_group": "bound", "algorithm": "cpu_atomic", "threads": 1, "assembly_ms": 30.0, "speedup": 1.0, "status": "PASS"},
                    {"env_group": "bound", "algorithm": "cpu_atomic", "threads": 2, "assembly_ms": 20.0, "speedup": 1.5, "status": "FAIL"},
                    {"env_group": "bound", "algorithm": "cpu_atomic", "threads": 4, "assembly_ms": 12.0, "speedup": 2.5, "status": "PASS"},
                    {"env_group": "bound", "algorithm": "cpu_private_csr", "threads": 2, "assembly_ms": 8.0, "speedup": 3.0, "status": "PASS"},
                ],
            )

            best = best_bound_records(root)

        self.assertEqual(best["cpu_atomic"].threads, 4)
        self.assertEqual(best["cpu_atomic"].assembly_ms, 12.0)
        self.assertEqual(best["cpu_atomic"].speedup, 2.5)
        self.assertEqual(best["cpu_private_csr"].threads, 2)

    def test_platform_rows_compute_time_ratio_against_full_host_best(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            full = base / "full"
            perf = base / "perf"
            eff = base / "eff"
            write_combined_csv(full, [{"env_group": "bound", "algorithm": "cpu_atomic", "threads": 8, "assembly_ms": 100.0, "speedup": 4.0, "status": "PASS"}])
            write_combined_csv(perf, [{"env_group": "bound", "algorithm": "cpu_atomic", "threads": 4, "assembly_ms": 125.0, "speedup": 3.2, "status": "PASS"}])
            write_combined_csv(eff, [{"env_group": "bound", "algorithm": "cpu_atomic", "threads": 2, "assembly_ms": 250.0, "speedup": 2.1, "status": "PASS"}])

            rows = platform_rows(
                [
                    ProfileInput("full_host", "Full host", full),
                    ProfileInput("performance_core_only", "P only", perf),
                    ProfileInput("efficiency_core_only", "E only", eff),
                ]
            )

        by_profile = {row.profile_id: row for row in rows}
        self.assertEqual(by_profile["full_host"].time_ratio, 1.0)
        self.assertEqual(by_profile["performance_core_only"].time_ratio, 1.25)
        self.assertEqual(by_profile["efficiency_core_only"].time_ratio, 2.5)


if __name__ == "__main__":
    unittest.main()
